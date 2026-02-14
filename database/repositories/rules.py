from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from database.engine import DatabaseEngine


class RulesRepository:
    def __init__(self, db: DatabaseEngine):
        self.db = db

    async def record_acknowledgement(self, user_id: int, rule_version: str, method: str) -> None:
        await self.db.execute(
            "INSERT INTO rule_acknowledgements (user_id, rule_version, method) VALUES (?, ?, ?)",
            (user_id, rule_version, method),
        )

    async def has_acknowledged(self, user_id: int, rule_version: str | None = None) -> bool:
        if rule_version:
            count = await self.db.fetch_val(
                "SELECT COUNT(*) FROM rule_acknowledgements WHERE user_id = ? AND rule_version = ?",
                (user_id, rule_version),
            )
        else:
            count = await self.db.fetch_val(
                "SELECT COUNT(*) FROM rule_acknowledgements WHERE user_id = ?",
                (user_id,),
            )
        return (count or 0) > 0

    async def get_latest_version(self, user_id: int) -> str | None:
        return await self.db.fetch_val(
            "SELECT rule_version FROM rule_acknowledgements WHERE user_id = ? "
            "ORDER BY created_at DESC LIMIT 1",
            (user_id,),
        )
