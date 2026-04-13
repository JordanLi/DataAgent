"""SQLValidator: SQL 安全校验器。

使用 sqlglot 解析 SQL AST，执行以下检查：
1. 只允许 SELECT 语句（拒绝所有 DDL / DML）
2. 检测 SQL 注入危险模式
3. 如果没有 LIMIT 子句则自动补充
4. （可选）检查引用的表/字段是否存在于已知 Schema 中
"""

from __future__ import annotations

import re

import sqlglot
import sqlglot.expressions as exp


# ---------------------------------------------------------------------------
# 危险关键字黑名单（防注入 / 恶意语句）
# ---------------------------------------------------------------------------
_DANGEROUS_PATTERNS = [
    re.compile(r"\bINTO\s+OUTFILE\b", re.IGNORECASE),
    re.compile(r"\bINTO\s+DUMPFILE\b", re.IGNORECASE),
    re.compile(r"\bLOAD_FILE\s*\(", re.IGNORECASE),
    re.compile(r"\bSLEEP\s*\(", re.IGNORECASE),
    re.compile(r"\bBENCHMARK\s*\(", re.IGNORECASE),
    re.compile(r"\bWAITFOR\s+DELAY\b", re.IGNORECASE),
    re.compile(r";\s*--", re.IGNORECASE),          # statement terminator + comment
    re.compile(r";\s*#", re.IGNORECASE),
    re.compile(r"/\*.*?\*/", re.DOTALL),           # block comments
    re.compile(r"\bINFORMATION_SCHEMA\b", re.IGNORECASE),
    re.compile(r"\bMYSQL\s*\.\s*USER\b", re.IGNORECASE),
]

# 允许的顶层语句类型（sqlglot expression classes）
_ALLOWED_STMT_TYPES = (exp.Select,)


class ValidationError(ValueError):
    """SQL 未通过安全校验。"""


class SQLValidator:
    """对 LLM 生成的 SQL 进行静态安全校验。"""

    def __init__(
        self,
        default_limit: int = 100,
        max_limit: int = 10_000,
        known_tables: list[str] | None = None,
    ) -> None:
        self._default_limit = default_limit
        self._max_limit = max_limit
        self._known_tables = {t.lower() for t in (known_tables or [])}

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

    def validate_and_rewrite(self, sql: str) -> str:
        """校验 SQL 并在必要时重写（如补 LIMIT），返回安全的 SQL 字符串。

        Raises:
            ValidationError: 校验失败时抛出，附带原因描述。
        """
        sql = sql.strip().rstrip(";")

        # 1. 危险模式检测
        self._check_dangerous_patterns(sql)

        # 2. AST 解析
        try:
            statements = sqlglot.parse(sql, dialect="mysql")
        except sqlglot.errors.ParseError as exc:
            raise ValidationError(f"SQL 解析失败: {exc}") from exc

        if not statements or statements[0] is None:
            raise ValidationError("SQL 为空或无法解析")

        stmt = statements[0]

        # 3. 只允许 SELECT
        if not isinstance(stmt, exp.Select):
            stmt_type = type(stmt).__name__.upper()
            raise ValidationError(
                f"只允许 SELECT 语句，检测到: {stmt_type}"
            )

        # 4. 禁止多语句（注入防护）
        if len([s for s in statements if s is not None]) > 1:
            raise ValidationError("不允许在单次请求中执行多条 SQL 语句")

        # 5. 检查已知表名（如果提供了 schema 信息）
        if self._known_tables:
            self._check_tables(stmt)

        # 6. 补充 / 校正 LIMIT
        stmt = self._ensure_limit(stmt)

        return stmt.sql(dialect="mysql")

    # ------------------------------------------------------------------
    # 私有检查方法
    # ------------------------------------------------------------------

    def _check_dangerous_patterns(self, sql: str) -> None:
        for pattern in _DANGEROUS_PATTERNS:
            if pattern.search(sql):
                raise ValidationError(
                    f"SQL 包含危险模式: {pattern.pattern!r}"
                )

    def _check_tables(self, stmt: exp.Select) -> None:
        referenced = {
            tbl.name.lower()
            for tbl in stmt.find_all(exp.Table)
            if tbl.name
        }
        unknown = referenced - self._known_tables
        if unknown:
            raise ValidationError(
                f"SQL 引用了未知表: {', '.join(sorted(unknown))}"
            )

    def _ensure_limit(self, stmt: exp.Select) -> exp.Select:
        """如果 SELECT 没有 LIMIT，注入默认值；如果超出上限，截断到上限。"""
        limit_node = stmt.args.get("limit")

        if limit_node is None:
            # 没有 LIMIT，注入默认值
            stmt = stmt.limit(self._default_limit)
        else:
            # 有 LIMIT，检查值是否超限
            try:
                # sqlglot 26.x: Limit uses 'expression' arg, not 'this'
                limit_expr = limit_node.args.get("expression")
                current = int(limit_expr.this) if limit_expr is not None else None
                if current is not None and current > self._max_limit:
                    stmt = stmt.limit(self._max_limit)
            except (AttributeError, TypeError, ValueError):
                # 无法静态求值（例如表达式），保留原样
                pass

        return stmt
