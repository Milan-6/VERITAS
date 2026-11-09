import base64
import hashlib
import logging
from cryptography.fernet import Fernet
from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_fernet_cipher() -> Fernet:
    """Derives a deterministic 32-byte Fernet key from settings.SECRET_KEY."""
    raw_key = settings.SECRET_KEY.encode("utf-8")
    derived_32 = hashlib.sha256(raw_key).digest()
    b64_key = base64.urlsafe_b64encode(derived_32)
    return Fernet(b64_key)


def encrypt_secret(plain_text: str) -> str:
    """Encrypts a plaintext string (e.g. API key) into a Fernet ciphertext string."""
    if not plain_text:
        return ""
    cipher = _get_fernet_cipher()
    token = cipher.encrypt(plain_text.encode("utf-8"))
    return token.decode("ascii")


def decrypt_secret(cipher_text: str) -> str:
    """Decrypts a Fernet ciphertext string back into the original plaintext."""
    if not cipher_text:
        return ""
    cipher = _get_fernet_cipher()
    plain_bytes = cipher.decrypt(cipher_text.encode("ascii"))
    return plain_bytes.decode("utf-8")
