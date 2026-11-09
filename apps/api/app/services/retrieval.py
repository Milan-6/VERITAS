import logging
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from qdrant_client import models
from app.services.vector_store import vector_store
from app.services.embeddings import dense_embedder, sparse_vectorizer

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    document_title: str
    page_number: int
    section_title: str
    subsection: Optional[str]
    content_text: str
    score: float
    dense_score: Optional[float]
    sparse_score: Optional[float]


class HybridRetrievalService:
    def __init__(self, vs=None):
        self.vs = vs or vector_store

    def search(
        self,
        query: str,
        tenant_id: str,
        document_id: Optional[str] = None,
        top_k: int = 10,
        dense_weight: float = 0.5,
        sparse_weight: float = 0.5,
    ) -> List[RetrievedChunk]:
        """
        Executes hybrid retrieval combining Dense Semantic Search and Sparse BM25 Keyword Search
        with Reciprocal Rank Fusion (RRF).

        STRICT TENANT ISOLATION:
        The query MUST enforce a boolean Must condition on `tenant_id == tenant_id`.
        """
        clean_query = query.strip()
        if not clean_query:
            return []

        # 1. Construct mandatory tenant security filter (SEC-01)
        must_conditions: List[models.Condition] = [
            models.FieldCondition(
                key="tenant_id",
                match=models.MatchValue(value=tenant_id),
            )
        ]

        if document_id:
            must_conditions.append(
                models.FieldCondition(
                    key="document_id",
                    match=models.MatchValue(value=document_id),
                )
            )

        security_filter = models.Filter(must=must_conditions)

        # 2. Compute query dense embedding and sparse BM25 vector
        query_dense = self.vs.embedder.embed_text(clean_query)
        query_sparse = sparse_vectorizer.vectorize(clean_query)

        candidate_limit = max(top_k * 3, 20)

        # 3. Dense Vector Search
        dense_results = self.vs.client.query_points(
            collection_name=self.vs.collection_name,
            query=query_dense,
            using="dense",
            query_filter=security_filter,
            limit=candidate_limit,
            with_payload=True,
        )

        # 4. Sparse Vector BM25 Search
        sparse_results = self.vs.client.query_points(
            collection_name=self.vs.collection_name,
            query=query_sparse,
            using="sparse",
            query_filter=security_filter,
            limit=candidate_limit,
            with_payload=True,
        )

        # 5. Reciprocal Rank Fusion (RRF) Reranking
        k_rrf = 60.0
        dense_ranks: Dict[str, int] = {}
        dense_scores: Dict[str, float] = {}
        candidates_by_point_id: Dict[str, Any] = {}

        for rank, pt in enumerate(dense_results.points, start=1):
            pid = str(pt.id)
            dense_ranks[pid] = rank
            dense_scores[pid] = float(pt.score) if pt.score is not None else 0.0
            candidates_by_point_id[pid] = pt

        sparse_ranks: Dict[str, int] = {}
        sparse_scores: Dict[str, float] = {}
        for rank, pt in enumerate(sparse_results.points, start=1):
            pid = str(pt.id)
            sparse_ranks[pid] = rank
            sparse_scores[pid] = float(pt.score) if pt.score is not None else 0.0
            candidates_by_point_id[pid] = pt

        all_candidate_ids = set(candidates_by_point_id.keys())
        scored_candidates = []

        for pid in all_candidate_ids:
            pt = candidates_by_point_id[pid]
            dense_rank = dense_ranks.get(pid)
            sparse_rank = sparse_ranks.get(pid)
            d_val = dense_scores.get(pid, 0.0)

            # Prune completely irrelevant candidates (non-positive similarity & zero keyword matches)
            if sparse_rank is None and d_val <= 0.0:
                continue

            rrf_score = 0.0
            if dense_rank is not None and d_val > 0.0:
                rrf_score += dense_weight * (1.0 / (k_rrf + dense_rank))
            if sparse_rank is not None:
                rrf_score += sparse_weight * (1.0 / (k_rrf + sparse_rank))

            if rrf_score > 0.0:
                scored_candidates.append(
                    (
                        rrf_score,
                        pt,
                        dense_scores.get(pid),
                        sparse_scores.get(pid),
                    )
                )

        # Sort descending by RRF score
        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        # 6. Format final Top-K results
        final_results: List[RetrievedChunk] = []
        for rrf_score, pt, d_score, s_score in scored_candidates[:top_k]:
            payload = pt.payload or {}
            final_results.append(
                RetrievedChunk(
                    chunk_id=payload.get("chunk_id", str(pt.id)),
                    document_id=payload.get("document_id", ""),
                    document_title=payload.get("document_title", "Untitled Document"),
                    page_number=payload.get("page_number", 1),
                    section_title=payload.get("section_title", "General"),
                    subsection=payload.get("subsection"),
                    content_text=payload.get("content_text", ""),
                    score=round(float(rrf_score), 6),
                    dense_score=round(d_score, 4) if d_score is not None else None,
                    sparse_score=round(s_score, 4) if s_score is not None else None,
                )
            )

        return final_results


retrieval_service = HybridRetrievalService()
