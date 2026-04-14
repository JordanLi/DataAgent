import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_admin_can_access_admin_routes(client: AsyncClient, admin_token: str):
    response = await client.get("/api/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_admin_can_register_new_user(client: AsyncClient, admin_token: str):
    new_user_data = {
        "username": "new_admin_created_user",
        "password": "securepassword",
        "role": "viewer"
    }
    response = await client.post(
        "/api/auth/register", 
        json=new_user_data, 
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 201

@pytest.mark.asyncio
async def test_analyst_cannot_access_admin_routes(client: AsyncClient, analyst_token: str):
    response = await client.get("/api/admin/users", headers={"Authorization": f"Bearer {analyst_token}"})
    assert response.status_code == 403
    assert "管理员" in response.json()["detail"]

@pytest.mark.asyncio
async def test_viewer_cannot_access_admin_routes(client: AsyncClient, viewer_token: str):
    response = await client.get("/api/admin/users", headers={"Authorization": f"Bearer {viewer_token}"})
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_analyst_can_access_datasource_routes(client: AsyncClient, analyst_token: str):
    response = await client.get("/api/datasources", headers={"Authorization": f"Bearer {analyst_token}"})
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_viewer_cannot_access_datasource_routes(client: AsyncClient, viewer_token: str):
    response = await client.get("/api/datasources", headers={"Authorization": f"Bearer {viewer_token}"})
    assert response.status_code == 403
    assert "分析师或管理员" in response.json()["detail"]

@pytest.mark.asyncio
async def test_viewer_can_access_chat_routes(client: AsyncClient, viewer_token: str):
    response = await client.get("/api/conversations", headers={"Authorization": f"Bearer {viewer_token}"})
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_unauthenticated_access_is_rejected(client: AsyncClient):
    response = await client.get("/api/admin/users")
    assert response.status_code == 401
    
    response = await client.get("/api/datasources")
    assert response.status_code == 401
    
    response = await client.get("/api/conversations")
    assert response.status_code == 401
