# Release Checklist

## Before Release

- Confirm `VERSION` is updated.
- Update `CHANGELOG.md` with user-visible changes.
- Verify `LICENSE` and `NOTICE` are present.
- Verify `.env.example` contains all required settings.

## Quality Gates

- Run `python -m ruff check .`
- Run `python -m mypy .`
- Run `python -m pytest`
- Run `healthcheck-agent.cmd` after local startup

## Packaging and Operations

- Verify `windows-bootstrap.ps1` works on a clean Windows environment.
- Verify `start-agent.cmd`, `status-agent.cmd`, `restart-agent.cmd`, and `stop-agent.cmd`.
- Verify `backup-agent.cmd` and `restore-agent.cmd`.
- Verify `open-agent.cmd` opens the admin UI.
- Verify `http://127.0.0.1:8000/admin`, `/status`, and `/metrics`.

## Release Artifacts

- Include `README.md`
- Include `docs/WINDOWS_SETUP_GUIDE.md`
- Include `CHANGELOG.md`
- Include `VERSION`
- Include `LICENSE` and `NOTICE`
