"""E2E Integration test for edge cases and complex scenarios.

Scenarios covered:
1. Querying an invalid/non-existent datasource.
2. LLM generates dangerous SQL (e.g. DROP TABLE), which should be caught by validator.
3. Multi-turn conversation (testing if history is correctly passed).
4. LLM returns no SQL.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio

# We reuse the e2e_client fixture from test_integration.py
# But we'll redefine it here to keep the file standalone, or just import it if it's in conftest.
# Actually, let's just copy the e2e_client fixture logic here for simplicity.

from httpx import ASGITransport, AsyncClient
from app.main import create_app
from app.models.database import get_db


@pytest.fixture
async def e2e_client(db_session):
    app = create_app()
    async def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_headers(e2e_client, test_users):
    """Login with the seeded admin user, return auth headers."""
    resp = await e2e_client.post("/api/auth/login", json={
        "username": "admin_user", "password": "adminpass"
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def setup_ds(e2e_client, auth_headers):
    ds_resp = await e2e_client.post("/api/datasources", json={
        "name": "edge_db", "db_type": "mysql", "host": "localhost",
        "port": 3306, "database": "test_db", "username": "root", "password": "pwd"
    }, headers=auth_headers)
    return ds_resp.json()["id"]


async def test_invalid_datasource(e2e_client, auth_headers):
    """Scenario 1: Querying an invalid datasource ID."""
    chat_resp = await e2e_client.post("/api/chat", json={
        "question": "What is the GMV?",
        "datasource_id": 99999,  # Doesn't exist
        "user_id": 1
    }, headers=auth_headers)
    
    assert chat_resp.status_code == 200
    events = []
    async for line in chat_resp.aiter_lines():
        if line.startswith("data: "):
            events.append(json.loads(line[6:].strip()))

    error_event = next((e for e in events if e["type"] == "error"), None)
    assert error_event is not None
    assert "不存在" in error_event["content"]


async def test_dangerous_sql_blocked(e2e_client, auth_headers, setup_ds):
    """Scenario 2: LLM generates DROP TABLE."""
    mock_llm = MagicMock()
    async def fake_stream(*args, **kwargs):
        yield "```sql\nDROP TABLE users;\n```"
    mock_llm.chat_stream.side_effect = lambda *a, **kw: fake_stream()

    with patch("app.core.agent.create_llm", return_value=mock_llm):
        chat_resp = await e2e_client.post("/api/chat", json={
            "question": "Delete all users",
            "datasource_id": setup_ds,
            "user_id": 1
        }, headers=auth_headers)
        
        events = []
        async for line in chat_resp.aiter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:].strip()))

    # Check that an error event was generated due to SQL validation failure
    error_event = next((e for e in events if e["type"] == "error"), None)
    assert error_event is not None
    assert "SQL 校验失败" in error_event["content"]
    assert "DROP" in error_event["content"] or "SELECT" in error_event["content"]


async def test_multi_turn_conversation(e2e_client, auth_headers, setup_ds):
    """Scenario 3: Multi-turn conversation."""
    mock_llm = MagicMock()
    
    # Turn 1
    async def fake_stream_1(*args, **kwargs):
        yield "```sql\nSELECT count(*) FROM users;\n```"
    mock_llm.chat_stream.side_effect = lambda *a, **kw: fake_stream_1()
    
    async def fake_chat_1(*args, **kwargs):
        return '{"summary": "You have 10 users", "chart_type": "table"}'
    mock_llm.chat = fake_chat_1

    mock_connector = AsyncMock()
    mock_connector.execute_query.return_value = (
        ["count"],
        [{"count": 10}],
    )

    with patch("app.core.agent.create_llm", return_value=mock_llm), \
         patch("app.core.agent.build_connector", return_value=mock_connector):
        
        resp1 = await e2e_client.post("/api/chat", json={
            "question": "How many users?",
            "datasource_id": setup_ds,
            "user_id": 1
        }, headers=auth_headers)
        
        events1 = []
        async for line in resp1.aiter_lines():
            if line.startswith("data: "):
                events1.append(json.loads(line[6:].strip()))
                
        done_event = next(e for e in events1 if e["type"] == "done")
        conv_id = done_event["conversation_id"]

    # Turn 2: Pass conversation_id
    async def fake_stream_2(*args, **kwargs):
        # We can inspect kwargs["history"] if needed, but here we just return a new SQL
        yield "```sql\nSELECT count(*) FROM orders;\n```"
    mock_llm.chat_stream.side_effect = lambda *a, **kw: fake_stream_2()

    with patch("app.core.agent.create_llm", return_value=mock_llm), \
         patch("app.core.agent.build_connector", return_value=mock_connector):
        
        resp2 = await e2e_client.post("/api/chat", json={
            "question": "What about orders?",
            "datasource_id": setup_ds,
            "conversation_id": conv_id,
            "user_id": 1
        }, headers=auth_headers)
        
        events2 = []
        async for line in resp2.aiter_lines():
            if line.startswith("data: "):
                events2.append(json.loads(line[6:].strip()))

        done_event2 = next(e for e in events2 if e["type"] == "done")
        assert done_event2["conversation_id"] == conv_id

    # Verify history is saved
    history_resp = await e2e_client.get(f"/api/conversations/{conv_id}/messages", headers=auth_headers)
    assert history_resp.status_code == 200
    msgs = history_resp.json()
    # User -> Assistant -> User -> Assistant
    assert len(msgs) == 4
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "How many users?"
    assert msgs[1]["role"] == "assistant"
    assert msgs[1]["content"] == "You have 10 users"
    assert msgs[2]["role"] == "user"
    assert msgs[2]["content"] == "What about orders?"


async def test_llm_returns_no_sql(e2e_client, auth_headers, setup_ds):
    """Scenario 4: LLM returns text but no SQL code block."""
    mock_llm = MagicMock()
    async def fake_stream(*args, **kwargs):
        yield "I'm sorry, I don't know how to answer that."
    mock_llm.chat_stream.side_effect = lambda *a, **kw: fake_stream()

    with patch("app.core.agent.create_llm", return_value=mock_llm):
        chat_resp = await e2e_client.post("/api/chat", json={
            "question": "Tell me a joke",
            "datasource_id": setup_ds,
            "user_id": 1
        }, headers=auth_headers)
        
        events = []
        async for line in chat_resp.aiter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:].strip()))

    error_event = next((e for e in events if e["type"] == "error"), None)
    assert error_event is not None
    assert "LLM 未返回有效 SQL" in error_event["content"]
