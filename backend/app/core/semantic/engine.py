"""Formats loaded semantic rules into an LLM prompt string."""


class SemanticEngine:
    """Converts structured semantic dictionary into LLM prompt text."""

    @staticmethod
    def build_schema_prompt(context_data: dict) -> str:
        """
        Takes the dictionary output of SemanticLoader.load_full_context
        and outputs a Markdown-formatted string for the LLM System Prompt.
        """
        lines = []
        lines.append(f"### 数据库: {context_data['database_name']}")
        lines.append("")

        # 1. Format Tables and Columns
        lines.append("### 表结构 (Schema):")
        for tname, tinfo in context_data["schema"].items():
            comment_str = f"({tinfo['comment']})" if tinfo.get("comment") else ""
            lines.append(f"表: {tname} {comment_str}")
            
            for col in tinfo["columns"]:
                # Construct column signature
                col_parts = [f"  - {col['name']}: {col['type']}"]
                if col.get("primary_key"):
                    col_parts.append("主键")
                
                # Add alias / comment
                desc_parts = []
                if col.get("alias"):
                    desc_parts.append(f"业务别名='{col['alias']}'")
                if col.get("comment"):
                    desc_parts.append(f"注释='{col['comment']}'")
                if col.get("description"):
                    desc_parts.append(f"说明='{col['description']}'")
                
                if desc_parts:
                    col_parts.append(", ".join(desc_parts))

                # Add enums
                if col.get("enums"):
                    enums_str = ", ".join(col["enums"])
                    col_parts.append(f"[枚举值: {enums_str}]")

                lines.append(", ".join(col_parts))
            lines.append("")

        # 2. Format Business Terms
        terms = context_data.get("business_terms", [])
        if terms:
            lines.append("### 业务术语与指标定义 (Business Terms):")
            lines.append("当你遇到以下业务词汇时，必须严格按照指定的SQL计算口径：")
            for term in terms:
                def_str = f" ({term['definition']})" if term['definition'] else ""
                lines.append(f"  - {term['term']}{def_str}: {term['sql']}")
            lines.append("")

        # 3. Format Table Relations
        rels = context_data.get("relations", [])
        if rels:
            lines.append("### 表关联关系 (JOIN Paths):")
            for rel in rels:
                lines.append(f"  - {rel}")
            lines.append("")

        return "\n".join(lines)
