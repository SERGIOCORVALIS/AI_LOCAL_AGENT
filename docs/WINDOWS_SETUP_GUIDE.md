<div align="center">

# 🪟 Windows Setup Guide

### 💎 Premium install · configure · operate · recover playbook

[![Windows](https://img.shields.io/badge/Windows-10%2F11-0078D6?style=for-the-badge&logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Desktop-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Guide](https://img.shields.io/badge/Status-Ready-22C55E?style=for-the-badge)](#-quick-path)

> 🚀 From zero to a running Local AI Agent with one-click launchers, healthchecks, backups, and a local admin panel.

</div>

---

## 🗺️ Quick Path

| ⏱️ Step | 🔘 Action | 🌈 Result |
|---|---|---|
| 1️⃣ | `windows-bootstrap.cmd` | Install deps + prepare `.venv` / `.env` |
| 2️⃣ | `start-agent.cmd` | Start Docker-first API + Qdrant |
| 3️⃣ | `open-agent.cmd` | Open **http://127.0.0.1:8000/admin** |
| 4️⃣ | `healthcheck-agent.cmd` | Confirm everything is green |

> 🟢 **Recommended daily flow:** `start-agent.cmd` → `open-agent.cmd` → `status-agent.cmd`

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
| `restart-agent.cmd` | 🟡 Restart | Rebuild & restart |
| `stop-agent.cmd` | 🔴 Stop | Stop services |
| `logs-agent.cmd` | 🟣 Logs | Stream Docker logs |
| `open-agent.cmd` | 🩵 UI | Open admin panel |
| `healthcheck-agent.cmd` | ❤️ Health | Full readiness validation |
| `configure-env.cmd` | ⚙️ Config | Interactive `.env` wizard |
| `backup-agent.cmd` | 💾 Backup | Create recovery zip |
| `restore-agent.cmd` | ♻️ Restore | Restore runtime / `.env` |
| `update-agent.cmd` | ⬆️ Update | Refresh Python environment |

```text
start-agent.cmd
status-agent.cmd
open-agent.cmd
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
| `LOCAL_AI_AGENT_ENV` | Environment (`dev`) |
| `LOCAL_AI_AGENT_APP_NAME` | App name |
| `LOCAL_AI_AGENT_MODEL_PRIMARY` | Primary model id |
| `LOCAL_AI_AGENT_MODEL_ROUTER` | Router model id |
| `LOCAL_AI_AGENT_QDRANT_URL` | Qdrant base URL |
| `LOCAL_AI_AGENT_QDRANT_COLLECTION` | Collection name |
| `LOCAL_AI_AGENT_RUNTIME_LOG_PATH` | Rotating runtime log |
| `LOCAL_AI_AGENT_BACKUP_DIR` | Backup directory |
| `LOCAL_AI_AGENT_ALLOWED_EXECUTE_ACTIONS_RAW` | Execute allowlist |
| `LOCAL_AI_AGENT_DOWNLOADS_WATCH_PATH` | FS watch path |
| `LOCAL_AI_AGENT_TELEGRAM_BOT_TOKEN` | Optional Telegram token |
| `LOCAL_AI_AGENT_TELEGRAM_ADMIN_CHAT_ID` | Optional admin chat |

---

## 🚦 Running the Project

### 🖥️ CLI status

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main status
```

### 🌐 Local API (no Docker)

```powershell
.\.venv\Scripts\python.exe -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --reload
```

### 🐳 Docker-first API + Qdrant

```powershell
cd infra
docker compose up --build -d qdrant api
```

Verify:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/status | ConvertTo-Json -Depth 8
```

### 🖥️ Admin panel

```text
open-agent.cmd
```

Direct URL:

```text
http://127.0.0.1:8000/admin
```

---

## 🌐 API Map

| 🎨 Method | 🔗 Path | 📌 Purpose |
|---|---|---|
| 💚 GET | `/health` | Liveness |
| 📡 GET | `/status` | Runtime snapshot |
| 📈 GET | `/metrics` | Counters / uptime |
| 🗂️ GET | `/tasks/recent` | Recent tasks |
| 🖥️ GET | `/admin` | Local dashboard |
| 🚀 POST | `/tasks/run` | Run task |
| 🧠 GET | `/memory` | List / filter / paginate |
| 🔎 GET | `/memory/search` | Search memory |
| ➕ POST | `/memory` | Create memory |
| 🩹 PATCH | `/memory/{id}` | Update memory |
| 🗑️ DELETE | `/memory/{id}` | Delete memory |

### 🧠 Memory pagination example

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/memory?q=style&kind=preference&limit=10&offset=0"
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
| `status-agent.cmd` | Status |
| `restart-agent.cmd` | Restart |
| `stop-agent.cmd` | Stop |
| `logs-agent.cmd` | Logs |
| `open-agent.cmd` | Admin UI |
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
