from pathlib import Path

from services.integrations import (
    PlaywrightAutomationAdapter,
    TelegramAdapter,
    WatchdogAdapter,
)
from services.memory import QdrantMemoryStore


def test_watchdog_adapter_exposes_watch_path() -> None:
    adapter = WatchdogAdapter(Path("C:/temp"))
    assert adapter.watch_path == Path("C:/temp")


def test_telegram_adapter_requires_configuration() -> None:
    adapter = TelegramAdapter(token=None, admin_chat_id=None)
    assert adapter.is_configured() is False


def test_playwright_adapter_reports_availability_flag() -> None:
    assert isinstance(PlaywrightAutomationAdapter().is_available(), bool)


def test_qdrant_memory_store_exposes_collection() -> None:
    store = QdrantMemoryStore(url="http://localhost:6333", collection="agent_memory")
    assert store.collection == "agent_memory"
