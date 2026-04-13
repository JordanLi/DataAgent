"""Database connector package. Implemented in Step 4."""

from app.connectors.base import BaseConnector
from app.connectors.mysql_connector import MySQLConnector
from app.connectors.schema_discovery import SchemaDiscoveryService as SchemaDiscovery
from app.models.datasource import DataSource


def build_connector(datasource: DataSource) -> BaseConnector:
    """Factory to build a connector instance based on the datasource type."""
    if datasource.db_type == "mysql":
        return MySQLConnector(datasource)
    raise NotImplementedError(f"Unsupported database type: {datasource.db_type}")

def encrypt_password(password: str) -> str:
    """Encrypt a database password for storage (MVP uses plaintext or simple masking)."""
    # For MVP, we'll store it as-is or you can integrate cryptography/Fernet here.
    return password
