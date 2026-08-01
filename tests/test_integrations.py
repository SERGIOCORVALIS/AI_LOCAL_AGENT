from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from pytest import MonkeyPatch

from packages.config import Settings
from packages.core import Action
from services.integrations import (
    PlaywrightAutomationAdapter,
    TelegramAdapter,
    WatchdogAdapter,
)
from services.integrations.telegram_bot import TelegramBotService, split_telegram_text
from services.memory import QdrantMemoryStore
from services.orchestrator.capabilities import CapabilityHandlers


def test_watchdog_adapter_exposes_watch_path() -> None:
    adapter = WatchdogAdapter(Path("C:/temp"))
    assert adapter.watch_path == Path("C:/temp")


def test_watchdog_adapter_start_drain_with_temp_dir(tmp_path: Path) -> None:
    adapter = WatchdogAdapter(tmp_path)
    if not adapter.is_available():
        assert adapter.start() is False
        assert adapter.drain_events() == []
        return
    assert adapter.start() is True
    assert adapter.start() is True  # idempotent
    (tmp_path / "watched.txt").write_text("hello", encoding="utf-8")
    events = adapter.poll_once(timeout_seconds=0.4)
    adapter.stop()
    assert isinstance(events, list)


def test_telegram_adapter_requires_configuration() -> None:
    adapter = TelegramAdapter(token=None, admin_chat_id=None)
    assert adapter.is_configured() is False
    assert adapter.is_authorized("1") is False


def test_telegram_adapter_notify_admin_uses_send_message() -> None:
    adapter = TelegramAdapter(token="123:abc", admin_chat_id="42")
    with patch.object(adapter, "send_message", return_value={"ok": True}) as send:
        payload = adapter.notify_admin("task done")
    assert payload["ok"] is True
    send.assert_called_once_with("42", "task done")


def test_telegram_adapter_send_message_posts_json() -> None:
    adapter = TelegramAdapter(token="123:abc", admin_chat_id="42")
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {"ok": True, "result": {"message_id": 1}}
    with patch.object(adapter._client, "post", return_value=response) as post:  # noqa: SLF001
        payload = adapter.send_message("42", "hello")
    assert payload["ok"] is True
    post.assert_called_once()


def test_telegram_adapter_send_chat_action() -> None:
    adapter = TelegramAdapter(token="123:abc", admin_chat_id="42")
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {"ok": True, "result": True}
    with patch.object(adapter._client, "post", return_value=response) as post:  # noqa: SLF001
        payload = adapter.send_chat_action("42", "typing")
    assert payload["ok"] is True
    assert post.call_args.args[0].endswith("/sendChatAction")


def test_split_telegram_text_chunks_long_replies() -> None:
    short = split_telegram_text("hello")
    assert short == ["hello"]
    long = "x" * 8500
    chunks = split_telegram_text(long, limit=4000)
    assert len(chunks) == 3
    assert "".join(chunks) == long


def test_telegram_bot_service_handles_help_for_admin() -> None:
    settings = Settings(
        telegram_bot_token="123:abc",
        telegram_admin_chat_id="42",
        qdrant_url="http://localhost:6333",
        runtime_log_path=Path("runtime/logs/agent-test.log"),
        audit_log_path=Path("runtime/audit/events-test.jsonl"),
        task_store_path=Path("runtime/tasks/state-test.json"),
        memory_store_path=Path("runtime/memory/preferences-test.json"),
        backup_dir=Path("backups-test"),
    )
    service = TelegramBotService(settings=settings)
    reply = service.handle_text("42", "/help")
    assert "Commands" in reply
    assert "/approve" in reply
    denied = service.handle_text("99", "hello")
    assert "Access denied" in denied


def test_telegram_approve_and_reject_commands() -> None:
    settings = Settings(
        telegram_bot_token="123:abc",
        telegram_admin_chat_id="42",
        qdrant_url="http://localhost:6333",
        runtime_log_path=Path("runtime/logs/agent-approve.log"),
        audit_log_path=Path("runtime/audit/events-approve.jsonl"),
        task_store_path=Path("runtime/tasks/state-approve.json"),
        memory_store_path=Path("runtime/memory/preferences-approve.json"),
        backup_dir=Path("backups-approve"),
    )
    runtime = MagicMock()
    runtime.continue_task.return_value = MagicMock(success=True, message="resumed")
    service = TelegramBotService(settings=settings, runtime=runtime)
    assert "Usage" in service.handle_text("42", "/approve")
    approved = service.handle_text("42", "/approve task-123")
    assert "approved" in approved
    runtime.continue_task.assert_called_with(
        "task-123", approved=True, reviewer="telegram"
    )
    rejected = service.handle_text("42", "/reject task-123")
    assert "rejected" in rejected
    runtime.continue_task.assert_called_with(
        "task-123", approved=False, reviewer="telegram"
    )


def test_telegram_bot_service_runs_task_for_admin_text() -> None:
    settings = Settings(
        telegram_bot_token="123:abc",
        telegram_admin_chat_id="42",
        qdrant_url="http://localhost:6333",
        runtime_log_path=Path("runtime/logs/agent-tg.log"),
        audit_log_path=Path("runtime/audit/events-tg.jsonl"),
        task_store_path=Path("runtime/tasks/state-tg.json"),
        memory_store_path=Path("runtime/memory/preferences-tg.json"),
        backup_dir=Path("backups-tg"),
        allowed_execute_actions_raw=(
            "bootstrap,noop,reflect,sandbox_run,web_fetch,web_search,"
            "coding_agent,code_intel,fs_scan,fs_watch,vision_inspect,browser_open"
        ),
    )
    service = TelegramBotService(settings=settings)
    with patch.object(service.adapter, "notify_admin", return_value={"ok": True}) as notify:
        start_reply = service.handle_text("42", "/start")
        status_reply = service.handle_text("42", "/status")
        task_reply = service.handle_text("42", "summarize workspace")
    assert "online" in start_reply.lower()
    assert "model_primary=" in status_reply
    assert "[telegram] ok" in task_reply
    assert "summarize workspace" in task_reply
    notify.assert_called()
    assert "summarize workspace" in notify.call_args.args[0]


def test_telegram_notify_admin_on_task_finish() -> None:
    settings = Settings(
        telegram_bot_token="123:abc",
        telegram_admin_chat_id="42",
        runtime_log_path=Path("runtime/logs/agent-tg-notify.log"),
        audit_log_path=Path("runtime/audit/events-tg-notify.jsonl"),
        task_store_path=Path("runtime/tasks/state-tg-notify.json"),
        memory_store_path=Path("runtime/memory/preferences-tg-notify.json"),
        backup_dir=Path("backups-tg-notify"),
    )
    service = TelegramBotService(settings=settings)
    with patch.object(service.adapter, "notify_admin", return_value={"ok": True}) as notify:
        with patch.object(service.adapter, "send_message", return_value={"ok": True}):
            reply = service.handle_text("42", "say hello quietly")
    assert "[telegram]" in reply
    notify.assert_called_once()
    assert "Agent:" in notify.call_args.args[0]


def test_telegram_handle_voice_file_runs_stt_then_task(tmp_path: Path) -> None:
    settings = Settings(
        telegram_bot_token="123:abc",
        telegram_admin_chat_id="42",
        runtime_log_path=tmp_path / "agent-voice.log",
        audit_log_path=tmp_path / "events-voice.jsonl",
        task_store_path=tmp_path / "state-voice.json",
        memory_store_path=tmp_path / "preferences-voice.json",
        backup_dir=tmp_path / "backups-voice",
    )
    audio = tmp_path / "note.ogg"
    audio.write_bytes(b"OggS")
    service = TelegramBotService(settings=settings)
    with (
        patch.object(
            service._gateway,  # noqa: SLF001
            "ingest_voice",
            return_value=MagicMock(transcript="summarize workspace", source="stt"),
        ) as ingest,
        patch.object(service, "handle_text", return_value="[telegram] ok") as handle_text,
    ):
        reply = service.handle_voice_file("42", audio, duration_seconds=1.2)
    assert reply == "[telegram] ok"
    ingest.assert_called_once()
    handle_text.assert_called_once_with("42", "summarize workspace", notify=True)


def test_telegram_handle_voice_file_reports_stt_unavailable(tmp_path: Path) -> None:
    from services.perception.stt import STT_UNAVAILABLE

    settings = Settings(
        telegram_bot_token="123:abc",
        telegram_admin_chat_id="42",
        runtime_log_path=tmp_path / "agent-voice2.log",
        audit_log_path=tmp_path / "events-voice2.jsonl",
        task_store_path=tmp_path / "state-voice2.json",
        memory_store_path=tmp_path / "preferences-voice2.json",
        backup_dir=tmp_path / "backups-voice2",
    )
    audio = tmp_path / "note.ogg"
    audio.write_bytes(b"OggS")
    service = TelegramBotService(settings=settings)
    with patch.object(
        service._gateway,  # noqa: SLF001
        "ingest_voice",
        return_value=MagicMock(transcript=STT_UNAVAILABLE, source="stt"),
    ):
        reply = service.handle_voice_file("42", audio)
    assert "Голос не распознан" in reply or "STT" in reply

def test_telegram_bot_service_start_stop_with_mocks() -> None:
    settings = Settings(
        telegram_bot_token="123:abc",
        telegram_admin_chat_id="42",
        runtime_log_path=Path("runtime/logs/agent-tg3.log"),
        audit_log_path=Path("runtime/audit/events-tg3.jsonl"),
        task_store_path=Path("runtime/tasks/state-tg3.json"),
        memory_store_path=Path("runtime/memory/preferences-tg3.json"),
        backup_dir=Path("backups-tg3"),
    )
    service = TelegramBotService(settings=settings)

    async def _run() -> None:
        with (
            patch("services.integrations.telegram_bot.Bot") as bot_cls,
            patch("services.integrations.telegram_bot.Dispatcher") as dp_cls,
        ):
            bot = MagicMock()
            bot.session.close = AsyncMock()
            bot_cls.return_value = bot
            dp = MagicMock()
            dp.start_polling = AsyncMock(side_effect=asyncio.CancelledError())
            dp.message = MagicMock(return_value=lambda handler: handler)
            dp_cls.return_value = dp
            task = service.start_background()
            assert task is not None
            await asyncio.sleep(0.05)
            await service.stop()

    asyncio.run(_run())


def test_capability_handlers_reflect_and_validation(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    handlers = CapabilityHandlers(
        downloads_watch_path=tmp_path / "downloads",
        prefer_docker=False,
        ollama_client=None,
    )
    reflect = handlers.reflect(
        Action(name="reflect", description="think", payload={"goal": "hello"})
    )
    assert reflect.success is True
    assert "hello" in reflect.message
    assert reflect.observations[0].details["backend"] == "local"
    assert reflect.observations[0].details["degraded"] is True
    assert "Ollama недоступен" in reflect.message

    bad_sandbox = handlers.sandbox_run(Action(name="sandbox_run", description="bad"))
    assert bad_sandbox.success is False

    vision = handlers.vision_inspect(Action(name="vision_inspect", description="default"))
    assert vision.success is False
    assert "existing image" in vision.message

    bad_web = handlers.web_fetch(Action(name="web_fetch", description="bad"))
    assert bad_web.success is False

    bad_search = handlers.web_search(Action(name="web_search", description="bad"))
    assert bad_search.success is False

    code = handlers.code_intel(Action(name="code_intel", description="idx", payload={"root": "."}))
    assert code.success is True

    fs = handlers.fs_scan(
        Action(name="fs_scan", description="scan", payload={"root": str(tmp_path / "downloads")})
    )
    assert fs.success is True

    browser = handlers.browser_open(
        Action(name="browser_open", description="open", payload={"url": "https://example.com"})
    )
    assert "success" in browser.model_dump(mode="json") or browser.message

    bad_browser = handlers.browser_open(Action(name="browser_open", description="open"))
    assert bad_browser.success is False


def test_playwright_adapter_reports_availability_flag() -> None:
    adapter = PlaywrightAutomationAdapter()
    assert isinstance(adapter.is_package_available(), bool)
    assert isinstance(adapter.browsers_installed(), bool)
    assert isinstance(adapter.is_available(), bool)


def test_playwright_open_page_hints_missing_browsers() -> None:
    adapter = PlaywrightAutomationAdapter()
    with (
        patch.object(adapter, "is_package_available", return_value=True),
        patch.object(adapter, "browsers_installed", return_value=False),
    ):
        result = adapter.open_page("https://example.com")
    assert result["success"] is False
    assert "hint" in result
    assert "playwright install" in result["hint"]


def test_playwright_ensure_browsers_short_circuits_when_ready() -> None:
    adapter = PlaywrightAutomationAdapter()
    with (
        patch.object(adapter, "is_package_available", return_value=True),
        patch.object(adapter, "browsers_installed", return_value=True),
    ):
        result = adapter.ensure_browsers()
    assert result["success"] is True
    assert result.get("already_installed") is True


def test_playwright_ensure_browsers_without_package() -> None:
    adapter = PlaywrightAutomationAdapter()
    with patch.object(adapter, "is_package_available", return_value=False):
        result = adapter.ensure_browsers()
    assert result["success"] is False
    assert "not installed" in result["summary"]


def test_playwright_ensure_browsers_runs_install() -> None:
    adapter = PlaywrightAutomationAdapter()
    completed = MagicMock(returncode=0, stderr="")
    with (
        patch.object(adapter, "is_package_available", return_value=True),
        patch.object(adapter, "browsers_installed", side_effect=[False, True]),
        patch("subprocess.run", return_value=completed) as run_mock,
    ):
        result = adapter.ensure_browsers()
    assert result["success"] is True
    assert "installed" in result["summary"].lower()
    run_mock.assert_called_once()


def test_playwright_ensure_browsers_reports_install_failure() -> None:
    adapter = PlaywrightAutomationAdapter()
    completed = MagicMock(returncode=1, stderr="boom")
    with (
        patch.object(adapter, "is_package_available", return_value=True),
        patch.object(adapter, "browsers_installed", return_value=False),
        patch("subprocess.run", return_value=completed),
    ):
        result = adapter.ensure_browsers()
    assert result["success"] is False
    assert result["exit_code"] == 1
    assert "boom" in result["summary"]


def test_playwright_open_page_without_package() -> None:
    adapter = PlaywrightAutomationAdapter()
    with patch.object(adapter, "is_package_available", return_value=False):
        result = adapter.open_page("https://example.com")
    assert result["success"] is False
    assert "not installed" in result["summary"]


def test_playwright_open_page_success_and_nav_error(tmp_path: Path) -> None:
    adapter = PlaywrightAutomationAdapter()
    screenshot = tmp_path / "shot.png"

    class FakePage:
        def goto(self, url: str, wait_until: str, timeout: int) -> MagicMock:
            response = MagicMock()
            response.status = 200
            return response

        def title(self) -> str:
            return "Example"

        @property
        def url(self) -> str:
            return "https://example.com/"

        def screenshot(self, path: str, full_page: bool) -> None:
            Path(path).write_bytes(b"png")

    class FakeBrowser:
        def new_page(self) -> FakePage:
            return FakePage()

        def close(self) -> None:
            return None

    class FakeChromium:
        def launch(self, headless: bool) -> FakeBrowser:
            return FakeBrowser()

    class FakePlaywright:
        chromium = FakeChromium()

        def __enter__(self) -> FakePlaywright:
            return self

        def __exit__(self, *args: object) -> None:
            return None

    with (
        patch.object(adapter, "is_package_available", return_value=True),
        patch.object(adapter, "browsers_installed", return_value=True),
        patch("playwright.sync_api.sync_playwright", return_value=FakePlaywright()),
    ):
        ok = adapter.open_page("https://example.com", screenshot_path=screenshot)
    assert ok["success"] is True
    assert ok["title"] == "Example"
    assert ok["screenshot"] == str(screenshot)

    class BoomPlaywright:
        chromium = FakeChromium()

        def __enter__(self) -> BoomPlaywright:
            raise RuntimeError("nav failed")

        def __exit__(self, *args: object) -> None:
            return None

    with (
        patch.object(adapter, "is_package_available", return_value=True),
        patch.object(adapter, "browsers_installed", return_value=True),
        patch("playwright.sync_api.sync_playwright", return_value=BoomPlaywright()),
    ):
        failed = adapter.open_page("https://example.com")
    assert failed["success"] is False
    assert "failed" in failed["summary"].lower()


def test_playwright_browsers_installed_handles_errors() -> None:
    adapter = PlaywrightAutomationAdapter()
    with patch.object(adapter, "is_package_available", return_value=False):
        assert adapter.browsers_installed() is False
    with (
        patch.object(adapter, "is_package_available", return_value=True),
        patch("playwright.sync_api.sync_playwright", side_effect=RuntimeError("x")),
    ):
        assert adapter.browsers_installed() is False


def test_qdrant_memory_store_exposes_collection() -> None:
    store = QdrantMemoryStore(url="http://localhost:6333", collection="agent_memory")
    assert store.collection == "agent_memory"
