"""Content filter — keeps the muppets from posting absolute shite"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from better_profanity import profanity

from core.errors import ContentFilterError

logger = logging.getLogger(__name__)


class ContentFilter:
    """
    Validates user-submitted content for bios, ticket reasons, etc.

    Checks for:
    - Slurs (from data/slurs.txt)
    - Profanity (via better-profanity library)
    - Length requirements
    - Other dodgy shite
    """

    def __init__(self):
        self.slurs: set[str] = set()
        self._load_slurs()
        profanity.load_censor_words()  # Load default profanity list

    def _load_slurs(self) -> None:
        """Load slurs from data/slurs.txt"""
        slurs_path = Path("data/slurs.txt")
        if not slurs_path.exists():
            logger.warning("data/slurs.txt not found — slur filtering disabled")
            return

        try:
            with slurs_path.open("r", encoding="utf-8") as f:
                self.slurs = {
                    line.strip().lower() for line in f if line.strip() and not line.startswith("#")
                }
            logger.info("Loaded %d slurs from data/slurs.txt", len(self.slurs))
        except Exception:
            logger.exception("Failed to load slurs.txt")

    def check_slurs(self, text: str) -> list[str]:
        """
        Check text for slurs.

        Returns list of matched slurs (lowercased).
        """
        if not self.slurs:
            return []

        text_lower = text.lower()
        found = []

        for slur in self.slurs:
            # Check for whole word matches (not just substrings)
            # cos we don't wanna flag "assessment" for having "ass" in it innit
            words = text_lower.split()
            if slur in words or f" {slur} " in f" {text_lower} ":
                found.append(slur)

        return found

    def check_profanity(self, text: str) -> bool:
        """
        Check if text contains profanity.

        Returns True if profanity detected, False otherwise.
        """
        return profanity.contains_profanity(text)

    def validate_bio(
        self, text: str, min_length: int = 30, max_length: int = 400
    ) -> None:
        """
        Validate intro bio.

        Raises ContentFilterError if validation fails with reasons.

        Args:
            text: Bio text to validate
            min_length: Minimum character count (default 30)
            max_length: Maximum character count (default 400)
        """
        reasons = []

        # Length check
        if len(text) < min_length:
            reasons.append(f"Bio must be at least {min_length} characters")
        if len(text) > max_length:
            reasons.append(f"Bio must be no more than {max_length} characters")

        # Slur check
        slurs_found = self.check_slurs(text)
        if slurs_found:
            reasons.append("Bio contains prohibited language")
            logger.warning("Bio rejected for slurs: %s", slurs_found)

        # Profanity check (bit lenient cos we're not puritans)
        # Only reject if there's excessive profanity
        if self.check_profanity(text):
            # Count profane words
            profane_count = sum(1 for word in text.split() if profanity.contains_profanity(word))
            if profane_count > 2:  # Allow a couple of swears, we're not bloody Mormons
                reasons.append("Bio contains excessive profanity")

        if reasons:
            raise ContentFilterError(reasons)

    def validate_reason(
        self, text: str, min_length: int = 10, max_length: int = 500
    ) -> None:
        """
        Validate ticket reason or other short text.

        Less strict than bio validation.

        Args:
            text: Text to validate
            min_length: Minimum character count (default 10)
            max_length: Maximum character count (default 500)
        """
        reasons = []

        # Length check
        if len(text) < min_length:
            reasons.append(f"Text must be at least {min_length} characters")
        if len(text) > max_length:
            reasons.append(f"Text must be no more than {max_length} characters")

        # Slur check
        slurs_found = self.check_slurs(text)
        if slurs_found:
            reasons.append("Text contains prohibited language")
            logger.warning("Text rejected for slurs: %s", slurs_found)

        if reasons:
            raise ContentFilterError(reasons)

    def sanitize(self, text: str) -> str:
        """
        Sanitize text by censoring profanity.

        Returns text with profanity censored (replaced with ***).
        """
        return profanity.censor(text)

    def is_low_effort(self, text: str) -> bool:
        """
        Check if text is low-effort spam.

        Returns True if text is likely spam/low-effort.
        """
        # Check for repeated characters (aaaaaa, lol lol lol, etc)
        words = text.split()
        if len(words) == 1 and len(set(text.lower())) < 3:
            return True

        # Check for single repeated word
        if len(set(w.lower() for w in words)) == 1 and len(words) > 3:
            return True

        # Check for single emoji or just numbers
        if len(text.strip()) < 5:
            return True

        return False
