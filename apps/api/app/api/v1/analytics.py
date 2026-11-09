import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.schemas.analytics import WorkspaceUsageSummaryOut, WorkspaceActivityOut
from app.services.telemetry import telemetry_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Platform Analytics & Telemetry"])


def verify_workspace_owner(workspace_id: str, user: User, db: Session) -> Workspace:
    """
    Enforces RBAC: Only OWNER role can view workspace analytics & telemetry.
    Returns 404 if workspace doesn't exist.
    Returns 403 if user is not OWNER.
    """
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Check direct ownership
    if workspace.owner_id == user.id:
        return workspace

    # Check member record
    member = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace.id,
            WorkspaceMember.user_id == user.id,
        )
        .first()
    )

    if not member or member.role.upper() != WorkspaceRole.OWNER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only workspace owners can view analytics and usage metrics.",
        )

    return workspace


@router.get(
    "/workspace/{workspace_id}/usage",
    response_model=WorkspaceUsageSummaryOut,
    summary="Get aggregated LLM token usage and cost metrics for a workspace",
)
def get_workspace_usage(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves aggregated LLM token usage, estimated USD costs, document counts,
    and total API requests for the target workspace. Restricted to OWNER role.
    """
    verify_workspace_owner(workspace_id, current_user, db)
    return telemetry_service.get_workspace_usage_summary(workspace_id, db)


@router.get(
    "/workspace/{workspace_id}/activity",
    response_model=WorkspaceActivityOut,
    summary="Get API request logs and response time performance metrics for a workspace",
)
def get_workspace_activity(
    workspace_id: str,
    limit: int = Query(50, ge=1, le=200, description="Max recent activity records"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves recent API requests, average response latency, and error rate
    for the target workspace. Restricted to OWNER role.
    """
    verify_workspace_owner(workspace_id, current_user, db)
    return telemetry_service.get_workspace_activity(workspace_id, db, limit=limit)
