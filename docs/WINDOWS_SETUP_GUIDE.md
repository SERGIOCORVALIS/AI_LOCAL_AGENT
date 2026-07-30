# Windows Setup Guide

This guide explains how to install, configure, run, and maintain the Local AI Agent on Windows.

## What This Project Includes

The repository provides:

- a local CLI for operator checks and runtime status
- a FastAPI service for orchestration and memory APIs
- a Docker-first Qdrant memory backend
- optional integrations for Telegram, Watchdog, and Playwright

## Recommended System Requirements

- Windows 10 or Windows 11
- Python 3.12 or newer
- Git
- Docker Desktop for the recommended Qdrant + API setup
- PowerShell 5.1+ or PowerShell 7+

## One-File Windows Bootstrap

The easiest way to set up the project is to run:

```powershell
.\windows-bootstrap.ps1 -UseDocker -RunTests
```

Or by double-clicking:

```text
windows-bootstrap.cmd
```

For a simpler daily start in the recommended mode:

```text
start-agent.cmd
```

For routine management:

```text
status-agent.cmd
restart-agent.cmd
stop-agent.cmd
logs-agent.cmd
open-agent.cmd
healthcheck-agent.cmd
configure-env.cmd
backup-agent.cmd
update-agent.cmd
```

### What the Bootstrap Script Does

`windows-bootstrap.ps1` will:

1. detect Python 3.12
2. create `.venv` if it does not exist
3. upgrade `pip`
4. install the project with `.[dev,integrations]`
5. create `.env` from `.env.example` if needed
6. run `python -m apps.cli.main status`
7. optionally run tests
8. optionally start Docker services
9. optionally start the local FastAPI server

## Bootstrap Script Modes

### 1. Install dependencies and prepare the environment

```powershell
.\windows-bootstrap.ps1
```

### 2. Install dependencies and run the test suite

```powershell
.\windows-bootstrap.ps1 -RunTests
```

### 3. Use Docker for Qdrant and API

```powershell
.\windows-bootstrap.ps1 -UseDocker -RunTests
```

### 4. Install Playwright browser binaries

```powershell
.\windows-bootstrap.ps1 -InstallPlaywrightBrowsers
```

### 5. Start the API locally without Docker

```powershell
.\windows-bootstrap.ps1 -RunApi
```

### 6. Try automatic installation of missing tools via winget

```powershell
.\windows-bootstrap.ps1 -InstallMissingTools
```

This mode may require administrator approval depending on your machine policy.

## Manual Installation

If you prefer to install everything manually:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev,integrations]"
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m pytest
```

## Configuration

The project reads settings from environment variables or `.env`.

Start by copying:

```powershell
Copy-Item .env.example .env
```

Then adjust the values in `.env` as needed.

### Important Variables

- `LOCAL_AI_AGENT_ENV`: environment name, usually `dev`
- `LOCAL_AI_AGENT_APP_NAME`: application name
- `LOCAL_AI_AGENT_MODEL_PRIMARY`: primary model identifier
- `LOCAL_AI_AGENT_MODEL_ROUTER`: router model identifier
- `LOCAL_AI_AGENT_QDRANT_URL`: Qdrant base URL
- `LOCAL_AI_AGENT_QDRANT_COLLECTION`: Qdrant collection name
- `LOCAL_AI_AGENT_MEMORY_STORE_PATH`: fallback local JSON memory store path
- `LOCAL_AI_AGENT_DOWNLOADS_WATCH_PATH`: Windows path watched by filesystem automation
- `LOCAL_AI_AGENT_TELEGRAM_BOT_TOKEN`: optional Telegram bot token
- `LOCAL_AI_AGENT_TELEGRAM_ADMIN_CHAT_ID`: optional Telegram admin chat id

## Running the Project

### One-click launchers

- `start-agent.cmd`: starts the recommended Docker-first mode
- `status-agent.cmd`: shows `docker compose ps` and tries to fetch the API status endpoint
- `restart-agent.cmd`: rebuilds and restarts the Docker services, then prints the API status payload
- `stop-agent.cmd`: stops the Docker services
- `logs-agent.cmd`: streams Docker logs for the API and Qdrant
- `open-agent.cmd`: opens the local admin panel in the browser
- `healthcheck-agent.cmd`: validates local readiness and critical endpoints
- `configure-env.cmd`: opens the interactive environment configuration wizard
- `backup-agent.cmd`: creates a local backup zip
- `restore-agent.cmd <archive.zip>`: restores runtime state and `.env` from a backup
- `update-agent.cmd`: refreshes the Python environment and performs a smoke test

Examples:

```text
start-agent.cmd
status-agent.cmd
restart-agent.cmd
stop-agent.cmd
logs-agent.cmd
open-agent.cmd
healthcheck-agent.cmd
```

### CLI status check

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main status
```

### Local API without Docker

```powershell
.\.venv\Scripts\python.exe -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --reload
```

### Docker-first API and Qdrant

```powershell
cd infra
docker compose up --build -d qdrant api
```

Verify:

```powershell
.\.venv\Scripts\python.exe -c "import json, urllib.request; print(json.dumps(json.load(urllib.request.urlopen('http://127.0.0.1:8000/status')), indent=2))"
```

### Local Admin Panel

Open:

```text
open-agent.cmd
```

Or navigate directly to:

```text
http://127.0.0.1:8000/admin
```

## API Endpoints

Main endpoints currently include:

- `GET /health`
- `GET /status`
- `GET /metrics`
- `GET /tasks/recent`
- `GET /admin`
- `POST /tasks/run`
- `GET /memory`
- `GET /memory/search`
- `POST /memory`
- `PATCH /memory/{memory_id}`
- `DELETE /memory/{memory_id}`

### Memory list with pagination and filtering

Example:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/memory?q=style&kind=preference&limit=10&offset=0"
```

## Quality Checks

Run all core checks with:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy .
.\.venv\Scripts\python.exe -m pytest
```

## Backup, Restore, and Update

### Create backup

```text
backup-agent.cmd
```

### Restore from backup

```text
restore-agent.cmd backups\local-ai-agent-backup-YYYYMMDD-HHMMSS.zip
```

### Refresh the local environment

```text
update-agent.cmd
```

### Run a full local healthcheck

```text
healthcheck-agent.cmd
```

## Safety and Local Governance

- common secret fields are redacted in the audit log
- execute-mode actions outside the configured allowlist require approval
- the execute allowlist is configured through `LOCAL_AI_AGENT_ALLOWED_EXECUTE_ACTIONS_RAW`
- backups are stored under `LOCAL_AI_AGENT_BACKUP_DIR`

## Observability

- runtime log file: `LOCAL_AI_AGENT_RUNTIME_LOG_PATH`
- audit log file: `LOCAL_AI_AGENT_AUDIT_LOG_PATH`
- metrics endpoint: `http://127.0.0.1:8000/metrics`
- recent tasks endpoint: `http://127.0.0.1:8000/tasks/recent`

## Troubleshooting

### PowerShell blocks script execution

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\windows-bootstrap.ps1
```

### Docker is installed but containers do not start

- make sure Docker Desktop is running
- retry `docker compose up --build -d qdrant api`
- inspect logs with:

```powershell
cd infra
docker compose logs qdrant api
```

### Python is not found

- install Python 3.12 manually, or
- run `.\windows-bootstrap.ps1 -InstallMissingTools`

### Qdrant is unavailable

The application will fall back to the JSON memory store when Qdrant cannot be reached.

## Project Files Added for Windows Users

- `windows-bootstrap.ps1`: main setup and run script
- `windows-bootstrap.cmd`: double-click launcher for the PowerShell bootstrap
- `start-agent.cmd`: quick launcher for the recommended Docker-first mode
- `status-agent.cmd`: quick status check for Docker services and API
- `restart-agent.cmd`: one-click rebuild/restart helper
- `stop-agent.cmd`: one-click stop helper
- `logs-agent.cmd`: Docker logs helper
- `open-agent.cmd`: admin UI launcher
- `healthcheck-agent.cmd`: full local readiness checker
- `configure-env.cmd`: environment wizard
- `backup-agent.cmd`: backup helper
- `restore-agent.cmd`: restore helper
- `update-agent.cmd`: dependency refresh helper
- `CHANGELOG.md`: release history
- `VERSION`: release version file
- `docs/RELEASE_CHECKLIST.md`: release checklist
- `docs/WINDOWS_SETUP_GUIDE.md`: detailed Windows documentation
- `LICENSE`: project license with author support notice
- `NOTICE`: author attribution and support information

## License and Author Support

This project includes a `LICENSE` file and a `NOTICE` file that embed the requested author attribution and support information for:

- Pankov Sergey Vladimirovish

Support details:

- USDT (ERC20): `0x587d0B8B786BC8254862dFDd632E00C81752B50a`
- BTC: `1Hehwq6T9E6JhWu1u7e7PHAqxmQwQXWA9m`
