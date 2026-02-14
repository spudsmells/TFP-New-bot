"""Sticky messages repository — for messages that need to stick around"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from database.engine import DatabaseEngine


class StickyRepository:
    """Repository for sticky messages that stay at the bottom of channels"""

    def __init__(self, db: DatabaseEngine):
        self.db = db

    async def create(self, channel_id: int, message_id: int, embed_type: str) -> int:
        """Create a new sticky message record"""
        query = """
            INSERT INTO sticky_messages (channel_id, message_id, embed_type)
            VALUES (?, ?, ?)
        """
        await self.db.execute(query, (channel_id, message_id, embed_type))
        return await self.db.fetch_val("SELECT last_insert_rowid()")

    async def get_by_channel(self, channel_id: int) -> dict | None:
        """Get sticky message for a channel"""
        query = """
            SELECT * FROM sticky_messages
            WHERE channel_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """
        return await self.db.fetch_one(query, (channel_id,))

    async def delete_by_channel(self, channel_id: int) -> None:
        """Delete sticky message for a channel"""
        query = "DELETE FROM sticky_messages WHERE channel_id = ?"
        await self.db.execute(query, (channel_id,))

    async def update_message_id(self, channel_id: int, new_message_id: int) -> None:
        """Update the message ID for a sticky message (when reposted)"""
        query = """
            UPDATE sticky_messages
            SET message_id = ?
            WHERE channel_id = ?
        """
        await self.db.execute(query, (new_message_id, channel_id))

    async def get_all(self) -> list[dict]:
        """Get all sticky messages"""
        query = "SELECT * FROM sticky_messages ORDER BY channel_id"
        return await self.db.fetch_all(query)
