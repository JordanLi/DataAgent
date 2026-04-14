"""Step 11 API 测试 — Auth 路由（login / register / me + JWT + RBAC）。"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.audit import AuditLog
from sqlalchemy import select

pytestmark = pytest.mark.asyncio


# ═══════════════════════════════════════════════════════════
# 注册 (RBAC)
# ═══════════════════════════════════════════════════════════

async def test_register_success_as_admin(client):
    """Admin can register new users."""
    resp = await client.post("/api/auth/register", json={
        "username": "alice", "password": "password123", "role": "analyst"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "alice"
    assert data["role"] == "analyst"
    assert "password" not in data
    assert "password_hash" not in data


async def test_register_requires_admin(unauth_client, analyst_client, viewer_client):
    """Unauth, Analyst, and Viewer cannot register new users."""
    payload = {"username": "hack_user", "password": "pwd", "role": "admin"}
    
    resp = await unauth_client.post("/api/auth/register", json=payload)
    assert resp.status_code == 401

    resp = await analyst_client.post("/api/auth/register", json=payload)
    assert resp.status_code == 403

    resp = await viewer_client.post("/api/auth/register", json=payload)
    assert resp.status_code == 403


async def test_register_duplicate_username(client):
    payload = {"username": "bob", "password": "password123", "role": "analyst"}
    await client.post("/api/auth/register", json=payload)
    resp = await client.post("/api/auth/register", json=payload)
    assert resp.status_code == 409


async def test_register_default_role_analyst(client):
    resp = await client.post("/api/auth/register", json={
        "username": "carol", "password": "password123"
    })
    assert resp.status_code == 201
    assert resp.json()["role"] == "analyst"


# ═══════════════════════════════════════════════════════════
# 登录
# ═══════════════════════════════════════════════════════════

async def test_login_success(client, unauth_client, db_session: AsyncSession):
    # Setup user
    await client.post("/api/auth/register", json={
        "username": "dave", "password": "mypassword1"
    })
    
    resp = await unauth_client.post("/api/auth/login", json={
        "username": "dave", "password": "mypassword1"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Check that audit log was created
    audit_res = await db_session.execute(select(AuditLog).where(AuditLog.action == "login"))
    logs = audit_res.scalars().all()
    assert len(logs) >= 1
    assert logs[-1].action == "login"


async def test_login_wrong_password(client, unauth_client):
    await client.post("/api/auth/register", json={
        "username": "eve", "password": "correct_pw"
    })
    resp = await unauth_client.post("/api/auth/login", json={
        "username": "eve", "password": "wrong_pw"
    })
    assert resp.status_code == 401


async def test_login_nonexistent_user(unauth_client):
    resp = await unauth_client.post("/api/auth/login", json={
        "username": "nobody", "password": "anypass1"
    })
    assert resp.status_code == 401


async def test_login_disabled_user(client, unauth_client, db_session: AsyncSession):
    # Setup user
    from app.auth import hash_password
    banned_user = User(
        username="banned_user",
        password_hash=hash_password("pwd"),
        role="viewer",
        is_active=False
    )
    db_session.add(banned_user)
    await db_session.commit()

    resp = await unauth_client.post("/api/auth/login", json={
        "username": "banned_user", "password": "pwd"
    })
    assert resp.status_code == 403
    assert "已禁用" in resp.json()["detail"]


# ═══════════════════════════════════════════════════════════
# /me — 需要 Bearer Token
# ═══════════════════════════════════════════════════════════

async def test_me_returns_current_user(client, unauth_client):
    await client.post("/api/auth/register", json={
        "username": "frank", "password": "passw0rd!"
    })
    login = await unauth_client.post("/api/auth/login", json={
        "username": "frank", "password": "passw0rd!"
    })
    token = login.json()["access_token"]

    resp = await unauth_client.get("/api/auth/me",
                            headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "frank"


async def test_me_without_token_returns_401(unauth_client):
    resp = await unauth_client.get("/api/auth/me")
    assert resp.status_code == 401


async def test_me_with_invalid_token_returns_401(unauth_client):
    resp = await unauth_client.get("/api/auth/me",
                            headers={"Authorization": "Bearer invalid.token.here"})
    assert resp.status_code == 401
