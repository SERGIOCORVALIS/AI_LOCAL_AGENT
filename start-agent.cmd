@echo off
setlocal
set SCRIPT_DIR=%~dp0
echo Starting Local AI Agent in recommended Docker-first mode...
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%start-agent.ps1"
set EXIT_CODE=%ERRORLEVEL%
if not "%EXIT_CODE%"=="0" (
    echo.
    echo Start failed. Window stays open so you can read the error above.
    pause
)
endlocal & exit /b %EXIT_CODE%
