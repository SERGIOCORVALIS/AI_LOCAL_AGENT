from __future__ import annotations

from importlib.util import find_spec
from pathlib import Path


class WatchdogAdapter:
    """Thin boundary for a future Watchdog-backed daemon."""

    def __init__(self, watch_path: Path) -> None:
        self._watch_path = watch_path

    @property
    def watch_path(self) -> Path:
        return self._watch_path

    def is_available(self) -> bool:
        return find_spec("watchdog") is not None
