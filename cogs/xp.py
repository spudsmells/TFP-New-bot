from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands, tasks

from core.constants import XPSource
from database.repositories.users import UserRepository
from database.repositories.xp import XPRepository
from services.card_renderer import RankCardData, LeaderboardEntry

if TYPE_CHECKING:
    from core.bot import GayborhoodBot

logger = logging.getLogger(__name__)


class XPCog(commands.Cog, name="XPCog"):
    """Release 1.5A: XP tracking, levels, leaderboard."""

    def __init__(self, bot: GayborhoodBot):
        self.bot = bot
        self._xp_cooldowns: dict[int, float] = {}  # user_id -> last_xp_timestamp
        self._user_repo = UserRepository(bot.db)
        self._xp_repo = XPRepository(bot.db)

    async def cog_load(self):
        self.vc_xp_loop.start()

    async def cog_unload(self):
        self.vc_xp_loop.cancel()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if message.guild.id != self.bot.config.guild_id:
            return

        import time
        user_id = message.author.id
        now = time.monotonic()
        cooldown = self.bot.config.xp.get("message_cooldown_seconds", 60)

        if user_id in self._xp_cooldowns:
            if now - self._xp_cooldowns[user_id] < cooldown:
                return

        self._xp_cooldowns[user_id] = now

        xp_min = self.bot.config.xp.get("message_min", 10)
        xp_max = self.bot.config.xp.get("message_max", 20)
        amount = random.randint(xp_min, xp_max)

        await self._award_xp(user_id, amount, XPSource.MESSAGE, f"msg:{message.channel.id}")
        await self._user_repo.increment_messages(user_id)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if not payload.guild_id or payload.guild_id != self.bot.config.guild_id:
            return
        if payload.member and payload.member.bot:
            return

        # Award XP to the message author, not the reactor
        channel = self.bot.get_channel(payload.channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return

        if message.author.bot or message.author.id == payload.user_id:
            return

        # Check max reactions per message
        detail_key = f"reaction:{payload.message_id}"
        max_per_msg = self.bot.config.xp.get("reaction_max_per_message", 20)
        count = await self._xp_repo.count_reactions_on_message(detail_key)
        if count >= max_per_msg:
            return

        reaction_xp = self.bot.config.xp.get("reaction_xp", 2)
        await self._award_xp(message.author.id, reaction_xp, XPSource.REACTION, detail_key)

    @tasks.loop(seconds=60)
    async def vc_xp_loop(self):
        """Award XP to non-muted users in voice channels."""
        guild = self.bot.guild
        if not guild:
            return

        xp_per_min = self.bot.config.xp.get("voice_per_minute", 5)

        for vc in guild.voice_channels:
            for member in vc.members:
                if member.bot:
                    continue
                if member.voice and (member.voice.self_mute or member.voice.self_deaf):
                    continue

                await self._award_xp(member.id, xp_per_min, XPSource.VOICE, f"vc:{vc.id}")
                await self._user_repo.add_vc_minutes(member.id, 1)

    @vc_xp_loop.before_loop
    async def before_vc_xp(self):
        await self.bot.wait_until_ready()

    async def _award_xp(self, user_id: int, amount: int, source: str, details: str | None = None):
        """Award XP, detect level-ups and milestones."""
        # Ensure user exists
        await self._user_repo.upsert(user_id)
        await self._xp_repo.add(user_id, amount, source, details)

        user = await self._user_repo.get(user_id)
        if not user:
            return

        old_level = user.level
        new_total = user.total_xp + amount
        new_level = self.bot.xp_calculator.calculate_level(new_total)

        await self._user_repo.add_xp(user_id, amount, new_level)

        if new_level > old_level:
            self.bot.dispatch("level_up", user_id, old_level, new_level)

            milestones = self.bot.xp_calculator.check_milestones(old_level, new_level)
            for milestone in milestones:
                self.bot.dispatch("milestone_reached", user_id, milestone)

    # ── Slash Commands ────────────────────────

    @app_commands.command(name="rank", description="Check your or someone's rank")
    @app_commands.describe(member="The member to check (defaults to you)")
    async def rank(self, interaction: discord.Interaction, member: discord.Member | None = None):
        target = member or interaction.user
        user = await self._user_repo.get(target.id)

        if not user:
            await interaction.response.send_message("No XP data found.", ephemeral=True)
            return

        await interaction.response.defer()

        rank_num = await self._user_repo.get_rank(target.id)
        current, needed = self.bot.xp_calculator.xp_progress_in_level(user.total_xp)
        avatar = await self.bot.card_renderer.fetch_avatar(target)

        data = RankCardData(
            username=target.display_name,
            discriminator=f"#{target.discriminator}" if hasattr(target, "discriminator") else "",
            avatar=avatar,
            level=user.level,
            rank=rank_num or 0,
            current_xp=current,
            needed_xp=needed,
            total_xp=user.total_xp,
            messages=user.messages_sent,
            vc_minutes=user.vc_minutes,
        )
        file = await self.bot.card_renderer.rank_card(data)
        await interaction.followup.send(file=file)

    @app_commands.command(name="leaderboard", description="View the XP leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        top = await self._user_repo.get_leaderboard(10)
        if not top:
            await interaction.response.send_message("No leaderboard data yet.", ephemeral=True)
            return

        await interaction.response.defer()

        entries = []
        for i, u in enumerate(top):
            member = self.bot.guild.get_member(u.user_id) if self.bot.guild else None
            name = member.display_name if member else f"User {u.user_id}"
            avatar = await self.bot.card_renderer.fetch_avatar(member) if member else None
            current, needed = self.bot.xp_calculator.xp_progress_in_level(u.total_xp)
            entries.append(LeaderboardEntry(
                rank=i + 1,
                username=name,
                avatar=avatar,
                level=u.level,
                total_xp=u.total_xp,
                current_xp=current,
                needed_xp=needed,
            ))

        # Check if requester is outside top 10
        requester_entry = None
        requester_id = interaction.user.id
        if not any(u.user_id == requester_id for u in top):
            req_user = await self._user_repo.get(requester_id)
            if req_user and req_user.total_xp > 0:
                rank_num = await self._user_repo.get_rank(requester_id)
                current, needed = self.bot.xp_calculator.xp_progress_in_level(req_user.total_xp)
                requester_entry = LeaderboardEntry(
                    rank=rank_num or 0,
                    username=interaction.user.display_name,
                    avatar=await self.bot.card_renderer.fetch_avatar(interaction.user),
                    level=req_user.level,
                    total_xp=req_user.total_xp,
                    current_xp=current,
                    needed_xp=needed,
                )

        file = await self.bot.card_renderer.leaderboard_card(entries, requester_entry)
        await interaction.followup.send(file=file)

    @app_commands.command(name="xp-give", description="Give XP to a member (Staff)")
    @app_commands.describe(member="Target member", amount="XP amount", reason="Reason")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def xp_give(self, interaction: discord.Interaction, member: discord.Member,
                      amount: app_commands.Range[int, 1, 10000], reason: str = "Staff bonus"):
        await self._award_xp(member.id, amount, XPSource.BONUS, reason)
        await self.bot.audit_logger.log(
            "xp_give", actor_id=interaction.user.id, target_id=member.id,
            details={"amount": amount, "reason": reason},
        )
        await interaction.response.send_message(
            f"Gave **{amount} XP** to {member.mention}. Reason: {reason}",
            ephemeral=True,
        )

    @app_commands.command(name="xp-take", description="Remove XP from a member (Staff)")
    @app_commands.describe(member="Target member", amount="XP amount", reason="Reason")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def xp_take(self, interaction: discord.Interaction, member: discord.Member,
                      amount: app_commands.Range[int, 1, 10000], reason: str = "Staff penalty"):
        await self._xp_repo.add(member.id, -amount, XPSource.PENALTY, reason)
        user = await self._user_repo.get(member.id)
        if user:
            new_total = max(0, user.total_xp - amount)
            new_level = self.bot.xp_calculator.calculate_level(new_total)
            await self._user_repo.set_xp(member.id, new_total, new_level)

        await self.bot.audit_logger.log(
            "xp_take", actor_id=interaction.user.id, target_id=member.id,
            details={"amount": amount, "reason": reason},
        )
        await interaction.response.send_message(
            f"Removed **{amount} XP** from {member.mention}. Reason: {reason}",
            ephemeral=True,
        )

    @app_commands.command(name="xp-set", description="Set a member's total XP (Staff)")
    @app_commands.describe(member="Target member", total_xp="New total XP")
    @app_commands.checks.has_permissions(administrator=True)
    async def xp_set(self, interaction: discord.Interaction, member: discord.Member,
                     total_xp: app_commands.Range[int, 0, 1000000]):
        new_level = self.bot.xp_calculator.calculate_level(total_xp)
        await self._user_repo.upsert(member.id)
        await self._user_repo.set_xp(member.id, total_xp, new_level)

        await self.bot.audit_logger.log(
            "xp_set", actor_id=interaction.user.id, target_id=member.id,
            details={"total_xp": total_xp, "level": new_level},
        )
        await interaction.response.send_message(
            f"Set {member.mention}'s XP to **{total_xp:,}** (Level {new_level}).",
            ephemeral=True,
        )

    @app_commands.command(name="xp-reset", description="Reset a member's XP (Staff)")
    @app_commands.describe(member="Target member")
    @app_commands.checks.has_permissions(administrator=True)
    async def xp_reset(self, interaction: discord.Interaction, member: discord.Member):
        await self._user_repo.set_xp(member.id, 0, 0)
        await self.bot.audit_logger.log(
            "xp_reset", actor_id=interaction.user.id, target_id=member.id,
        )
        await interaction.response.send_message(
            f"Reset {member.mention}'s XP to 0.", ephemeral=True,
        )

    @app_commands.command(name="xp-import", description="Bulk import XP levels from attachment (Staff)")
    @app_commands.describe(file="CSV or JSON file with user_id and level columns")
    @app_commands.checks.has_permissions(administrator=True)
    async def xp_import(self, interaction: discord.Interaction, file: discord.Attachment):
        await interaction.response.defer(ephemeral=True)

        content = (await file.read()).decode("utf-8")
        entries = []

        if file.filename.endswith(".json"):
            import json
            data = json.loads(content)
            for item in data:
                uid = int(item["user_id"])
                level = int(item["level"])
                xp = self.bot.xp_calculator.xp_for_import_level(level)
                entries.append((uid, xp, XPSource.IMPORT, f"Imported level {level}"))
        else:
            # CSV: user_id,level
            import csv
            import io
            reader = csv.DictReader(io.StringIO(content))
            for row in reader:
                uid = int(row["user_id"])
                level = int(row["level"])
                xp = self.bot.xp_calculator.xp_for_import_level(level)
                entries.append((uid, xp, XPSource.IMPORT, f"Imported level {level}"))

        # Process entries
        count = 0
        for uid, xp, source, details in entries:
            await self._user_repo.upsert(uid)
            await self._xp_repo.add(uid, xp, source, details)
            new_level = self.bot.xp_calculator.calculate_level(xp)
            await self._user_repo.set_xp(uid, xp, new_level)
            count += 1

        await self.bot.audit_logger.log(
            "xp_import", actor_id=interaction.user.id,
            details={"count": count, "file": file.filename},
        )
        await interaction.followup.send(f"Imported XP for **{count}** users.", ephemeral=True)


async def setup(bot: GayborhoodBot):
    await bot.add_cog(XPCog(bot))
