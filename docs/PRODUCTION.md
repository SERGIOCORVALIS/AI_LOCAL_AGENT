<p align="center">
  <img src="../assets/brand/local-ai-agent.png" width="96" alt="Local AI Agent" />
</p>

# Production Runbook (Local Windows + Docker LAN)

This project is a **local Windows appliance**. Production means hardened daily use on `127.0.0.1` / private LAN — not a public internet service.

## What production includes

- Bind API and Qdrant to localhost
- Optional API token for mutating routes
- Trusted Host middleware
- `/health` (liveness) and `/ready` (readiness)
- Docker Compose restart + healthchecks
- Non-root API container user
- Structured JSON logs with `correlation_id` when `LOCAL_AI_AGENT_ENV=prod`

## What is out of scope

- Public TLS / reverse proxy certificates
- OAuth / multi-user identity
- Internet-facing exposure of admin UI or Qdrant

Do **not** publish ports `8000` / `6333` to the public internet.

## Recommended `.env` for prod

```env
LOCAL_AI_AGENT_ENV=prod
LOCAL_AI_AGENT_LOG_LEVEL=INFO
LOCAL_AI_AGENT_API_BIND_HOST=127.0.0.1
LOCAL_AI_AGENT_TRUSTED_HOSTS=127.0.0.1,localhost
LOCAL_AI_AGENT_API_TOKEN=<generate-a-long-random-secret>
LOCAL_AI_AGENT_REQUIRE_API_TOKEN=true
LOCAL_AI_AGENT_SANDBOX_PREFER_DOCKER=true
```

If `ENV=prod` and `REQUIRE_API_TOKEN=true` without `API_TOKEN`, the process refuses to start.

## Start

```powershell
# Interactive env wizard (optional)
.\configure-env.cmd

# Docker-first
.\start-agent.cmd

# Health
.\healthcheck-agent.cmd
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/ready
```

Admin UI: http://127.0.0.1:8000/admin (luxury SPA — chat, stack, settings)  
Paste the API token into the left-rail field before mutating actions. Settings write `.env` via `PUT /settings` and require `restart-agent.cmd`.

## Mutating API with token

```powershell
$headers = @{ "X-API-Token" = "<token>"; "Content-Type" = "application/json" }
Invoke-RestMethod -Method Post http://127.0.0.1:8000/tasks/run `
  -Headers $headers `
  -Body '{"title":"demo","goal":"summarize workspace"}'
```

Also accepted: `Authorization: Bearer <token>`.

Public without token: `GET /health`, `GET /ready`, OpenAPI docs, and other `GET` reads.

## Backup / restore

```powershell
.\backup-agent.cmd
.\restore-agent.cmd
```

Runtime state lives under `runtime/`; backups under `backups/`. Compose mounts both into the API container.

## Telegram (optional)

```env
LOCAL_AI_AGENT_TELEGRAM_BOT_TOKEN=<botfather-token>
LOCAL_AI_AGENT_TELEGRAM_ADMIN_CHAT_ID=<numeric-chat-id>
```

Rules:
- Both values required for polling to start
- Do not put `# comments` on the same line as secrets
- After editing `.env`, restart the API container / process
- Bot answers only the admin chat; UX shows typing («печатает…»), ack, then the reply
- Use `/approve <task-id>` / `/reject <task-id>` for paused tasks

If Telegram stops after an `.env` edit: check token/`chat_id`, run `GET /status` → `telegram.available`, and rotate the token in BotFather if it was ever logged.

## Verification checklist

1. `ruff` / `mypy` / `pytest` green
2. `start-agent.cmd` brings up healthy API + Qdrant
3. `/health` returns `ok` with version `0.3.0`
4. Mutating POST without token returns `401` when token is configured
5. `backup-agent` / `restore-agent` round-trip works
