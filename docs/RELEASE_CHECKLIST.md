<div align="center">

# 🧭 Release Checklist

[![Release](https://img.shields.io/badge/Process-Premium-8B5CF6?style=for-the-badge)](#-before-release)
[![Quality](https://img.shields.io/badge/Gates-Required-EF4444?style=for-the-badge)](#-quality-gates)

> ✅ Use this checklist before every public push / tag.

</div>

---

## 🧾 Before Release

- [ ] 🏷️ Confirm `VERSION` is updated
- [ ] 📰 Update `CHANGELOG.md` with user-visible changes
- [ ] ⚖️ Verify `LICENSE` and `NOTICE` are present
- [ ] ⚙️ Verify `.env.example` contains all required settings
- [ ] 📘 Skim `README.md` and `docs/WINDOWS_SETUP_GUIDE.md` for stale steps

---

## 🧪 Quality Gates

- [ ] 🟠 `python -m ruff check .`
- [ ] 🔵 `python -m mypy .`
- [ ] 🟢 `python -m pytest`
- [ ] ❤️ `healthcheck-agent.cmd` after local startup

---

## 🎮 Packaging & Operations

- [ ] 🪄 `windows-bootstrap.ps1` works on a clean Windows environment
- [ ] 🟢 `start-agent.cmd`
- [ ] 🔵 `status-agent.cmd`
- [ ] 🟡 `restart-agent.cmd`
- [ ] 🔴 `stop-agent.cmd`
- [ ] 💾 `backup-agent.cmd` / ♻️ `restore-agent.cmd`
- [ ] 🖥️ `open-agent.cmd` opens admin UI
- [ ] 🌐 Verify `/admin`, `/status`, `/metrics`

---

## 📦 Release Artifacts

| 📁 Artifact | ✅ Ready |
|---|---|
| `README.md` | [ ] |
| `docs/WINDOWS_SETUP_GUIDE.md` | [ ] |
| `CHANGELOG.md` | [ ] |
| `VERSION` | [ ] |
| `LICENSE` | [ ] |
| `NOTICE` | [ ] |

---

<div align="center">

### 🏁 Ship only when every box is green

💎 Quality first · Local safety always

</div>
