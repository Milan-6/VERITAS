import base64
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.models.document import Document
from app.models.workspace import Workspace, WorkspaceMember, DocumentWorkspaceAssociation

bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256 with a random salt."""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return base64.b64encode(salt + key).decode("ascii")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against stored PBKDF2 hash."""
    try:
        decoded = base64.b64decode(hashed_password.encode("ascii"))
        salt = decoded[:16]
        key = decoded[16:]
        new_key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, 100000)
        return hmac.compare_digest(key, new_key)
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    payload = {
        **to_encode,
        "exp": int(expire.timestamp()),
        "iat": int(datetime.utcnow().timestamp()),
    }
    
    # Simple, zero-external-dependency standard JWT HS256 encoder
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b'=').decode('ascii')
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b'=').decode('ascii')
    
    signing_input = f"{header_b64}.{payload_b64}".encode('ascii')
    signature = hmac.new(settings.SECRET_KEY.encode('ascii'), signing_input, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).rstrip(b'=').decode('ascii')
    
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> dict:
    """Decode and verify a signed JWT token."""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            raise ValueError("Invalid token format")
            
        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode('ascii')
        expected_sig = hmac.new(settings.SECRET_KEY.encode('ascii'), signing_input, hashlib.sha256).digest()
        
        # Add padding back if necessary
        sig_padding = 4 - (len(sig_b64) % 4)
        if sig_padding != 4:
            sig_b64 += '=' * sig_padding
        actual_sig = base64.urlsafe_b64decode(sig_b64.encode('ascii'))
        
        if not hmac.compare_digest(expected_sig, actual_sig):
            raise ValueError("Signature verification failed")
            
        payload_padding = 4 - (len(payload_b64) % 4)
        if payload_padding != 4:
            payload_b64 += '=' * payload_padding
        payload_json = base64.urlsafe_b64decode(payload_b64.encode('ascii')).decode('utf-8')
        payload = json.loads(payload_json)
        
        if payload.get("exp", 0) < time.time():
            raise ValueError("Token expired")
            
        return payload
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Dependency to retrieve authenticated user from Bearer token."""
    if not auth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = decode_access_token(auth.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload: missing sub",
        )
        
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )
    return user


def verify_document_access(
    document_id: str,
    user: User,
    db: Session,
    require_write: bool = False
) -> Document:
    """
    Enforces strict tenant and workspace-level authorization on documents (SEC-01, SEC-06).
    1. Returns document if user is direct owner.
    2. Returns document if user has access via workspace association.
    3. Raises 404 (or 403) to prevent IDOR and document discovery attacks.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    
    # Direct owner
    if doc.user_id == user.id:
        return doc
        
    # Check workspace permissions
    if doc.workspace_id:
        ws = db.query(Workspace).filter(Workspace.id == doc.workspace_id).first()
        if ws:
            # Workspace owner has full access
            if ws.owner_id == user.id:
                return doc

            # Workspace member check
            member = db.query(WorkspaceMember).filter(
                WorkspaceMember.workspace_id == doc.workspace_id,
                WorkspaceMember.user_id == user.id,
            ).first()
            if member:
                if require_write and member.role.upper() not in ["OWNER", "EDITOR"]:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Insufficient permissions to modify this document in this workspace",
                    )
                return doc

        assoc = db.query(DocumentWorkspaceAssociation).filter(
            DocumentWorkspaceAssociation.document_id == document_id,
            DocumentWorkspaceAssociation.workspace_id == doc.workspace_id,
        ).first()
        
        if assoc:
            if require_write and assoc.access_role not in ["owner", "editor"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions to modify this document",
                )
            return doc
            
    # Denied
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Document not found",
    )
