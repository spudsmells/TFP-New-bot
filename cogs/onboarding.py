from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from database.repositories.users import UserRepository
from views.onboarding import OnboardingView
from services.card_renderer import WelcomeCardData

if TYPE_CHECKING:
    from core.bot import GayborhoodBot

logger = logging.getLogger(__name__)


class OnboardingCog(commands.Cog, name="OnboardingCog"):
    """Release 1: Member join, DM rules, fallback."""

    def __init__(self, bot: GayborhoodBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return

        if member.guild.id != self.bot.config.guild_id:
            return

        logger.info("New member joined: %s (%d)", member, member.id)

        # Ensure user exists in DB
        user_repo = UserRepository(self.bot.db)
        await user_repo.upsert(
            member.id,
            username=str(member),
            status="pending",
            joined_at=member.joined_at.isoformat() if member.joined_at else None,
        )

        # Assign Pending role
        pending_role_id = self.bot.config.roles.get("pending")
        if pending_role_id:
            await self.bot.role_service.add_role(member, pending_role_id, reason="New member")

        # Build rules DM
        embed = self.bot.embed_builder.info(
            title="Welcome to The Gayborhood!",
            description=(
                "We're glad you're here! Before you can access the server, "
                "please read and agree to our rules.\n\n"
                "**Server Rules:**\n"
                "1. Be respectful to all members\n"
                "2. No hate speech, slurs, or discrimination\n"
                "3. No NSFW content outside designated channels\n"
                "4. No spam or self-promotion\n"
                "5. Must be 18+ to join\n"
                "6. Listen to staff\n\n"
                "Click **I Agree to the Rules** below to accept and continue."
            ),
        )
        embed.set_author(name=member.guild.name, icon_url=member.guild.icon.url if member.guild.icon else None)

        view = OnboardingView(self.bot)
        result = await self.bot.dm_service.send(
            member, embed=embed, view=view,
            fallback_channel_id=self.bot.config.channels.get("onboarding_fallback"),
        )

        await self.bot.audit_logger.log(
            "member_join_dm",
            target_id=member.id,
            details={"dm_result": result.method},
        )

        # Post welcome card in #welcome channel
        welcome_channel_id = self.bot.config.channels.get("welcome")
        if welcome_channel_id:
            welcome_channel = self.bot.get_channel(welcome_channel_id)
            if welcome_channel and isinstance(welcome_channel, discord.TextChannel):
                avatar = await self.bot.card_renderer.fetch_avatar(member)
                data = WelcomeCardData(
                    username=member.display_name,
                    avatar=avatar,
                    member_number=member.guild.member_count or 0,
                    server_name=member.guild.name,
                )
                file = await self.bot.card_renderer.welcome_card(data)
                await welcome_channel.send(
                    f"Welcome {member.mention}!",
                    file=file,
                )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.bot:
            return
        if member.guild.id != self.bot.config.guild_id:
            return

        await self.bot.audit_logger.log(
            "member_leave", target_id=member.id,
            details={"username": str(member)},
        )


async def setup(bot: GayborhoodBot):
    await bot.add_cog(OnboardingCog(bot))
