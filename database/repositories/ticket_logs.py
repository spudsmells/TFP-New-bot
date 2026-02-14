from __future__ import annotations

from typing import TYPE_CHECKING

from database.models import TicketLog

if TYPE_CHECKING:
    from database.engine import DatabaseEngine


class TicketLogRepository:
    def __init__(self, db: DatabaseEngine):
        self.db = db

    async def add(self, ticket_id: int, event: str, actor_id: int | None = None,
                  details: str | None = None) -> None:
        await self.db.execute(
            "INSERT INTO ticket_logs (ticket_id, event, actor_id, details) VALUES (?, ?, ?, ?)",
            (ticket_id, event, actor_id, details),
        )

    async def get_for_ticket(self, ticket_id: int) -> list[TicketLog]:
        rows = await self.db.fetch_all(
            "SELECT * FROM ticket_logs WHERE ticket_id = ? ORDER BY created_at ASC",
            (ticket_id,),
        )
        return [TicketLog(**r) for r in rows]

    async def get_latest_event(self, ticket_id: int, event: str) -> TicketLog | None:
        row = await self.db.fetch_one(
            "SELECT * FROM ticket_logs WHERE ticket_id = ? AND event = ? "
            "ORDER BY created_at DESC LIMIT 1",
            (ticket_id, event),
        )
        return TicketLog(**row) if row else None
