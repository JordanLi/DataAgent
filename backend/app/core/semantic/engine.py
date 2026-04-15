"""Formats SemanticContext into LLM prompt strings, and provides utility methods."""

from __future__ import annotations

from app.core.semantic.types import SemanticContext


class SemanticEngine:
    """Converts a SemanticContext into LLM-ready prompt text and provides helper queries."""

    def __init__(self, loader) -> None:
        self._loader = loader

    # ------------------------------------------------------------------ #
    # Async convenience wrappers                                          #
    # ------------------------------------------------------------------ #

    async def load(self, datasource_id: int) -> SemanticContext:
        return await self._loader.load(datasource_id)

    async def get_prompt_context(self, datasource_id: int) -> str:
        ctx = await self._loader.load(datasource_id)
        return self.build_prompt_context(ctx)

    async def get_schema_context(self, datasource_id: int) -> str:
        ctx = await self._loader.load(datasource_id)
        return self.build_schema_context(ctx)

    # ------------------------------------------------------------------ #
    # Rendering methods                                                   #
    # ------------------------------------------------------------------ #

    def build_schema_context(self, ctx: SemanticContext) -> str:
        """Render schema (tables + columns) into a prompt string."""
        if not ctx.tables:
            return f"数据库: {ctx.database_name}"

        lines = [f"数据库: {ctx.database_name}"]
        for t in ctx.tables:
            comment = f" ({t.table_comment})" if t.table_comment else ""
            lines.append(f"表: {t.table_name}{comment}")
            if not t.columns:
                lines.append("  (无字段信息)")
            for c in t.columns:
                # Display name: alias if present, else column_name
                display = f"{c.alias_name} [{c.column_name}]" if c.alias_name else c.column_name
                type_str = c.column_type.upper() if c.column_type else ""
                parts = [f"  {display} {type_str}"]

                flags = []
                if c.column_key == "PRI":
                    flags.append("主键")
                if c.extra and "auto_increment" in c.extra:
                    flags.append("自增")
                if c.column_key == "UNI":
                    flags.append("唯一索引")
                if c.column_key == "MUL":
                    flags.append("索引")
                if not c.is_nullable:
                    flags.append("非空")
                if c.foreign_key_ref:
                    flags.append(f"外键->{c.foreign_key_ref}")
                if flags:
                    parts.append(f"[{', '.join(flags)}]")

                # Description: alias_description preferred over column_comment
                desc = c.alias_description or c.column_comment
                if desc:
                    parts.append(desc)

                if c.enum_labels:
                    enum_str = ", ".join(f"{k}={v}" for k, v in c.enum_labels.items())
                    parts.append(f"枚举: {enum_str}")

                lines.append(" ".join(parts))
        return "\n".join(lines)

    def build_semantic_context(self, ctx: SemanticContext) -> str:
        """Render business terms and relations into a prompt string."""
        parts: list[str] = []

        if ctx.business_terms:
            parts.append("业务术语:")
            for name, defn, sql in ctx.business_terms:
                if sql and defn:
                    parts.append(f"  {name}: {sql} | {defn}")
                elif sql:
                    parts.append(f"  {name}: {sql}")
                elif defn:
                    parts.append(f"  {name}: {defn}")

        if ctx.relations:
            parts.append("表关联:")
            for s_tbl, s_col, t_tbl, t_col in ctx.relations:
                parts.append(f"  {s_tbl}.{s_col} -> {t_tbl}.{t_col}")

        return "\n".join(parts)

    def build_prompt_context(self, ctx: SemanticContext) -> str:
        """Combine schema and semantic context into a full prompt string."""
        schema = self.build_schema_context(ctx)
        semantic = self.build_semantic_context(ctx)
        if semantic:
            return f"{schema}\n{semantic}"
        return schema

    # ------------------------------------------------------------------ #
    # Utility / query helpers                                             #
    # ------------------------------------------------------------------ #

    def get_table_names(self, ctx: SemanticContext) -> list[str]:
        return [t.table_name for t in ctx.tables]

    def get_column_names(self, ctx: SemanticContext, table_name: str) -> list[str]:
        for t in ctx.tables:
            if t.table_name == table_name:
                return [c.column_name for c in t.columns]
        return []

    def resolve_term(self, ctx: SemanticContext, term_name: str) -> str | None:
        for name, _defn, sql in ctx.business_terms:
            if name.lower() == term_name.lower():
                return sql  # may be None if term has no sql
        return None

    # ------------------------------------------------------------------ #
    # Backward-compat static method for API layer (uses dict format)     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def build_schema_prompt(context_data: dict) -> str:
        """Legacy dict-based renderer used by the /api/semantic/preview endpoint."""
        lines = [f"### 数据库: {context_data['database_name']}", ""]
        lines.append("### 表结构 (Schema):")
        for tname, tinfo in context_data.get("schema", {}).items():
            comment_str = f"({tinfo['comment']})" if tinfo.get("comment") else ""
            lines.append(f"表: {tname} {comment_str}")
            for col in tinfo.get("columns", []):
                col_parts = [f"  - {col['name']}: {col.get('type', '')}"]
                if col.get("primary_key"):
                    col_parts.append("主键")
                desc_parts = []
                if col.get("alias"):
                    desc_parts.append(f"业务别名='{col['alias']}'")
                if col.get("comment"):
                    desc_parts.append(f"注释='{col['comment']}'")
                if col.get("description"):
                    desc_parts.append(f"说明='{col['description']}'")
                if desc_parts:
                    col_parts.append(", ".join(desc_parts))
                if col.get("enums"):
                    col_parts.append(f"[枚举值: {', '.join(col['enums'])}]")
                lines.append(", ".join(col_parts))
            lines.append("")
        terms = context_data.get("business_terms", [])
        if terms:
            lines.append("### 业务术语与指标定义 (Business Terms):")
            lines.append("当你遇到以下业务词汇时，必须严格按照指定的SQL计算口径：")
            for term in terms:
                def_str = f" ({term['definition']})" if term.get("definition") else ""
                lines.append(f"  - {term['term']}{def_str}: {term.get('sql', '')}")
            lines.append("")
        rels = context_data.get("relations", [])
        if rels:
            lines.append("### 表关联关系 (JOIN Paths):")
            for rel in rels:
                lines.append(f"  - {rel}")
            lines.append("")
        return "\n".join(lines)
