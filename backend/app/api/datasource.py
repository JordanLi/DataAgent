"""Datasource CRUD + schema-discovery API router."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, get_current_user
from app.connectors import SchemaDiscovery, build_connector, encrypt_password
from app.models.audit import AuditLog
from app.models.database import get_db
from app.models.datasource import DataSource, TableMetadata
from app.schemas.datasource import (
    DataSourceCreate,
    DataSourceOut,
    DataSourceUpdate,
    TableMetadataOut,
)

logger = logging.getLogger(__name__)
router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

async def _get_datasource_or_404(db: AsyncSession, ds_id: int) -> DataSource:
    result = await db.execute(select(DataSource).where(DataSource.id == ds_id))
    ds = result.scalar_one_or_none()
    if ds is None:
        raise HTTPException(status_code=404, detail="DataSource not found")
    return ds


# ---------------------------------------------------------------------------
# CRUD endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=list[DataSourceOut])
async def list_datasources(db: DbDep):
    result = await db.execute(select(DataSource).order_by(DataSource.id))
    return result.scalars().all()


@router.post("", response_model=DataSourceOut, status_code=status.HTTP_201_CREATED)
async def create_datasource(payload: DataSourceCreate, db: DbDep):
    existing = await db.execute(
        select(DataSource).where(DataSource.name == payload.name)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"DataSource named '{payload.name}' already exists",
        )

    ds = DataSource(
        name=payload.name,
        db_type=payload.db_type,
        host=payload.host,
        port=payload.port,
        database=payload.database,
        username=payload.username,
        encrypted_password=encrypt_password(payload.password),
    )
    db.add(ds)
    await db.commit()
    await db.refresh(ds)
    return ds


@router.get("/{ds_id}", response_model=DataSourceOut)
async def get_datasource(ds_id: int, db: DbDep):
    return await _get_datasource_or_404(db, ds_id)


@router.patch("/{ds_id}", response_model=DataSourceOut)
async def update_datasource(ds_id: int, payload: DataSourceUpdate, db: DbDep):
    ds = await _get_datasource_or_404(db, ds_id)

    update_data = payload.model_dump(exclude_unset=True)
    if "password" in update_data:
        ds.encrypted_password = encrypt_password(update_data.pop("password"))
    for field, value in update_data.items():
        setattr(ds, field, value)

    await db.commit()
    await db.refresh(ds)
    return ds


@router.delete("/{ds_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_datasource(ds_id: int, db: DbDep):
    ds = await _get_datasource_or_404(db, ds_id)
    await db.delete(ds)
    await db.commit()


# ---------------------------------------------------------------------------
# Connection test
# ---------------------------------------------------------------------------

@router.post("/{ds_id}/test", status_code=200)
async def test_connection(ds_id: int, db: DbDep):
    """Verify that the datasource credentials are reachable."""
    ds = await _get_datasource_or_404(db, ds_id)
    connector = build_connector(ds)
    try:
        ok = await connector.test_connection()
        if not ok:
            raise HTTPException(status_code=400, detail="Connection test returned False")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Connection test failed for datasource=%d: %s", ds_id, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        await connector.close()


# ---------------------------------------------------------------------------
# Schema discovery
# ---------------------------------------------------------------------------

@router.post("/{ds_id}/discover", response_model=list[TableMetadataOut])
async def trigger_discover(
    ds_id: int,
    db: DbDep,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Trigger a full schema discovery and persist the results."""
    ds = await _get_datasource_or_404(db, ds_id)
    connector = build_connector(ds)
    try:
        from app.connectors.schema_discovery import SchemaDiscoveryService
        svc = SchemaDiscoveryService(db)
        count = await svc.discover(ds)
        # Fetch the discovered rows to return
        result = await db.execute(
            select(TableMetadata).where(TableMetadata.datasource_id == ds_id)
        )
        
        # 写入审计日志
        audit = AuditLog(
            user_id=current_user.user_id,
            action="schema_discover",
            datasource_id=ds_id,
        )
        db.add(audit)
        await db.commit()

        return result.scalars().all()
    except Exception as exc:
        logger.error("Schema discovery failed for datasource=%d: %s", ds_id, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        await connector.close()


@router.get("/{ds_id}/schema", response_model=list[TableMetadataOut])
async def get_schema(ds_id: int, db: DbDep):
    """Return cached schema metadata (from last discovery run)."""
    await _get_datasource_or_404(db, ds_id)
    result = await db.execute(
        select(TableMetadata)
        .where(TableMetadata.datasource_id == ds_id)
        .order_by(TableMetadata.table_name)
    )
    return result.scalars().all()
