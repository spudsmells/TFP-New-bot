from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from database.repositories.music import MusicRepository
from services.music_converter import convert, extract_music_urls

if TYPE_CHECKING:
    from core.bot import GayborhoodBot

logger = logging.getLogger(__name__)


class MusicCog(commands.Cog, name="MusicCog"):
    """Release 2.5B: Automatic music link conversion to YouTube."""

    def __init__(self, bot: GayborhoodBot):
        self.bot = bot
        self._repo = MusicRepository(bot.db)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if message.guild.id != self.bot.config.guild_id:
            return

        urls = extract_music_urls(message.content)
        if not urls:
            return

        # Rate limit
        limit = self.bot.config.rate_limits.get("music_per_user", 3)
        window = self.bot.config.rate_limits.get("music_window_seconds", 600)
        if not self.bot.rate_limiter.check(message.author.id, "music_convert", limit, window):
            return

        for url, platform in urls[:1]:  # Process first link only
            # Check cache
            cached = await self._repo.find_by_url(url)
            if cached and cached.youtube_url:
                embed = self.bot.embed_builder.info(
                    title=f"\U0001f3b5 {cached.artist or 'Track'} - {cached.title or 'Unknown'}",
                    description=f"[YouTube Link]({cached.youtube_url})",
                )
                embed.set_footer(text=f"Converted from {platform.replace('_', ' ').title()}")
                await message.reply(embed=embed, mention_author=False)
                return

            # Convert
            result = await convert(
                url, platform,
                spotify_client_id=self.bot.config.spotify_client_id,
                spotify_client_secret=self.bot.config.spotify_client_secret,
            )

            # Store result
            await self._repo.create(
                source_url=url,
                platform=platform,
                artist=result.artist,
                title=result.title,
                youtube_url=result.youtube_url,
                success=result.success,
                requested_by=message.author.id,
            )

            if result.success and result.youtube_url:
                title_str = f"{result.artist} - {result.title}" if result.artist and result.title else "Track"
                embed = self.bot.embed_builder.info(
                    title=f"\U0001f3b5 {title_str}",
                    description=f"[YouTube Link]({result.youtube_url})",
                )
                embed.set_footer(text=f"Converted from {platform.replace('_', ' ').title()}")
                await message.reply(embed=embed, mention_author=False)
            else:
                logger.debug("Music conversion failed for %s: %s", url, result.error)


async def setup(bot: GayborhoodBot):
    await bot.add_cog(MusicCog(bot))
