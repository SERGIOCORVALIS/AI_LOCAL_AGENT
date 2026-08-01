from pathlib import Path
from unittest.mock import MagicMock

from packages.core import Action, Task, TaskPriority
from packages.routing import ComplexityTier, TaskRouter
from services.llm import OLLAMA_UNAVAILABLE, OllamaClient
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


def test_router_confirms_with_ollama_json() -> None:
    client = MagicMock(spec=OllamaClient)
    client.chat_json.return_value = {
        "tier": "complex",
        "assigned_roles": ["router", "coder", "ops"],
        "reason": "llm override",
    }
    task = Task(
        title="Routed",
        goal="do something moderately long " + ("x" * 50),
        actions=[Action(name="noop", description="step")],
    )
    decision = TaskRouter(ollama_client=client).route(task)
    assert decision.tier == ComplexityTier.COMPLEX
    assert decision.assigned_roles == ["router", "coder", "ops"]
    assert decision.reason == "llm override"
    client.chat_json.assert_called_once()


def test_router_falls_back_when_ollama_unavailable() -> None:
    client = MagicMock(spec=OllamaClient)
    client.chat_json.return_value = None
    task = Task(title="Fallback", goal="hi", actions=[])
    decision = TaskRouter(ollama_client=client).route(task)
    assert "ollama_unavailable fallback" in decision.reason


def test_swarm_coordinator_dispatches_roles() -> None:
    task = Task(
        title="Dispatch",
        goal="Fan out code review",
        actions=[Action(name="noop", description="step")],
    )

    dispatch = SwarmCoordinator().dispatch(task)

    assert dispatch.route.assigned_roles
    assert dispatch.role_outputs
    assert all(":" in item for item in dispatch.role_outputs)
    assert dispatch.observations[0].source == "swarm"


def test_swarm_roles_call_ollama(tmp_path: Path) -> None:
    del tmp_path
    client = MagicMock(spec=OllamaClient)
    client.generate.return_value = "llm finding"
    router = TaskRouter(primary_model="gemma4:primary", router_model="gemma4:router")
    task = Task(
        title="SwarmLLM",
        goal="review this code carefully for risks",
        priority=TaskPriority.HIGH,
        actions=[
            Action(name="a1", description="step"),
            Action(name="a2", description="step"),
            Action(name="a3", description="step"),
        ],
    )
    dispatch = SwarmCoordinator(
        router=router,
        ollama_client=client,
        model="gemma4:primary",
        router_model="gemma4:router",
    ).dispatch(task)
    assert dispatch.role_outputs
    assert all("llm finding" in item for item in dispatch.role_outputs)
    assert client.generate.call_count == len(dispatch.route.assigned_roles)
    role_models = dispatch.observations[0].details["role_models"]
    assert role_models["router"] == "gemma4:router"
    assert role_models["coder"] == "gemma4:primary"


def test_swarm_falls_back_when_ollama_down() -> None:
    client = MagicMock(spec=OllamaClient)
    client.generate.return_value = OLLAMA_UNAVAILABLE
    task = Task(
        title="SwarmDown",
        goal="ops check",
        actions=[Action(name="noop", description="step")],
    )
    dispatch = SwarmCoordinator(ollama_client=client).dispatch(task)
    assert any(OLLAMA_UNAVAILABLE in item for item in dispatch.role_outputs)
