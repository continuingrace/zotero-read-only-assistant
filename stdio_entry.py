from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

from app.mcp_server import _handle_rpc
from app.zotero import ZoteroClient


async def serve() -> None:
    client = ZoteroClient("http://127.0.0.1:23119/api/")
    try:
        while True:
            raw = await asyncio.to_thread(sys.stdin.buffer.readline)
            if not raw:
                return
            payload: Any = None
            try:
                payload = json.loads(raw.decode("utf-8"))
                response = await _handle_rpc(payload, client)
            except Exception:
                request_id = payload.get("id") if isinstance(payload, dict) else None
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32700, "message": "MCP 요청을 해석하지 못했습니다"},
                }
            if response is not None:
                line = json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n"
                sys.stdout.buffer.write(line.encode("utf-8"))
                sys.stdout.buffer.flush()
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(serve())
