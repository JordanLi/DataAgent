"""SQLGenerator: 将自然语言问题转换为 SQL。

职责:
- 组装 System Prompt（角色设定 + 规则 + Schema + 语义层 + Few-shot）
- 调用 LLM 生成 SQL
- 从响应中提取 ```sql ... ``` 代码块
"""

from __future__ import annotations

import re

from app.core.llm.base import BaseLLM

# ---------------------------------------------------------------------------
# System Prompt 模板
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT_TEMPLATE = """\
你是一个专业的数据分析助手和 MySQL 专家。根据用户的自然语言问题，生成精确的 MySQL SELECT 查询语句。

## 规则
1. 只生成 SELECT 语句，严禁 INSERT / UPDATE / DELETE / DROP / CREATE / ALTER 等任何 DDL/DML 操作
2. 必须添加 LIMIT（默认 {default_limit}，除非用户明确要求全量）
3. 只使用下方 Schema 中存在的表和字段，不假设不存在的对象
4. 严格遵循【业务术语】中的计算口径，不得自行发明指标定义
5. 表关联时优先使用【表关联】中描述的 JOIN 条件
6. 字段名使用反引号包裹（`` `column` ``）以避免关键字冲突
7. 只输出 SQL 代码块，格式：

```sql
SELECT ...
```

不要输出任何解释性文字。

## 示例
问题: 上个月订单量最多的三个商品
解答:
```sql
SELECT p.name, SUM(oi.quantity) AS total_quantity 
FROM order_items oi
JOIN products p ON oi.product_id = p.id
WHERE oi.created_at >= DATE_SUB(CURRENT_DATE, INTERVAL 1 MONTH)
GROUP BY p.id, p.name
ORDER BY total_quantity DESC
LIMIT 3;
```

## Schema 信息
{schema_context}
"""

_SUMMARY_SYSTEM_PROMPT = """\
你是一个数据分析师。根据用户的问题和查询结果，用简洁的中文给出 2-3 句话的分析总结，\
并推荐最适合展示这份数据的图表类型。

图表类型候选：bar（柱状图）、line（折线图）、pie（饼图）、scatter（散点图）、none（仅表格不展示图表）

请严格输出纯 JSON 格式，不要包含任何其他说明文字：
{
  "summary": "分析总结...",
  "chart_type": "bar"
}
"""

# 提取 ```sql ... ``` 代码块
_SQL_PATTERN = re.compile(r"```sql\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


def extract_sql(text: str) -> str | None:
    """从 LLM 响应文本中提取第一个 SQL 代码块。"""
    m = _SQL_PATTERN.search(text)
    if m:
        return m.group(1).strip()
    # 降级：如果没有代码块标记，尝试把整段文本当 SQL
    stripped = text.strip()
    if stripped.upper().startswith("SELECT"):
        return stripped
    return None

def force_extract_sql(text: str) -> str:
    """降级：如果没有代码块标记，提取可能的SQL。"""
    # 简单过滤，把所有的文字可能包进来的剥离掉
    import re
    # 寻找 select 开头的语句，直到结尾
    # 允许匹配多行
    m = re.search(r"(SELECT\s+.*)", text, re.IGNORECASE | re.DOTALL)
    if m:
        sql = m.group(1).strip()
        # 清理可能结尾带的markdown符号
        sql = re.sub(r"```[a-z]*$", "", sql, flags=re.IGNORECASE).strip()
        sql = re.sub(r"```$", "", sql).strip()
        return sql
    return ""

class SQLGenerator:
    """将自然语言问题 + Schema 上下文 → SQL。"""

    def __init__(
        self,
        llm: BaseLLM,
        default_limit: int = 100,
    ) -> None:
        self._llm = llm
        self._default_limit = default_limit

    # ------------------------------------------------------------------
    # SQL 生成
    # ------------------------------------------------------------------

    async def generate(
        self,
        question: str,
        schema_context: str,
        semantic_context: str = "",
        history: list[dict] | None = None,
    ) -> str:
        """调用 LLM 生成 SQL，返回提取后的 SQL 字符串。

        Raises:
            ValueError: 无法从 LLM 响应中提取有效 SQL
        """
        system = _SYSTEM_PROMPT_TEMPLATE.format(
            default_limit=self._default_limit,
            schema_context=schema_context,
        )
        if semantic_context:
            system += f"\n## 语义层\n{semantic_context}\n"

        messages: list[dict] = [{"role": "system", "content": system}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": question})

        response = await self._llm.chat(messages, temperature=0)
        sql = extract_sql(response)
        if not sql:
            raise ValueError(
                f"LLM 未返回有效 SQL 代码块。原始响应:\n{response[:500]}"
            )
        return sql

    async def generate_stream(
        self,
        question: str,
        schema_context: str,
        semantic_context: str = "",
        history: list[dict] | None = None,
    ):
        """流式生成 SQL，yield 文本片段。调用方负责拼接后提取 SQL。"""
        system = _SYSTEM_PROMPT_TEMPLATE.format(
            default_limit=self._default_limit,
            schema_context=schema_context,
        )
        if semantic_context:
            system += f"\n## 语义层\n{semantic_context}\n"

        messages: list[dict] = [{"role": "system", "content": system}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": question})

        async for chunk in self._llm.chat_stream(messages, temperature=0.1):
            yield chunk

    # ------------------------------------------------------------------
    # 结果摘要生成
    # ------------------------------------------------------------------

    async def generate_summary(
        self,
        question: str,
        sql: str,
        columns: list[str],
        rows: list[list],
        row_count: int,
    ) -> dict:
        """生成自然语言摘要 + 图表类型建议。

        Returns:
            {"summary": str, "chart_type": str}
        """
        import json

        # 只取前 20 行用于摘要，避免 token 超限
        preview_rows = rows[:20]
        result_preview = (
            "列名: " + ", ".join(columns) + "\n"
            + f"共 {row_count} 行，前 {len(preview_rows)} 行数据:\n"
            + "\n".join(str(r) for r in preview_rows)
        )

        messages = [
            {"role": "system", "content": _SUMMARY_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"用户问题: {question}\n\n"
                    f"执行的 SQL:\n```sql\n{sql}\n```\n\n"
                    f"查询结果:\n{result_preview}"
                ),
            },
        ]
        response = await self._llm.chat(messages, temperature=0.3)

        # 解析 JSON
        try:
            # 去掉可能的 markdown 代码块
            clean = re.sub(r"```[a-z]*\s*|\s*```", "", response).strip()
            # 尝试提取 {...} 中的内容
            match = re.search(r"\{.*\}", clean, re.DOTALL)
            if match:
                clean = match.group(0)
            
            data = json.loads(clean)
            chart_type = data.get("chart_type", "none")
            if chart_type not in ["bar", "line", "pie", "scatter", "none"]:
                chart_type = "none"
            return {"summary": data.get("summary", ""), "chart_type": chart_type}
        except (json.JSONDecodeError, ValueError, TypeError):
            # 降级：返回原始文本，并尝试从文本中正则提取 chart_type
            chart_type_match = re.search(r"(?:\"chart_type\"|chart_type)['\":\s]+(bar|line|pie|scatter|none)", response, re.IGNORECASE)
            chart_type = chart_type_match.group(1).lower() if chart_type_match else "none"
            return {"summary": response.strip(), "chart_type": chart_type}
