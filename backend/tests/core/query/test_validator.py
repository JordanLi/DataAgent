"""Unit tests for SQLValidator.

SQLValidator is pure-logic (no DB, no LLM, no async).
All tests are synchronous and run without any patching.
"""

from __future__ import annotations

import pytest

from app.core.query.validator import SQLValidator, ValidationError


def v(known_tables=None, default_limit=100, max_limit=10_000):
    return SQLValidator(
        default_limit=default_limit,
        max_limit=max_limit,
        known_tables=known_tables,
    )


# ═══════════════════════════════════════════════════════════════════════════
# 基本合法 SELECT
# ═══════════════════════════════════════════════════════════════════════════

class TestValidSelect:

    def test_simple_select_passes(self):
        sql = v().validate_and_rewrite("SELECT id FROM users")
        assert "SELECT" in sql.upper()

    def test_select_with_where_passes(self):
        sql = v().validate_and_rewrite(
            "SELECT id, name FROM orders WHERE status = 1"
        )
        assert sql  # 不抛出即通过

    def test_select_with_join_passes(self):
        sql = v().validate_and_rewrite(
            "SELECT o.id, u.name FROM orders o JOIN users u ON o.user_id = u.id"
        )
        assert sql

    def test_select_with_group_by_passes(self):
        sql = v().validate_and_rewrite(
            "SELECT status, COUNT(*) FROM orders GROUP BY status"
        )
        assert sql

    def test_trailing_semicolon_stripped(self):
        sql = v().validate_and_rewrite("SELECT 1;")
        assert ";" not in sql

    def test_select_star_passes(self):
        sql = v().validate_and_rewrite("SELECT * FROM products LIMIT 10")
        assert sql


# ═══════════════════════════════════════════════════════════════════════════
# 拒绝非 SELECT 语句
# ═══════════════════════════════════════════════════════════════════════════

class TestRejectNonSelect:

    def test_insert_rejected(self):
        with pytest.raises(ValidationError, match="INSERT"):
            v().validate_and_rewrite("INSERT INTO users VALUES (1,'a')")

    def test_update_rejected(self):
        with pytest.raises(ValidationError, match="UPDATE"):
            v().validate_and_rewrite("UPDATE users SET name='x' WHERE id=1")

    def test_delete_rejected(self):
        with pytest.raises(ValidationError, match="DELETE"):
            v().validate_and_rewrite("DELETE FROM users WHERE id=1")

    def test_drop_rejected(self):
        with pytest.raises(ValidationError):
            v().validate_and_rewrite("DROP TABLE users")

    def test_create_rejected(self):
        with pytest.raises(ValidationError):
            v().validate_and_rewrite("CREATE TABLE t (id INT)")

    def test_alter_rejected(self):
        with pytest.raises(ValidationError):
            v().validate_and_rewrite("ALTER TABLE users ADD COLUMN age INT")

    def test_truncate_rejected(self):
        with pytest.raises(ValidationError):
            v().validate_and_rewrite("TRUNCATE TABLE users")


# ═══════════════════════════════════════════════════════════════════════════
# 危险模式检测
# ═══════════════════════════════════════════════════════════════════════════

class TestDangerousPatterns:

    def test_into_outfile_rejected(self):
        with pytest.raises(ValidationError, match="危险"):
            v().validate_and_rewrite(
                "SELECT * FROM users INTO OUTFILE '/tmp/dump.txt'"
            )

    def test_load_file_rejected(self):
        with pytest.raises(ValidationError, match="危险"):
            v().validate_and_rewrite(
                "SELECT LOAD_FILE('/etc/passwd')"
            )

    def test_sleep_rejected(self):
        with pytest.raises(ValidationError, match="危险"):
            v().validate_and_rewrite("SELECT SLEEP(5)")

    def test_benchmark_rejected(self):
        with pytest.raises(ValidationError, match="危险"):
            v().validate_and_rewrite("SELECT BENCHMARK(1000000, MD5('x'))")

    def test_information_schema_rejected(self):
        with pytest.raises(ValidationError, match="危险"):
            v().validate_and_rewrite(
                "SELECT table_name FROM information_schema.tables"
            )

    def test_block_comment_rejected(self):
        with pytest.raises(ValidationError, match="危险"):
            v().validate_and_rewrite("SELECT /* comment */ 1")


# ═══════════════════════════════════════════════════════════════════════════
# LIMIT 自动补充与截断
# ═══════════════════════════════════════════════════════════════════════════

class TestLimit:

    def test_limit_injected_when_missing(self):
        sql = v(default_limit=50).validate_and_rewrite(
            "SELECT id FROM users"
        )
        assert "LIMIT 50" in sql.upper()

    def test_existing_limit_preserved_when_under_max(self):
        sql = v(default_limit=100, max_limit=1000).validate_and_rewrite(
            "SELECT id FROM users LIMIT 200"
        )
        assert "LIMIT 200" in sql.upper()

    def test_overlimit_truncated_to_max(self):
        sql = v(default_limit=100, max_limit=500).validate_and_rewrite(
            "SELECT id FROM users LIMIT 9999"
        )
        assert "LIMIT 500" in sql.upper()

    def test_exact_max_limit_preserved(self):
        sql = v(default_limit=100, max_limit=1000).validate_and_rewrite(
            "SELECT id FROM users LIMIT 1000"
        )
        assert "LIMIT 1000" in sql.upper()

    def test_limit_1_preserved(self):
        sql = v().validate_and_rewrite("SELECT id FROM users LIMIT 1")
        assert "LIMIT 1" in sql.upper()


# ═══════════════════════════════════════════════════════════════════════════
# 已知表名校验
# ═══════════════════════════════════════════════════════════════════════════

class TestKnownTables:

    def test_known_table_passes(self):
        sql = v(known_tables=["users", "orders"]).validate_and_rewrite(
            "SELECT id FROM users"
        )
        assert sql

    def test_unknown_table_rejected(self):
        with pytest.raises(ValidationError, match="未知表"):
            v(known_tables=["users"]).validate_and_rewrite(
                "SELECT id FROM secret_table"
            )

    def test_no_known_tables_skips_check(self):
        # known_tables=None → 不检查表名
        sql = v(known_tables=None).validate_and_rewrite(
            "SELECT id FROM any_table_name"
        )
        assert sql

    def test_join_with_known_tables_passes(self):
        sql = v(known_tables=["orders", "users"]).validate_and_rewrite(
            "SELECT o.id FROM orders o JOIN users u ON o.user_id = u.id"
        )
        assert sql

    def test_join_with_unknown_table_rejected(self):
        with pytest.raises(ValidationError, match="未知表"):
            v(known_tables=["orders"]).validate_and_rewrite(
                "SELECT o.id FROM orders o JOIN ghost_table g ON o.id = g.id"
            )

    def test_table_name_check_case_insensitive(self):
        sql = v(known_tables=["Orders"]).validate_and_rewrite(
            "SELECT id FROM orders LIMIT 10"
        )
        assert sql
