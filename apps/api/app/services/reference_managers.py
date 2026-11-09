import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document, DocumentMetadata, DocumentStatus
from app.models.integration import IntegrationCredential
from app.models.workspace import Workspace
from app.services.discovery import validate_safe_url
from app.services.webhook_dispatcher import webhook_dispatcher

logger = logging.getLogger(__name__)

ZOTERO_API_BASE = "https://api.zotero.org"


class ZoteroIntegrationService:
    """
    Connects to the Zotero Web API (v3) to verify credentials, retrieve user
    collections, and synchronize academic reference items into the VERITAS
    workspace.
    """

    def verify_credentials(self, api_key: str, user_id: str) -> Dict[str, Any]:
        """Verifies API key and user ID against the Zotero API."""
        endpoint = f"{ZOTERO_API_BASE}/users/{user_id}/items?limit=1"
        headers = {
            "Zotero-API-Key": api_key,
            "Zotero-API-Version": "3",
            "User-Agent": "VERITAS-Research-Platform/1.0",
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(endpoint, headers=headers)
                if resp.status_code == 200:
                    total_results = resp.headers.get("Total-Results", "0")
                    return {
                        "valid": True,
                        "user_id": user_id,
                        "total_items": int(total_results) if total_results.isdigit() else 0,
                    }
                elif resp.status_code in (401, 403):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid Zotero API Key or User ID.",
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Zotero API error: HTTP {resp.status_code}",
                    )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Could not reach Zotero API: {str(e)}",
            )

    def fetch_items(
        self,
        api_key: str,
        user_id: str,
        collection_key: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Fetches reference items from the user's Zotero library."""
        if collection_key:
            endpoint = f"{ZOTERO_API_BASE}/users/{user_id}/collections/{collection_key}/items"
        else:
            endpoint = f"{ZOTERO_API_BASE}/users/{user_id}/items"

        headers = {
            "Zotero-API-Key": api_key,
            "Zotero-API-Version": "3",
            "User-Agent": "VERITAS-Research-Platform/1.0",
        }
        params = {"limit": limit, "format": "json"}

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(endpoint, headers=headers, params=params)
                if resp.status_code != 200:
                    logger.error(f"Zotero API items error: {resp.status_code} - {resp.text}")
                    return []
                return resp.json()
        except Exception as e:
            logger.error(f"Failed to fetch Zotero items: {e}")
            return []

    def sync_zotero_library(
        self,
        credential: IntegrationCredential,
        workspace_id: str,
        user_id: str,
        db: Session,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Synchronizes Zotero library items into VERITAS document catalog and
        emits 'document.ingested' events for new items.
        """
        api_key = credential.get_api_key()
        external_user_id = credential.external_user_id

        if not api_key or not external_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Zotero credentials are incomplete or missing API key / user ID.",
            )

        items = self.fetch_items(api_key=api_key, user_id=external_user_id, limit=limit)
        synced_count = 0
        created_count = 0
        skipped_count = 0

        for raw_item in items:
            data = raw_item.get("data", {})
            item_type = data.get("itemType", "")
            title = data.get("title", "").strip()

            # Skip attachments or notes without standalone titles
            if not title or item_type in ("attachment", "note"):
                skipped_count += 1
                continue

            synced_count += 1

            # Check if document already exists by title in this workspace
            existing = (
                db.query(Document)
                .join(DocumentMetadata)
                .filter(
                    Document.workspace_id == workspace_id,
                    DocumentMetadata.title == title,
                )
                .first()
            )
            if existing:
                skipped_count += 1
                continue

            # Extract authors from creators
            creators = data.get("creators", [])
            authors: List[str] = []
            for c in creators:
                first = c.get("firstName", "")
                last = c.get("lastName", "")
                name = c.get("name", "")
                full = f"{first} {last}".strip() if (first or last) else name
                if full:
                    authors.append(full)

            abstract = data.get("abstractNote", "")
            doi = data.get("DOI", None)
            pub_date = data.get("date", None)
            venue = data.get("publicationTitle") or data.get("proceedingsTitle") or data.get("university")

            # Create Document entity
            doc_id = str(uuid.uuid4())
            sanitized_fname = f"Zotero_{raw_item.get('key', doc_id[:8])}.pdf"
            new_doc = Document(
                id=doc_id,
                user_id=user_id,
                workspace_id=workspace_id,
                filename=sanitized_fname,
                storage_path=f"storage/zotero/{doc_id}.pdf",
                file_size_bytes=1024,
                mime_type="application/pdf",
                file_hash_sha256=f"zotero_{raw_item.get('key', doc_id)}",
                status=DocumentStatus.COMPLETED.value,
            )
            db.add(new_doc)
            db.flush()

            new_meta = DocumentMetadata(
                document_id=doc_id,
                title=title,
                authors=authors,
                abstract=abstract,
                publication_date=pub_date,
                doi=doi,
                journal_or_conference=venue,
                raw_metadata=data,
            )
            db.add(new_meta)
            created_count += 1

            # Dispatch document.ingested event for each imported item
            webhook_dispatcher.dispatch_event(
                event_name="document.ingested",
                workspace_id=workspace_id,
                payload={
                    "document_id": doc_id,
                    "title": title,
                    "source": "zotero",
                    "zotero_key": raw_item.get("key"),
                    "authors": authors,
                    "doi": doi,
                },
                db=db,
            )

        db.commit()

        return {
            "status": "success",
            "provider": "zotero",
            "total_items_fetched": len(items),
            "synced_references": synced_count,
            "documents_created": created_count,
            "skipped_or_existing": skipped_count,
        }


class MendeleyIntegrationService:
    """
    Interface connector for Mendeley Academic Reference Manager OAuth and library sync.
    """

    def get_authorization_url(self, client_id: str, redirect_uri: str) -> str:
        return f"https://api.mendeley.com/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope=all"

    def sync_library(
        self,
        credential: IntegrationCredential,
        workspace_id: str,
        user_id: str,
        db: Session,
    ) -> Dict[str, Any]:
        """Stub for Mendeley library synchronization."""
        return {
            "status": "stub",
            "provider": "mendeley",
            "message": "Mendeley OAuth connector interface initialized.",
            "documents_created": 0,
        }


zotero_service = ZoteroIntegrationService()
mendeley_service = MendeleyIntegrationService()
