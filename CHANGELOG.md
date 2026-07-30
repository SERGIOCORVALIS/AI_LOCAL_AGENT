# Changelog

## 0.2.0 - 2026-07-30

- Added Windows bootstrap and management scripts for install, start, stop, restart, status, logs, open, healthcheck, backup, restore, update, and env setup.
- Added Docker-first local operations guidance for Windows users.
- Added memory pagination/filtering and backend abstraction via `MemoryBackend`.
- Added `/metrics`, `/tasks/recent`, and `/admin` endpoints for local observability and administration.
- Added runtime log path, backup directory, admin UI title, and execute allowlist configuration.
- Added audit redaction for common secret fields and local execute allowlist protection.
