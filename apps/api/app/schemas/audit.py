from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DocumentAuditLogOut(BaseModel):
    id: str
    document_id: str
    document_title: str = "Unknown Document"
    workspace_id: Optional[str] = None
    user_id: Optional[str] = None
    action: str
    ip_address: Optional[str] = None
    timestamp: str


class SecurityIncidentLogOut(BaseModel):
    id: str
    workspace_id: Optional[str] = None
    user_id: Optional[str] = None
    incident_type: str
    severity: str
    details: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    timestamp: str


class DocumentAuditListResponse(BaseModel):
    workspace_id: str
    total: int
    items: List[DocumentAuditLogOut]


class SecurityIncidentListResponse(BaseModel):
    workspace_id: str
    total: int
    items: List[SecurityIncidentLogOut]
