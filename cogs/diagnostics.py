from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from core.constants import VERSION, BOT_NAME

if TYPE_CHECKING:
    from core.bot import GayborhoodBot

logger = logging.getLogger(__name__)


class DiagnosticsCog(commands.Cog, name="DiagnosticsCog"):
    """Bot diagnostics: /ping, /version, /status, /reload-config."""

    def __init__(self, bot: GayborhoodBot):
        self.bot = bot

    @app_commands.command(name="ping", description="Check bot latency")
    async def ping(self, interaction: discord.Interaction):
        latency_ms = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"Pong! **{latency_ms}ms**", ephemeral=True)

    @app_commands.command(name="version", description="Show bot version")
    async def version(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"**{BOT_NAME}** v{VERSION}", ephemeral=True)

    @app_commands.command(name="status", description="Bot health check")
    async def status(self, interaction: discord.Interaction):
        uptime_s = int(self.bot.uptime)
        hours, remainder = divmod(uptime_s, 3600)
        minutes, seconds = divmod(remainder, 60)

        guild = self.bot.guild
        member_count = guild.member_count if guild else "N/A"

        # DB check
        try:
            await self.bot.db.fetch_val("SELECT 1")
            db_status = "Connected"
        except Exception:
            db_status = "ERROR"

        embed = self.bot.embed_builder.info(title="Bot Status")
        embed.add_field(name="Uptime", value=f"{hours}h {minutes}m {seconds}s", inline=True)
        embed.add_field(name="Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        embed.add_field(name="Members", value=str(member_count), inline=True)
        embed.add_field(name="Database", value=db_status, inline=True)
        embed.add_field(name="Cogs Loaded", value=str(len(self.bot.cogs)), inline=True)
        embed.add_field(name="Version", value=f"v{VERSION}", inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="reload-config", description="Hot-reload config.yaml (Staff only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def reload_config(self, interaction: discord.Interaction):
        try:
            self.bot.config.reload()
            self.bot.dispatch("config_reloaded")
            await interaction.response.send_message(
                "Configuration reloaded successfully.", ephemeral=True,
            )
            await self.bot.audit_logger.log(
                "config_reloaded", actor_id=interaction.user.id,
            )
        except Exception as e:
            await interaction.response.send_message(
                f"Config reload failed: {e}", ephemeral=True,
            )

    @reload_config.error
    async def reload_config_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "You need administrator permissions to use this command.", ephemeral=True,
            )


async def setup(bot: GayborhoodBot):
    await bot.add_cog(DiagnosticsCog(bot))
