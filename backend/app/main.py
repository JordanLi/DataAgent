"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
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
    app.include_router(chat_router,       prefix="/api",            tags=["chat"])
    app.include_router(datasource_router, prefix="/api/datasources",tags=["datasources"])
    app.include_router(semantic_router,   prefix="/api/semantic",   tags=["semantic"])
    app.include_router(admin_router,      prefix="/api/admin",      tags=["admin"])

    @app.get("/health", tags=["health"])
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
