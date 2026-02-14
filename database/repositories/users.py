from __future__ import annotations

from typing import TYPE_CHECKING, Any

from database.models import User

if TYPE_CHECKING:
    from database.engine import DatabaseEngine


class UserRepository:
    def __init__(self, db: DatabaseEngine):
        self.db = db

    async def get(self, user_id: int) -> User | None:
        row = await self.db.fetch_one("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return User(**row) if row else None

    async def upsert(self, user_id: int, **kwargs: Any) -> None:
        existing = await self.get(user_id)
        if existing is None:
            cols = ["user_id"] + list(kwargs.keys())
            placeholders = ", ".join("?" for _ in cols)
            vals = [user_id] + list(kwargs.values())
            await self.db.execute(
                f"INSERT INTO users ({', '.join(cols)}) VALUES ({placeholders})",
                tuple(vals),
            )
        else:
            if not kwargs:
                return
            sets = ", ".join(f"{k} = ?" for k in kwargs)
            vals = list(kwargs.values()) + [user_id]
            await self.db.execute(
                f"UPDATE users SET {sets}, updated_at = datetime('now') WHERE user_id = ?",
                tuple(vals),
            )

    async def set_rules_agreed(self, user_id: int, version: str, method: str) -> None:
        await self.upsert(user_id)
        await self.db.execute(
            "UPDATE users SET rules_agreed = 1, rules_agreed_at = datetime('now'), "
            "rule_version = ?, rules_method = ?, updated_at = datetime('now') "
            "WHERE user_id = ?",
            (version, method, user_id),
        )

    async def set_intro_status(self, user_id: int, status: str) -> None:
        await self.db.execute(
            "UPDATE users SET intro_status = ?, updated_at = datetime('now') WHERE user_id = ?",
            (status, user_id),
        )

    async def set_status(self, user_id: int, status: str) -> None:
        await self.db.execute(
            "UPDATE users SET status = ?, updated_at = datetime('now') WHERE user_id = ?",
            (status, user_id),
        )

    async def add_xp(self, user_id: int, amount: int, new_level: int) -> None:
        await self.db.execute(
            "UPDATE users SET total_xp = total_xp + ?, level = ?, "
            "updated_at = datetime('now') WHERE user_id = ?",
            (amount, new_level, user_id),
        )

    async def set_xp(self, user_id: int, total_xp: int, level: int) -> None:
        await self.db.execute(
            "UPDATE users SET total_xp = ?, level = ?, updated_at = datetime('now') WHERE user_id = ?",
            (total_xp, level, user_id),
        )

    async def increment_messages(self, user_id: int) -> None:
        await self.db.execute(
            "UPDATE users SET messages_sent = messages_sent + 1, updated_at = datetime('now') WHERE user_id = ?",
            (user_id,),
        )

    async def add_vc_minutes(self, user_id: int, minutes: int) -> None:
        await self.db.execute(
            "UPDATE users SET vc_minutes = vc_minutes + ?, updated_at = datetime('now') WHERE user_id = ?",
            (minutes, user_id),
        )

    async def set_age_verified(self, user_id: int) -> None:
        await self.db.execute(
            "UPDATE users SET age_verified = 1, age_verified_at = datetime('now'), "
            "updated_at = datetime('now') WHERE user_id = ?",
            (user_id,),
        )

    async def get_leaderboard(self, limit: int = 10) -> list[User]:
        rows = await self.db.fetch_all(
            "SELECT * FROM users WHERE status = 'approved' ORDER BY total_xp DESC LIMIT ?",
            (limit,),
        )
        return [User(**r) for r in rows]

    async def get_rank(self, user_id: int) -> int | None:
        row = await self.db.fetch_val(
            "SELECT COUNT(*) + 1 FROM users "
            "WHERE status = 'approved' AND total_xp > "
            "(SELECT total_xp FROM users WHERE user_id = ?)",
            (user_id,),
        )
        return row
