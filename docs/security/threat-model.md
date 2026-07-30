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

## Baseline Mitigations

- Policy engine with `observe`, `suggest`, `dry-run`, and `execute` modes
- Approval requirement for sensitive, destructive, and privileged actions
- Append-only audit events for task entry and policy outcomes
- Centralized configuration and environment-based secret sourcing
- Sandbox-first execution strategy for agent-generated code

## Deferred Hardening

- Path allowlist and denylist enforcement
- Redaction middleware for logs and telemetry
- Signed audit exports and integrity validation
- Per-capability kill-switches and circuit breakers
