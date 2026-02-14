from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.config import Config

logger = logging.getLogger(__name__)

# Maps feature flag names to cog module paths
COG_FLAG_MAP: dict[str, str] = {
    # Core / Diagnostics (always recommended)
    "diagnostics": "cogs.diagnostics",
    "feature_toggle": "cogs.feature_toggle",  # Runtime feature management

    # Onboarding & Member Management
    "onboarding": "cogs.onboarding",
    "intros": "cogs.intros",
    "age_verify": "cogs.age_verify",

    # Progression & Engagement
    "xp": "cogs.xp",
    "milestones": "cogs.milestones",
    "achievements": "cogs.achievements",

    # Tickets & Support
    "tickets_member": "cogs.tickets_member",
    "tickets_staff": "cogs.tickets_staff",
    "ticket_lifecycle": "cogs.ticket_lifecycle",
    "ticket_panel": "cogs.ticket_panel",

    # Fun & Utilities
    "bully": "cogs.bully",
    "music": "cogs.music",
    "auto_threads": "cogs.auto_threads",
    "monthly_stats": "cogs.monthly_stats",

    # === NEW FEATURES (Phase 2 & 3) ===

    # Moderation Suite (Phase 2)
    "moderation": "cogs.moderation",
    "roles": "cogs.roles",
    "channels": "cogs.channels",
    "sticky": "cogs.sticky",

    # Community Features (Phase 3)
    "birthdays": "cogs.birthdays",
    "counting": "cogs.counting",
    "confessions": "cogs.confessions",
    "bump": "cogs.bump",
}


def get_enabled_cogs(config: Config) -> list[str]:
    """Return list of cog module paths that are enabled in config."""
    flags = config.get("features", {})
    enabled = []
    for flag, cog_path in COG_FLAG_MAP.items():
        if flags.get(flag, False):
            enabled.append(cog_path)
            logger.info("Feature enabled: %s -> %s", flag, cog_path)
        else:
            logger.debug("Feature disabled: %s", flag)
    return enabled
