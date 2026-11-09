from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


class SynthesisPoint(BaseModel):
    topic: str
    summary: str
    source_excerpt: Optional[str] = None
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    confidence_score: float = 1.0


class PaperSynthesis(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: str
    document_title: str
    problem_statement: SynthesisPoint
    methodology: SynthesisPoint
    dataset_used: SynthesisPoint
    key_results: SynthesisPoint
    limitations: SynthesisPoint
    created_at: datetime = datetime.utcnow()


class MatrixColumn(BaseModel):
    document_id: str
    document_title: str
    problem_statement: str
    methodology: str
    dataset_used: str
    key_results: str
    limitations: str


class MatrixContradiction(BaseModel):
    aspect: str  # e.g. "Dataset Results", "Methodological Divergence"
    paper_a_id: str
    paper_a_title: str
    paper_b_id: str
    paper_b_title: str
    description: str
    divergence_level: str  # "HIGH", "MEDIUM", "LOW"


class LiteratureMatrix(BaseModel):
    topic_query: Optional[str] = None
    document_count: int
    columns: List[MatrixColumn]
    contradictions_and_divergences: List[MatrixContradiction] = []
    generated_at: datetime = datetime.utcnow()


class MatrixRequest(BaseModel):
    document_ids: List[str]
    topic_query: Optional[str] = None
