"""FastAPI application entry point."""

from contextlib import asynccontextmanager
import os
import logging

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.config import get_settings
from app.auth import get_current_user, require_admin, require_analyst_or_admin, hash_password
from app.models.database import AsyncSessionLocal
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)

async def _init_admin_user() -> None:
    """初始化默认管理员账号"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.username == "admin"))
        if result.scalar_one_or_none() is None:
            logger.info("Initializing default admin user...")
            initial_password = os.getenv("ADMIN_INIT_PASSWORD", "admin123")
            admin = User(
                username="admin",
                password_hash=hash_password(initial_password),
                role=UserRole.admin
            )
            db.add(admin)
            await db.commit()
            logger.info("Default admin user created successfully.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    try:
        await _init_admin_user()
    except Exception as e:
        logger.warning(f"Failed to initialize admin user: {e}")
    yield
    # shutdown


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="DataAgent API",
        description="Natural language data query agent",
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers (populated in later steps)
    from app.api.auth import router as auth_router
    from app.api.chat import router as chat_router
    from app.api.datasource import router as datasource_router
    from app.api.semantic import router as semantic_router
    from app.api.admin import router as admin_router

    app.include_router(auth_router,       prefix="/api/auth",       tags=["auth"])
    app.include_router(chat_router,       prefix="/api",            tags=["chat"], dependencies=[Depends(get_current_user)])
    app.include_router(datasource_router, prefix="/api/datasources",tags=["datasources"], dependencies=[Depends(require_analyst_or_admin)])
    app.include_router(semantic_router,   prefix="/api/semantic",   tags=["semantic"], dependencies=[Depends(require_analyst_or_admin)])
    app.include_router(admin_router,      prefix="/api/admin",      tags=["admin"], dependencies=[Depends(require_admin)])

    @app.get("/health", tags=["health"])
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
