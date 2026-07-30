from pathlib import Path

from packages.config import Settings
from packages.core import Action, ActionMode, Task
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
    assert len(result.observations) == 3
    assert runtime.resume_task(str(task.id)) is not None


def test_runtime_requires_approval_for_destructive_execute() -> None:
    runtime = OrchestratorRuntime(
        Settings(
            audit_log_path=Path("runtime/test-audit.jsonl"),
            task_store_path=Path("runtime/test-state.json"),
            memory_store_path=Path("runtime/test-memory.json"),
        )
    )
    task = Task(
        title="Cleanup",
        goal="Delete files",
        actions=[
            Action(
                name="delete-files",
                description="Remove files",
                mode=ActionMode.EXECUTE,
                side_effects=["delete"],
            )
        ],
    )

    result = runtime.run_task(task)

    assert result.success is False
    assert result.policy_decision is not None
    assert result.policy_decision.required_approval is True
