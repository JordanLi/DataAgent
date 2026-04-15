"""Base abstraction for datasource connectors."""

from abc import ABC, abstractmethod
from typing import Any


class BaseConnector(ABC):
    """Abstract base class for all database connectors."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection or connection pool."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close connection or connection pool."""
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if the connection parameters are valid."""
        pass

    @abstractmethod
    async def execute_query(self, query: str) -> tuple[list[str], list[dict[str, Any]]]:
        """
        Execute a read-only query.
        
        :param query: SQL query string
        :return: Tuple of (column_names, list of row dicts)
        """
        pass

    @abstractmethod
    async def get_tables(self) -> list[str]:
        """Get a list of all tables in the database."""
        pass

    @abstractmethod
    async def get_table_schema(self, table_name: str) -> list[dict[str, Any]]:
        """
        Get the schema for a specific table.
        
        :param table_name: Name of the table
        :return: List of dicts describing columns (name, type, etc.)
        """
        pass

    async def get_table_comment(self, table_name: str) -> str | None:
        """Get the comment for a specific table. Returns None by default."""
        return None
