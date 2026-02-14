from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from database.repositories.milestones import MilestoneRepository
from services.card_renderer import LevelUpCardData

if TYPE_CHECKING:
    from core.bot import GayborhoodBot

logger = logging.getLogger(__name__)


class MilestonesCog(commands.Cog, name="MilestonesCog"):
    """Release 9: Level-up notifications and milestone tracking."""

    def __init__(self, bot: GayborhoodBot):
        self.bot = bot
        self._milestone_repo = MilestoneRepository(bot.db)

    async def _send_levelup_card(self, user: discord.User, old_level: int,
                                  new_level: int, unlocks: list[str]) -> None:
        """Generate and send a level-up image card via DM + post in channel."""
        avatar = await self.bot.card_renderer.fetch_avatar(user)
        data = LevelUpCardData(
            username=user.display_name,
            avatar=avatar,
            old_level=old_level,
            new_level=new_level,
            unlocks=unlocks,
        )
        file = await self.bot.card_renderer.level_up_card(data)

        # DM the user
        await self.bot.dm_service.send(user, file=file)

        # Also post in level-up channel if configured
        channel_id = self.bot.config.channels.get("levelup")
        if channel_id:
            channel = self.bot.get_channel(channel_id)
            if channel and isinstance(channel, discord.TextChannel):
                # Re-generate file (can't reuse after send)
                file2 = await self.bot.card_renderer.level_up_card(data)
                await channel.send(
                    f"\U0001f389 {user.mention} just reached **Level {new_level}**!",
                    file=file2,
                )

    @commands.Cog.listener()
    async def on_level_up(self, user_id: int, old_level: int, new_level: int):
        """Notify user on level up with an image card."""
        user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
        if not user:
            return

        # Check unlocks
        unlocks = []
        if self.bot.xp_calculator.is_age_verify_eligible(new_level) and not self.bot.xp_calculator.is_age_verify_eligible(old_level):
            unlocks.append("Age Verification")

        await self._send_levelup_card(user, old_level, new_level, unlocks)

    @commands.Cog.listener()
    async def on_milestone_reached(self, user_id: int, level: int):
        """Record and notify milestone achievements."""
        is_new = await self._milestone_repo.record(user_id, level)
        if not is_new:
            return

        await self._milestone_repo.mark_notified(user_id, level)

        user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
        if not user:
            return

        # Milestones get a special card too
        avatar = await self.bot.card_renderer.fetch_avatar(user)
        data = LevelUpCardData(
            username=user.display_name,
            avatar=avatar,
            old_level=level - 1,
            new_level=level,
            unlocks=[f"Level {level} Milestone!"],
        )
        file = await self.bot.card_renderer.level_up_card(data)
        await self.bot.dm_service.send(user, file=file)

        await self.bot.audit_logger.log(
            "milestone_reached", target_id=user_id,
            details={"level": level},
        )


async def setup(bot: GayborhoodBot):
    await bot.add_cog(MilestonesCog(bot))
