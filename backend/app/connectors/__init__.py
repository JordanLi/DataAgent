"""Database connector package. Implemented in Step 4."""

from app.connectors.base import BaseConnector
from app.connectors.crypto import encrypt_password, decrypt_password
from app.connectors.mysql_connector import MySQLConnector
from app.connectors.schema_discovery import SchemaDiscoveryService as SchemaDiscovery
from app.models.datasource import DataSource


def build_connector(datasource: DataSource) -> BaseConnector:
    """Factory to build a connector instance based on the datasource type."""
    if datasource.db_type == "mysql":
        return MySQLConnector(datasource)
    raise NotImplementedError(f"Unsupported database type: {datasource.db_type}")
