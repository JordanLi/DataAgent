"""Admin router — 用户管理 + 审计日志。

端点:
  GET    /api/admin/users           — 用户列表
  POST   /api/admin/users           — 创建用户
  GET    /api/admin/users/{id}      — 用户详情
  PATCH  /api/admin/users/{id}      — 更新用户
  DELETE /api/admin/users/{id}      — 删除用户
  GET    /api/admin/audit-logs      — 审计日志（支持过滤+分页）
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import hash_password
from app.models.audit import AuditLog
from app.models.database import get_db
from app.models.user import User
from app.schemas.audit import AuditLogOut
from app.schemas.user import UserCreate, UserOut, UserUpdate

logger = logging.getLogger(__name__)
router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

async def _get_user_or_404(db: AsyncSession, user_id: int) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


# ---------------------------------------------------------------------------
# 用户 CRUD
# ---------------------------------------------------------------------------

@router.get("/users", response_model=list[UserOut])
async def list_users(db: DbDep):
    """返回所有用户列表（按创建时间升序）。"""
    result = await db.execute(select(User).order_by(User.created_at))
    return result.scalars().all()


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, db: DbDep):
    """创建新用户（管理后台使用，Step 11 加权限校验）。"""
    existing = await db.execute(select(User).where(User.username == payload.username))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"用户名 '{payload.username}' 已存在",
        )
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/users/{user_id}", response_model=UserOut)
async def get_user(user_id: int, db: DbDep):
    return await _get_user_or_404(db, user_id)


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(user_id: int, payload: UserUpdate, db: DbDep):
    """更新用户信息。密码若提供则重新哈希。"""
    user = await _get_user_or_404(db, user_id)
    data = payload.model_dump(exclude_unset=True)
    if "password" in data:
        user.password_hash = hash_password(data.pop("password"))
    for field, value in data.items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: DbDep):
    user = await _get_user_or_404(db, user_id)
    await db.delete(user)
    await db.commit()


# ---------------------------------------------------------------------------
# 审计日志
# ---------------------------------------------------------------------------

@router.get("/audit-logs", response_model=list[AuditLogOut])
async def list_audit_logs(
    db: DbDep,
    user_id: int | None = Query(None, description="按用户 ID 过滤"),
    datasource_id: int | None = Query(None, description="按数据源 ID 过滤"),
    action: str | None = Query(None, description="按操作类型过滤，如 query/login"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页条数"),
):
    """查询审计日志，支持按用户/数据源/操作过滤，结果按时间倒序分页。"""
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
    if user_id is not None:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if datasource_id is not None:
        stmt = stmt.where(AuditLog.datasource_id == datasource_id)
    if action is not None:
        stmt = stmt.where(AuditLog.action == action)

    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    result = await db.execute(stmt)
    return result.scalars().all()
