# GitHub에서 참가자에게 배포하는 방법

## 강사가 미리 할 일

참가자에게 다음 두 링크만 보냅니다.

1. Zotero Desktop 설치: <https://www.zotero.org/download/>
2. GitHub 최신 Release의 `Install-Zotero-for-ChatGPT.exe`

참가자별 파일을 만들거나 주소·토큰을 발급할 필요가 없습니다. 참가자에게 소스 ZIP, `Start-Participant.vbs`, Python 설치 파일을 보내지 않습니다.

## 참가자에게 그대로 보낼 문장

```text
1. Zotero Desktop과 Windows용 ChatGPT 앱을 설치해 주세요.
2. Zotero를 열고 설정의 고급 항목에서 '이 컴퓨터의 다른 애플리케이션이 Zotero와 통신하도록 허용'을 켜 주세요.
3. 함께 보낸 GitHub 링크에서 Install-Zotero-for-ChatGPT.exe를 받아 더블클릭해 주세요.
4. 설치 완료 후 ChatGPT 앱을 완전히 종료했다가 다시 열어 주세요.
5. ChatGPT 설정의 플러그인 → Personal에서 Zotero for ChatGPT를 설치하거나 켜 주세요.
6. 새 일반 채팅에서 '내 Zotero에서 최근 추가된 자료 3개를 찾아줘'라고 입력해 주세요.
```

## 강의 당일 확인 순서

1. 참가자 화면에서 Zotero가 실행 중인지 확인합니다.
2. ChatGPT 플러그인 목록에 `Zotero for ChatGPT`가 있는지 확인합니다.
3. 최근 자료 3개 조회를 실행합니다.
4. 한 자료의 초록 요약과 PDF 전문 검색을 실행합니다.
5. 태그는 먼저 제안만 받아 봅니다.
6. 쓰기 기능 시범이 필요하면 테스트 자료 하나에만 태그 추가를 요청하고 ChatGPT와 Zotero의 두 승인 화면을 설명합니다.

## 주의

- 참가자는 Python, 터미널, PowerShell, 포트 번호, HTTPS 주소, 인증 토큰을 입력하지 않습니다.
- 웹 브라우저용 ChatGPT나 모바일 앱이 아니라 Windows용 ChatGPT 데스크톱 앱을 사용합니다.
- 실행 파일은 아직 코드 서명 인증서가 없으므로 Windows가 처음 한 번 보호 안내를 표시할 수 있습니다.
- 설치 파일은 GitHub Release 링크로만 배포하고 메신저에 재업로드한 사본은 피합니다.
- 민감 자료를 요약하면 해당 텍스트가 OpenAI 서비스로 전송될 수 있으므로 강의 전에 개인정보 안내를 합니다.
