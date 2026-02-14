from __future__ import annotations

import logging
import time
from typing import Any

import discord
from discord.ext import commands

from core.config import Config
from core.constants import VERSION, BOT_NAME
from core.feature_flags import get_enabled_cogs

logger = logging.getLogger(__name__)


class GayborhoodBot(commands.Bot):
    """Main bot subclass with service initialization and cog loading."""

    def __init__(self, config: Config):
        self.config = config
        self.start_time = time.monotonic()

        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.reactions = True
        intents.voice_states = True

        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            application_id=config.app_id,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="The Gayborhood",
            ),
        )

        # Services — populated in setup_hook
        self.db: Any = None
        self.dm_service: Any = None
        self.role_service: Any = None
        self.embed_builder: Any = None
        self.audit_logger: Any = None
        self.timer_service: Any = None
        self.rate_limiter: Any = None
        self.content_filter: Any = None
        self.welcome_generator: Any = None
        self.xp_calculator: Any = None
        self.card_renderer: Any = None

    @property
    def uptime(self) -> float:
        return time.monotonic() - self.start_time

    @property
    def guild(self) -> discord.Guild | None:
        return self.get_guild(self.config.guild_id)

    async def setup_hook(self) -> None:
        logger.info("Setting up %s v%s ...", BOT_NAME, VERSION)

        # 1. Database
        from database.engine import create_engine
        from database.migrations.migrate import run_migrations

        self.db = await create_engine(self.config.database_url)
        await run_migrations(self.db)
        logger.info("Database ready")

        # 2. Services
        from services.audit_logger import AuditLogger
        from services.dm_service import DMService
        from services.role_service import RoleService
        from services.embed_builder import EmbedBuilder
        from services.timer_service import TimerService
        from services.rate_limiter import RateLimiter
        from services.content_filter import ContentFilter
        from services.welcome_generator import WelcomeGenerator
        from services.xp_calculator import XPCalculator
        from services.card_renderer import CardRenderer

        self.audit_logger = AuditLogger(self.db)
        self.embed_builder = EmbedBuilder(self.config)
        self.dm_service = DMService(self, self.config, self.audit_logger)
        self.role_service = RoleService(self, self.config, self.audit_logger)
        self.rate_limiter = RateLimiter()
        self.content_filter = ContentFilter()
        self.welcome_generator = WelcomeGenerator()
        self.xp_calculator = XPCalculator(self.config)
        self.card_renderer = CardRenderer()
        self.timer_service = TimerService(self, self.db, self.audit_logger)
        logger.info("Services initialized")

        # 3. Persistent views
        from views.onboarding import OnboardingView, FallbackRetryView
        from views.intro_review import IntroReviewView
        from views.ticket_actions import TicketActionsView
        from views.ticket_panel import TicketPanelView
        from views.age_verify import AgeVerifyView

        self.add_view(OnboardingView(self))
        self.add_view(FallbackRetryView(self))
        self.add_view(IntroReviewView(self))
        self.add_view(TicketActionsView(self))
        self.add_view(TicketPanelView(self))
        self.add_view(AgeVerifyView(self))
        # Register DynamicItems
        self.add_dynamic_items(IntroReviewView.ReviewButton)
        logger.info("Persistent views registered")

        # 4. Load cogs
        enabled_cogs = get_enabled_cogs(self.config)
        for cog_path in enabled_cogs:
            try:
                await self.load_extension(cog_path)
                logger.info("Loaded cog: %s", cog_path)
            except Exception:
                logger.exception("Failed to load cog: %s", cog_path)

        # 5. Timer polling
        self.timer_service.start_polling()
        logger.info("Timer polling started")

        # 6. Sync commands to guild
        guild = discord.Object(id=self.config.guild_id)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        logger.info("Commands synced to guild %s", self.config.guild_id)

    async def on_ready(self) -> None:
        logger.info("Logged in as %s (ID: %s)", self.user, self.user.id)
        logger.info("Guild: %s", self.guild)
        logger.info("Latency: %.0fms", self.latency * 1000)

    async def close(self) -> None:
        logger.info("Shutting down...")
        if self.timer_service:
            self.timer_service.stop_polling()
        if self.db:
            await self.db.close()
        await super().close()
