@echo off
setlocal
set SCRIPT_DIR=%~dp0
if "%~1"=="" (
  echo Usage: restore-agent.cmd path\to\backup.zip
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%restore-agent.ps1" -ArchivePath "%~1"
endlocal
