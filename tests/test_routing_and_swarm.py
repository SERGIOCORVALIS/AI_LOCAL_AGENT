from packages.core import Action, Task, TaskPriority
from packages.routing import ComplexityTier, TaskRouter
from services.swarm import SwarmCoordinator


def test_router_selects_heavy_path_for_high_complexity_task() -> None:
    task = Task(
        title="Heavy",
        goal="Run a complex workflow",
        priority=TaskPriority.CRITICAL,
        actions=[
            Action(name="a1", description="step"),
            Action(name="a2", description="step"),
            Action(name="a3", description="step"),
            Action(name="a4", description="step"),
            Action(name="a5", description="step"),
        ],
    )

    decision = TaskRouter().route(task)

    assert decision.tier == ComplexityTier.HEAVY
    assert decision.parallelism == 4
    assert "coder" in decision.assigned_roles


def test_swarm_coordinator_dispatches_roles() -> None:
    task = Task(title="Dispatch", goal="Fan out", actions=[Action(name="noop", description="step")])

    dispatch = SwarmCoordinator().dispatch(task)

    assert dispatch.route.assigned_roles
    assert dispatch.role_outputs
    assert dispatch.observations[0].source == "swarm"
