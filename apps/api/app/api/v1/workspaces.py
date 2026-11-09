import re
import uuid
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.models.document import Document
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceOut,
    WorkspaceDetailOut,
    WorkspaceMemberInvite,
    WorkspaceMemberOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces", tags=["Workspaces & Collaboration"])


def _slugify(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-").lower()
    return f"{cleaned or 'workspace'}-{str(uuid.uuid4())[:8]}"


def _get_user_workspace_role(workspace: Workspace, user: User, db: Session) -> str | None:
    if workspace.owner_id == user.id:
        return WorkspaceRole.OWNER.value
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace.id,
        WorkspaceMember.user_id == user.id,
    ).first()
    return member.role.upper() if member else None


@router.post("", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
def create_workspace(
    payload: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Creates a new workspace, designating current user as OWNER."""
    slug = _slugify(payload.name)
    workspace = Workspace(
        name=payload.name.strip(),
        slug=slug,
        owner_id=current_user.id,
    )
    db.add(workspace)
    db.flush()

    # Automatically add owner as a member with OWNER role
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=current_user.id,
        role=WorkspaceRole.OWNER.value,
    )
    db.add(member)
    db.commit()
    db.refresh(workspace)

    return WorkspaceOut(
        id=workspace.id,
        name=workspace.name,
        slug=workspace.slug,
        owner_id=workspace.owner_id,
        role=WorkspaceRole.OWNER.value,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
    )


@router.get("", response_model=List[WorkspaceOut])
def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists all workspaces where current user is owner or member."""
    # Owned workspaces
    owned = db.query(Workspace).filter(Workspace.owner_id == current_user.id).all()
    # Member workspaces
    member_records = db.query(WorkspaceMember).filter(
        WorkspaceMember.user_id == current_user.id,
    ).all()
    member_ws_ids = {m.workspace_id: m.role for m in member_records}
    other_workspaces = db.query(Workspace).filter(
        Workspace.id.in_(member_ws_ids.keys()),
        Workspace.owner_id != current_user.id,
    ).all()

    results: List[WorkspaceOut] = []
    seen = set()

    for ws in owned:
        seen.add(ws.id)
        results.append(
            WorkspaceOut(
                id=ws.id,
                name=ws.name,
                slug=ws.slug,
                owner_id=ws.owner_id,
                role=WorkspaceRole.OWNER.value,
                created_at=ws.created_at,
                updated_at=ws.updated_at,
            )
        )

    for ws in other_workspaces:
        if ws.id not in seen:
            seen.add(ws.id)
            results.append(
                WorkspaceOut(
                    id=ws.id,
                    name=ws.name,
                    slug=ws.slug,
                    owner_id=ws.owner_id,
                    role=member_ws_ids.get(ws.id, WorkspaceRole.VIEWER.value),
                    created_at=ws.created_at,
                    updated_at=ws.updated_at,
                )
            )

    return results


@router.get("/{workspace_id}", response_model=WorkspaceDetailOut)
def get_workspace_detail(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves detailed workspace information, member list, and document metrics."""
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    user_role = _get_user_workspace_role(ws, current_user, db)
    if not user_role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found or unauthorized")

    members = db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == ws.id).all()
    
    member_outs: List[WorkspaceMemberOut] = []
    for m in members:
        user = db.query(User).filter(User.id == m.user_id).first()
        if user:
            member_outs.append(
                WorkspaceMemberOut(
                    id=m.id,
                    workspace_id=m.workspace_id,
                    user_id=m.user_id,
                    email=user.email,
                    full_name=user.full_name,
                    role=m.role,
                    joined_at=m.joined_at,
                )
            )

    # If owner is not in members table, add owner explicitly
    if not any(m.user_id == ws.owner_id for m in members):
        owner_user = db.query(User).filter(User.id == ws.owner_id).first()
        if owner_user:
            member_outs.insert(
                0,
                WorkspaceMemberOut(
                    id=f"owner-{ws.id}",
                    workspace_id=ws.id,
                    user_id=owner_user.id,
                    email=owner_user.email,
                    full_name=owner_user.full_name,
                    role=WorkspaceRole.OWNER.value,
                    joined_at=ws.created_at,
                ),
            )

    doc_count = db.query(Document).filter(Document.workspace_id == ws.id).count()

    return WorkspaceDetailOut(
        id=ws.id,
        name=ws.name,
        slug=ws.slug,
        owner_id=ws.owner_id,
        role=user_role,
        created_at=ws.created_at,
        updated_at=ws.updated_at,
        members=member_outs,
        document_count=doc_count,
    )


@router.post("/{workspace_id}/members", response_model=WorkspaceMemberOut, status_code=status.HTTP_201_CREATED)
def invite_workspace_member(
    workspace_id: str,
    payload: WorkspaceMemberInvite,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Invites a collaborator to the workspace with role EDITOR or VIEWER.
    Enforces RBAC: VIEWER cannot invite members (403 Forbidden).
    """
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    user_role = _get_user_workspace_role(ws, current_user, db)
    if not user_role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found or unauthorized")

    # RBAC check: only OWNER or EDITOR can invite members
    if user_role not in [WorkspaceRole.OWNER.value, WorkspaceRole.EDITOR.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Viewers are not permitted to invite or manage members",
        )

    target_email = payload.email.strip().lower()
    target_user = db.query(User).filter(User.email == target_email).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email '{target_email}' does not exist in VERITAS",
        )

    if target_user.id == ws.owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add the workspace owner as a standard member",
        )

    assigned_role = payload.role.strip().upper()
    if assigned_role not in [WorkspaceRole.EDITOR.value, WorkspaceRole.VIEWER.value]:
        assigned_role = WorkspaceRole.VIEWER.value

    # Check existing membership
    existing_member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == ws.id,
        WorkspaceMember.user_id == target_user.id,
    ).first()

    if existing_member:
        existing_member.role = assigned_role
        db.commit()
        db.refresh(existing_member)
        return WorkspaceMemberOut(
            id=existing_member.id,
            workspace_id=existing_member.workspace_id,
            user_id=existing_member.user_id,
            email=target_user.email,
            full_name=target_user.full_name,
            role=existing_member.role,
            joined_at=existing_member.joined_at,
        )

    new_member = WorkspaceMember(
        workspace_id=ws.id,
        user_id=target_user.id,
        role=assigned_role,
    )
    db.add(new_member)
    db.commit()
    db.refresh(new_member)

    return WorkspaceMemberOut(
        id=new_member.id,
        workspace_id=new_member.workspace_id,
        user_id=new_member.user_id,
        email=target_user.email,
        full_name=target_user.full_name,
        role=new_member.role,
        joined_at=new_member.joined_at,
    )


@router.delete("/{workspace_id}/members/{user_id}", status_code=status.HTTP_200_OK)
def remove_workspace_member(
    workspace_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Removes a member from the workspace.
    Requires OWNER role (or self-removal).
    """
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    user_role = _get_user_workspace_role(ws, current_user, db)
    if not user_role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found or unauthorized")

    # Only OWNER can remove others; users can remove themselves
    if user_role != WorkspaceRole.OWNER.value and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only workspace owners can remove members",
        )

    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == ws.id,
        WorkspaceMember.user_id == user_id,
    ).first()

    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found in workspace")

    db.delete(member)
    db.commit()
    return {"message": "Member removed successfully from workspace"}
