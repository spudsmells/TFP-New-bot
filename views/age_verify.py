from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord

from database.repositories.users import UserRepository
from views.common import PersistentView

if TYPE_CHECKING:
    from core.bot import GayborhoodBot

logger = logging.getLogger(__name__)


class AgeVerifyView(PersistentView):
    """Age verification confirmation view."""

    def __init__(self, bot: GayborhoodBot):
        super().__init__(bot)

    @discord.ui.button(
        label="Start Age Verification",
        style=discord.ButtonStyle.primary,
        custom_id="age_verify:start",
        emoji="\U0001f510",
    )
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_repo = UserRepository(self.bot.db)
        user = await user_repo.get(interaction.user.id)

        if not user:
            await interaction.response.send_message(
                "You need to complete onboarding first.", ephemeral=True,
            )
            return

        if user.age_verified:
            await interaction.response.send_message(
                "You're already age verified!", ephemeral=True,
            )
            return

        # Check level gate
        required_level = self.bot.config.xp.get("age_verify_level", 15)
        if user.level < required_level:
            await interaction.response.send_message(
                f"You need to be at least **Level {required_level}** to request age verification. "
                f"You're currently Level {user.level}.",
                ephemeral=True,
            )
            return

        # Dispatch to age verify cog
        age_cog = self.bot.get_cog("AgeVerifyCog")
        if age_cog:
            await age_cog.create_verify_ticket(interaction)
        else:
            await interaction.response.send_message(
                "Age verification is not currently available.", ephemeral=True,
            )
