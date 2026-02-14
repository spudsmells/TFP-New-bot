from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from core.constants import TicketLogEvent
from database.repositories.tickets import TicketRepository
from database.repositories.ticket_logs import TicketLogRepository

if TYPE_CHECKING:
    from core.bot import GayborhoodBot

logger = logging.getLogger(__name__)


class TicketLifecycleCog(commands.Cog, name="TicketLifecycleCog"):
    """Release 7: Ticket lifecycle polish — timer cancellation on member reply, mute expiry."""

    def __init__(self, bot: GayborhoodBot):
        self.bot = bot

    async def cog_load(self):
        self.bot.timer_service.register_handler("ticket_mute_expire", self._handle_mute_expire)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Cancel member nudge timer when member responds in ticket."""
        if message.author.bot or not message.guild:
            return
        if message.guild.id != self.bot.config.guild_id:
            return

        ticket_repo = TicketRepository(self.bot.db)
        ticket = await ticket_repo.get_by_channel(message.channel.id)
        if not ticket:
            return

        # If the message is from the ticket owner, cancel nudge timers
        if message.author.id == ticket.owner_id:
            cancelled = await self.bot.timer_service.cancel_timers_for(
                "ticket_member_nudge", str(ticket.id),
            )
            if cancelled:
                logger.debug("Cancelled %d nudge timers for ticket %d (member responded)", cancelled, ticket.id)

    async def _handle_mute_expire(self, timer_id: int, payload: dict):
        """Unmute member when mute timer expires."""
        ticket_id = payload.get("ticket_id")
        channel_id = payload.get("channel_id")

        if not ticket_id or not channel_id:
            return

        ticket_repo = TicketRepository(self.bot.db)
        log_repo = TicketLogRepository(self.bot.db)

        ticket = await ticket_repo.get(ticket_id)
        if not ticket or not ticket.muted:
            return

        await ticket_repo.set_muted(ticket_id, False)

        guild = self.bot.guild
        if not guild:
            return

        channel = self.bot.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        member = guild.get_member(ticket.owner_id)
        if member:
            await channel.set_permissions(member, send_messages=None)

        await log_repo.add(ticket_id, TicketLogEvent.UNMUTED, self.bot.user.id, "Mute expired")

        embed = self.bot.embed_builder.info(
            description="\U0001f50a Mute has expired. The member can send messages again.",
        )
        await channel.send(embed=embed)


async def setup(bot: GayborhoodBot):
    await bot.add_cog(TicketLifecycleCog(bot))
