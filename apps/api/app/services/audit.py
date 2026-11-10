import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.audit import (
    DocumentAuditLog,
    SecurityIncidentLog,
    DocumentAuditAction,
    SecurityIncidentType,
    SecurityIncidentSeverity,
)

logger = logging.getLogger(__name__)


class AuditService:
    """
    Append-only immutable audit logging service for document data access
    and security incident tracking (COMP-01, SEC-15).
    """

    def __init__(self, session_factory=None, max_workers: int = 4):
        self.session_factory = session_factory or SessionLocal
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="veritas_audit_")

    def _persist_document_audit(
        self,
        document_id: str,
        action: str,
        workspace_id: Optional[str],
        user_id: Optional[str],
        ip_address: Optional[str],
    ):
        db = self.session_factory()
        try:
            entry = DocumentAuditLog(
                document_id=document_id,
                action=action,
                workspace_id=workspace_id,
                user_id=user_id,
                ip_address=ip_address,
                timestamp=datetime.utcnow(),
            )
            db.add(entry)
            db.commit()
        except Exception as e:
            logger.warning(f"Failed to persist document audit log: {e}")
            db.rollback()
        finally:
            db.close()

    def log_document_access(
        self,
        document_id: str,
        action: str = DocumentAuditAction.VIEW.value,
        workspace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ):
        """Asynchronously writes a document access event to DocumentAuditLog."""
        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            self._persist_document_audit(document_id, action, workspace_id, user_id, ip_address)
        else:
            self.executor.submit(
                self._persist_document_audit,
                document_id,
                action,
                workspace_id,
                user_id,
                ip_address,
            )

    def _persist_security_incident(
        self,
        incident_type: str,
        severity: str,
        details: Optional[Dict[str, Any]],
        workspace_id: Optional[str],
        user_id: Optional[str],
        ip_address: Optional[str],
    ):
        db = self.session_factory()
        try:
            entry = SecurityIncidentLog(
                incident_type=incident_type,
                severity=severity,
                details=details,
                workspace_id=workspace_id,
                user_id=user_id,
                ip_address=ip_address,
                timestamp=datetime.utcnow(),
            )
            db.add(entry)
            db.commit()
        except Exception as e:
            logger.warning(f"Failed to persist security incident log: {e}")
            db.rollback()
        finally:
            db.close()

    def log_security_incident(
        self,
        incident_type: str,
        severity: str = SecurityIncidentSeverity.MEDIUM.value,
        details: Optional[Dict[str, Any]] = None,
        workspace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ):
        """Asynchronously records a security incident (e.g., prompt injection, SSRF, breach attempt)."""
        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            self._persist_security_incident(
                incident_type, severity, details, workspace_id, user_id, ip_address
            )
        else:
            self.executor.submit(
                self._persist_security_incident,
                incident_type,
                severity,
                details,
                workspace_id,
                user_id,
                ip_address,
            )

    def get_document_audit_logs(
        self,
        workspace_id: str,
        db: Session,
        limit: int = 50,
        offset: int = 0,
        document_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Queries append-only document audit trail filtered by workspace."""
        query = db.query(DocumentAuditLog).filter(DocumentAuditLog.workspace_id == workspace_id)
        if document_id:
            query = query.filter(DocumentAuditLog.document_id == document_id)

        records = query.order_by(DocumentAuditLog.timestamp.desc()).offset(offset).limit(limit).all()
        return [
            {
                "id": r.id,
                "document_id": r.document_id,
                "document_title": r.document.filename if r.document else "Unknown Document",
                "workspace_id": r.workspace_id,
                "user_id": r.user_id,
                "action": r.action,
                "ip_address": r.ip_address,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in records
        ]

    def get_security_incident_logs(
        self,
        workspace_id: str,
        db: Session,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Queries append-only security incident logs filtered by workspace."""
        records = (
            db.query(SecurityIncidentLog)
            .filter(SecurityIncidentLog.workspace_id == workspace_id)
            .order_by(SecurityIncidentLog.timestamp.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.id,
                "workspace_id": r.workspace_id,
                "user_id": r.user_id,
                "incident_type": r.incident_type,
                "severity": r.severity,
                "details": r.details or {},
                "ip_address": r.ip_address,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in records
        ]


audit_service = AuditService()
