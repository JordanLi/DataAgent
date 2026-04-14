import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.database import get_db, Base, engine
from app.models.user import User
from app.auth import hash_password

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
async def test_db_engine():
    """Create test tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session(test_db_engine):
    """Provide a transactional scope around each test."""
    connection = await test_db_engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()


@pytest.fixture
def override_get_db(db_session):
    """Override FastAPI dependency get_db with our test session."""
    async def _get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_test_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client(override_get_db):
    """Provide an HTTPX AsyncClient for FastAPI."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def setup_users(db_session: AsyncSession):
    """Create some users for testing."""
    admin_user = User(
        username="admin",
        password_hash=hash_password("admin_pass"),
        role="admin",
        is_active=True,
    )
    viewer_user = User(
        username="viewer",
        password_hash=hash_password("viewer_pass"),
        role="viewer",
        is_active=True,
    )
    disabled_user = User(
        username="banned",
        password_hash=hash_password("banned_pass"),
        role="analyst",
        is_active=False,
    )
    db_session.add_all([admin_user, viewer_user, disabled_user])
    await db_session.commit()
    return {"admin": admin_user, "viewer": viewer_user, "disabled": disabled_user}


# ---------------------------------------------------------------------------
# Tests: Auth & JWT
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, setup_users):
    """Test successful login."""
    response = await client.post("/api/auth/login", json={
        "username": "admin",
        "password": "admin_pass"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, setup_users):
    """Test login with incorrect password."""
    response = await client.post("/api/auth/login", json={
        "username": "admin",
        "password": "wrong_password"
    })
    assert response.status_code == 401
    assert "用户名或密码错误" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_user_not_found(client: AsyncClient, setup_users):
    """Test login with non-existent user."""
    response = await client.post("/api/auth/login", json={
        "username": "non_existent",
        "password": "password123"
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_disabled_user(client: AsyncClient, setup_users):
    """Test login with a disabled user."""
    response = await client.post("/api/auth/login", json={
        "username": "banned",
        "password": "banned_pass"
    })
    assert response.status_code == 403
    assert "账号已禁用" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_me_success(client: AsyncClient, setup_users):
    """Test fetching current user details with a valid token."""
    login_resp = await client.post("/api/auth/login", json={
        "username": "viewer",
        "password": "viewer_pass"
    })
    token = login_resp.json()["access_token"]
    
    response = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "viewer"
    assert data["role"] == "viewer"
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_get_me_no_token(client: AsyncClient):
    """Test accessing protected route without a token."""
    response = await client.get("/api/auth/me")
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"] or "缺少认证" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_me_invalid_token(client: AsyncClient):
    """Test accessing protected route with an invalid token."""
    response = await client.get("/api/auth/me", headers={"Authorization": "Bearer invalid_token_here"})
    assert response.status_code == 401
    assert "无效" in response.json()["detail"] or "Not authenticated" in response.json()["detail"]