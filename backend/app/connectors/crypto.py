"""Symmetric encryption helpers for storing datasource passwords at rest.

Uses Fernet (AES-128-CBC + HMAC-SHA256) from the cryptography library.
The encryption key is derived from JWT_SECRET via PBKDF2-HMAC-SHA256 so that
a single application secret secures both JWT tokens and stored credentials.
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

from app.config import get_settings

# A fixed salt is acceptable here because we are deriving a *symmetric wrapping
# key*, not hashing a user password.  The security comes from the secrecy of
# JWT_SECRET, not the salt.
_SALT = b"dataagent-connector-key-v1"


def _get_fernet() -> Fernet:
    secret = get_settings().jwt_secret.encode()
    raw_key = hashlib.pbkdf2_hmac(
        "sha256",
        secret,
        _SALT,
        iterations=100_000,
        dklen=32,
    )
    b64_key = base64.urlsafe_b64encode(raw_key)
    return Fernet(b64_key)


def encrypt_password(plain: str) -> str:
    """Return a URL-safe base64 Fernet token for *plain*."""
    return _get_fernet().encrypt(plain.encode()).decode()


def decrypt_password(token: str) -> str:
    """Decrypt a previously encrypted password token."""
    return _get_fernet().decrypt(token.encode()).decode()
