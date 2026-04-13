"""ORM models for the semantic layer: BusinessTerm, FieldAlias, EnumMapping, TableRelation."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.database import Base

if TYPE_CHECKING:
    from app.models.datasource import DataSource


class RelationType(str, enum.Enum):
    one_to_one = "one_to_one"
    one_to_many = "one_to_many"
    many_to_one = "many_to_one"
    many_to_many = "many_to_many"


class BusinessTerm(Base):
    """User-defined business metric / KPI with an explicit SQL expression."""

    __tablename__ = "business_terms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    datasource_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("datasources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    term_name: Mapped[str] = mapped_column(String(128), nullable=False)
    definition: Mapped[str | None] = mapped_column(Text, nullable=True)
    sql_expression: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="e.g. SUM(order_amount)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    datasource: Mapped[DataSource] = relationship("DataSource", back_populates="terms")

    __table_args__ = (
        UniqueConstraint("datasource_id", "term_name", name="uq_term_per_datasource"),
    )


class FieldAlias(Base):
    """Human-readable alias for a column, used in prompts and UI."""

    __tablename__ = "field_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    datasource_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("datasources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    table_name: Mapped[str] = mapped_column(String(256), nullable=False)
    column_name: Mapped[str] = mapped_column(String(256), nullable=False)
    alias_name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    datasource: Mapped[DataSource] = relationship("DataSource", back_populates="aliases")

    __table_args__ = (
        UniqueConstraint(
            "datasource_id", "table_name", "column_name",
            name="uq_alias_per_column",
        ),
    )


class EnumMapping(Base):
    """Maps raw enum/integer values to display labels for LLM context."""

    __tablename__ = "enum_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    datasource_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("datasources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    table_name: Mapped[str] = mapped_column(String(256), nullable=False)
    column_name: Mapped[str] = mapped_column(String(256), nullable=False)
    enum_value: Mapped[str] = mapped_column(String(256), nullable=False)
    display_label: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    datasource: Mapped[DataSource] = relationship("DataSource", back_populates="enums")

    __table_args__ = (
        UniqueConstraint(
            "datasource_id", "table_name", "column_name", "enum_value",
            name="uq_enum_value_per_column",
        ),
    )


class TableRelation(Base):
    """FK-like join relationship between two tables for prompt context."""

    __tablename__ = "table_relations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    datasource_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("datasources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_table: Mapped[str] = mapped_column(String(256), nullable=False)
    source_column: Mapped[str] = mapped_column(String(256), nullable=False)
    target_table: Mapped[str] = mapped_column(String(256), nullable=False)
    target_column: Mapped[str] = mapped_column(String(256), nullable=False)
    relation_type: Mapped[RelationType] = mapped_column(
        Enum(RelationType, name="relation_type_enum"),
        nullable=False,
        default=RelationType.many_to_one,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    datasource: Mapped[DataSource] = relationship("DataSource", back_populates="relations")
