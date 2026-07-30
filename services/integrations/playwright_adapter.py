from __future__ import annotations

from importlib.util import find_spec


class PlaywrightAutomationAdapter:
    """Availability guard for future UI/browser automation."""

    def is_available(self) -> bool:
        return find_spec("playwright") is not None
