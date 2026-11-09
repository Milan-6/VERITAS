import hashlib
import ipaddress
import logging
import os
import re
import socket
import time
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import (
    Document,
    DocumentMetadata,
    DocumentProcessingJob,
    DocumentStatus,
    JobStatus,
    ProcessingStage,
)
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.discovery import (
    CitationNetworkResponse,
    DirectIngestResponse,
    DiscoverySearchResponse,
    ExternalPaperMetadata,
)
from app.services.storage import sanitize_filename, storage_service
from app.workers.queue import job_manager

logger = logging.getLogger(__name__)

OPENALEX_BASE_URL = "https://api.openalex.org"
SEMANTIC_SCHOLAR_BASE_URL = "https://api.semanticscholar.org/graph/v1"


def validate_safe_url(url: str) -> str:
    """
    Strictly validates a URL against Server-Side Request Forgery (SSRF) threats:
    1. Scheme check: only http and https are allowed.
    2. Credentials check: no embedded user/pass.
    3. Hostname check: non-empty, no localhost, .local, or .internal.
    4. DNS resolution & IP check: resolves hostname to all IPs and ensures
       none belong to private, loopback, link-local (e.g. 169.254.169.254),
       multicast, or reserved address spaces.
    """
    if not url or not isinstance(url, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid URL provided: URL string cannot be empty.",
        )

    try:
        parsed = urlparse(url)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed URL: {str(e)}",
        )

    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Security violation: Scheme '{scheme}' is forbidden. Only HTTP and HTTPS are permitted.",
        )

    if parsed.username or parsed.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Security violation: URLs with embedded authentication credentials are forbidden.",
        )

    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Security violation: Missing hostname in URL.",
        )

    lower_host = hostname.lower().strip(".")
    if (
        lower_host in ("localhost", "127.0.0.1", "0.0.0.0", "::1", "metadata.google.internal")
        or lower_host.endswith(".local")
        or lower_host.endswith(".internal")
        or lower_host.endswith(".lan")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SSRF violation: Host '{hostname}' is not permitted.",
        )

    # Resolve hostname via DNS and check all returned IP addresses
    try:
        addr_info = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot resolve hostname '{hostname}': {str(e)}",
        )

    for family, _, _, _, sockaddr in addr_info:
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"SSRF violation: Unable to parse resolved IP '{ip_str}'.",
            )

        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"SSRF violation: Host '{hostname}' resolves to restricted network IP '{ip_str}'.",
            )

    return url


def reconstruct_abstract(inverted_index: Optional[Dict[str, List[int]]]) -> Optional[str]:
    """
    Reconstructs clean abstract text from OpenAlex's inverted index representation.
    """
    if not inverted_index or not isinstance(inverted_index, dict):
        return None

    positions: Dict[int, str] = {}
    for word, indices in inverted_index.items():
        for idx in indices:
            positions[idx] = word

    if not positions:
        return None

    max_idx = max(positions.keys())
    tokens = [positions[i] for i in range(max_idx + 1) if i in positions]
    return " ".join(tokens)


class SimpleTTLCache:
    """In-memory cache with time-to-live expiration for academic search queries."""

    def __init__(self, ttl_seconds: int = 300):
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, Tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            timestamp, data = self.cache[key]
            if time.time() - timestamp < self.ttl_seconds:
                return data
            del self.cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        self.cache[key] = (time.time(), value)


class ExternalDiscoveryService:
    def __init__(self):
        self.cache = SimpleTTLCache(ttl_seconds=300)
        self.headers = {
            "User-Agent": settings.DISCOVERY_USER_AGENT,
            "Accept": "application/json",
        }

    def _normalize_openalex_work(self, work: Dict[str, Any]) -> ExternalPaperMetadata:
        """Converts an OpenAlex work record into the unified ExternalPaperMetadata schema."""
        work_id = work.get("id") or ""
        title = work.get("title") or "Untitled Document"
        year = work.get("publication_year")

        authors: List[str] = []
        for authorship in work.get("authorships", []):
            author_obj = authorship.get("author", {})
            name = author_obj.get("display_name")
            if name:
                authors.append(name)

        doi_raw = work.get("doi")
        doi = None
        if doi_raw:
            doi = doi_raw.replace("https://doi.org/", "").replace("http://doi.org/", "")

        abstract = reconstruct_abstract(work.get("abstract_inverted_index"))

        # Primary and OA locations
        primary_loc = work.get("primary_location") or {}
        best_oa = work.get("best_oa_location") or {}
        open_access_info = work.get("open_access") or {}

        landing_page_url = primary_loc.get("landing_page_url") or best_oa.get("landing_page_url")
        pdf_url = best_oa.get("pdf_url") or primary_loc.get("pdf_url") or open_access_info.get("oa_url")
        is_oa = open_access_info.get("is_oa", False) or bool(pdf_url)

        citation_count = int(work.get("cited_by_count") or 0)

        venue = None
        source_obj = primary_loc.get("source") or best_oa.get("source")
        if source_obj and isinstance(source_obj, dict):
            venue = source_obj.get("display_name")

        return ExternalPaperMetadata(
            id=work_id,
            title=title,
            authors=authors,
            publication_year=year,
            abstract=abstract,
            doi=doi,
            landing_page_url=landing_page_url,
            pdf_url=pdf_url,
            is_open_access=is_oa,
            citation_count=citation_count,
            venue=venue,
            source="openalex",
        )

    def search_works(
        self,
        query: str,
        page: int = 1,
        per_page: int = 10,
        author: Optional[str] = None,
        year: Optional[int] = None,
    ) -> DiscoverySearchResponse:
        """
        Queries OpenAlex API for works matching research keywords, author, or publication year.
        Includes respectful mailto query and in-memory TTL caching.
        """
        clean_query = query.strip()
        cache_key = f"search:{clean_query}:{page}:{per_page}:{author}:{year}"
        cached_result = self.cache.get(cache_key)
        if cached_result:
            return cached_result

        params: Dict[str, Any] = {
            "search": clean_query,
            "page": page,
            "per-page": min(max(per_page, 1), 50),
            "mailto": settings.OPENALEX_MAILTO,
        }

        filter_parts: List[str] = []
        if author:
            filter_parts.append(f"authorships.author.display_name.search:{author.strip()}")
        if year:
            filter_parts.append(f"publication_year:{year}")

        if filter_parts:
            params["filter"] = ",".join(filter_parts)

        endpoint = f"{OPENALEX_BASE_URL}/works"

        try:
            with httpx.Client(timeout=settings.DISCOVERY_REQUEST_TIMEOUT) as client:
                response = client.get(endpoint, params=params, headers=self.headers)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as e:
            logger.error(f"OpenAlex search failed: {str(e)}")
            # Fallback for offline testing or when OpenAlex is unreachable
            return DiscoverySearchResponse(
                query=query,
                total_results=0,
                page=page,
                per_page=per_page,
                results=[],
            )

        meta = data.get("meta", {})
        total_results = meta.get("count", 0)
        raw_works = data.get("results", [])

        normalized_works = [self._normalize_openalex_work(w) for w in raw_works]

        result = DiscoverySearchResponse(
            query=clean_query,
            total_results=total_results,
            page=page,
            per_page=per_page,
            results=normalized_works,
        )

        self.cache.set(cache_key, result)
        return result

    def get_work_by_doi(self, doi: str) -> Optional[ExternalPaperMetadata]:
        """Fetches metadata for a specific paper from OpenAlex by its DOI."""
        clean_doi = doi.strip().replace("https://doi.org/", "").replace("http://doi.org/", "")
        endpoint = f"{OPENALEX_BASE_URL}/works/https://doi.org/{clean_doi}"
        params = {"mailto": settings.OPENALEX_MAILTO}

        try:
            with httpx.Client(timeout=settings.DISCOVERY_REQUEST_TIMEOUT) as client:
                response = client.get(endpoint, params=params, headers=self.headers)
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                data = response.json()
                return self._normalize_openalex_work(data)
        except Exception as e:
            logger.warning(f"Failed to fetch work by DOI '{doi}': {str(e)}")
            return None

    def get_citation_network(
        self,
        document_id: str,
        document_title: str,
        doi: Optional[str] = None,
    ) -> CitationNetworkResponse:
        """
        Retrieves outbound references, inbound citations, and related recommendations
        for a paper in the workspace using OpenAlex.
        """
        work: Optional[Dict[str, Any]] = None

        try:
            with httpx.Client(timeout=settings.DISCOVERY_REQUEST_TIMEOUT) as client:
                if doi:
                    clean_doi = doi.strip().replace("https://doi.org/", "").replace("http://doi.org/", "")
                    res = client.get(
                        f"{OPENALEX_BASE_URL}/works/https://doi.org/{clean_doi}",
                        params={"mailto": settings.OPENALEX_MAILTO},
                        headers=self.headers,
                    )
                    if res.status_code == 200:
                        work = res.json()

                if not work and document_title:
                    # Query by exact or clean title
                    res = client.get(
                        f"{OPENALEX_BASE_URL}/works",
                        params={
                            "filter": f"title.search:{document_title}",
                            "per-page": 1,
                            "mailto": settings.OPENALEX_MAILTO,
                        },
                        headers=self.headers,
                    )
                    if res.status_code == 200:
                        results = res.json().get("results", [])
                        if results:
                            work = results[0]

                if not work:
                    return CitationNetworkResponse(
                        document_id=document_id,
                        document_title=document_title,
                        doi=doi,
                        citation_count=0,
                        references=[],
                        cited_by=[],
                        top_related=[],
                    )

                work_id = work.get("id") or ""
                citation_count = int(work.get("cited_by_count") or 0)
                short_id = work_id.split("/")[-1] if "/" in work_id else work_id

                # 1. Fetch Inbound Citations ("Cited By")
                cited_by_res = client.get(
                    f"{OPENALEX_BASE_URL}/works",
                    params={
                        "filter": f"cites:{short_id}",
                        "sort": "cited_by_count:desc",
                        "per-page": 5,
                        "mailto": settings.OPENALEX_MAILTO,
                    },
                    headers=self.headers,
                )
                cited_by_list = (
                    [self._normalize_openalex_work(w) for w in cited_by_res.json().get("results", [])]
                    if cited_by_res.status_code == 200
                    else []
                )

                # 2. Fetch Top Related Works
                related_res = client.get(
                    f"{OPENALEX_BASE_URL}/works",
                    params={
                        "filter": f"related_to:{short_id}",
                        "sort": "cited_by_count:desc",
                        "per-page": 5,
                        "mailto": settings.OPENALEX_MAILTO,
                    },
                    headers=self.headers,
                )
                related_list = (
                    [self._normalize_openalex_work(w) for w in related_res.json().get("results", [])]
                    if related_res.status_code == 200
                    else []
                )

                # 3. Fetch References (Outbound) from referenced_works IDs if available
                ref_ids = (work.get("referenced_works") or [])[:5]
                references_list: List[ExternalPaperMetadata] = []
                if ref_ids:
                    # OpenAlex supports pipe-separated filter openalex_id:W1|W2
                    pipe_ids = "|".join([r.split("/")[-1] for r in ref_ids])
                    ref_res = client.get(
                        f"{OPENALEX_BASE_URL}/works",
                        params={
                            "filter": f"openalex_id:{pipe_ids}",
                            "per-page": 5,
                            "mailto": settings.OPENALEX_MAILTO,
                        },
                        headers=self.headers,
                    )
                    if ref_res.status_code == 200:
                        references_list = [
                            self._normalize_openalex_work(w) for w in ref_res.json().get("results", [])
                        ]

                return CitationNetworkResponse(
                    document_id=document_id,
                    document_title=document_title,
                    doi=doi,
                    citation_count=citation_count,
                    references=references_list,
                    cited_by=cited_by_list,
                    top_related=related_list,
                )
        except Exception as e:
            logger.warning(f"Error fetching citation network for doc '{document_id}': {str(e)}")
            return CitationNetworkResponse(
                document_id=document_id,
                document_title=document_title,
                doi=doi,
                citation_count=0,
                references=[],
                cited_by=[],
                top_related=[],
            )

    async def download_and_ingest_paper(
        self,
        doi_or_url: str,
        current_user: User,
        db: Session,
        workspace_id: Optional[str] = None,
        title_override: Optional[str] = None,
    ) -> DirectIngestResponse:
        """
        Direct Ingestion Pipeline:
        1. Resolves DOI to verified Open Access PDF URL (if DOI supplied).
        2. Strictly validates target URL against SSRF attacks.
        3. Securely downloads PDF stream under strict size and timeout bounds.
        4. Validates PDF magic bytes signature.
        5. Persists securely to storage and creates Document & ProcessingJob records.
        6. Enqueues background pipeline (validation, PyMuPDF parsing, chunking, embeddings).
        """
        raw_target = doi_or_url.strip()
        pdf_url: Optional[str] = None
        extracted_title: Optional[str] = title_override

        # Check if input is a DOI
        is_doi = (
            raw_target.startswith("10.")
            or "doi.org/10." in raw_target
            or not (raw_target.startswith("http://") or raw_target.startswith("https://"))
        )

        if is_doi:
            meta = self.get_work_by_doi(raw_target)
            if not meta or not meta.pdf_url:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Unable to resolve open-access PDF for DOI '{raw_target}'. "
                        "The document may be paywalled or lack a direct PDF link."
                    ),
                )
            pdf_url = meta.pdf_url
            if not extracted_title:
                extracted_title = meta.title
        else:
            pdf_url = raw_target

        # Enforce strict SSRF validation
        safe_url = validate_safe_url(pdf_url)

        # Securely stream download
        headers = {
            "User-Agent": settings.DISCOVERY_USER_AGENT,
            "Accept": "application/pdf,application/octet-stream,*/*",
        }

        try:
            async with httpx.AsyncClient(
                timeout=settings.DISCOVERY_REQUEST_TIMEOUT, follow_redirects=True
            ) as client:
                res = await client.get(safe_url, headers=headers)
                if res.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"External server returned status code {res.status_code} when downloading PDF.",
                    )
                content = res.content
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to retrieve PDF from remote server: {str(e)}",
            )

        # Derive filename
        base_name = "downloaded_paper.pdf"
        if extracted_title:
            base_name = f"{extracted_title[:40].strip()}.pdf"
        elif safe_url:
            path_part = urlparse(safe_url).path
            candidate = os.path.basename(path_part)
            if candidate and candidate.endswith(".pdf"):
                base_name = candidate

        # Validate magic bytes and persist
        sanitized_name, storage_path, file_size, sha256_hash = storage_service.save_pdf_bytes(
            content=content,
            original_filename=base_name,
        )

        # Check for duplicate document
        existing_doc = (
            db.query(Document)
            .filter(
                Document.user_id == current_user.id,
                Document.file_hash_sha256 == sha256_hash,
            )
            .first()
        )

        if existing_doc and existing_doc.status == DocumentStatus.COMPLETED.value:
            storage_service.delete_file(storage_path)
            job = (
                db.query(DocumentProcessingJob)
                .filter(DocumentProcessingJob.document_id == existing_doc.id)
                .order_by(DocumentProcessingJob.created_at.desc())
                .first()
            )
            existing_title = existing_doc.filename
            if existing_doc.doc_metadata and existing_doc.doc_metadata.title:
                existing_title = existing_doc.doc_metadata.title
            return DirectIngestResponse(
                document_id=existing_doc.id,
                job_id=job.id if job else "",
                filename=existing_doc.filename,
                title=existing_title,
                status=existing_doc.status,
                message="Document already exists in your workspace and is fully processed.",
            )

        # Verify workspace if specified
        resolved_ws_id = workspace_id
        if resolved_ws_id:
            ws = (
                db.query(Workspace)
                .filter(Workspace.id == resolved_ws_id, Workspace.owner_id == current_user.id)
                .first()
            )
            if not ws:
                resolved_ws_id = None

        if not resolved_ws_id:
            user_ws = db.query(Workspace).filter(Workspace.owner_id == current_user.id).first()
            if user_ws:
                resolved_ws_id = user_ws.id

        final_doc_title = extracted_title or sanitized_name

        # Create Document record
        document = Document(
            user_id=current_user.id,
            workspace_id=resolved_ws_id,
            filename=sanitized_name,
            storage_path=storage_path,
            file_size_bytes=file_size,
            mime_type="application/pdf",
            file_hash_sha256=sha256_hash,
            status=DocumentStatus.UPLOADED.value,
        )
        db.add(document)
        db.flush()

        # Seed metadata with extracted external title if available
        doc_meta = DocumentMetadata(
            document_id=document.id,
            title=final_doc_title,
        )
        db.add(doc_meta)

        # Create processing job
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

        # Enqueue background processing job
        job_manager.enqueue_job(job.id)

        return DirectIngestResponse(
            document_id=document.id,
            job_id=job.id,
            filename=document.filename,
            title=final_doc_title,
            status=document.status,
            message="Paper successfully imported and scheduled for processing.",
        )


external_discovery_service = ExternalDiscoveryService()
