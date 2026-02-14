from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.config import Config


class XPCalculator:
    """Level math and milestone detection.

    Formula: xp_needed(level) = 50 * level^2 + 50 * level
    Total XP to reach level N = sum of xp_needed(1..N)
    """

    def __init__(self, config: Config):
        xp_cfg = config.xp
        self._milestone_levels: list[int] = xp_cfg.get("milestone_levels", [5, 10, 15, 20, 25, 30, 40, 50, 75, 100])
        self._age_verify_level: int = xp_cfg.get("age_verify_level", 15)

    @staticmethod
    def xp_for_level(level: int) -> int:
        """XP needed to go FROM level-1 TO level."""
        return 50 * (level ** 2) + 50 * level

    @staticmethod
    def total_xp_for_level(level: int) -> int:
        """Cumulative XP needed to reach a given level from 0."""
        # Sum of 50*k^2 + 50*k for k=1..level
        # = 50 * (level)(level+1)(2level+1)/6 + 50 * level*(level+1)/2
        total = 0
        for k in range(1, level + 1):
            total += 50 * (k ** 2) + 50 * k
        return total

    @staticmethod
    def calculate_level(total_xp: int) -> int:
        """Calculate level from total XP."""
        level = 0
        cumulative = 0
        while True:
            next_needed = 50 * ((level + 1) ** 2) + 50 * (level + 1)
            if cumulative + next_needed > total_xp:
                break
            cumulative += next_needed
            level += 1
        return level

    @staticmethod
    def xp_to_next_level(total_xp: int) -> int:
        """XP remaining until next level up."""
        level = XPCalculator.calculate_level(total_xp)
        cumulative = XPCalculator.total_xp_for_level(level)
        next_needed = 50 * ((level + 1) ** 2) + 50 * (level + 1)
        return cumulative + next_needed - total_xp

    @staticmethod
    def xp_progress_in_level(total_xp: int) -> tuple[int, int]:
        """Returns (current_xp_in_level, xp_needed_for_level)."""
        level = XPCalculator.calculate_level(total_xp)
        cumulative = XPCalculator.total_xp_for_level(level)
        current_in_level = total_xp - cumulative
        needed = 50 * ((level + 1) ** 2) + 50 * (level + 1)
        return current_in_level, needed

    def check_milestones(self, old_level: int, new_level: int) -> list[int]:
        """Return list of milestone levels crossed between old and new level."""
        return [m for m in self._milestone_levels if old_level < m <= new_level]

    def is_age_verify_eligible(self, level: int) -> bool:
        return level >= self._age_verify_level

    def xp_for_import_level(self, level: int) -> int:
        """Calculate equivalent total XP for an imported level."""
        return self.total_xp_for_level(level)
