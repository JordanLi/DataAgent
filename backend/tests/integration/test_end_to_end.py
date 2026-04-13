import pytest
from unittest.mock import AsyncMock, patch

from app.schemas.datasource import DataSourceCreate, DataSourceOut
from app.schemas.semantic import BusinessTermCreate, FieldAliasCreate
from app.schemas.conversation import ConversationCreate

@pytest.mark.asyncio
@patch("app.api.datasource.build_connector")
@patch("app.core.agent.create_llm")
@patch("app.core.agent.build_connector")
async def test_end_to_end_flow(
    mock_build_connector_chat,
    mock_create_llm,
    mock_build_connector_ds,
    async_client
):
    """
    Tests the complete end-to-end flow from Step 1 to Step 8:
    1. Create a MySQL Datasource
    2. Discover schema (mocking the MySQLConnector)
    3. Configure Semantic Layer (Alias, Business Term)
    4. Create Conversation
    5. Trigger Chat (mocking LLM and MySQL execution)
    6. Verify Chat SSE stream
    7. Verify Audit Logs are written
    """

    # -------------------------------------------------------------------------
    # Mock Setups
    # -------------------------------------------------------------------------
    # 1. Mock the SchemaDiscovery connector behavior
    mock_connector_ds = AsyncMock()
    mock_connector_ds.test_connection.return_value = True
    mock_connector_ds.get_tables.return_value = ["orders"]
    mock_connector_ds.get_table_schema.return_value = [
        {"name": "id", "type": "int", "nullable": False, "primary_key": True, "comment": "Order ID"},
        {"name": "status", "type": "int", "nullable": True, "primary_key": False, "comment": "Order status"},
        {"name": "amount", "type": "decimal", "nullable": True, "primary_key": False, "comment": "Amount in USD"}
    ]
    # In SQLite for testing, mock execute to return table comment empty
    mock_connector_ds.pool.acquire.return_value.__aenter__.return_value.cursor.return_value.__aenter__.return_value.fetchone.return_value = ["Order records"]
    mock_build_connector_ds.return_value = mock_connector_ds

    # 2. Mock the Chat Query execution connector behavior
    mock_connector_chat = AsyncMock()
    mock_connector_chat.execute_query.return_value = {
        "columns": ["status", "total_amount"],
        "rows": [[1, 500.0], [2, 1200.0]],
        "row_count": 2,
        "execution_time_ms": 15
    }
    mock_build_connector_chat.return_value = mock_connector_chat

    # 3. Mock LLM layer
    mock_llm = AsyncMock()
    # First call is generate() via chat(), next call is generate_stream() via chat_stream()
    # Actually, generate_stream() yields chunks, so let's mock it as an async generator
    async def mock_stream(*args, **kwargs):
        chunks = ["```sql\\n", "SELECT status, SUM(amount) AS total_amount ", "FROM orders ", "GROUP BY status", "\\n```"]
        for c in chunks:
            yield c
    mock_llm.chat_stream = mock_stream
    
    # generate_summary calls chat()
    mock_llm.chat.return_value = '{"summary": "Total sales by status look good.", "chart_type": "bar"}'
    mock_create_llm.return_value = mock_llm

    # -------------------------------------------------------------------------
    # API Testing Flow
    # -------------------------------------------------------------------------
    
    # A. Create Datasource
    ds_payload = {
        "name": "test_mysql",
        "db_type": "mysql",
        "host": "localhost",
        "port": 3306,
        "database": "test_db",
        "username": "root",
        "password": "password"
    }
    res = await async_client.post("/api/datasources", json=ds_payload)
    assert res.status_code == 201
    ds_id = res.json()["id"]

    # B. Test Connection and Discover Schema
    res = await async_client.post(f"/api/datasources/{ds_id}/test")
    assert res.status_code == 200

    res = await async_client.post(f"/api/datasources/{ds_id}/discover")
    assert res.status_code == 200
    tables = res.json()
    assert len(tables) == 1
    assert tables[0]["table_name"] == "orders"

    # C. Configure Semantic Layer
    # 1. Alias
    alias_payload = {
        "table_name": "orders",
        "column_name": "amount",
        "alias_name": "Order Value",
        "description": "The transaction value"
    }
    res = await async_client.post(f"/api/semantic/datasources/{ds_id}/aliases", json=alias_payload)
    assert res.status_code == 201

    # 2. Business Term
    term_payload = {
        "term_name": "Total Revenue",
        "definition": "Sum of successful order amounts",
        "sql_expression": "SUM(amount) WHERE status=2"
    }
    res = await async_client.post(f"/api/semantic/datasources/{ds_id}/terms", json=term_payload)
    assert res.status_code == 201

    # Check Preview Context
    res = await async_client.get(f"/api/semantic/datasources/{ds_id}/preview")
    assert res.status_code == 200
    preview = res.json()
    assert "Total Revenue" in preview["semantic_context"]
    assert "Order Value" in preview["schema_context"]

    # D. Create Conversation
    conv_payload = {"title": "Sales Analysis"}
    res = await async_client.post("/api/conversations", json=conv_payload)
    assert res.status_code == 201
    conv_id = res.json()["id"]

    # E. Trigger Chat (SSE)
    chat_payload = {
        "question": "Show me total revenue by status",
        "datasource_id": ds_id,
        "conversation_id": conv_id,
        "user_id": 1
    }
    
    # We will read the SSE stream
    async with async_client.stream("POST", "/api/chat", json=chat_payload) as response:
        assert response.status_code == 200
        content = await response.aread()
        text = content.decode("utf-8")
        
        # Verify the events exist in the stream output
        assert "thinking" in text
        assert "sql_stream" in text
        assert "sql" in text
        assert "SELECT status, SUM(amount)" in text
        assert "result" in text
        assert "summary" in text
        assert "Total sales by status" in text
        assert "done" in text

    # F. Verify Chat History saved
    res = await async_client.get(f"/api/conversations/{conv_id}/messages")
    assert res.status_code == 200
    messages = res.json()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["sql_generated"] is not None

    # G. Verify Audit Logs
    res = await async_client.get("/api/admin/audit-logs")
    assert res.status_code == 200
    logs = res.json()
    assert len(logs) >= 1
    assert logs[0]["action"] == "query"
    assert logs[0]["datasource_id"] == ds_id
    assert logs[0]["sql_executed"] is not None
