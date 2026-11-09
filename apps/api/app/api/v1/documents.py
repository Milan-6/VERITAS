import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import get_current_user, verify_document_access
from app.models.user import User
from app.models.document import (
    Document,
    DocumentMetadata,
    DocumentProcessingJob,
    DocumentStatus,
    JobStatus,
    ProcessingStage,
)
from app.models.workspace import Workspace, DocumentWorkspaceAssociation
from app.schemas.document import (
    DocumentOut,
    DocumentDetailOut,
    DocumentProcessingJobOut,
    DocumentUploadResponse,
    BatchUploadResponse,
)
from app.services.storage import storage_service
from app.services.vector_store import vector_store
from app.workers.queue import job_manager

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    workspace_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Secure single PDF file upload endpoint.
    Performs validation, secure storage, and enqueues background processing.
    """
    # Verify workspace if provided
    if workspace_id:
        ws = db.query(Workspace).filter(Workspace.id == workspace_id, Workspace.owner_id == current_user.id).first()
        if not ws:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found or unauthorized")

    # Validate and persist file
    sanitized_name, storage_path, file_size, sha256_hash = await storage_service.validate_and_save_upload(file)

    # Check for duplicate file for this user
    existing_doc = db.query(Document).filter(
        Document.user_id == current_user.id,
        Document.file_hash_sha256 == sha256_hash
    ).first()

    if existing_doc and existing_doc.status == DocumentStatus.COMPLETED.value:
        # File already uploaded and processed
        # Clean up the newly saved duplicate file
        storage_service.delete_file(storage_path)
        job = db.query(DocumentProcessingJob).filter(DocumentProcessingJob.document_id == existing_doc.id).order_by(DocumentProcessingJob.created_at.desc()).first()
        return DocumentUploadResponse(
            document=DocumentOut.model_validate(existing_doc),
            job=DocumentProcessingJobOut.model_validate(job) if job else None,
            message="Document already exists and is fully processed.",
        )

    # Create document record
    document = Document(
        user_id=current_user.id,
        workspace_id=workspace_id,
        filename=sanitized_name,
        storage_path=storage_path,
        file_size_bytes=file_size,
        mime_type="application/pdf",
        file_hash_sha256=sha256_hash,
        status=DocumentStatus.UPLOADED.value,
    )
    db.add(document)
    db.flush()

    # Create initial processing job
    job = DocumentProcessingJob(
        document_id=document.id,
        status=JobStatus.PENDING.value,
        stage=ProcessingStage.VALIDATION.value,
        progress_pct=0.0,
    )
    db.add(job)
    db.commit()
    db.refresh(document)
    db.refresh(job)

    # Enqueue background processing
    job_manager.enqueue_job(job.id)

    return DocumentUploadResponse(
        document=DocumentOut.model_validate(document),
        job=DocumentProcessingJobOut.model_validate(job),
        message="Document uploaded successfully and queued for extraction.",
    )


@router.post("/upload-batch", response_model=BatchUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_documents_batch(
    files: List[UploadFile] = File(...),
    workspace_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Batch PDF file upload endpoint. Accepts multiple files and queues each for extraction.
    """
    successful = []
    failed = []

    for file in files:
        try:
            res = await upload_document(
                file=file,
                workspace_id=workspace_id,
                current_user=current_user,
                db=db
            )
            successful.append(res)
        except Exception as e:
            failed.append({
                "filename": file.filename or "unknown",
                "error": str(e)
            })

    return BatchUploadResponse(
        successful=successful,
        failed=failed,
        total_uploaded=len(successful),
    )


@router.get("", response_model=List[DocumentOut])
def list_documents(
    workspace_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Lists documents accessible to the authenticated user with optional workspace and status filters.
    """
    query = db.query(Document).options(
        joinedload(Document.doc_metadata),
        joinedload(Document.processing_jobs)
    ).filter(Document.user_id == current_user.id)

    if workspace_id:
        query = query.filter(Document.workspace_id == workspace_id)
    if status_filter:
        query = query.filter(Document.status == status_filter.upper())

    docs = query.order_by(Document.created_at.desc()).all()
    
    results = []
    for d in docs:
        d_out = DocumentOut.model_validate(d)
        if d.processing_jobs:
            d_out.latest_job = DocumentProcessingJobOut.model_validate(d.processing_jobs[0])
        results.append(d_out)

    return results


@router.get("/{document_id}", response_model=DocumentDetailOut)
def get_document_detail(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves full details of a document, including metadata, extracted sections, pages, and chunks.
    """
    doc = verify_document_access(document_id, current_user, db, require_write=False)
    
    detail = DocumentDetailOut.model_validate(doc)
    if doc.processing_jobs:
        detail.latest_job = DocumentProcessingJobOut.model_validate(doc.processing_jobs[0])
    return detail


@router.get("/{document_id}/status", response_model=DocumentProcessingJobOut)
def get_document_processing_status(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Poll processing status and progress percentage of a document.
    """
    verify_document_access(document_id, current_user, db, require_write=False)

    job = db.query(DocumentProcessingJob).filter(
        DocumentProcessingJob.document_id == document_id
    ).order_by(DocumentProcessingJob.created_at.desc()).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Processing job not found for this document",
        )

    return DocumentProcessingJobOut.model_validate(job)


@router.post("/{document_id}/retry", response_model=DocumentProcessingJobOut)
def retry_document_processing(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retries document extraction for a failed or stuck job.
    """
    verify_document_access(document_id, current_user, db, require_write=True)

    job = db.query(DocumentProcessingJob).filter(
        DocumentProcessingJob.document_id == document_id
    ).order_by(DocumentProcessingJob.created_at.desc()).first()

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    enqueued = job_manager.retry_job(job.id)
    if not enqueued:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not enqueue retry. Job may already be running or pending."
        )

    db.refresh(job)
    return DocumentProcessingJobOut.model_validate(job)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Deletes a document, its database records, and physical file from storage.
    """
    doc = verify_document_access(document_id, current_user, db, require_write=True)

    storage_path = doc.storage_path
    db.delete(doc)
    db.commit()

    # Safely clean up vectors in Qdrant and storage file
    vector_store.delete_document_vectors(document_id)
    storage_service.delete_file(storage_path)
    return None


@router.get("/{document_id}/download")
def download_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Securely download original PDF file.
    """
    doc = verify_document_access(document_id, current_user, db, require_write=False)
    if not os.path.exists(doc.storage_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored file missing from disk")

    return FileResponse(
        path=doc.storage_path,
        filename=doc.filename,
        media_type="application/pdf"
    )
