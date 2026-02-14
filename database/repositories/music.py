from __future__ import annotations

from typing import TYPE_CHECKING

from database.models import MusicConversion

if TYPE_CHECKING:
    from database.engine import DatabaseEngine


class MusicRepository:
    def __init__(self, db: DatabaseEngine):
        self.db = db

    async def create(self, source_url: str, platform: str, artist: str | None,
                     title: str | None, youtube_url: str | None, success: bool,
                     requested_by: int | None) -> int:
        await self.db.execute(
            "INSERT INTO music_conversions (source_url, platform, artist, title, "
            "youtube_url, success, requested_by) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (source_url, platform, artist, title, youtube_url, int(success), requested_by),
        )
        return await self.db.fetch_val("SELECT last_insert_rowid()")

    async def find_by_url(self, source_url: str) -> MusicConversion | None:
        row = await self.db.fetch_one(
            "SELECT * FROM music_conversions WHERE source_url = ? AND success = 1 "
            "ORDER BY created_at DESC LIMIT 1",
            (source_url,),
        )
        return MusicConversion(**row) if row else None

    async def get_recent(self, limit: int = 20) -> list[MusicConversion]:
        rows = await self.db.fetch_all(
            "SELECT * FROM music_conversions ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return [MusicConversion(**r) for r in rows]
