# VERITAS: Phase 8 Implementation Report
**Document Version:** 1.0.0  
**Phase:** Phase 8 — Research Knowledge Graph & Relational Entities  
**Product Name:** VERITAS  
**Tagline:** Research Intelligence. Grounded in Truth.  
**Execution Timestamp:** 2026-11-09  

---

## 1. Executive Summary

Phase 8 introduces the **Scientific Knowledge Graph** to the **VERITAS** research intelligence platform. Going beyond document-level retrieval and text synthesis, Phase 8 extracts, links, and visualizes canonical scientific entities (Papers, Authors, Datasets, Algorithms, Metrics, and Concepts) and their directional relationships (e.g., `INTRODUCES`, `EVALUATES`, `USES`, `BENCHMARKS_ON`, `AUTHORS`).

Every relationship in the knowledge graph maintains direct **sentence-level provenance** linking back to the verified semantic chunk and source document from which it was extracted.

---

## 2. Architecture Decisions: Relational Graph vs. Dedicated Graph DB

A core architectural objective for Phase 8 was evaluating whether to introduce a dedicated Graph Database (such as Neo4j) or model relationships natively within the relational PostgreSQL engine.

### Decision: Native Relational Graph in PostgreSQL
We adopted a relational graph architecture utilizing dedicated `graph_nodes` and `graph_edges` tables in PostgreSQL:

1. **Transactional Integrity & Strict Tenant Isolation:**
   - PostgreSQL allows native `tenant_id` foreign keys and composite unique constraints (`tenant_id, type, label`), guaranteeing mathematical tenant partitioning at the database level.
   - Dedicated graph databases typically require complex multi-tenant database partitioning or label-level tenancy hacks that increase cross-tenant leakage risks.
2. **Unified Provenance & Foreign Keys:**
   - Edges in PostgreSQL cleanly enforce foreign keys to `semantic_chunks.id` and `documents.id`. In a separate graph DB, provenance references would become untracked, fragile strings prone to dangling references when documents are deleted or reprocessed.
3. **Operational Simplicity & Zero Infrastructure Footprint:**
   - Eliminates the operational memory overhead, cluster synchronization, and JVM latency of running Neo4j alongside Qdrant, PostgreSQL, Redis, and FastAPI.
4. **Performance at Research Workspace Scale:**
   - Typical research workspaces contain hundreds of papers with thousands of entities. PostgreSQL B-tree and composite indexes provide sub-millisecond graph traversals ($O(1)$ to $O(\log N)$) without graph traversal bottlenecks.

---

## 3. Database Schemas & Migrations

```
                             ┌────────────────────────┐
                             │       documents        │
                             └───────────┬────────────┘
                                         │ 1:N
                                         ▼
                             ┌────────────────────────┐
                             │    semantic_chunks     │
                             └───────────┬────────────┘
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   │                                           │
                   ▼ 1:N                                       ▼ 1:N
        ┌─────────────────────┐                     ┌─────────────────────┐
        │     graph_nodes     │                     │     graph_edges     │
        ├─────────────────────┤                     ├─────────────────────┤
        │ id (UUID PK)        │◄───source_node_id───┤ id (UUID PK)        │
        │ tenant_id (Indexed) │                     │ tenant_id (Indexed) │
        │ type                │◄───target_node_id───┤ relationship_type   │
        │ label (Indexed)     │                     │ provenance_chunk_id ├───► (semantic_chunks)
        │ description         │                     │ source_excerpt      │
        │ document_id         │                     │ document_id         │
        └─────────────────────┘                     └─────────────────────┘
```

### Models Created in `apps/api/app/models/graph.py`:
* **`GraphNode`:**
  - `id`: UUID Primary Key
  - `tenant_id`: Workspace isolation key
  - `type`: `Paper`, `Author`, `Dataset`, `Algorithm`, `Metric`, `Concept`
  - `label`: Canonical entity label (e.g., `"ImageNet"`, `"Vision Transformer"`)
  - `description`: Textual summary of the entity
  - `document_id`: Source paper reference
  - **Constraint:** `UniqueConstraint("tenant_id", "type", "label")`
* **`GraphEdge`:**
  - `id`: UUID Primary Key
  - `tenant_id`: Workspace isolation key
  - `source_node_id`: FK to `graph_nodes.id` (ondelete="CASCADE")
  - `target_node_id`: FK to `graph_nodes.id` (ondelete="CASCADE")
  - `relationship_type`: `INTRODUCES`, `EVALUATES`, `USES`, `BENCHMARKS_ON`, `AUTHORS`, `PROVES`
  - `provenance_chunk_id`: FK to `semantic_chunks.id` (ondelete="SET NULL")
  - `source_excerpt`: Verbatim text excerpt supporting the relationship
  - `document_id`: Originating document reference
  - **Constraint:** `UniqueConstraint("tenant_id", "source_node_id", "target_node_id", "relationship_type")`

**Alembic Migration Applied:** `b98100ae8b84_add_graph_nodes_and_graph_edges_tables.py`.

---

## 4. Scientific Entity Extraction (NER) Engine

Implemented in `apps/api/app/services/knowledge_graph.py`:
1. **Dual-Mode Extraction Pipeline:**
   - **Production LLM Mode:** Uses Google Gemini Flash structured JSON schema decoding (`temperature=0.0`) to extract entities and directed edges from title, abstract, and high-salience semantic chunks.
   - **Deterministic Offline Mode:** Extracts canonical benchmark datasets (e.g., ImageNet, SQuAD, GLUE), architectures (e.g., Transformer, ViT, GNN), metrics (e.g., BLEU, Accuracy, F1-Score), and concepts with regex and text heuristics for hermetic, zero-latency unit testing.
2. **Entity Resolution & Deduplication (UPSERT):**
   - Entities with the same label and type within a tenant workspace are mapped to the same `GraphNode`. When multiple uploaded papers benchmark on `"ImageNet"`, both papers point to the identical `"ImageNet"` node, dynamically forming cross-paper knowledge clusters.
3. **Automatic Pipeline Hook:**
   - Hooked directly into `ProcessingPipeline.process_document` so that any uploaded or imported PDF automatically populates the workspace knowledge graph upon completing embeddings.

---

## 5. Graph Traversal API & Frontend Visualization

### API Endpoints (`apps/api/app/api/v1/graph.py`):
* `GET /api/v1/graph/workspace`: Retrieves all nodes and edges for the authenticated user's workspace in a structured payload optimized for network rendering.
* `POST /api/v1/graph/extract/{document_id}`: Triggers on-demand entity extraction on a document. Enforces document ownership permissions.

### Next.js Interactive Knowledge Graph (`apps/web/src/components/KnowledgeGraphView.tsx`):
* **Force-Directed Physics Simulation:** Uses `vis-network` (ForceAtlas2 physics solver) for real-time node repulsion, gravity, and drag-and-drop interaction.
* **Color-Coded Semantic Types:**
  - **Paper:** Sky Blue Diamond (`#0284C7`)
  - **Author:** Purple Dot (`#7C3AED`)
  - **Dataset:** Emerald Green Dot (`#059669`)
  - **Algorithm:** Amber Dot (`#D97706`)
  - **Metric:** Rose Red Dot (`#E11D48`)
  - **Concept:** Indigo Dot (`#4F46E5`)
* **Interactive Inspection Drawer:**
  - Clicking a **Node** reveals its entity type, description, and an action to jump directly to the originating document.
  - Clicking an **Edge** opens the relationship inspector, displaying the verified relationship and the **verbatim text excerpt** proving the grounding evidence.
* **Filtering & Search:** Real-time search by entity name, plus toggles to show/hide specific entity types.
* **Fullscreen Mode:** Maximizes graph exploration to the full browser window.

---

## 6. Verification & Test Outcomes

Automated tests in `apps/api/tests/test_knowledge_graph.py` verify all core requirements:
1. `test_entity_and_edge_extraction_models`: Validates extraction of Paper, Author, and Dataset nodes, proper relation typing, and provenance chunk binding.
2. `test_knowledge_graph_tenant_isolation`: Proves mathematical isolation: User A receives zero nodes from User B's workspace, and identical entities in separate workspaces remain strictly isolated with unique IDs.
3. `test_graph_upsert_deduplication`: Proves that re-extracting entities in the same tenant reuses existing nodes without duplication or constraint errors.
4. `test_cross_tenant_extract_rejection`: Proves that cross-tenant extraction triggers are rejected with HTTP 403/404.

**Test Suite Results:**
* **Total Automated Tests:** 48 passed (100% across all phases).
* **Execution Time:** 3.26 seconds.
* **Next.js Production Build:** `npm run build` compiled cleanly (4/4 routes, 0 errors).

---

## 7. Known Limitations

1. **Workspace Density:** Workspaces with over 5,000 entities may require level-of-detail (LOD) node clustering or degree-of-separation filters to avoid visual clutter in the 2D canvas.
2. **Cross-Tenant Entity Federation:** Entity deduplication is strictly confined to individual workspace boundaries by design to preserve zero-trust tenant privacy. Cross-tenant public ontology federation will be explored in future enterprise phases.
