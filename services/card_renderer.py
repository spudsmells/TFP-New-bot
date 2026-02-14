"""Card renderer — generates all the pretty image cards (or tries to anyway)"""
from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


class CardRenderer:
    """
    Generates PNG image cards using Pillow.

    Supports 6 card types:
    - Rank cards (XP, level, progress)
    - Leaderboard
    - Level-up notifications
    - Welcome cards
    - Achievement unlocks
    - Monthly stats reports

    Uses Inter font family with fallback to system fonts.
    """

    # Colour palette (the gay agenda but make it pastel)
    COLOUR_BG_START = (99, 102, 241)  # Purple
    COLOUR_BG_END = (219, 39, 119)  # Pink
    COLOUR_PANEL = (30, 30, 40, 220)  # Dark translucent
    COLOUR_TEXT_PRIMARY = (255, 255, 255)  # White
    COLOUR_TEXT_SECONDARY = (200, 200, 220)  # Light grey
    COLOUR_PROGRESS_BG = (60, 60, 70)  # Dark grey
    COLOUR_PROGRESS_FILL = (168, 139, 250)  # Purple
    COLOUR_GOLD = (251, 191, 36)  # Gold for #1
    COLOUR_SILVER = (209, 213, 219)  # Silver for #2
    COLOUR_BRONZE = (217, 119, 6)  # Bronze for #3

    def __init__(self):
        self.fonts_loaded = False
        self.font_regular: ImageFont.FreeTypeFont | None = None
        self.font_semibold: ImageFont.FreeTypeFont | None = None
        self.font_bold: ImageFont.FreeTypeFont | None = None
        self.font_extrabold: ImageFont.FreeTypeFont | None = None
        self._load_fonts()

    def _load_fonts(self) -> None:
        """Load Inter fonts from assets/fonts/ with fallback"""
        fonts_dir = Path("assets/fonts")

        try:
            # Try loading Inter fonts
            self.font_regular = ImageFont.truetype(str(fonts_dir / "Inter-Regular.ttf"), 24)
            self.font_semibold = ImageFont.truetype(str(fonts_dir / "Inter-SemiBold.ttf"), 24)
            self.font_bold = ImageFont.truetype(str(fonts_dir / "Inter-Bold.ttf"), 32)
            self.font_extrabold = ImageFont.truetype(str(fonts_dir / "Inter-ExtraBold.ttf"), 48)
            self.fonts_loaded = True
            logger.info("Loaded Inter fonts successfully")
        except Exception:
            logger.warning(
                "Failed to load Inter fonts — using default font (it'll look shit but it'll work)"
            )
            # Fallback to default PIL font
            self.font_regular = ImageFont.load_default()
            self.font_semibold = ImageFont.load_default()
            self.font_bold = ImageFont.load_default()
            self.font_extrabold = ImageFont.load_default()

    def _get_font(self, weight: str = "regular", size: int = 24) -> ImageFont.FreeTypeFont:
        """Get font with specified weight and size (with fallback)"""
        if not self.fonts_loaded:
            return ImageFont.load_default()

        try:
            fonts_dir = Path("assets/fonts")
            font_map = {
                "regular": "Inter-Regular.ttf",
                "semibold": "Inter-SemiBold.ttf",
                "bold": "Inter-Bold.ttf",
                "extrabold": "Inter-ExtraBold.ttf",
            }
            font_file = font_map.get(weight, "Inter-Regular.ttf")
            return ImageFont.truetype(str(fonts_dir / font_file), size)
        except Exception:
            return ImageFont.load_default()

    def _create_gradient_background(self, width: int, height: int) -> Image.Image:
        """Create a vertical gradient background (purple to pink)"""
        img = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(img)

        # Draw vertical gradient
        for y in range(height):
            # Interpolate colours
            ratio = y / height
            r = int(self.COLOUR_BG_START[0] + (self.COLOUR_BG_END[0] - self.COLOUR_BG_START[0]) * ratio)
            g = int(self.COLOUR_BG_START[1] + (self.COLOUR_BG_END[1] - self.COLOUR_BG_START[1]) * ratio)
            b = int(self.COLOUR_BG_START[2] + (self.COLOUR_BG_END[2] - self.COLOUR_BG_START[2]) * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        return img

    def _draw_glass_panel(
        self, draw: ImageDraw.ImageDraw, x: int, y: int, width: int, height: int, radius: int = 15
    ) -> None:
        """Draw a rounded rectangle with glass effect (dark translucent)"""
        # Draw rounded rectangle
        draw.rounded_rectangle(
            [(x, y), (x + width, y + height)],
            radius=radius,
            fill=self.COLOUR_PANEL,
        )

    def _draw_progress_bar(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        width: int,
        height: int,
        progress: float,
    ) -> None:
        """
        Draw a progress bar.

        Args:
            progress: 0.0 to 1.0 (percentage filled)
        """
        # Background
        draw.rounded_rectangle(
            [(x, y), (x + width, y + height)],
            radius=height // 2,
            fill=self.COLOUR_PROGRESS_BG,
        )

        # Filled portion
        if progress > 0:
            fill_width = int(width * min(progress, 1.0))
            draw.rounded_rectangle(
                [(x, y), (x + fill_width, y + height)],
                radius=height // 2,
                fill=self.COLOUR_PROGRESS_FILL,
            )

    def render_rank_card(
        self,
        username: str,
        discriminator: str,
        level: int,
        total_xp: int,
        current_xp: int,
        xp_for_next: int,
        rank: int,
        messages: int,
        vc_minutes: int,
    ) -> io.BytesIO:
        """
        Render rank card (934x282).

        Shows user's level, XP progress, rank, and stats.
        """
        width, height = 934, 282
        img = self._create_gradient_background(width, height)
        draw = ImageDraw.Draw(img)

        # Main glass panel
        self._draw_glass_panel(draw, 20, 20, width - 40, height - 40)

        # Username and discriminator
        font_name = self._get_font("bold", 36)
        font_disc = self._get_font("regular", 24)
        draw.text((140, 40), username, fill=self.COLOUR_TEXT_PRIMARY, font=font_name)
        draw.text((140 + font_name.getlength(username) + 10, 50), f"#{discriminator}", fill=self.COLOUR_TEXT_SECONDARY, font=font_disc)

        # Level (big number on right)
        font_level = self._get_font("extrabold", 72)
        level_text = f"LEVEL {level}"
        level_bbox = draw.textbbox((0, 0), level_text, font=font_level)
        level_width = level_bbox[2] - level_bbox[0]
        draw.text((width - level_width - 40, 40), level_text, fill=self.COLOUR_TEXT_PRIMARY, font=font_level)

        # Rank
        font_rank = self._get_font("semibold", 20)
        rank_text = f"Rank #{rank}"
        draw.text((140, 85), rank_text, fill=self.COLOUR_TEXT_SECONDARY, font=font_rank)

        # Progress bar
        progress = current_xp / xp_for_next if xp_for_next > 0 else 0
        self._draw_progress_bar(draw, 140, 130, width - 180, 30, progress)

        # XP text below progress bar
        font_xp = self._get_font("regular", 18)
        xp_text = f"{current_xp:,} / {xp_for_next:,} XP"
        draw.text((140, 170), xp_text, fill=self.COLOUR_TEXT_SECONDARY, font=font_xp)

        # Stats at bottom
        font_stats = self._get_font("semibold", 16)
        stats_y = 210
        draw.text((140, stats_y), f"💬 {messages:,} messages", fill=self.COLOUR_TEXT_SECONDARY, font=font_stats)
        draw.text((400, stats_y), f"🎤 {vc_minutes:,} mins voice", fill=self.COLOUR_TEXT_SECONDARY, font=font_stats)
        draw.text((700, stats_y), f"✨ {total_xp:,} total XP", fill=self.COLOUR_TEXT_SECONDARY, font=font_stats)

        # Convert to BytesIO
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer

    def render_leaderboard(self, entries: list[dict[str, Any]], title: str = "XP Leaderboard") -> io.BytesIO:
        """
        Render leaderboard card (800 x variable height).

        entries should be list of dicts with: rank, username, level, total_xp
        """
        width = 800
        entry_height = 60
        header_height = 100
        padding = 20
        height = header_height + (len(entries) * entry_height) + (padding * 2)

        img = self._create_gradient_background(width, height)
        draw = ImageDraw.Draw(img)

        # Main panel
        self._draw_glass_panel(draw, padding, padding, width - (padding * 2), height - (padding * 2))

        # Title
        font_title = self._get_font("bold", 40)
        title_bbox = draw.textbbox((0, 0), title, font=font_title)
        title_width = title_bbox[2] - title_bbox[0]
        draw.text(((width - title_width) // 2, 40), title, fill=self.COLOUR_TEXT_PRIMARY, font=font_title)

        # Entries
        font_rank = self._get_font("bold", 24)
        font_name = self._get_font("semibold", 22)
        font_stats = self._get_font("regular", 18)

        y = header_height + padding
        for entry in entries:
            rank = entry.get("rank", 0)
            username = entry.get("username", "Unknown")
            level = entry.get("level", 0)
            total_xp = entry.get("total_xp", 0)

            # Rank colour (gold/silver/bronze for top 3)
            rank_colour = self.COLOUR_TEXT_PRIMARY
            if rank == 1:
                rank_colour = self.COLOUR_GOLD
            elif rank == 2:
                rank_colour = self.COLOUR_SILVER
            elif rank == 3:
                rank_colour = self.COLOUR_BRONZE

            # Draw rank
            draw.text((50, y + 15), f"#{rank}", fill=rank_colour, font=font_rank)

            # Draw username
            draw.text((120, y + 12), username, fill=self.COLOUR_TEXT_PRIMARY, font=font_name)

            # Draw level and XP
            stats_text = f"Level {level}  •  {total_xp:,} XP"
            draw.text((120, y + 38), stats_text, fill=self.COLOUR_TEXT_SECONDARY, font=font_stats)

            y += entry_height

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer

    def render_levelup(self, username: str, old_level: int, new_level: int, unlocks: list[str] | None = None) -> io.BytesIO:
        """
        Render level-up card (800x250).

        Shows old → new level with optional unlocks list.
        """
        width, height = 800, 250
        img = self._create_gradient_background(width, height)
        draw = ImageDraw.Draw(img)

        # Main panel
        self._draw_glass_panel(draw, 20, 20, width - 40, height - 40)

        # "LEVEL UP!" text
        font_title = self._get_font("extrabold", 48)
        draw.text((40, 40), "LEVEL UP!", fill=self.COLOUR_GOLD, font=font_title)

        # Username
        font_name = self._get_font("semibold", 24)
        draw.text((40, 100), username, fill=self.COLOUR_TEXT_SECONDARY, font=font_name)

        # Old → New level
        font_level = self._get_font("bold", 56)
        level_text = f"{old_level} → {new_level}"
        draw.text((40, 135), level_text, fill=self.COLOUR_TEXT_PRIMARY, font=font_level)

        # Unlocks (if any)
        if unlocks:
            font_unlocks = self._get_font("regular", 18)
            unlocks_text = "Unlocked: " + ", ".join(unlocks)
            draw.text((width - 40 - font_unlocks.getlength(unlocks_text), 210), unlocks_text, fill=self.COLOUR_TEXT_SECONDARY, font=font_unlocks)

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer

    def render_achievement(
        self, name: str, description: str, rarity: str, xp_reward: int
    ) -> io.BytesIO:
        """
        Render achievement unlock card (800x200).

        Shows achievement name, description, rarity, and XP reward.
        """
        width, height = 800, 200
        img = self._create_gradient_background(width, height)
        draw = ImageDraw.Draw(img)

        # Main panel
        self._draw_glass_panel(draw, 20, 20, width - 40, height - 40)

        # "ACHIEVEMENT UNLOCKED" text
        font_title = self._get_font("bold", 32)
        draw.text((40, 35), "🏆 ACHIEVEMENT UNLOCKED", fill=self.COLOUR_GOLD, font=font_title)

        # Achievement name
        font_name = self._get_font("extrabold", 28)
        draw.text((40, 80), name, fill=self.COLOUR_TEXT_PRIMARY, font=font_name)

        # Description
        font_desc = self._get_font("regular", 18)
        draw.text((40, 115), description, fill=self.COLOUR_TEXT_SECONDARY, font=font_desc)

        # Rarity and XP reward
        font_meta = self._get_font("semibold", 16)
        meta_text = f"{rarity.upper()}  •  +{xp_reward} XP"
        draw.text((40, 150), meta_text, fill=self.COLOUR_TEXT_SECONDARY, font=font_meta)

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer

    def render_welcome(self, username: str, server_name: str = "The Gayborhood") -> io.BytesIO:
        """
        Render welcome card (1024x400).

        Simple welcome message with gradient background.
        """
        width, height = 1024, 400
        img = self._create_gradient_background(width, height)
        draw = ImageDraw.Draw(img)

        # Main panel
        self._draw_glass_panel(draw, 40, 40, width - 80, height - 80)

        # "WELCOME!" text
        font_title = self._get_font("extrabold", 72)
        title_text = "WELCOME!"
        title_bbox = draw.textbbox((0, 0), title_text, font=font_title)
        title_width = title_bbox[2] - title_bbox[0]
        draw.text(((width - title_width) // 2, 80), title_text, fill=self.COLOUR_TEXT_PRIMARY, font=font_title)

        # Username
        font_name = self._get_font("bold", 48)
        name_bbox = draw.textbbox((0, 0), username, font=font_name)
        name_width = name_bbox[2] - name_bbox[0]
        draw.text(((width - name_width) // 2, 180), username, fill=self.COLOUR_GOLD, font=font_name)

        # Server name
        font_server = self._get_font("regular", 28)
        server_text = f"to {server_name}"
        server_bbox = draw.textbbox((0, 0), server_text, font=font_server)
        server_width = server_bbox[2] - server_bbox[0]
        draw.text(((width - server_width) // 2, 250), server_text, fill=self.COLOUR_TEXT_SECONDARY, font=font_server)

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer

    def render_monthly_report(self, month: str, categories: dict[str, Any]) -> io.BytesIO:
        """
        Render monthly stats report card (~1200 x variable height).

        categories is a dict of category_name -> {winner: username, value: int/str}
        """
        width = 1200
        category_height = 70
        header_height = 120
        padding = 30
        height = header_height + (len(categories) * category_height) + (padding * 2)

        img = self._create_gradient_background(width, height)
        draw = ImageDraw.Draw(img)

        # Main panel
        self._draw_glass_panel(draw, padding, padding, width - (padding * 2), height - (padding * 2))

        # Title
        font_title = self._get_font("extrabold", 52)
        title_text = f"📊 {month} Stats"
        title_bbox = draw.textbbox((0, 0), title_text, font=font_title)
        title_width = title_bbox[2] - title_bbox[0]
        draw.text(((width - title_width) // 2, 50), title_text, fill=self.COLOUR_TEXT_PRIMARY, font=font_title)

        # Categories
        font_cat = self._get_font("bold", 26)
        font_winner = self._get_font("semibold", 22)
        font_value = self._get_font("regular", 20)

        y = header_height + padding
        for category, data in categories.items():
            winner = data.get("winner", "Unknown")
            value = data.get("value", "N/A")

            # Category name
            draw.text((50, y + 5), category, fill=self.COLOUR_TEXT_PRIMARY, font=font_cat)

            # Winner and value
            winner_text = f"🏆 {winner}"
            value_text = f"({value})"
            draw.text((50, y + 35), winner_text, fill=self.COLOUR_GOLD, font=font_winner)
            draw.text((50 + font_winner.getlength(winner_text) + 20, y + 38), value_text, fill=self.COLOUR_TEXT_SECONDARY, font=font_value)

            y += category_height

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer
