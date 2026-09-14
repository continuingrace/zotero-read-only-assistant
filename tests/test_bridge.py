from __future__ import annotations

import json

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
    if path.endswith("/users/0/items/PDF12345/fulltext"):
        return httpx.Response(200, json={"content": "A" * 2500, "indexedPages": 2, "totalPages": 2}, request=request)
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
    assert len(tools) == 10
    read_tools = [item for item in tools if item["name"].startswith("zotero_read_only_")]
    write_tools = [item for item in tools if item["name"].startswith("zotero_write_")]
    assert len(read_tools) == 8
    assert len(write_tools) == 2
    assert all(item["annotations"]["readOnlyHint"] for item in read_tools)
    assert all(not item["annotations"]["readOnlyHint"] for item in write_tools)


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


@pytest.mark.asyncio
async def test_pdf_fulltext_can_be_read_in_bounded_chunks(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/mcp", headers={"Authorization": f"Bearer {TOKEN}"}, json={"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "zotero_read_only_get_pdf_text", "arguments": {"item_key": "ABCD1234", "start": 1000, "max_chars": 1000}}})
    payload = response.json()["result"]["structuredContent"]
    assert payload["attachment_key"] == "PDF12345"
    assert len(payload["content"]) == 1000
    assert payload["has_more"] is True


@pytest.mark.asyncio
async def test_tag_write_uses_zotero_authorization_and_preserves_existing_tags():
    state = {"tags": [{"tag": "기존"}], "authorized": False, "patched": None}

    def write_transport(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "GET" and path.endswith("/api/"):
            return httpx.Response(200, json={}, headers={"Zotero-Server-ID": "server-1"}, request=request)
        if request.method == "POST" and path.endswith("/api/local/authorize"):
            state["authorized"] = True
            return httpx.Response(200, json={"key": "local-write-key", "remember": False}, request=request)
        if request.method == "PATCH" and path.endswith("/users/0/items/ABCD1234"):
            assert state["authorized"] is True
            assert request.headers["Zotero-API-Key"] == "local-write-key"
            state["patched"] = json.loads(request.content)
            state["tags"] = state["patched"]["tags"]
            return httpx.Response(204, request=request)
        if request.method == "GET" and path.endswith("/users/0/items/ABCD1234"):
            return httpx.Response(200, json={"key": "ABCD1234", "version": 7, "data": {"key": "ABCD1234", "version": 7, "itemType": "journalArticle", "title": "Paper", "tags": state["tags"]}}, request=request)
        return httpx.Response(404, json={}, request=request)

    zotero = ZoteroClient(settings().zotero_base_url, transport=httpx.MockTransport(write_transport))
    app = create_app(settings(), zotero)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/mcp", headers={"Authorization": f"Bearer {TOKEN}"}, json={"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "zotero_write_tag_with_confirmation", "arguments": {"item_key": "ABCD1234", "action": "add", "tag": "새 태그"}}})
    payload = response.json()["result"]["structuredContent"]
    assert payload["changed"] is True
    assert payload["before"] == ["기존"]
    assert payload["after"] == ["기존", "새 태그"]


@pytest.mark.asyncio
async def test_reader_formats_tags_and_collections_for_people(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/reader")
    assert response.status_code == 200
    assert "논문에 연결된 PDF" in response.text
    assert "function tagCards" in response.text
    assert "function collectionCards" in response.text
