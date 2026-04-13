"""Pydantic schemas for Conversation and Message."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.conversation import MessageRole


class ConversationCreate(BaseModel):
    title: str | None = None


class ConversationOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    user_id: int
    title: str | None
    created_at: datetime


class MessageOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    conversation_id: int
    role: MessageRole
    content: str
    sql_generated: str | None
    execution_time_ms: int | None
    row_count: int | None
    created_at: datetime


class ConversationWithMessages(ConversationOut):
    messages: list[MessageOut] = []
