from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class WorkspaceMemberOut(BaseModel):
    id: str
    workspace_id: str
    user_id: str
    email: str
    full_name: Optional[str] = None
    role: str
    joined_at: datetime

    class Config:
        from_attributes = True


class WorkspaceMemberInvite(BaseModel):
    email: str = Field(..., description="Email address of the collaborator to invite")
    role: str = Field(default="VIEWER", description="Role to assign: EDITOR or VIEWER")


class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Name of the workspace")


class WorkspaceOut(BaseModel):
    id: str
    name: str
    slug: str
    owner_id: str
    role: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkspaceDetailOut(WorkspaceOut):
    members: List[WorkspaceMemberOut] = []
    document_count: int = 0
