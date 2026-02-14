from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from database.engine import DatabaseEngine

logger = logging.getLogger(__name__)

CURRENT_VERSION = 3
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


async def run_migrations(db: DatabaseEngine) -> None:
    """Run schema migrations. Applies full schema on first run, then tracks version."""
    # Ensure schema_version table exists (bootstrap)
    await db.execute_script(
        "CREATE TABLE IF NOT EXISTS schema_version ("
        "  version INTEGER PRIMARY KEY,"
        "  applied_at TEXT NOT NULL DEFAULT (datetime('now'))"
        ");"
    )

    current = await db.fetch_val("SELECT MAX(version) FROM schema_version")
    if current is None:
        current = 0

    if current >= CURRENT_VERSION:
        logger.info("Schema up to date (version %d)", current)
        return

    # Apply full schema
    logger.info("Applying schema version %d (current: %d)", CURRENT_VERSION, current)
    schema_sql = SCHEMA_PATH.read_text()
    await db.execute_script(schema_sql)

    # Record version
    await db.execute(
        "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
        (CURRENT_VERSION,),
    )
    logger.info("Schema migrated to version %d", CURRENT_VERSION)
