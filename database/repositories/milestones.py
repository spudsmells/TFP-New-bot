from __future__ import annotations

from typing import TYPE_CHECKING

from database.models import Milestone

if TYPE_CHECKING:
    from database.engine import DatabaseEngine


class MilestoneRepository:
    def __init__(self, db: DatabaseEngine):
        self.db = db

    async def record(self, user_id: int, level: int) -> bool:
        """Record a milestone. Returns False if already recorded."""
        existing = await self.db.fetch_one(
            "SELECT id FROM milestones WHERE user_id = ? AND level = ?",
            (user_id, level),
        )
        if existing:
            return False
        await self.db.execute(
            "INSERT INTO milestones (user_id, level) VALUES (?, ?)",
            (user_id, level),
        )
        return True

    async def mark_notified(self, user_id: int, level: int) -> None:
        await self.db.execute(
            "UPDATE milestones SET notified = 1 WHERE user_id = ? AND level = ?",
            (user_id, level),
        )

    async def get_for_user(self, user_id: int) -> list[Milestone]:
        rows = await self.db.fetch_all(
            "SELECT * FROM milestones WHERE user_id = ? ORDER BY level ASC",
            (user_id,),
        )
        return [Milestone(**r) for r in rows]

    async def has_reached(self, user_id: int, level: int) -> bool:
        count = await self.db.fetch_val(
            "SELECT COUNT(*) FROM milestones WHERE user_id = ? AND level = ?",
            (user_id, level),
        )
        return (count or 0) > 0
