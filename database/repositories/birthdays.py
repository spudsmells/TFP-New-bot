"""Birthday repository — cos everyone deserves cake once a year"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from database.engine import DatabaseEngine


class BirthdayRepository:
    """Repository for birthday tracking"""

    def __init__(self, db: DatabaseEngine):
        self.db = db

    async def set_birthday(
        self, user_id: int, month: int, day: int, year: int | None = None, announce: bool = True
    ) -> None:
        """Set or update a user's birthday"""
        query = """
            INSERT INTO birthdays (user_id, birth_month, birth_day, birth_year, announce)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                birth_month = excluded.birth_month,
                birth_day = excluded.birth_day,
                birth_year = excluded.birth_year,
                announce = excluded.announce
        """
        await self.db.execute(query, (user_id, month, day, year, 1 if announce else 0))

    async def get_birthday(self, user_id: int) -> dict | None:
        """Get a user's birthday"""
        query = "SELECT * FROM birthdays WHERE user_id = ?"
        return await self.db.fetch_one(query, (user_id,))

    async def remove_birthday(self, user_id: int) -> None:
        """Remove a user's birthday"""
        query = "DELETE FROM birthdays WHERE user_id = ?"
        await self.db.execute(query, (user_id,))

    async def get_today_birthdays(self, month: int, day: int) -> list[dict]:
        """Get all users with birthdays today"""
        query = """
            SELECT * FROM birthdays
            WHERE birth_month = ? AND birth_day = ? AND announce = 1
        """
        return await self.db.fetch_all(query, (month, day))

    async def get_upcoming_birthdays(self, limit: int = 10) -> list[dict]:
        """Get upcoming birthdays (next N birthdays chronologically)"""
        # This is a bit tricky with months wrapping around
        # For simplicity, just return all and sort in Python
        query = "SELECT * FROM birthdays WHERE announce = 1 ORDER BY birth_month, birth_day"
        return await self.db.fetch_all(query)

    async def toggle_announce(self, user_id: int, announce: bool) -> None:
        """Toggle birthday announcements for a user"""
        query = "UPDATE birthdays SET announce = ? WHERE user_id = ?"
        await self.db.execute(query, (1 if announce else 0, user_id))
