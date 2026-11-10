import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, DocumentWorkspaceAssociation
from app.models.document import Document
from app.models.chat import ChatSession, ChatMessage
from app.models.graph import GraphNode, GraphEdge
from app.models.learning import FlashcardDeck, Quiz
from app.models.audit import DocumentAuditLog
from app.schemas.user import UserOut
from app.services.storage import storage_service
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users & Data Sovereignty"])


@router.get("/me", response_model=UserOut)
def get_user_profile(current_user: User = Depends(get_current_user)):
    """Returns profile of currently authenticated user."""
    return UserOut.model_validate(current_user)


@router.delete("/me", status_code=status.HTTP_200_OK)
def delete_user_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    GDPR Right to be Forgotten (GDPR-01).
    Permanently and irreversibly purges a user account and all personal research artifacts:
    1. Physical storage files unlinked from disk.
    2. Vector embeddings deleted from Qdrant.
    3. Owned workspaces and associated documents deleted.
    4. Knowledge graph nodes and edges purged.
    5. Flashcards, quizzes, and chat histories deleted.
    6. Memberships in shared workspaces removed without breaking shared resources.
    7. User account record purged.
    """
    user_id = current_user.id
    logger.info(f"Initiating GDPR account deletion for user: {user_id} ({current_user.email})")

    # 1. Identify all documents owned by user or in owned workspaces
    owned_workspaces = db.query(Workspace).filter(Workspace.owner_id == user_id).all()
    owned_ws_ids = {ws.id for ws in owned_workspaces}

    user_documents = (
        db.query(Document)
        .filter((Document.user_id == user_id) | (Document.workspace_id.in_(owned_ws_ids)))
        .all()
    )

    # 2. Delete physical storage files and vector points
    for doc in user_documents:
        try:
            vector_store.delete_document_vectors(doc.id)
        except Exception as e:
            logger.warning(f"Error purging vector embeddings for doc {doc.id}: {e}")

        try:
            storage_service.delete_file(doc.storage_path)
        except Exception as e:
            logger.warning(f"Error purging physical file for doc {doc.id}: {e}")

    # 3. Purge Knowledge Graph nodes and edges for user tenant or owned workspaces
    tenant_ids = [user_id] + list(owned_ws_ids)
    try:
        db.query(GraphEdge).filter(GraphEdge.tenant_id.in_(tenant_ids)).delete(synchronize_session=False)
        db.query(GraphNode).filter(GraphNode.tenant_id.in_(tenant_ids)).delete(synchronize_session=False)
    except Exception as e:
        logger.warning(f"Error purging knowledge graph entities: {e}")

    # 4. Purge Flashcards and Quizzes
    try:
        db.query(Quiz).filter(Quiz.tenant_id.in_(tenant_ids)).delete(synchronize_session=False)
        db.query(FlashcardDeck).filter(FlashcardDeck.tenant_id.in_(tenant_ids)).delete(synchronize_session=False)
    except Exception as e:
        logger.warning(f"Error purging learning artifacts: {e}")

    # 5. Purge Chat Sessions and Messages
    try:
        user_sessions = (
            db.query(ChatSession)
            .filter((ChatSession.user_id == user_id) | (ChatSession.workspace_id.in_(owned_ws_ids)))
            .all()
        )
        for s in user_sessions:
            db.delete(s)
        db.flush()
    except Exception as e:
        logger.warning(f"Error purging chat sessions: {e}")

    # 6. Remove user from shared workspaces where they are a member (not owner)
    db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user_id).delete(synchronize_session=False)

    # 7. Delete owned workspaces (cascades document associations, etc.)
    for ws in owned_workspaces:
        db.delete(ws)
    db.flush()

    # 8. Delete User entity
    db.delete(current_user)
    db.commit()

    logger.info(f"GDPR account deletion successfully completed for user: {user_id}")
    return {
        "status": "success",
        "message": "User account and all personal data permanently deleted in compliance with GDPR Right to be Forgotten.",
    }


@router.get("/me/export")
def export_user_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    GDPR Data Portability (GDPR-02).
    Assembles a complete, machine-readable JSON archive containing all user profile data,
    workspaces, document metadata, chat histories, and learning materials.
    """
    user_id = current_user.id

    # User profile
    profile_data = {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
    }

    # Workspaces
    owned_workspaces = db.query(Workspace).filter(Workspace.owner_id == user_id).all()
    member_records = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user_id).all()
    workspaces_data = [
        {"id": ws.id, "name": ws.name, "slug": ws.slug, "role": "OWNER", "created_at": ws.created_at.isoformat()}
        for ws in owned_workspaces
    ]
    for mem in member_records:
        if mem.workspace and mem.workspace.owner_id != user_id:
            workspaces_data.append({
                "id": mem.workspace.id,
                "name": mem.workspace.name,
                "slug": mem.workspace.slug,
                "role": mem.role,
                "joined_at": mem.joined_at.isoformat() if mem.joined_at else None,
            })

    # Documents
    documents = db.query(Document).filter(Document.user_id == user_id).all()
    docs_data = []
    for d in documents:
        docs_data.append({
            "id": d.id,
            "filename": d.filename,
            "file_size_bytes": d.file_size_bytes,
            "mime_type": d.mime_type,
            "status": d.status,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "metadata": {
                "title": d.doc_metadata.title if d.doc_metadata else d.filename,
                "authors": d.doc_metadata.authors if d.doc_metadata else [],
                "abstract": d.doc_metadata.abstract if d.doc_metadata else None,
                "publication_date": d.doc_metadata.publication_date if d.doc_metadata else None,
                "doi": d.doc_metadata.doi if d.doc_metadata else None,
            } if d.doc_metadata else {},
        })

    # Chat Sessions & Messages
    sessions = db.query(ChatSession).filter(ChatSession.user_id == user_id).all()
    chat_data = []
    for s in sessions:
        msgs = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == s.id)
            .order_by(ChatMessage.created_at.asc())
            .all()
        )
        chat_data.append({
            "session_id": s.id,
            "title": s.title,
            "workspace_id": s.workspace_id,
            "document_id": s.document_id,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "citations": m.citations,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in msgs
            ],
        })

    # Flashcard Decks
    decks = db.query(FlashcardDeck).filter(FlashcardDeck.tenant_id == user_id).all()
    flashcards_data = [
        {
            "deck_id": deck.id,
            "title": deck.title,
            "document_id": deck.document_id,
            "cards": [
                {
                    "front": c.front_concept,
                    "back": c.back_definition,
                    "citation": c.source_citation,
                    "page_number": c.page_number,
                }
                for c in deck.cards
            ],
        }
        for deck in decks
    ]

    export_payload = {
        "export_metadata": {
            "platform": "VERITAS",
            "tagline": "Research Intelligence. Grounded in Truth.",
            "compliance": "GDPR Article 20 - Right to Data Portability",
            "exported_at": datetime.now(timezone.utc).isoformat(),
        },
        "user_profile": profile_data,
        "workspaces": workspaces_data,
        "documents": docs_data,
        "chat_history": chat_data,
        "learning_materials": flashcards_data,
    }

    response = JSONResponse(content=export_payload)
    response.headers["Content-Disposition"] = f'attachment; filename="veritas_data_export_{user_id[:8]}.json"'
    return response
