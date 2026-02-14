from __future__ import annotations

from typing import TYPE_CHECKING

from database.models import Timer

if TYPE_CHECKING:
    from database.engine import DatabaseEngine


class TimerRepository:
    def __init__(self, db: DatabaseEngine):
        self.db = db

    async def create(self, timer_type: str, fires_at: str, payload: str | None = None) -> int:
        await self.db.execute(
            "INSERT INTO timers (timer_type, fires_at, payload) VALUES (?, ?, ?)",
            (timer_type, fires_at, payload),
        )
        return await self.db.fetch_val("SELECT last_insert_rowid()")

    async def get(self, timer_id: int) -> Timer | None:
        row = await self.db.fetch_one("SELECT * FROM timers WHERE id = ?", (timer_id,))
        return Timer(**row) if row else None

    async def get_pending(self) -> list[Timer]:
        """Get all timers that should fire now or are overdue."""
        rows = await self.db.fetch_all(
            "SELECT * FROM timers WHERE fired = 0 AND cancelled = 0 "
            "AND fires_at <= datetime('now') ORDER BY fires_at ASC",
        )
        return [Timer(**r) for r in rows]

    async def mark_fired(self, timer_id: int) -> None:
        await self.db.execute(
            "UPDATE timers SET fired = 1 WHERE id = ?", (timer_id,),
        )

    async def cancel(self, timer_id: int) -> None:
        await self.db.execute(
            "UPDATE timers SET cancelled = 1 WHERE id = ?", (timer_id,),
        )

    async def cancel_by_type_and_payload(self, timer_type: str, payload_contains: str) -> int:
        """Cancel all matching timers. Returns count cancelled."""
        rows = await self.db.fetch_all(
            "SELECT id FROM timers WHERE timer_type = ? AND payload LIKE ? "
            "AND fired = 0 AND cancelled = 0",
            (timer_type, f"%{payload_contains}%"),
        )
        for row in rows:
            await self.db.execute("UPDATE timers SET cancelled = 1 WHERE id = ?", (row["id"],))
        return len(rows)
