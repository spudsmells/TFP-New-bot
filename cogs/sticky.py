"""Sticky messages — messages that stick to the bottom of channels like good little soldiers"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from database.repositories.sticky import StickyRepository

if TYPE_CHECKING:
    from core.bot import GayborhoodBot

logger = logging.getLogger(__name__)


class StickyMessagesCog(commands.Cog, name="StickyMessagesCog"):
    """Sticky messages that auto-repost to stay at bottom of channels"""

    def __init__(self, bot: GayborhoodBot):
        self.bot = bot
        self.repo = StickyRepository(bot.db)
        # Cache of channel_id -> (message_id, embed_type)
        self._sticky_cache: dict[int, tuple[int, str]] = {}

    async def cog_load(self):
        """Load sticky messages into cache on startup"""
        try:
            stickies = await self.repo.get_all()
            for sticky in stickies:
                self._sticky_cache[sticky["channel_id"]] = (
                    sticky["message_id"],
                    sticky["embed_type"],
                )
            logger.info("Loaded %d sticky messages into cache", len(stickies))
        except Exception:
            logger.exception("Failed to load sticky messages cache")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Repost sticky message when someone sends a message"""
        # Ignore DMs
        if not message.guild:
            return

        # Ignore bot messages
        if message.author.bot:
            return

        # Check if this channel has a sticky message
        if message.channel.id not in self._sticky_cache:
            return

        old_message_id, embed_type = self._sticky_cache[message.channel.id]

        try:
            # Delete old sticky message
            try:
                old_msg = await message.channel.fetch_message(old_message_id)
                await old_msg.delete()
            except discord.NotFound:
                logger.debug("Old sticky message %d not found, probably already deleted", old_message_id)
            except discord.HTTPException as e:
                logger.warning("Failed to delete old sticky message: %s", e)

            # Create new sticky message based on type
            embed = self._create_sticky_embed(embed_type)
            if not embed:
                logger.error("Unknown sticky embed type: %s", embed_type)
                return

            new_msg = await message.channel.send(embed=embed)

            # Update cache and database
            self._sticky_cache[message.channel.id] = (new_msg.id, embed_type)
            await self.repo.update_message_id(message.channel.id, new_msg.id)

        except Exception:
            logger.exception("Error reposting sticky message in channel %s", message.channel.id)

    def _create_sticky_embed(self, embed_type: str) -> discord.Embed | None:
        """Create sticky embed based on type"""
        if embed_type == "rules":
            return self.bot.embed_builder.info(
                title="📜 Server Rules",
                description="Please read and follow our server rules:\n"
                "• Be respectful and kind\n"
                "• No harassment, hate speech, or discrimination\n"
                "• Keep conversations appropriate\n"
                "• Listen to moderators\n\n"
                "Full rules: Check the rules channel",
            )
        elif embed_type == "welcome":
            return self.bot.embed_builder.info(
                title="👋 Welcome!",
                description="Welcome to the server! Please introduce yourself and read the rules.",
            )
        elif embed_type == "info":
            return self.bot.embed_builder.info(
                title="ℹ️ Information",
                description="Important information about this channel.",
            )
        elif embed_type == "custom":
            # For custom messages, we'd need to store the content
            # For now, just return a generic one
            return self.bot.embed_builder.neutral(
                title="📌 Pinned Message",
                description="This is a sticky message.",
            )
        else:
            return None

    @app_commands.command(name="sticky-set", description="Set a sticky message for this channel")
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.describe(
        embed_type="Type of sticky message (rules/welcome/info/custom)",
        title="Custom title (only for custom type)",
        description="Custom description (only for custom type)",
    )
    async def sticky_set(
        self,
        interaction: discord.Interaction,
        embed_type: str,
        title: str | None = None,
        description: str | None = None,
    ):
        """Set a sticky message for the current channel"""
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(
                "Sticky messages only work in text channels.", ephemeral=True
            )
            return

        # Validate embed type
        valid_types = ["rules", "welcome", "info", "custom"]
        if embed_type.lower() not in valid_types:
            await interaction.response.send_message(
                f"Invalid embed type. Must be one of: {', '.join(valid_types)}",
                ephemeral=True,
            )
            return

        embed_type = embed_type.lower()

        # For custom type, require title and description
        if embed_type == "custom":
            if not title or not description:
                await interaction.response.send_message(
                    "For custom sticky messages, you must provide both title and description.",
                    ephemeral=True,
                )
                return
            # Create custom embed
            embed = self.bot.embed_builder.neutral(title=title, description=description)
        else:
            # Create predefined embed
            embed = self._create_sticky_embed(embed_type)
            if not embed:
                await interaction.response.send_message(
                    f"Failed to create embed for type: {embed_type}",
                    ephemeral=True,
                )
                return

        try:
            # Delete existing sticky message if any
            if interaction.channel.id in self._sticky_cache:
                old_message_id, _ = self._sticky_cache[interaction.channel.id]
                try:
                    old_msg = await interaction.channel.fetch_message(old_message_id)
                    await old_msg.delete()
                except discord.NotFound:
                    pass
                except discord.HTTPException:
                    pass

                # Remove from database
                await self.repo.delete_by_channel(interaction.channel.id)

            # Post new sticky message
            sticky_msg = await interaction.channel.send(embed=embed)

            # Save to database
            await self.repo.create(interaction.channel.id, sticky_msg.id, embed_type)

            # Update cache
            self._sticky_cache[interaction.channel.id] = (sticky_msg.id, embed_type)

            # Log to audit
            await self.bot.audit_logger.log(
                "sticky_set",
                actor_id=interaction.user.id,
                details=f"Channel {interaction.channel.id}, type: {embed_type}",
            )

            await interaction.response.send_message(
                f"✅ Sticky message set for {interaction.channel.mention}",
                ephemeral=True,
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "I don't have permissions to send messages in this channel.",
                ephemeral=True,
            )
        except discord.HTTPException as e:
            await interaction.response.send_message(
                f"Failed to set sticky message: {e}", ephemeral=True
            )

    @app_commands.command(name="sticky-remove", description="Remove sticky message from this channel")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def sticky_remove(self, interaction: discord.Interaction):
        """Remove sticky message from current channel"""
        if interaction.channel.id not in self._sticky_cache:
            await interaction.response.send_message(
                "This channel doesn't have a sticky message.", ephemeral=True
            )
            return

        try:
            # Delete the sticky message
            old_message_id, _ = self._sticky_cache[interaction.channel.id]
            try:
                old_msg = await interaction.channel.fetch_message(old_message_id)
                await old_msg.delete()
            except discord.NotFound:
                pass
            except discord.HTTPException:
                pass

            # Remove from database
            await self.repo.delete_by_channel(interaction.channel.id)

            # Remove from cache
            del self._sticky_cache[interaction.channel.id]

            # Log to audit
            await self.bot.audit_logger.log(
                "sticky_removed",
                actor_id=interaction.user.id,
                details=f"Channel {interaction.channel.id}",
            )

            await interaction.response.send_message(
                f"✅ Sticky message removed from {interaction.channel.mention}",
                ephemeral=True,
            )

        except Exception as e:
            logger.exception("Error removing sticky message")
            await interaction.response.send_message(
                f"Failed to remove sticky message: {e}", ephemeral=True
            )

    @app_commands.command(name="sticky-list", description="List all sticky messages")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def sticky_list(self, interaction: discord.Interaction):
        """List all sticky messages in the server"""
        if not self._sticky_cache:
            await interaction.response.send_message(
                "No sticky messages configured.", ephemeral=True
            )
            return

        embed = self.bot.embed_builder.info(
            title="📌 Sticky Messages",
            description=f"{len(self._sticky_cache)} sticky message(s) configured",
        )

        for channel_id, (message_id, embed_type) in self._sticky_cache.items():
            channel = interaction.guild.get_channel(channel_id)
            channel_name = channel.mention if channel else f"Unknown ({channel_id})"
            embed.add_field(
                name=channel_name,
                value=f"Type: {embed_type}\nMessage ID: {message_id}",
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # Error handler
    @sticky_set.error
    @sticky_remove.error
    @sticky_list.error
    async def sticky_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "You need 'Manage Channels' permission to use this command.", ephemeral=True
            )


async def setup(bot: GayborhoodBot):
    await bot.add_cog(StickyMessagesCog(bot))
