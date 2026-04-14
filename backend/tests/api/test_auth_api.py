"""Step 8 API 测试 — Auth 路由（login / register / me）。"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.asyncio


# ═══════════════════════════════════════════════════════════
# 注册
# ═══════════════════════════════════════════════════════════

async def test_register_success(client):
    resp = await client.post("/api/auth/register", json={
        "username": "alice", "password": "password123", "role": "analyst"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "alice"
    assert data["role"] == "analyst"
    assert "password" not in data
    assert "password_hash" not in data


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

async def test_login_success(client):
    await client.post("/api/auth/register", json={
        "username": "dave", "password": "mypassword1"
    })
    resp = await client.post("/api/auth/login", json={
        "username": "dave", "password": "mypassword1"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(client):
    await client.post("/api/auth/register", json={
        "username": "eve", "password": "correct_pw"
    })
    resp = await client.post("/api/auth/login", json={
        "username": "eve", "password": "wrong_pw"
    })
    assert resp.status_code == 401


async def test_login_nonexistent_user(client):
    resp = await client.post("/api/auth/login", json={
        "username": "nobody", "password": "anypass1"
    })
    assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════
# /me — 需要 Bearer Token
# ═══════════════════════════════════════════════════════════

async def test_me_returns_current_user(client):
    await client.post("/api/auth/register", json={
        "username": "frank", "password": "passw0rd!"
    })
    login = await client.post("/api/auth/login", json={
        "username": "frank", "password": "passw0rd!"
    })
    token = login.json()["access_token"]

    resp = await client.get("/api/auth/me",
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
