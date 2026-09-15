@echo off
start "" powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0Install-Zotero-for-ChatGPT.ps1"
exit /b
