"""Timer service — schedules shit to happen later (and actually remembers to do it)"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from database.repositories.timers import TimerRepository

if TYPE_CHECKING:
    from core.bot import GayborhoodBot
    from database.engine import DatabaseEngine
    from services.audit_logger import AuditLogger

logger = logging.getLogger(__name__)


class TimerService:
    """
    Manages persistent timers that survive bot restarts.

    Polls database every 30s for expired timers and executes them.
    Handles nudges, mute expiry, reminders, all that jazz.
    """

    def __init__(self, bot: GayborhoodBot, db: DatabaseEngine, audit_logger: AuditLogger):
        self.bot = bot
        self.db = db
        self.audit = audit_logger
        self.repo = TimerRepository(db)
        self._polling = False
        self._poll_task: asyncio.Task | None = None

    def start_polling(self) -> None:
        """Start polling for expired timers."""
        if self._polling:
            logger.warning("Timer polling already running innit")
            return

        self._polling = True
        self._poll_task = asyncio.create_task(self._poll_loop())
        logger.info("Timer polling started")

    def stop_polling(self) -> None:
        """Stop polling for timers."""
        if not self._polling:
            return

        self._polling = False
        if self._poll_task:
            self._poll_task.cancel()
        logger.info("Timer polling stopped")

    async def _poll_loop(self) -> None:
        """Main polling loop — checks database every 30s for expired timers."""
        while self._polling:
            try:
                await self._check_timers()
            except Exception:
                logger.exception("Error in timer polling loop — fuck")
                await self.audit.log_error(
                    "timer_poll_error",
                    "Timer polling encountered an error",
                )

            # Wait 30s before next check
            await asyncio.sleep(30)

    async def _check_timers(self) -> None:
        """Check for and execute expired timers."""
        pending = await self.repo.get_pending()
        if not pending:
            return

        logger.debug("Found %d pending timers to execute", len(pending))

        for timer in pending:
            try:
                await self._execute_timer(timer.id, timer.timer_type, timer.payload)
                await self.repo.mark_fired(timer.id)
            except Exception:
                logger.exception("Failed to execute timer %d", timer.id)
                await self.audit.log_error(
                    "timer_execution_failed",
                    f"Timer {timer.id} ({timer.timer_type}) failed",
                )

    async def _execute_timer(
        self, timer_id: int, timer_type: str, payload: str | None
    ) -> None:
        """Execute a timer based on its type."""
        logger.info("Executing timer %d: %s", timer_id, timer_type)

        # Parse payload (usually JSON)
        data = json.loads(payload) if payload else {}

        # Route to appropriate handler
        if timer_type == "ticket_member_nudge":
            await self._handle_ticket_nudge(data)
        elif timer_type == "ticket_staff_reminder":
            await self._handle_staff_reminder(data)
        elif timer_type == "ticket_mute_expiry":
            await self._handle_mute_expiry(data)
        else:
            logger.warning("Unknown timer type: %s", timer_type)

    async def _handle_ticket_nudge(self, data: dict) -> None:
        """Handle ticket nudge (member hasn't responded)."""
        from database.repositories.tickets import TicketRepository

        ticket_id = data.get("ticket_id")
        if not ticket_id:
            logger.error("Ticket nudge payload missing ticket_id")
            return

        ticket_repo = TicketRepository(self.db)
        ticket = await ticket_repo.get(ticket_id)
        if not ticket or ticket.status != "open":
            # Ticket already closed or doesn't exist
            return

        guild = self.bot.guild
        if not guild:
            return

        channel = guild.get_channel(ticket.channel_id)
        if not channel:
            logger.warning("Ticket channel %s not found", ticket.channel_id)
            return

        # Send nudge message
        try:
            owner = guild.get_member(ticket.owner_id)
            if owner:
                await channel.send(
                    f"{owner.mention} Just checking in — still need help with this ticket? "
                    f"If you've sorted it, feel free to close it x"
                )
                await ticket_repo.increment_nudge_count(ticket_id)
                logger.info("Sent nudge for ticket #%d", ticket_id)
        except Exception:
            logger.exception("Failed to send ticket nudge")

    async def _handle_staff_reminder(self, data: dict) -> None:
        """Handle staff reminder (ticket unclaimed for 12h)."""
        from database.repositories.tickets import TicketRepository

        ticket_id = data.get("ticket_id")
        if not ticket_id:
            logger.error("Staff reminder payload missing ticket_id")
            return

        ticket_repo = TicketRepository(self.db)
        ticket = await ticket_repo.get(ticket_id)
        if not ticket or ticket.status != "open" or ticket.claimed_by:
            # Ticket already claimed/closed
            return

        guild = self.bot.guild
        if not guild:
            return

        # Send reminder to staff alerts channel
        staff_alerts_id = self.bot.config.channels.get("staff_alerts")
        if not staff_alerts_id:
            return

        channel = guild.get_channel(staff_alerts_id)
        if not channel:
            return

        try:
            embed = self.bot.embed_builder.warning(
                title="📋 Unclaimed Ticket Reminder",
                description=f"Ticket #{ticket_id} has been waiting for 12 hours without a staff claim.\n"
                f"Channel: <#{ticket.channel_id}>",
            )
            await channel.send(embed=embed)
            logger.info("Sent staff reminder for ticket #%d", ticket_id)
        except Exception:
            logger.exception("Failed to send staff reminder")

    async def _handle_mute_expiry(self, data: dict) -> None:
        """Handle ticket mute expiry (unmute user)."""
        from database.repositories.tickets import TicketRepository

        ticket_id = data.get("ticket_id")
        if not ticket_id:
            logger.error("Mute expiry payload missing ticket_id")
            return

        ticket_repo = TicketRepository(self.db)
        ticket = await ticket_repo.get(ticket_id)
        if not ticket or not ticket.muted:
            # Already unmuted
            return

        guild = self.bot.guild
        if not guild:
            return

        channel = guild.get_channel(ticket.channel_id)
        member = guild.get_member(ticket.owner_id)

        if not channel or not member:
            logger.warning(
                "Cannot unmute ticket #%d — channel or member not found",
                ticket_id,
            )
            return

        # Remove send_messages deny permission
        try:
            await channel.set_permissions(
                member,
                send_messages=None,  # Reset to default (inherit from category)
                reason="Ticket mute expired",
            )
            await ticket_repo.unmute(ticket_id)
            await channel.send(f"{member.mention} You've been unmuted. Please let us know if you still need help!")
            logger.info("Unmuted ticket #%d", ticket_id)
            await self.audit.log_ticket_action("unmuted", None, ticket_id, "Automatic expiry")
        except Exception:
            logger.exception("Failed to unmute ticket #%d", ticket_id)

    async def schedule_timer(
        self, timer_type: str, execute_at: datetime, payload: dict | None = None
    ) -> int:
        """
        Schedule a new timer.

        Args:
            timer_type: Type of timer (ticket_member_nudge, ticket_mute_expiry, etc)
            execute_at: When to execute (datetime object)
            payload: Data to pass to timer handler (will be JSON-encoded)

        Returns:
            Timer ID
        """
        fires_at = execute_at.isoformat()
        payload_json = json.dumps(payload) if payload else None

        timer_id = await self.repo.create(timer_type, fires_at, payload_json)
        logger.debug(
            "Scheduled timer #%d: %s at %s",
            timer_id,
            timer_type,
            execute_at,
        )
        return timer_id

    async def cancel_timer(self, timer_id: int) -> None:
        """Cancel a timer by ID."""
        await self.repo.cancel(timer_id)
        logger.debug("Cancelled timer #%d", timer_id)

    async def cancel_matching_timers(
        self, timer_type: str, payload_contains: str
    ) -> int:
        """
        Cancel all timers matching type and payload content.

        Useful for cancelling all timers for a specific ticket.

        Returns:
            Number of timers cancelled
        """
        count = await self.repo.cancel_by_type_and_payload(timer_type, payload_contains)
        logger.debug(
            "Cancelled %d timers (type=%s, payload contains '%s')",
            count,
            timer_type,
            payload_contains,
        )
        return count

    async def schedule_ticket_nudge(self, ticket_id: int, hours: int = 2) -> int:
        """Schedule ticket nudge timer (convenience method)."""
        execute_at = datetime.utcnow() + timedelta(hours=hours)
        return await self.schedule_timer(
            "ticket_member_nudge",
            execute_at,
            {"ticket_id": ticket_id},
        )

    async def schedule_staff_reminder(self, ticket_id: int, hours: int = 12) -> int:
        """Schedule staff reminder timer (convenience method)."""
        execute_at = datetime.utcnow() + timedelta(hours=hours)
        return await self.schedule_timer(
            "ticket_staff_reminder",
            execute_at,
            {"ticket_id": ticket_id},
        )

    async def schedule_mute_expiry(self, ticket_id: int, minutes: int = 30) -> int:
        """Schedule mute expiry timer (convenience method)."""
        execute_at = datetime.utcnow() + timedelta(minutes=minutes)
        return await self.schedule_timer(
            "ticket_mute_expiry",
            execute_at,
            {"ticket_id": ticket_id},
        )
