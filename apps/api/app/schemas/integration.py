from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ZoteroConnectRequest(BaseModel):
    api_key: str = Field(..., min_length=8, description="Zotero API key")
    user_id: str = Field(..., min_length=1, description="Zotero user or library ID")
    workspace_id: Optional[str] = Field(None, description="Target workspace ID")


class ZoteroSyncRequest(BaseModel):
    workspace_id: str = Field(..., description="Target workspace ID for imported items")
    limit: Optional[int] = Field(50, ge=1, le=100, description="Max items to fetch from library")


class IntegrationStatusOut(BaseModel):
    id: str
    provider: str
    external_user_id: Optional[str] = None
    is_active: bool
    workspace_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WebhookCreate(BaseModel):
    workspace_id: str = Field(..., description="Workspace ID associated with this webhook")
    url: str = Field(..., description="HTTPS destination URL for webhook delivery")
    events_subscribed: List[str] = Field(
        default=["document.ingested", "agent.task.completed", "dossier.generated"],
        description="List of events: document.ingested, agent.task.completed, dossier.generated, or *",
    )
    description: Optional[str] = Field(None, max_length=255, description="Optional label for this webhook")


class WebhookOut(BaseModel):
    id: str
    workspace_id: str
    url: str
    events_subscribed: List[str]
    secret_key: str
    is_active: bool
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
