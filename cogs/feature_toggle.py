"""Feature toggle commands — turn features on/off at runtime"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from core.bot import GayborhoodBot

logger = logging.getLogger(__name__)


class FeatureToggleCog(commands.Cog, name="FeatureToggleCog"):
    """Runtime feature flag management (Staff only)"""

    def __init__(self, bot: GayborhoodBot):
        self.bot = bot

    @app_commands.command(name="features-list", description="List all features and their status")
    @app_commands.checks.has_permissions(administrator=True)
    async def features_list(self, interaction: discord.Interaction):
        """List all available features and their enabled/disabled status"""
        from core.feature_flags import COG_FLAG_MAP

        flags = self.bot.config.get("features", {})

        # Group features by category
        categories = {
            "Core": ["diagnostics"],
            "Onboarding": ["onboarding", "intros", "age_verify"],
            "Progression": ["xp", "milestones", "achievements"],
            "Tickets": ["tickets_member", "tickets_staff", "ticket_lifecycle", "ticket_panel"],
            "Fun & Utilities": ["bully", "music", "auto_threads", "monthly_stats"],
            "Moderation (Phase 2)": ["moderation", "roles", "channels", "sticky"],
            "Community (Phase 3)": ["birthdays", "counting", "confessions", "bump"],
        }

        embed = self.bot.embed_builder.info(
            title="🎛️ Feature Flags Status",
            description="Current feature enable/disable status",
        )

        for category, feature_list in categories.items():
            status_lines = []
            for feature in feature_list:
                if feature in COG_FLAG_MAP:
                    enabled = flags.get(feature, False)
                    status = "✅ Enabled" if enabled else "❌ Disabled"
                    status_lines.append(f"`{feature}`: {status}")
                else:
                    status_lines.append(f"`{feature}`: ⚠️ Not found")

            if status_lines:
                embed.add_field(
                    name=category,
                    value="\n".join(status_lines),
                    inline=False,
                )

        # Add note about reload
        embed.set_footer(text="Use /feature-toggle to enable/disable | Use /reload-config to apply config changes")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="feature-toggle", description="Enable or disable a feature at runtime")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        feature="The feature to toggle",
        enabled="True to enable, False to disable",
    )
    async def feature_toggle(
        self,
        interaction: discord.Interaction,
        feature: str,
        enabled: bool,
    ):
        """
        Toggle a feature on or off.

        NOTE: This updates config in memory only. To persist, edit config.yaml and /reload-config
        """
        from core.feature_flags import COG_FLAG_MAP

        # Validate feature exists
        if feature not in COG_FLAG_MAP:
            await interaction.response.send_message(
                f"❌ Unknown feature: `{feature}`\n\n"
                f"Available features: {', '.join(f'`{f}`' for f in COG_FLAG_MAP.keys())}",
                ephemeral=True,
            )
            return

        # Update config in memory
        if "features" not in self.bot.config._data:
            self.bot.config._data["features"] = {}

        old_state = self.bot.config._data["features"].get(feature, False)
        self.bot.config._data["features"][feature] = enabled

        # Get cog path
        cog_path = COG_FLAG_MAP[feature]
        cog_name = cog_path.split(".")[-1]

        # Try to load/unload the cog
        try:
            if enabled and not old_state:
                # Enabling: Load the cog
                await self.bot.load_extension(cog_path)
                status = f"✅ Enabled `{feature}` (loaded `{cog_name}` cog)"
                logger.info("Feature enabled via toggle: %s", feature)

            elif not enabled and old_state:
                # Disabling: Unload the cog
                await self.bot.unload_extension(cog_path)
                status = f"❌ Disabled `{feature}` (unloaded `{cog_name}` cog)"
                logger.info("Feature disabled via toggle: %s", feature)

            else:
                # No change needed
                state_str = "enabled" if enabled else "disabled"
                status = f"ℹ️ `{feature}` is already {state_str}"

            # Sync commands
            await self.bot.tree.sync(guild=discord.Object(id=self.bot.config.guild_id))

            await interaction.response.send_message(
                f"{status}\n\n"
                f"⚠️ **Note:** This change is in-memory only. "
                f"To make it permanent, edit `config.yaml` and use `/reload-config`.",
                ephemeral=True,
            )

            # Log to audit
            await self.bot.audit_logger.log(
                "feature_toggled",
                actor_id=interaction.user.id,
                details=f"{feature}: {enabled}",
            )

        except commands.ExtensionAlreadyLoaded:
            await interaction.response.send_message(
                f"⚠️ `{feature}` cog is already loaded. Config updated but no reload needed.",
                ephemeral=True,
            )
        except commands.ExtensionNotLoaded:
            await interaction.response.send_message(
                f"⚠️ `{feature}` cog is not loaded. Config updated but no unload needed.",
                ephemeral=True,
            )
        except commands.ExtensionNotFound:
            await interaction.response.send_message(
                f"❌ Cog `{cog_path}` not found. The feature might not be implemented yet.",
                ephemeral=True,
            )
        except Exception as e:
            logger.exception("Failed to toggle feature %s", feature)
            await interaction.response.send_message(
                f"❌ Failed to toggle `{feature}`: {e}",
                ephemeral=True,
            )

    @app_commands.command(name="feature-reload", description="Reload a feature cog")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        feature="The feature to reload",
    )
    async def feature_reload(self, interaction: discord.Interaction, feature: str):
        """
        Reload a feature cog (useful for applying code changes without restarting)
        """
        from core.feature_flags import COG_FLAG_MAP

        # Validate feature exists
        if feature not in COG_FLAG_MAP:
            await interaction.response.send_message(
                f"❌ Unknown feature: `{feature}`",
                ephemeral=True,
            )
            return

        cog_path = COG_FLAG_MAP[feature]

        try:
            await self.bot.reload_extension(cog_path)
            await self.bot.tree.sync(guild=discord.Object(id=self.bot.config.guild_id))

            await interaction.response.send_message(
                f"✅ Reloaded `{feature}` cog (`{cog_path}`)\n"
                f"Commands synced to guild.",
                ephemeral=True,
            )

            logger.info("Feature reloaded: %s", feature)

            # Log to audit
            await self.bot.audit_logger.log(
                "feature_reloaded",
                actor_id=interaction.user.id,
                details=feature,
            )

        except commands.ExtensionNotLoaded:
            await interaction.response.send_message(
                f"❌ `{feature}` is not loaded. Use `/feature-toggle` to enable it first.",
                ephemeral=True,
            )
        except Exception as e:
            logger.exception("Failed to reload feature %s", feature)
            await interaction.response.send_message(
                f"❌ Failed to reload `{feature}`: {e}",
                ephemeral=True,
            )

    # Error handlers
    @features_list.error
    @feature_toggle.error
    @feature_reload.error
    async def feature_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "You need Administrator permissions to manage features.",
                ephemeral=True,
            )


async def setup(bot: GayborhoodBot):
    await bot.add_cog(FeatureToggleCog(bot))
