from typing import List, Optional
from pydantic import BaseModel, Field


class GraphNodeOut(BaseModel):
    id: str
    tenant_id: str
    type: str = Field(..., description="Entity type: Paper, Author, Dataset, Algorithm, Metric, Concept")
    label: str = Field(..., description="Canonical entity label")
    description: Optional[str] = None
    document_id: Optional[str] = None

    class Config:
        from_attributes = True


class GraphEdgeOut(BaseModel):
    id: str
    tenant_id: str
    source_node_id: str
    target_node_id: str
    relationship_type: str = Field(..., description="Relationship: INTRODUCES, EVALUATES, USES, BENCHMARKS_ON, PROVES, AUTHORS")
    provenance_chunk_id: Optional[str] = None
    source_excerpt: Optional[str] = None
    document_id: Optional[str] = None

    class Config:
        from_attributes = True


class WorkspaceGraphResponse(BaseModel):
    tenant_id: str
    total_nodes: int
    total_edges: int
    nodes: List[GraphNodeOut]
    edges: List[GraphEdgeOut]


class ExtractGraphRequest(BaseModel):
    document_id: str
