import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.chunk import SemanticChunk
from app.models.document import Document, DocumentMetadata
from app.models.graph import GraphEdge, GraphNode
from app.schemas.graph import GraphEdgeOut, GraphNodeOut, WorkspaceGraphResponse

logger = logging.getLogger(__name__)

# Valid entity types
VALID_NODE_TYPES = {"Paper", "Author", "Dataset", "Algorithm", "Metric", "Concept"}

# Valid relationship types
VALID_EDGE_TYPES = {
    "INTRODUCES",
    "EVALUATES",
    "USES",
    "BENCHMARKS_ON",
    "PROVES",
    "AUTHORS",
    "OUTPERFORMS",
    "EXTENDS",
}


class KnowledgeGraphService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.LLM_MODEL

    def _extract_with_gemini(
        self,
        title: str,
        abstract: Optional[str],
        chunks: List[SemanticChunk],
    ) -> Dict[str, Any]:
        """
        Uses Google Gemini via structured JSON schema to extract scientific entities
        and relational edges from paper text.
        """
        if not self.api_key:
            return self._extract_deterministic_fallback(title, abstract, chunks)

        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config={
                    "temperature": 0.0,
                    "response_mime_type": "application/json",
                },
            )

            context_excerpts = "\n---\n".join(
                [f"[Chunk {c.id[:8]}] {c.content_text[:300]}" for c in chunks[:6]]
            )

            prompt = f"""You are a scientific knowledge graph extraction engine.
Analyze the following academic paper title, abstract, and text excerpts.
Extract key scientific entities (Nodes) and semantic relationships (Edges).

Paper Title: {title}
Abstract: {abstract or 'N/A'}

Text Excerpts:
{context_excerpts}

RULES:
1. Valid Node types: "Paper", "Author", "Dataset", "Algorithm", "Metric", "Concept"
2. Valid Edge relationship types: "INTRODUCES", "EVALUATES", "USES", "BENCHMARKS_ON", "PROVES", "AUTHORS", "OUTPERFORMS", "EXTENDS"
3. The paper itself should be included as a Node with type "Paper" and label "{title}".
4. For every edge, provide a direct excerpt or summary as source_excerpt.

Output JSON format strictly:
{{
  "nodes": [
    {{"type": "Dataset", "label": "ImageNet", "description": "Large-scale visual benchmark"}},
    {{"type": "Algorithm", "label": "Sparse Attention Transformer", "description": "O(N log N) attention"}}
  ],
  "edges": [
    {{
      "source_label": "{title}",
      "target_label": "Sparse Attention Transformer",
      "relationship_type": "INTRODUCES",
      "source_excerpt": "We introduce the Sparse Attention Transformer..."
    }},
    {{
      "source_label": "Sparse Attention Transformer",
      "target_label": "ImageNet",
      "relationship_type": "EVALUATES",
      "source_excerpt": "Evaluated empirically on the ImageNet validation split."
    }}
  ]
}}
"""
            response = model.generate_content(prompt)
            return json.loads(response.text)
        except Exception as e:
            logger.warning(f"Gemini entity extraction failed: {str(e)}. Falling back to deterministic extractor.")
            return self._extract_deterministic_fallback(title, abstract, chunks)

    def _extract_deterministic_fallback(
        self,
        title: str,
        abstract: Optional[str],
        chunks: List[SemanticChunk],
    ) -> Dict[str, Any]:
        """
        Deterministic, offline entity extractor for test environments and offline deployments.
        Identifies canonical scientific concepts, algorithms, datasets, and metrics from text patterns.
        """
        nodes: List[Dict[str, str]] = [
            {"type": "Paper", "label": title, "description": f"Research paper: {title}"}
        ]
        edges: List[Dict[str, str]] = []

        combined_text = f"{title} {abstract or ''} " + " ".join([c.content_text for c in chunks[:5]])

        # Canonical catalog of detectable entities
        patterns = [
            # Datasets
            (r"\b(ImageNet|SQuAD|GLUE|SuperGLUE|Common Crawl|MNIST|CIFAR-10|CIFAR-100|WMT-14|GSM8K|MATH)\b", "Dataset", "Standard evaluation benchmark dataset"),
            # Algorithms & Architectures
            (r"\b(Transformer|BERT|GPT|LLaMA|Diffusion Model|ResNet|Graph Neural Network|GNN|LSTM|DenseNet|ViT|Vision Transformer|Sparse Attention)\b", "Algorithm", "Deep learning architecture or algorithm"),
            # Metrics
            (r"\b(BLEU|ROUGE|Accuracy|Perplexity|F1[- ]Score|Exact Match|Top-1 Accuracy|Mean Squared Error|MSE|AUC-ROC)\b", "Metric", "Quantitative evaluation metric"),
            # Concepts
            (r"\b(Few-Shot Learning|Reinforcement Learning|RLHF|Attention Mechanism|Contrastive Learning|Self-Supervised Learning|Quantization|Pruning)\b", "Concept", "Fundamental machine learning methodology or concept"),
        ]

        found_labels = set()
        for regex, entity_type, desc in patterns:
            matches = re.findall(regex, combined_text, re.IGNORECASE)
            for m in matches:
                # Canonicalize casing
                canonical_label = m.strip()
                norm_key = canonical_label.lower()
                if norm_key not in found_labels:
                    found_labels.add(norm_key)
                    nodes.append({
                        "type": entity_type,
                        "label": canonical_label,
                        "description": desc,
                    })

                    # Formulate edge with Paper
                    rel_type = "EVALUATES" if entity_type == "Dataset" else ("INTRODUCES" if entity_type == "Algorithm" else "USES")
                    matching_chunk_id = chunks[0].id if chunks else None
                    edges.append({
                        "source_label": title,
                        "target_label": canonical_label,
                        "relationship_type": rel_type,
                        "source_excerpt": f"Paper examines {canonical_label} in context.",
                        "provenance_chunk_id": matching_chunk_id,
                    })

        return {"nodes": nodes, "edges": edges}

    def get_or_create_node(
        self,
        tenant_id: str,
        node_type: str,
        label: str,
        db: Session,
        description: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> GraphNode:
        """
        Retrieves or creates a GraphNode with strict tenant isolation.
        Performs case-insensitive label deduplication within the tenant workspace.
        """
        clean_label = label.strip()
        clean_type = node_type.strip()

        if clean_type not in VALID_NODE_TYPES:
            clean_type = "Concept"

        existing = (
            db.query(GraphNode)
            .filter(
                GraphNode.tenant_id == tenant_id,
                GraphNode.type == clean_type,
                func.lower(GraphNode.label) == clean_label.lower(),
            )
            .first()
        )

        if existing:
            if not existing.description and description:
                existing.description = description
                db.commit()
            return existing

        node = GraphNode(
            tenant_id=tenant_id,
            type=clean_type,
            label=clean_label,
            description=description,
            document_id=document_id,
        )
        db.add(node)
        db.commit()
        db.refresh(node)
        return node

    def get_or_create_edge(
        self,
        tenant_id: str,
        source_node_id: str,
        target_node_id: str,
        relationship_type: str,
        db: Session,
        provenance_chunk_id: Optional[str] = None,
        source_excerpt: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> GraphEdge:
        """
        Retrieves or creates a directed GraphEdge with tenant isolation and provenance linkage.
        """
        clean_rel = relationship_type.strip().upper()
        if clean_rel not in VALID_EDGE_TYPES:
            clean_rel = "USES"

        existing = (
            db.query(GraphEdge)
            .filter(
                GraphEdge.tenant_id == tenant_id,
                GraphEdge.source_node_id == source_node_id,
                GraphEdge.target_node_id == target_node_id,
                GraphEdge.relationship_type == clean_rel,
            )
            .first()
        )

        if existing:
            if not existing.provenance_chunk_id and provenance_chunk_id:
                existing.provenance_chunk_id = provenance_chunk_id
            if not existing.source_excerpt and source_excerpt:
                existing.source_excerpt = source_excerpt
            db.commit()
            return existing

        edge = GraphEdge(
            tenant_id=tenant_id,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            relationship_type=clean_rel,
            provenance_chunk_id=provenance_chunk_id,
            source_excerpt=source_excerpt,
            document_id=document_id,
        )
        db.add(edge)
        db.commit()
        db.refresh(edge)
        return edge

    def extract_entities_for_document(
        self,
        document_id: str,
        tenant_id: str,
        db: Session,
    ) -> Tuple[int, int]:
        """
        Executes scientific entity extraction on a document and updates the tenant knowledge graph.
        Returns: (nodes_created_count, edges_created_count)
        """
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return 0, 0

        title = doc.doc_metadata.title if doc.doc_metadata and doc.doc_metadata.title else doc.filename
        abstract = doc.doc_metadata.abstract if doc.doc_metadata else None

        chunks = (
            db.query(SemanticChunk)
            .filter(SemanticChunk.document_id == document_id)
            .order_by(SemanticChunk.chunk_index.asc())
            .all()
        )

        # 1. Ensure Paper Node exists
        paper_node = self.get_or_create_node(
            tenant_id=tenant_id,
            node_type="Paper",
            label=title,
            db=db,
            description=abstract or f"Academic paper: {title}",
            document_id=document_id,
        )

        # 2. Extract Authors if available
        if doc.doc_metadata and doc.doc_metadata.authors:
            for author_name in doc.doc_metadata.authors:
                if author_name.strip():
                    author_node = self.get_or_create_node(
                        tenant_id=tenant_id,
                        node_type="Author",
                        label=author_name.strip(),
                        db=db,
                        description=f"Researcher / Author",
                    )
                    self.get_or_create_edge(
                        tenant_id=tenant_id,
                        source_node_id=author_node.id,
                        target_node_id=paper_node.id,
                        relationship_type="AUTHORS",
                        db=db,
                        document_id=document_id,
                        source_excerpt=f"{author_name} is an author of {title}",
                    )

        # 3. Perform LLM or deterministic entity and edge extraction
        raw_graph = self._extract_with_gemini(title, abstract, chunks)
        raw_nodes = raw_graph.get("nodes", [])
        raw_edges = raw_graph.get("edges", [])

        label_to_node: Dict[str, GraphNode] = {title.lower(): paper_node}

        nodes_count = 0
        edges_count = 0

        # Persist extracted nodes
        for item in raw_nodes:
            n_type = item.get("type", "Concept")
            n_label = item.get("label", "").strip()
            n_desc = item.get("description")
            if not n_label:
                continue

            node_obj = self.get_or_create_node(
                tenant_id=tenant_id,
                node_type=n_type,
                label=n_label,
                db=db,
                description=n_desc,
                document_id=document_id if n_type == "Paper" else None,
            )
            label_to_node[n_label.lower()] = node_obj
            nodes_count += 1

        # Match provenance chunk for each edge
        for item in raw_edges:
            src_lbl = item.get("source_label", "").strip().lower()
            tgt_lbl = item.get("target_label", "").strip().lower()
            rel_type = item.get("relationship_type", "USES")
            excerpt = item.get("source_excerpt")

            src_node = label_to_node.get(src_lbl) or paper_node
            tgt_node = label_to_node.get(tgt_lbl)
            if not tgt_node or src_node.id == tgt_node.id:
                continue

            # Find matching chunk if excerpt is provided
            prov_chunk_id = item.get("provenance_chunk_id")
            if not prov_chunk_id and excerpt and chunks:
                for c in chunks:
                    if excerpt.lower()[:30] in c.content_text.lower():
                        prov_chunk_id = c.id
                        break
            if not prov_chunk_id and chunks:
                prov_chunk_id = chunks[0].id

            self.get_or_create_edge(
                tenant_id=tenant_id,
                source_node_id=src_node.id,
                target_node_id=tgt_node.id,
                relationship_type=rel_type,
                db=db,
                provenance_chunk_id=prov_chunk_id,
                source_excerpt=excerpt,
                document_id=document_id,
            )
            edges_count += 1

        return nodes_count, edges_count

    def get_workspace_graph(self, tenant_id: str, db: Session) -> WorkspaceGraphResponse:
        """
        Fetches the complete knowledge graph for the authenticated workspace/tenant.
        Guarantees strict tenant isolation.
        """
        nodes = (
            db.query(GraphNode)
            .filter(GraphNode.tenant_id == tenant_id)
            .order_by(GraphNode.created_at.desc())
            .all()
        )

        edges = (
            db.query(GraphEdge)
            .filter(GraphEdge.tenant_id == tenant_id)
            .order_by(GraphEdge.created_at.desc())
            .all()
        )

        return WorkspaceGraphResponse(
            tenant_id=tenant_id,
            total_nodes=len(nodes),
            total_edges=len(edges),
            nodes=[GraphNodeOut.model_validate(n) for n in nodes],
            edges=[GraphEdgeOut.model_validate(e) for e in edges],
        )


knowledge_graph_service = KnowledgeGraphService()
