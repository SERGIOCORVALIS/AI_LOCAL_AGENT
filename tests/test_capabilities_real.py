from pathlib import Path
from unittest.mock import MagicMock

from pytest import MonkeyPatch

from packages.core import Action, ActionMode
from packages.sandbox import SandboxRequest
from services.channels import ChannelGateway
from services.fs_daemon import FileSystemDaemon
from services.orchestrator.capabilities import CapabilityHandlers, plan_actions_for_goal
from services.sandbox import SandboxExecutor


def test_plan_actions_detects_url_and_workspace() -> None:
    actions = plan_actions_for_goal("fetch https://example.com and index workspace")
    names = {action.name for action in actions}
    assert "web_fetch" in names
    assert "code_intel" in names


def test_plan_actions_extracts_python_c_command() -> None:
    actions = plan_actions_for_goal('run python -c "print(41+1)"')
    sandbox = next(action for action in actions if action.name == "sandbox_run")
    assert sandbox.payload["command"] == ["python", "-c", "print(41+1)"]


def test_plan_actions_detects_fs_watch() -> None:
    actions = plan_actions_for_goal("watch and monitor downloads folder")
    assert any(action.name == "fs_watch" for action in actions)


def test_plan_actions_vision_requires_existing_image(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    without = plan_actions_for_goal("inspect screenshot with vision ocr")
    assert not any(action.name == "vision_inspect" for action in without)

    shots = tmp_path / "runtime" / "screenshots"
    shots.mkdir(parents=True)
    image = shots / "ui.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 24)
    with_image = plan_actions_for_goal("inspect screenshot with vision ocr")
    vision = next(action for action in with_image if action.name == "vision_inspect")
    assert vision.payload.get("path")


def test_plan_actions_browser_requires_url() -> None:
    actions = plan_actions_for_goal("open browser with playwright")
    assert not any(action.name == "browser_open" for action in actions)
    with_url = plan_actions_for_goal("navigate https://example.com with playwright")
    assert any(action.name == "browser_open" for action in with_url)


def test_capability_sandbox_and_reflect(tmp_path: Path) -> None:
    handlers = CapabilityHandlers(
        downloads_watch_path=tmp_path,
        prefer_docker=False,
        ollama_client=None,
    )
    sandbox_result = handlers.sandbox_run(
        Action(
            name="sandbox_run",
            description="run",
            mode=ActionMode.EXECUTE,
            payload={"command": ["python", "-c", "print('ok')"], "language": "python"},
        )
    )
    reflect_result = handlers.reflect(
        Action(
            name="reflect",
            description="think",
            payload={"goal": "improve memory"},
        ),
        memory_snippets=["style:strict"],
    )
    assert sandbox_result.success is True
    assert "ok" in sandbox_result.message
    assert sandbox_result.observations[0].details["mode"] == "local"
    assert reflect_result.success is True
    assert (
        "Ollama недоступен" in reflect_result.message
        or "Memory context items=1" in reflect_result.message
    )
    assert reflect_result.observations[0].details["backend"] == "local"
    assert reflect_result.observations[0].details["degraded"] is True


def test_sandbox_executor_scrubs_and_runs_locally() -> None:
    result = SandboxExecutor(prefer_docker=False).execute(
        SandboxRequest(
            command=["python", "-c", "print('isolated')"],
            language="python",
            allow_network=False,
        )
    )
    assert result.success is True
    assert "isolated" in result.stdout


def test_sandbox_falls_back_when_docker_missing(monkeypatch: MonkeyPatch) -> None:
    executor = SandboxExecutor(prefer_docker=True)
    monkeypatch.setattr(executor, "_docker_available", lambda: False)
    result = executor.execute(
        SandboxRequest(
            command=["python", "-c", "print('local-fallback')"],
            language="python",
            prefer_docker=True,
        )
    )
    assert result.success is True
    assert "local-fallback" in result.stdout
    assert result.mode == "local"
    assert result.degraded is True
    assert result.isolated is False


def test_channel_gateway_persists_approvals(tmp_path: Path) -> None:
    gateway = ChannelGateway(approval_log_path=tmp_path / "approvals.jsonl")
    saved = gateway.record_approval("task-1", "admin", True)
    listed = gateway.list_approvals()
    assert saved.approved is True
    assert listed[0].task_id == "task-1"


def test_fs_daemon_recursive_scan(tmp_path: Path) -> None:
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    (nested / "photo.jpg").write_bytes(b"jpg")
    records = FileSystemDaemon().scan_directory(tmp_path, recursive=True)
    assert any(record.category == "images" for record in records)


def test_capability_fs_watch_uses_adapter(tmp_path: Path) -> None:
    watchdog = MagicMock()
    watchdog.start.return_value = True
    watchdog.poll_once.return_value = [{"event_type": "created"}]
    watchdog.watch_path = tmp_path
    handlers = CapabilityHandlers(
        downloads_watch_path=tmp_path,
        prefer_docker=False,
        watchdog=watchdog,
        ollama_client=None,
    )
    result = handlers.fs_watch(
        Action(name="fs_watch", description="watch", payload={"seconds": 0.1})
    )
    assert result.success is True
    assert result.observations[0].details["events"] == [{"event_type": "created"}]


def test_resolve_existing_image_path_does_not_create_placeholder(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    from services.orchestrator import capabilities as caps

    monkeypatch.chdir(tmp_path)
    assert caps._resolve_existing_image_path(None) is None
    assert not (tmp_path / "runtime" / "screenshots" / "latest.png").exists()


def test_extract_image_path_picks_newest_screenshot(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    from services.orchestrator import capabilities as caps

    monkeypatch.chdir(tmp_path)
    shots = tmp_path / "runtime" / "screenshots"
    shots.mkdir(parents=True)
    older = shots / "old.png"
    newer = shots / "new.png"
    older.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 24)
    newer.write_bytes(b"\x89PNG\r\n\x1a\n" + b"1" * 24)
    resolved = caps._extract_image_path("please run vision ocr")
    assert resolved is not None
    assert resolved.endswith("new.png")
