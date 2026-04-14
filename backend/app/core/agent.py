"""AgentOrchestrator: NL-to-SQL 查询的核心编排器。

完整流程（每步通过 SSE yield 一个事件）：
  1. thinking   — 开始处理，显示"正在分析..."
  2. sql        — 流式输出 LLM 生成的 SQL
  3. validating — SQL 安全校验
  4. executing  — 执行查询，返回表格数据
  5. summary    — LLM 生成自然语言摘要 + 图表建议
  6. done / error

SSE 事件格式（每条都是 JSON 字符串）：
  {"type": "thinking", "content": "..."}
  {"type": "sql",      "content": "SELECT ..."}
  {"type": "result",   "columns": [...], "rows": [...], "row_count": N, "truncated": bool, "execution_time_ms": N}
  {"type": "summary",  "content": "...", "chart_type": "bar"}
  {"type": "done"}
  {"type": "error",    "content": "..."}
"""

from __future__ import annotations

import json
import logging
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.connectors import build_connector
from app.core.conversation.manager import ConversationManager
from app.core.llm.factory import create_llm
from app.core.query.executor import QueryExecutor
from app.core.query.generator import SQLGenerator, extract_sql
from app.core.query.validator import SQLValidator, ValidationError
from app.core.semantic.engine import SemanticEngine
from app.core.semantic.loader import SemanticLoader
from app.models.audit import AuditLog
from app.models.conversation import MessageRole
from app.models.datasource import DataSource

logger = logging.getLogger(__name__)


def _event(data: dict) -> str:
    """将 dict 序列化为 SSE data 行。"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


class AgentOrchestrator:
    """将用户自然语言问题编排为完整的 SQL 查询 + 结果 + 摘要流程。"""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._settings = get_settings()

    async def process_query(
        self,
        question: str,
        datasource_id: int,
        conversation_id: int | None = None,
        user_id: int = 1,
    ) -> AsyncIterator[str]:
        """执行完整查询流程，yield SSE 事件字符串。

        Args:
            question:        用户的自然语言问题
            datasource_id:   目标数据源 ID
            conversation_id: 已有会话 ID，None 表示新建会话
            user_id:         当前用户 ID
        """
        async for event in self._run(question, datasource_id, conversation_id, user_id):
            yield event

    async def _run(
        self,
        question: str,
        datasource_id: int,
        conversation_id: int | None,
        user_id: int,
    ) -> AsyncIterator[str]:
        conv_mgr = ConversationManager(self._db)
        llm = create_llm(self._settings)
        settings = self._settings

        # ── 1. 确保会话存在 ──────────────────────────────────────────
        if conversation_id is None:
            conv = await conv_mgr.create_conversation(user_id)
            conversation_id = conv.id
        await conv_mgr.update_conversation_title(conversation_id, question)

        # ── 保存用户消息 ─────────────────────────────────────────────
        await conv_mgr.save_message(
            conversation_id, MessageRole.user, question
        )

        yield _event({"type": "thinking", "content": "正在加载 Schema 和语义配置..."})

        try:
            # ── 2. 加载数据源 & 语义上下文 ───────────────────────────
            datasource = await self._db.get(DataSource, datasource_id)
            if datasource is None:
                yield _event({"type": "error", "content": f"数据源 {datasource_id} 不存在"})
                return

            semantic_loader = SemanticLoader(self._db)
            sem_ctx = await semantic_loader.load_full_context(datasource_id)
            schema_ctx = SemanticEngine.build_schema_prompt(sem_ctx)
            semantic_ctx = ""  # Currently bundled into schema_ctx
            known_tables = list(sem_ctx["schema"].keys())

            # ── 3. 加载对话历史 ──────────────────────────────────────
            history = await conv_mgr.get_history(
                conversation_id, max_turns=5
            )
            # 移除刚保存的用户消息（避免重复）
            if history and history[-1]["role"] == "user":
                history = history[:-1]

            # ── 4. 生成 SQL（流式） ──────────────────────────────────
            yield _event({"type": "thinking", "content": "正在生成 SQL..."})

            generator = SQLGenerator(
                llm=llm,
                default_limit=settings.default_sql_limit,
            )

            full_response = ""
            async for chunk in generator.generate_stream(
                question=question,
                schema_context=schema_ctx,
                semantic_context=semantic_ctx,
                history=history,
            ):
                full_response += chunk
                yield _event({"type": "sql_stream", "content": chunk})

            raw_sql = extract_sql(full_response)
            if not raw_sql:
                from app.core.query.generator import force_extract_sql
                raw_sql = force_extract_sql(full_response)

            if not raw_sql:
                raise ValueError("LLM 未返回有效 SQL，请重新提问")

            yield _event({"type": "sql", "content": raw_sql})

            # ── 5. SQL 安全校验 ──────────────────────────────────────
            yield _event({"type": "thinking", "content": "正在校验 SQL 安全性..."})

            validator = SQLValidator(
                default_limit=settings.default_sql_limit,
                max_limit=settings.query_max_rows,
                known_tables=known_tables if known_tables else None,
            )
            try:
                safe_sql = validator.validate_and_rewrite(raw_sql)
            except ValidationError as ve:
                yield _event({"type": "error", "content": f"SQL 校验失败: {ve}"})
                return

            # 如果重写后的 SQL 与原始不同，通知前端
            if safe_sql != raw_sql:
                yield _event({"type": "sql_rewritten", "content": safe_sql})

            # ── 6. 执行查询 ──────────────────────────────────────────
            yield _event({"type": "thinking", "content": "正在执行查询..."})

            connector = build_connector(datasource)
            try:
                executor = QueryExecutor(
                    connector=connector,
                    timeout=settings.query_timeout_seconds,
                    max_rows=settings.query_max_rows,
                )
                result = await executor.execute(safe_sql)
            finally:
                await connector.close()

            yield _event({
                "type": "result",
                "columns": result["columns"],
                "rows": result["rows"],
                "row_count": result["row_count"],
                "execution_time_ms": result["execution_time_ms"],
                "truncated": result["truncated"],
            })

            # ── 7. 生成摘要 & 图表建议 ───────────────────────────────
            yield _event({"type": "thinking", "content": "正在生成分析摘要..."})

            insight = await generator.generate_summary(
                question=question,
                sql=safe_sql,
                columns=result["columns"],
                rows=result["rows"],
                row_count=result["row_count"],
            )

            yield _event({
                "type": "summary",
                "content": insight.get("summary", ""),
                "chart_type": insight.get("chart_type", "table"),
            })

            # ── 8. 保存 assistant 消息 ───────────────────────────────
            summary_text = insight.get("summary", "")
            await conv_mgr.save_message(
                conversation_id=conversation_id,
                role=MessageRole.assistant,
                content=summary_text,
                sql_generated=safe_sql,
                execution_time_ms=result["execution_time_ms"],
                row_count=result["row_count"],
            )

            # ── 9. 写入审计日志 ──────────────────────────────────────
            audit = AuditLog(
                user_id=user_id,
                action="query",
                datasource_id=datasource_id,
                sql_executed=safe_sql,
                row_count=result["row_count"],
                duration_ms=result["execution_time_ms"],
            )
            self._db.add(audit)
            await self._db.commit()

            yield _event({"type": "done", "conversation_id": conversation_id})

        except Exception as exc:  # noqa: BLE001
            logger.exception("AgentOrchestrator 处理失败: %s", exc)
            # 尽力写入失败审计日志（不阻塞主流程）
            try:
                audit = AuditLog(
                    user_id=user_id,
                    action="query_error",
                    datasource_id=datasource_id,
                    sql_executed=None,
                    row_count=None,
                    duration_ms=None,
                )
                self._db.add(audit)
                await self._db.commit()
            except Exception:  # noqa: BLE001
                pass
            yield _event({"type": "error", "content": str(exc)})
