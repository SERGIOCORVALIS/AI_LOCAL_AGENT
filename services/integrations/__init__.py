from __future__ import annotations

from typing import Any

from .coding_agents import CodingAgentsAdapter, CodingAgentName, goal_requests_coding_agent
from .playwright_adapter import PlaywrightAutomationAdapter
from .telegram_adapter import TelegramAdapter
from .watchdog_adapter import WatchdogAdapter

__all__ = [
    "CodingAgentName",
    "CodingAgentsAdapter",
    "PlaywrightAutomationAdapter",
    "TelegramAdapter",
    "TelegramBotService",
    "WatchdogAdapter",
    "goal_requests_coding_agent",
    "run_telegram_bot_forever",
]


def __getattr__(name: str) -> Any:
    if name == "TelegramBotService":
        from .telegram_bot import TelegramBotService

        return TelegramBotService
    if name == "run_telegram_bot_forever":
        from .telegram_bot import run_telegram_bot_forever

        return run_telegram_bot_forever
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
