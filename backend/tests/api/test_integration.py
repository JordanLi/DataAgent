"""E2E Integration test linking Step 1 through Step 8.

Tests the full flow:
1. Auth: Register and Login
2. Datasource: Create a datasource
3. Semantic: Add a business term to the datasource
4. Chat: Send a natural language query, orchestrating LLM (mocked), 
   SQL validation, query execution (mocked connector), and summary generation.
5. Admin: Verify that an audit log was automatically created.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.models.database import get_db


pytestmark = pytest.mark.asyncio


@pytest.fixture
async def e2e_client(db_session):
    """Client for E2E tests, using the same db_session as conftest."""
    app = create_app()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


async def test_full_pipeline(e2e_client, test_users):
    # First, login with the default admin created by test fixture
    admin_login_resp = await e2e_client.post("/api/auth/login", json={
        "username": "admin_user",
        "password": "adminpass"
    })
    assert admin_login_resp.status_code == 200
    admin_token = admin_login_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # ── 1. Auth: Register & Login (Step 8/11) ────────────────────────────────
    await e2e_client.post("/api/auth/register", json={
        "username": "e2e_user",
        "password": "password123",
        "role": "admin"
    }, headers=admin_headers)
    login_resp = await e2e_client.post("/api/auth/login", json={
        "username": "e2e_user",
        "password": "password123"
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # ── 2. Datasource: Create (Step 4/8) ─────────────────────────────────────
    ds_resp = await e2e_client.post("/api/datasources", json={
        "name": "e2e_db",
        "db_type": "mysql",
        "host": "localhost",
        "port": 3306,
        "database": "test_db",
        "username": "root",
        "password": "pwd"
    }, headers=headers)
    assert ds_resp.status_code == 201
    ds_id = ds_resp.json()["id"]

    # ── 3. Semantic: Add business term (Step 5/8) ────────────────────────────
    term_resp = await e2e_client.post(f"/api/semantic/datasources/{ds_id}/terms", json={
        "term_name": "GMV",
        "definition": "Gross Merchandise Volume",
        "sql_expression": "SUM(amount) WHERE status=1"
    }, headers=headers)
    assert term_resp.status_code == 201

    # Verify Preview (Step 5/8)
    preview_resp = await e2e_client.get(f"/api/semantic/datasources/{ds_id}/preview", headers=headers)
    assert preview_resp.status_code == 200
    preview_data = preview_resp.json()
    assert "GMV" in preview_data["semantic_context"]

    # ── 4. Chat: NL to SQL (Step 6 & 7) ──────────────────────────────────────
    # We mock LLM and Connector to avoid real network/DB calls.
    from unittest.mock import MagicMock
    mock_llm = MagicMock()
    
    async def fake_stream(*args, **kwargs):
        yield "```sql\n"
        yield "SELECT * FROM orders LIMIT 10;\n"
        yield "```"
        
    mock_llm.chat_stream.side_effect = lambda *a, **kw: fake_stream()
    
    async def fake_chat(*args, **kwargs):
        return '{"summary": "Test insight", "chart_type": "bar"}'
    mock_llm.chat = fake_chat

    mock_connector = AsyncMock()
    mock_connector.execute_query.return_value = (
        ["id", "amount"],
        [{"id": 1, "amount": 100}],
    )

    # Patch factory functions
    with patch("app.core.agent.create_llm", return_value=mock_llm), \
         patch("app.core.agent.build_connector", return_value=mock_connector):
        
        chat_resp = await e2e_client.post("/api/chat", json={
            "question": "What is the GMV?",
            "datasource_id": ds_id,
            "user_id": 1
        }, headers=headers)
        
        assert chat_resp.status_code == 200
        
        # Parse SSE stream
        events = []
        async for line in chat_resp.aiter_lines():
            if line.startswith("data: "):
                data_str = line[len("data: "):].strip()
                events.append(json.loads(data_str))

    # Verify SSE events trace the pipeline
    event_types = [e["type"] for e in events]
    assert "thinking" in event_types
    assert "sql_stream" in event_types
    assert "sql" in event_types
    # Step 7 SQL validation should inject LIMIT 100 or preserve existing
    assert "result" in event_types
    assert "summary" in event_types
    assert "done" in event_types

    # Find the result event and summary event
    result_event = next(e for e in events if e["type"] == "result")
    assert result_event["row_count"] == 1
    assert result_event["columns"] == ["id", "amount"]

    summary_event = next(e for e in events if e["type"] == "summary")
    assert summary_event["content"] == "Test insight"
    assert summary_event["chart_type"] == "bar"

    # ── 5. Admin: Verify Audit Log (Step 8) ──────────────────────────────────
    audit_resp = await e2e_client.get("/api/admin/audit-logs", headers=headers)
    assert audit_resp.status_code == 200
    logs = audit_resp.json()
    query_logs = [l for l in logs if l["action"] == "query"]
    assert len(query_logs) == 1
    assert query_logs[0]["datasource_id"] == ds_id
    assert query_logs[0]["row_count"] == 1
    assert "SELECT * FROM orders" in query_logs[0]["sql_executed"]
