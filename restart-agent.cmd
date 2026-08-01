@echo off
setlocal
set SCRIPT_DIR=%~dp0
echo Restarting Local AI Agent Docker services...
pushd "%SCRIPT_DIR%infra"
docker compose up --build -d qdrant coding api
set EXIT_CODE=%ERRORLEVEL%
popd
if not "%EXIT_CODE%"=="0" (
    endlocal & exit /b %EXIT_CODE%
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-RestMethod 'http://127.0.0.1:8000/status' | ConvertTo-Json -Depth 8 } catch { Write-Error $_; exit 1 }"
endlocal
