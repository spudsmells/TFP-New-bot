from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class DatabaseEngine(ABC):
    """Abstract database interface — swap between SQLite and PostgreSQL."""

    @abstractmethod
    async def execute(self, query: str, params: tuple = ()) -> None:
        ...

    @abstractmethod
    async def fetch_one(self, query: str, params: tuple = ()) -> dict[str, Any] | None:
        ...

    @abstractmethod
    async def fetch_all(self, query: str, params: tuple = ()) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    async def fetch_val(self, query: str, params: tuple = ()) -> Any:
        ...

    @abstractmethod
    async def execute_script(self, script: str) -> None:
        ...

    @abstractmethod
    async def close(self) -> None:
        ...


class SQLiteEngine(DatabaseEngine):
    """SQLite engine using aiosqlite."""

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._conn = None

    async def connect(self) -> None:
        import aiosqlite
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")
        logger.info("SQLite connected: %s", self._db_path)

    async def execute(self, query: str, params: tuple = ()) -> None:
        async with self._conn.execute(query, params):
            await self._conn.commit()

    async def fetch_one(self, query: str, params: tuple = ()) -> dict[str, Any] | None:
        async with self._conn.execute(query, params) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return dict(row)

    async def fetch_all(self, query: str, params: tuple = ()) -> list[dict[str, Any]]:
        async with self._conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def fetch_val(self, query: str, params: tuple = ()) -> Any:
        async with self._conn.execute(query, params) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return row[0]

    async def execute_script(self, script: str) -> None:
        await self._conn.executescript(script)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            logger.info("SQLite connection closed")


def _convert_placeholders(query: str) -> tuple[str, bool]:
    """Convert ? placeholders to $N for asyncpg. Returns (query, was_converted)."""
    count = 0

    def replacer(match: re.Match) -> str:
        nonlocal count
        count += 1
        return f"${count}"

    converted = re.sub(r"\?", replacer, query)
    return converted, count > 0


class PostgreSQLEngine(DatabaseEngine):
    """PostgreSQL engine using asyncpg with connection pooling."""

    def __init__(self, dsn: str):
        self._dsn = dsn
        self._pool = None

    async def connect(self) -> None:
        import asyncpg
        self._pool = await asyncpg.create_pool(self._dsn, min_size=2, max_size=10)
        logger.info("PostgreSQL pool created: %s", self._dsn.split("@")[-1] if "@" in self._dsn else "local")

    async def execute(self, query: str, params: tuple = ()) -> None:
        query, _ = _convert_placeholders(query)
        async with self._pool.acquire() as conn:
            await conn.execute(query, *params)

    async def fetch_one(self, query: str, params: tuple = ()) -> dict[str, Any] | None:
        query, _ = _convert_placeholders(query)
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)
            return dict(row) if row else None

    async def fetch_all(self, query: str, params: tuple = ()) -> list[dict[str, Any]]:
        query, _ = _convert_placeholders(query)
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(r) for r in rows]

    async def fetch_val(self, query: str, params: tuple = ()) -> Any:
        query, _ = _convert_placeholders(query)
        async with self._pool.acquire() as conn:
            return await conn.fetchval(query, *params)

    async def execute_script(self, script: str) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(script)

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
            logger.info("PostgreSQL pool closed")


async def create_engine(database_url: str) -> DatabaseEngine:
    """Factory: create the correct engine based on DATABASE_URL prefix."""
    if database_url.startswith("sqlite"):
        # sqlite:///path/to/db or sqlite:///bot.db
        path = database_url.split("///", 1)[-1] if "///" in database_url else "bot.db"
        engine = SQLiteEngine(path)
    elif database_url.startswith("postgresql") or database_url.startswith("postgres"):
        engine = PostgreSQLEngine(database_url)
    else:
        raise ValueError(f"Unsupported DATABASE_URL scheme: {database_url}")

    await engine.connect()
    return engine
