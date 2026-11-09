import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.telemetry import ApiRequestLog, LlmUsageLog
from app.models.document import Document

logger = logging.getLogger(__name__)

# USD per 1 Million Tokens
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    "gemini-2.0-flash": {"prompt": 0.075, "completion": 0.30},
    "gemini-2.5-flash": {"prompt": 0.075, "completion": 0.30},
    "gemini-1.5-flash": {"prompt": 0.075, "completion": 0.30},
    "gemini-1.5-pro": {"prompt": 1.25, "completion": 5.00},
}
DEFAULT_PRICING = {"prompt": 0.10, "completion": 0.40}


def calculate_llm_cost(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculates estimated USD cost based on token counts and model pricing."""
    rates = MODEL_PRICING.get(model_name.lower(), DEFAULT_PRICING)
    cost = (prompt_tokens / 1_000_000.0) * rates["prompt"] + (
        completion_tokens / 1_000_000.0
    ) * rates["completion"]
    return round(cost, 6)


class TelemetryService:
    """
    Asynchronous internal telemetry logger for API response times,
    LLM token consumption, and cost tracking.
    """

    def __init__(self, session_factory=None, max_workers: int = 4):
        self.session_factory = session_factory or SessionLocal
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="veritas_telemetry_")

    def _persist_llm_log(
        self,
        workspace_id: Optional[str],
        user_id: Optional[str],
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        cost_usd: float,
        feature_context: str,
    ):
        db = self.session_factory()
        try:
            log_entry = LlmUsageLog(
                workspace_id=workspace_id,
                user_id=user_id,
                model_name=model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=cost_usd,
                feature_context=feature_context,
                timestamp=datetime.utcnow(),
            )
            db.add(log_entry)
            db.commit()
        except Exception as e:
            logger.warning(f"Failed to persist LLM usage log: {e}")
            db.rollback()
        finally:
            db.close()

    def log_llm_usage(
        self,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        workspace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        feature_context: str = "chat",
    ):
        """Asynchronously writes token metrics and costs to LlmUsageLog."""
        total_tokens = prompt_tokens + completion_tokens
        cost_usd = calculate_llm_cost(model_name, prompt_tokens, completion_tokens)

        # Check synchronous mode (testing)
        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            self._persist_llm_log(
                workspace_id=workspace_id,
                user_id=user_id,
                model_name=model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=cost_usd,
                feature_context=feature_context,
            )
        else:
            self.executor.submit(
                self._persist_llm_log,
                workspace_id,
                user_id,
                model_name,
                prompt_tokens,
                completion_tokens,
                total_tokens,
                cost_usd,
                feature_context,
            )

    def _persist_api_log(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: float,
        user_id: Optional[str],
        workspace_id: Optional[str],
        ip_address: Optional[str],
        user_agent: Optional[str],
    ):
        db = self.session_factory()
        try:
            log_entry = ApiRequestLog(
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                response_time_ms=response_time_ms,
                user_id=user_id,
                workspace_id=workspace_id,
                ip_address=ip_address,
                user_agent=user_agent,
                timestamp=datetime.utcnow(),
            )
            db.add(log_entry)
            db.commit()
        except Exception as e:
            logger.warning(f"Failed to persist API request log: {e}")
            db.rollback()
        finally:
            db.close()

    def log_api_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: float,
        user_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Asynchronously records an API request."""
        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            self._persist_api_log(
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                response_time_ms=response_time_ms,
                user_id=user_id,
                workspace_id=workspace_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        else:
            self.executor.submit(
                self._persist_api_log,
                endpoint,
                method,
                status_code,
                response_time_ms,
                user_id,
                workspace_id,
                ip_address,
                user_agent,
            )

    def get_workspace_usage_summary(self, workspace_id: str, db: Session) -> Dict[str, Any]:
        """Calculates aggregated token usage, cost, and request totals for a workspace."""
        # 1. Total LLM Usage
        llm_totals = (
            db.query(
                func.coalesce(func.sum(LlmUsageLog.prompt_tokens), 0).label("prompt_tokens"),
                func.coalesce(func.sum(LlmUsageLog.completion_tokens), 0).label("completion_tokens"),
                func.coalesce(func.sum(LlmUsageLog.total_tokens), 0).label("total_tokens"),
                func.coalesce(func.sum(LlmUsageLog.cost_usd), 0.0).label("total_cost"),
                func.count(LlmUsageLog.id).label("total_calls"),
            )
            .filter(LlmUsageLog.workspace_id == workspace_id)
            .first()
        )

        # 2. Breakdown by feature context
        feature_rows = (
            db.query(
                LlmUsageLog.feature_context,
                func.sum(LlmUsageLog.total_tokens).label("tokens"),
                func.sum(LlmUsageLog.cost_usd).label("cost"),
                func.count(LlmUsageLog.id).label("calls"),
            )
            .filter(LlmUsageLog.workspace_id == workspace_id)
            .group_by(LlmUsageLog.feature_context)
            .all()
        )
        by_feature = {
            r[0]: {"tokens": int(r[1] or 0), "cost_usd": round(float(r[2] or 0.0), 4), "calls": int(r[3] or 0)}
            for r in feature_rows
        }

        # 3. Total documents processed
        doc_count = db.query(Document).filter(Document.workspace_id == workspace_id).count()

        # 4. Total API requests
        api_requests_count = (
            db.query(ApiRequestLog).filter(ApiRequestLog.workspace_id == workspace_id).count()
        )

        return {
            "workspace_id": workspace_id,
            "total_documents": doc_count,
            "total_api_requests": api_requests_count,
            "llm_usage": {
                "prompt_tokens": int(llm_totals[0]) if llm_totals else 0,
                "completion_tokens": int(llm_totals[1]) if llm_totals else 0,
                "total_tokens": int(llm_totals[2]) if llm_totals else 0,
                "estimated_cost_usd": round(float(llm_totals[3]), 4) if llm_totals else 0.0,
                "total_llm_invocations": int(llm_totals[4]) if llm_totals else 0,
                "breakdown_by_feature": by_feature,
            },
        }

    def get_workspace_activity(
        self,
        workspace_id: str,
        db: Session,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Fetches recent API request records and aggregate performance metrics."""
        logs = (
            db.query(ApiRequestLog)
            .filter(ApiRequestLog.workspace_id == workspace_id)
            .order_by(ApiRequestLog.timestamp.desc())
            .limit(limit)
            .all()
        )

        # Performance aggregates
        stats = (
            db.query(
                func.coalesce(func.avg(ApiRequestLog.response_time_ms), 0.0).label("avg_latency"),
                func.count(ApiRequestLog.id).label("total_requests"),
            )
            .filter(ApiRequestLog.workspace_id == workspace_id)
            .first()
        )

        error_count = (
            db.query(ApiRequestLog)
            .filter(
                ApiRequestLog.workspace_id == workspace_id,
                ApiRequestLog.status_code >= 400,
            )
            .count()
        )
        total_reqs = stats[1] if stats else 0
        error_rate = round((error_count / total_reqs * 100.0), 2) if total_reqs > 0 else 0.0

        activity_records = [
            {
                "id": log.id,
                "endpoint": log.endpoint,
                "method": log.method,
                "status_code": log.status_code,
                "response_time_ms": round(log.response_time_ms, 2),
                "timestamp": log.timestamp.isoformat(),
            }
            for log in logs
        ]

        return {
            "workspace_id": workspace_id,
            "total_requests": total_reqs,
            "average_response_time_ms": round(float(stats[0]), 2) if stats else 0.0,
            "error_rate_percentage": error_rate,
            "recent_activity": activity_records,
        }


telemetry_service = TelemetryService()
