from __future__ import annotations

from importlib.util import find_spec

import httpx


class TelegramAdapter:
    """Token-aware Telegram adapter with Bot API send helpers."""

    def __init__(self, token: str | None, admin_chat_id: str | None) -> None:
        self._token = (token or "").strip() or None
        self._admin_chat_id = (admin_chat_id or "").strip() or None
        self._client = httpx.Client(timeout=15.0)

    def is_configured(self) -> bool:
        return bool(self._token and self._admin_chat_id)

    def is_available(self) -> bool:
        if find_spec("aiogram") is None:
            return False
        return self.is_configured()

    def is_authorized(self, chat_id: str | int | None) -> bool:
        if not self.is_configured() or chat_id is None:
            return False
        return str(chat_id).strip() == str(self._admin_chat_id)

    def send_message(self, chat_id: str | int, text: str) -> dict[str, object]:
        if not self._token:
            raise RuntimeError("Telegram bot token is not configured.")
        response = self._client.post(
            f"https://api.telegram.org/bot{self._token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or not payload.get("ok"):
            raise RuntimeError(f"Telegram API error: {payload}")
        return {str(key): value for key, value in payload.items()}

    def send_chat_action(
        self,
        chat_id: str | int,
        action: str = "typing",
    ) -> dict[str, object]:
        """Show Telegram client UX (typing / upload_*) while the agent works."""
        if not self._token:
            raise RuntimeError("Telegram bot token is not configured.")
        response = self._client.post(
            f"https://api.telegram.org/bot{self._token}/sendChatAction",
            json={"chat_id": chat_id, "action": action},
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or not payload.get("ok"):
            raise RuntimeError(f"Telegram API error: {payload}")
        return {str(key): value for key, value in payload.items()}

    def notify_admin(self, text: str) -> dict[str, object]:
        if not self._admin_chat_id:
            raise RuntimeError("Telegram admin chat id is not configured.")
        return self.send_message(self._admin_chat_id, text)
