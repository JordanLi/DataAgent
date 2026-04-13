"""Unit tests for SemanticLoader data-assembly logic.

Strategy: patch the private _load_* methods directly so SQLAlchemy's
select() builder is never called.  This lets us test the enrichment
and assembly logic (alias injection, enum merging, FK resolution, etc.)
without a real DB and without SQLAlchemy trying to compile queries
against mock objects (which hangs on Python 3.9).
"""

from __future__ import annotations

import asyncio
import json
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

# ── Patch ORM-dependent modules BEFORE any app imports ───────────────────────
for _m in (
    "app.models",
    "app.models.database",
    "app.models.datasource",
    "app.models.semantic",
    "sqlalchemy",
    "sqlalchemy.ext",
    "sqlalchemy.ext.asyncio",
):
    sys.modules.setdefault(_m, MagicMock())

# ── Safe imports ──────────────────────────────────────────────────────────────
from app.core.semantic.types import ColumnInfo, SemanticContext, TableInfo  # noqa: E402
from app.core.semantic.loader import SemanticLoader                          # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# Stub factories  (SimpleNamespace mimics ORM row attributes)
# ─────────────────────────────────────────────────────────────────────────────

def _ds(db_name: str = "ecommerce") -> SimpleNamespace:
    return SimpleNamespace(database=db_name)


def _tbl(name: str, comment, cols: list[dict]) -> SimpleNamespace:
    return SimpleNamespace(
        table_name=name, table_comment=comment,
        columns_json=json.dumps(cols),
    )


def _alias(tbl: str, col: str, alias: str, desc=None) -> SimpleNamespace:
    return SimpleNamespace(table_name=tbl, column_name=col, alias_name=alias, description=desc)


def _enum(tbl: str, col: str, val: str, label: str) -> SimpleNamespace:
    return SimpleNamespace(table_name=tbl, column_name=col, enum_value=val, display_label=label)


def _rel(s_tbl: str, s_col: str, t_tbl: str, t_col: str) -> SimpleNamespace:
    return SimpleNamespace(source_table=s_tbl, source_column=s_col,
                           target_table=t_tbl, target_column=t_col)


def _term(name: str, defn, sql) -> SimpleNamespace:
    return SimpleNamespace(term_name=name, definition=defn, sql_expression=sql)


# ─────────────────────────────────────────────────────────────────────────────
# Helper: build a SemanticLoader with all _load_* methods patched
# ─────────────────────────────────────────────────────────────────────────────

def _make_loader(
    *,
    datasource=None,
    tables=None,
    aliases=None,
    enums=None,
    relations=None,
    terms=None,
) -> SemanticLoader:
    loader = SemanticLoader.__new__(SemanticLoader)
    loader._db = MagicMock()

    async def _ret(val): return val

    loader._load_datasource    = AsyncMock(return_value=datasource or _ds())
    loader._load_table_metadata = AsyncMock(return_value=tables or [])
    loader._load_aliases       = AsyncMock(return_value=aliases or [])
    loader._load_enums         = AsyncMock(return_value=enums or [])
    loader._load_fk_refs       = AsyncMock(return_value=relations or [])
    loader._load_terms         = AsyncMock(return_value=terms or [])
    loader._load_relations     = AsyncMock(return_value=relations or [])
    return loader


def run(coro):
    return asyncio.run(coro)


# ─────────────────────────────────────────────────────────────────────────────
# Tests: return types and basic structure
# ─────────────────────────────────────────────────────────────────────────────

class TestLoaderReturnType:

    def test_returns_semantic_context(self):
        ctx = run(_make_loader(datasource=_ds("shop")).load(1))
        assert isinstance(ctx, SemanticContext)

    def test_database_name_from_datasource(self):
        ctx = run(_make_loader(datasource=_ds("my_db")).load(1))
        assert ctx.database_name == "my_db"

    def test_table_count_matches_metadata(self):
        tables = [_tbl("orders", "订单表", []), _tbl("users", "用户表", [])]
        ctx = run(_make_loader(tables=tables).load(1))
        assert len(ctx.tables) == 2

    def test_table_names_preserved(self):
        tables = [_tbl("orders", None, []), _tbl("products", None, [])]
        ctx = run(_make_loader(tables=tables).load(1))
        names = [t.table_name for t in ctx.tables]
        assert "orders" in names and "products" in names

    def test_table_comment_preserved(self):
        tables = [_tbl("orders", "订单表", [])]
        ctx = run(_make_loader(tables=tables).load(1))
        assert ctx.tables[0].table_comment == "订单表"


# ─────────────────────────────────────────────────────────────────────────────
# Tests: column parsing from JSON
# ─────────────────────────────────────────────────────────────────────────────

class TestColumnParsing:

    RAW = [
        {"column_name": "id",   "column_type": "INT",          "data_type": "int",
         "is_nullable": "NO",   "column_default": None,         "column_comment": "主键",
         "column_key": "PRI",   "extra": "auto_increment"},
        {"column_name": "name", "column_type": "VARCHAR(255)",  "data_type": "varchar",
         "is_nullable": "YES",  "column_default": None,         "column_comment": "名称",
         "column_key": None,    "extra": None},
    ]

    def _ctx(self):
        return run(_make_loader(tables=[_tbl("products", None, self.RAW)]).load(1))

    def test_column_count(self):
        assert len(self._ctx().tables[0].columns) == 2

    def test_column_name(self):
        assert self._ctx().tables[0].columns[0].column_name == "id"

    def test_column_key_pri(self):
        assert self._ctx().tables[0].columns[0].column_key == "PRI"

    def test_is_nullable_no(self):
        assert self._ctx().tables[0].columns[0].is_nullable is False

    def test_is_nullable_yes(self):
        assert self._ctx().tables[0].columns[1].is_nullable is True

    def test_column_type_preserved(self):
        assert self._ctx().tables[0].columns[1].column_type == "VARCHAR(255)"

    def test_column_comment_preserved(self):
        assert self._ctx().tables[0].columns[0].column_comment == "主键"

    def test_null_columns_json_yields_empty_list(self):
        tbl = SimpleNamespace(table_name="t", table_comment=None, columns_json=None)
        ctx = run(_make_loader(tables=[tbl]).load(1))
        assert ctx.tables[0].columns == []

    def test_empty_columns_json_array_yields_empty_list(self):
        tbl = SimpleNamespace(table_name="t", table_comment=None, columns_json="[]")
        ctx = run(_make_loader(tables=[tbl]).load(1))
        assert ctx.tables[0].columns == []


# ─────────────────────────────────────────────────────────────────────────────
# Tests: alias enrichment
# ─────────────────────────────────────────────────────────────────────────────

class TestAliasEnrichment:

    RAW = [{"column_name": "amt", "column_type": "DECIMAL", "data_type": "decimal",
            "is_nullable": "NO", "column_default": None, "column_comment": "金额",
            "column_key": None, "extra": None}]

    def test_alias_name_injected(self):
        ctx = run(_make_loader(
            tables=[_tbl("orders", None, self.RAW)],
            aliases=[_alias("orders", "amt", "实付金额")],
        ).load(1))
        assert ctx.tables[0].columns[0].alias_name == "实付金额"

    def test_alias_description_injected(self):
        ctx = run(_make_loader(
            tables=[_tbl("orders", None, self.RAW)],
            aliases=[_alias("orders", "amt", "实付金额", "用户实际支付的金额")],
        ).load(1))
        assert ctx.tables[0].columns[0].alias_description == "用户实际支付的金额"

    def test_no_alias_leaves_fields_none(self):
        ctx = run(_make_loader(tables=[_tbl("orders", None, self.RAW)]).load(1))
        c = ctx.tables[0].columns[0]
        assert c.alias_name is None
        assert c.alias_description is None

    def test_alias_only_applied_to_matching_table_column(self):
        raw2 = [{"column_name": "price", "column_type": "DECIMAL", "data_type": "decimal",
                 "is_nullable": "NO", "column_default": None, "column_comment": None,
                 "column_key": None, "extra": None}]
        ctx = run(_make_loader(
            tables=[_tbl("orders", None, self.RAW), _tbl("products", None, raw2)],
            aliases=[_alias("orders", "amt", "实付金额")],
        ).load(1))
        orders_col  = ctx.tables[0].columns[0]
        product_col = ctx.tables[1].columns[0]
        assert orders_col.alias_name == "实付金额"
        assert product_col.alias_name is None


# ─────────────────────────────────────────────────────────────────────────────
# Tests: enum label enrichment
# ─────────────────────────────────────────────────────────────────────────────

class TestEnumEnrichment:

    RAW = [{"column_name": "status", "column_type": "INT", "data_type": "int",
            "is_nullable": "NO", "column_default": None, "column_comment": "状态",
            "column_key": None, "extra": None}]

    def test_enum_labels_injected(self):
        ctx = run(_make_loader(
            tables=[_tbl("orders", None, self.RAW)],
            enums=[_enum("orders", "status", "1", "待支付"),
                   _enum("orders", "status", "2", "已支付")],
        ).load(1))
        labels = ctx.tables[0].columns[0].enum_labels
        assert labels == {"1": "待支付", "2": "已支付"}

    def test_three_enum_values_all_present(self):
        ctx = run(_make_loader(
            tables=[_tbl("t", None, self.RAW)],
            enums=[_enum("t", "status", "0", "草稿"),
                   _enum("t", "status", "1", "发布"),
                   _enum("t", "status", "2", "归档")],
        ).load(1))
        labels = ctx.tables[0].columns[0].enum_labels
        assert len(labels) == 3
        assert labels["0"] == "草稿" and labels["2"] == "归档"

    def test_no_enums_leaves_empty_dict(self):
        ctx = run(_make_loader(tables=[_tbl("t", None, self.RAW)]).load(1))
        assert ctx.tables[0].columns[0].enum_labels == {}

    def test_enums_for_different_columns_not_mixed(self):
        raw2 = [{"column_name": "type", "column_type": "INT", "data_type": "int",
                 "is_nullable": "NO", "column_default": None, "column_comment": None,
                 "column_key": None, "extra": None}]
        ctx = run(_make_loader(
            tables=[_tbl("t", None, self.RAW + raw2)],
            enums=[_enum("t", "status", "1", "激活"), _enum("t", "type", "9", "VIP")],
        ).load(1))
        assert ctx.tables[0].columns[0].enum_labels == {"1": "激活"}
        assert ctx.tables[0].columns[1].enum_labels == {"9": "VIP"}


# ─────────────────────────────────────────────────────────────────────────────
# Tests: FK reference enrichment
# ─────────────────────────────────────────────────────────────────────────────

class TestFKEnrichment:

    RAW = [{"column_name": "user_id", "column_type": "INT", "data_type": "int",
            "is_nullable": "NO", "column_default": None, "column_comment": None,
            "column_key": "MUL", "extra": None}]

    def test_fk_ref_injected(self):
        ctx = run(_make_loader(
            tables=[_tbl("orders", None, self.RAW)],
            relations=[_rel("orders", "user_id", "users", "id")],
        ).load(1))
        assert ctx.tables[0].columns[0].foreign_key_ref == "users.id"

    def test_no_relation_leaves_fk_ref_none(self):
        ctx = run(_make_loader(tables=[_tbl("orders", None, self.RAW)]).load(1))
        assert ctx.tables[0].columns[0].foreign_key_ref is None

    def test_fk_ref_format_table_dot_column(self):
        ctx = run(_make_loader(
            tables=[_tbl("orders", None, self.RAW)],
            relations=[_rel("orders", "user_id", "accounts", "account_id")],
        ).load(1))
        assert ctx.tables[0].columns[0].foreign_key_ref == "accounts.account_id"


# ─────────────────────────────────────────────────────────────────────────────
# Tests: business terms
# ─────────────────────────────────────────────────────────────────────────────

class TestBusinessTerms:

    def test_terms_present_in_context(self):
        terms = [_term("GMV", "成交总金额", "SUM(amount) WHERE status IN (2,3,4)"),
                 _term("DAU", "日活用户数", "COUNT(DISTINCT user_id)")]
        ctx = run(_make_loader(terms=terms).load(1))
        assert len(ctx.business_terms) == 2

    def test_term_name_preserved(self):
        ctx = run(_make_loader(terms=[_term("GMV", None, "SUM(x)")]).load(1))
        assert ctx.business_terms[0][0] == "GMV"

    def test_term_definition_preserved(self):
        ctx = run(_make_loader(terms=[_term("GMV", "成交总金额", None)]).load(1))
        assert ctx.business_terms[0][1] == "成交总金额"

    def test_term_sql_expression_preserved(self):
        ctx = run(_make_loader(terms=[_term("GMV", None, "SUM(amount)")]).load(1))
        assert ctx.business_terms[0][2] == "SUM(amount)"

    def test_no_terms_yields_empty_list(self):
        ctx = run(_make_loader().load(1))
        assert ctx.business_terms == []


# ─────────────────────────────────────────────────────────────────────────────
# Tests: table relations
# ─────────────────────────────────────────────────────────────────────────────

class TestRelations:

    def test_relations_present_in_context(self):
        rels = [_rel("orders", "user_id", "users", "id"),
                _rel("orders", "product_id", "products", "id")]
        ctx = run(_make_loader(relations=rels).load(1))
        assert len(ctx.relations) == 2

    def test_relation_tuple_format(self):
        ctx = run(_make_loader(
            relations=[_rel("orders", "user_id", "users", "id")]
        ).load(1))
        assert ctx.relations[0] == ("orders", "user_id", "users", "id")

    def test_no_relations_yields_empty_list(self):
        ctx = run(_make_loader().load(1))
        assert ctx.relations == []

    def test_multiple_relations_all_preserved(self):
        rels = [
            _rel("orders", "user_id",     "users",    "id"),
            _rel("orders", "product_id",  "products", "id"),
            _rel("products", "category_id", "categories", "id"),
        ]
        ctx = run(_make_loader(relations=rels).load(1))
        assert len(ctx.relations) == 3
