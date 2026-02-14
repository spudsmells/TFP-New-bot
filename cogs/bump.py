"""Bump reminders — reminds people to bump the server (cos we're needy like that)"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from database.repositories.bump import BumpRepository

if TYPE_CHECKING:
    from core.bot import GayborhoodBot

logger = logging.getLogger(__name__)


class BumpCog(commands.Cog, name="BumpCog"):
    """Server bump reminders for Disboard and similar bots"""

    def __init__(self, bot: GayborhoodBot):
        self.bot = bot
        self.repo = BumpRepository(bot.db)
        self._last_bump_time: datetime | None = None
        self._bump_reminder_task: asyncio.Task | None = None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Detect successful Disboard bumps"""
        # Ignore DMs
        if not message.guild:
            return

        # Check if it's from Disboard bot (ID: 302050872383242240)
        if message.author.id != 302050872383242240:
            return

        # Check for bump success message
        if not message.embeds:
            return

        embed = message.embeds[0]

        # Check if it's a bump success message
        # Disboard sends an embed with description containing "Bump done!"
        if embed.description and "Bump done!" in embed.description:
            # Extract user who bumped (mentioned in embed)
            # Usually in format: ":thumbsup: @Username, Bump done! :heart:"
            # We'll try to get it from interaction user if available
            interaction_user = message.interaction and message.interaction.user

            if interaction_user:
                await self._handle_bump(interaction_user, message.channel)

    async def _handle_bump(self, user: discord.User | discord.Member, channel: discord.TextChannel) -> None:
        """Handle a successful bump"""
        logger.info("Bump detected by user %s", user.id)

        # Record bump in database
        await self.repo.record_bump(user.id)

        # Update last bump time
        self._last_bump_time = datetime.utcnow()

        # Thank the user
        embed = self.bot.embed_builder.success(
            title="✅ Bump Successful!",
            description=f"Thanks for bumping the server, {user.mention}! 💖\n\n"
            f"You can bump again in **2 hours**. I'll remind you when it's time!",
        )

        try:
            await channel.send(embed=embed, delete_after=30)
        except discord.HTTPException:
            pass

        # Log to audit
        await self.bot.audit_logger.log(
            "server_bumped",
            actor_id=user.id,
            details=f"Bumped via Disboard in {channel.id}",
        )

        # Schedule reminder (2 hours from now)
        if self._bump_reminder_task:
            self._bump_reminder_task.cancel()

        self._bump_reminder_task = asyncio.create_task(self._bump_reminder(user.id, channel.id))

    async def _bump_reminder(self, user_id: int, channel_id: int) -> None:
        """Send bump reminder after 2 hours"""
        # Wait 2 hours
        await asyncio.sleep(7200)  # 2 hours in seconds

        guild = self.bot.guild
        if not guild:
            return

        # Get configured bump reminder role (optional)
        bump_role_id = self.bot.config.roles.get("bump_reminder")
        mention = f"<@&{bump_role_id}>" if bump_role_id else "@everyone"

        # Get channel
        channel = guild.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            # Fallback to configured bump channel
            bump_channel_id = self.bot.config.channels.get("bump_reminders")
            if bump_channel_id:
                channel = guild.get_channel(bump_channel_id)

        if not channel or not isinstance(channel, discord.TextChannel):
            logger.warning("No valid channel for bump reminder")
            return

        # Send reminder
        embed = self.bot.embed_builder.info(
            title="🔔 Bump Reminder",
            description=f"{mention} It's time to bump the server again!\n\n"
            f"Use `/bump` to bump the server on Disboard.",
        )

        try:
            await channel.send(embed=embed)
            logger.info("Sent bump reminder to channel %s", channel_id)
        except discord.HTTPException as e:
            logger.error("Failed to send bump reminder: %s", e)

    @app_commands.command(name="bump-stats", description="Show server bump statistics")
    async def bump_stats(self, interaction: discord.Interaction):
        """Show bump statistics"""
        total_bumps = await self.repo.get_total_bumps()
        top_bumpers = await self.repo.get_top_bumpers(limit=10)

        embed = self.bot.embed_builder.info(
            title="📊 Bump Statistics",
            description=f"Total bumps: **{total_bumps}**",
        )

        # Add top bumpers
        if top_bumpers:
            leaderboard = []
            guild = self.bot.guild
            for i, bumper in enumerate(top_bumpers, 1):
                user_id = bumper["user_id"]
                bump_count = bumper["bump_count"]

                # Get member
                member = guild.get_member(user_id) if guild else None
                name = member.display_name if member else f"User {user_id}"

                # Medal emojis for top 3
                medal = ""
                if i == 1:
                    medal = "🥇 "
                elif i == 2:
                    medal = "🥈 "
                elif i == 3:
                    medal = "🥉 "

                leaderboard.append(f"{medal}**{i}.** {name} — {bump_count} bump(s)")

            embed.add_field(
                name="Top Bumpers",
                value="\n".join(leaderboard),
                inline=False,
            )

        # Last bump time
        if self._last_bump_time:
            time_since = datetime.utcnow() - self._last_bump_time
            hours = time_since.total_seconds() / 3600

            if hours < 2:
                time_until = 2 - hours
                hours_str = int(time_until)
                mins_str = int((time_until % 1) * 60)
                embed.add_field(
                    name="Next Bump Available",
                    value=f"In {hours_str}h {mins_str}m",
                    inline=False,
                )
            else:
                embed.add_field(
                    name="Next Bump Available",
                    value="Now! Use `/bump`",
                    inline=False,
                )

        await interaction.response.send_message(embed=embed, ephemeral=False)

    @app_commands.command(name="bump-leaderboard", description="Show bump leaderboard")
    async def bump_leaderboard(self, interaction: discord.Interaction):
        """Show full bump leaderboard"""
        top_bumpers = await self.repo.get_top_bumpers(limit=20)

        if not top_bumpers:
            await interaction.response.send_message(
                "No bumps recorded yet!", ephemeral=True
            )
            return

        # Build leaderboard embed
        embed = self.bot.embed_builder.info(
            title="🏆 Bump Leaderboard",
            description="Top 20 server bumpers",
        )

        guild = self.bot.guild
        leaderboard_text = []

        for i, bumper in enumerate(top_bumpers, 1):
            user_id = bumper["user_id"]
            bump_count = bumper["bump_count"]

            # Get member
            member = guild.get_member(user_id) if guild else None
            name = member.display_name if member else f"User {user_id}"

            # Medal emojis for top 3
            medal = ""
            if i == 1:
                medal = "🥇 "
            elif i == 2:
                medal = "🥈 "
            elif i == 3:
                medal = "🥉 "

            leaderboard_text.append(f"{medal}**{i}.** {name} — {bump_count} bump(s)")

        embed.description = "\n".join(leaderboard_text)

        await interaction.response.send_message(embed=embed, ephemeral=False)


async def setup(bot: GayborhoodBot):
    await bot.add_cog(BumpCog(bot))
