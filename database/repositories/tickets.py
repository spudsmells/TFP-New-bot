from __future__ import annotations

from typing import TYPE_CHECKING

from database.models import Ticket

if TYPE_CHECKING:
    from database.engine import DatabaseEngine


class TicketRepository:
    def __init__(self, db: DatabaseEngine):
        self.db = db

    async def create(self, channel_id: int, ticket_type: str, owner_id: int,
                     opener_id: int, reason: str | None = None) -> int:
        await self.db.execute(
            "INSERT INTO tickets (channel_id, ticket_type, owner_id, opener_id, reason) "
            "VALUES (?, ?, ?, ?, ?)",
            (channel_id, ticket_type, owner_id, opener_id, reason),
        )
        row_id = await self.db.fetch_val("SELECT last_insert_rowid()")
        return row_id

    async def get(self, ticket_id: int) -> Ticket | None:
        row = await self.db.fetch_one("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
        return Ticket(**row) if row else None

    async def get_by_channel(self, channel_id: int) -> Ticket | None:
        row = await self.db.fetch_one("SELECT * FROM tickets WHERE channel_id = ?", (channel_id,))
        return Ticket(**row) if row else None

    async def get_open_for_user(self, user_id: int) -> Ticket | None:
        row = await self.db.fetch_one(
            "SELECT * FROM tickets WHERE owner_id = ? AND status IN ('open', 'claimed') LIMIT 1",
            (user_id,),
        )
        return Ticket(**row) if row else None

    async def get_open_tickets(self) -> list[Ticket]:
        rows = await self.db.fetch_all(
            "SELECT * FROM tickets WHERE status IN ('open', 'claimed') ORDER BY created_at ASC",
        )
        return [Ticket(**r) for r in rows]

    async def claim(self, ticket_id: int, staff_id: int) -> None:
        await self.db.execute(
            "UPDATE tickets SET status = 'claimed', claimed_by = ?, claimed_at = datetime('now') "
            "WHERE id = ?",
            (staff_id, ticket_id),
        )

    async def unclaim(self, ticket_id: int) -> None:
        await self.db.execute(
            "UPDATE tickets SET status = 'open', claimed_by = NULL, claimed_at = NULL WHERE id = ?",
            (ticket_id,),
        )

    async def close(self, ticket_id: int, closed_by: int) -> None:
        await self.db.execute(
            "UPDATE tickets SET status = 'closed', closed_by = ?, closed_at = datetime('now') WHERE id = ?",
            (closed_by, ticket_id),
        )

    async def archive(self, ticket_id: int) -> None:
        await self.db.execute(
            "UPDATE tickets SET status = 'archived' WHERE id = ?", (ticket_id,),
        )

    async def set_muted(self, ticket_id: int, muted: bool, expires_at: str | None = None) -> None:
        await self.db.execute(
            "UPDATE tickets SET muted = ?, mute_expires_at = ? WHERE id = ?",
            (int(muted), expires_at, ticket_id),
        )

    async def increment_nudge(self, ticket_id: int) -> None:
        await self.db.execute(
            "UPDATE tickets SET nudge_count = nudge_count + 1, last_nudge_at = datetime('now') WHERE id = ?",
            (ticket_id,),
        )
