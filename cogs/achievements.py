from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands, tasks

from core.constants import AchievementTrigger
from database.repositories.achievements import AchievementRepository
from database.repositories.users import UserRepository
from services.card_renderer import AchievementCardData

if TYPE_CHECKING:
    from core.bot import GayborhoodBot

logger = logging.getLogger(__name__)


class AchievementsCog(commands.Cog, name="AchievementsCog"):
    """Achievement system: automatic triggers, staff management, image cards."""

    def __init__(self, bot: GayborhoodBot):
        self.bot = bot
        self._ach_repo = AchievementRepository(bot.db)
        self._user_repo = UserRepository(bot.db)

    async def cog_load(self):
        count = await self._ach_repo.seed_defaults()
        if count:
            logger.info("Seeded %d default achievements", count)
        self.check_achievements_loop.start()

    async def cog_unload(self):
        self.check_achievements_loop.cancel()

    # ── Achievement Checking ─────────────────────

    async def check_user_achievements(self, user_id: int) -> list[int]:
        """Check all trigger-based achievements for a user. Returns newly unlocked IDs."""
        user = await self._user_repo.get(user_id)
        if not user:
            return []

        already = await self._ach_repo.get_user_achievement_ids(user_id)
        unlocked = []

        # Build stat map for this user
        stats = {
            AchievementTrigger.MESSAGES_SENT: user.messages_sent,
            AchievementTrigger.LEVEL_REACHED: user.level,
            AchievementTrigger.VC_MINUTES: user.vc_minutes,
            AchievementTrigger.AGE_VERIFIED: 1 if user.age_verified else 0,
        }

        # Check each active achievement
        active = await self._ach_repo.get_active()
        for ach in active:
            if ach.id in already:
                continue
            trigger_val = stats.get(ach.trigger_type, 0)
            if trigger_val >= ach.trigger_value:
                success = await self._ach_repo.unlock(user_id, ach.id)
                if success:
                    unlocked.append(ach.id)
                    # Award XP bonus
                    if ach.xp_reward > 0:
                        from database.repositories.xp import XPRepository
                        xp_repo = XPRepository(self.bot.db)
                        await xp_repo.add(user_id, ach.xp_reward, "achievement", ach.key)
                        new_total = user.total_xp + ach.xp_reward
                        new_level = self.bot.xp_calculator.calculate_level(new_total)
                        await self._user_repo.add_xp(user_id, ach.xp_reward, new_level)

        return unlocked

    async def _notify_unlock(self, user_id: int, achievement_id: int) -> None:
        """Send achievement card DM + post in channel."""
        ach = await self._ach_repo.get(achievement_id)
        if not ach:
            return

        discord_user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
        if not discord_user:
            return

        avatar = await self.bot.card_renderer.fetch_avatar(discord_user)
        data = AchievementCardData(
            username=discord_user.display_name,
            avatar=avatar,
            achievement_name=ach.name,
            achievement_desc=ach.description,
            rarity=ach.rarity,
            icon_name=ach.icon,
        )
        file = await self.bot.card_renderer.achievement_card(data)
        await self.bot.dm_service.send(discord_user, file=file)
        await self._ach_repo.mark_notified(user_id, achievement_id)

        # Post in staff alerts or a dedicated channel
        channel_id = self.bot.config.channels.get("bot_logs")
        if channel_id:
            channel = self.bot.get_channel(channel_id)
            if channel and isinstance(channel, discord.TextChannel):
                file2 = await self.bot.card_renderer.achievement_card(data)
                await channel.send(
                    f"\U0001f3c6 {discord_user.mention} unlocked **{ach.name}**!",
                    file=file2,
                )

    # ── Listeners ─────────────────────────────────

    @commands.Cog.listener()
    async def on_level_up(self, user_id: int, old_level: int, new_level: int):
        """Check achievements on level-up."""
        unlocked = await self.check_user_achievements(user_id)
        for ach_id in unlocked:
            await self._notify_unlock(user_id, ach_id)

    @commands.Cog.listener()
    async def on_milestone_reached(self, user_id: int, level: int):
        """Also check on milestone."""
        unlocked = await self.check_user_achievements(user_id)
        for ach_id in unlocked:
            await self._notify_unlock(user_id, ach_id)

    @tasks.loop(minutes=5)
    async def check_achievements_loop(self):
        """Periodic sweep for achievements that might have been missed."""
        # Only check users who have been active recently (have XP)
        guild = self.bot.guild
        if not guild:
            return

        # Check top 50 active users by XP
        top = await self._user_repo.get_leaderboard(50)
        for u in top:
            unlocked = await self.check_user_achievements(u.user_id)
            for ach_id in unlocked:
                await self._notify_unlock(u.user_id, ach_id)

    @check_achievements_loop.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    # ── User Commands ─────────────────────────────

    @app_commands.command(name="achievements", description="View your or someone's achievements")
    @app_commands.describe(member="The member to view (defaults to you)")
    async def achievements(self, interaction: discord.Interaction, member: discord.Member | None = None):
        target = member or interaction.user
        pairs = await self._ach_repo.get_user_achievements(target.id)

        if not pairs:
            await interaction.response.send_message(
                f"{target.display_name} hasn't unlocked any achievements yet.",
                ephemeral=True,
            )
            return

        # Build embed with achievement list
        embed = self.bot.embed_builder.info(
            title=f"\U0001f3c6 {target.display_name}'s Achievements ({len(pairs)})",
        )
        embed.set_thumbnail(url=target.display_avatar.url)

        rarity_icons = {"common": "\u2b50", "rare": "\U0001f48e", "epic": "\U0001f31f", "legendary": "\U0001f451"}
        lines = []
        for ua, ach in pairs[:25]:  # Discord field limit
            icon = rarity_icons.get(ach.rarity, "\u2b50")
            lines.append(f"{icon} **{ach.name}** — {ach.description}")

        embed.description = "\n".join(lines)

        if len(pairs) > 25:
            embed.set_footer(text=f"Showing 25 of {len(pairs)} achievements")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="achievement-list", description="Browse all available achievements")
    async def achievement_list(self, interaction: discord.Interaction):
        all_achs = await self._ach_repo.get_all()
        if not all_achs:
            await interaction.response.send_message("No achievements configured.", ephemeral=True)
            return

        # Get user's unlocked for checkmarks
        user_ids = await self._ach_repo.get_user_achievement_ids(interaction.user.id)

        rarity_icons = {"common": "\u2b50", "rare": "\U0001f48e", "epic": "\U0001f31f", "legendary": "\U0001f451"}
        lines = []
        for ach in all_achs[:25]:
            icon = rarity_icons.get(ach.rarity, "\u2b50")
            check = "\u2705" if ach.id in user_ids else "\u2b1c"
            lines.append(f"{check} {icon} **{ach.name}** — {ach.description}")

        embed = self.bot.embed_builder.info(
            title="\U0001f3c6 All Achievements",
            description="\n".join(lines),
        )
        if len(all_achs) > 25:
            embed.set_footer(text=f"Showing 25 of {len(all_achs)}")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── Staff Commands ────────────────────────────

    @app_commands.command(name="achievement-grant", description="Grant an achievement to a member (Staff)")
    @app_commands.describe(member="Target member", key="Achievement key")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def achievement_grant(self, interaction: discord.Interaction,
                                member: discord.Member, key: str):
        ach = await self._ach_repo.get_by_key(key)
        if not ach:
            await interaction.response.send_message(f"Achievement `{key}` not found.", ephemeral=True)
            return

        success = await self._ach_repo.unlock(member.id, ach.id)
        if not success:
            await interaction.response.send_message(
                f"{member.display_name} already has **{ach.name}**.", ephemeral=True,
            )
            return

        await self._notify_unlock(member.id, ach.id)
        await self.bot.audit_logger.log(
            "achievement_grant", actor_id=interaction.user.id, target_id=member.id,
            details={"achievement": key},
        )
        await interaction.response.send_message(
            f"Granted **{ach.name}** to {member.mention}.", ephemeral=True,
        )

    @app_commands.command(name="achievement-revoke", description="Revoke an achievement (Staff)")
    @app_commands.describe(member="Target member", key="Achievement key")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def achievement_revoke(self, interaction: discord.Interaction,
                                 member: discord.Member, key: str):
        ach = await self._ach_repo.get_by_key(key)
        if not ach:
            await interaction.response.send_message(f"Achievement `{key}` not found.", ephemeral=True)
            return

        success = await self._ach_repo.revoke(member.id, ach.id)
        if not success:
            await interaction.response.send_message(
                f"{member.display_name} doesn't have **{ach.name}**.", ephemeral=True,
            )
            return

        await self.bot.audit_logger.log(
            "achievement_revoke", actor_id=interaction.user.id, target_id=member.id,
            details={"achievement": key},
        )
        await interaction.response.send_message(
            f"Revoked **{ach.name}** from {member.mention}.", ephemeral=True,
        )

    @app_commands.command(name="achievement-create", description="Create a new achievement (Staff)")
    @app_commands.describe(
        key="Unique key (e.g. chatterbox_500)", name="Display name",
        description="What the user must do", trigger_type="Trigger type",
        trigger_value="Threshold value", rarity="Rarity tier",
        xp_reward="XP bonus on unlock",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def achievement_create(
        self, interaction: discord.Interaction, key: str, name: str,
        description: str, trigger_type: str, trigger_value: int,
        rarity: str = "common", xp_reward: int = 0,
    ):
        existing = await self._ach_repo.get_by_key(key)
        if existing:
            await interaction.response.send_message(f"Key `{key}` already exists.", ephemeral=True)
            return

        await self._ach_repo.create(
            key=key, name=name, description=description,
            trigger_type=trigger_type, trigger_value=trigger_value,
            rarity=rarity, xp_reward=xp_reward,
        )
        await self.bot.audit_logger.log(
            "achievement_create", actor_id=interaction.user.id,
            details={"key": key, "name": name},
        )
        await interaction.response.send_message(
            f"Created achievement **{name}** (`{key}`).", ephemeral=True,
        )

    @app_commands.command(name="achievement-delete", description="Delete an achievement (Admin)")
    @app_commands.describe(key="Achievement key to delete")
    @app_commands.checks.has_permissions(administrator=True)
    async def achievement_delete(self, interaction: discord.Interaction, key: str):
        ach = await self._ach_repo.get_by_key(key)
        if not ach:
            await interaction.response.send_message(f"Achievement `{key}` not found.", ephemeral=True)
            return

        await self._ach_repo.delete(ach.id)
        await self.bot.audit_logger.log(
            "achievement_delete", actor_id=interaction.user.id,
            details={"key": key, "name": ach.name},
        )
        await interaction.response.send_message(
            f"Deleted achievement **{ach.name}** (`{key}`).", ephemeral=True,
        )


async def setup(bot: GayborhoodBot):
    await bot.add_cog(AchievementsCog(bot))
