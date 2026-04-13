"""Pydantic schemas for AuditLog."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    user_id: int | None
    action: str
    datasource_id: int | None
    sql_executed: str | None
    row_count: int | None
    duration_ms: int | None
    created_at: datetime


class AuditLogFilter(BaseModel):
    user_id: int | None = None
    datasource_id: int | None = None
    action: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    page: int = 1
    page_size: int = 50
