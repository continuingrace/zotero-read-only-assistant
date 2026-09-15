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
        "abstract": known(data.get("abstractNote")),
        "doi": known(data.get("DOI")),
        "publication": known(
            data.get("publicationTitle")
            or data.get("bookTitle")
            or data.get("proceedingsTitle")
            or data.get("university")
        ),
        "language": known(data.get("language")),
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
                "User-Agent": "zotero-chatgpt-mcp/0.2.1",
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

    async def fulltext(self, key: str) -> dict[str, Any] | None:
        response = await self._client.get(f"users/0/items/{key}/fulltext")
        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            raise ZoteroError("PDF 전문을 가져오지 못했습니다")
        try:
            result = response.json()
        except ValueError as exc:
            raise ZoteroError("PDF 전문 응답을 해석할 수 없습니다") from exc
        return result if isinstance(result, dict) else None

    async def authorize_write(self) -> tuple[str, str]:
        """Request a short-lived local write key through Zotero's own dialog."""
        try:
            probe = await self._client.get("")
        except httpx.HTTPError as exc:
            raise ZoteroError("Zotero Desktop에 연결할 수 없습니다") from exc
        server_id = probe.headers.get("Zotero-Server-ID", "")
        if not server_id:
            raise ZoteroError("Zotero 10 이상의 로컬 쓰기 승인이 필요합니다")
        response = await self._client.post(
            "local/authorize",
            json={"appName": "ChatGPT Zotero Assistant"},
            headers={"Zotero-Server-ID": server_id},
        )
        if response.status_code == 403:
            raise ZoteroError("Zotero에서 변경 승인이 거부되었습니다")
        if response.status_code == 429:
            raise ZoteroError("승인 요청이 너무 많습니다. 잠시 후 다시 시도해 주세요")
        if response.status_code >= 400:
            raise ZoteroError("Zotero 변경 승인을 받지 못했습니다")
        try:
            key = str(response.json().get("key") or "")
        except ValueError as exc:
            raise ZoteroError("Zotero 변경 승인 응답을 해석할 수 없습니다") from exc
        if not key:
            raise ZoteroError("Zotero 변경 승인 키가 발급되지 않았습니다")
        return key, server_id

    async def patch_item(self, key: str, changes: dict[str, Any]) -> dict[str, Any]:
        current = await self.item(key)
        data = current.get("data") or {}
        version = data.get("version") or current.get("version")
        if not isinstance(version, int):
            raise ZoteroError("자료 버전을 확인할 수 없어 변경하지 않았습니다")
        write_key, server_id = await self.authorize_write()
        response = await self._client.patch(
            f"users/0/items/{key}",
            json=changes,
            headers={
                "Zotero-API-Key": write_key,
                "Zotero-Server-ID": server_id,
                "If-Unmodified-Since-Version": str(version),
            },
        )
        if response.status_code in {401, 403}:
            raise ZoteroError("Zotero 변경 승인이 만료되었거나 거부되었습니다")
        if response.status_code in {409, 412, 428}:
            raise ZoteroError("자료가 다른 곳에서 변경되어 안전하게 중단했습니다. 다시 시도해 주세요")
        if response.status_code >= 400:
            raise ZoteroError("Zotero 자료를 변경하지 못했습니다")
        return await self.item(key)
