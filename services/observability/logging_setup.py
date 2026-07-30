from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from packages.config import Settings

_CONFIGURED = False


def configure_logging(settings: Settings) -> None:
    global _CONFIGURED
    logger = logging.getLogger()
    if _CONFIGURED:
        return

    settings.runtime_log_path.parent.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    file_handler = RotatingFileHandler(
        settings.runtime_log_path,
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.setLevel(settings.log_level.upper())
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    _CONFIGURED = True
