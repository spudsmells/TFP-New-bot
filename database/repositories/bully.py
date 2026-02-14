from __future__ import annotations

from typing import TYPE_CHECKING

from database.models import BullyInsult

if TYPE_CHECKING:
    from database.engine import DatabaseEngine


class BullyRepository:
    def __init__(self, db: DatabaseEngine):
        self.db = db

    async def get_random_active(self) -> BullyInsult | None:
        row = await self.db.fetch_one(
            "SELECT * FROM bully_insults WHERE active = 1 ORDER BY RANDOM() LIMIT 1",
        )
        return BullyInsult(**row) if row else None

    async def add(self, text: str, added_by: int) -> int:
        await self.db.execute(
            "INSERT INTO bully_insults (text, added_by) VALUES (?, ?)",
            (text, added_by),
        )
        return await self.db.fetch_val("SELECT last_insert_rowid()")

    async def remove(self, insult_id: int, removed_by: int) -> bool:
        row = await self.db.fetch_one(
            "SELECT * FROM bully_insults WHERE id = ? AND active = 1", (insult_id,),
        )
        if not row:
            return False
        await self.db.execute(
            "UPDATE bully_insults SET active = 0, removed_by = ? WHERE id = ?",
            (removed_by, insult_id),
        )
        return True

    async def toggle(self, insult_id: int) -> bool | None:
        row = await self.db.fetch_one(
            "SELECT active FROM bully_insults WHERE id = ?", (insult_id,),
        )
        if not row:
            return None
        new_state = not row["active"]
        await self.db.execute(
            "UPDATE bully_insults SET active = ? WHERE id = ?",
            (int(new_state), insult_id),
        )
        return new_state

    async def list_all(self, active_only: bool = True) -> list[BullyInsult]:
        if active_only:
            rows = await self.db.fetch_all(
                "SELECT * FROM bully_insults WHERE active = 1 ORDER BY id",
            )
        else:
            rows = await self.db.fetch_all("SELECT * FROM bully_insults ORDER BY id")
        return [BullyInsult(**r) for r in rows]

    async def count_active(self) -> int:
        return await self.db.fetch_val(
            "SELECT COUNT(*) FROM bully_insults WHERE active = 1",
        ) or 0

    async def log_usage(self, caller_id: int, target_id: int, insult_id: int) -> None:
        await self.db.execute(
            "INSERT INTO bully_usage (caller_id, target_id, insult_id) VALUES (?, ?, ?)",
            (caller_id, target_id, insult_id),
        )

    async def count_usage_against(self, target_id: int, window_seconds: int) -> int:
        return await self.db.fetch_val(
            "SELECT COUNT(*) FROM bully_usage WHERE target_id = ? "
            "AND created_at > datetime('now', ?)",
            (target_id, f"-{window_seconds} seconds"),
        ) or 0

    async def seed_insults(self, insults: list[str], added_by: int) -> int:
        count = 0
        for text in insults:
            existing = await self.db.fetch_one(
                "SELECT id FROM bully_insults WHERE text = ?", (text,),
            )
            if not existing:
                await self.db.execute(
                    "INSERT INTO bully_insults (text, added_by) VALUES (?, ?)",
                    (text, added_by),
                )
                count += 1
        return count
