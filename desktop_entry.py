from __future__ import annotations

import ctypes
import secrets
import threading
import time
import webbrowser
from urllib.error import URLError
from urllib.request import urlopen

import uvicorn
from fastapi import Request
from fastapi.responses import JSONResponse

from app.config import Settings
from app.mcp_server import create_app

HOST = "127.0.0.1"
PORT = 8787
READER_URL = f"http://{HOST}:{PORT}/reader?desktop=1"
HEALTH_URL = f"http://{HOST}:{PORT}/healthz"


def show_error(message: str) -> None:
    ctypes.windll.user32.MessageBoxW(0, message, "Zotero 읽기 도우미", 0x10)


def is_healthy() -> bool:
    try:
        with urlopen(HEALTH_URL, timeout=0.5) as response:
            return response.status == 200
    except (URLError, TimeoutError, OSError):
        return False


def open_when_ready(server: uvicorn.Server) -> None:
    for _ in range(50):
        if is_healthy():
            webbrowser.open(READER_URL)
            return
        if server.should_exit:
            return
        time.sleep(0.1)
    server.should_exit = True
    show_error("검색 화면을 시작하지 못했습니다. 프로그램을 다시 실행해 주세요.")


def main() -> None:
    if is_healthy():
        webbrowser.open(READER_URL)
        return

    settings = Settings(auth_token=secrets.token_urlsafe(32))
    app = create_app(settings)
    server: uvicorn.Server

    @app.post("/reader/api/desktop/quit")
    async def desktop_quit(request: Request) -> JSONResponse:
        client_host = request.client.host if request.client else ""
        if client_host not in {"127.0.0.1", "::1", "localhost"}:
            return JSONResponse({"error": "로컬 요청만 허용됩니다"}, status_code=403)
        server.should_exit = True
        return JSONResponse({"status": "closing"})

    config = uvicorn.Config(
        app,
        host=HOST,
        port=PORT,
        log_config=None,
        access_log=False,
    )
    server = uvicorn.Server(config)
    opener = threading.Thread(target=open_when_ready, args=(server,), daemon=True)
    opener.start()
    try:
        server.run()
    except OSError:
        show_error("검색 화면을 시작하지 못했습니다. 이미 실행 중인지 확인해 주세요.")


if __name__ == "__main__":
    main()
