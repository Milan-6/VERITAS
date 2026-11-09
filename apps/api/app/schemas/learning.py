from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class FlashcardOut(BaseModel):
    id: str
    deck_id: str
    front_concept: str
    back_definition: str
    source_citation: Optional[str] = None
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    source_excerpt: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FlashcardDeckOut(BaseModel):
    id: str
    tenant_id: str
    document_id: str
    title: str
    card_count: int
    created_at: datetime
    updated_at: datetime
    cards: List[FlashcardOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class QuizQuestion(BaseModel):
    question_id: str
    question_text: str
    options: List[str]
    correct_answer: str
    explanation: str
    source_citation: Optional[str] = None
    page_number: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class QuizOut(BaseModel):
    id: str
    tenant_id: str
    document_id: str
    title: str
    total_questions: int
    created_at: datetime
    updated_at: datetime
    questions: List[QuizQuestion] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class QuizSubmitRequest(BaseModel):
    answers: Dict[str, str] = Field(
        ...,
        description="Map of question_id to the user's selected answer string.",
    )


class QuizQuestionResult(BaseModel):
    question_id: str
    question_text: str
    user_answer: Optional[str] = None
    correct_answer: str
    is_correct: bool
    explanation: str
    source_citation: Optional[str] = None
    page_number: Optional[int] = None


class QuizEvaluationResult(BaseModel):
    quiz_id: str
    document_id: str
    score: int
    total_questions: int
    percentage: float
    results: List[QuizQuestionResult]
