import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class DocumentStatus(str, Enum):
    UPLOADED = "UPLOADED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ProcessingStage(str, Enum):
    VALIDATION = "VALIDATION"
    PARSING = "PARSING"
    TEXT_EXTRACTION = "TEXT_EXTRACTION"
    LAYOUT_ANALYSIS = "LAYOUT_ANALYSIS"
    METADATA_EXTRACTION = "METADATA_EXTRACTION"
    SECTION_RECOGNITION = "SECTION_RECOGNITION"
    PAGE_MAPPING = "PAGE_MAPPING"
    PERSISTENCE = "PERSISTENCE"
    CHUNKING = "CHUNKING"
    VECTOR_INDEXING = "VECTOR_INDEXING"
    COMPLETED = "COMPLETED"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), default="application/pdf", nullable=False)
    file_hash_sha256: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default=DocumentStatus.UPLOADED.value, nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="documents")
    workspace_associations = relationship("DocumentWorkspaceAssociation", back_populates="document", cascade="all, delete-orphan")
    doc_metadata = relationship("DocumentMetadata", back_populates="document", uselist=False, cascade="all, delete-orphan")
    processing_jobs = relationship("DocumentProcessingJob", back_populates="document", cascade="all, delete-orphan", order_by="desc(DocumentProcessingJob.created_at)")
    extracted_pages = relationship("ExtractedPage", back_populates="document", cascade="all, delete-orphan", order_by="ExtractedPage.page_number")
    extracted_sections = relationship("ExtractedSection", back_populates="document", cascade="all, delete-orphan", order_by="ExtractedSection.order_index")
    extracted_contents = relationship("ExtractedContent", back_populates="document", cascade="all, delete-orphan", order_by="ExtractedContent.order_index")
    semantic_chunks = relationship("SemanticChunk", back_populates="document", cascade="all, delete-orphan", order_by="SemanticChunk.chunk_index")


class DocumentMetadata(Base):
    __tablename__ = "document_metadata"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False, default="Untitled Research Document")
    authors: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    keywords: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    publication_date: Mapped[str | None] = mapped_column(String(100), nullable=True)
    doi: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    journal_or_conference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    total_pages: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    raw_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="doc_metadata")


class DocumentProcessingJob(Base):
    __tablename__ = "document_processing_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default=JobStatus.PENDING.value, nullable=False, index=True)
    stage: Mapped[str] = mapped_column(String(50), default=ProcessingStage.VALIDATION.value, nullable=False)
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    error_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="processing_jobs")


class ExtractedPage(Base):
    __tablename__ = "extracted_pages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    width: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    height: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    text_length: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    has_images: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_tables: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_doc_page_unique", "document_id", "page_number", unique=True),
    )

    # Relationships
    document = relationship("Document", back_populates="extracted_pages")
    contents = relationship("ExtractedContent", back_populates="page", cascade="all, delete-orphan")


class ExtractedSection(Base):
    __tablename__ = "extracted_sections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    section_title: Mapped[str] = mapped_column(String(255), nullable=False)
    section_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    parent_section_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    start_page: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    end_page: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="extracted_sections")
    contents = relationship("ExtractedContent", back_populates="section_rel")


class ExtractedContent(Base):
    __tablename__ = "extracted_contents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    page_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("extracted_pages.id", ondelete="SET NULL"), nullable=True, index=True)
    section_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("extracted_sections.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Milestone 5 Provenance fields
    chunk_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    content_type: Mapped[str] = mapped_column(String(50), default="paragraph", nullable=False)  # paragraph, table, figure_caption, math_expression, reference, header
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    section: Mapped[str] = mapped_column(String(255), default="Body", nullable=False)
    subsection: Mapped[str | None] = mapped_column(String(255), nullable=True)
    extraction_method: Mapped[str] = mapped_column(String(50), default="pymupdf_layout", nullable=False)
    bounding_box: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="extracted_contents")
    page = relationship("ExtractedPage", back_populates="contents")
    section_rel = relationship("ExtractedSection", back_populates="contents")
