<div align="center">

# Changelog

[![Version](https://img.shields.io/badge/Latest-0.3.0-F59E0B?style=for-the-badge)](./VERSION)
[![Status](https://img.shields.io/badge/Channel-Stable-22C55E?style=for-the-badge)](#-030---2026-07-30)

All notable product changes live here.

</div>

---

## Unreleased

### Added

- Official Local AI Agent brand mark (`assets/brand/local-ai-agent.png`) in admin UI, README, and docs
- Luxury admin panel SPA (`/admin`) with left nav, agent chat dialog, stack views, settings dialogs
- `GET/PUT /settings` persists allowlisted keys to `.env` (restart required; secrets masked)
- Telegram UX: typing («печатает…»), ack on receive, progress edits, reactions, busy-chat guard
- Ollama agent catalog with role→model slots (primary/router/vision/embed)
- Runtime model resolution (`gemma4` → installed tag like `gemma4:e4b-it-q4_K_M`)
- Swarm roles use mapped models (`router`/`ops` → router model; others → route target)
- CLI `ollama-check` plus `ollama_agents` readiness in `/status` and `doctor`
- `configure-env.ps1` probes local Ollama and suggests installed models

### Fixed

- Telegram text handling no longer blocks aiogram polling (work runs in a thread)
- Secret env values strip inline `# comments` / placeholder templates
- `.env.example` Telegram + Qdrant host guidance (Compose still overrides in Docker)

---

## 0.3.0 — 2026-07-30

> Local Windows + Docker LAN production readiness.

### Added

- Prod settings: `API_BIND_HOST`, `API_TOKEN`, `REQUIRE_API_TOKEN`, `TRUSTED_HOSTS`
- API token middleware for mutating routes; `TrustedHostMiddleware`
- `GET /ready` readiness probe (separate from `/health` liveness)
- Perception readiness in `/status` and CLI `doctor` (STT, OCR, VLM, Playwright, embeddings)
- Native Ollama embedding dimensions (`EMBEDDING_PREFER_NATIVE`)
- Playwright browser install check + CLI `playwright-setup`
- Telegram `/approve` and `/reject` for paused tasks
- Sandbox execution metadata: `mode`, `isolated`, `degraded`
- Structured prod logging with `correlation_id`
- `docs/PRODUCTION.md` runbook

### Fixed

- Removed fake vision placeholder PNG; vision requires a real image file
- Planner no longer invents `sandbox-ok` / `example.com` defaults
- Reflect reports `backend=local` / `degraded` when Ollama is offline
- VLM readiness probes Ollama instead of always reporting available
- Version sync across `VERSION`, `pyproject.toml`, and API

### Security

- Docker Compose binds API/Qdrant to `127.0.0.1`
- Non-root API container user
- Prod fail-fast when `REQUIRE_API_TOKEN=true` and token is empty

---

## 0.2.0 — 2026-07-30

> Windows one-click suite, admin UI, metrics, safer local governance.

### Added

- Windows bootstrap + management scripts  
  (`install` · `start` · `stop` · `restart` · `status` · `logs` · `open` · `healthcheck` · `backup` · `restore` · `update` · `env setup`)
- Docker-first local operations guidance for Windows users
- Memory pagination / filtering + `MemoryBackend` protocol abstraction
- `/metrics`, `/tasks/recent`, `/admin` endpoints
- Runtime log path, backup directory, admin UI title, execute allowlist settings
- Audit redaction for common secret fields
- Local execute allowlist protection

### Docs & polish

- README + Windows Setup Guide
- Release checklist + version stamp

---

## Legend

| Tag | Meaning |
|---|---|
| Added | New capability |
| Fixed | Bug / reliability fix |
| Security | Safety / governance |
| Docs | Documentation |
