"""Pydantic schemas for User."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.user import UserRole


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=128)
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.analyst


class UserUpdate(BaseModel):
    username: str | None = Field(None, min_length=3, max_length=128)
    password: str | None = Field(None, min_length=8)
    role: UserRole | None = None
    is_active: bool | None = None


class UserOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    username: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
