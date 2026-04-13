"""Loads raw metadata and semantic rules from the database."""

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.datasource import DataSource, TableMetadata
from app.models.semantic import BusinessTerm, EnumMapping, FieldAlias, TableRelation


class SemanticLoader:
    """Service to load all schema and semantic layer info for a datasource."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def load_full_context(self, datasource_id: int) -> dict:
        """
        Loads all tables, columns, aliases, enums, terms, and relations
        and merges them into a structured dictionary.
        """
        ds = await self.db.get(DataSource, datasource_id)
        if not ds:
            raise ValueError(f"Datasource {datasource_id} not found")

        # 1. Load raw table metadata
        meta_stmt = select(TableMetadata).where(TableMetadata.datasource_id == datasource_id)
        meta_res = await self.db.execute(meta_stmt)
        tables = meta_res.scalars().all()

        # 2. Load semantic configs
        alias_stmt = select(FieldAlias).where(FieldAlias.datasource_id == datasource_id)
        aliases = (await self.db.execute(alias_stmt)).scalars().all()

        enum_stmt = select(EnumMapping).where(EnumMapping.datasource_id == datasource_id)
        enums = (await self.db.execute(enum_stmt)).scalars().all()

        term_stmt = select(BusinessTerm).where(BusinessTerm.datasource_id == datasource_id)
        terms = (await self.db.execute(term_stmt)).scalars().all()

        rel_stmt = select(TableRelation).where(TableRelation.datasource_id == datasource_id)
        relations = (await self.db.execute(rel_stmt)).scalars().all()

        # Organize indexes for quick lookup
        alias_map = {}  # (table, column) -> alias info
        for a in aliases:
            alias_map[(a.table_name, a.column_name)] = {
                "alias_name": a.alias_name,
                "description": a.description
            }

        enum_map = {}   # (table, column) -> list of enum mappings
        for e in enums:
            key = (e.table_name, e.column_name)
            if key not in enum_map:
                enum_map[key] = []
            enum_map[key].append(f"{e.enum_value}={e.display_label}")

        # Build final structured output
        schema_dict = {}
        for t in tables:
            cols = []
            if t.columns_json:
                raw_cols = json.loads(t.columns_json)
                for rc in raw_cols:
                    cname = rc.get("name")
                    # Enhance with semantic info
                    sem_alias = alias_map.get((t.table_name, cname))
                    sem_enum = enum_map.get((t.table_name, cname))
                    
                    cols.append({
                        "name": cname,
                        "type": rc.get("type"),
                        "primary_key": rc.get("primary_key", False),
                        "comment": rc.get("comment", ""),
                        "alias": sem_alias["alias_name"] if sem_alias else None,
                        "description": sem_alias["description"] if sem_alias else None,
                        "enums": sem_enum
                    })

            schema_dict[t.table_name] = {
                "comment": t.table_comment,
                "columns": cols
            }

        return {
            "database_name": ds.database,
            "schema": schema_dict,
            "business_terms": [
                {"term": t.term_name, "definition": t.definition, "sql": t.sql_expression}
                for t in terms
            ],
            "relations": [
                f"{r.source_table}.{r.source_column} -> {r.target_table}.{r.target_column} ({r.relation_type.value})"
                for r in relations
            ]
        }
