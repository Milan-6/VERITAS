from datetime import datetime
import logging
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.learning import (
    FlashcardDeckOut,
    QuizOut,
    QuizSubmitRequest,
    QuizEvaluationResult,
)
from app.services.learning import learning_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/learning", tags=["Learning & Research Productivity"])


def get_tenant_id(current_user: User, db: Session) -> str:
    user_ws = db.query(Workspace).filter(Workspace.owner_id == current_user.id).first()
    return user_ws.id if user_ws else current_user.id


@router.post("/flashcards/generate/{document_id}", response_model=FlashcardDeckOut, status_code=status.HTTP_201_CREATED)
def generate_flashcards(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generates 10-15 conceptual flashcards with exact page provenance for a paper."""
    tenant_id = get_tenant_id(current_user, db)
    deck = learning_service.generate_flashcards(document_id, tenant_id, db)
    out = FlashcardDeckOut.model_validate(deck)
    out.flashcards = out.cards
    out.status = "generated"
    return out


@router.get("/flashcards/{document_id}", response_model=FlashcardDeckOut)
def get_flashcards(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves existing flashcard deck for a document, returning empty not_generated if not present."""
    tenant_id = get_tenant_id(current_user, db)
    deck = learning_service.get_flashcard_deck(document_id, tenant_id, db)
    if not deck:
        return FlashcardDeckOut(
            id=f"empty_{document_id}",
            tenant_id=tenant_id,
            document_id=document_id,
            title="Flashcard Deck Not Generated",
            card_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            cards=[],
            flashcards=[],
            status="not_generated",
        )
    out = FlashcardDeckOut.model_validate(deck)
    out.flashcards = out.cards
    out.status = "generated"
    return out


@router.get("/flashcards/{document_id}/export")
def export_flashcards_anki(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Exports flashcard deck as an Anki-compatible CSV file."""
    tenant_id = get_tenant_id(current_user, db)
    csv_content = learning_service.export_deck_to_anki_csv(document_id, tenant_id, db)

    filename = f"anki_deck_{document_id[:8]}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )


@router.post("/quiz/generate/{document_id}", response_model=QuizOut, status_code=status.HTTP_201_CREATED)
def generate_quiz(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generates a 5-question diagnostic MCQ quiz with answer keys and citations."""
    tenant_id = get_tenant_id(current_user, db)
    quiz = learning_service.generate_quiz(document_id, tenant_id, db)
    out = QuizOut.model_validate(quiz)
    out.status = "generated"
    return out


@router.get("/quiz/{document_id}", response_model=QuizOut)
def get_quiz(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves existing diagnostic quiz for a document, returning empty not_generated if not present."""
    tenant_id = get_tenant_id(current_user, db)
    quiz = learning_service.get_quiz(document_id, tenant_id, db)
    if not quiz:
        return QuizOut(
            id=f"empty_{document_id}",
            tenant_id=tenant_id,
            document_id=document_id,
            title="Diagnostic Quiz Not Generated",
            total_questions=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            questions=[],
            status="not_generated",
        )
    out = QuizOut.model_validate(quiz)
    out.status = "generated"
    return out


@router.post("/quiz/{quiz_id}/evaluate", response_model=QuizEvaluationResult)
def evaluate_quiz(
    quiz_id: str,
    payload: QuizSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submits answers for a diagnostic quiz and calculates score with full citations."""
    tenant_id = get_tenant_id(current_user, db)
    result = learning_service.evaluate_quiz(quiz_id, tenant_id, payload.answers, db)
    return result
