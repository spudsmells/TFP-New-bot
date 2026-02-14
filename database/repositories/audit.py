"""Audit log repository — cos we need to know who fucked what"""
from __future__ import annotations

from typing import TYPE_CHECKING

from database.models import AuditEntry

if TYPE_CHECKING:
    from database.engine import DatabaseEngine


class AuditRepository:
    """Repository for audit log entries. tracks all the drama."""

    def __init__(self, db: DatabaseEngine):
        self.db = db

    async def create(
        self,
        event_type: str,
        severity: str = "info",
        actor_id: int | None = None,
        target_id: int | None = None,
        details: str | None = None,
    ) -> AuditEntry:
        """
        Create new audit log entry.

        severity can be: info, warning, error, critical
        """
        query = """
            INSERT INTO audit_log (event_type, severity, actor_id, target_id, details)
            VALUES (?, ?, ?, ?, ?)
            RETURNING *
        """
        row = await self.db.fetch_one(
            query, event_type, severity, actor_id, target_id, details
        )
        return AuditEntry(**row)

    async def get_recent(self, limit: int = 100) -> list[AuditEntry]:
        """Get recent audit entries for debugging when shit hits the fan"""
        query = """
            SELECT * FROM audit_log
            ORDER BY created_at DESC
            LIMIT ?
        """
        rows = await self.db.fetch_all(query, limit)
        return [AuditEntry(**row) for row in rows]

    async def get_by_actor(self, actor_id: int, limit: int = 50) -> list[AuditEntry]:
        """Get audit entries for specific user — useful for seeing what they've been up to"""
        query = """
            SELECT * FROM audit_log
            WHERE actor_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """
        rows = await self.db.fetch_all(query, actor_id, limit)
        return [AuditEntry(**row) for row in rows]

    async def get_by_event_type(
        self, event_type: str, limit: int = 100
    ) -> list[AuditEntry]:
        """Get audit entries by event type"""
        query = """
            SELECT * FROM audit_log
            WHERE event_type = ?
            ORDER BY created_at DESC
            LIMIT ?
        """
        rows = await self.db.fetch_all(query, event_type, limit)
        return [AuditEntry(**row) for row in rows]

    async def get_critical(self, limit: int = 50) -> list[AuditEntry]:
        """Get critical severity entries — the oh fuck moments"""
        query = """
            SELECT * FROM audit_log
            WHERE severity = 'critical'
            ORDER BY created_at DESC
            LIMIT ?
        """
        rows = await self.db.fetch_all(query, limit)
        return [AuditEntry(**row) for row in rows]
