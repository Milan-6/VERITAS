import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Set
from datetime import datetime

from app.core.database import SessionLocal
from app.models.document import Document, DocumentProcessingJob, DocumentStatus, JobStatus
from app.services.processing_pipeline import processing_pipeline

logger = logging.getLogger(__name__)


class BackgroundJobManager:
    def __init__(self, max_workers: int = 4, session_factory=None):
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="veritas_worker_")
        self._active_jobs: Set[str] = set()
        self._lock = threading.Lock()
        self.session_factory = session_factory or SessionLocal

    def enqueue_job(self, job_id: str) -> bool:
        """
        Enqueues a DocumentProcessingJob for asynchronous background processing.
        Updates job and document status to QUEUED.
        """
        with self._lock:
            if job_id in self._active_jobs:
                logger.warning(f"Job {job_id} is already enqueued or active.")
                return False
            self._active_jobs.add(job_id)

        # Update status in DB to QUEUED
        db = self.session_factory()
        try:
            job = db.query(DocumentProcessingJob).filter(DocumentProcessingJob.id == job_id).first()
            if job:
                job.status = JobStatus.PENDING.value
                doc = db.query(Document).filter(Document.id == job.document_id).first()
                if doc and doc.status == DocumentStatus.UPLOADED.value:
                    doc.status = DocumentStatus.QUEUED.value
                db.commit()
        finally:
            db.close()

        # Submit to thread pool
        self.executor.submit(self._run_job_wrapper, job_id)
        return True

    def _run_job_wrapper(self, job_id: str):
        try:
            logger.info(f"Worker starting execution for job {job_id}")
            db = self.session_factory()
            try:
                processing_pipeline.process_document_job(job_id, db=db)
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Worker uncaught exception for job {job_id}: {e}")
        finally:
            with self._lock:
                self._active_jobs.discard(job_id)
            logger.info(f"Worker finished execution for job {job_id}")

    def is_job_active(self, job_id: str) -> bool:
        with self._lock:
            return job_id in self._active_jobs

    def retry_job(self, job_id: str) -> bool:
        """
        Retries a failed job if attempts < max_retries.
        """
        db = self.session_factory()
        try:
            job = db.query(DocumentProcessingJob).filter(DocumentProcessingJob.id == job_id).first()
            if not job:
                return False
            if job.status == JobStatus.RUNNING.value:
                return False
            if job.attempts >= job.max_retries:
                logger.warning(f"Job {job_id} has exceeded max retries ({job.max_retries}).")
                # Reset attempt counter on explicit user retry request to allow manual recovery
                job.attempts = 0

            job.status = JobStatus.PENDING.value
            job.error_details = None
            job.progress_pct = 0.0
            doc = db.query(Document).filter(Document.id == job.document_id).first()
            if doc:
                doc.status = DocumentStatus.QUEUED.value
                doc.error_message = None
            db.commit()

            return self.enqueue_job(job_id)
        finally:
            db.close()


job_manager = BackgroundJobManager()
