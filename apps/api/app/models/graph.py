import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, UniqueConstraint, Index
from sqlalchemy.orm import relationship

from app.core.database import Base


class GraphNode(Base):
    __tablename__ = "graph_nodes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    type = Column(String(32), nullable=False, index=True)  # Paper, Author, Dataset, Algorithm, Metric, Concept
    label = Column(String(255), nullable=False, index=True)  # Name of entity (e.g., "ImageNet", "Transformer")
    description = Column(Text, nullable=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "type", "label", name="uq_graph_nodes_tenant_type_label"),
        Index("ix_graph_nodes_tenant_label", "tenant_id", "label"),
    )


class GraphEdge(Base):
    __tablename__ = "graph_edges"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    source_node_id = Column(String(36), ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    target_node_id = Column(String(36), ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type = Column(String(64), nullable=False, index=True)  # INTRODUCES, EVALUATES, USES, CITED_BY, BENCHMARKS_ON
    provenance_chunk_id = Column(String(36), ForeignKey("semantic_chunks.id", ondelete="SET NULL"), nullable=True, index=True)
    source_excerpt = Column(Text, nullable=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    source_node = relationship("GraphNode", foreign_keys=[source_node_id], backref="outbound_edges")
    target_node = relationship("GraphNode", foreign_keys=[target_node_id], backref="inbound_edges")

    __table_args__ = (
        UniqueConstraint("tenant_id", "source_node_id", "target_node_id", "relationship_type", name="uq_graph_edges_tenant_source_target_rel"),
        Index("ix_graph_edges_tenant_rel", "tenant_id", "relationship_type"),
    )
