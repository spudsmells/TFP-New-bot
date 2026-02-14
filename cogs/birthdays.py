"""Birthday tracking — cos everyone needs some birthday love"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands, tasks

from database.repositories.birthdays import BirthdayRepository

if TYPE_CHECKING:
    from core.bot import GayborhoodBot

logger = logging.getLogger(__name__)


class BirthdaysCog(commands.Cog, name="BirthdaysCog"):
    """Birthday tracking and announcements"""

    def __init__(self, bot: GayborhoodBot):
        self.bot = bot
        self.repo = BirthdayRepository(bot.db)
        self._announced_today: set[int] = set()

    async def cog_load(self):
        """Start birthday check task when cog loads"""
        self.birthday_check.start()
        logger.info("Birthday check task started")

    async def cog_unload(self):
        """Stop birthday check task when cog unloads"""
        self.birthday_check.cancel()
        logger.info("Birthday check task stopped")

    @tasks.loop(hours=1)
    async def birthday_check(self):
        """Check for birthdays every hour and announce"""
        now = datetime.utcnow()
        today_birthdays = await self.repo.get_today_birthdays(now.month, now.day)

        if not today_birthdays:
            return

        # Get birthday announcement channel
        channel_id = self.bot.config.channels.get("birthday_announcements")
        if not channel_id:
            logger.warning("No birthday announcement channel configured")
            return

        guild = self.bot.guild
        if not guild:
            return

        channel = guild.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            logger.warning("Birthday announcement channel %s not found", channel_id)
            return

        # Announce each birthday (only once per day)
        for bday in today_birthdays:
            user_id = bday["user_id"]

            # Skip if already announced today
            if user_id in self._announced_today:
                continue

            member = guild.get_member(user_id)
            if not member:
                continue

            # Calculate age if birth year is known
            age_str = ""
            if bday["birth_year"]:
                age = now.year - bday["birth_year"]
                age_str = f" (turning {age})"

            # Send birthday message
            embed = self.bot.embed_builder.success(
                title="🎂 Happy Birthday!",
                description=f"Happy birthday to {member.mention}{age_str}!\n\n"
                f"Wishing you a wonderful day filled with joy and celebration! 🎉",
            )

            try:
                await channel.send(embed=embed)
                self._announced_today.add(user_id)
                logger.info("Announced birthday for user %s", user_id)

                # Log to audit
                await self.bot.audit_logger.log(
                    "birthday_announced",
                    target_id=user_id,
                    details=f"Age: {age}" if bday["birth_year"] else "Age unknown",
                )

            except discord.HTTPException as e:
                logger.error("Failed to announce birthday for user %s: %s", user_id, e)

    @birthday_check.before_loop
    async def before_birthday_check(self):
        """Wait for bot to be ready before starting birthday checks"""
        await self.bot.wait_until_ready()
        # Clear announced list at midnight
        now = datetime.utcnow()
        if now.hour == 0:
            self._announced_today.clear()

    @app_commands.command(name="birthday-set", description="Set your birthday")
    @app_commands.describe(
        month="Birth month (1-12)",
        day="Birth day (1-31)",
        year="Birth year (optional, used to calculate age)",
    )
    async def birthday_set(
        self,
        interaction: discord.Interaction,
        month: int,
        day: int,
        year: int | None = None,
    ):
        """Set your birthday"""
        # Validate month and day
        if month < 1 or month > 12:
            await interaction.response.send_message(
                "Invalid month. Must be between 1 and 12.", ephemeral=True
            )
            return

        if day < 1 or day > 31:
            await interaction.response.send_message(
                "Invalid day. Must be between 1 and 31.", ephemeral=True
            )
            return

        # Validate year if provided
        if year:
            current_year = datetime.utcnow().year
            if year < 1900 or year > current_year:
                await interaction.response.send_message(
                    f"Invalid year. Must be between 1900 and {current_year}.",
                    ephemeral=True,
                )
                return

        try:
            await self.repo.set_birthday(interaction.user.id, month, day, year, announce=True)

            # Format date nicely
            date_str = f"{month}/{day}"
            if year:
                age = datetime.utcnow().year - year
                date_str += f" (turning {age} this year)"

            await interaction.response.send_message(
                f"✅ Birthday set to **{date_str}**!\n"
                f"You'll receive a birthday announcement on your special day! 🎂",
                ephemeral=True,
            )

            # Log to audit
            await self.bot.audit_logger.log(
                "birthday_set",
                actor_id=interaction.user.id,
                target_id=interaction.user.id,
                details=f"{month}/{day}" + (f"/{year}" if year else ""),
            )

        except Exception as e:
            logger.exception("Failed to set birthday for user %s", interaction.user.id)
            await interaction.response.send_message(
                f"Failed to set birthday: {e}", ephemeral=True
            )

    @app_commands.command(name="birthday-remove", description="Remove your birthday")
    async def birthday_remove(self, interaction: discord.Interaction):
        """Remove your birthday from the system"""
        existing = await self.repo.get_birthday(interaction.user.id)
        if not existing:
            await interaction.response.send_message(
                "You don't have a birthday set.", ephemeral=True
            )
            return

        try:
            await self.repo.remove_birthday(interaction.user.id)

            await interaction.response.send_message(
                "✅ Birthday removed. You won't receive birthday announcements anymore.",
                ephemeral=True,
            )

            # Log to audit
            await self.bot.audit_logger.log(
                "birthday_removed",
                actor_id=interaction.user.id,
                target_id=interaction.user.id,
            )

        except Exception as e:
            logger.exception("Failed to remove birthday for user %s", interaction.user.id)
            await interaction.response.send_message(
                f"Failed to remove birthday: {e}", ephemeral=True
            )

    @app_commands.command(name="birthday-toggle", description="Toggle birthday announcements on/off")
    async def birthday_toggle(self, interaction: discord.Interaction):
        """Toggle birthday announcements"""
        existing = await self.repo.get_birthday(interaction.user.id)
        if not existing:
            await interaction.response.send_message(
                "You don't have a birthday set. Use `/birthday-set` first.",
                ephemeral=True,
            )
            return

        try:
            new_state = not existing["announce"]
            await self.repo.toggle_announce(interaction.user.id, new_state)

            if new_state:
                await interaction.response.send_message(
                    "✅ Birthday announcements **enabled**. You'll be celebrated! 🎉",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    "✅ Birthday announcements **disabled**. No public celebration.",
                    ephemeral=True,
                )

        except Exception as e:
            logger.exception("Failed to toggle birthday for user %s", interaction.user.id)
            await interaction.response.send_message(
                f"Failed to toggle birthday: {e}", ephemeral=True
            )

    @app_commands.command(name="birthday-list", description="List upcoming birthdays")
    async def birthday_list(self, interaction: discord.Interaction):
        """List upcoming birthdays in the server"""
        all_birthdays = await self.repo.get_upcoming_birthdays(limit=50)

        if not all_birthdays:
            await interaction.response.send_message(
                "No birthdays have been set yet!", ephemeral=True
            )
            return

        # Sort by upcoming (next birthday from today)
        now = datetime.utcnow()
        current_month = now.month
        current_day = now.day

        def days_until(bday):
            """Calculate days until next birthday"""
            month = bday["birth_month"]
            day = bday["birth_day"]

            # Calculate days from today
            target = datetime(now.year, month, day)
            if target < now:
                # Already passed this year, use next year
                target = datetime(now.year + 1, month, day)

            return (target - now).days

        sorted_birthdays = sorted(all_birthdays, key=days_until)

        # Build embed
        embed = self.bot.embed_builder.info(
            title="🎂 Upcoming Birthdays",
            description=f"Next {min(10, len(sorted_birthdays))} birthdays",
        )

        guild = self.bot.guild
        for bday in sorted_birthdays[:10]:
            user_id = bday["user_id"]
            member = guild.get_member(user_id) if guild else None

            if not member:
                continue

            month = bday["birth_month"]
            day = bday["birth_day"]
            year = bday["birth_year"]

            date_str = f"{month}/{day}"
            if year:
                age = now.year - year
                if month < current_month or (month == current_month and day < current_day):
                    age += 1  # Next birthday
                date_str += f" (turning {age})"

            days = days_until(bday)
            days_str = f"in {days} day(s)" if days > 0 else "TODAY! 🎉"

            embed.add_field(
                name=member.display_name,
                value=f"{date_str} — {days_str}",
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: GayborhoodBot):
    await bot.add_cog(BirthdaysCog(bot))
