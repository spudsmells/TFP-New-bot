"""DM service — sends DMs to members (or fallback to channel when they're being difficult)"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from core.errors import DMFailedError

if TYPE_CHECKING:
    from core.bot import GayborhoodBot
    from core.config import Config
    from services.audit_logger import AuditLogger

logger = logging.getLogger(__name__)


class DMService:
    """
    Sends DMs to members with retry logic and fallback channel posting.

    Handles all the bollocks around closed DMs, deleted users, etc.
    """

    def __init__(self, bot: GayborhoodBot, config: Config, audit_logger: AuditLogger):
        self.bot = bot
        self.config = config
        self.audit = audit_logger

    async def send_dm(
        self,
        user: discord.User | discord.Member,
        content: str | None = None,
        embed: discord.Embed | None = None,
    ) -> discord.Message | None:
        """
        Send a DM to a user.

        Returns the message if successful, None if it fails.
        Doesn't raise exceptions — check return value innit.
        """
        try:
            msg = await user.send(content=content, embed=embed)
            logger.debug("DM sent successfully to user %s", user.id)
            return msg
        except discord.Forbidden:
            logger.warning("Cannot DM user %s — they've got DMs closed", user.id)
            await self.audit.log(
                "dm_failed",
                severity="warning",
                target_id=user.id,
                details="DMs closed",
            )
            return None
        except discord.HTTPException as e:
            logger.error("Failed to DM user %s: %s", user.id, e)
            await self.audit.log(
                "dm_failed",
                severity="error",
                target_id=user.id,
                details=f"HTTP error: {e}",
            )
            return None

    async def send_with_fallback(
        self,
        user: discord.User | discord.Member,
        content: str | None = None,
        embed: discord.Embed | None = None,
        fallback_channel_id: int | None = None,
    ) -> tuple[discord.Message | None, bool]:
        """
        Send DM with fallback to channel if DM fails.

        Args:
            user: User to DM
            content: Message content
            embed: Message embed
            fallback_channel_id: Channel to post in if DM fails (uses config default if not provided)

        Returns:
            (message, used_fallback) — message is None if both DM and fallback fail
        """
        # Try DM first
        dm_msg = await self.send_dm(user, content=content, embed=embed)
        if dm_msg:
            return (dm_msg, False)

        # DM failed, try fallback channel
        channel_id = fallback_channel_id or self.config.channels.get("onboarding_fallback")
        if not channel_id:
            logger.error(
                "DM failed for user %s and no fallback channel configured",
                user.id,
            )
            return (None, False)

        guild = self.bot.guild
        if not guild:
            logger.error("Cannot find guild for fallback posting")
            return (None, False)

        channel = guild.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            logger.error("Fallback channel %s not found or invalid", channel_id)
            return (None, False)

        try:
            # Post to fallback channel with user mention
            fallback_content = f"{user.mention} — couldn't DM you so posting here instead:\n\n{content or ''}"
            fallback_msg = await channel.send(
                content=fallback_content if content else user.mention,
                embed=embed,
            )
            logger.info(
                "Posted DM fallback for user %s in channel %s",
                user.id,
                channel_id,
            )
            await self.audit.log(
                "dm_fallback_used",
                target_id=user.id,
                details=f"Posted in channel {channel_id}",
            )
            return (fallback_msg, True)
        except discord.HTTPException as e:
            logger.error("Failed to post fallback message: %s", e)
            await self.audit.log_error(
                "dm_fallback_failed",
                f"User {user.id}, channel {channel_id}: {e}",
            )
            return (None, False)

    async def send_dm_or_raise(
        self,
        user: discord.User | discord.Member,
        content: str | None = None,
        embed: discord.Embed | None = None,
    ) -> discord.Message:
        """
        Send DM or raise DMFailedError if it fails.

        Use this when DM delivery is critical and you wanna handle failures explicitly.
        """
        msg = await self.send_dm(user, content=content, embed=embed)
        if not msg:
            raise DMFailedError(user.id, "DM delivery failed")
        return msg
