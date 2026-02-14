from __future__ import annotations

from typing import TYPE_CHECKING

from database.models import XPEntry

if TYPE_CHECKING:
    from database.engine import DatabaseEngine


class XPRepository:
    def __init__(self, db: DatabaseEngine):
        self.db = db

    async def add(self, user_id: int, amount: int, source: str, details: str | None = None) -> int:
        await self.db.execute(
            "INSERT INTO xp_history (user_id, amount, source, details) VALUES (?, ?, ?, ?)",
            (user_id, amount, source, details),
        )
        row_id = await self.db.fetch_val("SELECT last_insert_rowid()")
        return row_id

    async def get_history(self, user_id: int, limit: int = 50) -> list[XPEntry]:
        rows = await self.db.fetch_all(
            "SELECT * FROM xp_history WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        )
        return [XPEntry(**r) for r in rows]

    async def get_total_by_source(self, user_id: int) -> dict[str, int]:
        rows = await self.db.fetch_all(
            "SELECT source, SUM(amount) as total FROM xp_history "
            "WHERE user_id = ? GROUP BY source",
            (user_id,),
        )
        return {r["source"]: r["total"] for r in rows}

    async def count_reactions_on_message(self, message_details: str) -> int:
        count = await self.db.fetch_val(
            "SELECT COUNT(*) FROM xp_history WHERE source = 'reaction' AND details = ?",
            (message_details,),
        )
        return count or 0

    async def bulk_import(self, entries: list[tuple[int, int, str, str | None]]) -> int:
        count = 0
        for user_id, amount, source, details in entries:
            await self.db.execute(
                "INSERT INTO xp_history (user_id, amount, source, details) VALUES (?, ?, ?, ?)",
                (user_id, amount, source, details),
            )
            count += 1
        return count
