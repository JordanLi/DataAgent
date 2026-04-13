"""ORM models for DataSource and TableMetadata."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.database import Base

if TYPE_CHECKING:
    from app.models.semantic import BusinessTerm, EnumMapping, FieldAlias, TableRelation


class DbType(str, enum.Enum):
    mysql = "mysql"


class DataSource(Base):
    __tablename__ = "datasources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    db_type: Mapped[DbType] = mapped_column(
        Enum(DbType, name="db_type_enum"), nullable=False, default=DbType.mysql
    )
    host: Mapped[str] = mapped_column(String(256), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False, default=3306)
    database: Mapped[str] = mapped_column(String(128), nullable=False)
    username: Mapped[str] = mapped_column(String(128), nullable=False)
    encrypted_password: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    tables: Mapped[list[TableMetadata]] = relationship(
        "TableMetadata", back_populates="datasource", cascade="all, delete-orphan"
    )
    terms: Mapped[list[BusinessTerm]] = relationship(
        "BusinessTerm", back_populates="datasource", cascade="all, delete-orphan"
    )
    aliases: Mapped[list[FieldAlias]] = relationship(
        "FieldAlias", back_populates="datasource", cascade="all, delete-orphan"
    )
    enums: Mapped[list[EnumMapping]] = relationship(
        "EnumMapping", back_populates="datasource", cascade="all, delete-orphan"
    )
    relations: Mapped[list[TableRelation]] = relationship(
        "TableRelation", back_populates="datasource", cascade="all, delete-orphan"
    )


class TableMetadata(Base):
    __tablename__ = "table_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    datasource_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("datasources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    table_name: Mapped[str] = mapped_column(String(256), nullable=False)
    table_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    columns_json: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="JSON array of column metadata"
    )
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    datasource: Mapped[DataSource] = relationship("DataSource", back_populates="tables")
