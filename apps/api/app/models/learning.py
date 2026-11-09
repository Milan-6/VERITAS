import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, JSON, Index
from sqlalchemy.orm import relationship

from app.core.database import Base


class FlashcardDeck(Base):
    __tablename__ = "flashcard_decks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True, index=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    card_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    cards = relationship("Flashcard", back_populates="deck", cascade="all, delete-orphan", order_by="Flashcard.created_at.asc()")
    document = relationship("Document", backref="flashcard_decks")
    workspace = relationship("Workspace", backref="flashcard_decks")

    __table_args__ = (
        Index("ix_flashcard_decks_tenant_doc", "tenant_id", "document_id"),
    )


class Flashcard(Base):
    __tablename__ = "flashcards"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    deck_id = Column(String(36), ForeignKey("flashcard_decks.id", ondelete="CASCADE"), nullable=False, index=True)
    front_concept = Column(Text, nullable=False)
    back_definition = Column(Text, nullable=False)
    source_citation = Column(String(255), nullable=True)  # e.g., "[Document: Sparse Attention, Page: 4]"
    page_number = Column(Integer, nullable=True)
    section_title = Column(String(255), nullable=True)
    source_excerpt = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    deck = relationship("FlashcardDeck", back_populates="cards")


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    questions = Column(JSON, nullable=False, default=list)  # List of MCQ objects
    total_questions = Column(Integer, default=5, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    document = relationship("Document", backref="quizzes")

    __table_args__ = (
        Index("ix_quizzes_tenant_doc", "tenant_id", "document_id"),
    )
