from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field

class DocumentMetadataOut(BaseModel):
    id: str
    document_id: str
    title: str
    authors: Optional[list[str]] = []
    abstract: Optional[str] = None
    keywords: Optional[list[str]] = []
    publication_date: Optional[str] = None
    doi: Optional[str] = None
    journal_or_conference: Optional[str] = None
    total_pages: int
    raw_metadata: Optional[dict[str, Any]] = {}
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DocumentProcessingJobOut(BaseModel):
    id: str
    document_id: str
    status: str
    stage: str
    progress_pct: float
    attempts: int
    max_retries: int
    error_details: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ExtractedContentOut(BaseModel):
    id: str
    document_id: str
    chunk_id: str
    content_type: str
    source_text: str
    page_number: int
    section: str
    subsection: Optional[str] = None
    extraction_method: str
    bounding_box: Optional[dict[str, Any]] = None
    order_index: int
    created_at: datetime

    class Config:
        from_attributes = True

class ExtractedSectionOut(BaseModel):
    id: str
    document_id: str
    section_title: str
    section_level: int
    start_page: int
    end_page: int
    order_index: int

    class Config:
        from_attributes = True

class ExtractedPageOut(BaseModel):
    id: str
    document_id: str
    page_number: int
    width: float
    height: float
    text_length: int
    has_images: bool
    has_tables: bool

    class Config:
        from_attributes = True

class DocumentOut(BaseModel):
    id: str
    user_id: str
    workspace_id: Optional[str] = None
    filename: str
    file_size_bytes: int
    mime_type: str
    file_hash_sha256: str
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    metadata: Optional[DocumentMetadataOut] = Field(None, alias="doc_metadata")
    latest_job: Optional[DocumentProcessingJobOut] = None

    class Config:
        from_attributes = True
        populate_by_name = True

class DocumentDetailOut(DocumentOut):
    extracted_pages: list[ExtractedPageOut] = []
    extracted_sections: list[ExtractedSectionOut] = []
    extracted_contents: list[ExtractedContentOut] = []

class DocumentUploadResponse(BaseModel):
    document: DocumentOut
    job: DocumentProcessingJobOut
    message: str = "Document uploaded successfully and queued for extraction"
    document_id: Optional[str] = None
    filename: Optional[str] = None
    graph: Optional[dict[str, Any]] = None
    hierarchy: Optional[list[dict[str, Any]]] = None
    evidence: Optional[list[dict[str, Any]]] = None

class BatchUploadResponse(BaseModel):
    successful: list[DocumentUploadResponse]
    failed: list[dict[str, str]]
    total_uploaded: int


# --- Hierarchical Graph / Tree Data Contracts ---

class DocumentTreeNodeSchema(BaseModel):
    id: str
    label: str
    level: int  # 0: Root, 1: H1, 2: H2, 3: Flashcard
    topic_cluster: str
    panel_payload: str

    class Config:
        from_attributes = True


class DocumentTreeLinkSchema(BaseModel):
    source: str
    target: str
    relationship: Optional[str] = None

    class Config:
        from_attributes = True


class DocumentTreeDataResponse(BaseModel):
    nodes: list[DocumentTreeNodeSchema]
    links: list[DocumentTreeLinkSchema]

