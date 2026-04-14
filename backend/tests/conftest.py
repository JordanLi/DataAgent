import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.main import app
from app.models.database import Base, get_db
from app.auth import hash_password
from app.models.user import User, UserRole

# Use a test database URL
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DB_URL, echo=False)
TestingSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session():
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def test_users(db_session: AsyncSession):
    users = {
        "admin": User(username="admin_user", password_hash=hash_password("adminpass"), role=UserRole.admin, is_active=True),
        "analyst": User(username="analyst_user", password_hash=hash_password("analystpass"), role=UserRole.analyst, is_active=True),
        "viewer": User(username="viewer_user", password_hash=hash_password("viewerpass"), role=UserRole.viewer, is_active=True),
        "inactive": User(username="inactive_user", password_hash=hash_password("inactivepass"), role=UserRole.viewer, is_active=False),
    }
    for u in users.values():
        db_session.add(u)
    await db_session.commit()
    for u in users.values():
        await db_session.refresh(u)
    return users

@pytest.fixture
async def admin_token(client: AsyncClient, test_users):
    resp = await client.post("/api/auth/login", json={"username": "admin_user", "password": "adminpass"})
    return resp.json()["access_token"]

@pytest.fixture
async def analyst_token(client: AsyncClient, test_users):
    resp = await client.post("/api/auth/login", json={"username": "analyst_user", "password": "analystpass"})
    return resp.json()["access_token"]

@pytest.fixture
async def viewer_token(client: AsyncClient, test_users):
    resp = await client.post("/api/auth/login", json={"username": "viewer_user", "password": "viewerpass"})
    return resp.json()["access_token"]