from typing import List, Optional
from pydantic import BaseModel, Field


class ExternalPaperMetadata(BaseModel):
    id: str = Field(..., description="Unique external identifier (e.g., OpenAlex work ID or DOI)")
    title: str = Field(..., description="Full paper title")
    authors: List[str] = Field(default_factory=list, description="List of author names")
    publication_year: Optional[int] = Field(None, description="Year of publication")
    abstract: Optional[str] = Field(None, description="Paper abstract or summary")
    doi: Optional[str] = Field(None, description="Digital Object Identifier (DOI)")
    landing_page_url: Optional[str] = Field(None, description="Landing page or publisher URL")
    pdf_url: Optional[str] = Field(None, description="Direct Open Access PDF URL")
    is_open_access: bool = Field(False, description="Whether the paper has a verified open access version")
    citation_count: int = Field(0, description="Total recorded citation count")
    venue: Optional[str] = Field(None, description="Journal, conference, or repository host")
    source: str = Field("openalex", description="Source academic index (e.g. openalex, semantic_scholar)")


class DiscoverySearchResponse(BaseModel):
    query: str
    total_results: int
    page: int
    per_page: int
    results: List[ExternalPaperMetadata]


class DirectIngestRequest(BaseModel):
    doi_or_url: str = Field(..., description="DOI (e.g. 10.1145/...) or direct Open Access PDF URL")
    workspace_id: Optional[str] = Field(None, description="Optional target workspace ID")
    title: Optional[str] = Field(None, description="Optional override title for the paper")


class DirectIngestResponse(BaseModel):
    document_id: str
    job_id: str
    filename: str
    title: str
    status: str
    message: str


class CitationNetworkResponse(BaseModel):
    document_id: str
    document_title: str
    doi: Optional[str] = None
    citation_count: int = 0
    references: List[ExternalPaperMetadata] = Field(default_factory=list, description="Outbound citations (papers cited by this work)")
    cited_by: List[ExternalPaperMetadata] = Field(default_factory=list, description="Inbound citations (papers that cite this work)")
    top_related: List[ExternalPaperMetadata] = Field(default_factory=list, description="Top related papers based on citation co-occurrence")
