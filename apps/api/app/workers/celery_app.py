import logging
from celery import Celery
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Celery application
celery_app = Celery(
    "veritas_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# Standard production Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max for heavy multi-document ingestion
    worker_prefetch_multiplier=1,
)


@celery_app.task(name="process_document_job", bind=True, max_retries=3)
def process_document_job_task(self, job_id: str):
    """
    Celery task that processes uploaded research documents asynchronously:
    Text extraction, chunking, vector embedding, and graph entity extraction.
    """
    logger.info(f"[Celery] Starting execution for job_id={job_id}")
    from app.core.database import SessionLocal
    from app.services.processing_pipeline import processing_pipeline

    db = SessionLocal()
    try:
        processing_pipeline.process_document_job(job_id, db=db)
        logger.info(f"[Celery] Successfully completed job_id={job_id}")
    except Exception as exc:
        logger.error(f"[Celery] Error processing job_id={job_id}: {exc}")
        raise self.retry(exc=exc, countdown=10)
    finally:
        db.close()


@celery_app.task(name="deliver_webhook", bind=True, max_retries=3)
def deliver_webhook_task(
    self,
    subscription_id: str,
    target_url: str,
    secret_key: str,
    event_name: str,
    delivery_id: str,
    raw_body: str,
):
    """
    Celery task that dispatches HMAC-signed webhooks asynchronously to external endpoints.
    """
    logger.info(f"[Celery] Dispatching webhook delivery_id={delivery_id} to {target_url}")
    from app.services.webhook_dispatcher import webhook_dispatcher

    try:
        webhook_dispatcher._deliver_payload(
            subscription_id=subscription_id,
            target_url=target_url,
            secret_key=secret_key,
            event_name=event_name,
            delivery_id=delivery_id,
            raw_body=raw_body,
        )
    except Exception as exc:
        logger.error(f"[Celery] Webhook delivery failed for delivery_id={delivery_id}: {exc}")
        raise self.retry(exc=exc, countdown=5)
