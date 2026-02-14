"""Counting repository — tracking the counting game stats"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from database.engine import DatabaseEngine


class CountingRepository:
    """Repository for counting channel game stats"""

    def __init__(self, db: DatabaseEngine):
        self.db = db

    async def get_stats(self, channel_id: int) -> dict | None:
        """Get counting stats for a channel"""
        query = "SELECT * FROM counting_stats WHERE channel_id = ?"
        return await self.db.fetch_one(query, (channel_id,))

    async def init_channel(self, channel_id: int) -> None:
        """Initialize counting stats for a channel"""
        query = """
            INSERT INTO counting_stats (channel_id, current_count, highest_count)
            VALUES (?, 0, 0)
            ON CONFLICT(channel_id) DO NOTHING
        """
        await self.db.execute(query, (channel_id,))

    async def increment_count(self, channel_id: int, user_id: int) -> int:
        """Increment count and return new count"""
        query = """
            UPDATE counting_stats
            SET current_count = current_count + 1,
                last_user_id = ?,
                last_count_at = datetime('now'),
                updated_at = datetime('now')
            WHERE channel_id = ?
            RETURNING current_count
        """
        result = await self.db.fetch_one(query, (user_id, channel_id))
        return result["current_count"] if result else 0

    async def reset_count(self, channel_id: int) -> None:
        """Reset count to 0 (after a fail)"""
        query = """
            UPDATE counting_stats
            SET current_count = 0,
                last_user_id = NULL,
                fails = fails + 1,
                updated_at = datetime('now')
            WHERE channel_id = ?
        """
        await self.db.execute(query, (channel_id,))

    async def update_highest(self, channel_id: int, count: int) -> None:
        """Update highest count if current is higher"""
        query = """
            UPDATE counting_stats
            SET highest_count = ?
            WHERE channel_id = ? AND ? > highest_count
        """
        await self.db.execute(query, (count, channel_id, count))
