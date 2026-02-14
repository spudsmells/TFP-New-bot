"""Confessions system — spill the tea anonymously"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from database.repositories.confessions import ConfessionRepository

if TYPE_CHECKING:
    from core.bot import GayborhoodBot

logger = logging.getLogger(__name__)


class ConfessionsCog(commands.Cog, name="ConfessionsCog"):
    """Anonymous confessions with staff review"""

    def __init__(self, bot: GayborhoodBot):
        self.bot = bot
        self.repo = ConfessionRepository(bot.db)

    @app_commands.command(name="confess", description="Submit an anonymous confession")
    @app_commands.describe(
        confession="Your confession (will be reviewed by staff before posting)",
    )
    async def confess(self, interaction: discord.Interaction, confession: str):
        """Submit an anonymous confession"""
        # Validate length
        if len(confession) < 10:
            await interaction.response.send_message(
                "Confession must be at least 10 characters long.", ephemeral=True
            )
            return

        if len(confession) > 1000:
            await interaction.response.send_message(
                "Confession must be no more than 1000 characters.", ephemeral=True
            )
            return

        # Check for slurs/profanity using content filter
        try:
            self.bot.content_filter.validate_reason(confession, min_length=10, max_length=1000)
        except Exception as e:
            await interaction.response.send_message(
                f"Confession validation failed: {e}\n\n"
                f"Please keep confessions appropriate and respectful.",
                ephemeral=True,
            )
            return

        try:
            # Save confession (pending review)
            confession_id = await self.repo.create(interaction.user.id, confession)

            # Send to review channel
            review_channel_id = self.bot.config.channels.get("confession_review")
            if review_channel_id:
                guild = self.bot.guild
                if guild:
                    review_channel = guild.get_channel(review_channel_id)
                    if review_channel and isinstance(review_channel, discord.TextChannel):
                        # Get confession data
                        confession_data = await self.repo.get_by_id(confession_id)
                        confession_num = confession_data["confession_num"]

                        # Create review embed
                        embed = self.bot.embed_builder.warning(
                            title=f"📨 Confession #{confession_num} — Pending Review",
                            description=confession,
                        )
                        embed.set_footer(text=f"Confession ID: {confession_id}")

                        # Send to review channel
                        review_msg = await review_channel.send(embed=embed)

                        # Add reaction buttons for approve/reject
                        await review_msg.add_reaction("✅")  # Approve
                        await review_msg.add_reaction("❌")  # Reject

            # Confirm to user
            await interaction.response.send_message(
                "✅ Your confession has been submitted for review!\n\n"
                "Staff will review it before posting. If approved, it will be posted anonymously.",
                ephemeral=True,
            )

            # Log to audit (but not the content, to preserve anonymity)
            await self.bot.audit_logger.log(
                "confession_submitted",
                actor_id=interaction.user.id,
                details=f"Confession ID: {confession_id}",
            )

        except Exception as e:
            logger.exception("Failed to submit confession")
            await interaction.response.send_message(
                f"Failed to submit confession: {e}", ephemeral=True
            )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Handle confession approval/rejection via reactions"""
        # Ignore bot reactions
        if payload.user_id == self.bot.user.id:
            return

        # Only handle reactions in confession review channel
        review_channel_id = self.bot.config.channels.get("confession_review")
        if not review_channel_id or payload.channel_id != review_channel_id:
            return

        # Check if user has manage_messages permission (staff)
        guild = self.bot.guild
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        if not member or not member.guild_permissions.manage_messages:
            return

        # Get the message to find confession ID
        channel = guild.get_channel(payload.channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return

        # Extract confession ID from embed footer
        if not message.embeds:
            return

        embed = message.embeds[0]
        if not embed.footer or not embed.footer.text:
            return

        # Parse "Confession ID: 123"
        try:
            confession_id = int(embed.footer.text.split(": ")[1])
        except (IndexError, ValueError):
            return

        # Get confession data
        confession_data = await self.repo.get_by_id(confession_id)
        if not confession_data:
            return

        # Check if already reviewed
        if confession_data["approved"] or confession_data["rejected"]:
            return

        # Handle approval
        if str(payload.emoji) == "✅":
            await self._approve_confession(confession_id, confession_data, member, message)

        # Handle rejection
        elif str(payload.emoji) == "❌":
            await self._reject_confession(confession_id, confession_data, member, message)

    async def _approve_confession(
        self, confession_id: int, confession_data: dict, reviewer: discord.Member, review_msg: discord.Message
    ) -> None:
        """Approve and post a confession"""
        # Get confessions channel
        confessions_channel_id = self.bot.config.channels.get("confessions")
        if not confessions_channel_id:
            logger.error("No confessions channel configured")
            return

        guild = self.bot.guild
        if not guild:
            return

        confessions_channel = guild.get_channel(confessions_channel_id)
        if not confessions_channel or not isinstance(confessions_channel, discord.TextChannel):
            logger.error("Confessions channel not found")
            return

        # Post confession anonymously
        confession_num = confession_data["confession_num"]
        content = confession_data["content"]

        embed = self.bot.embed_builder.neutral(
            title=f"💭 Anonymous Confession #{confession_num}",
            description=content,
        )

        try:
            confession_msg = await confessions_channel.send(embed=embed)

            # Update database
            await self.repo.approve(
                confession_id, reviewer.id, confession_msg.id, confessions_channel_id
            )

            # Update review message
            review_embed = review_msg.embeds[0]
            review_embed.title = f"✅ Confession #{confession_num} — Approved"
            review_embed.colour = discord.Colour.green()
            review_embed.add_field(
                name="Approved by",
                value=reviewer.mention,
                inline=True,
            )
            review_embed.add_field(
                name="Posted",
                value=confession_msg.jump_url,
                inline=False,
            )

            await review_msg.edit(embed=review_embed)
            await review_msg.clear_reactions()

            # DM user (anonymously)
            user = guild.get_member(confession_data["user_id"])
            if user:
                try:
                    dm_embed = self.bot.embed_builder.success(
                        title="✅ Confession Approved",
                        description=f"Your confession has been approved and posted as Confession #{confession_num}!",
                    )
                    await user.send(embed=dm_embed)
                except discord.Forbidden:
                    pass

            # Log to audit
            await self.bot.audit_logger.log(
                "confession_approved",
                actor_id=reviewer.id,
                details=f"Confession ID: {confession_id}, posted to {confessions_channel_id}",
            )

        except Exception:
            logger.exception("Failed to approve confession %d", confession_id)

    async def _reject_confession(
        self, confession_id: int, confession_data: dict, reviewer: discord.Member, review_msg: discord.Message
    ) -> None:
        """Reject a confession"""
        # Update database
        await self.repo.reject(confession_id, reviewer.id)

        # Update review message
        confession_num = confession_data["confession_num"]
        review_embed = review_msg.embeds[0]
        review_embed.title = f"❌ Confession #{confession_num} — Rejected"
        review_embed.colour = discord.Colour.red()
        review_embed.add_field(
            name="Rejected by",
            value=reviewer.mention,
            inline=True,
        )

        await review_msg.edit(embed=review_embed)
        await review_msg.clear_reactions()

        # DM user (anonymously)
        guild = self.bot.guild
        if guild:
            user = guild.get_member(confession_data["user_id"])
            if user:
                try:
                    dm_embed = self.bot.embed_builder.error(
                        title="❌ Confession Rejected",
                        description="Your confession was reviewed and rejected by staff.\n\n"
                        "Confessions must follow server rules and be appropriate.",
                    )
                    await user.send(embed=dm_embed)
                except discord.Forbidden:
                    pass

        # Log to audit
        await self.bot.audit_logger.log(
            "confession_rejected",
            actor_id=reviewer.id,
            details=f"Confession ID: {confession_id}",
        )

    @app_commands.command(name="confession-stats", description="Show confession statistics")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def confession_stats(self, interaction: discord.Interaction):
        """Show confession statistics (staff only)"""
        pending = await self.repo.get_pending()
        approved_count = await self.repo.get_approved_count()

        embed = self.bot.embed_builder.info(title="📊 Confession Statistics")
        embed.add_field(name="Pending Review", value=str(len(pending)), inline=True)
        embed.add_field(name="Total Approved", value=str(approved_count), inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @confession_stats.error
    async def confession_stats_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "You need 'Manage Messages' permission to view confession stats.",
                ephemeral=True,
            )


async def setup(bot: GayborhoodBot):
    await bot.add_cog(ConfessionsCog(bot))
