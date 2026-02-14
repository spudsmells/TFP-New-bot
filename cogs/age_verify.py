from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from core.constants import TicketType, TicketLogEvent
from database.repositories.tickets import TicketRepository
from database.repositories.ticket_logs import TicketLogRepository
from database.repositories.users import UserRepository
from views.ticket_actions import TicketActionsView

if TYPE_CHECKING:
    from core.bot import GayborhoodBot

logger = logging.getLogger(__name__)


class AgeVerifyCog(commands.Cog, name="AgeVerifyCog"):
    """Release 6: Age verification via ticket."""

    def __init__(self, bot: GayborhoodBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_milestone_reached(self, user_id: int, level: int):
        """Send DM when user reaches age verify level."""
        required = self.bot.config.xp.get("age_verify_level", 15)
        if level != required:
            return

        user_repo = UserRepository(self.bot.db)
        user = await user_repo.get(user_id)
        if not user or user.age_verified:
            return

        discord_user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
        if not discord_user:
            return

        embed = self.bot.embed_builder.info(
            title=f"\U0001f389 You've reached Level {level}!",
            description=(
                "You're now eligible for **age verification**!\n\n"
                "Age-verified members get access to additional channels and features.\n"
                "You can start the process using the Age Verify button in your DM panel "
                "or in the #ticket-booth channel."
            ),
        )
        await self.bot.dm_service.send(discord_user, embed=embed)

    async def start_verify(self, interaction: discord.Interaction):
        """Entry point from views."""
        user_repo = UserRepository(self.bot.db)
        user = await user_repo.get(interaction.user.id)

        if not user:
            await interaction.response.send_message(
                "Please complete onboarding first.", ephemeral=True,
            )
            return

        if user.age_verified:
            await interaction.response.send_message(
                "You're already age verified!", ephemeral=True,
            )
            return

        required = self.bot.config.xp.get("age_verify_level", 15)
        if user.level < required:
            await interaction.response.send_message(
                f"You need to be **Level {required}** to request age verification. "
                f"You're currently Level {user.level}.",
                ephemeral=True,
            )
            return

        # Pre-screen message
        embed = self.bot.embed_builder.info(
            title="Age Verification",
            description=(
                "**Before you begin:**\n\n"
                "Age verification requires you to show a valid government-issued ID "
                "to a staff member in a private ticket. Your ID will not be stored.\n\n"
                "**Requirements:**\n"
                "- Government-issued photo ID\n"
                "- Must clearly show your date of birth\n"
                "- You may cover your name and photo if you wish\n\n"
                "Ready to proceed?"
            ),
        )

        view = discord.ui.View(timeout=120)

        async def confirm_callback(confirm_interaction: discord.Interaction):
            await self.create_verify_ticket(confirm_interaction)

        async def cancel_callback(cancel_interaction: discord.Interaction):
            await cancel_interaction.response.send_message("Age verification cancelled.", ephemeral=True)

        confirm_btn = discord.ui.Button(label="Proceed", style=discord.ButtonStyle.success)
        confirm_btn.callback = confirm_callback

        cancel_btn = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.secondary)
        cancel_btn.callback = cancel_callback

        view.add_item(confirm_btn)
        view.add_item(cancel_btn)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def create_verify_ticket(self, interaction: discord.Interaction):
        """Create the age verification ticket."""
        ticket_repo = TicketRepository(self.bot.db)
        log_repo = TicketLogRepository(self.bot.db)

        # Check for existing ticket
        existing = await ticket_repo.get_open_for_user(interaction.user.id)
        if existing:
            await interaction.response.send_message(
                "You already have an open ticket. Please use that one.",
                ephemeral=True,
            )
            return

        if interaction.response.is_done():
            await interaction.followup.send("Creating your verification ticket...", ephemeral=True)
        else:
            await interaction.response.defer(ephemeral=True)

        guild = interaction.guild or self.bot.guild
        if not guild:
            return

        category_id = self.bot.config.channels.get("ticket_category")
        category = guild.get_channel(category_id) if category_id else None

        staff_role_id = self.bot.config.roles.get("staff")
        staff_role = guild.get_role(staff_role_id) if staff_role_id else None

        import random
        suffix = random.randint(1000, 9999)
        channel_name = f"ageverify-{interaction.user.name[:15]}-{suffix}"

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(
                read_messages=True, send_messages=True, attach_files=True,
            ),
            guild.me: discord.PermissionOverwrite(
                read_messages=True, send_messages=True, manage_channels=True,
            ),
        }
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(
                read_messages=True, send_messages=True,
            )

        try:
            channel = await guild.create_text_channel(
                name=channel_name,
                category=category if isinstance(category, discord.CategoryChannel) else None,
                overwrites=overwrites,
                reason=f"Age verification for {interaction.user}",
            )
        except discord.Forbidden:
            await interaction.followup.send("Missing permissions.", ephemeral=True)
            return

        ticket_id = await ticket_repo.create(
            channel_id=channel.id,
            ticket_type=TicketType.AGE_VERIFY,
            owner_id=interaction.user.id,
            opener_id=interaction.user.id,
            reason="Age verification request",
        )
        await log_repo.add(ticket_id, TicketLogEvent.CREATED, interaction.user.id)

        embed = self.bot.embed_builder.ticket(
            title=f"Age Verification #{ticket_id}",
            description=(
                f"**Member:** {interaction.user.mention}\n\n"
                "Please upload a photo of your government-issued ID showing your date of birth.\n"
                "You may cover your name and photo if you wish.\n\n"
                "A staff member will review your submission."
            ),
        )
        view = TicketActionsView(self.bot)
        await channel.send(embed=embed, view=view)

        await interaction.followup.send(
            f"Your verification ticket has been created: {channel.mention}",
            ephemeral=True,
        )

        await self.bot.audit_logger.log(
            "age_verify_ticket", actor_id=interaction.user.id,
            details={"ticket_id": ticket_id},
        )


async def setup(bot: GayborhoodBot):
    await bot.add_cog(AgeVerifyCog(bot))
