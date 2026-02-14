"""Bump repository — tracking server bump stats"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from database.engine import DatabaseEngine


class BumpRepository:
    """Repository for server bump tracking"""

    def __init__(self, db: DatabaseEngine):
        self.db = db

    async def record_bump(self, user_id: int) -> None:
        """Record a server bump"""
        query = "INSERT INTO bump_stats (user_id) VALUES (?)"
        await self.db.execute(query, (user_id,))

    async def get_last_bump(self) -> dict | None:
        """Get the most recent bump"""
        query = """
            SELECT * FROM bump_stats
            ORDER BY bumped_at DESC
            LIMIT 1
        """
        return await self.db.fetch_one(query)

    async def get_user_bump_count(self, user_id: int) -> int:
        """Get total bump count for a user"""
        query = "SELECT COUNT(*) FROM bump_stats WHERE user_id = ?"
        return await self.db.fetch_val(query, (user_id,)) or 0

    async def get_top_bumpers(self, limit: int = 10) -> list[dict]:
        """Get leaderboard of top bumpers"""
        query = """
            SELECT user_id, COUNT(*) as bump_count
            FROM bump_stats
            GROUP BY user_id
            ORDER BY bump_count DESC
            LIMIT ?
        """
        return await self.db.fetch_all(query, (limit,))

    async def get_total_bumps(self) -> int:
        """Get total number of bumps"""
        return await self.db.fetch_val("SELECT COUNT(*) FROM bump_stats") or 0
