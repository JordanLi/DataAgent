"""Pydantic schemas for the semantic layer."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.semantic import RelationType


# ── BusinessTerm ─────────────────────────────────────────────────────────────

class BusinessTermCreate(BaseModel):
    term_name: str = Field(..., max_length=128)
    definition: str | None = None
    sql_expression: str | None = None


class BusinessTermUpdate(BaseModel):
    term_name: str | None = Field(None, max_length=128)
    definition: str | None = None
    sql_expression: str | None = None


class BusinessTermOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    datasource_id: int
    term_name: str
    definition: str | None
    sql_expression: str | None
    created_at: datetime


# ── FieldAlias ────────────────────────────────────────────────────────────────

class FieldAliasCreate(BaseModel):
    table_name: str = Field(..., max_length=256)
    column_name: str = Field(..., max_length=256)
    alias_name: str = Field(..., max_length=256)
    description: str | None = None


class FieldAliasUpdate(BaseModel):
    alias_name: str | None = Field(None, max_length=256)
    description: str | None = None


class FieldAliasOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    datasource_id: int
    table_name: str
    column_name: str
    alias_name: str
    description: str | None
    created_at: datetime


# ── EnumMapping ───────────────────────────────────────────────────────────────

class EnumMappingCreate(BaseModel):
    table_name: str = Field(..., max_length=256)
    column_name: str = Field(..., max_length=256)
    enum_value: str = Field(..., max_length=256)
    display_label: str = Field(..., max_length=256)


class EnumMappingUpdate(BaseModel):
    display_label: str | None = Field(None, max_length=256)


class EnumMappingOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    datasource_id: int
    table_name: str
    column_name: str
    enum_value: str
    display_label: str
    created_at: datetime


# ── TableRelation ─────────────────────────────────────────────────────────────

class TableRelationCreate(BaseModel):
    source_table: str = Field(..., max_length=256)
    source_column: str = Field(..., max_length=256)
    target_table: str = Field(..., max_length=256)
    target_column: str = Field(..., max_length=256)
    relation_type: RelationType = RelationType.many_to_one


class TableRelationUpdate(BaseModel):
    relation_type: RelationType | None = None


class TableRelationOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    datasource_id: int
    source_table: str
    source_column: str
    target_table: str
    target_column: str
    relation_type: RelationType
    created_at: datetime
