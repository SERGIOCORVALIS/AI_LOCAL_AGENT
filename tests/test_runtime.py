from pathlib import Path

from packages.config import Settings
from packages.core import Action, ActionMode, Task, TaskState
from services.orchestrator import OrchestratorRuntime


def test_runtime_executes_task() -> None:
    runtime = OrchestratorRuntime(
        Settings(
            audit_log_path=Path("runtime/test-audit.jsonl"),
            task_store_path=Path("runtime/test-state.json"),
            memory_store_path=Path("runtime/test-memory.json"),
        )
    )
    task = Task(title="Runtime", goal="Exercise runtime")

    result = runtime.run_task(task)

    assert result.success is True
    assert task.state == "succeeded"
    assert len(result.observations) >= 2
    assert runtime.resume_task(str(task.id)) is not None


def test_runtime_pauses_for_approval_then_continues(tmp_path: Path) -> None:
    runtime = OrchestratorRuntime(
        Settings(
            audit_log_path=tmp_path / "audit.jsonl",
            task_store_path=tmp_path / "state.json",
            memory_store_path=tmp_path / "memory.json",
            backup_dir=tmp_path / "backups",
        )
    )
    task = Task(
        title="Cleanup",
        goal="Delete files",
        actions=[
            Action(
                name="noop",
                description="Remove files",
                mode=ActionMode.EXECUTE,
                side_effects=["delete"],
            )
        ],
    )

    paused = runtime.run_task(task)
    assert paused.success is False
    assert paused.policy_decision is not None
    assert paused.policy_decision.required_approval is True
    assert task.state == TaskState.AWAITING_APPROVAL

    continued = runtime.continue_task(str(task.id), approved=True, reviewer="tester")
    assert continued.success is True
    stored = runtime.resume_task(str(task.id))
    assert stored is not None
    assert stored.state == TaskState.SUCCEEDED


def test_runtime_denies_hard_blocked_action(tmp_path: Path) -> None:
    runtime = OrchestratorRuntime(
        Settings(
            audit_log_path=tmp_path / "audit-deny.jsonl",
            task_store_path=tmp_path / "state-deny.json",
            memory_store_path=tmp_path / "memory-deny.json",
            backup_dir=tmp_path / "backups-deny",
        )
    )
    task = Task(
        title="Denied",
        goal="Wipe",
        actions=[
            Action(
                name="format_disk",
                description="wipe",
                mode=ActionMode.EXECUTE,
                side_effects=["delete"],
            )
        ],
    )
    result = runtime.run_task(task)
    assert result.success is False
    assert result.policy_decision is not None
    assert result.policy_decision.verdict.value == "deny"
    assert task.state == TaskState.FAILED


def test_runtime_rejects_unapproved_continue(tmp_path: Path) -> None:
    runtime = OrchestratorRuntime(
        Settings(
            audit_log_path=tmp_path / "audit-rej.jsonl",
            task_store_path=tmp_path / "state-rej.json",
            memory_store_path=tmp_path / "memory-rej.json",
            backup_dir=tmp_path / "backups-rej",
        )
    )
    task = Task(
        title="Reject",
        goal="Delete",
        actions=[
            Action(
                name="noop",
                description="Remove files",
                mode=ActionMode.EXECUTE,
                side_effects=["delete"],
            )
        ],
    )
    runtime.run_task(task)
    result = runtime.continue_task(str(task.id), approved=False, reviewer="tester")
    assert result.success is False
    stored = runtime.resume_task(str(task.id))
    assert stored is not None
    assert stored.state == TaskState.CANCELLED
