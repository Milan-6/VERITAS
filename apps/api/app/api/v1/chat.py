import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user, verify_document_access
from app.models.user import User
from app.models.workspace import Workspace
from app.models.chat import ChatSession, ChatMessage
from app.schemas.chat import (
    ChatSessionCreate,
    ChatSessionOut,
    ChatSessionDetailOut,
    ChatMessageCreate,
    ChatMessageOut,
)
from app.services.retrieval import retrieval_service
from app.services.llm import llm_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Grounded AI Chat Assistant"])


def verify_session_access(session_id: str, current_user: User, db: Session) -> ChatSession:
    """Enforces strict tenant isolation for chat sessions (SEC-01)."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found",
        )

    # Check ownership or workspace tenancy
    if session.user_id != current_user.id:
        user_ws = db.query(Workspace).filter(Workspace.owner_id == current_user.id).first()
        user_ws_id = user_ws.id if user_ws else None

        if not session.workspace_id or session.workspace_id != user_ws_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cross-tenant chat session access prevented.",
            )

    return session


@router.post("/sessions", response_model=ChatSessionOut, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: ChatSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Creates a new grounded research chat session."""
    user_ws = db.query(Workspace).filter(Workspace.owner_id == current_user.id).first()
    workspace_id = user_ws.id if user_ws else None

    # If document_id provided, verify user has access
    if payload.document_id:
        verify_document_access(payload.document_id, current_user, db, require_write=False)

    title = payload.title.strip() if payload.title else "New Research Session"

    session = ChatSession(
        user_id=current_user.id,
        workspace_id=workspace_id,
        document_id=payload.document_id,
        title=title,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return ChatSessionOut(
        id=session.id,
        user_id=session.user_id,
        workspace_id=session.workspace_id,
        document_id=session.document_id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=0,
    )


@router.get("/sessions", response_model=List[ChatSessionOut])
def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists all chat sessions for the authenticated user/tenant."""
    user_ws = db.query(Workspace).filter(Workspace.owner_id == current_user.id).first()
    workspace_id = user_ws.id if user_ws else None

    query = db.query(ChatSession).filter(
        (ChatSession.user_id == current_user.id) |
        (ChatSession.workspace_id == workspace_id) if workspace_id else (ChatSession.user_id == current_user.id)
    ).order_by(ChatSession.updated_at.desc())

    sessions = query.all()
    out = []
    for s in sessions:
        count = db.query(ChatMessage).filter(ChatMessage.session_id == s.id).count()
        out.append(
            ChatSessionOut(
                id=s.id,
                user_id=s.user_id,
                workspace_id=s.workspace_id,
                document_id=s.document_id,
                title=s.title,
                created_at=s.created_at,
                updated_at=s.updated_at,
                message_count=count,
            )
        )
    return out


@router.get("/sessions/{session_id}", response_model=ChatSessionDetailOut)
def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves session details and full message history."""
    session = verify_session_access(session_id, current_user, db)
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )

    return ChatSessionDetailOut(
        id=session.id,
        user_id=session.user_id,
        workspace_id=session.workspace_id,
        document_id=session.document_id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=[ChatMessageOut.model_validate(m) for m in messages],
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deletes a chat session and associated messages."""
    session = verify_session_access(session_id, current_user, db)
    db.delete(session)
    db.commit()
    return None


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageOut, status_code=status.HTTP_201_CREATED)
@router.post("/{session_id}/message", response_model=ChatMessageOut, status_code=status.HTTP_201_CREATED)
def send_chat_message(
    session_id: str,
    payload: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Submits a user query, executes hybrid retrieval over tenant documents,
    assembles grounded context, queries LLM with temperature=0.0,
    and returns assistant reply with inline citations.
    """
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message content cannot be empty.")

    session = verify_session_access(session_id, current_user, db)

    # 1. Persist User Message
    user_msg = ChatMessage(
        session_id=session.id,
        role="user",
        content=content,
    )
    db.add(user_msg)
    db.flush()

    # 2. Retrieve Conversation History (last 8 turns)
    recent_msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    # Exclude the newly added user message from previous history
    history = [{"role": m.role, "content": m.content} for m in recent_msgs[:-1]]

    # 3. Execute Hybrid Retrieval with Strict Tenant Isolation (SEC-01)
    user_ws = db.query(Workspace).filter(Workspace.owner_id == current_user.id).first()
    tenant_id = session.workspace_id or (user_ws.id if user_ws else current_user.id)

    retrieved_chunks = retrieval_service.search(
        query=content,
        tenant_id=tenant_id,
        document_id=session.document_id,
        top_k=5,
    )

    # 4. Generate Grounded Response via LLM Orchestration
    assistant_reply = llm_service.generate_response(
        query=content,
        context_chunks=retrieved_chunks,
        chat_history=history,
    )

    # 5. Format Citations Metadata
    is_abstention = assistant_reply == settings.STRICT_ABSTENTION_MESSAGE
    citations_data = []
    if not is_abstention and retrieved_chunks:
        citations_data = [
            {
                "document_id": c.document_id,
                "document_title": c.document_title,
                "page_number": c.page_number,
                "section_title": c.section_title,
                "chunk_id": c.chunk_id,
                "score": round(c.score, 4),
            }
            for c in retrieved_chunks
        ]

    # 6. Persist Assistant Message
    assistant_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=assistant_reply,
        citations=citations_data,
    )
    db.add(assistant_msg)

    # Auto-generate session title if default
    if session.title == "New Research Session" and len(recent_msgs) <= 1:
        # Create concise title from user query
        words = content.split()[:6]
        session.title = " ".join(words) + ("..." if len(content.split()) > 6 else "")

    session.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(assistant_msg)

    return ChatMessageOut.model_validate(assistant_msg)
