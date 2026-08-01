<div align="center">

# 🪟 Windows Setup Guide

### 💎 Premium install · configure · operate · recover playbook

[![Windows](https://img.shields.io/badge/Windows-10%2F11-0078D6?style=for-the-badge&logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Desktop-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Guide](https://img.shields.io/badge/Status-Ready-22C55E?style=for-the-badge)](#-quick-path)

<p align="center">
  <img src="../assets/brand/local-ai-agent.png" width="120" alt="Local AI Agent" />
</p>

> 🚀 From zero to a running Local AI Agent with one-click launchers, healthchecks, backups, and a local admin panel.

</div>

---

## 🗺️ Quick Path

| ⏱️ Step | 🔘 Action | 🌈 Result |
|---|---|---|
| 1️⃣ | `windows-bootstrap.cmd` | Install deps + prepare `.venv` / `.env` |
| 2️⃣ | `start-agent.cmd` | Daily Docker-first start (no full reinstall) |
| 3️⃣ | `open-admin-panel.cmd` | Open **http://127.0.0.1:8000/admin** |
| 4️⃣ | `healthcheck-agent.cmd` | Confirm everything is green |

> 🟢 **Recommended daily flow:** `start-agent.cmd` → `open-admin-panel.cmd` → `status-agent.cmd`

---

## 🎁 What You Get

| 🧩 Component | 💬 Description |
|---|---|
| 🖥️ CLI | Operator status / doctor / task runs |
| 🌐 FastAPI | Orchestration + memory + metrics + admin UI |
| 🧠 Qdrant memory | Docker-first vector memory backend |
| 🔌 Integrations | Telegram · Watchdog · Playwright ready |

---

## 💻 System Requirements

| ✅ Item | 📌 Minimum |
|---|---|
| 🪟 OS | Windows 10 / 11 |
| 🐍 Python | 3.12+ |
| 🐙 Git | any recent version |
| 🐳 Docker Desktop | required for recommended mode |
| ⚡ Shell | PowerShell 5.1+ or 7+ |

---

## 🪄 One-File Bootstrap

### 🔥 Fastest start

```powershell
.\windows-bootstrap.ps1 -UseDocker -RunTests
```

Or double-click:

```text
windows-bootstrap.cmd
```

Daily recommended mode:

```text
start-agent.cmd
```

### Telegram bot (admin chat)

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy the token.
2. Put it in `.env` as `LOCAL_AI_AGENT_TELEGRAM_BOT_TOKEN=123456:ABC...`  
   **Important:** no spaces and no `# comments` on the same line as the secret.
3. Message the bot, then set `LOCAL_AI_AGENT_TELEGRAM_ADMIN_CHAT_ID` to your numeric chat id  
   (e.g. from [@userinfobot](https://t.me/userinfobot)).
4. Restart: `restart-agent.cmd` or `REBUT-DOKER.cmd`.
5. Confirm `/status` in Telegram or `telegram.available=true` in `GET /status`.
6. Optional avatar: [@BotFather](https://t.me/BotFather) → Edit Botpic → upload `assets/brand/local-ai-agent.png`.

While the agent works you should see:
- header status **«печатает…»**
- ack message **«Запрос принят / ИИ печатает ответ»**
- reaction 👀 on your message, then ✅ when done

Only the configured admin chat can talk to the bot. Host `.env` should use `LOCAL_AI_AGENT_QDRANT_URL=http://127.0.0.1:6333` (Compose overrides Qdrant inside Docker).

Telegram replies start automatically with the API when both Telegram keys are set. Standalone polling:

```text
start-telegram.cmd
```

### 🧠 What bootstrap does

1. 🔍 Detect Python 3.12
2. 🧪 Create `.venv` if missing
3. ⬆️ Upgrade `pip`
4. 📦 Install `.[dev,integrations]`
5. 📝 Create `.env` from `.env.example`
6. ✅ Run CLI status check
7. 🧪 Optionally run tests
8. 🐳 Optionally start Docker services
9. 🌐 Optionally start local FastAPI

> 💡 Bootstrap also supports interactive mode and waits for API readiness after Docker start.

---

## 🎛️ Bootstrap Modes

| # | 🎯 Mode | 🧾 Command |
|---|---|---|
| 1 | 📦 Setup only | `.\windows-bootstrap.ps1` |
| 2 | 🧪 Setup + tests | `.\windows-bootstrap.ps1 -RunTests` |
| 3 | 🐳 Docker-first | `.\windows-bootstrap.ps1 -UseDocker -RunTests` |
| 4 | 🎭 Playwright browsers | `.\windows-bootstrap.ps1 -InstallPlaywrightBrowsers` |
| 5 | 🌐 Local API | `.\windows-bootstrap.ps1 -RunApi` |
| 6 | 🛠️ Auto-install tools | `.\windows-bootstrap.ps1 -InstallMissingTools` |

> ⚠️ `-InstallMissingTools` may require administrator approval (winget).

---

## 🕹️ One-Click Launchers

| 🔘 Launcher | 🌈 Color cue | 📌 Purpose |
|---|---|---|
| `start-agent.cmd` | 🟢 Start | Recommended Docker-first launch |
| `status-agent.cmd` | 🔵 Status | Compose + API status |
| `restart-agent.cmd` | 🟡 Restart | Quick rebuild & restart |
| `rebuild-agent.cmd` | 🧱 Rebuild | Full Docker image rebuild + recreate |
| `stop-agent.cmd` | 🔴 Stop | Stop services |
| `logs-agent.cmd` | 🟣 Logs | Stream Docker logs |
| `open-admin-panel.cmd` | 🩵 UI | Open admin panel |
| `healthcheck-agent.cmd` | ❤️ Health | Full readiness validation |
| `configure-env.cmd` | ⚙️ Config | Interactive `.env` wizard |
| `backup-agent.cmd` | 💾 Backup | Create recovery zip |
| `restore-agent.cmd` | ♻️ Restore | Restore runtime / `.env` |
| `update-agent.cmd` | ⬆️ Update | Refresh Python environment |

```text
start-agent.cmd
status-agent.cmd
open-admin-panel.cmd
healthcheck-agent.cmd
```

---

## 🛠️ Manual Installation

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev,integrations]"
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m pytest
```

---

## ⚙️ Configuration

Start from template:

```powershell
Copy-Item .env.example .env
```

Or use the wizard:

```text
configure-env.cmd
```

### 🔑 Important variables

| 🏷️ Variable | 🎯 Meaning |
|---|---|
| `LOCAL_AI_AGENT_ENV` | Environment (`dev` or `prod`) |
| `LOCAL_AI_AGENT_APP_NAME` | App name |
| `LOCAL_AI_AGENT_MODEL_PRIMARY` | Primary Ollama model (chat + swarm coder/reviewer/researcher) |
| `LOCAL_AI_AGENT_MODEL_ROUTER` | Router Ollama model (routing JSON + lightweight swarm roles) |
| `LOCAL_AI_AGENT_MODEL_VISION` | Vision / VLM Ollama model id |
| `LOCAL_AI_AGENT_MODEL_EMBED` | Embedding model (e.g. `nomic-embed-text`) |
| *(runtime resolve)* | Short ids like `gemma4` resolve to installed tags (`gemma4:e4b-it-q4_K_M`) |
| `LOCAL_AI_AGENT_EMBEDDING_PREFER_NATIVE` | Keep native Ollama vector size (`true`) |
| `LOCAL_AI_AGENT_EMBEDDING_DIMENSIONS` | Optional fixed projection size (omit for native) |
| `LOCAL_AI_AGENT_OLLAMA_URL` | Ollama base URL (`http://127.0.0.1:11434`) |
| `LOCAL_AI_AGENT_QDRANT_URL` | Qdrant base URL |
| `LOCAL_AI_AGENT_QDRANT_COLLECTION` | Collection name |
| `LOCAL_AI_AGENT_SANDBOX_PREFER_DOCKER` | Prefer Docker sandbox (`true`) |
| `LOCAL_AI_AGENT_API_BIND_HOST` | Documented bind host (`127.0.0.1`) |
| `LOCAL_AI_AGENT_TRUSTED_HOSTS` | Trusted Host allowlist (csv) |
| `LOCAL_AI_AGENT_API_TOKEN` | Shared secret for mutating API routes |
| `LOCAL_AI_AGENT_REQUIRE_API_TOKEN` | Fail start in prod if token missing (`true`) |
| `LOCAL_AI_AGENT_RUNTIME_LOG_PATH` | Rotating runtime log |
| `LOCAL_AI_AGENT_BACKUP_DIR` | Backup directory |
| `LOCAL_AI_AGENT_ALLOWED_EXECUTE_ACTIONS_RAW` | Execute allowlist (include `fs_watch`) |
| `LOCAL_AI_AGENT_DENIED_EXECUTE_ACTIONS_RAW` | Hard-deny action names |
| `LOCAL_AI_AGENT_DOWNLOADS_WATCH_PATH` | FS watch path |
| `LOCAL_AI_AGENT_TELEGRAM_BOT_TOKEN` | BotFather token (no inline `#` comments) |
| `LOCAL_AI_AGENT_TELEGRAM_ADMIN_CHAT_ID` | Your numeric Telegram chat id only |

### Production profile

For hardened local use see [`docs/PRODUCTION.md`](./PRODUCTION.md):

```env
LOCAL_AI_AGENT_ENV=prod
LOCAL_AI_AGENT_REQUIRE_API_TOKEN=true
LOCAL_AI_AGENT_API_TOKEN=<long-random-secret>
LOCAL_AI_AGENT_API_BIND_HOST=127.0.0.1
```

Docker Compose binds `8000` / `6333` to `127.0.0.1` only.

### 🧩 Optional extras

```powershell
# Telegram + Watchdog + Playwright + faster-whisper STT
.\.venv\Scripts\python.exe -m pip install -e ".[integrations]"

# OCR (pytesseract + Pillow) — also install system Tesseract OCR
.\.venv\Scripts\python.exe -m pip install -e ".[perception]"

# Everything
.\.venv\Scripts\python.exe -m pip install -e ".[full]"

# Playwright Chromium browser (required after playwright package install)
.\.venv\Scripts\python.exe -m apps.cli.main playwright-setup
# or: .\.venv\Scripts\python.exe -m playwright install chromium
# or: .\windows-bootstrap.ps1 -InstallPlaywrightBrowsers
```

---

## 🚦 Running the Project

### 🖥️ CLI

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main status
.\.venv\Scripts\python.exe -m apps.cli.main doctor
.\.venv\Scripts\python.exe -m apps.cli.main ollama-check
.\.venv\Scripts\python.exe -m apps.cli.main run "Demo" "summarize workspace"
.\.venv\Scripts\python.exe -m apps.cli.main approve <task-id> --approved
.\.venv\Scripts\python.exe -m apps.cli.main voice C:\path\to\audio.ogg
.\.venv\Scripts\python.exe -m apps.cli.main playwright-setup
# Telegram (when bot is running): /approve <task-id>  /reject <task-id>
```

`ollama-check` verifies the daemon plus primary/router/vision/embed slots and swarm role mapping.

### 🧰 Ollama coding CLIs + web search

In Docker mode, coding CLIs (`codex` / `opencode` / `droid`) run in the **`coding` sidecar** (`infra/coding.Dockerfile`, port `127.0.0.1:8091`). The API calls it via `LOCAL_AI_AGENT_CODING_AGENTS_URL=http://coding:8091` (set by Compose). Claude Code is not bundled in v1.

Host / non-Docker installs can still use PATH CLIs:

```powershell
ollama launch codex --model gemma4:e4b-it-q4_K_M
ollama launch opencode --model gemma4:e4b-it-q4_K_M
ollama launch droid --model gemma4:e4b-it-q4_K_M
ollama launch claude --model gemma4:e4b-it-q4_K_M
```

The orchestrator auto-selects an installed CLI for coding goals (`coding_agent` capability). Configure via:

- `LOCAL_AI_AGENT_CODING_AGENTS_ENABLED=true`
- `LOCAL_AI_AGENT_CODING_AGENT_DEFAULT=auto` (`codex` / `opencode` / `droid` / `claude`)
- `LOCAL_AI_AGENT_CODING_AGENT_TIMEOUT_SECONDS=300`
- `LOCAL_AI_AGENT_CODING_AGENTS_URL=` (empty = local PATH; Compose sets `http://coding:8091`; host CLI against stack: `http://127.0.0.1:8091`)

After `rebuild-agent.cmd`, smoke:

```powershell
Invoke-RestMethod http://127.0.0.1:8091/agents
Invoke-RestMethod http://127.0.0.1:8000/status  # coding_agents.available should list CLIs
```

Web search uses DuckDuckGo HTML (no API key) through the `web_search` capability when the goal asks to search/research without a URL. `status` / `doctor` / `GET /status` expose `coding_agents` readiness and `web_search.provider=duckduckgo`.

### 🌐 Local API (no Docker)

```powershell
.\.venv\Scripts\python.exe -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --reload
```

### 🐳 Docker-first API + Qdrant + coding sidecar

```powershell
cd infra
docker compose up --build -d qdrant coding api
```

Or from repo root: `rebuild-agent.cmd` / `start-agent.cmd`.

Verify:

```powershell
Invoke-RestMethod http://127.0.0.1:8091/agents | ConvertTo-Json -Depth 8
Invoke-RestMethod http://127.0.0.1:8000/status | ConvertTo-Json -Depth 8
```

`/status` includes `perception` readiness: STT, OCR, Playwright browsers, embeddings, and `ollama_agents` slots/roles, plus `coding_agents` and `web_search`.  
`/ready` is the readiness probe (memory + optional Ollama); `/health` is liveness only.

### 🖥️ Admin panel

```text
open-admin-panel.cmd
```

Direct URL:

```text
http://127.0.0.1:8000/admin
```

Luxury admin SPA (RU + tech terms): **Обзор**, **Чат** (`POST /tasks/run`), **Задачи**, **Память**, **Стек**, **Настройки**.  
Settings dialogs write `.env` via `PUT /settings` — then restart with `restart-agent.cmd` / `REBUT-DOKER.cmd`.  
Ops (Approve / FS Watch / Voice) live under Настройки → Операции. Paste API token in the left rail when required.

---

## 🌐 API Map

| 🎨 Method | 🔗 Path | 📌 Purpose |
|---|---|---|
| 💚 GET | `/health` | Liveness |
| 📡 GET | `/status` | Runtime + perception snapshot |
| 📈 GET | `/metrics` | Counters / uptime |
| 🗂️ GET | `/tasks/recent` | Recent tasks |
| 🔎 GET | `/tasks/{id}` | Load task by id |
| ✅ POST | `/tasks/{id}/approve` | Continue paused approval task |
| 🖥️ GET | `/admin` | Luxury admin panel |
| ⚙️ GET/PUT | `/settings` | Read / persist settings to `.env` |
| 🚀 POST | `/tasks/run` | Run task / admin chat |
| 🧠 GET | `/memory` | List / filter / paginate |
| 🔎 GET | `/memory/search` | Semantic / text search |
| ➕ POST | `/memory` | Create memory |
| 🩹 PATCH | `/memory/{id}` | Update memory |
| 🗑️ DELETE | `/memory/{id}` | Delete memory |
| 👁️ POST | `/fs/watch/start` | Start filesystem watch |
| 🛑 POST | `/fs/watch/stop` | Stop filesystem watch |
| 📥 GET | `/fs/watch/events` | Drain watch events |
| 🎙️ POST | `/voice/transcribe` | STT for local `audio_path` |

### 🧠 Memory pagination example

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/memory?q=style&kind=preference&limit=10&offset=0"
```

### ✅ Approve example

```powershell
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/tasks/<task-id>/approve" `
  -ContentType "application/json" `
  -Body '{"approved":true,"reviewer":"operator"}'
```

---

## ✅ Quality Checks

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy .
.\.venv\Scripts\python.exe -m pytest
```

| 🧪 Gate | 🌈 Badge |
|---|---|
| Ruff | 🟠 lint clean |
| mypy | 🔵 strict types |
| pytest | 🟢 passing |
| coverage | 🟣 95%+ |

---

## 💾 Backup · Restore · Update

| 🔘 Action | 🧾 Command |
|---|---|
| 💾 Create backup | `backup-agent.cmd` |
| ♻️ Restore backup | `restore-agent.cmd backups\local-ai-agent-backup-YYYYMMDD-HHMMSS.zip` |
| ⬆️ Update env | `update-agent.cmd` |
| ❤️ Healthcheck | `healthcheck-agent.cmd` |

> ⚠️ Restore asks for explicit confirmation (`RESTORE`) before overwriting runtime / `.env`.

---

## 🛡️ Safety & Observability

### 🔐 Governance

- 🧾 Secret fields are redacted in audit logs
- ✅ Execute actions outside allowlist require approval
- 🧷 Allowlist via `LOCAL_AI_AGENT_ALLOWED_EXECUTE_ACTIONS_RAW`
- 💾 Backups live under `LOCAL_AI_AGENT_BACKUP_DIR`

### 📊 Observability

| 🧭 Signal | 📍 Location |
|---|---|
| 🪵 Runtime logs | `LOCAL_AI_AGENT_RUNTIME_LOG_PATH` |
| 🧾 Audit log | `LOCAL_AI_AGENT_AUDIT_LOG_PATH` |
| 📈 Metrics | http://127.0.0.1:8000/metrics |
| 🗂️ Recent tasks | http://127.0.0.1:8000/tasks/recent |

---

## 🩹 Troubleshooting

### 🚫 PowerShell blocks scripts

```powershell
powershell -ExecutionPolicy Bypass -File .\windows-bootstrap.ps1
```

### 🚀 `start-agent.cmd` fails

- ✅ Ensure Docker Desktop is **Ready** (not just installed)
- 🔌 Free port `8000` if a local `uvicorn` is already bound there
- 🧰 First-time setup: run `windows-bootstrap.cmd` once, then use `start-agent.cmd` daily
- 📜 Inspect logs with `logs-agent.cmd`

### 🐳 Docker installed but containers fail

- ✅ Ensure Docker Desktop is running
- 🔁 Retry `docker compose up --build -d qdrant api`
- 📜 Inspect logs:

```powershell
cd infra
docker compose logs qdrant api
```

Or:

```text
logs-agent.cmd
```

### 🐍 Python not found

- install Python 3.12 manually, or
- run `.\windows-bootstrap.ps1 -InstallMissingTools`

### 🧠 Qdrant unavailable

> 🟡 App automatically falls back to the JSON memory store.

---

## 📁 Windows File Pack

| 📁 File | 🎯 Role |
|---|---|
| `windows-bootstrap.ps1` | Main bootstrap engine |
| `windows-bootstrap.cmd` | Double-click bootstrap |
| `start-agent.cmd` | Daily start |
| `start-agent.ps1` | Daily start engine |
| `status-agent.cmd` | Status |
| `restart-agent.cmd` | Restart |
| `rebuild-agent.cmd` / `rebuild-agent.ps1` | Full Docker rebuild |
| `stop-agent.cmd` | Stop |
| `logs-agent.cmd` | Logs |
| `open-admin-panel.cmd` | Admin UI |
| `healthcheck-agent.cmd` | Health |
| `configure-env.cmd` | Env wizard |
| `backup-agent.cmd` | Backup |
| `restore-agent.cmd` | Restore |
| `update-agent.cmd` | Update |
| `CHANGELOG.md` | Release notes |
| `VERSION` | Version stamp |
| `docs/RELEASE_CHECKLIST.md` | Ship checklist |
| `LICENSE` · `NOTICE` | License + support |

---

## 💖 License & Author Support

**Pankov Sergey Vladimirovish**

I am self-taught and really enjoy exploring the field of IT. I would be grateful for any support for my future work in this area; advancing requires modern equipment that I unfortunately cannot afford.

| 🪙 Asset | 📬 Address |
|---|---|
| 💎 USDT (ERC20) | `0x587d0B8B786BC8254862dFDd632E00C81752B50a` |
| 🟠 BTC | `1Hehwq6T9E6JhWu1u7e7PHAqxmQwQXWA9m` |

<div align="center">

### 🏁 You're ready

**Bootstrap → Start → Open Admin → Healthcheck**

🟢 Have a smooth local AI day!

</div>
