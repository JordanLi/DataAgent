"""Semantic layer CRUD router.

Endpoints are grouped under /api/semantic and cover:
  - Business terms   (KPI / metric definitions)
  - Field aliases    (human-readable column names)
  - Enum mappings    (value -> display label)
  - Table relations  (join hints)
  - Schema preview   (rendered prompt context for a datasource)
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.semantic.engine import SemanticEngine
from app.core.semantic.loader import SemanticLoader
from app.models.database import get_db
from app.models.datasource import DataSource
from app.models.semantic import (
    BusinessTerm,
    EnumMapping,
    FieldAlias,
    TableRelation,
)
from app.schemas.semantic import (
    BusinessTermCreate,
    BusinessTermOut,
    BusinessTermUpdate,
    EnumMappingCreate,
    EnumMappingOut,
    EnumMappingUpdate,
    FieldAliasCreate,
    FieldAliasOut,
    FieldAliasUpdate,
    TableRelationCreate,
    TableRelationOut,
    TableRelationUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]


# ---------------------------------------------------------------------------
# Shared guard
# ---------------------------------------------------------------------------

async def _require_datasource(db: AsyncSession, ds_id: int) -> DataSource:
    result = await db.execute(select(DataSource).where(DataSource.id == ds_id))
    ds = result.scalar_one_or_none()
    if ds is None:
        raise HTTPException(status_code=404, detail="DataSource not found")
    return ds


# ===========================================================================
# Business Terms  –  /api/semantic/datasources/{ds_id}/terms
# ===========================================================================

@router.get("/datasources/{ds_id}/terms", response_model=list[BusinessTermOut])
async def list_terms(ds_id: int, db: DbDep):
    await _require_datasource(db, ds_id)
    result = await db.execute(
        select(BusinessTerm)
        .where(BusinessTerm.datasource_id == ds_id)
        .order_by(BusinessTerm.term_name)
    )
    return result.scalars().all()


@router.post(
    "/datasources/{ds_id}/terms",
    response_model=BusinessTermOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_term(ds_id: int, payload: BusinessTermCreate, db: DbDep):
    await _require_datasource(db, ds_id)
    term = BusinessTerm(datasource_id=ds_id, **payload.model_dump())
    db.add(term)
    try:
        await db.commit()
        await db.refresh(term)
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return term


@router.get("/datasources/{ds_id}/terms/{term_id}", response_model=BusinessTermOut)
async def get_term(ds_id: int, term_id: int, db: DbDep):
    result = await db.execute(
        select(BusinessTerm).where(
            BusinessTerm.id == term_id, BusinessTerm.datasource_id == ds_id
        )
    )
    term = result.scalar_one_or_none()
    if term is None:
        raise HTTPException(status_code=404, detail="BusinessTerm not found")
    return term


@router.patch("/datasources/{ds_id}/terms/{term_id}", response_model=BusinessTermOut)
async def update_term(ds_id: int, term_id: int, payload: BusinessTermUpdate, db: DbDep):
    result = await db.execute(
        select(BusinessTerm).where(
            BusinessTerm.id == term_id, BusinessTerm.datasource_id == ds_id
        )
    )
    term = result.scalar_one_or_none()
    if term is None:
        raise HTTPException(status_code=404, detail="BusinessTerm not found")
    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(term, field_name, value)
    await db.commit()
    await db.refresh(term)
    return term


@router.delete(
    "/datasources/{ds_id}/terms/{term_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_term(ds_id: int, term_id: int, db: DbDep):
    result = await db.execute(
        select(BusinessTerm).where(
            BusinessTerm.id == term_id, BusinessTerm.datasource_id == ds_id
        )
    )
    term = result.scalar_one_or_none()
    if term is None:
        raise HTTPException(status_code=404, detail="BusinessTerm not found")
    await db.delete(term)
    await db.commit()


# ===========================================================================
# Field Aliases  –  /api/semantic/datasources/{ds_id}/aliases
# ===========================================================================

@router.get("/datasources/{ds_id}/aliases", response_model=list[FieldAliasOut])
async def list_aliases(ds_id: int, db: DbDep):
    await _require_datasource(db, ds_id)
    result = await db.execute(
        select(FieldAlias)
        .where(FieldAlias.datasource_id == ds_id)
        .order_by(FieldAlias.table_name, FieldAlias.column_name)
    )
    return result.scalars().all()


@router.post(
    "/datasources/{ds_id}/aliases",
    response_model=FieldAliasOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_alias(ds_id: int, payload: FieldAliasCreate, db: DbDep):
    await _require_datasource(db, ds_id)
    alias = FieldAlias(datasource_id=ds_id, **payload.model_dump())
    db.add(alias)
    try:
        await db.commit()
        await db.refresh(alias)
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return alias


@router.patch(
    "/datasources/{ds_id}/aliases/{alias_id}", response_model=FieldAliasOut
)
async def update_alias(ds_id: int, alias_id: int, payload: FieldAliasUpdate, db: DbDep):
    result = await db.execute(
        select(FieldAlias).where(
            FieldAlias.id == alias_id, FieldAlias.datasource_id == ds_id
        )
    )
    alias = result.scalar_one_or_none()
    if alias is None:
        raise HTTPException(status_code=404, detail="FieldAlias not found")
    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(alias, field_name, value)
    await db.commit()
    await db.refresh(alias)
    return alias


@router.delete(
    "/datasources/{ds_id}/aliases/{alias_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_alias(ds_id: int, alias_id: int, db: DbDep):
    result = await db.execute(
        select(FieldAlias).where(
            FieldAlias.id == alias_id, FieldAlias.datasource_id == ds_id
        )
    )
    alias = result.scalar_one_or_none()
    if alias is None:
        raise HTTPException(status_code=404, detail="FieldAlias not found")
    await db.delete(alias)
    await db.commit()


# ===========================================================================
# Enum Mappings  –  /api/semantic/datasources/{ds_id}/enums
# ===========================================================================

@router.get("/datasources/{ds_id}/enums", response_model=list[EnumMappingOut])
async def list_enums(ds_id: int, db: DbDep):
    await _require_datasource(db, ds_id)
    result = await db.execute(
        select(EnumMapping)
        .where(EnumMapping.datasource_id == ds_id)
        .order_by(EnumMapping.table_name, EnumMapping.column_name, EnumMapping.enum_value)
    )
    return result.scalars().all()


@router.post(
    "/datasources/{ds_id}/enums",
    response_model=EnumMappingOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_enum(ds_id: int, payload: EnumMappingCreate, db: DbDep):
    await _require_datasource(db, ds_id)
    mapping = EnumMapping(datasource_id=ds_id, **payload.model_dump())
    db.add(mapping)
    try:
        await db.commit()
        await db.refresh(mapping)
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return mapping


@router.patch(
    "/datasources/{ds_id}/enums/{enum_id}", response_model=EnumMappingOut
)
async def update_enum(ds_id: int, enum_id: int, payload: EnumMappingUpdate, db: DbDep):
    result = await db.execute(
        select(EnumMapping).where(
            EnumMapping.id == enum_id, EnumMapping.datasource_id == ds_id
        )
    )
    mapping = result.scalar_one_or_none()
    if mapping is None:
        raise HTTPException(status_code=404, detail="EnumMapping not found")
    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(mapping, field_name, value)
    await db.commit()
    await db.refresh(mapping)
    return mapping


@router.delete(
    "/datasources/{ds_id}/enums/{enum_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_enum(ds_id: int, enum_id: int, db: DbDep):
    result = await db.execute(
        select(EnumMapping).where(
            EnumMapping.id == enum_id, EnumMapping.datasource_id == ds_id
        )
    )
    mapping = result.scalar_one_or_none()
    if mapping is None:
        raise HTTPException(status_code=404, detail="EnumMapping not found")
    await db.delete(mapping)
    await db.commit()


# ===========================================================================
# Table Relations  –  /api/semantic/datasources/{ds_id}/relations
# ===========================================================================

@router.get("/datasources/{ds_id}/relations", response_model=list[TableRelationOut])
async def list_relations(ds_id: int, db: DbDep):
    await _require_datasource(db, ds_id)
    result = await db.execute(
        select(TableRelation)
        .where(TableRelation.datasource_id == ds_id)
        .order_by(TableRelation.source_table, TableRelation.source_column)
    )
    return result.scalars().all()


@router.post(
    "/datasources/{ds_id}/relations",
    response_model=TableRelationOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_relation(ds_id: int, payload: TableRelationCreate, db: DbDep):
    await _require_datasource(db, ds_id)
    relation = TableRelation(datasource_id=ds_id, **payload.model_dump())
    db.add(relation)
    try:
        await db.commit()
        await db.refresh(relation)
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return relation


@router.patch(
    "/datasources/{ds_id}/relations/{rel_id}", response_model=TableRelationOut
)
async def update_relation(
    ds_id: int, rel_id: int, payload: TableRelationUpdate, db: DbDep
):
    result = await db.execute(
        select(TableRelation).where(
            TableRelation.id == rel_id, TableRelation.datasource_id == ds_id
        )
    )
    relation = result.scalar_one_or_none()
    if relation is None:
        raise HTTPException(status_code=404, detail="TableRelation not found")
    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(relation, field_name, value)
    await db.commit()
    await db.refresh(relation)
    return relation


@router.delete(
    "/datasources/{ds_id}/relations/{rel_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_relation(ds_id: int, rel_id: int, db: DbDep):
    result = await db.execute(
        select(TableRelation).where(
            TableRelation.id == rel_id, TableRelation.datasource_id == ds_id
        )
    )
    relation = result.scalar_one_or_none()
    if relation is None:
        raise HTTPException(status_code=404, detail="TableRelation not found")
    await db.delete(relation)
    await db.commit()


# ===========================================================================
# Schema Preview  –  rendered prompt context for the LLM
# ===========================================================================

@router.get("/datasources/{ds_id}/preview")
async def preview_prompt_context(ds_id: int, db: DbDep):
    """Return the full rendered schema + semantic context as plain text.

    Useful for debugging the prompt that will be sent to the LLM.
    """
    await _require_datasource(db, ds_id)
    try:
        loader = SemanticLoader(db)
        ctx = await loader.load_full_context(ds_id)
        schema_context = SemanticEngine.build_schema_prompt(ctx)
        # Build semantic context from business terms and relations
        sem_lines = []
        if ctx.get("business_terms"):
            sem_lines.append("业务术语:")
            for t in ctx["business_terms"]:
                sem_lines.append(f"  {t['term']}: {t.get('sql', '')} | {t.get('definition', '')}")
        if ctx.get("relations"):
            sem_lines.append("表关联:")
            for r in ctx["relations"]:
                sem_lines.append(f"  {r}")
        semantic_context = "\n".join(sem_lines)
        return {
            "schema_context": schema_context,
            "semantic_context": semantic_context,
            "full_context": f"{schema_context}\n{semantic_context}" if semantic_context else schema_context,
            "table_count": len(ctx["schema"]),
            "term_count": len(ctx["business_terms"]),
            "relation_count": len(ctx["relations"]),
        }
    except Exception as exc:
        logger.error("Failed to build semantic preview for datasource=%d: %s", ds_id, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
