# Zotero for ChatGPT

Windows용 ChatGPT 데스크톱 앱의 일반 채팅에서 각 사용자의 로컬 Zotero Desktop 자료를 검색하고 분석하는 플러그인입니다. 참가자는 Python, 터미널, PowerShell, 포트 번호, 인증 토큰, HTTPS 주소를 입력하지 않습니다.

기존 `Zotero-Read-Only-Assistant.exe`는 브라우저에서 목록만 보는 로컬 도우미였습니다. 이 프로젝트의 새 설치 파일 `Install-Zotero-for-ChatGPT.exe`는 ChatGPT가 Zotero 도구를 직접 호출하도록 로컬 MCP 플러그인을 설치합니다. 요약·비교·질문 답변은 ChatGPT가 수행합니다.

## 참가자 설치

1. [Zotero Desktop](https://www.zotero.org/download/)을 설치하고 실행합니다.
2. Zotero에서 `설정 → 고급 → 이 컴퓨터의 다른 애플리케이션이 Zotero와 통신하도록 허용`을 켭니다.
3. GitHub Releases에서 `Install-Zotero-for-ChatGPT.exe`를 내려받아 더블클릭합니다.
4. 설치 완료 안내가 나오면 ChatGPT 데스크톱 앱을 완전히 종료했다가 다시 엽니다.
5. ChatGPT의 `설정 → 플러그인`에서 `Personal → Zotero for ChatGPT`를 설치하거나 활성화합니다.
6. 새 일반 채팅에서 다음과 같이 말합니다.

```text
내 Zotero에서 최근 추가된 논문 5개를 찾아줘.
```

설치 상세와 문제 해결은 [참가자용 설치 안내](docs/participant-installation.md)를 참고하세요.

## 지원 기능

읽기 도구 8개:

- 라이브러리 검색
- 최근 자료 조회
- 자료 메타데이터 조회
- 태그 조회
- 컬렉션 조회
- 하위 PDF 첨부파일 확인
- PDF 색인 전문 검색
- PDF 색인 전문을 구간별로 읽기

승인 후 쓰기 도구 2개:

- 태그 추가·제거
- 기존 컬렉션에 자료 추가

논문·서지 레코드, 독립 PDF, 하위 PDF 첨부파일을 구분합니다. 값이 없으면 정확히 `확인되지 않음`을 반환합니다. PDF 전문은 Zotero가 색인한 텍스트만 읽습니다.

다음 변경은 지원하지 않습니다.

- 자료 또는 파일 삭제
- 컬렉션 생성·삭제·이동
- 노트 생성·수정·삭제
- 제목·저자·초록 등 서지정보 덮어쓰기

태그나 컬렉션을 변경할 때는 ChatGPT의 도구 실행 승인과 Zotero Desktop의 로컬 쓰기 권한 승인이 모두 필요합니다.

## 구조와 보안

```text
Windows ChatGPT 데스크톱 일반 채팅
              │ 로컬 stdio MCP
              ▼
      Zotero for ChatGPT 플러그인
              │ localhost 요청
              ▼
 Zotero Desktop 127.0.0.1:23119/api/
```

Zotero 로컬 API는 `localhost`에만 둡니다. 외부 HTTPS 터널, 공유기 포트 개방, 참가자별 서버 주소와 토큰은 필요하지 않습니다. 이 방식은 Windows ChatGPT 데스크톱 앱용이며 웹 브라우저나 모바일 ChatGPT에서는 로컬 Zotero에 연결할 수 없습니다.

ChatGPT가 요약·비교를 수행하면 선택된 서지정보나 PDF 텍스트가 사용자의 OpenAI 서비스로 전송될 수 있습니다. 민감한 자료는 사용 전 소속기관 정책과 사용 중인 ChatGPT 계정의 데이터 설정을 확인하세요.

## Claude용 Zotero MCP와의 관계

[isezen/zotero-mcp](https://github.com/isezen/zotero-mcp)는 Claude에만 묶인 형식이 아니라 MCP 서버이므로 기능 설계의 참고가 될 수 있습니다. 이 프로젝트는 일반 참가자용 Windows 설치, ChatGPT 플러그인 등록, 로컬 Zotero 승인 절차를 별도로 구현했고 삭제·노트 편집·서지정보 덮어쓰기 같은 기능은 포함하지 않았습니다.

## 개발 및 검증

```powershell
python -m pytest -q
python -m compileall app tests stdio_entry.py setup_entry.py
powershell -ExecutionPolicy Bypass -File .\build-windows.ps1
```

빌드 결과:

- `release/Install-Zotero-for-ChatGPT.exe`: 참가자용 설치 파일
- `release/Zotero-ChatGPT-MCP.exe`: 플러그인 내부 MCP 실행 파일
- `release/Zotero-Read-Only-Assistant.exe`: 이전 로컬 목록 열람 도우미

테스트 문장은 [테스트 프롬프트](prompts/test-prompts.md)에 있습니다. HTTPS 서버 방식은 데스크톱 플러그인을 사용할 수 없는 조직 환경을 위한 고급·레거시 선택지이며 [고급 설치 안내](docs/installation.md)에 분리했습니다.
