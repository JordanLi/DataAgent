"""ConversationManager: 对话历史的读写与上下文拼接。

职责:
- 创建 / 加载会话
- 从 DB 读取最近 N 轮对话，转成 LLM messages 格式
- 将 user / assistant 消息持久化到 DB
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message, MessageRole


class ConversationManager:
    """管理单个 AsyncSession 内的对话历史。"""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # 会话管理
    # ------------------------------------------------------------------

    async def create_conversation(
        self,
        user_id: int,
        title: str | None = None,
    ) -> Conversation:
        """创建并持久化一个新会话。"""
        conv = Conversation(user_id=user_id, title=title)
        self._db.add(conv)
        await self._db.commit()
        await self._db.refresh(conv)
        return conv

    async def get_conversation(self, conversation_id: int) -> Conversation | None:
        result = await self._db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def list_conversations(self, user_id: int) -> list[Conversation]:
        result = await self._db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.created_at.desc())
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # 消息管理
    # ------------------------------------------------------------------

    async def get_history(
        self,
        conversation_id: int,
        max_turns: int = 5,
    ) -> list[dict]:
        """返回最近 *max_turns* 轮对话，格式为 LLM messages list。

        每轮包含一条 user 消息和一条 assistant 消息（共 2 * max_turns 条）。
        结果按时间升序排列（最旧的在前），便于 LLM 理解上下文。
        """
        result = await self._db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(max_turns * 2)
        )
        messages = list(reversed(result.scalars().all()))

        return [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages
        ]

    async def save_message(
        self,
        conversation_id: int,
        role: MessageRole,
        content: str,
        sql_generated: str | None = None,
        execution_time_ms: int | None = None,
        row_count: int | None = None,
    ) -> Message:
        """将一条消息写入 DB。"""
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            sql_generated=sql_generated,
            execution_time_ms=execution_time_ms,
            row_count=row_count,
        )
        self._db.add(msg)
        await self._db.commit()
        await self._db.refresh(msg)
        return msg

    async def get_messages(self, conversation_id: int) -> list[Message]:
        """返回某会话的全部消息（升序）。"""
        result = await self._db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        return list(result.scalars().all())

    async def update_conversation_title(
        self, conversation_id: int, title: str
    ) -> None:
        """用第一个用户问题作为会话标题（首次对话后调用）。"""
        conv = await self.get_conversation(conversation_id)
        if conv and not conv.title:
            conv.title = title[:128]
            await self._db.commit()
