from __future__ import annotations

import base64
import json
import time
from pathlib import Path
from typing import Any

import httpx

from services.llm.models import model_is_available, resolve_model_name

OLLAMA_UNAVAILABLE = "ollama_unavailable"


class OllamaClient:
    """HTTP client for local Ollama chat/generate APIs."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        client: httpx.Client | None = None,
        timeout: float = 60.0,
        ping_ttl_seconds: float = 15.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        # Windows system proxy env can make localhost Ollama return 503 via httpx.
        self._client = client or httpx.Client(timeout=timeout, trust_env=False)
        self._ping_cache: bool | None = None
        self._ping_checked_at = 0.0
        self._ping_ttl_seconds = ping_ttl_seconds

    @property
    def base_url(self) -> str:
        return self._base_url

    def ping(self) -> bool:
        now = time.monotonic()
        if (
            self._ping_cache is not None
            and (now - self._ping_checked_at) < self._ping_ttl_seconds
        ):
            return self._ping_cache
        try:
            response = self._client.get(f"{self._base_url}/api/tags")
        except httpx.HTTPError:
            self._ping_cache = False
            self._ping_checked_at = now
            return False
        self._ping_cache = response.is_success
        self._ping_checked_at = now
        return self._ping_cache

    def invalidate_ping(self) -> None:
        self._ping_cache = None
        self._ping_checked_at = 0.0

    def list_models(self) -> list[str]:
        """Return installed Ollama model names, or empty list if offline."""
        try:
            response = self._client.get(f"{self._base_url}/api/tags")
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError, TypeError):
            self._ping_cache = False
            return []
        self._ping_cache = True
        models = payload.get("models", [])
        names: list[str] = []
        if isinstance(models, list):
            for item in models:
                if isinstance(item, dict):
                    name = str(item.get("name", "")).strip()
                    if name:
                        names.append(name)
        return names

    def resolve_model(self, requested: str) -> str | None:
        """Return an installed tag matching ``requested``, or None."""
        return resolve_model_name(requested, self.list_models())

    def has_model(self, requested: str) -> bool:
        return model_is_available(requested, self.list_models())

    def generate(self, model: str, prompt: str) -> str:
        self.invalidate_ping()
        if not self.ping():
            return OLLAMA_UNAVAILABLE
        try:
            response = self._client.post(
                f"{self._base_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
            )
            response.raise_for_status()
            payload = response.json()
            return str(payload.get("response", "")).strip() or OLLAMA_UNAVAILABLE
        except (httpx.HTTPError, ValueError, KeyError):
            self.invalidate_ping()
            return OLLAMA_UNAVAILABLE

    def chat(self, model: str, messages: list[dict[str, str]]) -> str:
        self.invalidate_ping()
        if not self.ping():
            return OLLAMA_UNAVAILABLE
        try:
            response = self._client.post(
                f"{self._base_url}/api/chat",
                json={"model": model, "messages": messages, "stream": False},
            )
            response.raise_for_status()
            payload = response.json()
            message = payload.get("message", {})
            if isinstance(message, dict):
                content = str(message.get("content", "")).strip()
                return content or OLLAMA_UNAVAILABLE
            return OLLAMA_UNAVAILABLE
        except (httpx.HTTPError, ValueError, KeyError):
            self.invalidate_ping()
            return OLLAMA_UNAVAILABLE

    def generate_with_image(
        self,
        model: str,
        prompt: str,
        image_path: Path,
    ) -> str:
        if not image_path.exists():
            return OLLAMA_UNAVAILABLE
        if not self.ping():
            return OLLAMA_UNAVAILABLE
        encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
        try:
            response = self._client.post(
                f"{self._base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "images": [encoded],
                    "stream": False,
                },
            )
            response.raise_for_status()
            payload = response.json()
            return str(payload.get("response", "")).strip() or OLLAMA_UNAVAILABLE
        except (httpx.HTTPError, ValueError, KeyError):
            return OLLAMA_UNAVAILABLE

    def embed(self, model: str, text: str) -> list[float] | None:
        if not text.strip():
            return None
        if not self.ping():
            return None
        try:
            response = self._client.post(
                f"{self._base_url}/api/embeddings",
                json={"model": model, "prompt": text},
            )
            response.raise_for_status()
            payload = response.json()
            vector = payload.get("embedding")
            if not isinstance(vector, list) or not vector:
                return None
            return [float(value) for value in vector]
        except (httpx.HTTPError, ValueError, TypeError):
            return None

    def chat_json(self, model: str, prompt: str) -> dict[str, Any] | None:
        raw = self.chat(
            model,
            [
                {
                    "role": "system",
                    "content": "Reply with valid JSON only. No markdown.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        if raw == OLLAMA_UNAVAILABLE:
            return None
        try:
            start = raw.find("{")
            end = raw.rfind("}")
            if start < 0 or end <= start:
                return None
            payload = json.loads(raw[start : end + 1])
            return payload if isinstance(payload, dict) else None
        except json.JSONDecodeError:
            return None
