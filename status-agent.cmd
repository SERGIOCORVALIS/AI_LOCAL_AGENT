@echo off
setlocal
set SCRIPT_DIR=%~dp0
echo Local AI Agent Docker service status:
pushd "%SCRIPT_DIR%infra"
docker compose ps
set EXIT_CODE=%ERRORLEVEL%
popd
if not "%EXIT_CODE%"=="0" (
    endlocal & exit /b %EXIT_CODE%
)
echo.
echo API status endpoint:
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-RestMethod 'http://127.0.0.1:8000/status' | ConvertTo-Json -Depth 8 } catch { Write-Warning 'API endpoint is not reachable yet.'; exit 0 }"
endlocal
