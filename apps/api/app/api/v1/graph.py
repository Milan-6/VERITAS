import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, verify_document_access
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.graph import WorkspaceGraphResponse
from app.services.knowledge_graph import knowledge_graph_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graph", tags=["Research Knowledge Graph"])


@router.get("/workspace", response_model=WorkspaceGraphResponse)
def get_workspace_knowledge_graph(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Fetches all scientific nodes (Entities) and edges (Relationships) for the
    authenticated user's active workspace.
    Enforces strict tenant isolation.
    """
    user_ws = db.query(Workspace).filter(Workspace.owner_id == current_user.id).first()
    tenant_id = user_ws.id if user_ws else current_user.id

    return knowledge_graph_service.get_workspace_graph(tenant_id=tenant_id, db=db)


@router.post("/extract/{document_id}")
def extract_document_entities(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Triggers entity and relation extraction for a specific document,
    updating the workspace knowledge graph with nodes, edges, and provenance links.
    """
    doc = verify_document_access(document_id, current_user, db, require_write=True)

    user_ws = db.query(Workspace).filter(Workspace.owner_id == current_user.id).first()
    tenant_id = doc.workspace_id or (user_ws.id if user_ws else current_user.id)

    nodes_count, edges_count = knowledge_graph_service.extract_entities_for_document(
        document_id=doc.id,
        tenant_id=tenant_id,
        db=db,
    )

    return {
        "status": "success",
        "document_id": doc.id,
        "nodes_extracted": nodes_count,
        "edges_extracted": edges_count,
    }
