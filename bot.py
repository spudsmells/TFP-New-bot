"""The Gayborhood Bot — Entry point."""
from __future__ import annotations

import asyncio
import logging
import sys

from core.bot import GayborhoodBot
from core.config import Config
from core.constants import BOT_NAME, VERSION

# ── Logging Setup ─────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
# Quiet noisy libraries
logging.getLogger("discord").setLevel(logging.WARNING)
logging.getLogger("discord.http").setLevel(logging.WARNING)
logging.getLogger("aiosqlite").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def main() -> None:
    logger.info("Starting %s v%s", BOT_NAME, VERSION)

    config = Config()
    bot = GayborhoodBot(config)

    async with bot:
        await bot.start(config.token)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down via KeyboardInterrupt")
