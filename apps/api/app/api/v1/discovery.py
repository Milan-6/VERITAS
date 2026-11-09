import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, verify_document_access
from app.models.document import Document
from app.models.user import User
from app.schemas.discovery import (
    CitationNetworkResponse,
    DirectIngestRequest,
    DirectIngestResponse,
    DiscoverySearchResponse,
)
from app.services.discovery import external_discovery_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/discovery", tags=["Academic Research Discovery"])


@router.get("/search", response_model=DiscoverySearchResponse)
def search_global_literature(
    query: str = Query(..., min_length=1, description="Keywords or topic to search across global literature"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=50, description="Results per page"),
    author: Optional[str] = Query(None, description="Filter by author name"),
    year: Optional[int] = Query(None, description="Filter by publication year"),
    current_user: User = Depends(get_current_user),
):
    """
    Searches global scientific literature via OpenAlex with metadata normalization,
    rate-limit compliance, and caching.
    """
    return external_discovery_service.search_works(
        query=query,
        page=page,
        per_page=per_page,
        author=author,
        year=year,
    )


@router.post("/ingest", response_model=DirectIngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_paper(
    payload: DirectIngestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Directly ingests an open-access paper into the user's workspace via DOI or PDF URL.
    Enforces SSRF prevention, magic bytes validation, and kicks off background processing.
    """
    return await external_discovery_service.download_and_ingest_paper(
        doi_or_url=payload.doi_or_url,
        current_user=current_user,
        db=db,
        workspace_id=payload.workspace_id,
        title_override=payload.title,
    )


@router.get("/citations/{document_id}", response_model=CitationNetworkResponse)
def get_citation_network(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Fetches outbound references, inbound citations, and related literature
    for a specific document in the user's workspace.
    """
    doc = verify_document_access(document_id, current_user, db, require_write=False)
    title = doc.doc_metadata.title if doc.doc_metadata and doc.doc_metadata.title else doc.filename
    doi = doc.doc_metadata.doi if doc.doc_metadata and doc.doc_metadata.doi else None

    return external_discovery_service.get_citation_network(
        document_id=doc.id,
        document_title=title,
        doi=doi,
    )
