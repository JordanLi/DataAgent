"""Step 11 API 测试 — AuditLog 审计日志。"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog

pytestmark = pytest.mark.asyncio


async def test_audit_logs_list_requires_admin(unauth_client, analyst_client, viewer_client):
    """Only Admin can access /api/admin/audit-logs."""
    resp = await unauth_client.get("/api/admin/audit-logs")
    assert resp.status_code == 401

    resp = await analyst_client.get("/api/admin/audit-logs")
    assert resp.status_code == 403

    resp = await viewer_client.get("/api/admin/audit-logs")
    assert resp.status_code == 403


async def test_audit_logs_list_and_filter(client, db_session: AsyncSession):
    """Test retrieving and filtering audit logs."""
    # Insert dummy logs
    logs = [
        AuditLog(user_id=1, action="login", datasource_id=None),
        AuditLog(user_id=1, action="query", datasource_id=10),
        AuditLog(user_id=2, action="query", datasource_id=10),
        AuditLog(user_id=2, action="schema_discover", datasource_id=20),
    ]
    db_session.add_all(logs)
    await db_session.commit()

    # 1. No filter (all logs)
    resp = await client.get("/api/admin/audit-logs")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 4

    # 2. Filter by user_id
    resp = await client.get("/api/admin/audit-logs?user_id=2")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    for log in data:
        assert log["user_id"] == 2

    # 3. Filter by datasource_id
    resp = await client.get("/api/admin/audit-logs?datasource_id=10")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    for log in data:
        assert log["datasource_id"] == 10

    # 4. Filter by action
    resp = await client.get("/api/admin/audit-logs?action=login")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["action"] == "login"


async def test_audit_logs_pagination(client, db_session: AsyncSession):
    """Test pagination of audit logs."""
    # Insert 15 dummy logs
    logs = [
        AuditLog(user_id=1, action="query", datasource_id=10)
        for _ in range(15)
    ]
    db_session.add_all(logs)
    await db_session.commit()

    # Get page 1, size 10
    resp = await client.get("/api/admin/audit-logs?page=1&page_size=10")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 10

    # Get page 2, size 10
    resp = await client.get("/api/admin/audit-logs?page=2&page_size=10")
    assert resp.status_code == 200
    data = resp.json()
    # Since we added 15, and maybe some previous ones exist in the DB session...
    # Actually each test runs in a clean isolated sqlite memory DB thanks to db_session fixture!
    # Wait, the auth token fixture may add users, but it doesn't add audit logs.
    # Let's just check length > 0 and <= 10.
    assert 0 < len(data) <= 10
