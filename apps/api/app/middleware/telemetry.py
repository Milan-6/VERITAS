import logging
import re
import time
from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.rate_limiter import rate_limiter
from app.core.security import decode_access_token
from app.services.telemetry import telemetry_service

logger = logging.getLogger(__name__)

EXCLUDED_PATHS = {
    "/health",
    f"{settings.API_V1_PREFIX}/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
}

HEAVY_PATTERNS = [
    re.compile(r"/chat"),
    re.compile(r"/agent"),
    re.compile(r"/analysis"),
    re.compile(r"/learning/flashcards/generate"),
    re.compile(r"/learning/quiz/generate"),
]

WORKSPACE_PATTERN = re.compile(r"/(?:workspaces|workspace)/([a-zA-Z0-9_\-]+)")


class RateLimitAndTelemetryMiddleware(BaseHTTPMiddleware):
    """
    Middleware providing:
    1. Sliding window rate limiting per user/IP with X-RateLimit-* headers & HTTP 429.
    2. End-to-end request latency profiling (X-Response-Time-Ms).
    3. Asynchronous internal telemetry logging to ApiRequestLog.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Bypass telemetry and rate limiting for health, docs, and preflight
        if path in EXCLUDED_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        # 1. Identify Client & Authenticated User
        user_id: Optional[str] = None
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            try:
                payload = decode_access_token(token)
                user_id = payload.get("sub")
            except Exception:
                pass

        # Determine IP
        x_forwarded = request.headers.get("x-forwarded-for")
        client_ip = (
            x_forwarded.split(",")[0].strip()
            if x_forwarded
            else (request.client.host if request.client else "127.0.0.1")
        )

        client_id = f"user:{user_id}" if user_id else f"ip:{client_ip}"

        # 2. Extract Workspace ID if present
        workspace_id = request.headers.get("x-workspace-id")
        if not workspace_id:
            ws_match = WORKSPACE_PATTERN.search(path)
            if ws_match:
                workspace_id = ws_match.group(1)
        if not workspace_id:
            workspace_id = request.query_params.get("workspace_id")

        # 3. Determine Limit Tier
        tier = "default"
        for pattern in HEAVY_PATTERNS:
            if pattern.search(path):
                tier = "heavy"
                break

        # 4. Check Rate Limit
        is_allowed, rl_headers, retry_after = rate_limiter.check_rate_limit(
            client_id=client_id,
            limit_tier=tier,
        )

        if not is_allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please wait before making more requests.",
                    "retry_after": retry_after,
                },
                headers=rl_headers,
            )

        # 5. Profile Request Latency
        start_time = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        # 6. Inject Rate Limiting & Latency Headers into Response
        for header_key, header_val in rl_headers.items():
            response.headers[header_key] = str(header_val)
        response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.2f}"

        # 7. Asynchronously Log API Telemetry
        try:
            telemetry_service.log_api_request(
                endpoint=path,
                method=request.method,
                status_code=response.status_code,
                response_time_ms=elapsed_ms,
                user_id=user_id,
                workspace_id=workspace_id,
                ip_address=client_ip,
                user_agent=request.headers.get("user-agent"),
            )
        except Exception as e:
            logger.warning(f"Telemetry logging error: {e}")

        return response
