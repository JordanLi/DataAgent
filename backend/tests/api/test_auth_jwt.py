"""Unit tests for JWT handler and password utilities.

Pure logic tests — no DB, no HTTP.
"""

from __future__ import annotations

import pytest
import jwt as pyjwt

from app.auth.jwt_handler import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
)
from app.config import get_settings


# ---------------------------------------------------------------------------
# 密码工具
# ---------------------------------------------------------------------------

class TestPassword:

    def test_hash_is_not_plain(self):
        h = hash_password("secret123")
        assert h != "secret123"

    def test_verify_correct_password(self):
        h = hash_password("correct_pass")
        assert verify_password("correct_pass", h) is True

    def test_verify_wrong_password(self):
        h = hash_password("correct_pass")
        assert verify_password("wrong_pass", h) is False

    def test_two_hashes_differ(self):
        """bcrypt 每次加盐，同一明文哈希值应不同。"""
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2

    def test_verify_bad_hash_returns_false(self):
        assert verify_password("any", "not-a-valid-hash") is False


# ---------------------------------------------------------------------------
# JWT 签发与解码
# ---------------------------------------------------------------------------

class TestJWT:

    def test_token_is_string(self):
        token = create_access_token(1, "alice", "admin")
        assert isinstance(token, str)
        assert len(token) > 20

    def test_decode_recovers_claims(self):
        token = create_access_token(42, "bob", "analyst")
        payload = decode_token(token)
        assert payload["sub"] == "42"
        assert payload["username"] == "bob"
        assert payload["role"] == "analyst"

    def test_expired_token_raises(self):
        """手动签发一个已过期的 token。"""
        settings = get_settings()
        import time
        payload = {
            "sub": "1",
            "username": "x",
            "role": "viewer",
            "exp": int(time.time()) - 1,  # 已过期
        }
        token = pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            decode_token(token)
        assert exc_info.value.status_code == 401
        assert "过期" in exc_info.value.detail

    def test_invalid_token_raises(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            decode_token("this.is.not.a.valid.token")
        assert exc_info.value.status_code == 401

    def test_tampered_token_raises(self):
        from fastapi import HTTPException
        token = create_access_token(1, "alice", "admin")
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(HTTPException):
            decode_token(tampered)
