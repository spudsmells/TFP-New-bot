from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord

from database.repositories.rules import RulesRepository
from database.repositories.users import UserRepository
from views.common import PersistentView

if TYPE_CHECKING:
    from core.bot import GayborhoodBot

logger = logging.getLogger(__name__)

RULE_VERSION = "1.0"


class OnboardingView(PersistentView):
    """DM onboarding panel: I Agree, Start Intro (disabled), Support Ticket (disabled), Age Verify (disabled)."""

    def __init__(self, bot: GayborhoodBot):
        super().__init__(bot)

    @discord.ui.button(
        label="I Agree to the Rules",
        style=discord.ButtonStyle.success,
        custom_id="onboarding:agree",
        emoji="\u2705",
        row=0,
    )
    async def agree_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_repo = UserRepository(self.bot.db)
        rules_repo = RulesRepository(self.bot.db)

        # Check if already agreed
        already = await rules_repo.has_acknowledged(interaction.user.id, RULE_VERSION)
        if already:
            await interaction.response.send_message(
                "You've already agreed to the rules! Use the buttons below to continue.",
                ephemeral=True,
            )
            return

        # Record agreement
        await user_repo.upsert(interaction.user.id, username=str(interaction.user))
        await rules_repo.record_acknowledgement(interaction.user.id, RULE_VERSION, "dm")
        await user_repo.set_rules_agreed(interaction.user.id, RULE_VERSION, "dm")

        await self.bot.audit_logger.log(
            "rules_agreed", target_id=interaction.user.id,
            details={"version": RULE_VERSION, "method": "dm"},
        )

        # Send updated view with Start Intro enabled
        embed = self.bot.embed_builder.success(
            title="Rules Accepted!",
            description=(
                "Thanks for agreeing to the rules! You can now start your introduction.\n\n"
                "Click **Start Intro** below to begin."
            ),
        )

        enabled_view = OnboardingEnabledView(self.bot)
        await interaction.response.edit_message(embed=embed, view=enabled_view)

    @discord.ui.button(
        label="Start Intro",
        style=discord.ButtonStyle.primary,
        custom_id="onboarding:intro",
        disabled=True,
        emoji="\U0001f4dd",
        row=0,
    )
    async def intro_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # This will be handled when enabled
        pass

    @discord.ui.button(
        label="Support Ticket",
        style=discord.ButtonStyle.secondary,
        custom_id="onboarding:ticket",
        disabled=True,
        emoji="\U0001f3ab",
        row=1,
    )
    async def ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(
        label="Age Verify",
        style=discord.ButtonStyle.secondary,
        custom_id="onboarding:age_verify",
        disabled=True,
        emoji="\U0001f510",
        row=1,
    )
    async def age_verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass


class OnboardingEnabledView(PersistentView):
    """Post-agreement view with Start Intro enabled."""

    def __init__(self, bot: GayborhoodBot):
        super().__init__(bot)

    @discord.ui.button(
        label="Start Intro",
        style=discord.ButtonStyle.primary,
        custom_id="onboarding:intro_enabled",
        emoji="\U0001f4dd",
        row=0,
    )
    async def intro_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if intros cog is loaded and dispatch
        intros_cog = self.bot.get_cog("IntrosCog")
        if intros_cog:
            await intros_cog.start_intro(interaction)
        else:
            await interaction.response.send_message(
                "The intro system is not currently available. Please contact staff.",
                ephemeral=True,
            )

    @discord.ui.button(
        label="Support Ticket",
        style=discord.ButtonStyle.secondary,
        custom_id="onboarding:ticket_enabled",
        emoji="\U0001f3ab",
        row=1,
    )
    async def ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        tickets_cog = self.bot.get_cog("TicketsMemberCog")
        if tickets_cog:
            await tickets_cog.open_ticket_from_dm(interaction)
        else:
            await interaction.response.send_message(
                "The ticket system is not currently available. Please contact staff.",
                ephemeral=True,
            )

    @discord.ui.button(
        label="Age Verify",
        style=discord.ButtonStyle.secondary,
        custom_id="onboarding:age_verify_enabled",
        emoji="\U0001f510",
        row=1,
    )
    async def age_verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        age_cog = self.bot.get_cog("AgeVerifyCog")
        if age_cog:
            await age_cog.start_verify(interaction)
        else:
            await interaction.response.send_message(
                "Age verification is not currently available. Please contact staff.",
                ephemeral=True,
            )


class FallbackRetryView(PersistentView):
    """Retry DM button posted in fallback channel."""

    def __init__(self, bot: GayborhoodBot):
        super().__init__(bot)

    @discord.ui.button(
        label="Retry DM",
        style=discord.ButtonStyle.primary,
        custom_id="fallback:retry_dm",
        emoji="\U0001f4e8",
    )
    async def retry_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        # Build the rules embed
        embed = self.bot.embed_builder.info(
            title="Welcome to The Gayborhood!",
            description=(
                "Please read and agree to the server rules to get started.\n\n"
                "**Server Rules:**\n"
                "1. Be respectful to all members\n"
                "2. No hate speech, slurs, or discrimination\n"
                "3. No NSFW content outside designated channels\n"
                "4. No spam or self-promotion\n"
                "5. Must be 18+ to join\n"
                "6. Listen to staff\n\n"
                "Click **I Agree** below to accept and continue."
            ),
        )

        view = OnboardingView(self.bot)
        result = await self.bot.dm_service.send(
            interaction.user, embed=embed, view=view,
        )

        if result.method == "dm":
            await interaction.followup.send(
                "Check your DMs! I've sent you the onboarding message.",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                "I still can't DM you. Please enable DMs from server members in your "
                "Privacy Settings (right-click the server > Privacy Settings > Direct Messages).",
                ephemeral=True,
            )
