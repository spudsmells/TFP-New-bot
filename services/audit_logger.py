"""Audit logger — keeps track of every bloody thing that happens"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from database.repositories.audit import AuditRepository

if TYPE_CHECKING:
    from database.engine import DatabaseEngine

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Logs significant bot actions to the database.

    Use this for anything that staff might wanna see later —
    role changes, xp modifications, intro approvals, the lot.
    """

    def __init__(self, db: DatabaseEngine):
        self.repo = AuditRepository(db)

    async def log(
        self,
        event_type: str,
        severity: str = "info",
        actor_id: int | None = None,
        target_id: int | None = None,
        details: str | None = None,
    ) -> None:
        """
        Log an event to the audit trail.

        Args:
            event_type: What happened (intro_approved, role_added, xp_modified, etc)
            severity: info/warning/error/critical (defaults to info cos most things aren't that dramatic)
            actor_id: Who did the thing
            target_id: Who it happened to
            details: Any extra context (JSON string is fine here)
        """
        try:
            await self.repo.create(
                event_type=event_type,
                severity=severity,
                actor_id=actor_id,
                target_id=target_id,
                details=details,
            )
            logger.debug(
                "Audit logged: %s (severity=%s, actor=%s, target=%s)",
                event_type,
                severity,
                actor_id,
                target_id,
            )
        except Exception:
            # Don't let audit logging break the actual operation
            logger.exception("Failed to write audit log entry — well that's ironic")

    # Convenience methods for common events
    # (makes calling code cleaner innit)

    async def log_intro_submission(self, user_id: int) -> None:
        """Log when someone submits an intro"""
        await self.log("intro_submitted", actor_id=user_id, target_id=user_id)

    async def log_intro_approval(
        self, reviewer_id: int, user_id: int, region: str | None = None
    ) -> None:
        """Log intro approval"""
        details = f"Region: {region}" if region else None
        await self.log(
            "intro_approved",
            actor_id=reviewer_id,
            target_id=user_id,
            details=details,
        )

    async def log_intro_rejection(
        self, reviewer_id: int, user_id: int, reason: str
    ) -> None:
        """Log intro rejection"""
        await self.log(
            "intro_rejected",
            severity="warning",
            actor_id=reviewer_id,
            target_id=user_id,
            details=reason,
        )

    async def log_role_change(
        self, actor_id: int | None, user_id: int, role_id: int, action: str
    ) -> None:
        """Log role add/remove"""
        await self.log(
            f"role_{action}",
            actor_id=actor_id,
            target_id=user_id,
            details=f"Role ID: {role_id}",
        )

    async def log_xp_modification(
        self, actor_id: int | None, user_id: int, amount: int, reason: str
    ) -> None:
        """Log XP changes"""
        severity = "warning" if amount < 0 else "info"
        await self.log(
            "xp_modified",
            severity=severity,
            actor_id=actor_id,
            target_id=user_id,
            details=f"{amount:+d} XP: {reason}",
        )

    async def log_ticket_action(
        self, event: str, actor_id: int | None, ticket_id: int, details: str | None = None
    ) -> None:
        """Log ticket events"""
        await self.log(
            f"ticket_{event}",
            actor_id=actor_id,
            details=f"Ticket #{ticket_id}" + (f" — {details}" if details else ""),
        )

    async def log_moderation_action(
        self, action: str, moderator_id: int, target_id: int, reason: str | None = None
    ) -> None:
        """Log moderation actions (kick, ban, mute, warn)"""
        await self.log(
            f"mod_{action}",
            severity="warning",
            actor_id=moderator_id,
            target_id=target_id,
            details=reason,
        )

    async def log_error(self, error_type: str, details: str) -> None:
        """Log system errors"""
        await self.log(
            f"error_{error_type}",
            severity="error",
            details=details,
        )

    async def log_critical(self, event: str, details: str) -> None:
        """Log critical events that need immediate attention"""
        await self.log(
            event,
            severity="critical",
            details=details,
        )
        logger.critical("CRITICAL AUDIT EVENT: %s — %s", event, details)
