@echo off
setlocal
cd /d "%~dp0.."
echo Starting Zotero Read-only Assistant...
powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File "%~dp0ParticipantLauncher.ps1"
if errorlevel 1 (
  echo.
  echo The setup window could not be started.
  echo Please send this window to the administrator.
  pause
)
