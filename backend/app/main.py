"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.auth import get_current_user, require_admin, require_analyst_or_admin


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
    app.include_router(chat_router,       prefix="/api",            tags=["chat"], dependencies=[Depends(get_current_user)])
    app.include_router(datasource_router, prefix="/api/datasources",tags=["datasources"], dependencies=[Depends(require_analyst_or_admin)])
    app.include_router(semantic_router,   prefix="/api/semantic",   tags=["semantic"], dependencies=[Depends(require_analyst_or_admin)])
    app.include_router(admin_router,      prefix="/api/admin",      tags=["admin"], dependencies=[Depends(require_admin)])

    @app.get("/health", tags=["health"])
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
