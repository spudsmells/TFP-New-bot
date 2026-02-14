from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

import discord

from core.constants import IntroStatus, UserStatus
from database.repositories.intros import IntroRepository
from database.repositories.users import UserRepository
from views.common import PersistentView

if TYPE_CHECKING:
    from core.bot import GayborhoodBot

logger = logging.getLogger(__name__)


class RejectReasonModal(discord.ui.Modal, title="Rejection Reason"):
    reason = discord.ui.TextInput(
        label="Reason (sent to user)",
        style=discord.TextStyle.paragraph,
        placeholder="Explain why the intro was rejected...",
        min_length=10,
        max_length=500,
    )

    def __init__(self, bot: GayborhoodBot, intro_id: int, action: str):
        super().__init__()
        self.bot = bot
        self.intro_id = intro_id
        self.action = action

    async def on_submit(self, interaction: discord.Interaction):
        intro_repo = IntroRepository(self.bot.db)
        user_repo = UserRepository(self.bot.db)
        intro = await intro_repo.get(self.intro_id)
        if not intro:
            await interaction.response.send_message("Intro not found.", ephemeral=True)
            return

        reason = self.reason.value

        if self.action == "reject":
            await intro_repo.update_status(
                self.intro_id, IntroStatus.REJECTED,
                reviewer_id=interaction.user.id,
                review_action="rejected",
                review_reason=reason,
            )
            await user_repo.set_intro_status(intro.user_id, IntroStatus.REJECTED)

            # Check if user can resubmit (max 2 submissions)
            count = await intro_repo.count_for_user(intro.user_id)
            can_resubmit = count < 2

            user = self.bot.get_user(intro.user_id) or await self.bot.fetch_user(intro.user_id)
            if user:
                embed = self.bot.embed_builder.warning(
                    title="Intro Rejected",
                    description=f"**Reason:** {reason}",
                )
                if can_resubmit:
                    embed.add_field(
                        name="What's next?",
                        value="You can submit a corrected intro using the Start Intro button.",
                        inline=False,
                    )
                else:
                    embed.add_field(
                        name="What's next?",
                        value="You've used all your submission attempts. Please contact staff via a support ticket.",
                        inline=False,
                    )
                await self.bot.dm_service.send(user, embed=embed)

        elif self.action == "kick":
            await intro_repo.update_status(
                self.intro_id, IntroStatus.REJECTED,
                reviewer_id=interaction.user.id,
                review_action="kicked",
                review_reason=reason,
            )
            await user_repo.set_status(intro.user_id, UserStatus.KICKED)
            guild = self.bot.guild
            if guild:
                member = guild.get_member(intro.user_id)
                if member:
                    try:
                        await member.kick(reason=f"Intro rejected: {reason}")
                    except discord.Forbidden:
                        logger.error("Cannot kick %d: missing permissions", intro.user_id)

        elif self.action == "ban":
            await intro_repo.update_status(
                self.intro_id, IntroStatus.REJECTED,
                reviewer_id=interaction.user.id,
                review_action="banned",
                review_reason=reason,
            )
            await user_repo.set_status(intro.user_id, UserStatus.BANNED)
            guild = self.bot.guild
            if guild:
                member = guild.get_member(intro.user_id)
                if member:
                    try:
                        await member.ban(reason=f"Intro rejected: {reason}")
                    except discord.Forbidden:
                        logger.error("Cannot ban %d: missing permissions", intro.user_id)

        await self.bot.audit_logger.log(
            f"intro_{self.action}", actor_id=interaction.user.id,
            target_id=intro.user_id,
            details={"intro_id": self.intro_id, "reason": reason},
        )

        # Update the review embed
        embed = interaction.message.embeds[0] if interaction.message.embeds else discord.Embed()
        embed.color = discord.Color.red()
        embed.set_footer(text=f"{self.action.title()}d by {interaction.user} | {reason}")
        await interaction.response.edit_message(embed=embed, view=None)


class IntroReviewView(PersistentView):
    """Staff review panel for intro submissions."""

    class ReviewButton(discord.ui.DynamicItem[discord.ui.Button],
                       template=r"intro_review:(?P<intro_id>\d+):(?P<action>\w+)"):

        def __init__(self, intro_id: int, action: str):
            self.intro_id = intro_id
            self.action = action
            style_map = {
                "approve": discord.ButtonStyle.success,
                "reject": discord.ButtonStyle.danger,
                "reject_info": discord.ButtonStyle.secondary,
                "kick": discord.ButtonStyle.danger,
                "ban": discord.ButtonStyle.danger,
            }
            label_map = {
                "approve": "Approve",
                "reject": "Reject",
                "reject_info": "Reject & Request Info",
                "kick": "Kick",
                "ban": "Ban",
            }
            super().__init__(
                discord.ui.Button(
                    style=style_map.get(action, discord.ButtonStyle.secondary),
                    label=label_map.get(action, action.title()),
                    custom_id=f"intro_review:{intro_id}:{action}",
                )
            )

        @classmethod
        async def from_custom_id(cls, interaction: discord.Interaction,
                                 item: discord.ui.Button, match: re.Match):
            intro_id = int(match["intro_id"])
            action = match["action"]
            return cls(intro_id, action)

        async def callback(self, interaction: discord.Interaction):
            bot: GayborhoodBot = interaction.client  # type: ignore

            # Approve doesn't need a modal
            if self.action == "approve":
                await _handle_approve(bot, interaction, self.intro_id)
                return

            # All others need a reason
            modal = RejectReasonModal(bot, self.intro_id, self.action)
            await interaction.response.send_modal(modal)

    def __init__(self, bot: GayborhoodBot):
        super().__init__(bot)


async def _handle_approve(bot: GayborhoodBot, interaction: discord.Interaction, intro_id: int):
    """Handle intro approval: assign roles, post welcome, award XP."""
    intro_repo = IntroRepository(bot.db)
    user_repo = UserRepository(bot.db)

    intro = await intro_repo.get(intro_id)
    if not intro:
        await interaction.response.send_message("Intro not found.", ephemeral=True)
        return

    # Update DB
    await intro_repo.update_status(
        intro_id, IntroStatus.APPROVED,
        reviewer_id=interaction.user.id,
        review_action="approved",
    )
    await user_repo.set_status(intro.user_id, UserStatus.APPROVED)
    await user_repo.set_intro_status(intro.user_id, IntroStatus.APPROVED)

    guild = bot.guild
    if guild:
        member = guild.get_member(intro.user_id)
        if member:
            # Swap Pending -> Gaybor
            await bot.role_service.swap_roles(
                member,
                remove_id=bot.config.roles["pending"],
                add_id=bot.config.roles["gaybor"],
                reason="Intro approved",
            )

            # Assign regional role if available
            if intro.region_key and intro.region_key in bot.config.roles:
                await bot.role_service.add_role(
                    member, bot.config.roles[intro.region_key],
                    reason=f"Region: {intro.region_key}",
                )

    # DM user
    user = bot.get_user(intro.user_id) or await bot.fetch_user(intro.user_id)
    if user:
        embed = bot.embed_builder.success(
            title="Welcome to The Gayborhood!",
            description="Your intro has been approved! You now have full access to the server.",
        )
        await bot.dm_service.send(user, embed=embed)

    # Post welcome in welcome channel
    welcome_channel_id = bot.config.channels.get("welcome")
    if welcome_channel_id:
        channel = bot.get_channel(welcome_channel_id)
        if channel and isinstance(channel, discord.TextChannel):
            welcome_text = bot.welcome_generator.generate(
                name=intro.preferred_name or str(user),
                pronouns=intro.pronouns or "",
                location=intro.location or "",
            )
            welcome_embed = bot.embed_builder.welcome(description=welcome_text)
            if user:
                welcome_embed.set_author(name=str(user), icon_url=user.display_avatar.url)

            welcome_msg = await channel.send(embed=welcome_embed)

            # Post intro details below
            intro_embed = bot.embed_builder.info(title=f"About {intro.preferred_name or 'them'}")
            intro_embed.add_field(name="Pronouns", value=intro.pronouns or "Not specified", inline=True)
            intro_embed.add_field(name="Location", value=intro.location or "Not specified", inline=True)
            intro_embed.add_field(name="Bio", value=intro.bio or "No bio provided", inline=False)
            intro_msg = await channel.send(embed=intro_embed)

            await intro_repo.set_welcome_messages(intro_id, welcome_msg.id, intro_msg.id)

    # Award XP bonus
    from database.repositories.xp import XPRepository
    xp_repo = XPRepository(bot.db)
    xp_bonus = bot.config.xp.get("intro_bonus", 50)
    await xp_repo.add(intro.user_id, xp_bonus, "bonus", "Intro approved")

    db_user = await user_repo.get(intro.user_id)
    if db_user:
        new_total = db_user.total_xp + xp_bonus
        new_level = bot.xp_calculator.calculate_level(new_total)
        await user_repo.add_xp(intro.user_id, xp_bonus, new_level)

    await bot.audit_logger.log(
        "intro_approved", actor_id=interaction.user.id,
        target_id=intro.user_id, details={"intro_id": intro_id},
    )

    # Update review embed
    embed = interaction.message.embeds[0] if interaction.message.embeds else discord.Embed()
    embed.color = discord.Color.green()
    embed.set_footer(text=f"Approved by {interaction.user}")
    await interaction.response.edit_message(embed=embed, view=None)
