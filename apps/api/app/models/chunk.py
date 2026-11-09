import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class SemanticChunk(Base):
    __tablename__ = "semantic_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Milestone 2 Provenance & Structure fields
    chunk_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    section_title: Mapped[str] = mapped_column(String(255), default="General", nullable=False)
    subsection: Mapped[str | None] = mapped_column(String(255), nullable=True)
    context_header: Mapped[str] = mapped_column(String(500), nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedded_text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Vector indexing status
    qdrant_point_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    is_indexed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="semantic_chunks")
    user = relationship("User", backref="semantic_chunks")
    workspace = relationship("Workspace", backref="semantic_chunks")
