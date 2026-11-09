import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.models.integration import IntegrationCredential, WebhookSubscription
from app.schemas.integration import (
    ZoteroConnectRequest,
    ZoteroSyncRequest,
    IntegrationStatusOut,
    WebhookCreate,
    WebhookOut,
)
from app.services.discovery import validate_safe_url
from app.services.reference_managers import zotero_service
from app.services.webhook_dispatcher import generate_webhook_secret, SUPPORTED_WEBHOOK_EVENTS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Advanced Integrations & Webhooks"])


def _verify_workspace_access(
    workspace_id: str,
    user: User,
    db: Session,
    require_write: bool = False,
) -> Workspace:
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    if ws.owner_id == user.id:
        return ws
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user.id,
    ).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found or unauthorized")
    if require_write and member.role.upper() not in [WorkspaceRole.OWNER.value, WorkspaceRole.EDITOR.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Viewers are not permitted to manage integrations or webhooks",
        )
    return ws


# =====================================================================
# Reference Manager Integrations (Zotero)
# =====================================================================

@router.post("/integrations/zotero/connect", response_model=IntegrationStatusOut, status_code=status.HTTP_201_CREATED)
def connect_zotero_account(
    payload: ZoteroConnectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Validates and securely encrypts Zotero API credentials for user or workspace.
    """
    ws_id = payload.workspace_id
    if ws_id:
        _verify_workspace_access(ws_id, current_user, db, require_write=True)
    else:
        # Default to user's first owned workspace or create an association
        user_ws = db.query(Workspace).filter(Workspace.owner_id == current_user.id).first()
        ws_id = user_ws.id if user_ws else None

    # Validate against Zotero API (mockable in tests)
    verification = zotero_service.verify_credentials(
        api_key=payload.api_key.strip(),
        user_id=payload.user_id.strip(),
    )

    # Check existing credential
    existing = (
        db.query(IntegrationCredential)
        .filter(
            IntegrationCredential.user_id == current_user.id,
            IntegrationCredential.provider == "zotero",
            IntegrationCredential.workspace_id == ws_id,
        )
        .first()
    )

    if existing:
        existing.set_api_key(payload.api_key.strip())
        existing.external_user_id = payload.user_id.strip()
        existing.is_active = True
        existing.settings_json = {"total_items": verification.get("total_items", 0)}
        db.commit()
        db.refresh(existing)
        return existing

    credential = IntegrationCredential(
        user_id=current_user.id,
        workspace_id=ws_id,
        provider="zotero",
        external_user_id=payload.user_id.strip(),
        is_active=True,
        settings_json={"total_items": verification.get("total_items", 0)},
    )
    credential.set_api_key(payload.api_key.strip())
    db.add(credential)
    db.commit()
    db.refresh(credential)
    return credential


@router.post("/integrations/zotero/sync", status_code=status.HTTP_200_OK)
def sync_zotero_library(
    payload: ZoteroSyncRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Synchronizes references from Zotero into the target workspace catalog.
    """
    ws = _verify_workspace_access(payload.workspace_id, current_user, db, require_write=True)

    # Lookup credential
    credential = (
        db.query(IntegrationCredential)
        .filter(
            IntegrationCredential.provider == "zotero",
            IntegrationCredential.is_active == True,
            (
                (IntegrationCredential.workspace_id == ws.id)
                | (IntegrationCredential.user_id == current_user.id)
            ),
        )
        .first()
    )

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active Zotero integration found for this workspace. Please connect credentials first.",
        )

    result = zotero_service.sync_zotero_library(
        credential=credential,
        workspace_id=ws.id,
        user_id=current_user.id,
        db=db,
        limit=payload.limit or 50,
    )
    return result


@router.get("/integrations/status", response_model=List[IntegrationStatusOut])
def list_integration_status(
    workspace_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists configured integrations for the current user and workspace."""
    query = db.query(IntegrationCredential).filter(IntegrationCredential.user_id == current_user.id)
    if workspace_id:
        _verify_workspace_access(workspace_id, current_user, db, require_write=False)
        query = query.filter(
            (IntegrationCredential.workspace_id == workspace_id)
            | (IntegrationCredential.workspace_id.is_(None))
        )
    return query.all()


# =====================================================================
# Secure Webhooks API
# =====================================================================

@router.post("/webhooks", response_model=WebhookOut, status_code=status.HTTP_201_CREATED)
def create_webhook(
    payload: WebhookCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Registers a new webhook subscription.
    Enforces SSRF validation on the destination URL at registration time.
    Generates a secure HMAC-SHA256 signing secret.
    """
    ws = _verify_workspace_access(payload.workspace_id, current_user, db, require_write=True)

    # 1. Enforce Phase 6 SSRF URL validation
    validate_safe_url(payload.url)

    # 2. Filter valid events
    valid_events = [e for e in payload.events_subscribed if e in SUPPORTED_WEBHOOK_EVENTS or e == "*"]
    if not valid_events:
        valid_events = ["document.ingested", "agent.task.completed", "dossier.generated"]

    # 3. Generate cryptographic signing secret
    secret_key = generate_webhook_secret()

    webhook = WebhookSubscription(
        workspace_id=ws.id,
        user_id=current_user.id,
        url=payload.url.strip(),
        events_subscribed=valid_events,
        secret_key=secret_key,
        is_active=True,
        description=payload.description.strip() if payload.description else None,
    )
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    return webhook


@router.get("/webhooks", response_model=List[WebhookOut])
def list_webhooks(
    workspace_id: str = Query(..., description="Workspace ID to filter webhooks"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists all registered webhooks for the workspace."""
    _verify_workspace_access(workspace_id, current_user, db, require_write=False)
    webhooks = (
        db.query(WebhookSubscription)
        .filter(WebhookSubscription.workspace_id == workspace_id)
        .order_by(WebhookSubscription.created_at.desc())
        .all()
    )
    return webhooks


@router.delete("/webhooks/{webhook_id}", status_code=status.HTTP_200_OK)
def delete_webhook(
    webhook_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deletes a webhook subscription."""
    webhook = db.query(WebhookSubscription).filter(WebhookSubscription.id == webhook_id).first()
    if not webhook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")

    _verify_workspace_access(webhook.workspace_id, current_user, db, require_write=True)

    db.delete(webhook)
    db.commit()
    return {"message": "Webhook subscription deleted successfully"}
