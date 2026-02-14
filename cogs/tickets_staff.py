from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from core.constants import TicketType, TicketLogEvent
from database.repositories.tickets import TicketRepository
from database.repositories.ticket_logs import TicketLogRepository
from views.ticket_actions import TicketActionsView

if TYPE_CHECKING:
    from core.bot import GayborhoodBot

logger = logging.getLogger(__name__)


class StaffTicketReasonModal(discord.ui.Modal, title="Create Staff Ticket"):
    reason = discord.ui.TextInput(
        label="Reason (optional)",
        style=discord.TextStyle.paragraph,
        placeholder="Why are you opening a ticket for this member?",
        required=False,
        max_length=1000,
    )

    def __init__(self, bot: GayborhoodBot, target: discord.Member):
        super().__init__()
        self.bot = bot
        self.target = target

    async def on_submit(self, interaction: discord.Interaction):
        ticket_repo = TicketRepository(self.bot.db)
        log_repo = TicketLogRepository(self.bot.db)

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild or self.bot.guild
        if not guild:
            return

        category_id = self.bot.config.channels.get("ticket_category")
        category = guild.get_channel(category_id) if category_id else None

        staff_role_id = self.bot.config.roles.get("staff")
        staff_role = guild.get_role(staff_role_id) if staff_role_id else None

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            self.target: discord.PermissionOverwrite(
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

        channel_name = f"staff-{self.target.name[:20]}"
        try:
            channel = await guild.create_text_channel(
                name=channel_name,
                category=category if isinstance(category, discord.CategoryChannel) else None,
                overwrites=overwrites,
                reason=f"Staff ticket for {self.target} by {interaction.user}",
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "Missing permissions to create channel.", ephemeral=True,
            )
            return

        ticket_id = await ticket_repo.create(
            channel_id=channel.id,
            ticket_type=TicketType.STAFF,
            owner_id=self.target.id,
            opener_id=interaction.user.id,
            reason=self.reason.value or None,
        )
        await log_repo.add(ticket_id, TicketLogEvent.CREATED, interaction.user.id)

        # Auto-claim by creator
        await ticket_repo.claim(ticket_id, interaction.user.id)
        await log_repo.add(ticket_id, TicketLogEvent.CLAIMED, interaction.user.id)

        embed = self.bot.embed_builder.ticket(
            title=f"Staff Ticket #{ticket_id}",
            description=(
                f"**Member:** {self.target.mention}\n"
                f"**Opened by:** {interaction.user.mention}\n"
                f"**Reason:** {self.reason.value or 'No reason provided'}"
            ),
        )
        view = TicketActionsView(self.bot)
        await channel.send(embed=embed, view=view)

        # Notify member via DM
        dm_embed = self.bot.embed_builder.info(
            title="Staff Ticket Opened",
            description=f"A staff member has opened a ticket with you: {channel.mention}",
        )
        await self.bot.dm_service.send(self.target, embed=dm_embed)

        # Staff reminder timer (12 hours)
        reminder_hours = self.bot.config.get("tickets", {}).get("staff_reminder_hours", 12)
        await self.bot.timer_service.create_timer(
            "ticket_staff_reminder",
            delay_seconds=reminder_hours * 3600,
            payload={"ticket_id": ticket_id, "channel_id": channel.id, "staff_id": interaction.user.id},
        )

        await interaction.followup.send(
            f"Staff ticket created: {channel.mention}", ephemeral=True,
        )

        await self.bot.audit_logger.log(
            "ticket_created", actor_id=interaction.user.id,
            target_id=self.target.id,
            details={"ticket_id": ticket_id, "type": "staff"},
        )


class TicketsStaffCog(commands.Cog, name="TicketsStaffCog"):
    """Releases 4-5: Staff ticket features."""

    def __init__(self, bot: GayborhoodBot):
        self.bot = bot

    async def cog_load(self):
        self.bot.timer_service.register_handler("ticket_staff_reminder", self._handle_reminder)

    async def _handle_reminder(self, timer_id: int, payload: dict):
        """Remind staff about their open ticket."""
        channel_id = payload.get("channel_id")
        staff_id = payload.get("staff_id")
        ticket_id = payload.get("ticket_id")

        if not channel_id or not ticket_id:
            return

        ticket_repo = TicketRepository(self.bot.db)
        ticket = await ticket_repo.get(ticket_id)
        if not ticket or ticket.status in ("closed", "archived"):
            return

        channel = self.bot.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        mention = f"<@{staff_id}>" if staff_id else "Staff"
        embed = self.bot.embed_builder.warning(
            description=f"\u23f0 {mention}, this staff ticket has been open for a while. Please follow up.",
        )
        await channel.send(embed=embed)

    @app_commands.command(name="ticket-create", description="Open a ticket for a member (Staff)")
    @app_commands.describe(member="Target member")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def ticket_create(self, interaction: discord.Interaction, member: discord.Member):
        modal = StaffTicketReasonModal(self.bot, member)
        await interaction.response.send_modal(modal)

    @app_commands.command(name="ticket-add", description="Add a member to the current ticket (Staff)")
    @app_commands.describe(member="Member to add")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def ticket_add(self, interaction: discord.Interaction, member: discord.Member):
        ticket_repo = TicketRepository(self.bot.db)
        ticket = await ticket_repo.get_by_channel(interaction.channel_id)

        if not ticket:
            await interaction.response.send_message("This isn't a ticket channel.", ephemeral=True)
            return

        if isinstance(interaction.channel, discord.TextChannel):
            await interaction.channel.set_permissions(
                member, read_messages=True, send_messages=True,
            )

            log_repo = TicketLogRepository(self.bot.db)
            await log_repo.add(ticket.id, TicketLogEvent.MEMBER_ADDED, interaction.user.id,
                               f"Added {member}")

            # DM the added member
            dm_embed = self.bot.embed_builder.info(
                title="Added to Ticket",
                description=f"You've been added to a ticket: {interaction.channel.mention}",
            )
            await self.bot.dm_service.send(member, embed=dm_embed)

            await interaction.response.send_message(
                f"{member.mention} has been added to this ticket.", ephemeral=True,
            )

    @app_commands.command(name="ticket-list", description="List open tickets (Staff)")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def ticket_list(self, interaction: discord.Interaction):
        ticket_repo = TicketRepository(self.bot.db)
        tickets = await ticket_repo.get_open_tickets()

        if not tickets:
            await interaction.response.send_message("No open tickets.", ephemeral=True)
            return

        lines = []
        for t in tickets[:20]:
            channel = self.bot.get_channel(t.channel_id) if t.channel_id else None
            ch_str = channel.mention if channel else f"#{t.channel_id}"
            owner = self.bot.get_user(t.owner_id)
            owner_str = str(owner) if owner else f"User {t.owner_id}"
            status = t.status
            if t.claimed_by:
                claimer = self.bot.get_user(t.claimed_by)
                status += f" (claimed by {claimer or t.claimed_by})"
            lines.append(f"**#{t.id}** {ch_str} | {owner_str} | {status}")

        embed = self.bot.embed_builder.info(
            title=f"Open Tickets ({len(tickets)})",
            description="\n".join(lines),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: GayborhoodBot):
    await bot.add_cog(TicketsStaffCog(bot))
