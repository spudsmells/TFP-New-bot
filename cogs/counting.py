"""Counting channel game — count to infinity without fucking it up"""
from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from database.repositories.counting import CountingRepository

if TYPE_CHECKING:
    from core.bot import GayborhoodBot

logger = logging.getLogger(__name__)


class CountingCog(commands.Cog, name="CountingCog"):
    """Counting channel game where users count sequentially"""

    def __init__(self, bot: GayborhoodBot):
        self.bot = bot
        self.repo = CountingRepository(bot.db)
        # Cache of channel_id -> (current_count, last_user_id)
        self._counting_channels: set[int] = set()

    async def cog_load(self):
        """Load counting channels from config"""
        counting_channels = self.bot.config.features.get("counting_channels", [])
        self._counting_channels = set(counting_channels)
        logger.info("Loaded %d counting channels", len(self._counting_channels))

        # Initialize channels in database
        for channel_id in self._counting_channels:
            await self.repo.init_channel(channel_id)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Check counting channel messages"""
        # Ignore DMs
        if not message.guild:
            return

        # Ignore bots
        if message.author.bot:
            return

        # Check if this is a counting channel
        if message.channel.id not in self._counting_channels:
            return

        # Get current stats
        stats = await self.repo.get_stats(message.channel.id)
        if not stats:
            # Initialize if not exists
            await self.repo.init_channel(message.channel.id)
            stats = await self.repo.get_stats(message.channel.id)

        current_count = stats["current_count"]
        last_user_id = stats["last_user_id"]
        expected_number = current_count + 1

        # Extract number from message (allow some text, but must contain the number)
        content = message.content.strip()
        numbers = re.findall(r'\d+', content)

        if not numbers:
            # No number found — fail
            await self._handle_fail(message, expected_number, "no number found")
            return

        # Get first number in message
        try:
            user_number = int(numbers[0])
        except ValueError:
            await self._handle_fail(message, expected_number, "invalid number")
            return

        # Check if same user counting twice in a row
        if last_user_id and last_user_id == message.author.id:
            await self._handle_fail(message, expected_number, "same user twice")
            return

        # Check if correct number
        if user_number != expected_number:
            await self._handle_fail(
                message,
                expected_number,
                f"wrong number (expected {expected_number}, got {user_number})",
            )
            return

        # Correct! Increment count
        new_count = await self.repo.increment_count(message.channel.id, message.author.id)

        # React with checkmark
        try:
            await message.add_reaction("✅")
        except discord.HTTPException:
            pass

        # Update highest if needed
        await self.repo.update_highest(message.channel.id, new_count)

        # Milestone reactions
        if new_count % 100 == 0:
            try:
                await message.add_reaction("💯")
            except discord.HTTPException:
                pass

        if new_count % 1000 == 0:
            try:
                await message.add_reaction("🎉")
                embed = self.bot.embed_builder.success(
                    title="🎊 Milestone Reached!",
                    description=f"Congratulations! The count has reached **{new_count}**!",
                )
                await message.channel.send(embed=embed)
            except discord.HTTPException:
                pass

    async def _handle_fail(self, message: discord.Message, expected: int, reason: str) -> None:
        """Handle counting fail"""
        logger.info(
            "Counting fail in channel %s: expected %d, reason: %s",
            message.channel.id,
            expected,
            reason,
        )

        # Get current count before reset
        stats = await self.repo.get_stats(message.channel.id)
        old_count = stats["current_count"] if stats else 0

        # Reset count
        await self.repo.reset_count(message.channel.id)

        # React with X
        try:
            await message.add_reaction("❌")
        except discord.HTTPException:
            pass

        # Delete the wrong message
        try:
            await message.delete()
        except discord.HTTPException:
            pass

        # Send fail message
        embed = self.bot.embed_builder.error(
            title="❌ Counting Failed!",
            description=f"{message.author.mention} broke the count at **{old_count}**!\n\n"
            f"**Expected:** {expected}\n"
            f"**Reason:** {reason}\n\n"
            f"The count has been reset to **0**. Start again!",
        )

        try:
            await message.channel.send(embed=embed, delete_after=10)
        except discord.HTTPException:
            pass

        # Log to audit
        await self.bot.audit_logger.log(
            "counting_failed",
            actor_id=message.author.id,
            details=f"Channel {message.channel.id}, count was {old_count}, reason: {reason}",
        )

    @app_commands.command(name="counting-stats", description="Show counting channel statistics")
    async def counting_stats(self, interaction: discord.Interaction):
        """Show counting stats for the current channel"""
        if interaction.channel.id not in self._counting_channels:
            await interaction.response.send_message(
                "This isn't a counting channel.", ephemeral=True
            )
            return

        stats = await self.repo.get_stats(interaction.channel.id)
        if not stats:
            await interaction.response.send_message(
                "No counting stats available yet.", ephemeral=True
            )
            return

        embed = self.bot.embed_builder.info(title="📊 Counting Stats")
        embed.add_field(name="Current Count", value=str(stats["current_count"]), inline=True)
        embed.add_field(name="Highest Count", value=str(stats["highest_count"]), inline=True)
        embed.add_field(name="Total Fails", value=str(stats["fails"]), inline=True)

        if stats["last_user_id"]:
            last_user = interaction.guild.get_member(stats["last_user_id"])
            if last_user:
                embed.add_field(
                    name="Last Counter",
                    value=last_user.mention,
                    inline=False,
                )

        await interaction.response.send_message(embed=embed, ephemeral=False)

    @app_commands.command(name="counting-reset", description="Reset counting stats (Staff only)")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def counting_reset(self, interaction: discord.Interaction):
        """Reset counting stats for current channel"""
        if interaction.channel.id not in self._counting_channels:
            await interaction.response.send_message(
                "This isn't a counting channel.", ephemeral=True
            )
            return

        stats = await self.repo.get_stats(interaction.channel.id)
        old_count = stats["current_count"] if stats else 0

        await self.repo.reset_count(interaction.channel.id)

        # Also reset highest
        await self.repo.update_highest(interaction.channel.id, 0)

        await interaction.response.send_message(
            f"✅ Counting stats reset. Previous count was {old_count}.",
            ephemeral=True,
        )

        # Log to audit
        await self.bot.audit_logger.log(
            "counting_reset",
            actor_id=interaction.user.id,
            details=f"Channel {interaction.channel.id}, count was {old_count}",
        )

    @counting_reset.error
    async def counting_reset_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "You need 'Manage Channels' permission to reset counting stats.",
                ephemeral=True,
            )


async def setup(bot: GayborhoodBot):
    await bot.add_cog(CountingCog(bot))
