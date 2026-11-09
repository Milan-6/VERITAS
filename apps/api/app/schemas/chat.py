from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, ConfigDict


class ChatSessionCreate(BaseModel):
    title: Optional[str] = "New Research Session"
    document_id: Optional[str] = None


class ChatMessageCreate(BaseModel):
    content: str


class CitationOut(BaseModel):
    document_id: str
    document_title: str
    page_number: int
    section_title: str
    chunk_id: str
    score: Optional[float] = None


class VerifiedClaim(BaseModel):
    claim_id: str
    claim_text: str
    status: str  # "SUPPORTED", "CONTRADICTED", "MISSING"
    document_id: Optional[str] = None
    document_title: Optional[str] = None
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    chunk_id: Optional[str] = None
    source_excerpt: Optional[str] = None
    reasoning: Optional[str] = None


class VerificationReport(BaseModel):
    overall_status: str  # "VERIFIED", "PARTIALLY_VERIFIED", "UNVERIFIED", "ABSTAINED"
    claims: List[VerifiedClaim] = []
    supported_count: int = 0
    contradicted_count: int = 0
    missing_count: int = 0
    verification_score: float = 0.0


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    role: str
    content: str
    citations: Optional[List[Dict[str, Any]]] = None
    verification_report: Optional[VerificationReport] = None
    created_at: datetime


class ChatSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    workspace_id: Optional[str] = None
    document_id: Optional[str] = None
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class ChatSessionDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    workspace_id: Optional[str] = None
    document_id: Optional[str] = None
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessageOut] = []
