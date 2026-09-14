# 참가자용 간단 설치 안내

이 안내는 일반 참가자용입니다. 참가자는 터미널, PowerShell 명령, HTTPS 터널, 인증 토큰을 입력하지 않습니다. 이 폴더의 `participant\START-HERE.txt`도 함께 참고하세요.

## 참가자에게 전달할 것

- 관리자가 GitHub 저장소의 `Code → Download ZIP`으로 내려받은 압축 파일
- 또는 관리자가 압축해 전달한 프로젝트 폴더

참가자용 로컬 검색만 사용할 때는 `participant-config.json`, HTTPS 주소, 토큰을 만들 필요가 없습니다.

## 참가자 사용법

1. Zotero Desktop을 설치하고 실행합니다.
2. Zotero에서 로컬 API를 켭니다.
3. 압축 파일 안의 `participant\Start-Participant.vbs`를 더블클릭합니다.
4. 창에서 `Setup and Start` 버튼을 한 번 누릅니다.
5. 브라우저에 `Zotero 읽기 도우미`가 열리면 검색합니다.
6. 다음부터는 Zotero를 먼저 열고 같은 파일을 더블클릭하면 됩니다.

VBS 파일을 열어도 창이 나타나지 않으면 같은 폴더의 `Start-Participant-Fallback.cmd`를 더블클릭합니다. 이 파일은 오류 내용을 검은 창에 표시하므로 관리자에게 문제를 전달할 때 사용합니다.

`Start-Participant.vbs`를 더블클릭해도 창이 전혀 뜨지 않으면 관리자에게 `Start-Participant-Debug.cmd`를 실행한 화면을 보내세요. 이 파일은 문제 내용을 화면에 표시하는 진단용 파일입니다.

창이 열리지 않으면 Windows에서 파일을 차단한 경우일 수 있습니다. 파일을 마우스 오른쪽 버튼으로 열어 `속성 → 차단 해제`를 선택합니다.

## 관리자가 미리 해야 하는 일

- Zotero Desktop 설치 링크를 함께 보냅니다.
- 참가자가 사용할 ZIP 파일을 준비합니다.
- 처음 모임에서 Zotero의 로컬 API 허용 설정을 확인합니다.
- Python이 없는 참가자에게 [Python 3.11 이상](https://www.python.org/downloads/) 설치를 한 번 도와줍니다. 설치 화면에서 `Add python.exe to PATH`를 체크합니다.

개인 ChatGPT 계정 참가자에게는 ChatGPT 사용자 지정 MCP 앱을 요구하지 않습니다. ChatGPT 안에서 쓰는 MCP 연결은 별도의 고급 설정이며, 개인계정·요금제에 따라 제공되지 않을 수 있습니다.

참가자는 Python, PowerShell 명령, 포트 번호, 인증 토큰을 직접 입력하지 않습니다. 단, 최초 실행 시 Python이 설치되어 있지 않으면 관리자가 Python 설치 파일을 한 번 제공해야 합니다.

## 참가자 테스트 문장

```text
검색창에 `행복한 내향인의 특징`을 입력합니다.

결과에서 논문 레코드, 독립 PDF, 하위 PDF 첨부파일이 구분되어 표시되는지 확인합니다.
```
