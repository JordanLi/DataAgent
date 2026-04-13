"""Auth router — login / register / me.

端点:
  POST /api/auth/login    — 用户名+密码登录，返回 JWT
  POST /api/auth/register — 注册新用户（Step 11 起限 admin 可操作）
  GET  /api/auth/me       — 返回当前登录用户信息
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    CurrentUser,
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.models.database import get_db
from app.models.user import User
from app.schemas.user import LoginRequest, TokenOut, UserCreate, UserOut

logger = logging.getLogger(__name__)
router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------

@router.post("/login", response_model=TokenOut)
async def login(payload: LoginRequest, db: DbDep):
    """用户名 + 密码登录，成功返回 Bearer JWT。"""
    result = await db.execute(select(User).where(User.username == payload.username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已禁用，请联系管理员",
        )

    token = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role.value,
    )
    logger.info("User '%s' logged in successfully", user.username)
    return TokenOut(access_token=token)


# ---------------------------------------------------------------------------
# POST /api/auth/register
# ---------------------------------------------------------------------------

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: DbDep):
    """注册新用户。

    注意：Step 11 将为此接口添加 admin 权限校验；当前开放注册用于开发调试。
    """
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
    logger.info("New user registered: '%s' (role=%s)", user.username, user.role.value)
    return user


# ---------------------------------------------------------------------------
# GET /api/auth/me
# ---------------------------------------------------------------------------

@router.get("/me", response_model=UserOut)
async def me(
    current: Annotated[CurrentUser, Depends(get_current_user)],
    db: DbDep,
):
    """返回当前登录用户的详细信息。"""
    result = await db.execute(select(User).where(User.id == current.user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return user
