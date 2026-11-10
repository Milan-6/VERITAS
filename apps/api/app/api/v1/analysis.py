import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, verify_document_access
from app.models.user import User
from app.models.workspace import Workspace
from app.models.document import Document
from app.schemas.analysis import PaperSynthesis, LiteratureMatrix, MatrixRequest
from app.services.academic_extraction import academic_extraction_service
from app.services.literature_matrix import literature_matrix_service
from app.services.prompt_security import prompt_security_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["Scientific Intelligence & Literature Analysis"])


@router.get("/summary/{document_id}", response_model=PaperSynthesis)
def get_paper_synthesis(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Extracts a 5-point structured academic synthesis for a single research document:
    Problem Statement, Methodology, Datasets Used, Key Results, and Limitations.
    All points retain exact page and source text provenance.
    """
    doc = verify_document_access(document_id, current_user, db, require_write=False)

    # Resolve tenant
    user_ws = db.query(Workspace).filter(Workspace.owner_id == current_user.id).first()
    tenant_id = doc.workspace_id or (user_ws.id if user_ws else current_user.id)

    title = (doc.doc_metadata.title if doc.doc_metadata and doc.doc_metadata.title else doc.filename)

    synthesis = academic_extraction_service.synthesize_paper(
        document_id=doc.id,
        tenant_id=tenant_id,
        document_title=title,
    )

    return synthesis


@router.post("/matrix", response_model=LiteratureMatrix)
def generate_literature_matrix(
    payload: MatrixRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Constructs a cross-paper comparative literature matrix across 2 to 5 research papers.
    Detects empirical contradictions, benchmark discrepancies, and methodological divergences.
    Strictly verifies all papers belong to the authenticated user's tenant.
    """
    user_ws = db.query(Workspace).filter(Workspace.owner_id == current_user.id).first()
    tenant_id = user_ws.id if user_ws else current_user.id

    # Phase 14: Prompt Injection & Jailbreak Defense (SEC-16)
    if payload.topic_query:
        prompt_security_service.validate_prompt_or_raise(
            text=payload.topic_query,
            workspace_id=tenant_id,
            user_id=current_user.id,
            endpoint_context="analysis_matrix",
        )

    matrix = literature_matrix_service.generate_matrix(
        document_ids=payload.document_ids,
        current_user=current_user,
        tenant_id=tenant_id,
        db=db,
        topic_query=payload.topic_query,
    )

    return matrix
