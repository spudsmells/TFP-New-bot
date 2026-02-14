from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord

from core.constants import TicketStatus, TicketLogEvent
from database.repositories.tickets import TicketRepository
from database.repositories.ticket_logs import TicketLogRepository
from views.common import PersistentView

if TYPE_CHECKING:
    from core.bot import GayborhoodBot

logger = logging.getLogger(__name__)


class TicketActionsView(PersistentView):
    """Buttons inside every ticket channel: Claim, Close, Mute."""

    def __init__(self, bot: GayborhoodBot):
        super().__init__(bot)

    @discord.ui.button(
        label="Claim Ticket",
        style=discord.ButtonStyle.primary,
        custom_id="ticket:claim",
        emoji="\U0001f3f7\ufe0f",
        row=0,
    )
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket_repo = TicketRepository(self.bot.db)
        log_repo = TicketLogRepository(self.bot.db)

        ticket = await ticket_repo.get_by_channel(interaction.channel_id)
        if not ticket:
            await interaction.response.send_message("No ticket found for this channel.", ephemeral=True)
            return

        # Check staff role
        staff_role_id = self.bot.config.roles.get("staff")
        if staff_role_id and not any(r.id == staff_role_id for r in interaction.user.roles):
            await interaction.response.send_message("Only staff can claim tickets.", ephemeral=True)
            return

        if ticket.claimed_by:
            claimer = self.bot.get_user(ticket.claimed_by)
            name = str(claimer) if claimer else f"User {ticket.claimed_by}"
            await interaction.response.send_message(
                f"This ticket is already claimed by {name}.", ephemeral=True,
            )
            return

        await ticket_repo.claim(ticket.id, interaction.user.id)
        await log_repo.add(ticket.id, TicketLogEvent.CLAIMED, interaction.user.id)
        await self.bot.audit_logger.log(
            "ticket_claimed", actor_id=interaction.user.id,
            details={"ticket_id": ticket.id},
        )

        embed = self.bot.embed_builder.info(
            description=f"\U0001f3f7\ufe0f **{interaction.user.display_name}** claimed this ticket.",
        )
        await interaction.response.send_message(embed=embed)

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.danger,
        custom_id="ticket:close",
        emoji="\U0001f512",
        row=0,
    )
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket_repo = TicketRepository(self.bot.db)
        log_repo = TicketLogRepository(self.bot.db)

        ticket = await ticket_repo.get_by_channel(interaction.channel_id)
        if not ticket:
            await interaction.response.send_message("No ticket found for this channel.", ephemeral=True)
            return

        # Staff can always close; members can only close their own within window
        staff_role_id = self.bot.config.roles.get("staff")
        is_staff = staff_role_id and any(r.id == staff_role_id for r in interaction.user.roles)
        is_owner = interaction.user.id == ticket.owner_id

        if not is_staff and not is_owner:
            await interaction.response.send_message("You cannot close this ticket.", ephemeral=True)
            return

        if is_owner and not is_staff and ticket.ticket_type == "member":
            from datetime import datetime, timezone
            created = datetime.fromisoformat(ticket.created_at).replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            window_hours = self.bot.config.get("tickets", {}).get("member_close_window_hours", 2)
            if (now - created).total_seconds() > window_hours * 3600:
                await interaction.response.send_message(
                    "The close window has expired. Please ask staff to close this ticket.",
                    ephemeral=True,
                )
                return

        await ticket_repo.close(ticket.id, interaction.user.id)
        await log_repo.add(ticket.id, TicketLogEvent.CLOSED, interaction.user.id)

        # Cancel any active timers for this ticket
        await self.bot.timer_service.cancel_timers_for("ticket_member_nudge", str(ticket.id))
        await self.bot.timer_service.cancel_timers_for("ticket_staff_reminder", str(ticket.id))

        await self.bot.audit_logger.log(
            "ticket_closed", actor_id=interaction.user.id,
            details={"ticket_id": ticket.id},
        )

        embed = self.bot.embed_builder.info(
            description=f"\U0001f512 Ticket closed by **{interaction.user.display_name}**.",
        )
        await interaction.response.send_message(embed=embed)

        # Archive channel
        archive_cat_id = self.bot.config.channels.get("ticket_archive_category")
        if archive_cat_id and isinstance(interaction.channel, discord.TextChannel):
            category = interaction.guild.get_channel(archive_cat_id)
            if category and isinstance(category, discord.CategoryChannel):
                try:
                    await interaction.channel.edit(category=category, sync_permissions=True)
                    await ticket_repo.archive(ticket.id)
                    await log_repo.add(ticket.id, TicketLogEvent.ARCHIVED, interaction.user.id)
                except discord.Forbidden:
                    logger.error("Cannot move ticket channel to archive category")

    @discord.ui.button(
        label="Mute Member",
        style=discord.ButtonStyle.secondary,
        custom_id="ticket:mute",
        emoji="\U0001f507",
        row=0,
    )
    async def mute_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket_repo = TicketRepository(self.bot.db)
        log_repo = TicketLogRepository(self.bot.db)

        ticket = await ticket_repo.get_by_channel(interaction.channel_id)
        if not ticket:
            await interaction.response.send_message("No ticket found.", ephemeral=True)
            return

        staff_role_id = self.bot.config.roles.get("staff")
        if staff_role_id and not any(r.id == staff_role_id for r in interaction.user.roles):
            await interaction.response.send_message("Only staff can mute.", ephemeral=True)
            return

        if ticket.muted:
            # Unmute
            await ticket_repo.set_muted(ticket.id, False)
            await log_repo.add(ticket.id, TicketLogEvent.UNMUTED, interaction.user.id)
            # Remove send message deny for owner
            if isinstance(interaction.channel, discord.TextChannel):
                member = interaction.guild.get_member(ticket.owner_id)
                if member:
                    await interaction.channel.set_permissions(member, send_messages=None)
            embed = self.bot.embed_builder.info(description="\U0001f50a Member unmuted in this ticket.")
            await interaction.response.send_message(embed=embed)
        else:
            # Mute
            mute_minutes = self.bot.config.get("tickets", {}).get("mute_default_minutes", 30)
            from datetime import datetime, timedelta, timezone
            expires = datetime.now(timezone.utc) + timedelta(minutes=mute_minutes)
            await ticket_repo.set_muted(ticket.id, True, expires.isoformat())
            await log_repo.add(ticket.id, TicketLogEvent.MUTED, interaction.user.id)

            # Deny send messages for owner
            if isinstance(interaction.channel, discord.TextChannel):
                member = interaction.guild.get_member(ticket.owner_id)
                if member:
                    await interaction.channel.set_permissions(member, send_messages=False)

            # Create unmute timer
            await self.bot.timer_service.create_timer(
                "ticket_mute_expire",
                delay_seconds=mute_minutes * 60,
                payload={"ticket_id": ticket.id, "channel_id": interaction.channel_id},
            )

            embed = self.bot.embed_builder.warning(
                description=f"\U0001f507 Member muted for {mute_minutes} minutes.",
            )
            await interaction.response.send_message(embed=embed)
