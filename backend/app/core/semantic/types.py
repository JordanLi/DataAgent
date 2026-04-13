"""Pure-Python data containers for the semantic layer.

These dataclasses carry no SQLAlchemy or FastAPI dependency so they can be
safely imported in tests and other lightweight contexts without triggering
the full ORM initialisation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ColumnInfo:
    """Metadata for a single database column, enriched with semantic data."""

    column_name: str
    column_type: str           # full type string, e.g. "int(11)", "varchar(255)"
    data_type: str             # base type: "int", "varchar", …
    is_nullable: bool
    column_default: str | None
    column_comment: str | None
    column_key: str | None     # "PRI", "MUL", "UNI" or "" / None
    extra: str | None          # "auto_increment", etc.
    # semantic enrichments (populated by SemanticLoader)
    alias_name: str | None = None
    alias_description: str | None = None
    enum_labels: dict[str, str] = field(default_factory=dict)  # value -> label
    foreign_key_ref: str | None = None   # "ref_table.ref_column" or None


@dataclass
class TableInfo:
    """Metadata for a single database table."""

    table_name: str
    table_comment: str | None
    columns: list[ColumnInfo] = field(default_factory=list)


@dataclass
class SemanticContext:
    """All semantic data for one datasource, ready to be rendered into prompts."""

    database_name: str
    tables: list[TableInfo] = field(default_factory=list)
    # (term_name, definition, sql_expression)
    business_terms: list[tuple[str, str | None, str | None]] = field(
        default_factory=list
    )
    # (src_table, src_col, tgt_table, tgt_col)
    relations: list[tuple[str, str, str, str]] = field(default_factory=list)
