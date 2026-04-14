import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditLog
from app.models.user import User

@pytest.mark.asyncio
async def test_login_creates_audit_log(client: AsyncClient, db_session: AsyncSession, test_users):
    # 模拟用户登录
    response = await client.post("/api/auth/login", json={"username": "analyst_user", "password": "analystpass"})
    assert response.status_code == 200
    
    # 查询审计日志
    result = await db_session.execute(
        select(AuditLog).where(AuditLog.user_id == test_users["analyst"].id)
    )
    logs = result.scalars().all()
    
    assert len(logs) >= 1
    # 最新的审计日志必须是登录
    latest_log = sorted(logs, key=lambda x: x.created_at, reverse=True)[0]
    assert latest_log.action == "login"
    assert latest_log.datasource_id is None

@pytest.mark.asyncio
async def test_admin_can_read_audit_logs(client: AsyncClient, admin_token: str):
    response = await client.get("/api/admin/audit-logs", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    
@pytest.mark.asyncio
async def test_admin_can_filter_audit_logs(client: AsyncClient, admin_token: str, test_users):
    # Perform a specific action to ensure an audit log exists for filter
    await client.post("/api/auth/login", json={"username": "viewer_user", "password": "viewerpass"})
    
    # Check filter by action and user_id
    response = await client.get(
        f"/api/admin/audit-logs?action=login&user_id={test_users['viewer'].id}", 
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) >= 1
    for log in data:
        assert log["action"] == "login"
        assert log["user_id"] == test_users['viewer'].id

@pytest.mark.asyncio
async def test_analyst_cannot_read_audit_logs(client: AsyncClient, analyst_token: str):
    response = await client.get("/api/admin/audit-logs", headers={"Authorization": f"Bearer {analyst_token}"})
    assert response.status_code == 403
