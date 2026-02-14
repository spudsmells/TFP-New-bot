from __future__ import annotations

from typing import TYPE_CHECKING

# Re-export from onboarding for clean imports
from views.onboarding import FallbackRetryView

if TYPE_CHECKING:
    from core.bot import GayborhoodBot

__all__ = ["FallbackRetryView"]
