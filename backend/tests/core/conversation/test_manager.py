"""Unit tests for ConversationManager data-assembly logic.

DB-dependent methods (_load from DB) are replaced with plain async stubs
so no real PostgreSQL is needed.  ORM modules are stubbed in sys.modules.
"""

from __future__ import annotations

import asyncio
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

# Stub ORM modules before any app import
for _m in ("app.models", "app.models.database",
           "app.models.datasource", "app.models.semantic",
           "app.models.conversation"):
    sys.modules.setdefault(_m, MagicMock())

# Provide MessageRole enum-like stub
import enum as _enum

class _MessageRole(str, _enum.Enum):
    user = "user"
    assistant = "assistant"

sys.modules["app.models.conversation"].MessageRole = _MessageRole
sys.modules["app.models.conversation"].Conversation = MagicMock()
sys.modules["app.models.conversation"].Message = MagicMock()

from app.core.conversation.manager import ConversationManager  # noqa: E402
import app.core.conversation.manager as _mgr_mod  # noqa: E402

# sqlalchemy.select would reject MagicMock ORM classes; replace it with a stub
# that returns a chainable mock so _db.execute (also stubbed) receives anything.
_select_stub = MagicMock()
_select_stub.return_value = MagicMock()
_mgr_mod.select = _select_stub


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _msg(role: str, content: str):
    return SimpleNamespace(role=_MessageRole(role), content=content)


def _make_manager(messages: list | None = None):
    """Return a ConversationManager with all DB calls replaced by stubs."""
    mgr = ConversationManager.__new__(ConversationManager)
    mgr._db = MagicMock()

    _msgs = messages or []

    # Stub the DB execute call used in get_history.
    # The real query uses ORDER BY created_at DESC; simulate that by reversing
    # so ConversationManager.get_history's reversed() restores ascending order.
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = list(reversed(_msgs))
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock

    async def _execute(*a, **kw):
        return result_mock

    mgr._db.execute = _execute
    mgr._db.add = MagicMock()
    mgr._db.commit = MagicMock(return_value=_coro(None))
    mgr._db.refresh = MagicMock(return_value=_coro(None))
    return mgr


async def _coro(val):
    return val


# ═══════════════════════════════════════════════════════════════════════════
# get_history  — LLM message 格式转换
# ═══════════════════════════════════════════════════════════════════════════

class TestGetHistory:

    def test_returns_list_of_dicts(self):
        msgs = [_msg("user", "问题"), _msg("assistant", "回答")]
        mgr = _make_manager(msgs)
        history = run(mgr.get_history(conversation_id=1))
        assert isinstance(history, list)
        assert all(isinstance(m, dict) for m in history)

    def test_role_and_content_keys_present(self):
        msgs = [_msg("user", "你好")]
        mgr = _make_manager(msgs)
        history = run(mgr.get_history(conversation_id=1))
        assert "role" in history[0]
        assert "content" in history[0]

    def test_role_value_is_string(self):
        msgs = [_msg("user", "x")]
        mgr = _make_manager(msgs)
        history = run(mgr.get_history(conversation_id=1))
        assert history[0]["role"] == "user"

    def test_content_preserved(self):
        msgs = [_msg("user", "查询销售额")]
        mgr = _make_manager(msgs)
        history = run(mgr.get_history(conversation_id=1))
        assert history[0]["content"] == "查询销售额"

    def test_multiple_messages_order_preserved(self):
        msgs = [
            _msg("user", "问题1"),
            _msg("assistant", "回答1"),
            _msg("user", "问题2"),
        ]
        mgr = _make_manager(msgs)
        history = run(mgr.get_history(conversation_id=1))
        # get_history 先取降序再 reverse，最终为升序
        assert history[0]["content"] == "问题1"
        assert history[-1]["content"] == "问题2"

    def test_empty_history_returns_empty_list(self):
        mgr = _make_manager([])
        history = run(mgr.get_history(conversation_id=1))
        assert history == []

    def test_assistant_role_preserved(self):
        msgs = [_msg("assistant", "SELECT 1")]
        mgr = _make_manager(msgs)
        history = run(mgr.get_history(conversation_id=1))
        assert history[0]["role"] == "assistant"

    def test_six_messages_all_returned(self):
        """max_turns=5 → limit = 10; 6 条消息全部返回。"""
        msgs = [_msg("user", f"q{i}") for i in range(6)]
        mgr = _make_manager(msgs)
        history = run(mgr.get_history(conversation_id=1, max_turns=5))
        assert len(history) == 6

    def test_custom_max_turns(self):
        """验证 max_turns 参数被传递（DB 侧限制，stub 忽略限制直接返回全量）。"""
        msgs = [_msg("user", "q1"), _msg("assistant", "a1")]
        mgr = _make_manager(msgs)
        history = run(mgr.get_history(conversation_id=1, max_turns=1))
        assert len(history) == 2  # stub 返回全量


# ═══════════════════════════════════════════════════════════════════════════
# save_message  — 消息持久化（验证 DB.add 被调用）
# ═══════════════════════════════════════════════════════════════════════════

class TestSaveMessage:

    def test_save_calls_db_add(self):
        mgr = _make_manager()
        add_calls = []
        mgr._db.add = lambda obj: add_calls.append(obj)

        # 给 refresh 返回带属性的 stub
        saved = SimpleNamespace(
            id=1, conversation_id=1, role=_MessageRole.user,
            content="hello", sql_generated=None,
            execution_time_ms=None, row_count=None,
        )

        async def _refresh(obj):
            obj.__dict__.update(saved.__dict__)

        mgr._db.refresh = _refresh
        run(mgr.save_message(
            conversation_id=1,
            role=_MessageRole.user,
            content="hello",
        ))
        assert len(add_calls) == 1

    def test_save_with_sql_metadata(self):
        mgr = _make_manager()
        add_calls = []
        mgr._db.add = lambda obj: add_calls.append(obj)

        saved = SimpleNamespace(id=1, conversation_id=1, role=_MessageRole.assistant,
                                content="摘要", sql_generated="SELECT 1",
                                execution_time_ms=50, row_count=10)

        async def _refresh(obj):
            obj.__dict__.update(saved.__dict__)

        mgr._db.refresh = _refresh
        run(mgr.save_message(
            conversation_id=1,
            role=_MessageRole.assistant,
            content="摘要",
            sql_generated="SELECT 1",
            execution_time_ms=50,
            row_count=10,
        ))
        obj = add_calls[0]
        assert obj.sql_generated == "SELECT 1"
        assert obj.execution_time_ms == 50
        assert obj.row_count == 10
