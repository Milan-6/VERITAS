from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LlmFeatureUsage(BaseModel):
    tokens: int = 0
    cost_usd: float = 0.0
    calls: int = 0


class LlmUsageSummary(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    total_llm_invocations: int = 0
    breakdown_by_feature: Dict[str, LlmFeatureUsage] = Field(default_factory=dict)


class WorkspaceUsageSummaryOut(BaseModel):
    workspace_id: str
    total_documents: int = 0
    total_api_requests: int = 0
    llm_usage: LlmUsageSummary


class ActivityRecord(BaseModel):
    id: str
    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    timestamp: str


class WorkspaceActivityOut(BaseModel):
    workspace_id: str
    total_requests: int = 0
    average_response_time_ms: float = 0.0
    error_rate_percentage: float = 0.0
    recent_activity: List[ActivityRecord] = Field(default_factory=list)
