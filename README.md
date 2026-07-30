<div align="center">

# 🧠 Local AI Agent

### ⚡ Windows-first · Local-first · Safety-first Digital Twin Runtime

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Qdrant](https://img.shields.io/badge/Qdrant-Memory-DC244C?style=for-the-badge&logo=qdrant&logoColor=white)](https://qdrant.tech/)
[![License](https://img.shields.io/badge/License-MIT-22C55E?style=for-the-badge)](./LICENSE)
[![Version](https://img.shields.io/badge/Version-0.2.0-F59E0B?style=for-the-badge)](./VERSION)

[![Ruff](https://img.shields.io/badge/Ruff-Clean-✓-111827?style=flat-square&labelColor=F97316)](https://docs.astral.sh/ruff/)
[![mypy](https://img.shields.io/badge/mypy-strict-✓-111827?style=flat-square&labelColor=3B82F6)](https://mypy-lang.org/)
[![pytest](https://img.shields.io/badge/pytest-passing-✓-111827?style=flat-square&labelColor=10B981)](https://docs.pytest.org/)
[![Coverage](https://img.shields.io/badge/coverage-95%25+-✓-111827?style=flat-square&labelColor=8B5CF6)](./pyproject.toml)

> 💎 **Premium local autonomy** — orchestrate tasks, remember preferences, automate Windows workflows, and keep every side effect under policy control.

[📖 Setup Guide](./docs/WINDOWS_SETUP_GUIDE.md) · [🧭 Release Checklist](./docs/RELEASE_CHECKLIST.md) · [🧾 Changelog](./CHANGELOG.md) · [🔐 Threat Model](./docs/security/threat-model.md)

</div>

---

## ✨ Why Local AI Agent?

| 🎯 Capability | 💬 What you get |
|---|---|
| 🧩 **Typed orchestration** | Reliable task lifecycle with Pydantic contracts |
| 🛡️ **Safety layer** | Audit trail, dry-run, allowlist, approval gates |
| 🧪 **Sandbox execution** | Isolated runs for generated code |
| 🧠 **Memory & Digital Twin** | Preference retrieval via JSON or Qdrant |
| 🛰️ **Omnichannel ready** | CLI, HTTP API, Telegram / Watchdog / Playwright adapters |

---

## 🚀 Quick Start

### 🥇 Recommended — one click on Windows

```text
start-agent.cmd
```

Then open the admin panel:

```text
open-agent.cmd
```

> 🟢 **Tip:** first install with `windows-bootstrap.cmd` or  
> `.\windows-bootstrap.ps1 -UseDocker -RunTests`

### 🧰 Full bootstrap

```powershell
.\windows-bootstrap.ps1 -UseDocker -RunTests
```

### 🐳 Docker-first (manual)

```powershell
cd infra
docker compose up --build -d qdrant api
```

Verify status:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/status | ConvertTo-Json -Depth 8
```

### 💻 Local Python (without Docker)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
pytest
python -m apps.cli.main status
uvicorn apps.api.main:app --reload
```

---

## 🎮 One-Click Control Center

| 🔘 Action | 📁 Launcher | 🌈 Purpose |
|---|---|---|
| ▶️ Start | `start-agent.cmd` | Docker-first recommended mode |
| 📊 Status | `status-agent.cmd` | Containers + API status |
| 🔄 Restart | `restart-agent.cmd` | Rebuild & restart services |
| ⏹️ Stop | `stop-agent.cmd` | Stop API + Qdrant |
| 📜 Logs | `logs-agent.cmd` | Live Docker logs |
| 🖥️ Admin UI | `open-agent.cmd` | Open local dashboard |
| ❤️ Health | `healthcheck-agent.cmd` | Full readiness check |
| ⚙️ Configure | `configure-env.cmd` | Interactive `.env` wizard |
| 💾 Backup | `backup-agent.cmd` | Zip runtime + config |
| ♻️ Restore | `restore-agent.cmd` | Restore from backup |
| ⬆️ Update | `update-agent.cmd` | Refresh dependencies |

📘 Detailed Windows playbook: [`docs/WINDOWS_SETUP_GUIDE.md`](./docs/WINDOWS_SETUP_GUIDE.md)

---

## 🧱 Monorepo Layout

```text
📦 AI_LOCAL_AGENT
┣ 📂 apps/
┃ ┣ 🖥️ cli/          operator CLI
┃ ┗ 🌐 api/          FastAPI entrypoint + admin UI
┣ 📂 services/
┃ ┣ 🎛️ orchestrator/ runtime state machine
┃ ┣ 🧠 memory/       JSON + Qdrant backends
┃ ┣ 🐝 swarm/        multi-agent routing
┃ ┗ 📡 integrations/ Telegram / Watchdog / Playwright
┣ 📂 packages/       typed contracts & safety
┣ 📂 infra/          Docker Compose + API image
┣ 📂 docs/           guides, ADR, runbooks
┗ 📂 tests/          quality gates
```

---

## 🌐 Live Surfaces

| 🔗 Endpoint | 🎨 Role |
|---|---|
| `GET /health` | 💚 Liveness |
| `GET /status` | 📡 Runtime snapshot |
| `GET /metrics` | 📈 Counters & uptime |
| `GET /admin` | 🖥️ Local management panel |
| `GET /tasks/recent` | 🗂️ Recent tasks |
| `GET/POST/PATCH/DELETE /memory` | 🧠 Memory CRUD + filters |
| `POST /tasks/run` | 🚀 Run orchestrator task |

Admin panel: **http://127.0.0.1:8000/admin**

---

## ✅ Quality Standards

- 🐍 Python **3.12+**
- 🧬 Full type hints on public contracts
- 🧹 `ruff` · 🔎 `mypy` · 🧪 `pytest` · 📊 coverage · 🪝 pre-commit
- 🪵 Structured logging with correlation IDs
- 🛡️ Safety gates for side effects

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy .
.\.venv\Scripts\python.exe -m pytest
```

---

## 🔐 Safety & Governance

| 🛡️ Control | 📌 Behavior |
|---|---|
| 🧾 Audit log | Append-only JSONL with secret redaction |
| ✅ Allowlist | Execute actions limited via env config |
| ✋ Approvals | Destructive / privileged actions require approval |
| 💾 Backups | Local zip recovery under `backups/` |

---

## 📦 Release Pack

| 📁 File | 🧭 Purpose |
|---|---|
| `VERSION` | 🏷️ Current release |
| `CHANGELOG.md` | 📰 User-visible history |
| `docs/RELEASE_CHECKLIST.md` | ✅ Ship checklist |
| `LICENSE` · `NOTICE` | ⚖️ License + author support |

---

## 💖 Support the Author

**Pankov Sergey Vladimirovish**

I am self-taught and really enjoy exploring the field of IT. I would be grateful for any support for my future work in this area; advancing requires modern equipment that I unfortunately cannot afford.

| 🪙 Network | 📬 Address |
|---|---|
| 💎 USDT (ERC20) | `0x587d0B8B786BC8254862dFDd632E00C81752B50a` |
| 🟠 BTC | `1Hehwq6T9E6JhWu1u7e7PHAqxmQwQXWA9m` |

📄 Full license text: [`LICENSE`](./LICENSE) · [`NOTICE`](./NOTICE)

---

## 🏁 Current Status

🟢 **Production-ready local foundation** with:

- real HTTP API
- Docker-first Qdrant memory path
- Windows one-click ops suite
- admin UI + metrics
- optional Telegram / Watchdog / Playwright boundaries

<div align="center">

**Built for powerful Windows machines · Runs locally on your hardware · Learns with you**

⭐ If this project helps you — star the repo and share it!



                                 ⭐ Детальные рекомендации по моделям 
 1)   Gemma 4 E2B и E4B
  
         -(Edge / Mobile)Оптимизированы для работы на конечных устройствах.
         -Поддерживают мультимодальность: текст, изображения, видео и нативный аудиовход (распознавание речи без сторонних моделей)
        - Мобильные устройства: Смартфоны с Android (через AICore / LiteRT-LM) или iOS. 
         -Требуется от 6–8 ГБ общей RAM.Одноплатники: Raspberry Pi 5 (8GB), NVIDIA Jetson Nano.
          -Для E2B в 4-битном формате скорость работы будет близка к реальному времени (near-zero latency).
          -Компьютеры без дискретной GPU: Работают на обычных CPU через llama.cpp / Ollama.
          - Желательно иметь от 16 ГБ системной RAM DDR4/DDR5


3)   Gemma 4 12B Unified

     -(Золотой стандарт для ПК)Уникальная архитектура без классических энкодеров зрения и звука (работает напрямую с патчами картинок и аудио).
     -Идеальный баланс ума и прожорливости.Минимум для GPU: NVIDIA RTX 3060 (12GB) или RTX 4060.
     - В квантовании Q4/Q5 модель полностью влезает в видеопамять, выдавая отличный Token-per-Second.Apple Silicon: Любой Mac на M1/M2/M3 с 16 ГБ
     - объединенной памяти (Unified Memory) идеально крутит эту модель через MLX фреймворк.


6)    Gemma 4 26B MoE

       -(Высокая скорость / Бизнес)Архитектура Mixture of Experts: формально весит 26Б, но на каждый токен активирует всего 3.8 млрд параметров.
       - Работает со скоростью 4-битных моделей, но обладает эрудицией крупной сети.
       - Рекомендуемый GPU: Одна карта RTX 3090 / RTX 4090 (24GB). Модель в Q4 или Q5 квантовании займет около 18–20 ГБ VRAM, оставляя место под контекст.
       - Системные требования: Минимум 32 ГБ RAM на ПК. На Mac — версии с 32 ГБ или 64 ГБ общей памяти (Mac Studio / MacBook Pro M-Max).


9)    Gemma 4 31B Dense

  
      -(Флагман линейки)Плотная модель, входящая в топ-3 открытых моделей мира на Arena Leaderboard.
      -Требует жестких вычислительных мощностей, так как при каждом запросе активны все 31 млрд параметров.
      -Для домашнего использования (Quantized): Строго RTX 4090 (24GB) для запуска в сильном 4-битном сжатии (Q4_0).
       -При обработке больших документов (длинный контекст) 24 ГБ может не хватить, и начнется сброс в медленную системную RAM.
        -Для коммерческой разработки / Production (BF16 или Q8):Профессиональные карты: 1 × NVIDIA RTX 6000 Ada (48GB) или 1 × NVIDIA A100 / H100 (80GB).
        -Связки из двух видеокарт: 2 × RTX 3090/4090, объединенные через NVLink или распределенные через vLLM / Hugging Face Transformers.


