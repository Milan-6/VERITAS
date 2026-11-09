import hashlib
import hmac
import json
import logging
import secrets
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.integration import WebhookSubscription
from app.services.discovery import validate_safe_url

logger = logging.getLogger(__name__)

SUPPORTED_WEBHOOK_EVENTS = {
    "document.ingested",
    "agent.task.completed",
    "dossier.generated",
}


def generate_webhook_secret() -> str:
    """Generates a secure, cryptographically random secret key for HMAC-SHA256 verification."""
    return f"whsec_{secrets.token_hex(24)}"


def compute_hmac_signature(secret_key: str, payload_bytes: bytes) -> str:
    """Computes an HMAC-SHA256 hexadecimal digest for the given payload."""
    return hmac.new(secret_key.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()


class WebhookDispatcher:
    """
    Asynchronous, SSRF-protected event dispatcher with HMAC-SHA256 signatures
    for workspace webhooks.
    """

    def __init__(self, session_factory=None, max_workers: int = 4):
        self.session_factory = session_factory or SessionLocal
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="veritas_webhook_")

    def _deliver_payload(
        self,
        subscription_id: str,
        target_url: str,
        secret_key: str,
        event_name: str,
        delivery_id: str,
        raw_body: str,
    ) -> bool:
        """
        Validates target URL against SSRF, computes HMAC-SHA256 signature,
        and executes an outbound HTTP POST with a strict 5.0-second timeout.
        """
        # 1. SSRF URL validation
        try:
            validate_safe_url(target_url)
        except Exception as ssrf_err:
            logger.warning(
                f"[SSRF BLOCKED] Webhook delivery {delivery_id} to {target_url} blocked: {ssrf_err}"
            )
            return False

        # 2. Compute HMAC signature
        signature = compute_hmac_signature(secret_key, raw_body.encode("utf-8"))

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "VERITAS-Webhook-Dispatcher/1.0",
            "X-Veritas-Event": event_name,
            "X-Veritas-Delivery": delivery_id,
            "X-Veritas-Signature": f"sha256={signature}",
        }

        # 3. Execute HTTP POST with strict 5-second timeout
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.post(target_url, content=raw_body, headers=headers)
                if resp.status_code >= 200 and resp.status_code < 300:
                    logger.info(
                        f"Webhook {delivery_id} delivered successfully to {target_url} (HTTP {resp.status_code})"
                    )
                    return True
                else:
                    logger.warning(
                        f"Webhook {delivery_id} to {target_url} returned non-2xx status code: {resp.status_code}"
                    )
                    return False
        except Exception as e:
            logger.warning(f"Webhook {delivery_id} delivery error to {target_url}: {str(e)}")
            return False

    def dispatch_event(
        self,
        event_name: str,
        workspace_id: str,
        payload: Dict[str, Any],
        db=None,
    ) -> List[str]:
        """
        Finds active webhook subscriptions matching event_name for workspace_id
        and enqueues background delivery tasks.
        """
        local_db = db or self.session_factory()
        delivery_ids: List[str] = []

        try:
            subscriptions = (
                local_db.query(WebhookSubscription)
                .filter(
                    WebhookSubscription.workspace_id == workspace_id,
                    WebhookSubscription.is_active == True,
                )
                .all()
            )

            for sub in subscriptions:
                sub_events = sub.events_subscribed or []
                if event_name in sub_events or "*" in sub_events:
                    delivery_id = str(uuid.uuid4())
                    delivery_ids.append(delivery_id)

                    envelope = {
                        "event": event_name,
                        "delivery_id": delivery_id,
                        "workspace_id": workspace_id,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "data": payload,
                    }
                    raw_body = json.dumps(envelope, sort_keys=True)

                    # Check eager execution mode (e.g. for testing)
                    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
                        self._deliver_payload(
                            subscription_id=sub.id,
                            target_url=sub.url,
                            secret_key=sub.secret_key,
                            event_name=event_name,
                            delivery_id=delivery_id,
                            raw_body=raw_body,
                        )
                    else:
                        self.executor.submit(
                            self._deliver_payload,
                            sub.id,
                            sub.url,
                            sub.secret_key,
                            event_name,
                            delivery_id,
                            raw_body,
                        )

            return delivery_ids

        finally:
            if not db:
                local_db.close()


webhook_dispatcher = WebhookDispatcher()
