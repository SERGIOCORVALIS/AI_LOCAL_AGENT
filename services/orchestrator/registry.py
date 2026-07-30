from __future__ import annotations

from collections.abc import Callable

from packages.core import Action, ActionResult

CapabilityHandler = Callable[[Action], ActionResult]


class CapabilityRegistry:
    """Simple handler registry for capability execution."""

    def __init__(self) -> None:
        self._handlers: dict[str, CapabilityHandler] = {}

    def register(self, action_name: str, handler: CapabilityHandler) -> None:
        self._handlers[action_name] = handler

    def has(self, action_name: str) -> bool:
        return action_name in self._handlers

    def execute(self, action: Action) -> ActionResult:
        handler = self._handlers.get(action.name)
        if handler is None:
            raise KeyError(f"No capability registered for action '{action.name}'.")
        return handler(action)
