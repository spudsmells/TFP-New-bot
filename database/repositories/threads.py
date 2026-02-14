from __future__ import annotations

from typing import TYPE_CHECKING

from database.models import AutoThreadConfig

if TYPE_CHECKING:
    from database.engine import DatabaseEngine


class ThreadRepository:
    def __init__(self, db: DatabaseEngine):
        self.db = db

    async def get(self, channel_id: int) -> AutoThreadConfig | None:
        row = await self.db.fetch_one(
            "SELECT * FROM auto_thread_configs WHERE channel_id = ?", (channel_id,),
        )
        return AutoThreadConfig(**row) if row else None

    async def upsert(self, channel_id: int, **kwargs) -> None:
        existing = await self.get(channel_id)
        if existing is None:
            cols = ["channel_id"] + list(kwargs.keys())
            placeholders = ", ".join("?" for _ in cols)
            vals = [channel_id] + list(kwargs.values())
            await self.db.execute(
                f"INSERT INTO auto_thread_configs ({', '.join(cols)}) VALUES ({placeholders})",
                tuple(vals),
            )
        else:
            if not kwargs:
                return
            sets = ", ".join(f"{k} = ?" for k in kwargs)
            vals = list(kwargs.values()) + [channel_id]
            await self.db.execute(
                f"UPDATE auto_thread_configs SET {sets}, updated_at = datetime('now') "
                f"WHERE channel_id = ?",
                tuple(vals),
            )

    async def delete(self, channel_id: int) -> bool:
        existing = await self.get(channel_id)
        if not existing:
            return False
        await self.db.execute(
            "DELETE FROM auto_thread_configs WHERE channel_id = ?", (channel_id,),
        )
        return True

    async def list_enabled(self) -> list[AutoThreadConfig]:
        rows = await self.db.fetch_all(
            "SELECT * FROM auto_thread_configs WHERE enabled = 1",
        )
        return [AutoThreadConfig(**r) for r in rows]

    async def list_all(self) -> list[AutoThreadConfig]:
        rows = await self.db.fetch_all("SELECT * FROM auto_thread_configs ORDER BY channel_id")
        return [AutoThreadConfig(**r) for r in rows]
