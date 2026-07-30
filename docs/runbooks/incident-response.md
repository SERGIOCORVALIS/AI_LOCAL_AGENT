# Incident Response Runbook

## Trigger Conditions

- Agent attempts destructive action without explicit approval
- Sandbox execution loops repeatedly fail
- Memory or audit stores become corrupted
- Channel adapters ingest malformed or suspicious payloads

## Immediate Actions

1. Switch the runtime to `observe` or `dry-run` mode.
2. Preserve `runtime/audit` and `runtime/tasks` artifacts.
3. Review the latest task record, audit events, and failing module tests.
4. Disable the affected capability until root cause is understood.
5. If Dockerized services are involved, run `docker compose ps` and `docker compose logs qdrant api` from `infra/`.

## Recovery

1. Re-run `ruff check .`
2. Re-run `python -m mypy .`
3. Re-run `pytest`
4. Restart the Dockerized data path with `docker compose restart qdrant api` when the memory backend is degraded.
5. Restore clean runtime state files if local artifacts are corrupted.

## Exit Criteria

- Quality gates pass
- Failing capability has regression coverage
- Audit trail remains intact
