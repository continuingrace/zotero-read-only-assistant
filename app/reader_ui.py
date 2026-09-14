from __future__ import annotations

from typing import Any, Awaitable, Callable

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse

from .tools import HANDLERS
from .zotero import ZoteroClient, ZoteroError

ReaderHandler = Callable[[ZoteroClient, dict[str, Any]], Awaitable[dict[str, Any]]]


def register_reader_ui(app: FastAPI, client: ZoteroClient) -> None:
    """Register a loopback-only, read-only browser interface for participants."""

    async def call(name: str, arguments: dict[str, Any]) -> JSONResponse:
        handler: ReaderHandler | None = HANDLERS.get(name)  # type: ignore[assignment]
        if handler is None:
            return JSONResponse({"error": "읽기 전용 기능을 찾을 수 없습니다"}, status_code=404)
        try:
            return JSONResponse(await handler(client, arguments))
        except (ValueError, ZoteroError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        except Exception:
            return JSONResponse({"error": "Zotero 읽기 요청을 처리하지 못했습니다"}, status_code=500)

    @app.get("/reader", response_class=HTMLResponse)
    async def reader_home() -> str:
        return READER_HTML

    @app.get("/reader/api/search")
    async def reader_search(query: str = Query(min_length=1, max_length=200), limit: int = Query(default=20, ge=1, le=100)) -> JSONResponse:
        return await call("zotero_read_only_search_library", {"query": query, "limit": limit, "qmode": "titleCreatorYear"})

    @app.get("/reader/api/recent")
    async def reader_recent(limit: int = Query(default=20, ge=1, le=100)) -> JSONResponse:
        return await call("zotero_read_only_get_recent_items", {"limit": limit})

    @app.get("/reader/api/item/{item_key}")
    async def reader_item(item_key: str) -> JSONResponse:
        return await call("zotero_read_only_get_item_metadata", {"item_key": item_key})

    @app.get("/reader/api/tags")
    async def reader_tags(query: str = "", limit: int = Query(default=100, ge=1, le=100)) -> JSONResponse:
        return await call("zotero_read_only_list_tags", {"query": query, "limit": limit})

    @app.get("/reader/api/collections")
    async def reader_collections(limit: int = Query(default=100, ge=1, le=100)) -> JSONResponse:
        return await call("zotero_read_only_list_collections", {"limit": limit})

    @app.get("/reader/api/pdfs")
    async def reader_pdfs(parent_item_key: str | None = None, limit: int = Query(default=100, ge=1, le=100)) -> JSONResponse:
        arguments: dict[str, Any] = {"limit": limit}
        if parent_item_key:
            arguments["parent_item_key"] = parent_item_key
        return await call("zotero_read_only_list_pdf_attachments", arguments)

    @app.get("/reader/api/pdf-search")
    async def reader_pdf_search(query: str = Query(min_length=1, max_length=200), limit: int = Query(default=20, ge=1, le=100)) -> JSONResponse:
        return await call("zotero_read_only_search_pdf_full_text", {"query": query, "limit": limit})


READER_HTML = r'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Zotero 읽기 도우미</title>
<style>
:root{font-family:"Malgun Gothic",system-ui,sans-serif}body{margin:0;background:#f5f7fb;color:#20252b}main{max-width:980px;margin:auto;padding:32px 20px 64px}.card{background:#fff;border:1px solid #dfe4ec;border-radius:14px;padding:22px;box-shadow:0 5px 18px #1c27320d}h1{margin:0 0 8px;font-size:28px}p{color:#596575}.notice{background:#eef6ff;border-left:4px solid #3878d8;padding:12px 14px;border-radius:7px}form{display:flex;gap:8px;margin-top:18px}input{flex:1;min-width:0;border:1px solid #b9c2cf;border-radius:8px;padding:12px;font-size:16px}button{border:0;border-radius:8px;padding:11px 16px;background:#2769c5;color:white;cursor:pointer;font-size:15px}.secondary{background:#64748b}.quick{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}#status{margin-top:15px;color:#596575;min-height:22px}#results{margin-top:18px;display:grid;gap:10px}.item{border:1px solid #e0e5ed;border-radius:10px;padding:14px;background:#fff}.item h3{margin:0 0 8px;font-size:17px}.meta{color:#596575;font-size:14px;line-height:1.55}.badge{display:inline-block;background:#edf1f7;border-radius:99px;padding:3px 8px;font-size:12px;margin-right:5px}pre{white-space:pre-wrap;word-break:break-word;background:#f7f8fa;padding:12px;border-radius:8px;overflow:auto}footer{color:#768294;font-size:13px;margin-top:20px}
</style></head><body><main><section class="card"><h1>Zotero 읽기 도우미</h1><p>내 컴퓨터의 Zotero 자료를 검색합니다. 자료를 추가·수정·삭제하지 않습니다.</p><div class="notice">Zotero Desktop을 먼저 열고, 로컬 API 허용 설정을 켜 주세요.</div>
<form id="searchForm"><input id="query" placeholder="예: 행복한 내향인의 특징" autocomplete="off"><button type="submit">검색</button></form>
<div class="quick"><button class="secondary" id="recent" type="button">최근 자료</button><button class="secondary" id="tags" type="button">태그 보기</button><button class="secondary" id="collections" type="button">컬렉션 보기</button><button class="secondary" id="pdfs" type="button">PDF 보기</button></div><div id="status"></div><div id="results"></div><footer>읽기 전용 · Zotero 로컬 API는 이 컴퓨터 안에서만 사용됩니다.</footer></section></main>
<script>
const $=id=>document.getElementById(id), status=t=>$("status").textContent=t;
const esc=v=>String(v??"확인되지 않음").replace(/[&<>'"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;","\"":"&quot;"}[c]));
function card(i){const title=i.title||i.filename||"제목 확인되지 않음";const tags=Array.isArray(i.tags)?i.tags.map(t=>`<span class="badge">${esc(t)}</span>`).join(""):"";return `<article class="item"><h3>${esc(title)}</h3><div class="meta"><b>구분:</b> ${esc(i.classification)} · <b>자료 유형:</b> ${esc(i.item_type)} · <b>키:</b> ${esc(i.key)}<br><b>저자:</b> ${esc(JSON.stringify(i.creators))} · <b>연도:</b> ${esc(i.date)}<br>${tags}</div></article>`}
function show(d){const a=d.items||d.attachments||d.tags||d.collections||[];$("results").innerHTML=Array.isArray(a)&&a.length&&a[0].classification?a.map(card).join(""):`<pre>${esc(JSON.stringify(d,null,2))}</pre>`;status(`결과 ${Array.isArray(a)?a.length:0}개`)}
async function load(url,label){status(`${label} 확인 중...`);$("results").innerHTML="";try{const r=await fetch(url),d=await r.json();if(!r.ok)throw Error(d.error||"요청 실패");show(d)}catch(e){status("확인 필요");$("results").innerHTML=`<div class="item">${esc(e.message)}</div>`}}
$("searchForm").onsubmit=e=>{e.preventDefault();const q=$("query").value.trim();if(q)load(`/reader/api/search?query=${encodeURIComponent(q)}`,"자료")};$("recent").onclick=()=>load("/reader/api/recent","최근 자료");$("tags").onclick=()=>load("/reader/api/tags","태그");$("collections").onclick=()=>load("/reader/api/collections","컬렉션");$("pdfs").onclick=()=>load("/reader/api/pdfs","PDF");
</script></body></html>'''
