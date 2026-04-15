"""Metadata automatic discovery service."""

import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.factory import build_connector
from app.models.datasource import DataSource, TableMetadata


class SchemaDiscoveryService:
    """Discovers and synchronizes schema metadata from a datasource to our metadata DB."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def discover(self, datasource: DataSource) -> int:
        """
        Connects to the datasource, reads all tables and columns, 
        and updates TableMetadata records.
        Returns the number of tables discovered.
        """
        if datasource.db_type != "mysql":
            raise NotImplementedError(f"Discovery not implemented for {datasource.db_type}")

        connector = build_connector(datasource)
        try:
            await connector.connect()
            tables = await connector.get_tables()

            count = 0
            for table_name in tables:
                columns = await connector.get_table_schema(table_name)
                table_comment = await connector.get_table_comment(table_name) or ""

                # Create or Update the metadata record
                from sqlalchemy import select
                stmt = select(TableMetadata).where(
                    TableMetadata.datasource_id == datasource.id,
                    TableMetadata.table_name == table_name
                )
                result = await self.db.execute(stmt)
                meta_record = result.scalar_one_or_none()

                columns_json = json.dumps(columns, ensure_ascii=False)

                if meta_record:
                    meta_record.columns_json = columns_json
                    meta_record.table_comment = table_comment
                else:
                    meta_record = TableMetadata(
                        datasource_id=datasource.id,
                        table_name=table_name,
                        table_comment=table_comment,
                        columns_json=columns_json
                    )
                    self.db.add(meta_record)
                count += 1

            await self.db.commit()
            return count

        finally:
            await connector.close()
