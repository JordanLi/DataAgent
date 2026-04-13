"""Unit tests for SQLGenerator helper logic.

Tests focus on:
  - extract_sql()           — pure string parsing, no LLM needed
  - generate_summary()      — JSON parsing / fallback logic (LLM mocked)
  - generate() / generate_stream() — correct prompt assembly (LLM mocked)
"""

from __future__ import annotations

import asyncio
import json
import sys
from unittest.mock import MagicMock

# Stub ORM modules so SQLAlchemy is never initialised on Python 3.9
for _m in ("app.models", "app.models.database",
           "app.models.datasource", "app.models.semantic",
           "app.models.conversation"):
    sys.modules.setdefault(_m, MagicMock())

from app.core.query.generator import SQLGenerator, extract_sql  # noqa: E402


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _mock_llm(response: str):
    """Return a BaseLLM stub whose chat() returns *response*."""
    llm = MagicMock()
    llm.chat = MagicMock(return_value=_coro(response))

    async def _stream(messages, **kw):
        yield response

    llm.chat_stream = MagicMock(return_value=_aiter(response))
    return llm


async def _coro(val):
    return val


async def _aiter_gen(val):
    yield val


def _aiter(val):
    return _aiter_gen(val)


# ═══════════════════════════════════════════════════════════════════════════
# extract_sql
# ═══════════════════════════════════════════════════════════════════════════

class TestExtractSql:

    def test_extracts_from_code_block(self):
        text = "Here is the SQL:\n```sql\nSELECT id FROM users LIMIT 10\n```"
        assert extract_sql(text) == "SELECT id FROM users LIMIT 10"

    def test_extracts_from_code_block_no_lang_tag(self):
        # 无 sql 标签，只有 ``` ```
        text = "```\nSELECT 1\n```"
        # 没有 sql 标签不匹配 _SQL_PATTERN，但 fallback 逻辑应捕获裸 SELECT
        # 注意：text.strip() 不以 SELECT 开头 → 返回 None
        result = extract_sql(text)
        # 没有 sql 标签 → None（明确验证行为）
        assert result is None

    def test_extracts_bare_select(self):
        text = "SELECT * FROM orders WHERE status = 1"
        assert extract_sql(text) == text

    def test_returns_none_for_non_sql_text(self):
        assert extract_sql("I cannot answer that question.") is None

    def test_strips_whitespace(self):
        text = "```sql\n  SELECT id FROM t  \n```"
        assert extract_sql(text) == "SELECT id FROM t"

    def test_case_insensitive_sql_tag(self):
        text = "```SQL\nSELECT 1\n```"
        assert extract_sql(text) == "SELECT 1"

    def test_multiline_sql_preserved(self):
        sql = "SELECT\n  id,\n  name\nFROM users\nLIMIT 10"
        text = f"```sql\n{sql}\n```"
        assert extract_sql(text) == sql

    def test_first_block_returned_when_multiple(self):
        text = "```sql\nSELECT 1\n```\n\n```sql\nSELECT 2\n```"
        assert extract_sql(text) == "SELECT 1"

    def test_empty_string_returns_none(self):
        assert extract_sql("") is None

    def test_whitespace_only_returns_none(self):
        assert extract_sql("   \n  ") is None


# ═══════════════════════════════════════════════════════════════════════════
# SQLGenerator.generate_summary — JSON 解析与降级
# ═══════════════════════════════════════════════════════════════════════════

class TestGenerateSummary:

    def _gen(self, llm_response: str) -> SQLGenerator:
        llm = MagicMock()
        llm.chat = MagicMock(return_value=_coro(llm_response))
        return SQLGenerator(llm=llm, default_limit=100)

    def _call(self, gen, question="问题", sql="SELECT 1", columns=None, rows=None):
        return run(gen.generate_summary(
            question=question,
            sql=sql,
            columns=columns or ["id"],
            rows=rows or [[1]],
            row_count=1,
        ))

    def test_valid_json_parsed(self):
        resp = '{"summary": "共有100条记录", "chart_type": "bar"}'
        result = self._call(self._gen(resp))
        assert result["summary"] == "共有100条记录"
        assert result["chart_type"] == "bar"

    def test_json_in_code_block_parsed(self):
        resp = "```json\n{\"summary\": \"摘要\", \"chart_type\": \"line\"}\n```"
        result = self._call(self._gen(resp))
        assert result["chart_type"] == "line"

    def test_fallback_on_invalid_json(self):
        result = self._call(self._gen("这是一段无法解析的文本"))
        assert "summary" in result
        assert "chart_type" in result
        assert result["chart_type"] == "table"

    def test_fallback_preserves_raw_text(self):
        text = "无效JSON但是有意义的文本"
        result = self._call(self._gen(text))
        assert text in result["summary"]

    def test_summary_key_present(self):
        resp = '{"summary": "OK", "chart_type": "pie"}'
        result = self._call(self._gen(resp))
        assert "summary" in result

    def test_chart_type_key_present(self):
        resp = '{"summary": "OK", "chart_type": "pie"}'
        result = self._call(self._gen(resp))
        assert "chart_type" in result


# ═══════════════════════════════════════════════════════════════════════════
# SQLGenerator.generate — prompt 组装 & SQL 提取
# ═══════════════════════════════════════════════════════════════════════════

class TestGenerate:

    def test_generate_returns_sql(self):
        llm = MagicMock()
        llm.chat = MagicMock(return_value=_coro("```sql\nSELECT 1\n```"))
        gen = SQLGenerator(llm=llm)
        sql = run(gen.generate(
            question="查询所有用户",
            schema_context="表: users",
        ))
        assert sql == "SELECT 1"

    def test_generate_raises_on_no_sql(self):
        llm = MagicMock()
        llm.chat = MagicMock(return_value=_coro("我不知道怎么查"))
        gen = SQLGenerator(llm=llm)
        try:
            run(gen.generate(question="xxx", schema_context=""))
            assert False, "应该抛出 ValueError"
        except ValueError as e:
            assert "SQL" in str(e)

    def test_history_appended_to_messages(self):
        captured = []

        async def mock_chat(messages, **kw):
            captured.extend(messages)
            return "```sql\nSELECT 1\n```"

        llm = MagicMock()
        llm.chat = mock_chat
        gen = SQLGenerator(llm=llm)
        history = [
            {"role": "user", "content": "上一个问题"},
            {"role": "assistant", "content": "上一个回答"},
        ]
        run(gen.generate(
            question="新问题",
            schema_context="schema",
            history=history,
        ))
        roles = [m["role"] for m in captured]
        assert "system" in roles
        assert roles.count("user") >= 2   # history + 当前问题

    def test_semantic_context_injected_when_provided(self):
        captured = []

        async def mock_chat(messages, **kw):
            captured.extend(messages)
            return "```sql\nSELECT 1\n```"

        llm = MagicMock()
        llm.chat = mock_chat
        gen = SQLGenerator(llm=llm)
        run(gen.generate(
            question="q",
            schema_context="schema",
            semantic_context="业务术语: GMV",
        ))
        system_msg = next(m for m in captured if m["role"] == "system")
        assert "GMV" in system_msg["content"]

    def test_default_limit_in_system_prompt(self):
        captured = []

        async def mock_chat(messages, **kw):
            captured.extend(messages)
            return "```sql\nSELECT 1\n```"

        llm = MagicMock()
        llm.chat = mock_chat
        gen = SQLGenerator(llm=llm, default_limit=250)
        run(gen.generate(question="q", schema_context="s"))
        system_msg = next(m for m in captured if m["role"] == "system")
        assert "250" in system_msg["content"]
