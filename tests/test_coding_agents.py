from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from packages.core import Action, ActionMode, Task
from packages.routing import ComplexityTier, TaskRouter
from services.integrations.coding_agents import (
    CodingAgentName,
    CodingAgentsAdapter,
    goal_requests_coding_agent,
)
from services.orchestrator.capabilities import CapabilityHandlers, plan_actions_for_goal


def test_plan_actions_detects_web_search_without_url() -> None:
    actions = plan_actions_for_goal("search for local AI agent frameworks")
    names = [action.name for action in actions]
    assert "web_search" in names
    assert "web_fetch" not in names


def test_plan_actions_detects_coding_agent_and_hint() -> None:
    actions = plan_actions_for_goal("use codex to implement a cache helper")
    coding = [action for action in actions if action.name == "coding_agent"]
    assert coding
    assert coding[0].payload["agent"] == "codex"
    assert coding[0].payload["prompt"]


def test_plan_actions_russian_create_file_uses_write_file() -> None:
    actions = plan_actions_for_goal("создай файл hello.py со скриптом print hello")
    names = [action.name for action in actions]
    assert "write_file" in names
    write = next(action for action in actions if action.name == "write_file")
    assert write.payload["path"] == "hello.py"
    assert "print" in write.payload["content"]
    assert "fs_scan" not in names


def test_plan_actions_internet_keyword_triggers_web_search() -> None:
    actions = plan_actions_for_goal("выйди в интернет и найди pathlib")
    assert any(action.name == "web_search" for action in actions)


def test_goal_requests_coding_agent_keywords() -> None:
    assert goal_requests_coding_agent("please refactor this module")
    assert goal_requests_coding_agent("run droid on the failing tests")
    assert not goal_requests_coding_agent("say hello")


def test_select_agent_prefers_hint_then_default_then_auto() -> None:
    which = MagicMock(side_effect=lambda name: f"C:/{name}.exe" if name != "claude" else None)
    adapter = CodingAgentsAdapter(
        default_agent="opencode",
        enabled=True,
        which=which,
    )
    assert adapter.select_agent("use droid please") == CodingAgentName.DROID
    assert adapter.select_agent("implement feature") == CodingAgentName.OPENCODE
    auto = CodingAgentsAdapter(default_agent="auto", enabled=True, which=which)
    assert auto.select_agent("implement feature") == CodingAgentName.CODEX


def test_select_agent_falls_back_when_preferred_missing() -> None:
    which = MagicMock(side_effect=lambda name: f"C:/{name}.exe" if name == "opencode" else None)
    adapter = CodingAgentsAdapter(default_agent="claude", enabled=True, which=which)
    assert adapter.select_agent("fix bug", preferred="claude") == CodingAgentName.OPENCODE


def test_build_command_shapes() -> None:
    which = MagicMock(side_effect=lambda name: f"C:/{name}.exe")
    adapter = CodingAgentsAdapter(model="gemma4", which=which)
    assert adapter.build_command("codex", "hi")[:5] == [
        "C:/codex.exe",
        "exec",
        "--oss",
        "--local-provider",
        "ollama",
    ]
    assert adapter.build_command("opencode", "hi") == [
        "C:/opencode.exe",
        "run",
        "-m",
        "ollama/gemma4",
        "hi",
    ]
    assert adapter.build_command("droid", "hi") == [
        "C:/droid.exe",
        "exec",
        "--auto",
        "low",
        "-m",
        "gemma4",
        "hi",
    ]
    assert adapter.build_command("claude", "hi") == ["C:/claude.exe", "-p", "hi"]


def test_invoke_success_and_missing_binary() -> None:
    runner = MagicMock(
        return_value=SimpleNamespace(returncode=0, stdout="done", stderr="")
    )
    which = MagicMock(side_effect=lambda name: f"C:/{name}.exe" if name == "codex" else None)
    adapter = CodingAgentsAdapter(enabled=True, which=which, runner=runner, model="gemma4")
    ok = adapter.invoke("codex", "implement foo", cwd=".")
    assert ok.success
    assert ok.stdout == "done"
    runner.assert_called_once()

    missing = adapter.invoke("claude", "hi")
    assert not missing.success
    assert missing.exit_code == 127
    assert "ollama launch claude" in (missing.error or "")


def test_coding_agent_capability_with_mock_adapter(tmp_path) -> None:
    runner = MagicMock(
        return_value=SimpleNamespace(returncode=0, stdout="patched file", stderr="")
    )
    which = MagicMock(return_value="C:/codex.exe")
    adapter = CodingAgentsAdapter(
        enabled=True,
        default_agent="codex",
        which=which,
        runner=runner,
        model="gemma4",
    )
    handlers = CapabilityHandlers(tmp_path, coding_agents=adapter)
    result = handlers.coding_agent(
        Action(
            name="coding_agent",
            description="run",
            mode=ActionMode.EXECUTE,
            payload={"prompt": "implement helper", "cwd": str(tmp_path)},
        )
    )
    assert result.success
    assert "patched file" in result.message


def test_coding_agent_disabled() -> None:
    handlers = CapabilityHandlers(
        __import__("pathlib").Path("."),
        coding_agents=CodingAgentsAdapter(enabled=False),
    )
    result = handlers.coding_agent(
        Action(name="coding_agent", description="run", payload={"prompt": "x"})
    )
    assert not result.success
    assert "disabled" in result.message.lower()


def test_router_boosts_coding_tasks() -> None:
    router = TaskRouter(primary_model="gemma4", router_model="gemma4")
    task = Task(
        title="Fix",
        goal="implement a retry helper",
        actions=[
            Action(
                name="coding_agent",
                description="code",
                mode=ActionMode.EXECUTE,
                payload={"prompt": "implement a retry helper"},
            )
        ],
    )
    decision = router.route(task)
    assert decision.tier in {ComplexityTier.COMPLEX, ComplexityTier.HEAVY}
    assert "coder" in decision.assigned_roles


def test_readiness_payload() -> None:
    which = MagicMock(side_effect=lambda name: "C:/codex.exe" if name == "codex" else None)
    adapter = CodingAgentsAdapter(enabled=True, default_agent="auto", which=which)
    payload = adapter.readiness()
    assert payload["selected"] == "codex"
    assert payload["agents"]["codex"]["installed"] is True
    assert payload["agents"]["claude"]["installed"] is False
    assert "ollama launch" in payload["agents"]["claude"]["launch_hint"]
