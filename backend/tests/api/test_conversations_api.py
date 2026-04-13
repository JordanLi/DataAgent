"""API tests for /api/conversations — 会话管理。

TC-CONV-01  列出会话（空列表）
TC-CONV-02  创建会话 -> 201
TC-CONV-03  获取会话详情（含空消息列表）
TC-CONV-04  获取不存在会话 -> 404
TC-CONV-05  获取会话的消息列表
TC-CONV-06  删除会话 -> 204
TC-CONV-07  删除不存在会话 -> 404
"""

from __future__ import annotations

import pytest
from sqlalchemy import insert

from app.models.conversation import Message


pytestmark = pytest.mark.anyio


async def test_tc_conv_01_list_empty(client):
    resp = await client.get("/api/conversations?user_id=1")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_tc_conv_02_create_conversation(client):
    resp = await client.post(
        "/api/conversations?user_id=1",
        json={"title": "测试对话"}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "测试对话"
    assert "id" in data


async def test_tc_conv_03_get_conversation_detail(client):
    create = await client.post(
        "/api/conversations?user_id=1",
        json={"title": "详情测试"}
    )
    conv_id = create.json()["id"]
    resp = await client.get(f"/api/conversations/{conv_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "详情测试"
    assert data["messages"] == []


async def test_tc_conv_04_get_nonexistent(client):
    resp = await client.get("/api/conversations/99999")
    assert resp.status_code == 404


async def test_tc_conv_05_list_messages(client, db_session):
    create = await client.post(
        "/api/conversations?user_id=1",
        json={"title": "消息测试"}
    )
    conv_id = create.json()["id"]

    # 直接插入一条消息
    await db_session.execute(
        insert(Message).values(
            conversation_id=conv_id,
            role="user",
            content="查询最近7天的订单数量"
        )
    )
    await db_session.commit()

    resp = await client.get(f"/api/conversations/{conv_id}/messages")
    assert resp.status_code == 200
    msgs = resp.json()
    assert len(msgs) == 1
    assert msgs[0]["content"] == "查询最近7天的订单数量"


async def test_tc_conv_06_delete_conversation(client):
    create = await client.post(
        "/api/conversations?user_id=1",
        json={"title": "待删除"}
    )
    conv_id = create.json()["id"]
    del_resp = await client.delete(f"/api/conversations/{conv_id}")
    assert del_resp.status_code == 204
    get_resp = await client.get(f"/api/conversations/{conv_id}")
    assert get_resp.status_code == 404


async def test_tc_conv_07_delete_nonexistent(client):
    resp = await client.delete("/api/conversations/99999")
    assert resp.status_code == 404
