from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from database.repositories.threads import ThreadRepository
from database.repositories.users import UserRepository

if TYPE_CHECKING:
    from core.bot import GayborhoodBot

logger = logging.getLogger(__name__)

# Media extensions that trigger auto-threading
MEDIA_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4", ".mov", ".webm", ".mp3", ".wav", ".ogg"}
YOUTUBE_DOMAINS = {"youtube.com", "youtu.be", "www.youtube.com"}


class AutoThreadsCog(commands.Cog, name="AutoThreadsCog"):
    """Release 1.5B: Automatic thread creation for media posts."""

    def __init__(self, bot: GayborhoodBot):
        self.bot = bot
        self._thread_repo = ThreadRepository(bot.db)
        self._configs: dict[int, dict] = {}  # channel_id -> config (cached)

    async def cog_load(self):
        await self._refresh_cache()

    async def _refresh_cache(self):
        configs = await self._thread_repo.list_enabled()
        self._configs = {c.channel_id: c.__dict__ for c in configs}
        logger.info("Auto-thread configs cached: %d channels", len(self._configs))

    @commands.Cog.listener()
    async def on_config_reloaded(self):
        await self._refresh_cache()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if message.guild.id != self.bot.config.guild_id:
            return
        if message.channel.id not in self._configs:
            return

        config = self._configs[message.channel.id]
        if not config.get("enabled", True):
            return

        should_thread = False
        file_type = "post"

        # Check media attachments
        if config.get("trigger_media", True) and message.attachments:
            for att in message.attachments:
                ext = "." + att.filename.rsplit(".", 1)[-1].lower() if "." in att.filename else ""
                if ext in MEDIA_EXTENSIONS:
                    should_thread = True
                    file_type = ext.lstrip(".")
                    break

        # Check links
        if not should_thread and config.get("trigger_links", False):
            if "http://" in message.content or "https://" in message.content:
                should_thread = True
                file_type = "link"

        # Check YouTube
        if not should_thread and config.get("trigger_youtube", False):
            for domain in YOUTUBE_DOMAINS:
                if domain in message.content.lower():
                    should_thread = True
                    file_type = "youtube"
                    break

        if not should_thread:
            return

        # Rate limit check
        max_per_min = self.bot.config.threading.get("max_threads_per_minute", 5)
        if not self.bot.rate_limiter.check(message.channel.id, "auto_thread", max_per_min, 60):
            return

        # Format thread name
        name_format = config.get("name_format", "{username} - {file_type}")
        user_repo = UserRepository(self.bot.db)
        db_user = await user_repo.get(message.author.id)
        level = db_user.level if db_user else 0

        thread_name = (
            name_format
            .replace("{username}", message.author.display_name[:20])
            .replace("{file_type}", file_type)
            .replace("{timestamp}", datetime.now(timezone.utc).strftime("%m/%d"))
            .replace("{level}", str(level))
        )[:100]  # Discord thread name limit

        try:
            auto_archive = self.bot.config.threading.get("auto_archive_duration", 1440)
            thread = await message.create_thread(
                name=thread_name,
                auto_archive_duration=auto_archive,
            )
            logger.debug("Auto-thread created: %s in #%s", thread_name, message.channel.name)
        except discord.Forbidden:
            logger.warning("Cannot create thread in %s: missing permissions", message.channel.id)
        except discord.HTTPException as e:
            logger.warning("Thread creation failed in %s: %s", message.channel.id, e)

    # ── Staff Commands ────────────────────────

    @app_commands.command(name="thread-setup", description="Enable auto-threading in a channel (Staff)")
    @app_commands.describe(
        channel="Target channel",
        trigger_media="Create threads for media posts",
        trigger_links="Create threads for link posts",
        trigger_youtube="Create threads for YouTube links",
        name_format="Thread name format ({username}, {file_type}, {timestamp}, {level})",
    )
    @app_commands.checks.has_permissions(manage_channels=True)
    async def thread_setup(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        trigger_media: bool = True,
        trigger_links: bool = False,
        trigger_youtube: bool = False,
        name_format: str = "{username} - {file_type}",
    ):
        await self._thread_repo.upsert(
            channel.id,
            enabled=1,
            trigger_media=int(trigger_media),
            trigger_links=int(trigger_links),
            trigger_youtube=int(trigger_youtube),
            name_format=name_format,
            created_by=interaction.user.id,
        )
        await self._refresh_cache()
        await interaction.response.send_message(
            f"Auto-threading configured for {channel.mention}.", ephemeral=True,
        )

    @app_commands.command(name="thread-disable", description="Disable auto-threading in a channel (Staff)")
    @app_commands.describe(channel="Target channel")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def thread_disable(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await self._thread_repo.upsert(channel.id, enabled=0)
        await self._refresh_cache()
        await interaction.response.send_message(
            f"Auto-threading disabled for {channel.mention}.", ephemeral=True,
        )

    @app_commands.command(name="thread-enable", description="Re-enable auto-threading in a channel (Staff)")
    @app_commands.describe(channel="Target channel")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def thread_enable(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await self._thread_repo.upsert(channel.id, enabled=1)
        await self._refresh_cache()
        await interaction.response.send_message(
            f"Auto-threading enabled for {channel.mention}.", ephemeral=True,
        )

    @app_commands.command(name="thread-list", description="List all auto-thread configurations (Staff)")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def thread_list(self, interaction: discord.Interaction):
        configs = await self._thread_repo.list_all()
        if not configs:
            await interaction.response.send_message("No auto-thread configs found.", ephemeral=True)
            return

        lines = []
        for c in configs:
            channel = self.bot.get_channel(c.channel_id)
            name = channel.mention if channel else f"#{c.channel_id}"
            status = "Enabled" if c.enabled else "Disabled"
            triggers = []
            if c.trigger_media:
                triggers.append("media")
            if c.trigger_links:
                triggers.append("links")
            if c.trigger_youtube:
                triggers.append("youtube")
            lines.append(f"{name} — {status} | Triggers: {', '.join(triggers) or 'none'}")

        embed = self.bot.embed_builder.info(
            title="Auto-Thread Configurations",
            description="\n".join(lines),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: GayborhoodBot):
    await bot.add_cog(AutoThreadsCog(bot))
