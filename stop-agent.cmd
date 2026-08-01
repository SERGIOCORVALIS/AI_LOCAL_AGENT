@echo off
setlocal
set SCRIPT_DIR=%~dp0
echo Stopping Local AI Agent Docker services...
pushd "%SCRIPT_DIR%infra"
docker compose stop qdrant coding api
set EXIT_CODE=%ERRORLEVEL%
popd
endlocal & exit /b %EXIT_CODE%
