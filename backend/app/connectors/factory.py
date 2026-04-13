"""Connector factory: builds the appropriate BaseConnector for a DataSource row."""

from __future__ import annotations

from app.connectors.base import BaseConnector
from app.connectors.crypto import decrypt_password
from app.connectors.mysql_connector import MySQLConnector
from app.models.datasource import DataSource, DbType


def build_connector(datasource: DataSource) -> BaseConnector:
    """Instantiate and return the correct connector for *datasource*.

    The encrypted_password stored on the model is decrypted transparently so
    callers never need to handle raw credentials.

    Raises ValueError for unsupported db_type values (future-proofing).
    """
    password = decrypt_password(datasource.encrypted_password)

    if datasource.db_type == DbType.mysql:
        return MySQLConnector(
            host=datasource.host,
            port=datasource.port,
            database=datasource.database,
            username=datasource.username,
            password=password,
        )

    raise ValueError(f"Unsupported db_type: {datasource.db_type!r}")
