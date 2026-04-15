"""Loads raw metadata and semantic rules from the database into typed objects."""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.datasource import DataSource, TableMetadata
from app.models.semantic import BusinessTerm, EnumMapping, FieldAlias, TableRelation
from app.core.semantic.types import ColumnInfo, SemanticContext, TableInfo


class SemanticLoader:
    """Loads all schema and semantic layer info for a datasource into a SemanticContext."""

    def __init__(self, db: AsyncSession):
        self._db = db

    # ------------------------------------------------------------------ #
    # Private helpers — each loads one slice of data from the DB          #
    # ------------------------------------------------------------------ #

    async def _load_datasource(self, datasource_id: int) -> DataSource:
        ds = await self._db.get(DataSource, datasource_id)
        if ds is None:
            raise ValueError(f"Datasource {datasource_id} not found")
        return ds

    async def _load_table_metadata(self, datasource_id: int) -> list:
        result = await self._db.execute(
            select(TableMetadata).where(TableMetadata.datasource_id == datasource_id)
        )
        return result.scalars().all()

    async def _load_aliases(self, datasource_id: int) -> list:
        result = await self._db.execute(
            select(FieldAlias).where(FieldAlias.datasource_id == datasource_id)
        )
        return result.scalars().all()

    async def _load_enums(self, datasource_id: int) -> list:
        result = await self._db.execute(
            select(EnumMapping).where(EnumMapping.datasource_id == datasource_id)
        )
        return result.scalars().all()

    async def _load_fk_refs(self, datasource_id: int) -> list:
        """Load table relations used to annotate FK columns."""
        result = await self._db.execute(
            select(TableRelation).where(TableRelation.datasource_id == datasource_id)
        )
        return result.scalars().all()

    async def _load_terms(self, datasource_id: int) -> list:
        result = await self._db.execute(
            select(BusinessTerm).where(BusinessTerm.datasource_id == datasource_id)
        )
        return result.scalars().all()

    async def _load_relations(self, datasource_id: int) -> list:
        """Load table relations used to build SemanticContext.relations tuples."""
        result = await self._db.execute(
            select(TableRelation).where(TableRelation.datasource_id == datasource_id)
        )
        return result.scalars().all()

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    async def load(self, datasource_id: int) -> SemanticContext:
        """Load all data and return a typed SemanticContext."""
        ds = await self._load_datasource(datasource_id)
        raw_tables = await self._load_table_metadata(datasource_id)
        aliases = await self._load_aliases(datasource_id)
        enums = await self._load_enums(datasource_id)
        fk_refs = await self._load_fk_refs(datasource_id)
        terms = await self._load_terms(datasource_id)
        relations = await self._load_relations(datasource_id)

        # Build lookup indexes
        alias_map: dict[tuple, object] = {
            (a.table_name, a.column_name): a for a in aliases
        }
        enum_map: dict[tuple, dict[str, str]] = {}
        for e in enums:
            key = (e.table_name, e.column_name)
            if key not in enum_map:
                enum_map[key] = {}
            enum_map[key][str(e.enum_value)] = e.display_label

        fk_map: dict[tuple, str] = {
            (r.source_table, r.source_column): f"{r.target_table}.{r.target_column}"
            for r in fk_refs
        }

        # Build TableInfo list
        table_infos: list[TableInfo] = []
        for t in raw_tables:
            columns: list[ColumnInfo] = []
            if t.columns_json:
                raw_cols = json.loads(t.columns_json)
                for rc in raw_cols:
                    cname = rc.get("column_name") or rc.get("name")
                    alias_row = alias_map.get((t.table_name, cname))
                    col = ColumnInfo(
                        column_name=cname,
                        column_type=rc.get("column_type") or rc.get("type", ""),
                        data_type=rc.get("data_type", ""),
                        is_nullable=(rc.get("is_nullable", "YES") != "NO"),
                        column_default=rc.get("column_default"),
                        column_comment=rc.get("column_comment") or rc.get("comment"),
                        column_key=rc.get("column_key"),
                        extra=rc.get("extra"),
                        alias_name=alias_row.alias_name if alias_row else None,
                        alias_description=alias_row.description if alias_row else None,
                        enum_labels=dict(enum_map.get((t.table_name, cname), {})),
                        foreign_key_ref=fk_map.get((t.table_name, cname)),
                    )
                    columns.append(col)
            table_infos.append(TableInfo(
                table_name=t.table_name,
                table_comment=t.table_comment,
                columns=columns,
            ))

        # Build business terms as tuples
        business_terms = [
            (term.term_name, term.definition, term.sql_expression)
            for term in terms
        ]

        # Build relations as tuples
        relation_tuples = [
            (r.source_table, r.source_column, r.target_table, r.target_column)
            for r in relations
        ]

        return SemanticContext(
            database_name=ds.database,
            tables=table_infos,
            business_terms=business_terms,
            relations=relation_tuples,
        )

    async def load_full_context(self, datasource_id: int) -> dict:
        """Backward-compatible dict output for the API layer."""
        ctx = await self.load(datasource_id)

        schema_dict: dict = {}
        for t in ctx.tables:
            cols = []
            for c in t.columns:
                cols.append({
                    "name": c.column_name,
                    "type": c.column_type,
                    "primary_key": c.column_key == "PRI",
                    "comment": c.column_comment,
                    "alias": c.alias_name,
                    "description": c.alias_description,
                    "enums": [f"{k}={v}" for k, v in c.enum_labels.items()] or None,
                })
            schema_dict[t.table_name] = {
                "comment": t.table_comment,
                "columns": cols,
            }

        return {
            "database_name": ctx.database_name,
            "schema": schema_dict,
            "business_terms": [
                {"term": name, "definition": defn, "sql": sql}
                for name, defn, sql in ctx.business_terms
            ],
            "relations": [
                f"{s_tbl}.{s_col} -> {t_tbl}.{t_col}"
                for s_tbl, s_col, t_tbl, t_col in ctx.relations
            ],
        }
