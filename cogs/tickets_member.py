from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from core.constants import TicketType, TicketLogEvent
from database.repositories.tickets import TicketRepository
from database.repositories.ticket_logs import TicketLogRepository
from views.ticket_actions import TicketActionsView

if TYPE_CHECKING:
    from core.bot import GayborhoodBot

logger = logging.getLogger(__name__)


class TicketReasonModal(discord.ui.Modal, title="Open Support Ticket"):
    reason = discord.ui.TextInput(
        label="What do you need help with?",
        style=discord.TextStyle.paragraph,
        placeholder="Describe your issue in detail (20-1000 characters)...",
        min_length=20,
        max_length=1000,
    )

    def __init__(self, bot: GayborhoodBot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        # Content filter
        result = self.bot.content_filter.validate_ticket_reason(self.reason.value)
        if not result.passed:
            reasons = "\n".join(f"- {r}" for r in result.reasons)
            await interaction.response.send_message(
                f"Your reason didn't pass validation:\n{reasons}", ephemeral=True,
            )
            return

        ticket_repo = TicketRepository(self.bot.db)
        log_repo = TicketLogRepository(self.bot.db)

        # Check for existing open ticket
        existing = await ticket_repo.get_open_for_user(interaction.user.id)
        if existing:
            await interaction.response.send_message(
                f"You already have an open ticket. Please use that one first.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        # Create ticket channel
        guild = interaction.guild or self.bot.guild
        if not guild:
            await interaction.followup.send("Server not found.", ephemeral=True)
            return

        category_id = self.bot.config.channels.get("ticket_category")
        category = guild.get_channel(category_id) if category_id else None

        # Permissions
        staff_role_id = self.bot.config.roles.get("staff")
        staff_role = guild.get_role(staff_role_id) if staff_role_id else None

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

        channel_name = f"ticket-{interaction.user.name[:20]}"
        try:
            channel = await guild.create_text_channel(
                name=channel_name,
                category=category if isinstance(category, discord.CategoryChannel) else None,
                overwrites=overwrites,
                reason=f"Support ticket by {interaction.user}",
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "I don't have permission to create ticket channels.", ephemeral=True,
            )
            return

        # Save to DB
        ticket_id = await ticket_repo.create(
            channel_id=channel.id,
            ticket_type=TicketType.MEMBER,
            owner_id=interaction.user.id,
            opener_id=interaction.user.id,
            reason=self.reason.value,
        )
        await log_repo.add(ticket_id, TicketLogEvent.CREATED, interaction.user.id)

        # Send ticket embed
        embed = self.bot.embed_builder.ticket(
            title=f"Support Ticket #{ticket_id}",
            description=f"**Opened by:** {interaction.user.mention}\n**Reason:** {self.reason.value}",
        )
        embed.set_footer(text="Staff will be with you shortly. Use the buttons below for actions.")

        view = TicketActionsView(self.bot)
        await channel.send(embed=embed, view=view)

        # Set up nudge timer (2 hours)
        nudge_hours = self.bot.config.get("tickets", {}).get("member_nudge_hours", 2)
        await self.bot.timer_service.create_timer(
            "ticket_member_nudge",
            delay_seconds=nudge_hours * 3600,
            payload={"ticket_id": ticket_id, "channel_id": channel.id, "owner_id": interaction.user.id},
        )

        # DM confirmation
        dm_embed = self.bot.embed_builder.success(
            title="Ticket Created!",
            description=f"Your support ticket has been created: {channel.mention}",
        )
        await self.bot.dm_service.send(interaction.user, embed=dm_embed)

        await interaction.followup.send(
            f"Your ticket has been created: {channel.mention}", ephemeral=True,
        )

        await self.bot.audit_logger.log(
            "ticket_created", actor_id=interaction.user.id,
            details={"ticket_id": ticket_id, "type": "member"},
        )


class TicketsMemberCog(commands.Cog, name="TicketsMemberCog"):
    """Release 3: Member ticket creation."""

    def __init__(self, bot: GayborhoodBot):
        self.bot = bot

    async def cog_load(self):
        # Register nudge timer handler
        self.bot.timer_service.register_handler("ticket_member_nudge", self._handle_nudge)

    async def _handle_nudge(self, timer_id: int, payload: dict):
        """Send a nudge to the ticket channel if no staff has responded."""
        ticket_repo = TicketRepository(self.bot.db)
        ticket_id = payload.get("ticket_id")
        channel_id = payload.get("channel_id")

        if not ticket_id or not channel_id:
            return

        ticket = await ticket_repo.get(ticket_id)
        if not ticket or ticket.status not in ("open",):
            return  # Already claimed or closed

        channel = self.bot.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        await ticket_repo.increment_nudge(ticket_id)

        embed = self.bot.embed_builder.warning(
            description=(
                "\u23f0 This ticket has been open for a while without a staff response.\n"
                "Staff, please claim this ticket when available."
            ),
        )
        await channel.send(embed=embed)

        # Alert staff
        alert_channel_id = self.bot.config.channels.get("staff_alerts")
        if alert_channel_id:
            alert_channel = self.bot.get_channel(alert_channel_id)
            if alert_channel and isinstance(alert_channel, discord.TextChannel):
                await alert_channel.send(
                    f"\u23f0 Unclaimed ticket needs attention: {channel.mention}",
                )

    async def open_ticket_from_dm(self, interaction: discord.Interaction):
        """Called from onboarding DM panel."""
        modal = TicketReasonModal(self.bot)
        await interaction.response.send_modal(modal)

    async def open_ticket_from_panel(self, interaction: discord.Interaction):
        """Called from server panel."""
        modal = TicketReasonModal(self.bot)
        await interaction.response.send_modal(modal)


async def setup(bot: GayborhoodBot):
    await bot.add_cog(TicketsMemberCog(bot))
