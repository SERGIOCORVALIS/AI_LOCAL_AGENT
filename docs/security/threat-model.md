# Threat Model

## Security Objectives

- Prevent uncontrolled side effects on the local workstation
- Keep secrets out of code, logs, and accidental exports
- Provide a durable audit trail for every meaningful action
- Force explicit approval on sensitive, destructive, or privileged execution

## Primary Risks

- Filesystem damage from autonomous rename, move, or delete actions
- Privilege escalation through shell or UI automation
- Secret leakage through prompts, logs, screenshots, or crash dumps
- Unsafe generated code escaping into the host system without sandboxing
- Memory poisoning through stale or malicious preference capture
- Unauthorized local API misuse if ports are exposed beyond localhost

## Baseline Mitigations

- Policy engine with `observe`, `suggest`, `dry-run`, and `execute` modes
- Approval requirement for sensitive, destructive, and privileged actions
- Append-only audit events for task entry and policy outcomes (secret field redaction)
- Centralized configuration and environment-based secret sourcing
- Sandbox-first execution with explicit `mode` / `isolated` / `degraded` flags
- Optional API token for mutating HTTP routes; Trusted Host middleware
- Docker Compose binds API/Qdrant to `127.0.0.1`; non-root API container user
- Approval channels: Admin UI, CLI, Telegram `/approve` / `/reject`

## Deferred Hardening

- Broad filesystem path allowlist / denylist beyond downloads watch root
- Signed audit exports and integrity validation
- Per-capability kill-switches and circuit breakers
- Public TLS / reverse-proxy termination (intentionally out of local-prod scope)
