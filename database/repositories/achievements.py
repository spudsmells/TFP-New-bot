from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from database.models import Achievement, UserAchievement

if TYPE_CHECKING:
    from database.engine import DatabaseEngine

DATA_DIR = Path(__file__).parent.parent.parent / "data"


class AchievementRepository:
    def __init__(self, db: DatabaseEngine):
        self.db = db

    async def get(self, achievement_id: int) -> Achievement | None:
        row = await self.db.fetch_one("SELECT * FROM achievements WHERE id = ?", (achievement_id,))
        return Achievement(**row) if row else None

    async def get_by_key(self, key: str) -> Achievement | None:
        row = await self.db.fetch_one("SELECT * FROM achievements WHERE key = ?", (key,))
        return Achievement(**row) if row else None

    async def get_active(self) -> list[Achievement]:
        rows = await self.db.fetch_all(
            "SELECT * FROM achievements WHERE active = 1 ORDER BY trigger_type, trigger_value",
        )
        return [Achievement(**r) for r in rows]

    async def get_by_trigger(self, trigger_type: str) -> list[Achievement]:
        rows = await self.db.fetch_all(
            "SELECT * FROM achievements WHERE trigger_type = ? AND active = 1 ORDER BY trigger_value",
            (trigger_type,),
        )
        return [Achievement(**r) for r in rows]

    async def get_all(self) -> list[Achievement]:
        rows = await self.db.fetch_all("SELECT * FROM achievements ORDER BY category, trigger_value")
        return [Achievement(**r) for r in rows]

    async def create(self, key: str, name: str, description: str, trigger_type: str,
                     trigger_value: int, icon: str = "star", rarity: str = "common",
                     category: str = "general", xp_reward: int = 0) -> int:
        await self.db.execute(
            "INSERT INTO achievements (key, name, description, icon, rarity, category, "
            "trigger_type, trigger_value, xp_reward) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (key, name, description, icon, rarity, category, trigger_type, trigger_value, xp_reward),
        )
        return await self.db.fetch_val("SELECT last_insert_rowid()")

    async def update(self, achievement_id: int, **kwargs) -> None:
        if not kwargs:
            return
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [achievement_id]
        await self.db.execute(f"UPDATE achievements SET {sets} WHERE id = ?", tuple(vals))

    async def delete(self, achievement_id: int) -> None:
        await self.db.execute("DELETE FROM user_achievements WHERE achievement_id = ?", (achievement_id,))
        await self.db.execute("DELETE FROM achievements WHERE id = ?", (achievement_id,))

    # ── User Achievements ─────────────────────

    async def unlock(self, user_id: int, achievement_id: int) -> bool:
        """Unlock an achievement for a user. Returns False if already unlocked."""
        existing = await self.db.fetch_one(
            "SELECT id FROM user_achievements WHERE user_id = ? AND achievement_id = ?",
            (user_id, achievement_id),
        )
        if existing:
            return False
        await self.db.execute(
            "INSERT INTO user_achievements (user_id, achievement_id) VALUES (?, ?)",
            (user_id, achievement_id),
        )
        return True

    async def revoke(self, user_id: int, achievement_id: int) -> bool:
        existing = await self.db.fetch_one(
            "SELECT id FROM user_achievements WHERE user_id = ? AND achievement_id = ?",
            (user_id, achievement_id),
        )
        if not existing:
            return False
        await self.db.execute(
            "DELETE FROM user_achievements WHERE user_id = ? AND achievement_id = ?",
            (user_id, achievement_id),
        )
        return True

    async def mark_notified(self, user_id: int, achievement_id: int) -> None:
        await self.db.execute(
            "UPDATE user_achievements SET notified = 1 WHERE user_id = ? AND achievement_id = ?",
            (user_id, achievement_id),
        )

    async def get_user_achievements(self, user_id: int) -> list[tuple[UserAchievement, Achievement]]:
        rows = await self.db.fetch_all(
            "SELECT ua.id, ua.user_id, ua.achievement_id, ua.unlocked_at, ua.notified, "
            "a.key, a.name, a.description, a.icon, a.rarity, a.category, "
            "a.trigger_type, a.trigger_value, a.xp_reward, a.active, a.created_at as a_created "
            "FROM user_achievements ua JOIN achievements a ON ua.achievement_id = a.id "
            "WHERE ua.user_id = ? ORDER BY ua.unlocked_at DESC",
            (user_id,),
        )
        results = []
        for r in rows:
            ua = UserAchievement(
                id=r["id"], user_id=r["user_id"], achievement_id=r["achievement_id"],
                unlocked_at=r["unlocked_at"], notified=r["notified"],
            )
            ach = Achievement(
                id=r["achievement_id"], key=r["key"], name=r["name"],
                description=r["description"], icon=r["icon"], rarity=r["rarity"],
                category=r["category"], trigger_type=r["trigger_type"],
                trigger_value=r["trigger_value"], xp_reward=r["xp_reward"],
                active=r["active"], created_at=r["a_created"],
            )
            results.append((ua, ach))
        return results

    async def get_user_achievement_ids(self, user_id: int) -> set[int]:
        rows = await self.db.fetch_all(
            "SELECT achievement_id FROM user_achievements WHERE user_id = ?",
            (user_id,),
        )
        return {r["achievement_id"] for r in rows}

    async def count_user_achievements(self, user_id: int) -> int:
        return await self.db.fetch_val(
            "SELECT COUNT(*) FROM user_achievements WHERE user_id = ?",
            (user_id,),
        ) or 0

    async def seed_defaults(self) -> int:
        """Seed from data/default_achievements.json."""
        path = DATA_DIR / "default_achievements.json"
        if not path.exists():
            return 0

        data = json.loads(path.read_text())
        count = 0
        for a in data.get("achievements", []):
            existing = await self.get_by_key(a["key"])
            if not existing:
                await self.create(
                    key=a["key"], name=a["name"], description=a["description"],
                    trigger_type=a["trigger_type"], trigger_value=a["trigger_value"],
                    icon=a.get("icon", "star"), rarity=a.get("rarity", "common"),
                    category=a.get("category", "general"), xp_reward=a.get("xp_reward", 0),
                )
                count += 1
        return count
