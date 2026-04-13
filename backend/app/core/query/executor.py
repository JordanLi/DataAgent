"""QueryExecutor: 安全执行 SQL 并返回结构化结果。

在 MySQL 只读连接上执行，强制超时和行数上限，
将原始结果转为 JSON 友好的格式。
"""

from __future__ import annotations

import asyncio
import datetime
import decimal
import logging
from typing import Any

from app.connectors.base import BaseConnector

logger = logging.getLogger(__name__)


def _serialize_value(v: Any) -> Any:
    """将数据库原始值转为 JSON 可序列化类型。"""
    if v is None:
        return None
    if isinstance(v, (datetime.datetime, datetime.date, datetime.time)):
        return v.isoformat()
    if isinstance(v, decimal.Decimal):
        return float(v)
    if isinstance(v, bytes):
        return v.decode("utf-8", errors="replace")
    return v


class QueryExecutor:
    """在给定连接器上安全执行 SELECT 语句。"""

    def __init__(
        self,
        connector: BaseConnector,
        timeout: int = 30,
        max_rows: int = 10_000,
    ) -> None:
        self._connector = connector
        self._timeout = timeout
        self._max_rows = max_rows

    async def execute(self, sql: str) -> dict[str, Any]:
        """执行 SQL 并返回结构化结果字典。

        Returns:
            {
                "columns":          list[str],
                "rows":             list[list],   # JSON 可序列化
                "row_count":        int,
                "execution_time_ms": int,
                "truncated":        bool,         # 是否因行数限制被截断
            }

        Raises:
            asyncio.TimeoutError: 超时
            Exception: 执行错误（由连接器向上抛出）
        """
        try:
            start_time = asyncio.get_event_loop().time()
            columns, dict_rows = await asyncio.wait_for(
                self._connector.execute_query(sql),
                timeout=self._timeout
            )
            end_time = asyncio.get_event_loop().time()
            
            rows = [[row.get(col) for col in columns] for row in dict_rows]
            execution_time_ms = int((end_time - start_time) * 1000)
            
        except asyncio.TimeoutError:
            logger.warning("Query timed out after %ds: %.200s", self._timeout, sql)
            raise

        # 判断是否被截断
        truncated = len(rows) > self._max_rows
        if truncated:
            rows = rows[: self._max_rows]

        # 序列化每个值
        safe_rows = [
            [_serialize_value(cell) for cell in row]
            for row in rows
        ]

        return {
            "columns": columns,
            "rows": safe_rows,
            "row_count": len(safe_rows),
            "execution_time_ms": execution_time_ms,
            "truncated": truncated,
        }
