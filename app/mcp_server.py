from __future__ import annotations

import json
import logging
import secrets
import time
from collections import defaultdict, deque
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from .config import Settings
from .reader_ui import register_reader_ui
from .tools import HANDLERS, TOOL_DEFINITIONS
from .zotero import ZoteroClient, ZoteroError

LOGGER = logging.getLogger("zotero-read-only-mcp-bridge")
PROTOCOL_VERSION = "2025-03-26"


class RateLimiter:
    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.events: dict[str, deque[float]] = defaultdict(deque)

    def allowed(self, key: str) -> bool:
        now = time.monotonic()
        bucket = self.events[key]
        while bucket and now - bucket[0] > 60:
            bucket.popleft()
        if len(bucket) >= self.limit:
            return False
        bucket.append(now)
        return True


def create_app(settings: Settings | None = None, zotero: ZoteroClient | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    client = zotero or ZoteroClient(settings.zotero_base_url, settings.max_results)
    limiter = RateLimiter(settings.rate_limit_per_minute)
    app = FastAPI(title="Zotero Read-Only MCP Bridge", docs_url=None, redoc_url=None)
    app.state.zotero = client
    register_reader_ui(app, client)

    @app.middleware("http")
    async def security_middleware(request: Request, call_next):
        if request.method == "POST" and request.url.path == "/mcp":
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > settings.max_request_bytes:
                return JSONResponse({"error": "요청이 너무 큽니다"}, status_code=413)
            if request.headers.get("content-type", "").split(";", 1)[0].lower() != "application/json":
                return JSONResponse({"error": "Content-Type: application/json이 필요합니다"}, status_code=415)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.options("/mcp")
    async def mcp_options() -> Response:
        return Response(status_code=204, headers={"Allow": "POST, OPTIONS"})

    @app.post("/mcp")
    async def mcp(request: Request):
        auth = request.headers.get("authorization", "")
        if not auth.startswith("Bearer ") or not settings.token_matches(auth[7:].strip()):
            return JSONResponse({"error": "인증이 필요합니다"}, status_code=401, headers={"WWW-Authenticate": "Bearer"})
        client_key = request.client.host if request.client else "unknown"
        if not limiter.allowed(client_key):
            return JSONResponse({"error": "요청이 너무 많습니다"}, status_code=429)
        try:
            payload = await request.json()
        except ValueError:
            return JSONResponse(_rpc_error(None, -32700, "잘못된 JSON입니다"), status_code=400)
        response = await _handle_rpc(payload, client)
        if response is None:
            return Response(status_code=202)
        headers = {"MCP-Protocol-Version": PROTOCOL_VERSION}
        if payload.get("method") == "initialize":
            headers["Mcp-Session-Id"] = secrets.token_urlsafe(24)
        return JSONResponse(response, headers=headers)

    @app.on_event("shutdown")
    async def close_client() -> None:
        if zotero is None:
            await client.close()

    return app


async def _handle_rpc(payload: Any, client: ZoteroClient) -> dict[str, Any] | None:
    if not isinstance(payload, dict) or payload.get("jsonrpc") != "2.0":
        return _rpc_error(None, -32600, "유효한 JSON-RPC 2.0 요청이 아닙니다")
    request_id = payload.get("id")
    method = payload.get("method")
    if method in {"notifications/initialized", "notifications/cancelled"}:
        return None
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"protocolVersion": PROTOCOL_VERSION, "capabilities": {"tools": {"listChanged": False}}, "serverInfo": {"name": "zotero-read-only-mcp-bridge", "version": "1.0.0"}}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOL_DEFINITIONS}}
    if method == "tools/call":
        params = payload.get("params") or {}
        name = params.get("name")
        handler = HANDLERS.get(name)
        if handler is None:
            return _rpc_error(request_id, -32602, "허용되지 않은 읽기 전용 도구입니다")
        try:
            data = await handler(client, params.get("arguments") or {})
        except (ValueError, ZoteroError) as exc:
            return {"jsonrpc": "2.0", "id": request_id, "result": {"isError": True, "content": [{"type": "text", "text": str(exc)}]}}
        except Exception:
            LOGGER.exception("read-only tool failed: %s", name)
            return {"jsonrpc": "2.0", "id": request_id, "result": {"isError": True, "content": [{"type": "text", "text": "읽기 요청을 처리하지 못했습니다"}]}}
        text = json.dumps(data, ensure_ascii=False)
        return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": text}], "structuredContent": data}}
    return _rpc_error(request_id, -32601, "지원하지 않는 MCP 메서드입니다")


def _rpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
