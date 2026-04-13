"""Step 8 API 测试 — Admin 路由（用户 CRUD + 审计日志）。"""

from __future__ import annotations

import pytest
from sqlalchemy import insert

from app.models.audit import AuditLog


pytestmark = pytest.mark.asyncio


# ═══════════════════════════════════════════════════════════
# 用户 CRUD
# ═══════════════════════════════════════════════════════════

async def test_list_users_empty(client):
    resp = await client.get("/api/admin/users")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_create_user(client):
    resp = await client.post("/api/admin/users", json={
        "username": "admin1", "password": "adminpass1", "role": "admin"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "admin1"
    assert data["role"] == "admin"
    assert data["is_active"] is True


async def test_create_user_duplicate(client):
    payload = {"username": "dup", "password": "password1", "role": "analyst"}
    await client.post("/api/admin/users", json=payload)
    resp = await client.post("/api/admin/users", json=payload)
    assert resp.status_code == 409


async def test_get_user(client):
    create = await client.post("/api/admin/users", json={
        "username": "getme", "password": "password1", "role": "viewer"
    })
    uid = create.json()["id"]
    resp = await client.get(f"/api/admin/users/{uid}")
    assert resp.status_code == 200
    assert resp.json()["username"] == "getme"


async def test_get_user_not_found(client):
    resp = await client.get("/api/admin/users/9999")
    assert resp.status_code == 404


async def test_update_user_role(client):
    create = await client.post("/api/admin/users", json={
        "username": "patchme", "password": "password1", "role": "viewer"
    })
    uid = create.json()["id"]
    resp = await client.patch(f"/api/admin/users/{uid}", json={"role": "analyst"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "analyst"


async def test_update_user_disable(client):
    create = await client.post("/api/admin/users", json={
        "username": "disable_me", "password": "password1", "role": "analyst"
    })
    uid = create.json()["id"]
    resp = await client.patch(f"/api/admin/users/{uid}", json={"is_active": False})
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


async def test_update_user_password(client):
    """修改密码后可用新密码登录，旧密码失效。"""
    await client.post("/api/admin/users", json={
        "username": "pwdchange", "password": "oldpass12", "role": "analyst"
    })
    get = await client.get("/api/admin/users")
    uid = next(u["id"] for u in get.json() if u["username"] == "pwdchange")

    await client.patch(f"/api/admin/users/{uid}", json={"password": "newpass12"})

    ok = await client.post("/api/auth/login", json={
        "username": "pwdchange", "password": "newpass12"
    })
    assert ok.status_code == 200

    fail = await client.post("/api/auth/login", json={
        "username": "pwdchange", "password": "oldpass12"
    })
    assert fail.status_code == 401


async def test_delete_user(client):
    create = await client.post("/api/admin/users", json={
        "username": "deleteme", "password": "password1", "role": "analyst"
    })
    uid = create.json()["id"]
    del_resp = await client.delete(f"/api/admin/users/{uid}")
    assert del_resp.status_code == 204
    get_resp = await client.get(f"/api/admin/users/{uid}")
    assert get_resp.status_code == 404


async def test_list_users_after_create(client):
    for i in range(3):
        await client.post("/api/admin/users", json={
            "username": f"user{i}", "password": "password1", "role": "analyst"
        })
    resp = await client.get("/api/admin/users")
    assert resp.status_code == 200
    assert len(resp.json()) == 3


# ═══════════════════════════════════════════════════════════
# 审计日志
# ═══════════════════════════════════════════════════════════

async def test_audit_logs_empty(client):
    resp = await client.get("/api/admin/audit-logs")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_audit_logs_with_data(client, db_session):
    """直接向 DB 写入审计日志，再通过 API 查询。"""
    await db_session.execute(insert(AuditLog).values([
        {"user_id": 1, "action": "query", "datasource_id": 1,
         "sql_executed": "SELECT 1", "row_count": 1, "duration_ms": 10},
        {"user_id": 2, "action": "login", "datasource_id": None,
         "sql_executed": None, "row_count": None, "duration_ms": 5},
    ]))
    await db_session.commit()

    resp = await client.get("/api/admin/audit-logs")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_audit_logs_filter_by_user(client, db_session):
    await db_session.execute(insert(AuditLog).values([
        {"user_id": 10, "action": "query", "datasource_id": 1},
        {"user_id": 20, "action": "query", "datasource_id": 1},
    ]))
    await db_session.commit()

    resp = await client.get("/api/admin/audit-logs?user_id=10")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["user_id"] == 10


async def test_audit_logs_filter_by_action(client, db_session):
    await db_session.execute(insert(AuditLog).values([
        {"user_id": 1, "action": "query"},
        {"user_id": 1, "action": "login"},
        {"user_id": 1, "action": "query"},
    ]))
    await db_session.commit()

    resp = await client.get("/api/admin/audit-logs?action=query")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_audit_logs_pagination(client, db_session):
    await db_session.execute(insert(AuditLog).values(
        [{"user_id": 1, "action": "query"} for _ in range(10)]
    ))
    await db_session.commit()

    resp = await client.get("/api/admin/audit-logs?page=1&page_size=3")
    assert resp.status_code == 200
    assert len(resp.json()) == 3

    resp2 = await client.get("/api/admin/audit-logs?page=2&page_size=3")
    assert resp2.status_code == 200
    assert len(resp2.json()) == 3
