from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands, tasks

from database.repositories.monthly_stats import MonthlyStatsRepository
from database.repositories.users import UserRepository
from services.card_renderer import MonthlyStatEntry

if TYPE_CHECKING:
    from core.bot import GayborhoodBot

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
STOP_WORDS: set[str] = set()


def _load_stop_words() -> set[str]:
    path = DATA_DIR / "stop_words.txt"
    if path.exists():
        return {w.strip().lower() for w in path.read_text().splitlines() if w.strip() and not w.startswith("#")}
    return set()


def _extract_words(content: str, min_length: int = 3) -> dict[str, int]:
    """Extract meaningful words from message content."""
    words: dict[str, int] = defaultdict(int)
    # Remove mentions, URLs, emotes
    cleaned = re.sub(r"<[@#!&]?\d+>", "", content)
    cleaned = re.sub(r"https?://\S+", "", cleaned)
    cleaned = re.sub(r"<a?:\w+:\d+>", "", cleaned)
    for word in re.findall(r"[a-zA-Z]+", cleaned.lower()):
        if len(word) >= min_length and word not in STOP_WORDS:
            words[word] += 1
    return dict(words)


class MonthlyStatsCog(commands.Cog, name="MonthlyStatsCog"):
    """Monthly analytics: message tracking, reaction stats, automated reports."""

    def __init__(self, bot: GayborhoodBot):
        self.bot = bot
        self._stats_repo = MonthlyStatsRepository(bot.db)
        self._user_repo = UserRepository(bot.db)

        # In-memory batch accumulators (flushed every 60s)
        self._msg_batch: dict[tuple[str, int], dict] = {}  # (date, user_id) -> stats
        self._channel_batch: dict[tuple[str, int, int], int] = {}  # (date, channel_id, user_id) -> count
        self._word_batch: dict[tuple[str, str], int] = {}  # (date, word) -> count
        self._mention_batch: dict[tuple[str, int], int] = {}  # (date, mentioned_id) -> count

    async def cog_load(self):
        global STOP_WORDS
        STOP_WORDS = _load_stop_words()
        logger.info("Loaded %d stop words", len(STOP_WORDS))
        self.flush_batch_loop.start()
        self.monthly_report_check.start()

    async def cog_unload(self):
        self.flush_batch_loop.cancel()
        self.monthly_report_check.cancel()
        # Final flush
        await self._flush_batches()

    def _today(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _this_month(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m")

    def _is_tracked_channel(self, channel_id: int) -> bool:
        """Check if channel should be tracked."""
        config = self.bot.config.get("monthly_stats", {})
        excluded = config.get("excluded_channels", [])
        if channel_id in excluded:
            return False
        tracking = config.get("tracking_channels", [])
        if tracking:
            return channel_id in tracking
        return True

    # ── Listeners ─────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if message.guild.id != self.bot.config.guild_id:
            return
        if not self._is_tracked_channel(message.channel.id):
            return

        date = self._today()
        user_id = message.author.id
        content = message.content or ""
        char_count = len(content)
        word_count = len(content.split()) if content else 0
        has_attachment = bool(message.attachments)

        # Track message in DB (for longest message / most reacted queries)
        await self._stats_repo.track_message(
            message.id, user_id, message.channel.id,
            char_count, word_count, has_attachment,
        )

        # Batch: daily stats
        key = (date, user_id)
        if key not in self._msg_batch:
            self._msg_batch[key] = {
                "messages_sent": 0, "longest_message": 0, "edits": 0,
                "reactions_given": 0,
            }
        self._msg_batch[key]["messages_sent"] += 1
        self._msg_batch[key]["longest_message"] = max(
            self._msg_batch[key]["longest_message"], char_count,
        )

        # Batch: channel stats
        ch_key = (date, message.channel.id, user_id)
        self._channel_batch[ch_key] = self._channel_batch.get(ch_key, 0) + 1

        # Batch: word frequency
        words = _extract_words(content)
        for word, count in words.items():
            w_key = (date, word)
            self._word_batch[w_key] = self._word_batch.get(w_key, 0) + count

        # Batch: mentions
        mentioned_ids = [u.id for u in message.mentions if not u.bot and u.id != user_id]
        for mid in mentioned_ids:
            m_key = (date, mid)
            self._mention_batch[m_key] = self._mention_batch.get(m_key, 0) + 1

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if after.author.bot or not after.guild:
            return
        if after.guild.id != self.bot.config.guild_id:
            return

        date = self._today()
        user_id = after.author.id
        key = (date, user_id)
        if key not in self._msg_batch:
            self._msg_batch[key] = {
                "messages_sent": 0, "longest_message": 0, "edits": 0,
                "reactions_given": 0,
            }
        self._msg_batch[key]["edits"] += 1

        # Also mark in message_tracking
        await self._stats_repo.mark_edited(after.id)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if not payload.guild_id or payload.guild_id != self.bot.config.guild_id:
            return
        if payload.member and payload.member.bot:
            return

        date = self._today()

        # Increment the reactor's reactions_given
        if payload.user_id:
            key = (date, payload.user_id)
            if key not in self._msg_batch:
                self._msg_batch[key] = {
                    "messages_sent": 0, "longest_message": 0, "edits": 0,
                    "reactions_given": 0,
                }
            self._msg_batch[key]["reactions_given"] += 1

        # Increment reaction count on the message itself
        await self._stats_repo.increment_reaction(payload.message_id)

    # ── Batch Flushing ────────────────────────────

    @tasks.loop(seconds=60)
    async def flush_batch_loop(self):
        await self._flush_batches()

    @flush_batch_loop.before_loop
    async def before_flush(self):
        await self.bot.wait_until_ready()

    async def _flush_batches(self) -> None:
        """Flush in-memory batches to database."""
        # Daily stats
        msg_batch = self._msg_batch.copy()
        self._msg_batch.clear()
        for (date, user_id), stats in msg_batch.items():
            if stats["messages_sent"] > 0:
                await self._stats_repo.increment_daily(date, user_id, "messages_sent", stats["messages_sent"])
            if stats["edits"] > 0:
                await self._stats_repo.increment_daily(date, user_id, "edits", stats["edits"])
            if stats["reactions_given"] > 0:
                await self._stats_repo.increment_daily(date, user_id, "reactions_given", stats["reactions_given"])
            if stats["longest_message"] > 0:
                await self._stats_repo.update_longest_message(date, user_id, stats["longest_message"])

        # Channel stats
        ch_batch = self._channel_batch.copy()
        self._channel_batch.clear()
        for (date, channel_id, user_id), count in ch_batch.items():
            for _ in range(count):
                await self._stats_repo.increment_channel(date, channel_id, user_id)

        # Word frequency
        word_batch = self._word_batch.copy()
        self._word_batch.clear()
        if word_batch:
            # Group by date
            by_date: dict[str, dict[str, int]] = defaultdict(dict)
            for (date, word), count in word_batch.items():
                by_date[date][word] = by_date[date].get(word, 0) + count
            for date, words in by_date.items():
                await self._stats_repo.increment_words(date, words)

        # Mention tracking
        mention_batch = self._mention_batch.copy()
        self._mention_batch.clear()
        if mention_batch:
            by_date_mentions: dict[str, list[int]] = defaultdict(list)
            for (date, mid), count in mention_batch.items():
                for _ in range(count):
                    by_date_mentions[date].append(mid)
            for date, mids in by_date_mentions.items():
                await self._stats_repo.increment_mentions(date, mids)

    # ── Monthly Report Generation ─────────────────

    @tasks.loop(minutes=30)
    async def monthly_report_check(self):
        """Check if it's the 1st of the month and generate report."""
        now = datetime.now(timezone.utc)
        if now.day == 1 and now.hour == 0 and now.minute < 30:
            # Generate report for previous month
            if now.month == 1:
                prev_month = f"{now.year - 1}-12"
            else:
                prev_month = f"{now.year}-{now.month - 1:02d}"

            # Check if already generated
            existing = await self._stats_repo.get_report(prev_month)
            if existing:
                return

            await self._generate_and_post_report(prev_month)

    @monthly_report_check.before_loop
    async def before_report_check(self):
        await self.bot.wait_until_ready()

    async def _generate_and_post_report(self, month: str) -> discord.Message | None:
        """Generate the monthly stats card and post it."""
        # Gather all stats
        report_data: dict = {}
        stat_entries: list[MonthlyStatEntry] = []

        guild = self.bot.guild
        if not guild:
            return None

        def _resolve_name(uid: int) -> str:
            member = guild.get_member(uid)
            return member.display_name if member else f"User {uid}"

        async def _resolve_avatar(uid: int):
            member = guild.get_member(uid)
            if member:
                return await self.bot.card_renderer.fetch_avatar(member)
            return None

        # 1. Most Messages
        top_msgs = await self._stats_repo.get_monthly_top_messages(month, 1)
        if top_msgs:
            winner = top_msgs[0]
            name = _resolve_name(winner["user_id"])
            avatar = await _resolve_avatar(winner["user_id"])
            stat_entries.append(MonthlyStatEntry(
                category="Most Messages", icon_name="\U0001f4ac",
                winner_name=name, winner_avatar=avatar,
                value=f"{winner['total']:,} messages",
            ))
            report_data["most_messages"] = {"user_id": winner["user_id"], "total": winner["total"]}

        # 2. Most Active Days
        top_active = await self._stats_repo.get_monthly_most_active_days(month, 1)
        if top_active:
            winner = top_active[0]
            name = _resolve_name(winner["user_id"])
            avatar = await _resolve_avatar(winner["user_id"])
            stat_entries.append(MonthlyStatEntry(
                category="Most Active Days", icon_name="\U0001f525",
                winner_name=name, winner_avatar=avatar,
                value=f"{winner['total']} days",
            ))
            report_data["most_active_days"] = {"user_id": winner["user_id"], "total": winner["total"]}

        # 3. Most Voice Time
        top_voice = await self._stats_repo.get_monthly_top_voice(month, 1)
        if top_voice:
            winner = top_voice[0]
            total_min = winner["total"] or 0
            name = _resolve_name(winner["user_id"])
            avatar = await _resolve_avatar(winner["user_id"])
            stat_entries.append(MonthlyStatEntry(
                category="Most Voice Time", icon_name="\U0001f3a4",
                winner_name=name, winner_avatar=avatar,
                value=f"{total_min // 60}h {total_min % 60}m",
            ))
            report_data["most_voice"] = {"user_id": winner["user_id"], "total": total_min}

        # 4. Most @'d Member
        top_mentioned = await self._stats_repo.get_monthly_most_mentioned(month, 1)
        if top_mentioned:
            winner = top_mentioned[0]
            name = _resolve_name(winner["user_id"])
            avatar = await _resolve_avatar(winner["user_id"])
            stat_entries.append(MonthlyStatEntry(
                category="Most @'d Member", icon_name="\U0001f4e2",
                winner_name=name, winner_avatar=avatar,
                value=f"{winner['total']:,} mentions",
            ))
            report_data["most_mentioned"] = {"user_id": winner["user_id"], "total": winner["total"]}

        # 5. Most Edits
        top_edits = await self._stats_repo.get_monthly_most_edits(month, 1)
        if top_edits:
            winner = top_edits[0]
            name = _resolve_name(winner["user_id"])
            avatar = await _resolve_avatar(winner["user_id"])
            stat_entries.append(MonthlyStatEntry(
                category="Most Edits", icon_name="\u270f\ufe0f",
                winner_name=name, winner_avatar=avatar,
                value=f"{winner['total']:,} edits",
            ))
            report_data["most_edits"] = {"user_id": winner["user_id"], "total": winner["total"]}

        # 6. Top Reactor
        top_reactors = await self._stats_repo.get_monthly_top_reactors(month, 1)
        if top_reactors:
            winner = top_reactors[0]
            name = _resolve_name(winner["user_id"])
            avatar = await _resolve_avatar(winner["user_id"])
            stat_entries.append(MonthlyStatEntry(
                category="Top Reactor", icon_name="\u2764\ufe0f",
                winner_name=name, winner_avatar=avatar,
                value=f"{winner['total']:,} reactions",
            ))
            report_data["top_reactor"] = {"user_id": winner["user_id"], "total": winner["total"]}

        # 7. Longest Message
        longest = await self._stats_repo.get_monthly_longest_message(month)
        if longest:
            name = _resolve_name(longest["user_id"])
            avatar = await _resolve_avatar(longest["user_id"])
            stat_entries.append(MonthlyStatEntry(
                category="Longest Message", icon_name="\U0001f4dd",
                winner_name=name, winner_avatar=avatar,
                value=f"{longest['char_count']:,} characters",
            ))
            report_data["longest_message"] = longest

        # 8. Most Popular Word
        top_words = await self._stats_repo.get_monthly_top_word(month, 1)
        if top_words:
            word = top_words[0]
            stat_entries.append(MonthlyStatEntry(
                category="Most Popular Word", icon_name="\U0001f4ac",
                winner_name=f'"{word["word"]}"', winner_avatar=None,
                value=f"Used {word['total']:,} times",
            ))
            report_data["most_popular_word"] = word

        # 9. Most Reacted Image
        most_reacted = await self._stats_repo.get_monthly_most_reacted_image(month)
        if most_reacted:
            name = _resolve_name(most_reacted["user_id"])
            avatar = await _resolve_avatar(most_reacted["user_id"])
            stat_entries.append(MonthlyStatEntry(
                category="Most Reacted Image", icon_name="\U0001f5bc\ufe0f",
                winner_name=name, winner_avatar=avatar,
                value=f"{most_reacted['reaction_count']:,} reactions",
            ))
            report_data["most_reacted_image"] = most_reacted

        # 10. Most Active Channel
        top_channels = await self._stats_repo.get_monthly_top_channels(month, 1)
        if top_channels:
            ch = top_channels[0]
            channel = self.bot.get_channel(ch["channel_id"])
            ch_name = f"#{channel.name}" if channel else f"Channel {ch['channel_id']}"
            stat_entries.append(MonthlyStatEntry(
                category="Most Active Channel", icon_name="\U0001f4c8",
                winner_name=ch_name, winner_avatar=None,
                value=f"{ch['total']:,} messages",
            ))
            report_data["most_active_channel"] = ch

        if not stat_entries:
            logger.info("No stats for month %s", month)
            return None

        # Parse month label
        try:
            dt = datetime.strptime(month, "%Y-%m")
            month_label = dt.strftime("%B %Y")
        except ValueError:
            month_label = month

        # Generate card
        file = await self.bot.card_renderer.monthly_stats_card(month_label, stat_entries)

        # Post in report channel
        config = self.bot.config.get("monthly_stats", {})
        channel_id = config.get("report_channel")
        posted_msg = None
        if channel_id:
            channel = self.bot.get_channel(channel_id)
            if channel and isinstance(channel, discord.TextChannel):
                posted_msg = await channel.send(
                    f"\U0001f4ca **Monthly Report — {month_label}**",
                    file=file,
                )

        # Save report to DB
        await self._stats_repo.save_report(
            month, report_data,
            message_id=posted_msg.id if posted_msg else None,
            channel_id=channel_id,
        )

        # Award XP to winners
        xp_rewards = config.get("monthly_xp_rewards", {})
        from database.repositories.xp import XPRepository
        xp_repo = XPRepository(self.bot.db)
        reward_map = {
            "most_messages": "most_messages",
            "most_active_days": "most_active_days",
            "most_voice": "most_voice",
            "most_mentioned": "most_mentioned",
            "top_reactor": "top_reactor",
        }
        for report_key, config_key in reward_map.items():
            data = report_data.get(report_key)
            if data and config_key in xp_rewards:
                amount = xp_rewards[config_key]
                uid = data["user_id"]
                await self._user_repo.upsert(uid)
                await xp_repo.add(uid, amount, "monthly_reward", f"{month}:{config_key}")
                user = await self._user_repo.get(uid)
                if user:
                    new_total = user.total_xp + amount
                    new_level = self.bot.xp_calculator.calculate_level(new_total)
                    await self._user_repo.add_xp(uid, amount, new_level)

        logger.info("Monthly report generated for %s", month)
        return posted_msg

    # ── User Commands ─────────────────────────────

    @app_commands.command(name="monthly", description="View current month's running stats")
    @app_commands.describe(member="View stats for a specific member")
    async def monthly(self, interaction: discord.Interaction, member: discord.Member | None = None):
        month = self._this_month()

        if member:
            stats = await self._stats_repo.get_user_monthly_stats(month, member.id)
            embed = self.bot.embed_builder.info(
                title=f"\U0001f4ca {member.display_name}'s Stats — {month}",
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="Messages", value=f"{stats.get('messages') or 0:,}", inline=True)
            embed.add_field(name="Voice", value=f"{(stats.get('voice') or 0) // 60}h {(stats.get('voice') or 0) % 60}m", inline=True)
            embed.add_field(name="Reactions", value=f"{stats.get('reactions') or 0:,}", inline=True)
            embed.add_field(name="Edits", value=f"{stats.get('edits') or 0:,}", inline=True)
            embed.add_field(name="Longest Msg", value=f"{stats.get('longest') or 0:,} chars", inline=True)
            embed.add_field(name="Active Days", value=f"{stats.get('active_days') or 0}", inline=True)
            await interaction.response.send_message(embed=embed)
            return

        # Server-wide summary for current month
        top_msgs = await self._stats_repo.get_monthly_top_messages(month, 5)
        top_voice = await self._stats_repo.get_monthly_top_voice(month, 5)
        top_channels = await self._stats_repo.get_monthly_top_channels(month, 5)

        embed = self.bot.embed_builder.info(title=f"\U0001f4ca Monthly Stats — {month}")

        if top_msgs:
            lines = []
            for i, row in enumerate(top_msgs):
                m = self.bot.guild.get_member(row["user_id"]) if self.bot.guild else None
                name = m.display_name if m else f"User {row['user_id']}"
                lines.append(f"**{i + 1}.** {name} — {row['total']:,}")
            embed.add_field(name="\U0001f4ac Top Messages", value="\n".join(lines), inline=True)

        if top_voice:
            lines = []
            for i, row in enumerate(top_voice):
                m = self.bot.guild.get_member(row["user_id"]) if self.bot.guild else None
                name = m.display_name if m else f"User {row['user_id']}"
                mins = row["total"] or 0
                lines.append(f"**{i + 1}.** {name} — {mins // 60}h {mins % 60}m")
            embed.add_field(name="\U0001f3a4 Top Voice", value="\n".join(lines), inline=True)

        if top_channels:
            lines = []
            for i, row in enumerate(top_channels):
                ch = self.bot.get_channel(row["channel_id"])
                ch_name = f"#{ch.name}" if ch else f"ID {row['channel_id']}"
                lines.append(f"**{i + 1}.** {ch_name} — {row['total']:,}")
            embed.add_field(name="\U0001f4c8 Top Channels", value="\n".join(lines), inline=True)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="monthly-recap", description="Regenerate last month's report (Staff)")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def monthly_recap(self, interaction: discord.Interaction):
        await interaction.response.defer()

        now = datetime.now(timezone.utc)
        if now.month == 1:
            prev_month = f"{now.year - 1}-12"
        else:
            prev_month = f"{now.year}-{now.month - 1:02d}"

        msg = await self._generate_and_post_report(prev_month)
        if msg:
            await interaction.followup.send(f"Monthly report posted! {msg.jump_url}")
        else:
            await interaction.followup.send("No data available for last month.", ephemeral=True)

    @app_commands.command(name="stats-channel", description="View stats for a specific channel")
    @app_commands.describe(channel="The channel to check")
    async def stats_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        month = self._this_month()
        top_channels = await self._stats_repo.get_monthly_top_channels(month, 50)

        ch_data = next((c for c in top_channels if c["channel_id"] == channel.id), None)
        if not ch_data:
            await interaction.response.send_message(
                f"No activity data for {channel.mention} this month.", ephemeral=True,
            )
            return

        embed = self.bot.embed_builder.info(
            title=f"\U0001f4ca #{channel.name} — {month}",
        )
        embed.add_field(name="Total Messages", value=f"{ch_data['total']:,}", inline=True)

        # Find rank among all channels
        rank = next((i + 1 for i, c in enumerate(top_channels) if c["channel_id"] == channel.id), None)
        if rank:
            embed.add_field(name="Channel Rank", value=f"#{rank}", inline=True)

        await interaction.response.send_message(embed=embed)


async def setup(bot: GayborhoodBot):
    await bot.add_cog(MonthlyStatsCog(bot))
