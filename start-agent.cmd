@echo off
setlocal
set SCRIPT_DIR=%~dp0
echo Starting Local AI Agent in recommended Docker-first mode...
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%windows-bootstrap.ps1" -UseDocker
endlocal
