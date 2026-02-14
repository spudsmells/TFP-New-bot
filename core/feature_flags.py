from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.config import Config

logger = logging.getLogger(__name__)

# Maps feature flag names to cog module paths
COG_FLAG_MAP: dict[str, str] = {
    "diagnostics": "cogs.diagnostics",
    "onboarding": "cogs.onboarding",
    "xp": "cogs.xp",
    "auto_threads": "cogs.auto_threads",
    "intros": "cogs.intros",
    "bully": "cogs.bully",
    "music": "cogs.music",
    "tickets_member": "cogs.tickets_member",
    "tickets_staff": "cogs.tickets_staff",
    "age_verify": "cogs.age_verify",
    "ticket_lifecycle": "cogs.ticket_lifecycle",
    "ticket_panel": "cogs.ticket_panel",
    "milestones": "cogs.milestones",
    "achievements": "cogs.achievements",
    "monthly_stats": "cogs.monthly_stats",
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
