@echo off
setlocal
set SCRIPT_DIR=%~dp0
echo Streaming Local AI Agent Docker logs...
pushd "%SCRIPT_DIR%infra"
docker compose logs -f qdrant api
set EXIT_CODE=%ERRORLEVEL%
popd
endlocal & exit /b %EXIT_CODE%
