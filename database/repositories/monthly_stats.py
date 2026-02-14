from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from database.models import DailyStat, MessageTracking, MonthlyReport

if TYPE_CHECKING:
    from database.engine import DatabaseEngine


class MonthlyStatsRepository:
    def __init__(self, db: DatabaseEngine):
        self.db = db

    # ── Daily Stats ───────────────────────────

    async def upsert_daily(self, date: str, user_id: int, **kwargs) -> None:
        existing = await self.db.fetch_one(
            "SELECT id FROM daily_stats WHERE date = ? AND user_id = ?",
            (date, user_id),
        )
        if existing is None:
            cols = ["date", "user_id"] + list(kwargs.keys())
            placeholders = ", ".join("?" for _ in cols)
            vals = [date, user_id] + list(kwargs.values())
            await self.db.execute(
                f"INSERT INTO daily_stats ({', '.join(cols)}) VALUES ({placeholders})",
                tuple(vals),
            )
        else:
            if not kwargs:
                return
            sets = ", ".join(f"{k} = {k} + ?" if k != "channels_active" and k != "longest_message"
                            else f"{k} = MAX({k}, ?)" if k == "longest_message"
                            else f"{k} = ?"
                            for k in kwargs)
            vals = list(kwargs.values()) + [date, user_id]
            await self.db.execute(
                f"UPDATE daily_stats SET {sets} WHERE date = ? AND user_id = ?",
                tuple(vals),
            )

    async def increment_daily(self, date: str, user_id: int, field: str, amount: int = 1) -> None:
        existing = await self.db.fetch_one(
            "SELECT id FROM daily_stats WHERE date = ? AND user_id = ?",
            (date, user_id),
        )
        if existing is None:
            await self.db.execute(
                f"INSERT INTO daily_stats (date, user_id, {field}) VALUES (?, ?, ?)",
                (date, user_id, amount),
            )
        else:
            await self.db.execute(
                f"UPDATE daily_stats SET {field} = {field} + ? WHERE date = ? AND user_id = ?",
                (amount, date, user_id),
            )

    async def update_longest_message(self, date: str, user_id: int, char_count: int) -> None:
        existing = await self.db.fetch_one(
            "SELECT id, longest_message FROM daily_stats WHERE date = ? AND user_id = ?",
            (date, user_id),
        )
        if existing is None:
            await self.db.execute(
                "INSERT INTO daily_stats (date, user_id, longest_message) VALUES (?, ?, ?)",
                (date, user_id, char_count),
            )
        elif char_count > (existing["longest_message"] or 0):
            await self.db.execute(
                "UPDATE daily_stats SET longest_message = ? WHERE id = ?",
                (char_count, existing["id"]),
            )

    # ── Message Tracking ──────────────────────

    async def track_message(self, message_id: int, user_id: int, channel_id: int,
                            char_count: int, word_count: int, has_attachment: bool) -> None:
        await self.db.execute(
            "INSERT INTO message_tracking (message_id, user_id, channel_id, char_count, "
            "word_count, has_attachment) VALUES (?, ?, ?, ?, ?, ?)",
            (message_id, user_id, channel_id, char_count, word_count, int(has_attachment)),
        )

    async def mark_edited(self, message_id: int) -> None:
        await self.db.execute(
            "UPDATE message_tracking SET edited = 1 WHERE message_id = ?",
            (message_id,),
        )

    async def increment_reaction(self, message_id: int) -> None:
        await self.db.execute(
            "UPDATE message_tracking SET reaction_count = reaction_count + 1 WHERE message_id = ?",
            (message_id,),
        )

    # ── Channel Stats ─────────────────────────

    async def increment_channel(self, date: str, channel_id: int, user_id: int) -> None:
        existing = await self.db.fetch_one(
            "SELECT id FROM channel_stats WHERE date = ? AND channel_id = ?",
            (date, channel_id),
        )
        if existing is None:
            await self.db.execute(
                "INSERT INTO channel_stats (date, channel_id, message_count, unique_users) VALUES (?, ?, 1, 1)",
                (date, channel_id),
            )
        else:
            await self.db.execute(
                "UPDATE channel_stats SET message_count = message_count + 1 WHERE date = ? AND channel_id = ?",
                (date, channel_id),
            )

    # ── Word Frequency ────────────────────────

    async def increment_words(self, date: str, words: dict[str, int]) -> None:
        for word, count in words.items():
            existing = await self.db.fetch_one(
                "SELECT id FROM word_frequency WHERE date = ? AND word = ?",
                (date, word),
            )
            if existing is None:
                await self.db.execute(
                    "INSERT INTO word_frequency (date, word, count) VALUES (?, ?, ?)",
                    (date, word, count),
                )
            else:
                await self.db.execute(
                    "UPDATE word_frequency SET count = count + ? WHERE date = ? AND word = ?",
                    (count, date, word),
                )

    # ── Mention Tracking ──────────────────────

    async def increment_mentions(self, date: str, mentioned_ids: list[int]) -> None:
        for mid in mentioned_ids:
            existing = await self.db.fetch_one(
                "SELECT id FROM mention_tracking WHERE date = ? AND mentioned_id = ?",
                (date, mid),
            )
            if existing is None:
                await self.db.execute(
                    "INSERT INTO mention_tracking (date, mentioned_id, count) VALUES (?, ?, 1)",
                    (date, mid),
                )
            else:
                await self.db.execute(
                    "UPDATE mention_tracking SET count = count + 1 WHERE date = ? AND mentioned_id = ?",
                    (date, mid),
                )

    # ── Monthly Queries ───────────────────────

    async def get_monthly_top_messages(self, month: str, limit: int = 10) -> list[dict]:
        rows = await self.db.fetch_all(
            "SELECT user_id, SUM(messages_sent) as total FROM daily_stats "
            "WHERE date LIKE ? GROUP BY user_id ORDER BY total DESC LIMIT ?",
            (f"{month}%", limit),
        )
        return [dict(r) for r in rows]

    async def get_monthly_top_voice(self, month: str, limit: int = 10) -> list[dict]:
        rows = await self.db.fetch_all(
            "SELECT user_id, SUM(vc_minutes) as total FROM daily_stats "
            "WHERE date LIKE ? GROUP BY user_id ORDER BY total DESC LIMIT ?",
            (f"{month}%", limit),
        )
        return [dict(r) for r in rows]

    async def get_monthly_top_reactors(self, month: str, limit: int = 10) -> list[dict]:
        rows = await self.db.fetch_all(
            "SELECT user_id, SUM(reactions_given) as total FROM daily_stats "
            "WHERE date LIKE ? GROUP BY user_id ORDER BY total DESC LIMIT ?",
            (f"{month}%", limit),
        )
        return [dict(r) for r in rows]

    async def get_monthly_most_mentioned(self, month: str, limit: int = 10) -> list[dict]:
        rows = await self.db.fetch_all(
            "SELECT mentioned_id as user_id, SUM(count) as total FROM mention_tracking "
            "WHERE date LIKE ? GROUP BY mentioned_id ORDER BY total DESC LIMIT ?",
            (f"{month}%", limit),
        )
        return [dict(r) for r in rows]

    async def get_monthly_most_edits(self, month: str, limit: int = 10) -> list[dict]:
        rows = await self.db.fetch_all(
            "SELECT user_id, SUM(edits) as total FROM daily_stats "
            "WHERE date LIKE ? GROUP BY user_id ORDER BY total DESC LIMIT ?",
            (f"{month}%", limit),
        )
        return [dict(r) for r in rows]

    async def get_monthly_longest_message(self, month: str) -> dict | None:
        row = await self.db.fetch_one(
            "SELECT user_id, char_count, message_id, channel_id FROM message_tracking "
            "WHERE created_at LIKE ? ORDER BY char_count DESC LIMIT 1",
            (f"{month}%",),
        )
        return dict(row) if row else None

    async def get_monthly_top_word(self, month: str, limit: int = 10) -> list[dict]:
        rows = await self.db.fetch_all(
            "SELECT word, SUM(count) as total FROM word_frequency "
            "WHERE date LIKE ? GROUP BY word ORDER BY total DESC LIMIT ?",
            (f"{month}%", limit),
        )
        return [dict(r) for r in rows]

    async def get_monthly_most_reacted_image(self, month: str) -> dict | None:
        row = await self.db.fetch_one(
            "SELECT message_id, user_id, channel_id, reaction_count FROM message_tracking "
            "WHERE created_at LIKE ? AND has_attachment = 1 ORDER BY reaction_count DESC LIMIT 1",
            (f"{month}%",),
        )
        return dict(row) if row else None

    async def get_monthly_top_channels(self, month: str, limit: int = 10) -> list[dict]:
        rows = await self.db.fetch_all(
            "SELECT channel_id, SUM(message_count) as total FROM channel_stats "
            "WHERE date LIKE ? GROUP BY channel_id ORDER BY total DESC LIMIT ?",
            (f"{month}%", limit),
        )
        return [dict(r) for r in rows]

    async def get_active_days(self, month: str, user_id: int) -> int:
        count = await self.db.fetch_val(
            "SELECT COUNT(DISTINCT date) FROM daily_stats "
            "WHERE date LIKE ? AND user_id = ? AND messages_sent > 0",
            (f"{month}%", user_id),
        )
        return count or 0

    async def get_monthly_most_active_days(self, month: str, limit: int = 10) -> list[dict]:
        rows = await self.db.fetch_all(
            "SELECT user_id, COUNT(DISTINCT date) as total FROM daily_stats "
            "WHERE date LIKE ? AND messages_sent > 0 GROUP BY user_id ORDER BY total DESC LIMIT ?",
            (f"{month}%", limit),
        )
        return [dict(r) for r in rows]

    async def get_user_monthly_stats(self, month: str, user_id: int) -> dict:
        row = await self.db.fetch_one(
            "SELECT SUM(messages_sent) as messages, SUM(vc_minutes) as voice, "
            "SUM(reactions_given) as reactions, SUM(edits) as edits, "
            "MAX(longest_message) as longest, COUNT(DISTINCT date) as active_days "
            "FROM daily_stats WHERE date LIKE ? AND user_id = ?",
            (f"{month}%", user_id),
        )
        return dict(row) if row else {}

    # ── Monthly Reports ───────────────────────

    async def save_report(self, month: str, report_data: dict, message_id: int | None = None,
                          channel_id: int | None = None) -> int:
        await self.db.execute(
            "INSERT INTO monthly_reports (month, report_data, message_id, channel_id) VALUES (?, ?, ?, ?)",
            (month, json.dumps(report_data), message_id, channel_id),
        )
        return await self.db.fetch_val("SELECT last_insert_rowid()")

    async def get_report(self, month: str) -> MonthlyReport | None:
        row = await self.db.fetch_one(
            "SELECT * FROM monthly_reports WHERE month = ? ORDER BY created_at DESC LIMIT 1",
            (month,),
        )
        return MonthlyReport(**row) if row else None
