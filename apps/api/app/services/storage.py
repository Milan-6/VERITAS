import hashlib
import os
import re
import uuid
from pathlib import Path
from typing import Tuple
from fastapi import UploadFile, HTTPException, status
from app.core.config import settings

# PDF magic bytes signature: %PDF- (hex: 25 50 44 46 2D)
PDF_MAGIC_BYTES = b"%PDF-"

def sanitize_filename(filename: str) -> str:
    """
    Sanitize client filename to prevent path traversal, null bytes,
    and dangerous shell characters.
    """
    # Remove directory separators
    filename = os.path.basename(filename)
    # Strip null bytes
    filename = filename.replace("\x00", "")
    # Remove dangerous characters, allow alphanumerics, dots, hyphens, underscores, spaces
    filename = re.sub(r'[^a-zA-Z0-9._\-\s()]', '_', filename).strip()
    if not filename or filename == ".pdf":
        filename = f"document_{uuid.uuid4().hex[:8]}.pdf"
    return filename


class StorageService:
    def __init__(self, storage_dir: Path = settings.STORAGE_DIR):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    async def validate_and_save_upload(
        self, upload_file: UploadFile
    ) -> Tuple[str, str, int, str]:
        """
        Validates uploaded file against security constraints:
        1. File extension validation.
        2. MIME type check.
        3. File size limit (0 < size <= MAX_UPLOAD_SIZE_BYTES).
        4. PDF Magic Bytes file signature check.
        5. Computes SHA-256 hash.
        6. Saves file securely using an isolated UUID name.

        Returns: (sanitized_original_filename, absolute_storage_path, file_size_bytes, sha256_hash)
        """
        original_name = upload_file.filename or "unknown.pdf"
        sanitized_name = sanitize_filename(original_name)

        # 1. Extension check
        ext = os.path.splitext(sanitized_name)[1].lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file extension '{ext}'. Only .pdf files are accepted.",
            )

        # 2. Content-type check
        content_type = upload_file.content_type or ""
        if content_type.lower() not in settings.ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid MIME type '{content_type}'. Expected 'application/pdf'.",
            )

        # Read initial chunk to verify magic bytes
        first_chunk = await upload_file.read(1024)
        if len(first_chunk) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file rejected: upload size is 0 bytes.",
            )

        # 4. Check PDF magic bytes (%PDF-)
        if not first_chunk.startswith(PDF_MAGIC_BYTES):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Malformed file: Missing valid PDF header signature (%PDF-).",
            )

        # Generate secure isolated storage filename
        storage_uuid = str(uuid.uuid4())
        dest_filename = f"{storage_uuid}.pdf"
        dest_path = self.storage_dir / dest_filename

        # Stream save while hashing and measuring size
        hasher = hashlib.sha256()
        total_size = len(first_chunk)
        hasher.update(first_chunk)

        try:
            with open(dest_path, "wb") as f:
                f.write(first_chunk)
                while True:
                    chunk = await upload_file.read(64 * 1024)  # 64KB chunks
                    if not chunk:
                        break
                    total_size += len(chunk)
                    if total_size > settings.MAX_UPLOAD_SIZE_BYTES:
                        # Exceeded size limit, clean up
                        f.close()
                        if dest_path.exists():
                            dest_path.unlink()
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_BYTES // (1024*1024)}MB.",
                        )
                    hasher.update(chunk)
                    f.write(chunk)
        except HTTPException:
            raise
        except Exception as e:
            if dest_path.exists():
                dest_path.unlink()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to persist file: {str(e)}",
            )

        sha256_hash = hasher.hexdigest()
        return sanitized_name, str(dest_path.resolve()), total_size, sha256_hash

    def save_pdf_bytes(self, content: bytes, original_filename: str) -> Tuple[str, str, int, str]:
        """
        Validates and securely persists raw PDF bytes from an external download.
        Enforces size limits, magic bytes validation, and SHA-256 hashing.
        Returns: (sanitized_name, storage_path, file_size, sha256_hash)
        """
        if not original_filename.lower().endswith(".pdf"):
            original_filename = f"{original_filename}.pdf"
        sanitized_name = sanitize_filename(original_filename)

        total_size = len(content)
        if total_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file rejected: downloaded size is 0 bytes.",
            )

        if total_size > settings.MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_BYTES // (1024*1024)}MB.",
            )

        if not content.startswith(PDF_MAGIC_BYTES):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Malformed file: Missing valid PDF header signature (%PDF-).",
            )

        storage_uuid = str(uuid.uuid4())
        dest_filename = f"{storage_uuid}.pdf"
        dest_path = self.storage_dir / dest_filename

        with open(dest_path, "wb") as f:
            f.write(content)

        sha256_hash = hashlib.sha256(content).hexdigest()
        return sanitized_name, str(dest_path.resolve()), total_size, sha256_hash

    def delete_file(self, file_path: str) -> bool:
        """Safely removes a stored file."""
        try:
            p = Path(file_path)
            if p.exists() and p.is_file():
                p.unlink()
                return True
        except Exception:
            pass
        return False


storage_service = StorageService()
