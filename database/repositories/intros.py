from __future__ import annotations

from typing import TYPE_CHECKING, Any

from database.models import Intro

if TYPE_CHECKING:
    from database.engine import DatabaseEngine


class IntroRepository:
    def __init__(self, db: DatabaseEngine):
        self.db = db

    async def create(self, user_id: int, age: int, preferred_name: str,
                     pronouns: str, location: str, region_key: str | None,
                     bio: str, submission_num: int = 1) -> int:
        await self.db.execute(
            "INSERT INTO intros (user_id, age, preferred_name, pronouns, location, "
            "region_key, bio, submission_num) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, age, preferred_name, pronouns, location, region_key, bio, submission_num),
        )
        row_id = await self.db.fetch_val("SELECT last_insert_rowid()")
        return row_id

    async def get(self, intro_id: int) -> Intro | None:
        row = await self.db.fetch_one("SELECT * FROM intros WHERE id = ?", (intro_id,))
        return Intro(**row) if row else None

    async def get_latest_for_user(self, user_id: int) -> Intro | None:
        row = await self.db.fetch_one(
            "SELECT * FROM intros WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (user_id,),
        )
        return Intro(**row) if row else None

    async def get_pending(self) -> list[Intro]:
        rows = await self.db.fetch_all(
            "SELECT * FROM intros WHERE status IN ('submitted', 'resubmitted') "
            "ORDER BY created_at ASC",
        )
        return [Intro(**r) for r in rows]

    async def count_for_user(self, user_id: int) -> int:
        count = await self.db.fetch_val(
            "SELECT COUNT(*) FROM intros WHERE user_id = ?", (user_id,),
        )
        return count or 0

    async def update_status(self, intro_id: int, status: str, reviewer_id: int | None = None,
                            review_action: str | None = None, review_reason: str | None = None) -> None:
        await self.db.execute(
            "UPDATE intros SET status = ?, reviewer_id = ?, review_action = ?, "
            "review_reason = ?, reviewed_at = datetime('now') WHERE id = ?",
            (status, reviewer_id, review_action, review_reason, intro_id),
        )

    async def set_welcome_messages(self, intro_id: int, welcome_msg_id: int, intro_msg_id: int) -> None:
        await self.db.execute(
            "UPDATE intros SET welcome_msg_id = ?, intro_msg_id = ? WHERE id = ?",
            (welcome_msg_id, intro_msg_id, intro_id),
        )
