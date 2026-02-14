from __future__ import annotations

import time
from collections import defaultdict


class RateLimiter:
    """In-memory token bucket per (user_id, action) pair."""

    def __init__(self):
        # Key: (user_id, action) -> list of timestamps
        self._hits: dict[tuple[int, str], list[float]] = defaultdict(list)

    def check(self, user_id: int, action: str, limit: int, window_seconds: float) -> bool:
        """Return True if action is allowed, False if rate-limited."""
        key = (user_id, action)
        now = time.monotonic()
        cutoff = now - window_seconds

        # Prune old entries
        self._hits[key] = [t for t in self._hits[key] if t > cutoff]

        if len(self._hits[key]) >= limit:
            return False

        self._hits[key].append(now)
        return True

    def time_until_available(self, user_id: int, action: str, limit: int, window_seconds: float) -> float:
        """Return seconds until next action is allowed. 0 if already allowed."""
        key = (user_id, action)
        now = time.monotonic()
        cutoff = now - window_seconds

        hits = [t for t in self._hits.get(key, []) if t > cutoff]
        if len(hits) < limit:
            return 0.0

        # Oldest hit in window — wait until it expires
        oldest = min(hits)
        return max(0.0, (oldest + window_seconds) - now)

    def reset(self, user_id: int, action: str) -> None:
        """Clear rate limit for a specific user/action pair."""
        key = (user_id, action)
        self._hits.pop(key, None)

    def cleanup(self, max_age: float = 3600.0) -> int:
        """Remove all entries older than max_age. Returns count removed."""
        now = time.monotonic()
        cutoff = now - max_age
        removed = 0
        keys_to_remove = []
        for key, hits in self._hits.items():
            self._hits[key] = [t for t in hits if t > cutoff]
            removed += len(hits) - len(self._hits[key])
            if not self._hits[key]:
                keys_to_remove.append(key)
        for key in keys_to_remove:
            del self._hits[key]
        return removed
