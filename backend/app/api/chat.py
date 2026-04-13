"""Chat router — SSE 流式 NL-to-SQL 查询接口。

端点:
  POST /api/chat            — 主查询（SSE 流）
  GET  /api/conversations   — 会话列表
  POST /api/conversations   — 创建会话
  GET  /api/conversations/{id}/messages — 消息列表
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent import AgentOrchestrator
from app.core.conversation.manager import ConversationManager
from app.models.conversation import Conversation, Message
from app.models.database import get_db
from app.schemas.conversation import (
    ConversationCreate,
    ConversationOut,
    ConversationWithMessages,
    MessageOut,
)

logger = logging.getLogger(__name__)
router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]

# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000, description="自然语言问题")
    datasource_id: int = Field(..., description="目标数据源 ID")
    conversation_id: int | None = Field(None, description="已有会话 ID，None 表示新建")
    user_id: int = Field(1, description="当前用户 ID（Step 11 接入 JWT 后自动注入）")


# ---------------------------------------------------------------------------
# 主查询接口（SSE）
# ---------------------------------------------------------------------------


@router.post("/chat")
async def chat(payload: ChatRequest, db: DbDep):
    """NL-to-SQL 查询，以 Server-Sent Events 流式返回各阶段结果。

    事件类型:
      thinking      — 处理进度提示
      sql_stream    — SQL 片段（流式）
      sql           — 完整 SQL
      sql_rewritten — 校验后重写的 SQL（LIMIT 补充等）
      result        — 查询结果表格
      summary       — 自然语言摘要 + 图表建议
      done          — 流程完成（含 conversation_id）
      error         — 错误信息
    """
    orchestrator = AgentOrchestrator(db)

    async def event_stream():
        try:
            async for event in orchestrator.process_query(
                question=payload.question,
                datasource_id=payload.datasource_id,
                conversation_id=payload.conversation_id,
                user_id=payload.user_id,
            ):
                yield event
        except Exception as exc:
            import json
            logger.exception("Chat stream error: %s", exc)
            yield f"data: {json.dumps({'type': 'error', 'content': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",       # 关闭 nginx 缓冲
        },
    )


# ---------------------------------------------------------------------------
# 会话管理
# ---------------------------------------------------------------------------


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(user_id: int = 1, db: DbDep = None):
    """返回指定用户的所有会话（按创建时间倒序）。"""
    mgr = ConversationManager(db)
    return await mgr.list_conversations(user_id)


@router.post("/conversations", response_model=ConversationOut, status_code=201)
async def create_conversation(payload: ConversationCreate, user_id: int = 1, db: DbDep = None):
    """手动创建一个空会话。"""
    mgr = ConversationManager(db)
    return await mgr.create_conversation(user_id=user_id, title=payload.title)


@router.get("/conversations/{conv_id}", response_model=ConversationWithMessages)
async def get_conversation(conv_id: int, db: DbDep):
    """返回会话详情及所有消息。"""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conv_id)
    )
    conv = result.scalar_one_or_none()
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv_id)
        .order_by(Message.created_at)
    )
    messages = list(msg_result.scalars().all())

    return ConversationWithMessages(
        id=conv.id,
        user_id=conv.user_id,
        title=conv.title,
        created_at=conv.created_at,
        messages=[MessageOut.model_validate(m) for m in messages],
    )


@router.get("/conversations/{conv_id}/messages", response_model=list[MessageOut])
async def list_messages(conv_id: int, db: DbDep):
    """返回某会话的消息列表（升序）。"""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv_id)
        .order_by(Message.created_at)
    )
    return result.scalars().all()


@router.delete("/conversations/{conv_id}", status_code=204)
async def delete_conversation(conv_id: int, db: DbDep):
    """删除会话及其所有消息。"""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conv_id)
    )
    conv = result.scalar_one_or_none()
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await db.delete(conv)
    await db.commit()
