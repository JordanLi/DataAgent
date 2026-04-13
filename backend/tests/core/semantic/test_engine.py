"""Unit tests for SemanticEngine rendering logic.

No database, no SQLAlchemy, no network.
sys.modules patching at the top ensures ORM models are never initialised
(required for Python 3.9 compatibility; production runtime is Python 3.11).
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# ── Patch ORM-dependent modules BEFORE any app imports ───────────────────────
for _m in (
    "app.models",
    "app.models.database",
    "app.models.datasource",
    "app.models.semantic",
):
    sys.modules.setdefault(_m, MagicMock())

# ── Now import the pure-Python types (zero ORM deps) ─────────────────────────
from app.core.semantic.types import ColumnInfo, SemanticContext, TableInfo  # noqa: E402

# ── Import engine directly (bypasses __init__.py eager chain) ────────────────
from app.core.semantic.engine import SemanticEngine  # noqa: E402


# ── Helper: build SemanticEngine without a real DB session ───────────────────

def make_engine() -> SemanticEngine:
    engine = SemanticEngine.__new__(SemanticEngine)
    engine._loader = MagicMock()
    return engine


# ── Column factory shorthand ─────────────────────────────────────────────────

def col(
    name: str,
    col_type: str = "INT",
    *,
    key: str | None = None,
    nullable: bool = False,
    comment: str | None = None,
    extra: str | None = None,
    alias: str | None = None,
    alias_desc: str | None = None,
    enum_labels: dict | None = None,
    fk_ref: str | None = None,
) -> ColumnInfo:
    return ColumnInfo(
        column_name=name,
        column_type=col_type,
        data_type=col_type.lower().split("(")[0],
        is_nullable=nullable,
        column_default=None,
        column_comment=comment,
        column_key=key,
        extra=extra,
        alias_name=alias,
        alias_description=alias_desc,
        enum_labels=enum_labels or {},
        foreign_key_ref=fk_ref,
    )


# ── Shared fixture-like context ───────────────────────────────────────────────

def make_ecommerce_ctx() -> SemanticContext:
    orders = TableInfo(
        table_name="orders",
        table_comment="订单表",
        columns=[
            col("id",         "INT",          key="PRI", extra="auto_increment", comment="订单ID"),
            col("user_id",    "INT",          key="MUL", comment="用户ID", fk_ref="users.id"),
            col("status",     "INT",          comment="订单状态",
                enum_labels={"1": "待支付", "2": "已支付", "3": "已发货",
                              "4": "已完成", "5": "已取消"}),
            col("amount",     "DECIMAL(10,2)", comment="订单金额"),
            col("created_at", "DATETIME",      comment="下单时间"),
        ],
    )
    users = TableInfo(
        table_name="users",
        table_comment="用户表",
        columns=[
            col("id",       "INT",         key="PRI", extra="auto_increment"),
            col("username", "VARCHAR(128)", nullable=False, comment="用户名"),
            col("email",    "VARCHAR(256)", key="UNI", comment="邮箱"),
        ],
    )
    return SemanticContext(
        database_name="ecommerce",
        tables=[orders, users],
        business_terms=[
            ("GMV",  "成交总金额",         "SUM(amount) WHERE status IN (2,3,4)"),
            ("客单价", "每个用户平均消费金额", "GMV / COUNT(DISTINCT user_id) WHERE status IN (2,3,4)"),
        ],
        relations=[
            ("orders", "user_id",    "users",    "id"),
            ("orders", "product_id", "products", "id"),
        ],
    )


# ═══════════════════════════════════════════════════════════════════════════
# build_schema_context
# ═══════════════════════════════════════════════════════════════════════════

class TestBuildSchemaContext:
    def setup_method(self):
        self.engine = make_engine()
        self.ctx    = make_ecommerce_ctx()

    def _schema(self):
        return self.engine.build_schema_context(self.ctx)

    def test_database_header(self):
        assert self._schema().startswith("数据库: ecommerce")

    def test_table_header_with_comment(self):
        assert "表: orders (订单表)" in self._schema()

    def test_table_header_without_comment(self):
        ctx = SemanticContext(
            database_name="db",
            tables=[TableInfo(table_name="raw_events", table_comment=None)],
        )
        out = self.engine.build_schema_context(ctx)
        assert "表: raw_events" in out
        assert "(None)" not in out

    def test_primary_key_marker(self):
        assert "主键" in self._schema()

    def test_auto_increment_marker(self):
        assert "自增" in self._schema()

    def test_unique_index_marker(self):
        assert "唯一索引" in self._schema()

    def test_mul_index_marker(self):
        assert "索引" in self._schema()

    def test_foreign_key_reference(self):
        assert "外键->users.id" in self._schema()

    def test_enum_labels_rendered(self):
        out = self._schema()
        assert "1=待支付" in out
        assert "5=已取消" in out

    def test_column_comment_as_description(self):
        assert "订单金额" in self._schema()

    def test_alias_overrides_display_name(self):
        ctx = SemanticContext(
            database_name="db",
            tables=[TableInfo("orders", None, [
                col("amt", "DECIMAL(10,2)", alias="金额", alias_desc="订单实付金额")
            ])],
        )
        out = self.engine.build_schema_context(ctx)
        assert "金额 [amt]" in out
        assert "订单实付金额" in out

    def test_alias_description_preferred_over_column_comment(self):
        ctx = SemanticContext(
            database_name="db",
            tables=[TableInfo("t", None, [
                col("c", "INT", comment="原始注释", alias_desc="别名描述")
            ])],
        )
        out = self.engine.build_schema_context(ctx)
        assert "别名描述" in out
        assert "原始注释" not in out

    def test_empty_table_placeholder(self):
        ctx = SemanticContext(
            database_name="db",
            tables=[TableInfo("empty_tbl", None, columns=[])],
        )
        assert "(无字段信息)" in self.engine.build_schema_context(ctx)

    def test_nullable_column_omits_nonnull_marker(self):
        ctx = SemanticContext(
            database_name="db",
            tables=[TableInfo("t", None, [col("notes", "TEXT", nullable=True)])],
        )
        assert "非空" not in self.engine.build_schema_context(ctx)

    def test_nonnullable_column_has_nonnull_marker(self):
        ctx = SemanticContext(
            database_name="db",
            tables=[TableInfo("t", None, [col("name", "VARCHAR(64)", nullable=False)])],
        )
        assert "非空" in self.engine.build_schema_context(ctx)

    def test_multiple_tables_all_present(self):
        out = self._schema()
        assert "表: orders" in out
        assert "表: users" in out

    def test_column_type_uppercased(self):
        ctx = SemanticContext(
            database_name="db",
            tables=[TableInfo("t", None, [col("x", "varchar(32)")])],
        )
        assert "VARCHAR(32)" in self.engine.build_schema_context(ctx)

    def test_no_tables_only_db_header(self):
        ctx = SemanticContext(database_name="empty_db")
        assert self.engine.build_schema_context(ctx) == "数据库: empty_db"


# ═══════════════════════════════════════════════════════════════════════════
# build_semantic_context
# ═══════════════════════════════════════════════════════════════════════════

class TestBuildSemanticContext:
    def setup_method(self):
        self.engine = make_engine()
        self.ctx    = make_ecommerce_ctx()

    def _sem(self):
        return self.engine.build_semantic_context(self.ctx)

    def test_business_terms_header(self):
        assert "业务术语:" in self._sem()

    def test_term_sql_expression_present(self):
        assert "SUM(amount) WHERE status IN (2,3,4)" in self._sem()

    def test_term_definition_present(self):
        assert "成交总金额" in self._sem()

    def test_term_format_sql_pipe_definition(self):
        assert "GMV: SUM(amount) WHERE status IN (2,3,4) | 成交总金额" in self._sem()

    def test_relations_header(self):
        assert "表关联:" in self._sem()

    def test_relation_arrow_notation(self):
        out = self._sem()
        assert "orders.user_id -> users.id" in out
        assert "orders.product_id -> products.id" in out

    def test_empty_context_returns_empty_string(self):
        ctx = SemanticContext(database_name="db")
        assert self.engine.build_semantic_context(ctx) == ""

    def test_only_terms_no_relations_section(self):
        ctx = SemanticContext(
            database_name="db",
            business_terms=[("DAU", "日活用户数", "COUNT(DISTINCT user_id)")],
        )
        out = self.engine.build_semantic_context(ctx)
        assert "业务术语:" in out
        assert "表关联:" not in out

    def test_only_relations_no_terms_section(self):
        ctx = SemanticContext(
            database_name="db",
            relations=[("orders", "user_id", "users", "id")],
        )
        out = self.engine.build_semantic_context(ctx)
        assert "表关联:" in out
        assert "业务术语:" not in out

    def test_term_with_only_sql_no_trailing_pipe(self):
        ctx = SemanticContext(
            database_name="db",
            business_terms=[("Revenue", None, "SUM(price)")],
        )
        out = self.engine.build_semantic_context(ctx)
        assert "Revenue: SUM(price)" in out
        assert "Revenue: SUM(price) |" not in out

    def test_term_with_only_definition_no_sql(self):
        ctx = SemanticContext(
            database_name="db",
            business_terms=[("新用户", "首次下单的用户", None)],
        )
        assert "新用户: 首次下单的用户" in self.engine.build_semantic_context(ctx)


# ═══════════════════════════════════════════════════════════════════════════
# build_prompt_context
# ═══════════════════════════════════════════════════════════════════════════

class TestBuildPromptContext:
    def setup_method(self):
        self.engine = make_engine()
        self.ctx    = make_ecommerce_ctx()

    def test_combines_schema_and_semantic(self):
        out = self.engine.build_prompt_context(self.ctx)
        assert "数据库: ecommerce" in out
        assert "业务术语:" in out
        assert "表关联:" in out

    def test_schema_comes_before_semantic(self):
        out = self.engine.build_prompt_context(self.ctx)
        assert out.index("数据库:") < out.index("业务术语:")

    def test_no_semantic_data_returns_only_schema(self):
        ctx = SemanticContext(
            database_name="db",
            tables=[TableInfo("t", None, [col("id", "INT")])],
        )
        out = self.engine.build_prompt_context(ctx)
        assert "数据库: db" in out
        assert "业务术语:" not in out
        assert "表关联:" not in out


# ═══════════════════════════════════════════════════════════════════════════
# Utility methods
# ═══════════════════════════════════════════════════════════════════════════

class TestUtilityMethods:
    def setup_method(self):
        self.engine = make_engine()
        self.ctx    = make_ecommerce_ctx()

    def test_get_table_names(self):
        names = self.engine.get_table_names(self.ctx)
        assert set(names) == {"orders", "users"}

    def test_get_table_names_empty(self):
        assert self.engine.get_table_names(SemanticContext(database_name="db")) == []

    def test_get_column_names(self):
        cols = self.engine.get_column_names(self.ctx, "orders")
        assert {"id", "status", "amount"}.issubset(set(cols))

    def test_get_column_names_unknown_table(self):
        assert self.engine.get_column_names(self.ctx, "nonexistent") == []

    def test_resolve_term_found(self):
        assert self.engine.resolve_term(self.ctx, "GMV") == "SUM(amount) WHERE status IN (2,3,4)"

    def test_resolve_term_case_insensitive(self):
        assert self.engine.resolve_term(self.ctx, "gmv") is not None

    def test_resolve_term_not_found(self):
        assert self.engine.resolve_term(self.ctx, "未知指标") is None

    def test_resolve_term_none_when_sql_is_none(self):
        ctx = SemanticContext(
            database_name="db",
            business_terms=[("纯描述术语", "只有描述", None)],
        )
        assert self.engine.resolve_term(ctx, "纯描述术语") is None


# ═══════════════════════════════════════════════════════════════════════════
# Dataclass correctness
# ═══════════════════════════════════════════════════════════════════════════

class TestDataclasses:
    def test_semantic_context_defaults(self):
        ctx = SemanticContext(database_name="db")
        assert ctx.tables == []
        assert ctx.business_terms == []
        assert ctx.relations == []

    def test_table_info_defaults(self):
        assert TableInfo(table_name="t", table_comment=None).columns == []

    def test_column_info_defaults(self):
        c = ColumnInfo("x", "INT", "int", True, None, None, None, None)
        assert c.alias_name is None
        assert c.enum_labels == {}
        assert c.foreign_key_ref is None

    def test_enum_labels_not_shared_between_instances(self):
        c1 = ColumnInfo("a", "INT", "int", False, None, None, None, None)
        c2 = ColumnInfo("b", "INT", "int", False, None, None, None, None)
        c1.enum_labels["1"] = "yes"
        assert c2.enum_labels == {}


# ═══════════════════════════════════════════════════════════════════════════
# Async Convenience Methods
# ═══════════════════════════════════════════════════════════════════════════

class TestAsyncMethods:
    def setup_method(self):
        self.engine = make_engine()
        self.ctx = make_ecommerce_ctx()
        # Mock the loader's load method to return our fixture context
        self.engine._loader.load = AsyncMock(return_value=self.ctx)

    @pytest.mark.asyncio
    async def test_load_calls_loader(self):
        ctx = await self.engine.load(123)
        assert ctx is self.ctx
        self.engine._loader.load.assert_called_once_with(123)

    @pytest.mark.asyncio
    async def test_get_prompt_context(self):
        out = await self.engine.get_prompt_context(456)
        assert "数据库: ecommerce" in out
        assert "业务术语:" in out
        assert "表关联:" in out
        self.engine._loader.load.assert_called_once_with(456)

    @pytest.mark.asyncio
    async def test_get_schema_context(self):
        out = await self.engine.get_schema_context(789)
        assert "数据库: ecommerce" in out
        assert "业务术语:" not in out
        assert "表关联:" not in out
        self.engine._loader.load.assert_called_once_with(789)

