from __future__ import annotations

import threading
import time
from importlib.util import find_spec
from pathlib import Path
from typing import Any


class WatchdogAdapter:
    """Watchdog-backed filesystem event collector."""

    def __init__(self, watch_path: Path) -> None:
        self._watch_path = watch_path
        self._events: list[dict[str, Any]] = []
        self._observer: Any | None = None
        self._lock = threading.Lock()

    @property
    def watch_path(self) -> Path:
        return self._watch_path

    def is_available(self) -> bool:
        return find_spec("watchdog") is not None

    def start(self) -> bool:
        if not self.is_available():
            return False
        if self._observer is not None:
            return True

        from watchdog.events import FileSystemEventHandler  # type: ignore[import-not-found]
        from watchdog.observers import Observer  # type: ignore[import-not-found]

        adapter = self

        class Handler(FileSystemEventHandler):  # type: ignore[misc]
            def on_any_event(self, event: Any) -> None:  # noqa: N802
                with adapter._lock:
                    adapter._events.append(
                        {
                            "event_type": getattr(event, "event_type", "unknown"),
                            "src_path": str(getattr(event, "src_path", "")),
                            "is_directory": bool(getattr(event, "is_directory", False)),
                            "timestamp": time.time(),
                        }
                    )

        self._watch_path.mkdir(parents=True, exist_ok=True)
        observer = Observer()
        observer.schedule(Handler(), str(self._watch_path), recursive=True)
        observer.start()
        self._observer = observer
        return True

    def stop(self) -> None:
        if self._observer is None:
            return
        self._observer.stop()
        self._observer.join(timeout=5)
        self._observer = None

    def drain_events(self) -> list[dict[str, Any]]:
        with self._lock:
            events = list(self._events)
            self._events.clear()
            return events

    def poll_once(self, timeout_seconds: float = 0.5) -> list[dict[str, Any]]:
        started = self.start()
        if not started:
            return []
        time.sleep(timeout_seconds)
        return self.drain_events()
