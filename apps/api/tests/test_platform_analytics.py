import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limiter import rate_limiter, SlidingWindowRateLimiter
from app.core.security import hash_password, create_access_token
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.models.telemetry import ApiRequestLog, LlmUsageLog
from app.services.telemetry import calculate_llm_cost, telemetry_service


@pytest.fixture
def secondary_user(db: Session) -> User:
    """Creates an editor user for RBAC tests."""
    user = User(
        id=str(uuid.uuid4()),
        email="analytics_editor@veritas.ai",
        full_name="Analytics Editor",
        hashed_password=hash_password("password123"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def secondary_headers(secondary_user: User) -> dict:
    token = create_access_token({"sub": secondary_user.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def viewer_user(db: Session) -> User:
    """Creates a viewer user for RBAC tests."""
    user = User(
        id=str(uuid.uuid4()),
        email="analytics_viewer@veritas.ai",
        full_name="Analytics Viewer",
        hashed_password=hash_password("password123"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def viewer_headers(viewer_user: User) -> dict:
    token = create_access_token({"sub": viewer_user.id})
    return {"Authorization": f"Bearer {token}"}


def test_rate_limiter_unit_sliding_window():
    """Verifies that SlidingWindowRateLimiter enforces bounds, calculates headers and rejects over limit."""
    limiter = SlidingWindowRateLimiter()
    limiter.reset_cache()
    client_id = f"test_client_{uuid.uuid4().hex[:6]}"

    # Allowed up to custom limit of 3
    for i in range(3):
        allowed, headers, retry_after = limiter.check_rate_limit(
            client_id=client_id,
            custom_limit=3,
            custom_window=60,
        )
        assert allowed is True
        assert headers["X-RateLimit-Limit"] == "3"
        assert int(headers["X-RateLimit-Remaining"]) == (2 - i)
        assert "X-RateLimit-Reset" in headers
        assert retry_after == 0

    # 4th request must be rejected
    allowed, headers, retry_after = limiter.check_rate_limit(
        client_id=client_id,
        custom_limit=3,
        custom_window=60,
    )
    assert allowed is False
    assert headers["X-RateLimit-Remaining"] == "0"
    assert "Retry-After" in headers
    assert retry_after > 0


def test_middleware_rate_limiting_and_latency_headers(client: TestClient, auth_headers: dict):
    """Verifies rate limiting and latency headers injected by RateLimitAndTelemetryMiddleware."""
    rate_limiter.reset_cache()

    # Call a standard endpoint
    res = client.get("/api/v1/workspaces", headers=auth_headers)
    assert res.status_code == 200

    # Validate headers injected by middleware
    assert "x-ratelimit-limit" in res.headers
    assert "x-ratelimit-remaining" in res.headers
    assert "x-ratelimit-reset" in res.headers
    assert "x-response-time-ms" in res.headers
    latency = float(res.headers["x-response-time-ms"])
    assert latency >= 0.0


def test_llm_cost_calculation():
    """Verifies precision cost calculations across Gemini models and fallbacks."""
    # Gemini 2.0 Flash: $0.075 / 1M prompt, $0.30 / 1M completion
    cost_flash = calculate_llm_cost("gemini-2.0-flash", prompt_tokens=1_000_000, completion_tokens=1_000_000)
    assert cost_flash == 0.375

    # Gemini 1.5 Pro: $1.25 / 1M prompt, $5.00 / 1M completion
    cost_pro = calculate_llm_cost("gemini-1.5-pro", prompt_tokens=1_000_000, completion_tokens=1_000_000)
    assert cost_pro == 6.25

    # Small token counts
    small_cost = calculate_llm_cost("gemini-2.0-flash", prompt_tokens=1000, completion_tokens=500)
    assert small_cost > 0.0


def test_llm_usage_logging_and_summary(db: Session, test_user: User):
    """Verifies LLM usage logging and workspace aggregation service."""
    ws = Workspace(
        id=str(uuid.uuid4()),
        name="Telemetry Lab",
        slug=f"ws-tele-{uuid.uuid4().hex[:6]}",
        owner_id=test_user.id,
    )
    db.add(ws)
    db.commit()

    ws_id = str(ws.id)
    u_id = str(test_user.id)

    # Log LLM invocations for chat and matrix
    telemetry_service._persist_llm_log(
        workspace_id=ws_id,
        user_id=u_id,
        model_name="gemini-2.0-flash",
        prompt_tokens=1200,
        completion_tokens=300,
        total_tokens=1500,
        cost_usd=calculate_llm_cost("gemini-2.0-flash", 1200, 300),
        feature_context="chat",
    )
    telemetry_service._persist_llm_log(
        workspace_id=ws_id,
        user_id=u_id,
        model_name="gemini-2.0-flash",
        prompt_tokens=4000,
        completion_tokens=1000,
        total_tokens=5000,
        cost_usd=calculate_llm_cost("gemini-2.0-flash", 4000, 1000),
        feature_context="literature_matrix",
    )

    summary = telemetry_service.get_workspace_usage_summary(ws_id, db)
    assert summary["workspace_id"] == ws_id
    assert summary["llm_usage"]["prompt_tokens"] == 5200
    assert summary["llm_usage"]["completion_tokens"] == 1300
    assert summary["llm_usage"]["total_tokens"] == 6500
    assert summary["llm_usage"]["total_llm_invocations"] == 2
    assert "chat" in summary["llm_usage"]["breakdown_by_feature"]
    assert "literature_matrix" in summary["llm_usage"]["breakdown_by_feature"]
    assert summary["llm_usage"]["breakdown_by_feature"]["chat"]["tokens"] == 1500
    assert summary["llm_usage"]["breakdown_by_feature"]["literature_matrix"]["tokens"] == 5000


def test_api_activity_logging_and_metrics(db: Session, test_user: User):
    """Verifies API request persistence and latency/error statistics."""
    ws = Workspace(
        id=str(uuid.uuid4()),
        name="Performance Lab",
        slug=f"ws-perf-{uuid.uuid4().hex[:6]}",
        owner_id=test_user.id,
    )
    db.add(ws)
    db.commit()

    ws_id = str(ws.id)
    u_id = str(test_user.id)

    # Log 3 successful requests and 1 error
    telemetry_service._persist_api_log("/api/v1/chat", "POST", 200, 120.5, u_id, ws_id, "127.0.0.1", "test-agent")
    telemetry_service._persist_api_log("/api/v1/workspaces", "GET", 200, 35.2, u_id, ws_id, "127.0.0.1", "test-agent")
    telemetry_service._persist_api_log("/api/v1/documents", "GET", 200, 44.3, u_id, ws_id, "127.0.0.1", "test-agent")
    telemetry_service._persist_api_log("/api/v1/chat", "POST", 500, 200.0, u_id, ws_id, "127.0.0.1", "test-agent")

    activity = telemetry_service.get_workspace_activity(ws_id, db, limit=10)
    assert activity["workspace_id"] == ws_id
    assert activity["total_requests"] == 4
    assert activity["average_response_time_ms"] > 0
    assert activity["error_rate_percentage"] == 25.0  # 1 out of 4 is >= 400
    assert len(activity["recent_activity"]) == 4


def test_analytics_rbac_owner_vs_collaborators(
    client: TestClient,
    db: Session,
    test_user: User,
    auth_headers: dict,
    secondary_user: User,
    secondary_headers: dict,
    viewer_user: User,
    viewer_headers: dict,
):
    """
    Verifies strict RBAC on Analytics & Telemetry endpoints:
    1. Workspace OWNER has full access to usage & activity.
    2. Workspace EDITOR receives HTTP 403 Forbidden.
    3. Workspace VIEWER receives HTTP 403 Forbidden.
    4. Non-existent workspace receives HTTP 404 Not Found.
    """
    # 1. Create Workspace with test_user as OWNER
    create_res = client.post(
        "/api/v1/workspaces",
        json={"name": "Secure Telemetry Workspace"},
        headers=auth_headers,
    )
    assert create_res.status_code == 201
    ws_id = create_res.json()["id"]
    u_id = str(test_user.id)

    # 2. Invite secondary_user as EDITOR and viewer_user as VIEWER
    inv_editor = client.post(
        f"/api/v1/workspaces/{ws_id}/members",
        json={"email": secondary_user.email, "role": "EDITOR"},
        headers=auth_headers,
    )
    assert inv_editor.status_code == 201

    inv_viewer = client.post(
        f"/api/v1/workspaces/{ws_id}/members",
        json={"email": viewer_user.email, "role": "VIEWER"},
        headers=auth_headers,
    )
    assert inv_viewer.status_code == 201

    # 3. Log a usage record for this workspace
    telemetry_service._persist_llm_log(
        workspace_id=ws_id,
        user_id=u_id,
        model_name="gemini-2.0-flash",
        prompt_tokens=800,
        completion_tokens=200,
        total_tokens=1000,
        cost_usd=0.0001,
        feature_context="chat",
    )
    telemetry_service._persist_api_log(
        endpoint=f"/api/v1/workspaces/{ws_id}",
        method="GET",
        status_code=200,
        response_time_ms=45.0,
        user_id=u_id,
        workspace_id=ws_id,
        ip_address="127.0.0.1",
        user_agent="pytest-client",
    )

    # 4. OWNER Queries Usage & Activity -> 200 OK
    usage_res = client.get(f"/api/v1/analytics/workspace/{ws_id}/usage", headers=auth_headers)
    assert usage_res.status_code == 200
    usage_json = usage_res.json()
    assert usage_json["workspace_id"] == ws_id
    assert usage_json["llm_usage"]["total_tokens"] >= 1000

    activity_res = client.get(f"/api/v1/analytics/workspace/{ws_id}/activity", headers=auth_headers)
    assert activity_res.status_code == 200
    activity_json = activity_res.json()
    assert activity_json["workspace_id"] == ws_id
    assert activity_json["total_requests"] >= 1

    # 5. EDITOR Queries Usage & Activity -> 403 Forbidden
    editor_usage = client.get(f"/api/v1/analytics/workspace/{ws_id}/usage", headers=secondary_headers)
    assert editor_usage.status_code == 403
    assert "Only workspace owners" in editor_usage.json()["detail"]

    editor_act = client.get(f"/api/v1/analytics/workspace/{ws_id}/activity", headers=secondary_headers)
    assert editor_act.status_code == 403
    assert "Only workspace owners" in editor_act.json()["detail"]

    # 6. VIEWER Queries Usage & Activity -> 403 Forbidden
    viewer_usage = client.get(f"/api/v1/analytics/workspace/{ws_id}/usage", headers=viewer_headers)
    assert viewer_usage.status_code == 403
    assert "Only workspace owners" in viewer_usage.json()["detail"]

    viewer_act = client.get(f"/api/v1/analytics/workspace/{ws_id}/activity", headers=viewer_headers)
    assert viewer_act.status_code == 403
    assert "Only workspace owners" in viewer_act.json()["detail"]

    # 7. Non-existent Workspace -> 404 Not Found
    non_existent_id = str(uuid.uuid4())
    notFound = client.get(f"/api/v1/analytics/workspace/{non_existent_id}/usage", headers=auth_headers)
    assert notFound.status_code == 404
