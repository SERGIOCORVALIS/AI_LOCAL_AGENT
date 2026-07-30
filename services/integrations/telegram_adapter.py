from __future__ import annotations

from importlib.util import find_spec


class TelegramAdapter:
    """Token-aware adapter boundary for a future aiogram bot."""

    def __init__(self, token: str | None, admin_chat_id: str | None) -> None:
        self._token = token
        self._admin_chat_id = admin_chat_id

    def is_configured(self) -> bool:
        return bool(self._token and self._admin_chat_id)

    def is_available(self) -> bool:
        if find_spec("aiogram") is None:
            return False
        return self.is_configured()
