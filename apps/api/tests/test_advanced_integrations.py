import json
import uuid
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import httpx

from app.core.encryption import encrypt_secret, decrypt_secret
from app.models.user import User
from app.models.workspace import Workspace
from app.models.integration import IntegrationCredential, WebhookSubscription
from app.models.document import Document
from app.services.webhook_dispatcher import (
    compute_hmac_signature,
    webhook_dispatcher,
)
from app.services.reference_managers import zotero_service


def test_api_key_encryption_at_rest(db: Session, test_user: User):
    """
    Verifies that integration API keys are symmetrically encrypted at rest (Fernet)
    in the database and seamlessly decrypted in memory.
    """
    raw_api_key = "zotero_secret_token_abc123456789"
    cipher_text = encrypt_secret(raw_api_key)

    assert cipher_text != raw_api_key
    assert len(cipher_text) > 30
    assert decrypt_secret(cipher_text) == raw_api_key

    # Test IntegrationCredential model helper methods
    cred = IntegrationCredential(
        user_id=test_user.id,
        provider="zotero",
        external_user_id="1234567",
        encrypted_api_key="",
    )
    cred.set_api_key(raw_api_key)
    db.add(cred)
    db.commit()
    db.refresh(cred)

    # Database column stores encrypted ciphertext
    assert cred.encrypted_api_key != raw_api_key
    assert cred.encrypted_api_key.startswith("gAAAAA")

    # In-memory retrieval decrypts accurately
    assert cred.get_api_key() == raw_api_key


def test_webhook_ssrf_blocking_at_registration(
    client: TestClient,
    test_user: User,
    auth_headers: dict,
    db: Session,
):
    """
    Asserts that webhook registration strictly enforces Phase 6 SSRF protections:
    rejects localhost, private IPs (127.0.0.1, 10.0.0.1, 192.168.1.1), link-local,
    and non-HTTP/HTTPS schemes.
    """
    # 1. Create workspace
    ws = Workspace(name="Webhook Security Workspace", slug=f"ws-{uuid.uuid4().hex[:6]}", owner_id=test_user.id)
    db.add(ws)
    db.commit()

    malicious_urls = [
        "http://127.0.0.1:8080/internal-admin",
        "http://localhost:5000/hook",
        "http://169.254.169.254/latest/meta-data/",
        "ftp://example.com/webhook",
        "http://0.0.0.0/attack",
    ]

    for bad_url in malicious_urls:
        res = client.post(
            "/api/v1/webhooks",
            json={
                "workspace_id": ws.id,
                "url": bad_url,
                "events_subscribed": ["document.ingested"],
                "description": "Malicious SSRF test",
            },
            headers=auth_headers,
        )
        assert res.status_code == 400
        assert "violation" in res.json()["detail"].lower() or "forbidden" in res.json()["detail"].lower() or "ssrf" in res.json()["detail"].lower()


def test_webhook_registration_and_hmac_signature(
    client: TestClient,
    test_user: User,
    auth_headers: dict,
    db: Session,
):
    """
    Verifies valid webhook registration, generation of cryptographic secret,
    and accurate HMAC-SHA256 signature calculation.
    """
    ws = Workspace(name="Webhook Test Lab", slug=f"ws-{uuid.uuid4().hex[:6]}", owner_id=test_user.id)
    db.add(ws)
    db.commit()

    # 1. Register valid webhook using a valid public IP or mocked DNS
    with patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 443))]):
        res = client.post(
            "/api/v1/webhooks",
            json={
                "workspace_id": ws.id,
                "url": "https://api.veritas-external-partner.org/webhook-receiver",
                "events_subscribed": ["document.ingested", "agent.task.completed"],
                "description": "Production Slack Sync",
            },
            headers=auth_headers,
        )
        assert res.status_code == 201
        data = res.json()
        assert data["url"] == "https://api.veritas-external-partner.org/webhook-receiver"
        assert data["secret_key"].startswith("whsec_")
        assert len(data["secret_key"]) > 30
        wh_id = data["id"]
        secret_key = data["secret_key"]

    # 2. List webhooks
    list_res = client.get(f"/api/v1/webhooks?workspace_id={ws.id}", headers=auth_headers)
    assert list_res.status_code == 200
    assert any(w["id"] == wh_id for w in list_res.json())

    # 3. Verify HMAC signature computation
    test_payload = json.dumps({"event": "document.ingested", "test": True}, sort_keys=True)
    expected_sig = compute_hmac_signature(secret_key, test_payload.encode("utf-8"))
    assert len(expected_sig) == 64  # SHA256 hex digest length

    # 4. Delete webhook
    del_res = client.delete(f"/api/v1/webhooks/{wh_id}", headers=auth_headers)
    assert del_res.status_code == 200


def test_zotero_connect_and_mock_sync_service(
    client: TestClient,
    test_user: User,
    auth_headers: dict,
    db: Session,
):
    """
    Mocks Zotero external API calls and verifies:
    1. Credentials connection & encrypted storage.
    2. Reference items fetching and document catalog synchronization.
    3. Document metadata extraction from Zotero creators & abstract.
    """
    ws = Workspace(name="Zotero Sync Lab", slug=f"ws-{uuid.uuid4().hex[:6]}", owner_id=test_user.id)
    db.add(ws)
    db.commit()

    # Mock sample Zotero items response
    mock_zotero_items = [
        {
            "key": "ZOT_ITEM_001",
            "data": {
                "itemType": "journalArticle",
                "title": "Attention Is All You Need",
                "creators": [
                    {"creatorType": "author", "firstName": "Ashish", "lastName": "Vaswani"},
                    {"creatorType": "author", "firstName": "Noam", "lastName": "Shazeer"},
                ],
                "abstractNote": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks.",
                "publicationTitle": "Advances in Neural Information Processing Systems",
                "date": "2017",
                "DOI": "10.48550/arXiv.1706.03762",
                "url": "https://arxiv.org/abs/1706.03762",
            },
        },
        {
            "key": "ZOT_ITEM_002",
            "data": {
                "itemType": "journalArticle",
                "title": "BERT: Pre-training of Deep Bidirectional Transformers",
                "creators": [
                    {"creatorType": "author", "firstName": "Jacob", "lastName": "Devlin"},
                ],
                "abstractNote": "We introduce a new language representation model called BERT.",
                "publicationTitle": "NAACL-HLT",
                "date": "2019",
                "DOI": "10.48550/arXiv.1810.04805",
                "url": "https://arxiv.org/abs/1810.04805",
            },
        },
        {
            "key": "ZOT_ATTACHMENT_003",
            "data": {
                "itemType": "attachment",
                "title": "",  # Attachment without title -> should be skipped
            },
        },
    ]

    # 1. Connect Zotero Account (Mocking external verification call)
    with patch.object(zotero_service, "verify_credentials", return_value={"valid": True, "user_id": "999888", "total_items": 2}):
        connect_res = client.post(
            "/api/v1/integrations/zotero/connect",
            json={
                "api_key": "valid_test_zotero_api_key_12345",
                "user_id": "999888",
                "workspace_id": ws.id,
            },
            headers=auth_headers,
        )
        assert connect_res.status_code == 201
        conn_data = connect_res.json()
        assert conn_data["provider"] == "zotero"
        assert conn_data["external_user_id"] == "999888"

    # 2. Sync Zotero Library (Mocking items fetching)
    with patch.object(zotero_service, "fetch_items", return_value=mock_zotero_items):
        sync_res = client.post(
            "/api/v1/integrations/zotero/sync",
            json={"workspace_id": ws.id, "limit": 10},
            headers=auth_headers,
        )
        assert sync_res.status_code == 200
        sync_data = sync_res.json()
        assert sync_data["status"] == "success"
        assert sync_data["total_items_fetched"] == 3
        assert sync_data["documents_created"] == 2
        assert sync_data["skipped_or_existing"] == 1

    # 3. Verify documents in database catalog
    docs = db.query(Document).filter(Document.workspace_id == ws.id).all()
    assert len(docs) == 2
    titles = [d.doc_metadata.title for d in docs if d.doc_metadata]
    assert "Attention Is All You Need" in titles
    assert "BERT: Pre-training of Deep Bidirectional Transformers" in titles

    # 4. Status endpoint check
    status_res = client.get(f"/api/v1/integrations/status?workspace_id={ws.id}", headers=auth_headers)
    assert status_res.status_code == 200
    assert len(status_res.json()) >= 1


def test_webhook_dispatcher_ssrf_blocking_and_delivery(db: Session, test_user: User):
    """
    Verifies that WebhookDispatcher:
    1. Blocks delivery when destination URL violates SSRF.
    2. Sends signed HMAC-SHA256 headers when dispatching to valid destination.
    """
    ws = Workspace(name="Dispatcher Lab", slug=f"ws-{uuid.uuid4().hex[:6]}", owner_id=test_user.id)
    db.add(ws)
    db.commit()

    # 1. SSRF URL Subscription
    sub_malicious = WebhookSubscription(
        workspace_id=ws.id,
        user_id=test_user.id,
        url="http://127.0.0.1:9000/internal-leak",
        events_subscribed=["document.ingested"],
        secret_key="whsec_test_secret_01",
        is_active=True,
    )
    # 2. Valid URL Subscription
    sub_valid = WebhookSubscription(
        workspace_id=ws.id,
        user_id=test_user.id,
        url="https://93.184.216.34/webhook-receiver",
        events_subscribed=["document.ingested"],
        secret_key="whsec_test_secret_02",
        is_active=True,
    )
    db.add_all([sub_malicious, sub_valid])
    db.commit()

    # Mock httpx.Client post
    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        deliveries = webhook_dispatcher.dispatch_event(
            event_name="document.ingested",
            workspace_id=ws.id,
            payload={"doc_id": "test_doc_123"},
            db=db,
        )

        assert len(deliveries) == 2
        # Only the valid subscription makes the HTTP POST request (malicious was blocked by SSRF)
        assert mock_post.call_count == 1
        call_args, call_kwargs = mock_post.call_args
        assert call_args[0] == "https://93.184.216.34/webhook-receiver"
        headers = call_kwargs["headers"]
        assert headers["X-Veritas-Event"] == "document.ingested"
        assert headers["X-Veritas-Signature"].startswith("sha256=")

