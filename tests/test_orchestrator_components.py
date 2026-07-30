from pathlib import Path

from packages.core import Action, ActionResult, Observation, Task
from services.orchestrator import CapabilityRegistry, TaskStore


def test_capability_registry_executes_registered_handler() -> None:
    registry = CapabilityRegistry()

    def handler(action: Action) -> ActionResult:
        return ActionResult(
            action=action,
            success=True,
            message="handled",
            observations=[Observation(source="test", summary="handled")],
        )

    registry.register("inspect", handler)
    result = registry.execute(Action(name="inspect", description="Inspect target"))

    assert result.success is True
    assert result.message == "handled"


def test_task_store_persists_and_loads_task(tmp_path: Path) -> None:
    store = TaskStore(tmp_path / "tasks.json")
    task = Task(title="Persist", goal="Verify resumability")

    store.save(task)
    loaded = store.load(str(task.id))

    assert loaded is not None
    assert loaded.id == task.id
    assert loaded.title == "Persist"
