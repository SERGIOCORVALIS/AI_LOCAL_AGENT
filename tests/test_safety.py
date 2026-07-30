import json
from pathlib import Path

from packages.core import Action, ActionMode
from packages.safety import (
    ActionSensitivity,
    AuditEvent,
    AuditLogger,
    PolicyEngine,
)


def test_policy_engine_classifies_destructive_actions() -> None:
    policy = PolicyEngine()
    action = Action(
        name="cleanup",
        description="Delete temporary files",
        mode=ActionMode.EXECUTE,
        side_effects=["delete"],
    )

    assert policy.classify(action) == ActionSensitivity.DESTRUCTIVE
    decision = policy.evaluate(action)
    assert decision.required_approval is True


def test_policy_engine_enforces_execute_allowlist() -> None:
    policy = PolicyEngine(allowed_execute_actions={"noop"})
    action = Action(
        name="shell",
        description="Run shell command",
        mode=ActionMode.EXECUTE,
    )

    decision = policy.evaluate(action)

    assert decision.required_approval is True
    assert "allowlist" in decision.tags


def test_audit_logger_writes_jsonl(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    logger = AuditLogger(audit_path)
    event = AuditEvent(
        event_type="task.started",
        actor="tester",
        summary="Audit event created",
    )

    logger.write(event)

    stored = audit_path.read_text(encoding="utf-8").strip()
    payload = json.loads(stored)
    assert payload["event_type"] == "task.started"
    assert payload["actor"] == "tester"


def test_audit_logger_redacts_sensitive_fields(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    logger = AuditLogger(audit_path)
    event = AuditEvent(
        event_type="secret.checked",
        actor="tester",
        summary="Secrets were processed",
        details={
            "token": "raw-secret",
            "nested": {"api_key": "raw-key"},
        },
    )

    logger.write(event)

    payload = json.loads(audit_path.read_text(encoding="utf-8").strip())
    assert payload["details"]["token"] == "***REDACTED***"
    assert payload["details"]["nested"]["api_key"] == "***REDACTED***"
