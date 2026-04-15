"""MySQL datasource connector implementation."""

from typing import Any

import aiomysql

from app.connectors.base import BaseConnector
from app.models.datasource import DataSource


class MySQLConnector(BaseConnector):
    """MySQL connector using aiomysql."""

    def __init__(self, datasource: DataSource):
        self.host = datasource.host
        self.port = datasource.port
        self.user = datasource.username
        self.password = datasource.encrypted_password  # Should be decrypted in real prod
        self.db = datasource.database
        self.pool: aiomysql.Pool | None = None

    async def connect(self) -> None:
        """Initialize aiomysql connection pool."""
        if not self.pool:
            self.pool = await aiomysql.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                db=self.db,
                minsize=1,
                maxsize=10,
                autocommit=True,
                charset="utf8mb4",
                # Force read-only session for safety
                init_command="SET SESSION TRANSACTION READ ONLY"
            )

    async def close(self) -> None:
        """Close the connection pool."""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            self.pool = None

    async def test_connection(self) -> bool:
        """Test if credentials are valid."""
        try:
            await self.connect()
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1")
            return True
        except Exception:
            return False

    async def execute_query(self, query: str) -> tuple[list[str], list[dict[str, Any]]]:
        """Execute a read-only SQL query."""
        if not self.pool:
            await self.connect()

        assert self.pool is not None
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query)
                rows = await cur.fetchall()
                # If there are no rows, description might still be available
                columns = [desc[0] for desc in cur.description] if cur.description else []
                return columns, list(rows)

    async def get_tables(self) -> list[str]:
        """Fetch all non-system tables."""
        query = """
            SELECT TABLE_NAME 
            FROM information_schema.tables 
            WHERE table_schema = %s 
              AND table_type = 'BASE TABLE'
        """
        if not self.pool:
            await self.connect()
            
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (self.db,))
                rows = await cur.fetchall()
                return [row[0] for row in rows]

    async def get_table_schema(self, table_name: str) -> list[dict[str, Any]]:
        """Fetch column metadata from information_schema."""
        query = """
            SELECT 
                COLUMN_NAME as name,
                COLUMN_TYPE as type,
                IS_NULLABLE as is_nullable,
                COLUMN_KEY as column_key,
                COLUMN_COMMENT as comment
            FROM information_schema.columns 
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ORDINAL_POSITION
        """
        if not self.pool:
            await self.connect()
            
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, (self.db, table_name))
                rows = await cur.fetchall()
                
                columns = []
                for r in rows:
                    columns.append({
                        "name": r["name"],
                        "type": r["type"],
                        "nullable": r["is_nullable"] == "YES",
                        "primary_key": r["column_key"] == "PRI",
                        "comment": r["comment"] or ""
                    })
                return columns

    async def get_table_comment(self, table_name: str) -> str | None:
        """Fetch the table-level comment from information_schema."""
        query = """
            SELECT TABLE_COMMENT
            FROM information_schema.tables
            WHERE table_schema = %s AND table_name = %s
        """
        if not self.pool:
            await self.connect()
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (self.db, table_name))
                row = await cur.fetchone()
                return row[0] if row and row[0] else None
