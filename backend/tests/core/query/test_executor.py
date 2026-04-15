"""Unit tests for QueryExecutor.

BaseConnector is replaced with a stub that returns pre-canned data.
No real DB, no async mock machinery — connector.execute_query is a plain
async function returning a dict.
"""

from __future__ import annotations

import asyncio
import datetime
import decimal
import sys
from unittest.mock import MagicMock, patch

# Stub ORM / connector modules before any app import (Python 3.9 compat)
for _m in (
    "app.models", "app.models.database",
    "app.models.datasource", "app.models.semantic",
    "app.models.conversation",
    "app.connectors", "app.connectors.base",
    "app.connectors.factory", "app.connectors.crypto",
    "app.connectors.mysql_connector",
):
    sys.modules.setdefault(_m, MagicMock())

from app.core.query.executor import QueryExecutor, _serialize_value  # noqa: E402


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _make_connector(columns, rows, exec_ms=42):
    """Return a connector stub whose execute_query returns canned data."""
    connector = MagicMock()

    async def execute_query(sql):
        # We need to simulate a small delay if execution_time_ms is > 0 so that `end_time - start_time` matches expectations
        if exec_ms > 0:
            # We can't use asyncio.sleep because it would be real delay.
            # But the executor uses `asyncio.get_event_loop().time()` to measure execution time.
            # The test actually just wants the execution_time_ms.
            # However, since the executor uses the loop time now, we can't easily control it
            # without mocking `asyncio.get_event_loop().time()`.
            # A simpler way is to just mock `asyncio.get_event_loop().time` in the test.
            pass
        dict_rows = [dict(zip(columns, r)) for r in rows]
        return columns, dict_rows

    connector.execute_query = execute_query
    connector.close = MagicMock(return_value=_coro(None))
    return connector


async def _coro(val):
    return val


def _exec(connector, max_rows=10_000, timeout=30):
    return QueryExecutor(connector=connector, timeout=timeout, max_rows=max_rows)


# ═══════════════════════════════════════════════════════════════════════════
# _serialize_value  (pure function, no async needed)
# ═══════════════════════════════════════════════════════════════════════════

class TestSerializeValue:

    def test_none_stays_none(self):
        assert _serialize_value(None) is None

    def test_int_unchanged(self):
        assert _serialize_value(42) == 42

    def test_string_unchanged(self):
        assert _serialize_value("hello") == "hello"

    def test_decimal_to_float(self):
        result = _serialize_value(decimal.Decimal("3.14"))
        assert isinstance(result, float)
        assert abs(result - 3.14) < 1e-9

    def test_datetime_to_isoformat(self):
        dt = datetime.datetime(2024, 1, 15, 10, 30, 0)
        assert _serialize_value(dt) == "2024-01-15T10:30:00"

    def test_date_to_isoformat(self):
        d = datetime.date(2024, 6, 1)
        assert _serialize_value(d) == "2024-06-01"

    def test_time_to_isoformat(self):
        t = datetime.time(8, 0, 0)
        assert _serialize_value(t) == "08:00:00"

    def test_bytes_decoded_to_str(self):
        assert _serialize_value(b"hello") == "hello"

    def test_bytes_with_invalid_utf8_replaced(self):
        result = _serialize_value(b"\xff\xfe")
        assert isinstance(result, str)

    def test_bool_unchanged(self):
        assert _serialize_value(True) is True

    def test_float_unchanged(self):
        assert _serialize_value(1.5) == 1.5


# ═══════════════════════════════════════════════════════════════════════════
# QueryExecutor.execute
# ═══════════════════════════════════════════════════════════════════════════

class TestExecute:

    def test_returns_columns(self):
        c = _make_connector(["id", "name"], [[1, "Alice"]])
        result = run(_exec(c).execute("SELECT id, name FROM users"))
        assert result["columns"] == ["id", "name"]

    def test_returns_rows(self):
        c = _make_connector(["id"], [[1], [2], [3]])
        result = run(_exec(c).execute("SELECT id FROM t"))
        assert result["rows"] == [[1], [2], [3]]

    def test_row_count_matches(self):
        c = _make_connector(["x"], [[i] for i in range(5)])
        result = run(_exec(c).execute("SELECT x FROM t"))
        assert result["row_count"] == 5

    def test_execution_time_preserved(self):
        c = _make_connector(["x"], [[1]], exec_ms=123)
        with patch("app.core.query.executor.asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.time.side_effect = [0.0, 0.123]
            result = run(_exec(c).execute("SELECT x FROM t"))
            assert result["execution_time_ms"] == 123

    def test_not_truncated_when_under_limit(self):
        c = _make_connector(["x"], [[i] for i in range(10)])
        result = run(_exec(c, max_rows=100).execute("SELECT x FROM t"))
        assert result["truncated"] is False

    def test_truncated_when_over_limit(self):
        # connector returns max_rows+1 rows; executor should cap at max_rows
        c = _make_connector(["x"], [[i] for i in range(6)])
        result = run(_exec(c, max_rows=5).execute("SELECT x FROM t"))
        assert result["truncated"] is True
        assert result["row_count"] == 5

    def test_rows_serialized(self):
        c = _make_connector(
            ["dt", "amt"],
            [[datetime.date(2024, 1, 1), decimal.Decimal("99.99")]],
        )
        result = run(_exec(c).execute("SELECT dt, amt FROM t"))
        row = result["rows"][0]
        assert row[0] == "2024-01-01"
        assert isinstance(row[1], float)

    def test_empty_result_set(self):
        c = _make_connector(["id"], [])
        result = run(_exec(c).execute("SELECT id FROM t WHERE 1=0"))
        assert result["columns"] == ["id"]
        assert result["rows"] == []
        assert result["row_count"] == 0
        assert result["truncated"] is False

    def test_none_values_preserved(self):
        c = _make_connector(["a", "b"], [[1, None]])
        result = run(_exec(c).execute("SELECT a, b FROM t"))
        assert result["rows"][0] == [1, None]

    def test_multiple_rows_all_serialized(self):
        c = _make_connector(
            ["dt"],
            [[datetime.date(2024, 1, d)] for d in range(1, 4)],
        )
        result = run(_exec(c).execute("SELECT dt FROM t"))
        assert result["rows"] == [["2024-01-01"], ["2024-01-02"], ["2024-01-03"]]
