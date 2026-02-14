from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord

from views.common import PersistentView

if TYPE_CHECKING:
    from core.bot import GayborhoodBot

logger = logging.getLogger(__name__)


class TicketPanelView(PersistentView):
    """Permanent panel in #ticket-booth with 3 buttons."""

    def __init__(self, bot: GayborhoodBot):
        super().__init__(bot)

    @discord.ui.button(
        label="Open Support Ticket",
        style=discord.ButtonStyle.primary,
        custom_id="panel:support_ticket",
        emoji="\U0001f3ab",
        row=0,
    )
    async def support_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        tickets_cog = self.bot.get_cog("TicketsMemberCog")
        if tickets_cog:
            await tickets_cog.open_ticket_from_panel(interaction)
        else:
            await interaction.response.send_message(
                "The ticket system is not currently available.", ephemeral=True,
            )

    @discord.ui.button(
        label="Start Intro",
        style=discord.ButtonStyle.success,
        custom_id="panel:start_intro",
        emoji="\U0001f4dd",
        row=0,
    )
    async def intro_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        intros_cog = self.bot.get_cog("IntrosCog")
        if intros_cog:
            await intros_cog.start_intro(interaction)
        else:
            await interaction.response.send_message(
                "The intro system is not currently available.", ephemeral=True,
            )

    @discord.ui.button(
        label="Age Verification",
        style=discord.ButtonStyle.secondary,
        custom_id="panel:age_verify",
        emoji="\U0001f510",
        row=0,
    )
    async def age_verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        age_cog = self.bot.get_cog("AgeVerifyCog")
        if age_cog:
            await age_cog.start_verify(interaction)
        else:
            await interaction.response.send_message(
                "Age verification is not currently available.", ephemeral=True,
            )
