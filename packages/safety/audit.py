from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from packages.core.models import utc_now


class AuditEvent(BaseModel):
    event_type: str
    actor: str
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())


class AuditLogger:
    """Append-only JSONL audit sink."""

    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    def write(self, event: AuditEvent) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        redacted_event = event.model_copy(
            update={
                "details": redact_sensitive_data(event.details),
            }
        )
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(redacted_event.model_dump(), ensure_ascii=True) + "\n"
            )


def redact_sensitive_data(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: (
                "***REDACTED***"
                if _is_sensitive_key(key)
                else redact_sensitive_data(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive_data(item) for item in value]
    return value


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    sensitive_markers = (
        "token",
        "secret",
        "password",
        "api_key",
        "private_key",
    )
    return any(marker in lowered for marker in sensitive_markers)
