"""Embed builder — cos we're not animals, we use pretty embeds"""
from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from core.config import Config


class EmbedBuilder:
    """
    Builds consistently-styled embeds with server branding.

    Saves having to set colours and footers everywhere like a muppet.
    """

    # Colour scheme (the gay agenda in hex form)
    COLOUR_SUCCESS = 0x43B581  # green
    COLOUR_ERROR = 0xF04747  # red
    COLOUR_WARNING = 0xFAA61A  # yellow/orange
    COLOUR_INFO = 0xA78BFA  # purple (gay rights)
    COLOUR_NEUTRAL = 0x36393F  # dark grey

    def __init__(self, config: Config):
        self.config = config
        self.footer_text = config.embeds.get("footer_text", "The Gayborhood Bot")
        self.thumbnail_url = config.embeds.get("thumbnail_url")

    def _build(
        self,
        title: str | None = None,
        description: str | None = None,
        colour: int | None = None,
    ) -> discord.Embed:
        """Base embed builder with common styling"""
        embed = discord.Embed(
            title=title,
            description=description,
            colour=colour or self.COLOUR_NEUTRAL,
        )

        # Add footer
        embed.set_footer(text=self.footer_text)

        # Add thumbnail if configured
        if self.thumbnail_url:
            embed.set_thumbnail(url=self.thumbnail_url)

        return embed

    def success(
        self, title: str | None = None, description: str | None = None
    ) -> discord.Embed:
        """Green embed for successful operations"""
        return self._build(title=title, description=description, colour=self.COLOUR_SUCCESS)

    def error(
        self, title: str | None = None, description: str | None = None
    ) -> discord.Embed:
        """Red embed for errors — when shit goes tits up"""
        return self._build(title=title, description=description, colour=self.COLOUR_ERROR)

    def warning(
        self, title: str | None = None, description: str | None = None
    ) -> discord.Embed:
        """Yellow/orange embed for warnings"""
        return self._build(title=title, description=description, colour=self.COLOUR_WARNING)

    def info(
        self, title: str | None = None, description: str | None = None
    ) -> discord.Embed:
        """Purple embed for informational messages"""
        return self._build(title=title, description=description, colour=self.COLOUR_INFO)

    def neutral(
        self, title: str | None = None, description: str | None = None
    ) -> discord.Embed:
        """Grey embed for neutral messages"""
        return self._build(title=title, description=description, colour=self.COLOUR_NEUTRAL)

    def custom(
        self,
        title: str | None = None,
        description: str | None = None,
        colour: int | None = None,
        fields: list[tuple[str, str, bool]] | None = None,
    ) -> discord.Embed:
        """
        Custom embed with fields.

        Args:
            title: Embed title
            description: Embed description
            colour: Custom colour (hex int)
            fields: List of (name, value, inline) tuples
        """
        embed = self._build(title=title, description=description, colour=colour)

        if fields:
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)

        return embed
