from __future__ import annotations

import re
from typing import Any

from .zotero import UNKNOWN, ZoteroClient, ZoteroError, compact_item, is_pdf, known

KEY_RE = re.compile(r"^[A-Z0-9]{8}$")


def _key(value: Any) -> str:
    if not isinstance(value, str) or not KEY_RE.fullmatch(value):
        raise ValueError("Zotero item key 형식이 올바르지 않습니다")
    return value


def _limit(value: Any, maximum: int) -> int:
    if value is None:
        return min(20, maximum)
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= maximum:
        raise ValueError(f"limit은 1에서 {maximum} 사이의 정수여야 합니다")
    return value


def _query(value: Any, required: bool = False) -> str:
    if value is None:
        if required:
            raise ValueError("query가 필요합니다")
        return ""
    if not isinstance(value, str) or len(value) > 200:
        raise ValueError("query는 200자 이하의 문자열이어야 합니다")
    result = value.strip()
    if required and not result:
        raise ValueError("query가 필요합니다")
    return result


def _short_text(value: Any, field: str, maximum: int = 200) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise ValueError(f"{field}은 1자에서 {maximum}자 사이여야 합니다")
    return value.strip()


async def search_library(client: ZoteroClient, args: dict[str, Any]) -> dict[str, Any]:
    query = _query(args.get("query"), required=True)
    limit = _limit(args.get("limit"), client.max_results)
    qmode = args.get("qmode", "titleCreatorYear")
    if qmode not in {"titleCreatorYear", "everything"}:
        raise ValueError("qmode은 허용된 검색 모드여야 합니다")
    params: dict[str, Any] = {"q": query, "qmode": qmode, "limit": limit}
    item_type = args.get("item_type")
    if item_type is not None:
        if not isinstance(item_type, str) or len(item_type) > 80:
            raise ValueError("item_type 형식이 올바르지 않습니다")
        params["itemType"] = item_type
    items = await client.items(params)
    return {"query": query, "count": len(items), "items": [compact_item(item) for item in items]}


async def recent_items(client: ZoteroClient, args: dict[str, Any]) -> dict[str, Any]:
    limit = _limit(args.get("limit"), client.max_results)
    items = await client.items({"sort": "dateAdded", "direction": "desc", "limit": limit})
    return {"count": len(items), "items": [compact_item(item) for item in items]}


async def get_item_metadata(client: ZoteroClient, args: dict[str, Any]) -> dict[str, Any]:
    item = await client.item(_key(args.get("item_key")))
    data = compact_item(item)
    if data["classification"] == "bibliographic_record":
        children = await client.children(str(data["key"]))
        data["child_attachments"] = [compact_item(child) for child in children if is_pdf(child.get("data") or {})]
    else:
        data["child_attachments"] = []
    return data


async def list_tags(client: ZoteroClient, args: dict[str, Any]) -> dict[str, Any]:
    query = _query(args.get("query"))
    limit = _limit(args.get("limit"), client.max_results)
    params: dict[str, Any] = {"limit": limit}
    if query:
        params.update({"q": query, "qmode": "contains"})
    tags = await client.get("/users/0/tags", params)
    values = [{"tag": known(tag.get("tag")), "type": tag.get("type", 0)} for tag in (tags if isinstance(tags, list) else [])]
    return {"query": query or UNKNOWN, "count": len(values), "tags": values}


async def list_collections(client: ZoteroClient, args: dict[str, Any]) -> dict[str, Any]:
    limit = _limit(args.get("limit"), client.max_results)
    collections = await client.get("/users/0/collections", {"limit": limit})
    values = []
    for collection in collections if isinstance(collections, list) else []:
        data = collection.get("data") or {}
        values.append(
            {
                "key": known(collection.get("key") or data.get("key")),
                "name": known(data.get("name")),
                "parent_collection_key": known(data.get("parentCollection")),
                "library": collection.get("library") or UNKNOWN,
            }
        )
    return {"count": len(values), "collections": values}


async def list_pdf_attachments(client: ZoteroClient, args: dict[str, Any]) -> dict[str, Any]:
    limit = _limit(args.get("limit"), client.max_results)
    parent_key = args.get("parent_item_key")
    if parent_key is not None:
        parent_key = _key(parent_key)
        attachments = await client.children(parent_key)
    else:
        attachments = await client.items({"itemType": "attachment", "limit": limit})
    pdfs = [compact_item(item) for item in attachments if is_pdf(item.get("data") or {})]
    return {"parent_item_key": parent_key or UNKNOWN, "count": len(pdfs), "attachments": pdfs[:limit]}


async def search_pdf_full_text(client: ZoteroClient, args: dict[str, Any]) -> dict[str, Any]:
    query = _query(args.get("query"), required=True)
    limit = _limit(args.get("limit"), client.max_results)
    items = await client.items({"q": query, "qmode": "everything", "itemType": "attachment", "limit": limit})
    pdfs = [compact_item(item) for item in items if is_pdf(item.get("data") or {})]
    return {
        "query": query,
        "count": len(pdfs),
        "search_scope": "Zotero가 색인한 첨부파일 전문 및 메타데이터",
        "attachments": pdfs,
        "note": UNKNOWN if not pdfs else "검색어가 포함된 PDF 첨부파일입니다",
    }


async def get_pdf_text(client: ZoteroClient, args: dict[str, Any]) -> dict[str, Any]:
    requested_key = _key(args.get("item_key"))
    start = args.get("start", 0)
    max_chars = args.get("max_chars", 30000)
    if not isinstance(start, int) or isinstance(start, bool) or start < 0:
        raise ValueError("start는 0 이상의 정수여야 합니다")
    if not isinstance(max_chars, int) or isinstance(max_chars, bool) or not 1000 <= max_chars <= 50000:
        raise ValueError("max_chars는 1000에서 50000 사이의 정수여야 합니다")

    item = await client.item(requested_key)
    data = item.get("data") or {}
    attachment_key = requested_key
    if data.get("itemType") != "attachment":
        children = await client.children(requested_key)
        pdfs = [child for child in children if is_pdf(child.get("data") or {})]
        if not pdfs:
            return {"requested_item_key": requested_key, "attachment_key": UNKNOWN, "content": UNKNOWN, "reason": "PDF 첨부파일이 없습니다"}
        attachment_key = str(pdfs[0].get("key") or (pdfs[0].get("data") or {}).get("key"))

    fulltext = await client.fulltext(attachment_key)
    if not fulltext or not isinstance(fulltext.get("content"), str) or not fulltext["content"]:
        return {"requested_item_key": requested_key, "attachment_key": attachment_key, "content": UNKNOWN, "reason": "Zotero에서 검색 가능한 PDF 전문이 확인되지 않음"}
    content = fulltext["content"]
    end = min(len(content), start + max_chars)
    return {
        "requested_item_key": requested_key,
        "attachment_key": attachment_key,
        "content": content[start:end],
        "start": start,
        "end": end,
        "total_characters": len(content),
        "has_more": end < len(content),
        "indexed_pages": known(fulltext.get("indexedPages")),
        "total_pages": known(fulltext.get("totalPages")),
    }


async def write_tag_with_confirmation(client: ZoteroClient, args: dict[str, Any]) -> dict[str, Any]:
    item_key = _key(args.get("item_key"))
    action = args.get("action")
    if action not in {"add", "remove"}:
        raise ValueError("action은 add 또는 remove여야 합니다")
    tag = _short_text(args.get("tag"), "tag")
    item = await client.item(item_key)
    data = item.get("data") or {}
    before = [str(entry.get("tag")) for entry in (data.get("tags") or []) if entry.get("tag")]
    if action == "add":
        after = before if tag in before else [*before, tag]
    else:
        after = [value for value in before if value != tag]
    if after == before:
        return {"changed": False, "item_key": item_key, "action": action, "tag": tag, "before": before, "after": after}
    updated = await client.patch_item(item_key, {"tags": [{"tag": value} for value in after]})
    updated_data = updated.get("data") or {}
    confirmed_after = [str(entry.get("tag")) for entry in (updated_data.get("tags") or []) if entry.get("tag")]
    return {"changed": True, "item_key": item_key, "action": action, "tag": tag, "before": before, "after": confirmed_after}


async def add_to_collection_with_confirmation(client: ZoteroClient, args: dict[str, Any]) -> dict[str, Any]:
    item_key = _key(args.get("item_key"))
    collection_key = _key(args.get("collection_key"))
    await client.get(f"/users/0/collections/{collection_key}")
    item = await client.item(item_key)
    data = item.get("data") or {}
    before = [str(value) for value in (data.get("collections") or [])]
    after = before if collection_key in before else [*before, collection_key]
    if after == before:
        return {"changed": False, "item_key": item_key, "collection_key": collection_key, "before": before, "after": after}
    updated = await client.patch_item(item_key, {"collections": after})
    confirmed_after = [str(value) for value in ((updated.get("data") or {}).get("collections") or [])]
    return {"changed": True, "item_key": item_key, "collection_key": collection_key, "before": before, "after": confirmed_after}


TOOL_DEFINITIONS = [
    {
        "name": "zotero_read_only_search_library",
        "description": "읽기 전용: Zotero 라이브러리의 논문 레코드, 독립 PDF, 하위 첨부파일 메타데이터를 검색합니다.",
        "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "item_type": {"type": "string"}, "qmode": {"type": "string", "enum": ["titleCreatorYear", "everything"]}, "limit": {"type": "integer", "minimum": 1, "maximum": 100}}, "required": ["query"], "additionalProperties": False},
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True},
    },
    {
        "name": "zotero_read_only_get_recent_items",
        "description": "읽기 전용: Zotero에서 최근 추가된 자료를 조회합니다.",
        "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 100}}, "additionalProperties": False},
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True},
    },
    {
        "name": "zotero_read_only_get_item_metadata",
        "description": "읽기 전용: Zotero 자료 하나의 메타데이터와 하위 PDF 첨부파일을 조회합니다.",
        "inputSchema": {"type": "object", "properties": {"item_key": {"type": "string", "pattern": "^[A-Z0-9]{8}$"}}, "required": ["item_key"], "additionalProperties": False},
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True},
    },
    {
        "name": "zotero_read_only_list_tags",
        "description": "읽기 전용: Zotero 태그 목록을 조회합니다.",
        "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 100}}, "additionalProperties": False},
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True},
    },
    {
        "name": "zotero_read_only_list_collections",
        "description": "읽기 전용: Zotero 컬렉션과 상위 컬렉션 관계를 조회합니다.",
        "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 100}}, "additionalProperties": False},
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True},
    },
    {
        "name": "zotero_read_only_list_pdf_attachments",
        "description": "읽기 전용: 독립 PDF와 특정 자료의 하위 PDF 첨부파일을 구분해 조회합니다.",
        "inputSchema": {"type": "object", "properties": {"parent_item_key": {"type": "string", "pattern": "^[A-Z0-9]{8}$"}, "limit": {"type": "integer", "minimum": 1, "maximum": 100}}, "additionalProperties": False},
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True},
    },
    {
        "name": "zotero_read_only_search_pdf_full_text",
        "description": "읽기 전용: Zotero가 색인한 PDF 전문에서 검색어를 찾아 PDF 첨부파일을 반환합니다.",
        "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 100}}, "required": ["query"], "additionalProperties": False},
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True},
    },
    {
        "name": "zotero_read_only_get_pdf_text",
        "description": "읽기 전용: 논문 레코드 또는 PDF 첨부파일의 Zotero 색인 전문을 구간별로 읽습니다. 자료를 변경하지 않습니다.",
        "inputSchema": {"type": "object", "properties": {"item_key": {"type": "string", "pattern": "^[A-Z0-9]{8}$"}, "start": {"type": "integer", "minimum": 0}, "max_chars": {"type": "integer", "minimum": 1000, "maximum": 50000}}, "required": ["item_key"], "additionalProperties": False},
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True},
    },
    {
        "name": "zotero_write_tag_with_confirmation",
        "description": "쓰기·승인 필요: Zotero 자료 하나에 태그를 추가하거나 제거합니다. ChatGPT 승인 뒤 Zotero 자체 변경 승인창도 통과해야 합니다.",
        "inputSchema": {"type": "object", "properties": {"item_key": {"type": "string", "pattern": "^[A-Z0-9]{8}$"}, "action": {"type": "string", "enum": ["add", "remove"]}, "tag": {"type": "string", "minLength": 1, "maxLength": 200}}, "required": ["item_key", "action", "tag"], "additionalProperties": False},
        "annotations": {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": True},
    },
    {
        "name": "zotero_write_add_to_collection_with_confirmation",
        "description": "쓰기·승인 필요: Zotero 자료 하나를 기존 컬렉션에 추가합니다. 다른 컬렉션에서는 제거하거나 이동하지 않습니다.",
        "inputSchema": {"type": "object", "properties": {"item_key": {"type": "string", "pattern": "^[A-Z0-9]{8}$"}, "collection_key": {"type": "string", "pattern": "^[A-Z0-9]{8}$"}}, "required": ["item_key", "collection_key"], "additionalProperties": False},
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True},
    },
]

HANDLERS = {
    "zotero_read_only_search_library": search_library,
    "zotero_read_only_get_recent_items": recent_items,
    "zotero_read_only_get_item_metadata": get_item_metadata,
    "zotero_read_only_list_tags": list_tags,
    "zotero_read_only_list_collections": list_collections,
    "zotero_read_only_list_pdf_attachments": list_pdf_attachments,
    "zotero_read_only_search_pdf_full_text": search_pdf_full_text,
    "zotero_read_only_get_pdf_text": get_pdf_text,
    "zotero_write_tag_with_confirmation": write_tag_with_confirmation,
    "zotero_write_add_to_collection_with_confirmation": add_to_collection_with_confirmation,
}
