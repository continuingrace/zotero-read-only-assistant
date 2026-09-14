from __future__ import annotations

import httpx
import pytest

from app.config import Settings
from app.mcp_server import create_app
from app.zotero import ZoteroClient, classify_item


TOKEN = "test-token-" + "x" * 40


def settings() -> Settings:
    return Settings(auth_token=TOKEN)


def zotero_transport(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path.endswith("/users/0/items/ABCD1234"):
        return httpx.Response(200, json={"key": "ABCD1234", "data": {"key": "ABCD1234", "itemType": "journalArticle", "title": "Read-only test", "tags": [{"tag": "test"}]}}, request=request)
    if path.endswith("/users/0/items/ABCD1234/children"):
        return httpx.Response(200, json=[{"key": "PDF12345", "data": {"key": "PDF12345", "itemType": "attachment", "parentItem": "ABCD1234", "contentType": "application/pdf", "filename": "paper.pdf"}}], request=request)
    if path.endswith("/users/0/items"):
        return httpx.Response(200, json=[{"key": "ABCD1234", "data": {"key": "ABCD1234", "itemType": "journalArticle", "title": "Read-only test"}}, {"key": "PDF12345", "data": {"key": "PDF12345", "itemType": "attachment", "contentType": "application/pdf", "filename": "paper.pdf"}}], request=request)
    if path.endswith("/users/0/tags"):
        return httpx.Response(200, json=[{"tag": "test", "type": 0}], request=request)
    if path.endswith("/users/0/collections"):
        return httpx.Response(200, json=[{"key": "COLL1234", "data": {"name": "Research"}}], request=request)
    return httpx.Response(404, json={}, request=request)


@pytest.fixture
def app():
    client = ZoteroClient(settings().zotero_base_url, transport=httpx.MockTransport(zotero_transport))
    return create_app(settings(), client)


@pytest.mark.asyncio
async def test_auth_and_tools_list(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        denied = await client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        assert denied.status_code == 401
        response = await client.post("/mcp", headers={"Authorization": f"Bearer {TOKEN}"}, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert response.status_code == 200
    tools = response.json()["result"]["tools"]
    assert len(tools) == 7
    assert all(item["name"].startswith("zotero_read_only_") for item in tools)
    assert all(item["annotations"]["readOnlyHint"] for item in tools)


@pytest.mark.asyncio
async def test_read_only_tool_call_and_classification(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/mcp", headers={"Authorization": f"Bearer {TOKEN}"}, json={"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "zotero_read_only_get_item_metadata", "arguments": {"item_key": "ABCD1234"}}})
    assert response.status_code == 200
    payload = response.json()["result"]["structuredContent"]
    assert payload["classification"] == "bibliographic_record"
    assert payload["child_attachments"][0]["classification"] == "child_attachment"
    assert classify_item({"itemType": "attachment", "contentType": "application/pdf"}) == "standalone_pdf"


@pytest.mark.asyncio
async def test_unknown_tool_is_rejected(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/mcp", headers={"Authorization": f"Bearer {TOKEN}"}, json={"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "write_something", "arguments": {}}})
    assert response.json()["error"]["code"] == -32602
