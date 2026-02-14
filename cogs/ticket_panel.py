from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from views.ticket_panel import TicketPanelView

if TYPE_CHECKING:
    from core.bot import GayborhoodBot

logger = logging.getLogger(__name__)


class TicketPanelCog(commands.Cog, name="TicketPanelCog"):
    """Release 8: Permanent server panel in #ticket-booth."""

    def __init__(self, bot: GayborhoodBot):
        self.bot = bot

    @app_commands.command(name="panel-deploy", description="Deploy the ticket booth panel (Admin)")
    @app_commands.describe(channel="Channel to deploy the panel in")
    @app_commands.checks.has_permissions(administrator=True)
    async def panel_deploy(self, interaction: discord.Interaction, channel: discord.TextChannel | None = None):
        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message("Must be a text channel.", ephemeral=True)
            return

        embed = self.bot.embed_builder.info(
            title="The Gayborhood — Help Desk",
            description=(
                "Welcome! Use the buttons below to get started.\n\n"
                "\U0001f4dd **Start Intro** — Begin your introduction to join the server\n"
                "\U0001f3ab **Open Support Ticket** — Get help from staff\n"
                "\U0001f510 **Age Verification** — Verify your age for additional access\n"
            ),
        )

        view = TicketPanelView(self.bot)
        msg = await target.send(embed=embed, view=view)

        # Track sticky message
        await self.bot.db.execute(
            "INSERT INTO sticky_messages (channel_id, message_id, embed_type) VALUES (?, ?, ?)",
            (target.id, msg.id, "ticket_panel"),
        )

        await interaction.response.send_message(
            f"Panel deployed in {target.mention}.", ephemeral=True,
        )

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """Auto-repost panel if deleted."""
        if not message.guild or message.guild.id != self.bot.config.guild_id:
            return

        row = await self.bot.db.fetch_one(
            "SELECT * FROM sticky_messages WHERE message_id = ? AND embed_type = 'ticket_panel'",
            (message.id,),
        )
        if not row:
            return

        channel = self.bot.get_channel(row["channel_id"])
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        logger.warning("Ticket panel deleted in %s, reposting...", channel.name)

        embed = self.bot.embed_builder.info(
            title="The Gayborhood — Help Desk",
            description=(
                "Welcome! Use the buttons below to get started.\n\n"
                "\U0001f4dd **Start Intro** — Begin your introduction to join the server\n"
                "\U0001f3ab **Open Support Ticket** — Get help from staff\n"
                "\U0001f510 **Age Verification** — Verify your age for additional access\n"
            ),
        )

        view = TicketPanelView(self.bot)
        new_msg = await channel.send(embed=embed, view=view)

        # Update tracking
        await self.bot.db.execute(
            "UPDATE sticky_messages SET message_id = ? WHERE id = ?",
            (new_msg.id, row["id"]),
        )


async def setup(bot: GayborhoodBot):
    await bot.add_cog(TicketPanelCog(bot))
