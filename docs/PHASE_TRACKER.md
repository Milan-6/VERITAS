# VERITAS: Phase Tracking & Implementation Roadmap
**Product Name:** VERITAS  
**Tagline:** Research Intelligence. Grounded in Truth.  
**Former Name:** ScholarPulse AI (Permanently Retired)  
**Last Updated:** 2026-11-09  

---

## Phase Overview

| Phase | Description | Status |
| :--- | :--- | :--- |
| **Phase 0** | Baseline Audit, Architecture & Threat Modeling | **COMPLETED** |
| **Phase 1** | Foundations, Secure Ingestion & Document Processing Engine | **COMPLETED** |
| **Phase 2** | Research Intelligence & Hybrid Retrieval | **COMPLETED** |
| **Phase 3** | Grounded AI Research Assistant & Conversational Memory | **COMPLETED** |
| **Phase 4** | Evidence Verification Engine & Claim Entailment Analysis | **COMPLETED** |
| **Phase 5** | Scientific Intelligence & Comparative Literature Analysis | **COMPLETED** |
| **Phase 6** | Academic Research Discovery & Citation Networks | **COMPLETED** |
| **Phase 8** | Research Knowledge Graph & Relational Entities | **COMPLETED** |
| **Phase 9** | Autonomous AI Research Agents & Multi-Paper Synthesis | **PLANNED** (Next Phase) |

---

## Phase 8 Detailed Milestones & Tasks

| Task ID | Milestone / Deliverable | Status | Verification Detail |
| :--- | :--- | :--- | :--- |
| **P8-M1** | Prerequisite Verification & Audit | **COMPLETED** | Inspected Phase 6 discovery routes and report, verified baseline 44/44 tests passing. |
| **P8-M2** | Graph Database Schemas & Migrations | **COMPLETED** | Created `GraphNode` and `GraphEdge` models in `app/models/graph.py` with unique constraints and foreign keys to `documents` and `semantic_chunks`. Applied Alembic migration `b98100ae8b84`. |
| **P8-M3** | Scientific Entity Extraction (NER) | **COMPLETED** | Implemented `KnowledgeGraphService` in `app/services/knowledge_graph.py` with dual-mode Gemini JSON schema and deterministic fallback. Integrated automatic extraction hook upon document indexing completion in `ProcessingPipeline`. |
| **P8-M4** | Graph Traversal API | **COMPLETED** | Built `GET /api/v1/graph/workspace` and `POST /api/v1/graph/extract/{document_id}` in `app/api/v1/graph.py` with strict tenant isolation and provenance mapping. |
| **P8-M5** | Frontend Graph Visualization | **COMPLETED** | Built interactive `KnowledgeGraphView.tsx` using `vis-network` ForceAtlas2 physics solver. Features type color coding, search bar, entity type toggles, and side drawer for entity inspection and verified grounding excerpts. Next.js production build verified. |
| **P8-M6** | Testing and Security Verification | **COMPLETED** | Created `apps/api/tests/test_knowledge_graph.py`. 48 automated tests passing (4 new Phase 8 tests). Proved entity/relation extraction, strict multi-tenant isolation, UPSERT deduplication, and cross-tenant extraction rejection. |
| **P8-M7** | Git Management & Documentation | **COMPLETED** | Authored `docs/VERITAS_PHASE_8_IMPLEMENTATION_REPORT.md` and updated `docs/PHASE_TRACKER.md`. Local git commits recorded. |

---

## Phase 6 Detailed Milestones & Tasks

| Task ID | Milestone / Deliverable | Status | Verification Detail |
| :--- | :--- | :--- | :--- |
| **P6-M1** | Prerequisite Verification & Audit | **COMPLETED** | Inspected Phase 5 analysis routes and report, verified baseline 38/38 tests passing. |
| **P6-M2** | External Discovery Service Integration | **COMPLETED** | Implemented `ExternalDiscoveryService` in `app/services/discovery.py` and schemas in `app/schemas/discovery.py`. OpenAlex works query client with polite pool `mailto`, inverted index abstract decoder, and 300s TTL cache. |
| **P6-M3** | Direct Ingestion Pipeline & SSRF Protection | **COMPLETED** | Built `validate_safe_url` blocking private IPs, loopback, link-local IMDS `169.254.169.254`, and non-HTTP protocols. Implemented `download_and_ingest_paper` streaming PDF download, magic bytes validation, and automatic processing queue entry. |
| **P6-M4** | Citation Network Mapping | **COMPLETED** | Built `get_citation_network` querying OpenAlex for inbound citing works (`cites:`), outbound references, and co-occurrence related literature recommendations. |
| **P6-M5** | API & Frontend Integration | **COMPLETED** | Implemented `/api/v1/discovery/search`, `/api/v1/discovery/ingest`, and `/api/v1/discovery/citations/{id}` in `apps/api/app/api/v1/discovery.py`. Built `GlobalDiscoveryView.tsx` with search filters, direct DOI import, and citation network drawer. Added "Citation Graph" tab in `DocumentDetailView.tsx`. Next.js production build verified. |
| **P6-M6** | Testing and Security Verification | **COMPLETED** | Created `apps/api/tests/test_academic_discovery.py`. 44 automated tests passing (6 new Phase 6 tests). Verified OpenAlex search normalization, citation graph mapping, SSRF rejections, and direct PDF download flow. |
| **P6-M7** | Git Management & Documentation | **COMPLETED** | Authored `docs/VERITAS_PHASE_6_IMPLEMENTATION_REPORT.md` and updated `docs/PHASE_TRACKER.md`. Local git commits recorded. |

---

## Phase 5 Detailed Milestones & Tasks

| Task ID | Milestone / Deliverable | Status | Verification Detail |
| :--- | :--- | :--- | :--- |
| **P5-M1** | Prerequisite Verification & Audit | **COMPLETED** | Inspected Phase 4 deliverables (`verification.py`, `docs/VERITAS_PHASE_4_IMPLEMENTATION_REPORT.md`), verified baseline 35/35 tests passing. |
| **P5-M2** | Structured Paper Synthesis Service | **COMPLETED** | Implemented `AcademicExtractionService` in `app/services/academic_extraction.py` and schemas in `app/schemas/analysis.py`. Extracts 5 core dimensions (`Problem_Statement`, `Methodology`, `Dataset_Used`, `Key_Results`, `Limitations`) using targeted hybrid chunk retrieval with page-level citations and direct source quotes. |
| **P5-M3** | Cross-Paper Comparative Matrix Engine | **COMPLETED** | Implemented `LiteratureMatrixService` in `app/services/literature_matrix.py`. Supports 2-5 papers, multi-tenant document validation (SEC-01), dimension alignment, and empirical contradiction / methodological divergence heuristics. |
| **P5-M4** | API & Frontend Integration | **COMPLETED** | Implemented endpoints in `app/api/v1/analysis.py` (`GET /summary/{document_id}` and `POST /matrix`). Added "Structured Synthesis" tab to `DocumentDetailView.tsx` and created `LiteratureMatrixView.tsx` with document multi-selection, comparative matrix, and contradiction alerts. Next.js production build verified. |
| **P5-M5** | Testing and Security Verification | **COMPLETED** | Created `apps/api/tests/test_literature_analysis.py`. 38 automated tests passing (3 new Phase 5 tests). Proved single document synthesis, SEC-01 cross-tenant rejection with HTTP 403, and multi-paper matrix generation with contradiction detection. |
| **P5-M6** | Git Management & Documentation | **COMPLETED** | Created `docs/VERITAS_PHASE_5_IMPLEMENTATION_REPORT.md` and updated `docs/PHASE_TRACKER.md`. Commits cleanly recorded locally. |

---

## Phase 4 Detailed Milestones & Tasks

| Task ID | Milestone / Deliverable | Status | Verification Detail |
| :--- | :--- | :--- | :--- |
| **P4-M1** | Prerequisite Verification & Audit | **COMPLETED** | Inspected Phase 3 deliverables (`apps/api/app/api/v1/chat.py`, `app/services/llm.py`), verified 31/31 baseline tests pass. |
| **P4-M2** | Atomic Claim Extraction Pipeline | **COMPLETED** | Implemented `ClaimExtractor` in `app/services/verification.py`. Decomposes complex paragraphs and coordinated clauses with contrastive conjunctions into standalone factual claims; bypasses strict abstentions cleanly. |
| **P4-M3** | Entailment Verification Logic | **COMPLETED** | Implemented `EvidenceVerifier` in `app/services/verification.py`. Natural Language Inference (NLI) classification (`SUPPORTED`, `CONTRADICTED`, `MISSING`), maps supported claims to source text excerpt and page citations. Dual Gemini + deterministic offline execution. |
| **P4-M4** | API & Frontend Payload Integration | **COMPLETED** | Added `verification_report` column to `ChatMessage` with Alembic migration `e969daf54158`. Integrated into `POST /chat/sessions/{id}/messages`. Added interactive Evidence Entailment Audit Card in `ChatInterface.tsx` with claim pills and source excerpt drawers. |
| **P4-M5** | Testing and Security Verification | **COMPLETED** | Created `test_evidence_verification.py`. 35 automated tests passing (4 new Phase 4 tests). Verified extraction, contradiction detection, missing claim flagging, and chat API payload delivery. |
| **P4-M6** | Git Management & Documentation | **COMPLETED** | Created `docs/VERITAS_PHASE_4_IMPLEMENTATION_REPORT.md` and updated `docs/PHASE_TRACKER.md`. Commits cleanly recorded locally. |

---

## Phase 3 Detailed Milestones & Tasks

| Task ID | Milestone / Deliverable | Status | Verification Detail |
| :--- | :--- | :--- | :--- |
| **P3-M1** | Prerequisite Verification & Audit | **COMPLETED** | Inspected Phase 2 hybrid retrieval, Qdrant vectors, verified 26/26 backend tests pass. |
| **P3-M2** | Conversational Memory & Database Schemas | **COMPLETED** | Implemented `ChatSession` and `ChatMessage` models in `app/models/chat.py`. Generated and applied Alembic migration `b56ff4efae49_add_chat_sessions_and_messages_tables.py`. |
| **P3-M3** | LLM Provider Abstraction & Prompt Management | **COMPLETED** | Built `GeminiLLMProvider` (Google Gemini with exponential backoff) and `DeterministicChatProvider` in `app/services/llm.py`. Enforced `temperature=0.0`, strict system prompt, and exact abstention fallback `"This is not mentioned in the provided research corpus."`. |
| **P3-M4** | RAG Context Construction & Chat API | **COMPLETED** | Implemented RESTful chat endpoints in `app/api/v1/chat.py` (`POST /sessions`, `GET /sessions`, `GET /sessions/{id}`, `DELETE /sessions/{id}`, `POST /sessions/{id}/messages`). Assembles last 8 turns, executes hybrid search with strict tenant isolation, queries LLM, persists messages and citations. |
| **P3-M5** | Frontend Chat Interface | **COMPLETED** | Created `ChatInterface.tsx` in Next.js 14 frontend. Charcoal/navy design, session management sidebar, interactive citation badges (`[Document: X, Page: Y]`), grounding evidence drawer, strict abstention alert. Next.js production build verified. |
| **P3-M6** | Testing and Security Verification | **COMPLETED** | Created `test_chat_assistant.py`. 31 automated tests passing (5 new Phase 3 tests). Proved multi-tenant isolation, exact abstention string compliance, citation provenance, and multi-turn session persistence. |
| **P3-M7** | Git Management & Documentation | **COMPLETED** | Created `docs/VERITAS_PHASE_3_IMPLEMENTATION_REPORT.md` and updated `docs/PHASE_TRACKER.md`. Commits cleanly recorded locally. |

---

## Phase 2 Detailed Milestones & Tasks

| Task ID | Milestone / Deliverable | Status | Verification Detail |
| :--- | :--- | :--- | :--- |
| **P2-M1** | Prerequisite Verification & Audit | **COMPLETED** | Inspected Phase 1 outputs, database schemas (`Document`, `ExtractedContent`, `ExtractedPage`), verified 18/18 Phase 1 tests pass cleanly. |
| **P2-M2** | Section-Aware Semantic Chunking | **COMPLETED** | Implemented `SectionAwareChunker` in `app/services/chunker.py`. Sentence-boundary preserving window (800 tokens, 150 token overlap), structural breadcrumb injection (`[Document: ...] [Section: ...]`), and database model `SemanticChunk`. |
| **P2-M3** | Vector Database Deployment & Integration | **COMPLETED** | Integrated Qdrant Python client (`qdrant-client` 1.20) with collection `veritas_research_chunks`. Dual vector configuration: Dense vectors (768 dimensions, Cosine) and Sparse vectors (BM25). Created payload indexes for `tenant_id` and `document_id`. Local embedded storage fallback when server is offline. |
| **P2-M4** | Embedding Generation Pipeline | **COMPLETED** | Implemented modular embedding provider in `app/services/embeddings.py`. Integrated Google Gemini `models/text-embedding-004` with exponential backoff on HTTP 429 rate limits, deterministic dense embedding fallback (768d), and BM25 sparse vectorizer. Integrated into background processing pipeline. |
| **P2-M5** | Hybrid Retrieval API | **COMPLETED** | Implemented `POST /api/v1/retrieval/search` in `app/api/v1/retrieval.py`. Executes concurrent dense semantic search and sparse BM25 keyword search with Reciprocal Rank Fusion (RRF) reranking. Enforces strict tenant isolation (`tenant_id` filter) and returns complete chunk provenance (Document Title, Page, Section, Scores). |
| **P2-M6** | Testing and Security Verification | **COMPLETED** | 26 automated tests passing (8 new Phase 2 tests). Verified mathematical tenant isolation, semantic chunking overlap, Qdrant insertion and deletion synchronization, and rate-limit backoff handling. |
| **P2-M7** | Git Management & Documentation | **COMPLETED** | Meaningful commits per milestone on `master` branch. Generated `docs/VERITAS_PHASE_2_IMPLEMENTATION_REPORT.md` and updated `README.md` and `docker-compose.yml`. |
