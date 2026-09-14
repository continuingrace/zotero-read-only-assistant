# 참가자 설치·운영 안내

## 1. Zotero 준비

Zotero Desktop을 실행하고 로컬 API를 활성화합니다. 브리지는 `http://127.0.0.1:23119/api/`로만 접근하며, `ZOTERO_BASE_URL`은 루프백 주소가 아니면 시작 단계에서 거부됩니다.

## 2. 브리지 설치

```powershell
cd C:\path\to\zotero-read-only-mcp-bridge
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(32))"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8787
```

출력된 값을 `BRIDGE_AUTH_TOKEN`에 설정한 뒤 실행합니다. 실제 운영에서는 토큰을 PowerShell 명령 기록, 채팅, Git, 화면 공유에 노출하지 마세요. `.env`를 사용하는 경우 파일 권한을 참가자 계정으로 제한합니다.

## 3. HTTPS 터널

브리지는 외부 인터페이스에 직접 바인딩하지 않습니다. 다음 중 하나를 사용합니다.

### Cloudflare Tunnel 예시

운영용 named tunnel과 Cloudflare Access 정책을 사용하고, 공개 호스트의 원본은 `http://127.0.0.1:8787`로 설정합니다.

```yaml
# cloudflared config.yml의 개념 예시
tunnel: <named-tunnel-id>
credentials-file: C:\Users\<user>\.cloudflared\<named-tunnel-id>.json
ingress:
  - hostname: zotero-bridge.example.com
    service: http://127.0.0.1:8787
  - service: http_status:404
```

Cloudflare Access/OIDC를 사용하는 경우 `/mcp` 요청이 원본 브리지에 도달할 때 브리지 토큰이 `Authorization` 헤더로 전달되거나 안전한 고정 헤더로 주입되도록 확인합니다. Access만 켜고 브리지 인증을 제거하지 마세요.

### Tailscale Serve 예시

```powershell
tailscale serve --https=443 http://127.0.0.1:8787
```

Tailscale ACL로 참가자 계정만 접근하게 하고, MCP 클라이언트가 브리지의 Bearer 토큰을 전송하도록 구성합니다.

Quick Tunnel은 개발 확인용으로만 사용합니다. 장기 운영에서는 고정 호스트, 접근 정책, 로그 보존 정책이 있는 named tunnel을 사용하세요.

## 4. ChatGPT 사용자 지정 MCP 앱 연결

ChatGPT에서 Developer mode와 사용자 지정 앱 생성 권한을 활성화한 뒤, 터널의 HTTPS URL 뒤에 `/mcp`를 붙여 등록합니다. ChatGPT의 관리자 정책에 따라 사용자가 직접 추가하지 못하고 워크스페이스 관리자의 승인이나 배포가 필요할 수 있습니다.

현재 앱 UI가 Bearer 토큰을 직접 받는 경우 참가자별 토큰을 입력합니다. OAuth 연결만 지원하는 경우 OAuth 2.1/OIDC reverse proxy를 앞에 두고, 로그인한 참가자의 요청만 로컬 브리지로 전달합니다. OAuth 프록시가 브리지 인증 토큰을 서버 측에서 주입하도록 하며, 토큰을 브라우저 쿼리스트링에 넣지 않습니다.

등록 뒤 `tools/list`에 7개 도구만 보이는지 확인합니다. `readOnlyHint: true`가 보이지 않으면 등록된 MCP 서버가 오래된 도구 스냅샷을 사용 중일 수 있으므로 앱을 새로고침하거나 재등록합니다.

## 5. 보안 운영 원칙

- `127.0.0.1:23119`을 포트 포워딩, 공유기 포트 개방, 공용 프록시로 직접 노출하지 않습니다.
- 브리지의 `BRIDGE_BIND_HOST`와 `ZOTERO_BASE_URL`을 루프백이 아닌 주소로 바꾸지 않습니다.
- 토큰은 참가자별로 다르게 만들고, 유출 시 즉시 교체한 뒤 터널/앱 연결도 갱신합니다.
- MCP 요청 크기, 요청 빈도, 결과 수는 서버에서 제한됩니다.
- PDF 파일 경로나 원문 파일은 반환하지 않고 Zotero가 색인한 전문 검색 결과의 메타데이터만 반환합니다.
- HTTPS 인증서 검증을 끄지 않습니다. 터널 공급자의 Access 로그와 브리지 로그에 검색어·PDF 전문·토큰이 남지 않도록 합니다.
- 로컬 API가 꺼져 있으면 서버는 `Zotero 로컬 API가 비활성화되어 있습니다`라고 반환하며 우회하지 않습니다.

## 6. 문제 확인

```powershell
Invoke-WebRequest http://127.0.0.1:8787/healthz
```

`healthz`가 정상이어도 Zotero API 권한이 정상이라는 뜻은 아닙니다. ChatGPT에서 읽기 전용 검색 도구를 호출해 확인합니다. Zotero가 403을 반환하면 로컬 API 설정을 확인하세요.

공식 참고:

- [Zotero Local API](https://www.zotero.org/support/dev/web_api/v3/local_api)
- [Zotero Web API 검색 파라미터](https://www.zotero.org/support/dev/web_api/v3/basics)
- [Zotero Full-Text Content](https://www.zotero.org/support/dev/web_api/v3/fulltext_content)
- [OpenAI ChatGPT MCP 앱 안내](https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt)
