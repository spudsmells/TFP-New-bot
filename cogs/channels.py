"""Channel management commands — for when you need to sort out the channels"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from core.bot import GayborhoodBot

logger = logging.getLogger(__name__)


class ChannelManagementCog(commands.Cog, name="ChannelManagementCog"):
    """Channel management commands: /slowmode, /lock, /unlock, /purge"""

    def __init__(self, bot: GayborhoodBot):
        self.bot = bot

    @app_commands.command(name="slowmode", description="Set slowmode delay for a channel")
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.describe(
        seconds="Slowmode delay in seconds (0 to disable, max 21600 = 6 hours)",
        channel="Channel to set slowmode for (defaults to current channel)",
    )
    async def slowmode(
        self,
        interaction: discord.Interaction,
        seconds: int,
        channel: discord.TextChannel | None = None,
    ):
        """Set slowmode for a channel"""
        target_channel = channel or interaction.channel

        if not isinstance(target_channel, discord.TextChannel):
            await interaction.response.send_message(
                "Can only set slowmode for text channels.", ephemeral=True
            )
            return

        if seconds < 0 or seconds > 21600:
            await interaction.response.send_message(
                "Slowmode must be between 0 and 21600 seconds (6 hours).", ephemeral=True
            )
            return

        try:
            await target_channel.edit(
                slowmode_delay=seconds,
                reason=f"Slowmode set by {interaction.user.name}",
            )

            if seconds == 0:
                await interaction.response.send_message(
                    f"✅ Slowmode disabled in {target_channel.mention}",
                    ephemeral=True,
                )
            else:
                # Format seconds nicely
                if seconds < 60:
                    time_str = f"{seconds} second(s)"
                elif seconds < 3600:
                    mins = seconds // 60
                    secs = seconds % 60
                    time_str = f"{mins} minute(s)" + (f" {secs} second(s)" if secs else "")
                else:
                    hours = seconds // 3600
                    mins = (seconds % 3600) // 60
                    time_str = f"{hours} hour(s)" + (f" {mins} minute(s)" if mins else "")

                await interaction.response.send_message(
                    f"✅ Slowmode set to {time_str} in {target_channel.mention}",
                    ephemeral=True,
                )

            # Log to audit
            await self.bot.audit_logger.log(
                "channel_slowmode",
                actor_id=interaction.user.id,
                details=f"Channel {target_channel.id}: {seconds}s",
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                f"I don't have permissions to edit {target_channel.mention}.",
                ephemeral=True,
            )
        except discord.HTTPException as e:
            await interaction.response.send_message(
                f"Failed to set slowmode: {e}", ephemeral=True
            )

    @app_commands.command(name="lock", description="Lock a channel (prevent @everyone from sending messages)")
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.describe(
        channel="Channel to lock (defaults to current channel)",
        reason="Reason for locking the channel",
    )
    async def lock(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel | None = None,
        reason: str | None = None,
    ):
        """Lock a channel"""
        target_channel = channel or interaction.channel

        if not isinstance(target_channel, discord.TextChannel):
            await interaction.response.send_message(
                "Can only lock text channels.", ephemeral=True
            )
            return

        try:
            # Get @everyone role
            everyone_role = interaction.guild.default_role

            # Get current permissions
            overwrites = target_channel.overwrites
            everyone_overwrite = overwrites.get(everyone_role, discord.PermissionOverwrite())

            # Check if already locked
            if everyone_overwrite.send_messages is False:
                await interaction.response.send_message(
                    f"{target_channel.mention} is already locked.", ephemeral=True
                )
                return

            # Lock channel by denying send_messages
            everyone_overwrite.send_messages = False
            overwrites[everyone_role] = everyone_overwrite

            await target_channel.edit(
                overwrites=overwrites,
                reason=reason or f"Locked by {interaction.user.name}",
            )

            # Send lock notification to channel
            embed = self.bot.embed_builder.warning(
                title="🔒 Channel Locked",
                description="This channel has been locked by moderators.",
            )
            if reason:
                embed.add_field(name="Reason", value=reason, inline=False)

            await target_channel.send(embed=embed)

            # Respond to moderator
            await interaction.response.send_message(
                f"✅ Locked {target_channel.mention}",
                ephemeral=True,
            )

            # Log to audit
            await self.bot.audit_logger.log(
                "channel_locked",
                actor_id=interaction.user.id,
                details=f"Channel {target_channel.id}: {reason or 'No reason'}",
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                f"I don't have permissions to edit {target_channel.mention}.",
                ephemeral=True,
            )
        except discord.HTTPException as e:
            await interaction.response.send_message(
                f"Failed to lock channel: {e}", ephemeral=True
            )

    @app_commands.command(name="unlock", description="Unlock a channel (allow @everyone to send messages)")
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.describe(
        channel="Channel to unlock (defaults to current channel)",
        reason="Reason for unlocking the channel",
    )
    async def unlock(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel | None = None,
        reason: str | None = None,
    ):
        """Unlock a channel"""
        target_channel = channel or interaction.channel

        if not isinstance(target_channel, discord.TextChannel):
            await interaction.response.send_message(
                "Can only unlock text channels.", ephemeral=True
            )
            return

        try:
            # Get @everyone role
            everyone_role = interaction.guild.default_role

            # Get current permissions
            overwrites = target_channel.overwrites
            everyone_overwrite = overwrites.get(everyone_role, discord.PermissionOverwrite())

            # Check if not locked
            if everyone_overwrite.send_messages is not False:
                await interaction.response.send_message(
                    f"{target_channel.mention} isn't locked.", ephemeral=True
                )
                return

            # Unlock by removing send_messages override (reset to default/inherit)
            everyone_overwrite.send_messages = None
            if everyone_overwrite.is_empty():
                # If no other overrides, remove the overwrite entirely
                if everyone_role in overwrites:
                    del overwrites[everyone_role]
            else:
                overwrites[everyone_role] = everyone_overwrite

            await target_channel.edit(
                overwrites=overwrites,
                reason=reason or f"Unlocked by {interaction.user.name}",
            )

            # Send unlock notification to channel
            embed = self.bot.embed_builder.success(
                title="🔓 Channel Unlocked",
                description="This channel has been unlocked.",
            )
            if reason:
                embed.add_field(name="Reason", value=reason, inline=False)

            await target_channel.send(embed=embed)

            # Respond to moderator
            await interaction.response.send_message(
                f"✅ Unlocked {target_channel.mention}",
                ephemeral=True,
            )

            # Log to audit
            await self.bot.audit_logger.log(
                "channel_unlocked",
                actor_id=interaction.user.id,
                details=f"Channel {target_channel.id}: {reason or 'No reason'}",
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                f"I don't have permissions to edit {target_channel.mention}.",
                ephemeral=True,
            )
        except discord.HTTPException as e:
            await interaction.response.send_message(
                f"Failed to unlock channel: {e}", ephemeral=True
            )

    @app_commands.command(name="purge", description="Delete multiple messages in a channel")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(
        amount="Number of messages to delete (1-100)",
        user="Only delete messages from this user (optional)",
    )
    async def purge(
        self,
        interaction: discord.Interaction,
        amount: int,
        user: discord.Member | None = None,
    ):
        """Purge messages from a channel"""
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(
                "Can only purge messages in text channels.", ephemeral=True
            )
            return

        if amount < 1 or amount > 100:
            await interaction.response.send_message(
                "Amount must be between 1 and 100.", ephemeral=True
            )
            return

        # Defer response since this might take a bit
        await interaction.response.defer(ephemeral=True)

        try:
            if user:
                # Delete messages from specific user
                def check(m):
                    return m.author.id == user.id

                deleted = await interaction.channel.purge(limit=amount, check=check)
            else:
                # Delete all messages
                deleted = await interaction.channel.purge(limit=amount)

            # Respond
            response = f"✅ Deleted {len(deleted)} message(s)"
            if user:
                response += f" from **{user.name}**"

            await interaction.followup.send(response, ephemeral=True)

            # Log to audit
            await self.bot.audit_logger.log(
                "messages_purged",
                actor_id=interaction.user.id,
                target_id=user.id if user else None,
                details=f"Channel {interaction.channel.id}: {len(deleted)} messages",
            )

        except discord.Forbidden:
            await interaction.followup.send(
                "I don't have permissions to delete messages in this channel.",
                ephemeral=True,
            )
        except discord.HTTPException as e:
            await interaction.followup.send(
                f"Failed to purge messages: {e}", ephemeral=True
            )

    # Error handler
    @slowmode.error
    @lock.error
    @unlock.error
    @purge.error
    async def channel_management_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "You don't have permission to use this command.", ephemeral=True
            )


async def setup(bot: GayborhoodBot):
    await bot.add_cog(ChannelManagementCog(bot))
