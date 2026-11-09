from typing import Optional, List
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="Semantic or keyword research query")
    document_id: Optional[str] = Field(None, description="Optional document ID to restrict search scope")
    top_k: int = Field(10, ge=1, le=50, description="Maximum number of retrieved evidence chunks")
    dense_weight: float = Field(0.5, ge=0.0, le=1.0, description="Weight for dense semantic vector search")
    sparse_weight: float = Field(0.5, ge=0.0, le=1.0, description="Weight for sparse BM25 keyword search")


class SearchChunkResult(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    page_number: int
    section_title: str
    subsection: Optional[str] = None
    content_text: str
    score: float
    dense_score: Optional[float] = None
    sparse_score: Optional[float] = None

    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    query: str
    tenant_id: str
    total_results: int
    results: List[SearchChunkResult]
