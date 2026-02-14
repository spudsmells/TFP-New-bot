from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from database.repositories.bully import BullyRepository

if TYPE_CHECKING:
    from core.bot import GayborhoodBot

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"


class BullyCog(commands.Cog, name="BullyCog"):
    """Release 2.5A: /bully command with insult database."""

    def __init__(self, bot: GayborhoodBot):
        self.bot = bot
        self._repo = BullyRepository(bot.db)

    async def cog_load(self):
        await self._seed_defaults()

    async def _seed_defaults(self):
        """Seed default insults from data/default_insults.json."""
        path = DATA_DIR / "default_insults.json"
        if not path.exists():
            return

        data = json.loads(path.read_text())
        insults = data.get("insults", [])
        if insults:
            count = await self._repo.seed_insults(insults, 0)
            if count:
                logger.info("Seeded %d default insults", count)

    @app_commands.command(name="bully", description="Send a friendly insult to someone")
    @app_commands.describe(target="Who to bully")
    async def bully(self, interaction: discord.Interaction, target: discord.Member):
        # Channel restriction (optional — restrict to specific channels via config)
        # Rate limit
        cooldown = self.bot.config.rate_limits.get("bully_cooldown_seconds", 60)
        if not self.bot.rate_limiter.check(interaction.user.id, "bully", 1, cooldown):
            wait = self.bot.rate_limiter.time_until_available(interaction.user.id, "bully", 1, cooldown)
            await interaction.response.send_message(
                f"Slow down! Try again in {wait:.0f} seconds.", ephemeral=True,
            )
            return

        # Can't bully yourself
        if target.id == interaction.user.id:
            await interaction.response.send_message("You can't bully yourself!", ephemeral=True)
            return

        # Can't bully the bot
        if target.id == self.bot.user.id:
            await interaction.response.send_message("Nice try, but you can't bully me.", ephemeral=True)
            return

        insult = await self._repo.get_random_active()
        if not insult:
            await interaction.response.send_message(
                "No insults available! Staff needs to add some.", ephemeral=True,
            )
            return

        # Log usage
        await self._repo.log_usage(interaction.user.id, target.id, insult.id)

        # Abuse detection
        threshold = self.bot.config.rate_limits.get("bully_abuse_threshold", 10)
        window = self.bot.config.rate_limits.get("bully_abuse_window_seconds", 3600)
        count = await self._repo.count_usage_against(target.id, window)
        if count >= threshold:
            alert_channel_id = self.bot.config.channels.get("staff_alerts")
            if alert_channel_id:
                channel = self.bot.get_channel(alert_channel_id)
                if channel and isinstance(channel, discord.TextChannel):
                    await channel.send(
                        f"\u26a0\ufe0f **Bully Abuse Alert**: {target.mention} has been bullied "
                        f"{count} times in the last hour.",
                    )

        # Format and send
        text = insult.text.replace("{target}", target.mention).replace("{user}", interaction.user.mention)
        if "{target}" not in insult.text:
            text = f"{target.mention} {text}"

        await interaction.response.send_message(text)

    # ── Staff Commands ────────────────────────

    @app_commands.command(name="bully-add", description="Add an insult to the database (Staff)")
    @app_commands.describe(text="Insult text (use {target} for target mention)")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def bully_add(self, interaction: discord.Interaction, text: str):
        try:
            insult_id = await self._repo.add(text, interaction.user.id)
            await interaction.response.send_message(
                f"Insult #{insult_id} added: `{text}`", ephemeral=True,
            )
        except Exception:
            await interaction.response.send_message(
                "That insult already exists.", ephemeral=True,
            )

    @app_commands.command(name="bully-remove", description="Remove an insult (Staff)")
    @app_commands.describe(insult_id="ID of the insult to remove")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def bully_remove(self, interaction: discord.Interaction, insult_id: int):
        removed = await self._repo.remove(insult_id, interaction.user.id)
        if removed:
            await interaction.response.send_message(
                f"Insult #{insult_id} removed.", ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"Insult #{insult_id} not found or already removed.", ephemeral=True,
            )

    @app_commands.command(name="bully-list", description="List all insults (Staff)")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def bully_list(self, interaction: discord.Interaction):
        insults = await self._repo.list_all(active_only=False)
        if not insults:
            await interaction.response.send_message("No insults found.", ephemeral=True)
            return

        lines = []
        for ins in insults[:25]:  # Limit to 25
            status = "Active" if ins.active else "Inactive"
            lines.append(f"`#{ins.id}` [{status}] {ins.text[:60]}")

        embed = self.bot.embed_builder.info(
            title=f"Bully Insults ({len(insults)} total)",
            description="\n".join(lines),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="bully-toggle", description="Toggle an insult active/inactive (Staff)")
    @app_commands.describe(insult_id="ID of the insult to toggle")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def bully_toggle(self, interaction: discord.Interaction, insult_id: int):
        new_state = await self._repo.toggle(insult_id)
        if new_state is None:
            await interaction.response.send_message(
                f"Insult #{insult_id} not found.", ephemeral=True,
            )
        else:
            state_str = "active" if new_state else "inactive"
            await interaction.response.send_message(
                f"Insult #{insult_id} is now **{state_str}**.", ephemeral=True,
            )


async def setup(bot: GayborhoodBot):
    await bot.add_cog(BullyCog(bot))
