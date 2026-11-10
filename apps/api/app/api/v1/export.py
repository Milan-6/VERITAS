import logging
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, verify_document_access
from app.models.user import User
from app.models.workspace import Workspace
from app.models.audit import DocumentAuditAction
from app.services.audit import audit_service
from app.services.dossier_export import dossier_export_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/export", tags=["Dossier Export & Integrations"])


@router.get("/dossier/{document_id}")
def export_research_dossier_pdf(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Assembles and exports a verified, publication-grade PDF research dossier
    for the requested document containing:
    - Executive metadata & abstract
    - 5-point grounded literature synthesis
    - Knowledge graph relational entity assertions
    - Chunk citations with verified provenance
    """
    doc = verify_document_access(document_id, current_user, db, require_write=False)

    # Resolve tenant
    user_ws = db.query(Workspace).filter(Workspace.owner_id == current_user.id).first()
    tenant_id = doc.workspace_id or (user_ws.id if user_ws else current_user.id)

    pdf_bytes = dossier_export_service.generate_dossier_pdf(
        document=doc,
        tenant_id=tenant_id,
        db=db,
    )

    clean_filename = f"VERITAS_Dossier_{doc.id[:8]}.pdf"

    # Phase 14: Document Access Audit Trail (COMP-01)
    audit_service.log_document_access(
        document_id=doc.id,
        action=DocumentAuditAction.EXPORT_PDF.value,
        workspace_id=tenant_id,
        user_id=current_user.id,
    )

    # Trigger Webhook Event: dossier.generated
    try:
        from app.services.webhook_dispatcher import webhook_dispatcher
        webhook_dispatcher.dispatch_event(
            event_name="dossier.generated",
            workspace_id=tenant_id,
            payload={
                "document_id": doc.id,
                "title": doc.doc_metadata.title if doc.doc_metadata else doc.filename,
                "filename": clean_filename,
                "pdf_size_bytes": len(pdf_bytes),
            },
            db=db,
        )
    except Exception as wh_err:
        logger.warning(f"Webhook dispatch non-fatal warning on dossier export: {wh_err}")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{clean_filename}"',
            "Content-Type": "application/pdf",
        },
    )
