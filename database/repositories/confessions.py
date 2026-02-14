"""Confessions repository — for all the secret tea"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from database.engine import DatabaseEngine


class ConfessionRepository:
    """Repository for anonymous confessions"""

    def __init__(self, db: DatabaseEngine):
        self.db = db

    async def create(self, user_id: int, content: str) -> int:
        """Create a new confession (pending review)"""
        # Get next confession number
        max_num = await self.db.fetch_val(
            "SELECT MAX(confession_num) FROM confessions"
        )
        next_num = (max_num or 0) + 1

        query = """
            INSERT INTO confessions (confession_num, user_id, content)
            VALUES (?, ?, ?)
        """
        await self.db.execute(query, (next_num, user_id, content))
        return await self.db.fetch_val("SELECT last_insert_rowid()")

    async def get_pending(self) -> list[dict]:
        """Get all pending confessions (not approved or rejected)"""
        query = """
            SELECT * FROM confessions
            WHERE approved = 0 AND rejected = 0
            ORDER BY created_at ASC
        """
        return await self.db.fetch_all(query)

    async def get_by_id(self, confession_id: int) -> dict | None:
        """Get confession by ID"""
        query = "SELECT * FROM confessions WHERE id = ?"
        return await self.db.fetch_one(query, (confession_id,))

    async def approve(
        self, confession_id: int, reviewer_id: int, message_id: int, channel_id: int
    ) -> None:
        """Approve a confession and record where it was posted"""
        query = """
            UPDATE confessions
            SET approved = 1,
                reviewed_by = ?,
                reviewed_at = datetime('now'),
                message_id = ?,
                channel_id = ?
            WHERE id = ?
        """
        await self.db.execute(query, (reviewer_id, message_id, channel_id, confession_id))

    async def reject(self, confession_id: int, reviewer_id: int) -> None:
        """Reject a confession"""
        query = """
            UPDATE confessions
            SET rejected = 1,
                reviewed_by = ?,
                reviewed_at = datetime('now')
            WHERE id = ?
        """
        await self.db.execute(query, (reviewer_id, confession_id))

    async def get_user_confessions(self, user_id: int) -> list[dict]:
        """Get all confessions by a user (for moderation purposes)"""
        query = """
            SELECT * FROM confessions
            WHERE user_id = ?
            ORDER BY created_at DESC
        """
        return await self.db.fetch_all(query, (user_id,))

    async def get_approved_count(self) -> int:
        """Get total count of approved confessions"""
        return await self.db.fetch_val(
            "SELECT COUNT(*) FROM confessions WHERE approved = 1"
        ) or 0
