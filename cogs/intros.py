from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands
from rapidfuzz import fuzz, process

from core.constants import IntroStatus
from database.repositories.intros import IntroRepository
from database.repositories.users import UserRepository
from views.intro_review import IntroReviewView

if TYPE_CHECKING:
    from core.bot import GayborhoodBot

logger = logging.getLogger(__name__)


class IntroModal(discord.ui.Modal, title="Tell Us About Yourself!"):
    age = discord.ui.TextInput(
        label="Age (must be 18+)",
        placeholder="e.g. 24",
        min_length=2,
        max_length=3,
    )
    preferred_name = discord.ui.TextInput(
        label="Preferred Name",
        placeholder="What should we call you?",
        max_length=50,
    )
    pronouns = discord.ui.TextInput(
        label="Pronouns",
        placeholder="e.g. he/him, she/her, they/them",
        max_length=50,
    )
    location = discord.ui.TextInput(
        label="Location (state/country)",
        placeholder="e.g. California, UK, Germany",
        max_length=100,
    )
    bio = discord.ui.TextInput(
        label="Bio (30-400 characters)",
        style=discord.TextStyle.paragraph,
        placeholder="Tell us about yourself, your interests, why you're here...",
        min_length=30,
        max_length=400,
    )

    def __init__(self, bot: GayborhoodBot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        # Validate age
        try:
            age_val = int(self.age.value)
        except ValueError:
            await interaction.response.send_message("Age must be a number.", ephemeral=True)
            return

        if age_val < 18:
            await interaction.response.send_message(
                "You must be 18 or older to join this server.", ephemeral=True,
            )
            return

        # Content filter
        result = self.bot.content_filter.validate_bio(self.bio.value)
        if not result.passed:
            reasons = "\n".join(f"- {r}" for r in result.reasons)
            await interaction.response.send_message(
                f"Your bio didn't pass our content filter:\n{reasons}\n\n"
                "Please try again with a different bio.",
                ephemeral=True,
            )
            return

        # Fuzzy match location to region
        region_key = _match_region(self.location.value, self.bot.config.get("location_mapping", {}))

        # Check submission count
        intro_repo = IntroRepository(self.bot.db)
        user_repo = UserRepository(self.bot.db)
        count = await intro_repo.count_for_user(interaction.user.id)

        if count >= 2:
            await interaction.response.send_message(
                "You've already submitted the maximum number of intros (2). "
                "Please open a support ticket if you need help.",
                ephemeral=True,
            )
            return

        # Create intro
        await user_repo.upsert(interaction.user.id, username=str(interaction.user))
        intro_id = await intro_repo.create(
            user_id=interaction.user.id,
            age=age_val,
            preferred_name=self.preferred_name.value,
            pronouns=self.pronouns.value,
            location=self.location.value,
            region_key=region_key,
            bio=self.bio.value,
            submission_num=count + 1,
        )
        status = IntroStatus.RESUBMITTED if count > 0 else IntroStatus.SUBMITTED
        await intro_repo.update_status(intro_id, status)
        await user_repo.set_intro_status(interaction.user.id, status)

        # DM confirmation
        await interaction.response.send_message(
            "Your intro has been submitted for review! "
            "You'll receive a DM when staff have reviewed it.",
            ephemeral=True,
        )

        # Post to staff review channel
        review_channel_id = self.bot.config.channels.get("staff_review")
        if review_channel_id:
            channel = self.bot.get_channel(review_channel_id)
            if channel and isinstance(channel, discord.TextChannel):
                # Account age warning
                account_age = (discord.utils.utcnow() - interaction.user.created_at).days
                age_warning = ""
                if account_age < 7:
                    age_warning = "\n\u26a0\ufe0f **New Account** (created {account_age} days ago)"

                embed = self.bot.embed_builder.staff(
                    title=f"Intro Review — {interaction.user}",
                )
                embed.set_thumbnail(url=interaction.user.display_avatar.url)
                embed.add_field(name="Age", value=str(age_val), inline=True)
                embed.add_field(name="Preferred Name", value=self.preferred_name.value, inline=True)
                embed.add_field(name="Pronouns", value=self.pronouns.value, inline=True)
                embed.add_field(name="Location", value=self.location.value, inline=True)
                embed.add_field(name="Region", value=region_key or "Unknown", inline=True)
                embed.add_field(name="Submission #", value=str(count + 1), inline=True)
                embed.add_field(name="Bio", value=self.bio.value, inline=False)
                if age_warning:
                    embed.add_field(
                        name="Warnings",
                        value=f"\u26a0\ufe0f Account created {account_age} days ago",
                        inline=False,
                    )
                embed.set_footer(text=f"User ID: {interaction.user.id} | Intro ID: {intro_id}")

                # Create review view with DynamicItem buttons
                view = discord.ui.View(timeout=None)
                for action in ["approve", "reject", "reject_info", "kick", "ban"]:
                    view.add_item(IntroReviewView.ReviewButton(intro_id, action).item)

                await channel.send(embed=embed, view=view)

        await self.bot.audit_logger.log(
            "intro_submitted", target_id=interaction.user.id,
            details={"intro_id": intro_id, "submission_num": count + 1},
        )


def _match_region(location: str, mapping: dict[str, list[str]]) -> str | None:
    """Fuzzy match a location string to a region key."""
    if not mapping:
        return None

    location_lower = location.lower().strip()

    # Build flat list of (keyword, region_key)
    candidates: list[tuple[str, str]] = []
    for region_key, keywords in mapping.items():
        for keyword in keywords:
            candidates.append((keyword.lower(), region_key))

    if not candidates:
        return None

    # Try exact substring match first
    for keyword, region_key in candidates:
        if keyword in location_lower:
            return region_key

    # Fuzzy match
    keywords_only = [c[0] for c in candidates]
    match = process.extractOne(location_lower, keywords_only, scorer=fuzz.WRatio, score_cutoff=70)
    if match:
        matched_keyword = match[0]
        for keyword, region_key in candidates:
            if keyword == matched_keyword:
                return region_key

    return "region_other"


class IntrosCog(commands.Cog, name="IntrosCog"):
    """Release 2: Full intro system with modal, review, welcome."""

    def __init__(self, bot: GayborhoodBot):
        self.bot = bot

    async def start_intro(self, interaction: discord.Interaction):
        """Called from onboarding/panel views."""
        # Check if user has agreed to rules
        user_repo = UserRepository(self.bot.db)
        user = await user_repo.get(interaction.user.id)
        if not user or not user.rules_agreed:
            await interaction.response.send_message(
                "Please agree to the rules first before starting your intro.",
                ephemeral=True,
            )
            return

        # Check if already approved
        if user.intro_status == IntroStatus.APPROVED:
            await interaction.response.send_message(
                "Your intro has already been approved!", ephemeral=True,
            )
            return

        # Check if pending review
        if user.intro_status in (IntroStatus.SUBMITTED, IntroStatus.RESUBMITTED):
            await interaction.response.send_message(
                "Your intro is currently under review. Please wait for staff to respond.",
                ephemeral=True,
            )
            return

        modal = IntroModal(self.bot)
        await interaction.response.send_modal(modal)


async def setup(bot: GayborhoodBot):
    await bot.add_cog(IntrosCog(bot))
