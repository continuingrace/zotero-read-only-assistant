# 고급·레거시 HTTPS 서버 설치 안내

일반 참가자는 이 문서를 사용할 필요가 없습니다. Windows ChatGPT 데스크톱 앱에서는 [참가자용 설치 파일](participant-installation.md)을 사용하면 터널과 토큰 없이 로컬 MCP로 연결됩니다.

이 문서는 조직 정책상 데스크톱 플러그인을 사용할 수 없어 별도의 HTTPS MCP 서버를 직접 운영해야 하는 개발자·관리자용입니다.

## 1. Zotero 준비

Zotero Desktop을 실행하고 로컬 API를 활성화합니다. 브리지는 `http://127.0.0.1:23119/api/`로만 접근하며 `ZOTERO_BASE_URL`이 루프백 주소가 아니면 시작을 거부합니다.

## 2. 브리지 설치

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(32))"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8787
```

출력된 값을 `.env`의 `BRIDGE_AUTH_TOKEN`에 설정합니다. 토큰을 채팅, Git, 화면 공유, URL 쿼리 문자열에 노출하지 않습니다.

## 3. HTTPS 터널

브리지는 외부 인터페이스에 직접 바인딩하지 않습니다. 운영용 Cloudflare named tunnel, Tailscale Serve 또는 동등한 인증 프록시로 `http://127.0.0.1:8787`을 보호합니다. Quick Tunnel과 무인증 포트 공개는 운영에 사용하지 않습니다.

Cloudflare Tunnel 개념 예시:

```yaml
tunnel: <named-tunnel-id>
credentials-file: C:\Users\<user>\.cloudflared\<named-tunnel-id>.json
ingress:
  - hostname: zotero-bridge.example.com
    service: http://127.0.0.1:8787
  - service: http_status:404
```

외부 인증 프록시와 내부 `BRIDGE_AUTH_TOKEN` 검증을 함께 유지합니다. 참가자별로 별도 터널과 토큰이 필요하므로 일반 강의 배포에는 권장하지 않습니다.

## 4. MCP 등록

클라이언트에 `https://<보호된-호스트>/mcp`를 등록합니다. 고정 Bearer 헤더가 지원되면 참가자별 토큰을 사용하고, OAuth만 지원되면 OAuth 2.1/OIDC 프록시가 인증 후 내부 Bearer 토큰을 주입하도록 구성합니다.

현재 서버에는 읽기 도구 8개와 승인형 쓰기 도구 2개가 있습니다. 외부 서버로 쓰기 기능까지 공개하려면 추가 접근제어, 감사로그, CSRF·재전송 방지 정책을 별도로 설계하세요. 강의 참가자에게는 로컬 데스크톱 플러그인을 권장합니다.

## 5. 보안 원칙

- Zotero의 `127.0.0.1:23119`을 직접 외부에 노출하지 않습니다.
- `BRIDGE_BIND_HOST`와 `ZOTERO_BASE_URL`을 루프백이 아닌 주소로 바꾸지 않습니다.
- 토큰은 사용자별로 다르게 만들고 유출 시 즉시 교체합니다.
- HTTPS 인증서 검증을 끄지 않습니다.
- 검색어와 PDF 전문이 터널·프록시 로그에 남지 않도록 로그 정책을 확인합니다.
- 태그·컬렉션 쓰기에는 사용자 확인과 별도의 권한 정책을 적용합니다.

공식 참고:

- [Zotero Local API](https://www.zotero.org/support/dev/web_api/v3/local_api)
- [Zotero Web API](https://www.zotero.org/support/dev/web_api/v3/basics)
- [Zotero Full-Text Content](https://www.zotero.org/support/dev/web_api/v3/fulltext_content)
