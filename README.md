# Local AI Agent

Windows-first local autonomous AI agent platform designed as a safe Digital Twin runtime.

## License

This repository is licensed under the MIT License. See `LICENSE` and `NOTICE` for author attribution and support information for Pankov Sergey Vladimirovish.

## Goals

- Reliable task orchestration with typed contracts
- Safety-first local automation with auditability
- Sandbox execution for generated code
- Memory-driven personalization and preference retrieval
- Extensible capabilities for files, web, vision, code, and messaging

## Monorepo Layout

- `apps/cli` - operator-facing command line interface
- `apps/api` - FastAPI entrypoint for local automation and orchestration
- `services/orchestrator` - runtime state machine and capability execution
- `packages/core` - domain models and shared contracts
- `packages/config` - environment-aware settings and configuration loading
- `infra` - local infrastructure definitions
- `docs/adr` - architecture decisions
- `tests` - unit and integration tests

## Quality Standards

- Python 3.12+
- Full type hints on public contracts
- `ruff`, `mypy`, `pytest`, coverage, and pre-commit hooks
- Structured logging with correlation IDs
- Safety gates for side effects

## Quick Start

### Windows One-File Bootstrap

```powershell
.\windows-bootstrap.ps1 -UseDocker -RunTests
```

Double-click alternative:

```text
windows-bootstrap.cmd
```

Fast daily start:

```text
start-agent.cmd
```

Management helpers:

```text
status-agent.cmd
restart-agent.cmd
stop-agent.cmd
logs-agent.cmd
open-agent.cmd
healthcheck-agent.cmd
configure-env.cmd
backup-agent.cmd
restore-agent.cmd <backup.zip>
update-agent.cmd
```

Detailed setup and usage documentation is available in `docs/WINDOWS_SETUP_GUIDE.md`.

## Operations

- `http://127.0.0.1:8000/admin` provides a minimal local admin panel
- `GET /metrics` exposes local runtime counters
- `GET /tasks/recent` returns recent persisted tasks
- `healthcheck-agent.cmd` validates the local environment and API readiness
- `backup-agent.cmd` and `restore-agent.cmd` provide local recovery helpers
- `update-agent.cmd` refreshes the local Python environment safely

## Release Files

- `VERSION`
- `CHANGELOG.md`
- `docs/RELEASE_CHECKLIST.md`
- `LICENSE`
- `NOTICE`

### Recommended: Docker-First

```powershell
cd infra
docker compose up --build -d qdrant api
python -c "import json, urllib.request; print(json.dumps(json.load(urllib.request.urlopen('http://127.0.0.1:8000/status')), indent=2))"
```

This is the recommended local setup because the API can reach `qdrant` over the Docker network even when direct host access to the Qdrant REST port is unreliable.

### Local Dev Without Docker

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
pytest
python -m apps.cli.main status
uvicorn apps.api.main:app --reload
```

## Current Status

This repository now provides a tested local foundation plus a real HTTP entrypoint, Docker-first Qdrant-backed memory flow, and optional integration boundaries for Watchdog, Telegram, and Playwright.
