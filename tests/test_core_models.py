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


def test_task_awaiting_approval_transition() -> None:
    from packages.core import Observation

    task = Task(title="Approve", goal="Needs human")
    task.mark_awaiting_approval(
        Observation(source="policy", summary="paused"),
        action_index=0,
    )
    assert task.state == "awaiting_approval"
    assert task.resume_from_index == 0


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
