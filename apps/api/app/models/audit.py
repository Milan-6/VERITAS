import uuid
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, Index, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DocumentAuditAction(str, Enum):
    VIEW = "VIEW"
    DOWNLOAD = "DOWNLOAD"
    EXPORT_PDF = "EXPORT_PDF"
    RETRIEVAL = "RETRIEVAL"


class SecurityIncidentType(str, Enum):
    PROMPT_INJECTION = "PROMPT_INJECTION"
    SSRF_ATTEMPT = "SSRF_ATTEMPT"
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    BRUTE_FORCE = "BRUTE_FORCE"


class SecurityIncidentSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DocumentAuditLog(Base):
    """
    Append-only immutable audit trail recording every access, view, download,
    or PDF export of a research document (COMP-01).
    """
    __tablename__ = "document_audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True)
    workspace_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # VIEW, DOWNLOAD, EXPORT_PDF, RETRIEVAL
    ip_address: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    document = relationship("Document", back_populates="audit_logs")
    workspace = relationship("Workspace", backref="document_audit_logs")
    user = relationship("User", backref="document_audit_logs")

    __table_args__ = (
        Index("ix_doc_audit_doc_timestamp", "document_id", "timestamp"),
        Index("ix_doc_audit_workspace_timestamp", "workspace_id", "timestamp"),
        Index("ix_doc_audit_action_timestamp", "action", "timestamp"),
    )


class SecurityIncidentLog(Base):
    """
    Append-only immutable security log tracking prompt injections, SSRF attempts,
    and access control violations (SEC-15).
    """
    __tablename__ = "security_incident_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    incident_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # PROMPT_INJECTION, SSRF_ATTEMPT, UNAUTHORIZED_ACCESS
    severity: Mapped[str] = mapped_column(String(20), default=SecurityIncidentSeverity.MEDIUM.value, nullable=False, index=True)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Detection rule, snippet, target endpoint
    ip_address: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    workspace = relationship("Workspace", backref="security_incident_logs")
    user = relationship("User", backref="security_incident_logs")

    __table_args__ = (
        Index("ix_sec_incident_workspace_timestamp", "workspace_id", "timestamp"),
        Index("ix_sec_incident_type_severity", "incident_type", "severity"),
    )
