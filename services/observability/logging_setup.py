from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from typing import Any

from packages.config import Settings

_CONFIGURED = False
_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> str | None:
    return _correlation_id.get()


def set_correlation_id(value: str | None) -> None:
    _correlation_id.set(value)


def clear_correlation_id() -> None:
    _correlation_id.set(None)


class CorrelationFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id() or "-"
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", "-"),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


def configure_logging(settings: Settings) -> None:
    global _CONFIGURED
    logger = logging.getLogger()
    if _CONFIGURED:
        return

    settings.runtime_log_path.parent.mkdir(parents=True, exist_ok=True)
    correlation_filter = CorrelationFilter()

    if settings.is_prod:
        formatter: logging.Formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s [cid=%(correlation_id)s] %(message)s",
        )

    file_handler = RotatingFileHandler(
        settings.runtime_log_path,
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(correlation_filter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(correlation_filter)

    logger.setLevel(settings.log_level.upper())
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    _CONFIGURED = True
