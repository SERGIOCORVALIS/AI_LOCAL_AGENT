<div align="center">

# Release Checklist

[![Release](https://img.shields.io/badge/Process-Premium-8B5CF6?style=for-the-badge)](#-before-release)
[![Quality](https://img.shields.io/badge/Gates-Required-EF4444?style=for-the-badge)](#-quality-gates)

> Use this checklist before every public push / tag.

</div>

---

## Before Release

- [ ] Confirm `VERSION` matches `pyproject.toml` and API `/health`
- [ ] Update `CHANGELOG.md` with user-visible changes
- [ ] Verify `LICENSE` and `NOTICE` are present
- [ ] Verify `.env.example` contains all required settings (incl. API token / trusted hosts)
- [ ] Skim `README.md`, `docs/WINDOWS_SETUP_GUIDE.md`, `docs/PRODUCTION.md`

---

## Quality Gates

- [ ] `python -m ruff check .`
- [ ] `python -m mypy .`
- [ ] `python -m pytest`
- [ ] `healthcheck-agent.cmd` after local startup
- [ ] `GET /ready` returns `memory_ok=true`

---

## Packaging & Operations

- [ ] `windows-bootstrap.ps1` works on a clean Windows environment
- [ ] `start-agent.cmd`
- [ ] `status-agent.cmd`
- [ ] `restart-agent.cmd`
- [ ] `stop-agent.cmd`
- [ ] `backup-agent.cmd` / `restore-agent.cmd`
- [ ] `open-agent.cmd` opens admin UI
- [ ] Verify `/admin`, `/status`, `/metrics`, `/ready`
- [ ] With `API_TOKEN` set, mutating POST without token returns `401`
- [ ] Compose ports listen on `127.0.0.1` only

---

## Release Artifacts

| Artifact | Ready |
|---|---|
| `README.md` | [ ] |
| `docs/WINDOWS_SETUP_GUIDE.md` | [ ] |
| `docs/PRODUCTION.md` | [ ] |
| `CHANGELOG.md` | [ ] |
| `VERSION` | [ ] |
| `LICENSE` | [ ] |
| `NOTICE` | [ ] |

---

<div align="center">

### Ship only when every box is green

Quality first · Local safety always

</div>
