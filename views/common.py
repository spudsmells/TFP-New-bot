from __future__ import annotations

import re
from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from core.bot import GayborhoodBot


class PersistentView(discord.ui.View):
    """Base class for persistent views (timeout=None, survives restarts)."""

    def __init__(self, bot: GayborhoodBot):
        super().__init__(timeout=None)
        self.bot = bot


class DynamicButton(discord.ui.DynamicItem[discord.ui.Button]):
    """Base class for DynamicItem buttons with entity ID in custom_id.

    Subclasses must define:
        template: str  — custom_id format string, e.g. "intro_review:{id}:{action}"
        pattern: re.Pattern — regex with named groups to parse custom_id
    """

    template: str = ""
    pattern: re.Pattern = re.compile(r"")

    def __init__(self, bot: GayborhoodBot, **kwargs):
        self.bot = bot
        custom_id = self.template.format(**kwargs)
        super().__init__(
            discord.ui.Button(custom_id=custom_id, **self._button_kwargs(**kwargs)),
        )

    def _button_kwargs(self, **kwargs) -> dict:
        """Override to set label, style, emoji, etc."""
        return {}

    @classmethod
    async def from_custom_id(
        cls,
        interaction: discord.Interaction,
        item: discord.ui.Button,
        match: re.Match,
    ):
        """Called by discord.py when a stored button is clicked."""
        raise NotImplementedError
