# Zotero 읽기 전용 MCP 브리지

각 참가자의 Zotero Desktop 라이브러리를 읽기 전용으로 검색하는 도구입니다. 기본 참가자 모드는 인터넷 공개나 ChatGPT 설정 없이 자기 컴퓨터에서 브라우저로 사용합니다. 고급 사용자는 같은 코드의 `/mcp` 엔드포인트를 ChatGPT 또는 다른 MCP 클라이언트에 연결할 수 있습니다.

## 지원 범위

도구는 다음 7개뿐이며 모두 이름과 설명에 `read_only`를 포함합니다.

- `zotero_read_only_search_library`
- `zotero_read_only_get_recent_items`
- `zotero_read_only_get_item_metadata`
- `zotero_read_only_list_tags`
- `zotero_read_only_list_collections`
- `zotero_read_only_list_pdf_attachments`
- `zotero_read_only_search_pdf_full_text`

서버는 Zotero에 읽기 요청만 보내며, 도구 allowlist 밖의 MCP 호출은 거부합니다. 논문/서지 레코드, 독립 PDF, 하위 첨부파일은 `classification`으로 구분합니다. 값이 없으면 정확히 `확인되지 않음`을 반환합니다.

## 참가자에게 권장하는 사용법

1. Zotero Desktop을 설치하고 실행합니다.
2. Zotero에서 로컬 API 허용을 켭니다.
3. `participant\Start-Participant.vbs`를 더블클릭합니다.
4. 열린 창에서 `Setup and Start`를 한 번 누릅니다.
5. 브라우저에 `Zotero 읽기 도우미`가 열리면 검색합니다.

참가자는 터미널, Python, 포트 번호, 인증 토큰, HTTPS 주소를 입력하지 않습니다. 처음 한 번만 관리자가 Python 설치를 도와주면 됩니다. 배포 시에는 Python까지 포함한 Windows 실행 파일을 별도로 제공하면 이 단계도 없앨 수 있습니다.

## 구조

```text
ChatGPT custom MCP app
        │ HTTPS + Bearer token 또는 OAuth를 종료하는 보안 터널
        ▼
참가자 PC의 bridge: 127.0.0.1:8787/mcp
        │ loopback HTTP 읽기 요청만
        ▼
Zotero Desktop Local API: 127.0.0.1:23119/api/
```

참가자마다 브리지와 토큰을 하나씩 사용해야 합니다. 하나의 중앙 서버가 여러 참가자의 로컬 Zotero를 직접 읽는 구조는 지원하지 않습니다.

## 개발자용 빠른 실행

1. Zotero Desktop에서 `설정 → 고급 → 이 컴퓨터의 다른 애플리케이션이 Zotero와 통신하도록 허용`을 켭니다.
2. Python 3.11 이상 환경에서 `python -m venv .venv`와 `pip install -r requirements.txt`를 실행합니다.
3. `.env.example`을 `.env`로 복사하고 32자 이상의 무작위 `BRIDGE_AUTH_TOKEN`을 설정합니다.
4. PowerShell에서 `./run.ps1`을 실행합니다.
5. 외부 공개는 [docs/installation.md](docs/installation.md)의 보안 터널 절차로 구성합니다.

## 일반 참가자용 파일

일반 참가자에게는 저장소 전체가 아니라 프로젝트 폴더를 압축해 전달합니다. 참가자는 `participant\Start-Participant.vbs`를 더블클릭하고 `Setup and Start` 버튼만 누르면 브라우저 검색 화면을 사용할 수 있습니다. 자세한 안내는 [docs/participant-installation.md](docs/participant-installation.md)에 있습니다.

## ChatGPT 등록

ChatGPT의 사용자 지정 MCP 앱은 워크스페이스 정책과 요금제에 따라 Developer mode가 필요할 수 있습니다. 현재 UI에서 `Settings → Apps → Create` 또는 워크스페이스의 사용자 지정 앱 생성 메뉴를 열고 다음을 등록합니다.

- MCP server URL: `https://<참가자-터널-호스트>/mcp`
- 인증: `Authorization: Bearer <BRIDGE_AUTH_TOKEN>` 또는 조직의 OAuth 보호 프록시
- 권한: 읽기 전용 도구만 허용

UI가 고정 Bearer 헤더 입력을 제공하지 않고 OAuth만 허용하면, 브리지 앞에 OAuth 2.1/OIDC reverse proxy를 두고 `/mcp`로 전달할 때 내부적으로 `Authorization: Bearer <BRIDGE_AUTH_TOKEN>`을 주입합니다. 브리지 토큰은 ChatGPT 대화나 저장소에 넣지 않습니다.

## 검증

```powershell
$env:BRIDGE_AUTH_TOKEN = "a-long-random-token-at-least-32-characters"
python -m pytest -q
python -m compileall app tests
```

운영 전 체크리스트는 [docs/installation.md](docs/installation.md)를 참고하세요. 테스트 프롬프트는 [prompts/test-prompts.md](prompts/test-prompts.md)에 있습니다.
