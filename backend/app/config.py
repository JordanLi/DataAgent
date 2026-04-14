"""Application configuration loaded from environment variables / .env file."""

from __future__ import annotations

from functools import lru_cache
from typing import List, Optional
import os
import re
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    debug: bool = True

    # CORS: comma-separated list of allowed origins
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # System metadata database (PostgreSQL + asyncpg for runtime, psycopg2 for alembic)
    system_db_url: str = (
        "postgresql+asyncpg://dataagent:dataagent@localhost:5432/dataagent"
    )

    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # LLM
    llm_provider: str = "openai"          # openai | claude | deepseek
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_base_url: Optional[str] = None    # custom API base (e.g. local proxy)

    # Query execution limits
    query_timeout_seconds: int = 30
    query_max_rows: int = 10000
    default_sql_limit: int = 100

    @field_validator("llm_api_key", mode="after")
    @classmethod
    def expand_env_vars(cls, v: str) -> str:
        """Expand environment variables like ${VAR} if present."""
        if v and "${" in v:
            # First try os.path.expandvars which handles $VAR and ${VAR}
            expanded = os.path.expandvars(v)
            if expanded != v:
                return expanded
            # If expandvars didn't work (e.g. variable not in os.environ), let's parse manually
            match = re.search(r"\$\{([^}]+)\}", v)
            if match:
                env_name = match.group(1)
                return os.environ.get(env_name, "")
        return v

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def system_db_url_sync(self) -> str:
        """Alembic uses a synchronous psycopg2 driver."""
        url = self.system_db_url
        if "+asyncpg" in url:
            return url.replace("+asyncpg", "", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
