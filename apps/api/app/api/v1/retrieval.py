import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, verify_document_access
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.retrieval import SearchRequest, SearchResponse, SearchChunkResult
from app.services.retrieval import retrieval_service
from app.services.audit import audit_service
from app.models.audit import DocumentAuditAction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/retrieval", tags=["Hybrid Retrieval"])


@router.post("/search", response_model=SearchResponse)
def hybrid_search(
    request: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Executes hybrid retrieval over scientific literature combining dense semantic vectors
    and sparse BM25 keyword matching with Reciprocal Rank Fusion (RRF).

    STRICT TENANT ISOLATION:
    Enforces that queries only access chunks indexed for the authenticated user's workspace/tenant.
    Cross-tenant retrieval is physically blocked by the vector store filter (SEC-01).
    """
    # Determine tenant_id from user's primary workspace or user_id
    user_ws = db.query(Workspace).filter(Workspace.owner_id == current_user.id).first()
    tenant_id = user_ws.id if user_ws else current_user.id

    # If document_id is provided, verify user has authorization to access it
    if request.document_id:
        verify_document_access(request.document_id, current_user, db, require_write=False)

    try:
        chunks = retrieval_service.search(
            query=request.query,
            tenant_id=tenant_id,
            document_id=request.document_id,
            top_k=request.top_k,
            dense_weight=request.dense_weight,
            sparse_weight=request.sparse_weight,
        )

        results = [
            SearchChunkResult(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                document_title=c.document_title,
                page_number=c.page_number,
                section_title=c.section_title,
                subsection=c.subsection,
                content_text=c.content_text,
                score=c.score,
                dense_score=c.dense_score,
                sparse_score=c.sparse_score,
            )
            for c in chunks
        ]

        # Phase 14: Document Audit Logging (COMP-01)
        if request.document_id:
            audit_service.log_document_access(
                document_id=request.document_id,
                action=DocumentAuditAction.RETRIEVAL.value,
                workspace_id=tenant_id,
                user_id=current_user.id,
            )

        return SearchResponse(
            query=request.query,
            tenant_id=tenant_id,
            total_results=len(results),
            results=results,
        )

    except Exception as e:
        logger.error(f"Hybrid retrieval failure for query '{request.query}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retrieval engine failure: {str(e)}",
        )
