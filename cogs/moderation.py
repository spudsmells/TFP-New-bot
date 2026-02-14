"""Moderation commands — for when people need a proper bollocking"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from core.bot import GayborhoodBot

logger = logging.getLogger(__name__)


class ModerationCog(commands.Cog, name="ModerationCog"):
    """Moderation commands: /kick, /ban, /mute, /warn"""

    def __init__(self, bot: GayborhoodBot):
        self.bot = bot

    @app_commands.command(name="kick", description="Kick a member from the server")
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.describe(
        member="The member to kick",
        reason="Reason for kicking (will be DMed to the member)",
    )
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str | None = None,
    ):
        """Kick a member from the server"""
        if member.id == interaction.user.id:
            await interaction.response.send_message(
                "You can't kick yourself ya muppet.", ephemeral=True
            )
            return

        if member.id == self.bot.user.id:
            await interaction.response.send_message(
                "I'm not kicking myself, fuck off.", ephemeral=True
            )
            return

        # Check role hierarchy
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                "You can't kick someone with equal or higher roles than you.", ephemeral=True
            )
            return

        if member.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                "I can't kick someone with equal or higher roles than me.", ephemeral=True
            )
            return

        # Try to DM the member first
        dm_sent = False
        try:
            embed = self.bot.embed_builder.warning(
                title="You've been kicked",
                description=f"You've been kicked from **{interaction.guild.name}**",
            )
            if reason:
                embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(
                name="What now?",
                value="You can rejoin using an invite link if you wish.",
                inline=False,
            )
            await member.send(embed=embed)
            dm_sent = True
        except discord.Forbidden:
            logger.warning("Couldn't DM member %s before kick — DMs closed", member.id)
        except discord.HTTPException as e:
            logger.error("Failed to DM member %s before kick: %s", member.id, e)

        # Kick the member
        try:
            await member.kick(reason=reason or f"Kicked by {interaction.user.name}")

            # Log to audit
            await self.bot.audit_logger.log_moderation_action(
                "kick",
                interaction.user.id,
                member.id,
                reason,
            )

            # Respond to moderator
            response = f"✅ Kicked **{member.name}** (ID: {member.id})"
            if not dm_sent:
                response += "\n⚠️ Couldn't DM them — they've got DMs closed"

            await interaction.response.send_message(response, ephemeral=True)

        except discord.Forbidden:
            await interaction.response.send_message(
                "I don't have permissions to kick this member.", ephemeral=True
            )
        except discord.HTTPException as e:
            await interaction.response.send_message(
                f"Failed to kick member: {e}", ephemeral=True
            )

    @app_commands.command(name="ban", description="Ban a member from the server")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.describe(
        member="The member to ban",
        reason="Reason for banning (will be DMed to the member)",
        delete_days="Number of days of messages to delete (0-7)",
    )
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str | None = None,
        delete_days: int = 0,
    ):
        """Ban a member from the server"""
        if member.id == interaction.user.id:
            await interaction.response.send_message(
                "You can't ban yourself ya plonker.", ephemeral=True
            )
            return

        if member.id == self.bot.user.id:
            await interaction.response.send_message(
                "Nice try. I'm not banning myself.", ephemeral=True
            )
            return

        # Check role hierarchy
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                "You can't ban someone with equal or higher roles than you.", ephemeral=True
            )
            return

        if member.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                "I can't ban someone with equal or higher roles than me.", ephemeral=True
            )
            return

        # Validate delete_days
        if delete_days < 0 or delete_days > 7:
            await interaction.response.send_message(
                "delete_days must be between 0 and 7.", ephemeral=True
            )
            return

        # Try to DM the member first
        dm_sent = False
        try:
            embed = self.bot.embed_builder.error(
                title="You've been banned",
                description=f"You've been banned from **{interaction.guild.name}**",
            )
            if reason:
                embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(
                name="Appeals",
                value="If you believe this was a mistake, you can appeal via ModMail.",
                inline=False,
            )
            await member.send(embed=embed)
            dm_sent = True
        except discord.Forbidden:
            logger.warning("Couldn't DM member %s before ban — DMs closed", member.id)
        except discord.HTTPException as e:
            logger.error("Failed to DM member %s before ban: %s", member.id, e)

        # Ban the member
        try:
            await member.ban(
                reason=reason or f"Banned by {interaction.user.name}",
                delete_message_days=delete_days,
            )

            # Log to audit
            await self.bot.audit_logger.log_moderation_action(
                "ban",
                interaction.user.id,
                member.id,
                reason,
            )

            # Respond to moderator
            response = f"✅ Banned **{member.name}** (ID: {member.id})"
            if delete_days > 0:
                response += f"\n🗑️ Deleted {delete_days} day(s) of messages"
            if not dm_sent:
                response += "\n⚠️ Couldn't DM them — they've got DMs closed"

            await interaction.response.send_message(response, ephemeral=True)

        except discord.Forbidden:
            await interaction.response.send_message(
                "I don't have permissions to ban this member.", ephemeral=True
            )
        except discord.HTTPException as e:
            await interaction.response.send_message(
                f"Failed to ban member: {e}", ephemeral=True
            )

    @app_commands.command(name="unban", description="Unban a user from the server")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.describe(
        user_id="The user ID to unban",
        reason="Reason for unbanning",
    )
    async def unban(
        self,
        interaction: discord.Interaction,
        user_id: str,
        reason: str | None = None,
    ):
        """Unban a user from the server"""
        try:
            user_id_int = int(user_id)
        except ValueError:
            await interaction.response.send_message(
                "Invalid user ID. Must be a number.", ephemeral=True
            )
            return

        try:
            user = await self.bot.fetch_user(user_id_int)
            await interaction.guild.unban(
                user,
                reason=reason or f"Unbanned by {interaction.user.name}",
            )

            # Log to audit
            await self.bot.audit_logger.log_moderation_action(
                "unban",
                interaction.user.id,
                user_id_int,
                reason,
            )

            await interaction.response.send_message(
                f"✅ Unbanned **{user.name}** (ID: {user_id_int})",
                ephemeral=True,
            )

        except discord.NotFound:
            await interaction.response.send_message(
                "User not found or not banned.", ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "I don't have permissions to unban users.", ephemeral=True
            )
        except discord.HTTPException as e:
            await interaction.response.send_message(
                f"Failed to unban user: {e}", ephemeral=True
            )

    @app_commands.command(name="mute", description="Timeout a member (temporarily mute)")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(
        member="The member to timeout",
        duration="Duration in minutes (max 40320 = 28 days)",
        reason="Reason for the timeout",
    )
    async def mute(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        duration: int,
        reason: str | None = None,
    ):
        """Timeout (mute) a member for a specified duration"""
        if member.id == interaction.user.id:
            await interaction.response.send_message(
                "You can't mute yourself.", ephemeral=True
            )
            return

        if member.id == self.bot.user.id:
            await interaction.response.send_message(
                "You can't mute me, I'm the bot.", ephemeral=True
            )
            return

        # Check role hierarchy
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                "You can't mute someone with equal or higher roles than you.", ephemeral=True
            )
            return

        if member.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                "I can't mute someone with equal or higher roles than me.", ephemeral=True
            )
            return

        # Validate duration (max 28 days = 40320 minutes)
        if duration < 1 or duration > 40320:
            await interaction.response.send_message(
                "Duration must be between 1 and 40320 minutes (28 days).", ephemeral=True
            )
            return

        # Calculate timeout until
        until = datetime.utcnow() + timedelta(minutes=duration)

        # Try to DM the member
        dm_sent = False
        try:
            embed = self.bot.embed_builder.warning(
                title="You've been timed out",
                description=f"You've been timed out in **{interaction.guild.name}**",
            )
            if reason:
                embed.add_field(name="Reason", value=reason, inline=False)

            # Format duration nicely
            if duration < 60:
                duration_str = f"{duration} minute(s)"
            elif duration < 1440:
                hours = duration // 60
                mins = duration % 60
                duration_str = f"{hours} hour(s)" + (f" {mins} min(s)" if mins else "")
            else:
                days = duration // 1440
                hours = (duration % 1440) // 60
                duration_str = f"{days} day(s)" + (f" {hours} hour(s)" if hours else "")

            embed.add_field(name="Duration", value=duration_str, inline=False)
            await member.send(embed=embed)
            dm_sent = True
        except Exception:
            logger.warning("Couldn't DM member %s before timeout", member.id)

        # Apply timeout
        try:
            await member.timeout(until, reason=reason or f"Timed out by {interaction.user.name}")

            # Log to audit
            await self.bot.audit_logger.log_moderation_action(
                "timeout",
                interaction.user.id,
                member.id,
                f"{duration}m: {reason}" if reason else f"{duration}m",
            )

            # Respond to moderator
            response = f"✅ Timed out **{member.name}** for {duration} minute(s)"
            if not dm_sent:
                response += "\n⚠️ Couldn't DM them"

            await interaction.response.send_message(response, ephemeral=True)

        except discord.Forbidden:
            await interaction.response.send_message(
                "I don't have permissions to timeout this member.", ephemeral=True
            )
        except discord.HTTPException as e:
            await interaction.response.send_message(
                f"Failed to timeout member: {e}", ephemeral=True
            )

    @app_commands.command(name="unmute", description="Remove timeout from a member")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(
        member="The member to unmute",
        reason="Reason for removing timeout",
    )
    async def unmute(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str | None = None,
    ):
        """Remove timeout from a member"""
        if not member.is_timed_out():
            await interaction.response.send_message(
                f"**{member.name}** isn't timed out.", ephemeral=True
            )
            return

        try:
            await member.timeout(None, reason=reason or f"Unmuted by {interaction.user.name}")

            # Log to audit
            await self.bot.audit_logger.log_moderation_action(
                "untimeout",
                interaction.user.id,
                member.id,
                reason,
            )

            await interaction.response.send_message(
                f"✅ Removed timeout from **{member.name}**",
                ephemeral=True,
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "I don't have permissions to remove timeout from this member.", ephemeral=True
            )
        except discord.HTTPException as e:
            await interaction.response.send_message(
                f"Failed to remove timeout: {e}", ephemeral=True
            )

    @app_commands.command(name="warn", description="Warn a member (sends DM, logs to audit)")
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.describe(
        member="The member to warn",
        reason="Warning message",
    )
    async def warn(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str,
    ):
        """Warn a member (DM + audit log)"""
        if member.id == interaction.user.id:
            await interaction.response.send_message(
                "You can't warn yourself.", ephemeral=True
            )
            return

        if member.bot:
            await interaction.response.send_message(
                "You can't warn bots.", ephemeral=True
            )
            return

        # Try to DM the member
        dm_sent = False
        try:
            embed = self.bot.embed_builder.warning(
                title="⚠️ Warning",
                description=f"You've received a warning in **{interaction.guild.name}**",
            )
            embed.add_field(name="Warning", value=reason, inline=False)
            embed.add_field(
                name="Note",
                value="Please review the server rules. Continued violations may result in further action.",
                inline=False,
            )
            await member.send(embed=embed)
            dm_sent = True
        except discord.Forbidden:
            logger.warning("Couldn't DM member %s for warning — DMs closed", member.id)
        except discord.HTTPException as e:
            logger.error("Failed to DM member %s for warning: %s", member.id, e)

        # Log to audit
        await self.bot.audit_logger.log_moderation_action(
            "warn",
            interaction.user.id,
            member.id,
            reason,
        )

        # Respond to moderator
        response = f"✅ Warned **{member.name}**"
        if not dm_sent:
            response += "\n⚠️ Couldn't DM them — they've got DMs closed"
        else:
            response += "\n📨 Warning sent via DM"

        await interaction.response.send_message(response, ephemeral=True)

    # Error handlers for permission checks
    @kick.error
    @ban.error
    @unban.error
    @mute.error
    @unmute.error
    @warn.error
    async def moderation_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "You don't have permission to use this command.", ephemeral=True
            )


async def setup(bot: GayborhoodBot):
    await bot.add_cog(ModerationCog(bot))
