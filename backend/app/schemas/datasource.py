"""Pydantic schemas for DataSource and TableMetadata."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.datasource import DbType


class DataSourceCreate(BaseModel):
    name: str = Field(..., max_length=128)
    db_type: DbType = DbType.mysql
    host: str = Field(..., max_length=256)
    port: int = Field(3306, ge=1, le=65535)
    database: str = Field(..., max_length=128)
    username: str = Field(..., max_length=128)
    password: str = Field(..., description="Plain-text password; stored encrypted")


class DataSourceUpdate(BaseModel):
    name: str | None = Field(None, max_length=128)
    host: str | None = Field(None, max_length=256)
    port: int | None = Field(None, ge=1, le=65535)
    database: str | None = Field(None, max_length=128)
    username: str | None = Field(None, max_length=128)
    password: str | None = None
    is_active: bool | None = None


class DataSourceOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    db_type: DbType
    host: str
    port: int
    database: str
    username: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TableMetadataOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    datasource_id: int
    table_name: str
    table_comment: str | None
    columns_json: str | None
    discovered_at: datetime
