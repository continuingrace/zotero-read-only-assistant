from __future__ import annotations

from typing import Any

import httpx

UNKNOWN = "확인되지 않음"


class ZoteroError(RuntimeError):
    """A safe, user-facing error from the local Zotero API."""


def known(value: Any) -> Any:
    return UNKNOWN if value is None or value == "" or value == [] else value


def classify_item(data: dict[str, Any]) -> str:
    item_type = data.get("itemType")
    if item_type == "attachment":
        return "child_attachment" if data.get("parentItem") else "standalone_pdf" if is_pdf(data) else "standalone_attachment"
    if item_type == "note":
        return "note"
    return "bibliographic_record"


def is_pdf(data: dict[str, Any]) -> bool:
    content_type = str(data.get("contentType") or "").lower()
    filename = str(data.get("filename") or "").lower()
    path = str(data.get("path") or "").lower()
    return content_type == "application/pdf" or filename.endswith(".pdf") or path.endswith(".pdf")


def compact_item(item: dict[str, Any]) -> dict[str, Any]:
    data = item.get("data") or {}
    return {
        "key": known(item.get("key") or data.get("key")),
        "item_type": known(data.get("itemType")),
        "classification": classify_item(data),
        "title": known(data.get("title")),
        "creators": data.get("creators") or UNKNOWN,
        "date": known(data.get("date")),
        "date_added": known(data.get("dateAdded")),
        "date_modified": known(data.get("dateModified")),
        "parent_item_key": known(data.get("parentItem")),
        "filename": known(data.get("filename")),
        "content_type": known(data.get("contentType")),
        "library": item.get("library") or UNKNOWN,
        "tags": [tag.get("tag", UNKNOWN) for tag in (data.get("tags") or [])],
    }


class ZoteroClient:
    def __init__(self, base_url: str, max_results: int = 100, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.base_url = base_url
        self.max_results = max_results
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(10.0, connect=2.0),
            follow_redirects=False,
            transport=transport,
            headers={
                "Accept": "application/json",
                "Zotero-API-Version": "3",
                "Zotero-Allowed-Request": "true",
                "User-Agent": "zotero-read-only-mcp-bridge/1.0",
            },
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        if not path.startswith("/") or any(part in path for part in ("..", "\\")):
            raise ZoteroError("잘못된 Zotero 경로입니다")
        try:
            response = await self._client.get(path.lstrip("/"), params=params)
        except httpx.HTTPError as exc:
            raise ZoteroError("Zotero Desktop에 연결할 수 없습니다") from exc
        if response.status_code == 403:
            raise ZoteroError("Zotero 로컬 API가 비활성화되어 있습니다")
        if response.status_code == 404:
            raise ZoteroError("요청한 Zotero 자료를 찾을 수 없습니다")
        if response.status_code >= 400:
            raise ZoteroError("Zotero 로컬 API가 요청을 처리하지 못했습니다")
        try:
            return response.json()
        except ValueError as exc:
            raise ZoteroError("Zotero 응답을 해석할 수 없습니다") from exc

    async def items(self, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        request_params = dict(params or {})
        request_params["limit"] = min(int(request_params.get("limit", self.max_results)), self.max_results)
        result = await self.get("/users/0/items", request_params)
        return result if isinstance(result, list) else []

    async def item(self, key: str) -> dict[str, Any]:
        result = await self.get(f"/users/0/items/{key}")
        return result if isinstance(result, dict) else {}

    async def children(self, key: str) -> list[dict[str, Any]]:
        result = await self.get(f"/users/0/items/{key}/children", {"limit": self.max_results})
        return result if isinstance(result, list) else []
