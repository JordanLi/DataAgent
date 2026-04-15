import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Override DB URL to use an in-memory SQLite BEFORE importing the app
os.environ["SYSTEM_DB_URL"] = "sqlite+aiosqlite:///:memory:"

from app.main import app
from app.models.database import Base, get_db
from app.models.user import User, UserRole
from app.auth import hash_password

# Create an async engine for the tests
test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
TestSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)

async def override_get_db():
    async with TestSessionLocal() as session:
        yield session

# Override the FastAPI dependency
app.dependency_overrides[get_db] = override_get_db

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Create all tables and seed admin user in the test database once."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Seed admin user
    async with TestSessionLocal() as session:
        admin = User(
            username="admin",
            password_hash=hash_password("adminpass"),
            role=UserRole.admin,
            is_active=True,
        )
        session.add(admin)
        await session.commit()
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def async_client():
    """Provides an authenticated async HTTP client for the FastAPI app."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/auth/login", json={"username": "admin", "password": "adminpass"})
        token = resp.json()["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
        yield client

@pytest_asyncio.fixture
async def db_session():
    """Provides a direct DB session for test setup/assertions."""
    async with TestSessionLocal() as session:
        yield session
