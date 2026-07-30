from packages.core import (
    Action,
    ActionMode,
    Artifact,
    ArtifactKind,
    PolicyDecision,
    PolicyVerdict,
    Task,
)


def test_task_state_transitions() -> None:
    task = Task(title="Bootstrap", goal="Create a foundational runtime")
    assert task.state == "pending"

    task.mark_running()
    assert task.state == "running"

    task.mark_succeeded()
    assert task.state == "succeeded"


def test_action_and_policy_models_are_typed() -> None:
    action = Action(
        name="scan",
        description="Inspect workspace",
        mode=ActionMode.DRY_RUN,
    )
    artifact = Artifact(kind=ArtifactKind.REPORT, name="workspace-report")
    decision = PolicyDecision(
        verdict=PolicyVerdict.REQUIRE_APPROVAL,
        reason="Filesystem write requested",
        required_approval=True,
    )

    assert action.mode == ActionMode.DRY_RUN
    assert artifact.kind == ArtifactKind.REPORT
    assert decision.required_approval is True
