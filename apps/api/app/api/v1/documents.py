import json
import os
from pathlib import Path
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
    ExtractedSection,
)
from app.models.learning import FlashcardDeck, Flashcard
from app.models.workspace import Workspace, DocumentWorkspaceAssociation
from app.schemas.document import (
    DocumentOut,
    DocumentDetailOut,
    DocumentProcessingJobOut,
    DocumentUploadResponse,
    BatchUploadResponse,
    DocumentTreeDataResponse,
    DocumentTreeNodeSchema,
    DocumentTreeLinkSchema,
)
from app.services.storage import storage_service
from app.services.vector_store import vector_store
from app.services.audit import audit_service
from app.services.pdf_parser import pdf_parser_service
from app.models.audit import DocumentAuditAction
from app.workers.queue import job_manager

router = APIRouter(prefix="/documents", tags=["Documents"])
tree_router = APIRouter(prefix="/document", tags=["Document Tree"])


@router.get("/tree", response_model=DocumentTreeDataResponse)
@tree_router.get("/tree", response_model=DocumentTreeDataResponse)
def get_document_tree(
    document_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Returns the hierarchical 3D/2D document knowledge tree (Root -> H1 -> H2 -> Flashcards).
    If a specific document_id is provided, constructs the tree from database records;
    otherwise, returns the canonical research tree (or fallback mock tree if DB is empty).
    """
    # 1. If document_id provided, build from DB
    if document_id:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{document_id}' not found.",
            )

        title = doc.doc_metadata.title if doc.doc_metadata else doc.filename
        nodes: list[DocumentTreeNodeSchema] = [
            DocumentTreeNodeSchema(
                id="node_root",
                label=title,
                level=0,
                topic_cluster="cluster_foundation",
                panel_payload=f"Primary document: {doc.filename}\nStatus: {doc.status}\nSHA256: {doc.file_hash_sha256}",
            )
        ]
        links: list[DocumentTreeLinkSchema] = []

        # Sections (Level 1 and Level 2)
        sections = (
            db.query(ExtractedSection)
            .filter(ExtractedSection.document_id == document_id)
            .order_by(ExtractedSection.order_index)
            .all()
        )

        # If sections not yet populated in DB, run fast extraction directly from file
        if not sections and doc.storage_path and os.path.exists(doc.storage_path):
            tree_data = pdf_parser_service.extract_document_tree_and_hierarchy(
                file_path=doc.storage_path,
                document_id=doc.id,
                filename=doc.filename,
            )
            g = tree_data.get("graph", {})
            return DocumentTreeDataResponse(
                nodes=[DocumentTreeNodeSchema(**n) for n in g.get("nodes", [])],
                links=[DocumentTreeLinkSchema(**l) for l in g.get("links", [])],
            )

        cluster_keys = ["cluster_ingestion", "cluster_retrieval", "cluster_evaluation", "cluster_security"]
        section_id_map = {}

        for idx, sec in enumerate(sections):
            lvl = 1 if sec.section_level <= 1 else 2
            cluster = cluster_keys[idx % len(cluster_keys)]
            node_id = f"sec_{sec.id}"
            section_id_map[sec.id] = node_id

            nodes.append(
                DocumentTreeNodeSchema(
                    id=node_id,
                    label=sec.section_title,
                    level=lvl,
                    topic_cluster=cluster,
                    panel_payload=f"Section: {sec.section_title}\nLevel: {sec.section_level}\nPages: {sec.start_page}-{sec.end_page}",
                )
            )

            # Link H1 to Root, or H2 to parent H1
            if lvl == 1 or not sec.parent_section_id:
                links.append(DocumentTreeLinkSchema(source="node_root", target=node_id))
            else:
                parent_node_id = section_id_map.get(sec.parent_section_id, "node_root")
                links.append(DocumentTreeLinkSchema(source=parent_node_id, target=node_id))

        # Flashcards (Level 3)
        deck = db.query(FlashcardDeck).filter(FlashcardDeck.document_id == document_id).first()
        if deck:
            cards = db.query(Flashcard).filter(Flashcard.deck_id == deck.id).all()
            for c_idx, card in enumerate(cards):
                c_id = f"fc_{card.id}"
                c_cluster = cluster_keys[c_idx % len(cluster_keys)]
                nodes.append(
                    DocumentTreeNodeSchema(
                        id=c_id,
                        label=card.front_concept[:60],
                        level=3,
                        topic_cluster=c_cluster,
                        panel_payload=f"Concept: {card.front_concept}\n\nDefinition: {card.back_definition}\n\nCitation: {card.source_citation or 'N/A'}",
                    )
                )
                # Attach flashcard to first available section or root
                target_parent = list(section_id_map.values())[c_idx % len(section_id_map)] if section_id_map else "node_root"
                links.append(DocumentTreeLinkSchema(source=target_parent, target=c_id))

        return DocumentTreeDataResponse(nodes=nodes, links=links)

    # 2. General / Mock document tree fallback
    mock_file = Path(__file__).resolve().parents[5] / "apps" / "graph-ui" / "src" / "data" / "mock_document_tree.json"
    if mock_file.exists():
        with open(mock_file, "r", encoding="utf-8") as f:
            raw_tree = json.load(f)
            return DocumentTreeDataResponse(
                nodes=[DocumentTreeNodeSchema(**n) for n in raw_tree.get("nodes", [])],
                links=[DocumentTreeLinkSchema(**l) for l in raw_tree.get("links", [])],
            )

    # 3. Minimal procedural tree if file is not found
    return DocumentTreeDataResponse(
        nodes=[
            DocumentTreeNodeSchema(
                id="node_root",
                label="VERITAS: Research Intelligence",
                level=0,
                topic_cluster="cluster_foundation",
                panel_payload="VERITAS Research Intelligence Platform Root Node.",
            )
        ],
        links=[],
    )



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
    Guarantees atomic transaction integrity and robust error recovery.
    """
    storage_path = None
    try:
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
            
            # Build immediate hierarchical graph & evidence for dynamic explorer sync
            try:
                tree_payload = pdf_parser_service.extract_document_tree_and_hierarchy(
                    file_path=existing_doc.storage_path,
                    document_id=existing_doc.id,
                    filename=existing_doc.filename,
                )
            except Exception as tree_err:
                tree_payload = {
                    "graph": {"nodes": [], "links": []},
                    "hierarchy": [],
                    "evidence": [],
                }

            return DocumentUploadResponse(
                document=DocumentOut.model_validate(existing_doc),
                job=DocumentProcessingJobOut.model_validate(job) if job else None,
                message="Document already exists and is fully processed.",
                document_id=existing_doc.id,
                filename=existing_doc.filename,
                graph=tree_payload.get("graph"),
                hierarchy=tree_payload.get("hierarchy"),
                evidence=tree_payload.get("evidence"),
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

        # Extract immediate hierarchical graph, nodes, links, and evidence for client UI
        try:
            tree_payload = pdf_parser_service.extract_document_tree_and_hierarchy(
                file_path=storage_path,
                document_id=document.id,
                filename=sanitized_name,
            )
        except Exception as tree_err:
            tree_payload = {
                "graph": {"nodes": [], "links": []},
                "hierarchy": [],
                "evidence": [],
            }

        return DocumentUploadResponse(
            document=DocumentOut.model_validate(document),
            job=DocumentProcessingJobOut.model_validate(job),
            message="Document uploaded successfully and queued for extraction.",
            document_id=document.id,
            filename=sanitized_name,
            graph=tree_payload.get("graph"),
            hierarchy=tree_payload.get("hierarchy"),
            evidence=tree_payload.get("evidence"),
        )
    except HTTPException:
        db.rollback()
        if storage_path:
            storage_service.delete_file(storage_path)
        raise
    except Exception as exc:
        db.rollback()
        if storage_path:
            storage_service.delete_file(storage_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process document upload: {str(exc)}",
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
@router.get("/", response_model=List[DocumentOut])
def list_documents(
    workspace_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Lists documents accessible to the authenticated user with optional workspace and status filters.
    If a document has no specific workspace_id assigned, it is visible across the user's workspaces.
    """
    query = db.query(Document).options(
        joinedload(Document.doc_metadata),
        joinedload(Document.processing_jobs)
    ).filter(Document.user_id == current_user.id)

    if workspace_id:
        query = query.filter((Document.workspace_id == workspace_id) | (Document.workspace_id == None))
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
    
    # Phase 14: Document Access Audit Trail (COMP-01)
    audit_service.log_document_access(
        document_id=doc.id,
        action=DocumentAuditAction.VIEW.value,
        workspace_id=doc.workspace_id,
        user_id=current_user.id,
    )

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

    # Phase 14: Document Access Audit Trail (COMP-01)
    audit_service.log_document_access(
        document_id=doc.id,
        action=DocumentAuditAction.DOWNLOAD.value,
        workspace_id=doc.workspace_id,
        user_id=current_user.id,
    )

    return FileResponse(
        path=doc.storage_path,
        filename=doc.filename,
        media_type="application/pdf"
    )
