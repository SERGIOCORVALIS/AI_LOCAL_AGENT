from __future__ import annotations

import asyncio

from packages.config import load_settings
from services.integrations.telegram_bot import run_telegram_bot_forever


def main() -> None:
    settings = load_settings()
    asyncio.run(run_telegram_bot_forever(settings))


if __name__ == "__main__":
    main()
