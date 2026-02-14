"""Role management commands — for when you need to fiddle with people's roles"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from core.bot import GayborhoodBot

logger = logging.getLogger(__name__)


class RoleManagementCog(commands.Cog, name="RoleManagementCog"):
    """Role management commands: /addrole, /removerole, /listroles"""

    def __init__(self, bot: GayborhoodBot):
        self.bot = bot

    @app_commands.command(name="addrole", description="Add a role to a member")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.describe(
        member="The member to add the role to",
        role="The role to add",
    )
    async def addrole(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        role: discord.Role,
    ):
        """Add a role to a member"""
        # Check if bot can manage this role
        if role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                f"I can't manage the **{role.name}** role — it's higher than or equal to my highest role.",
                ephemeral=True,
            )
            return

        # Check if user can manage this role
        if role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message(
                f"You can't manage the **{role.name}** role — it's higher than or equal to your highest role.",
                ephemeral=True,
            )
            return

        # Check if member already has the role
        if role in member.roles:
            await interaction.response.send_message(
                f"**{member.name}** already has the **{role.name}** role.",
                ephemeral=True,
            )
            return

        # Add the role using RoleService
        success = await self.bot.role_service.add_role(
            member,
            role,
            reason=f"Added by {interaction.user.name} via /addrole",
            actor_id=interaction.user.id,
        )

        if success:
            await interaction.response.send_message(
                f"✅ Added **{role.name}** to **{member.name}**",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"❌ Failed to add **{role.name}** to **{member.name}** — check logs",
                ephemeral=True,
            )

    @app_commands.command(name="removerole", description="Remove a role from a member")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.describe(
        member="The member to remove the role from",
        role="The role to remove",
    )
    async def removerole(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        role: discord.Role,
    ):
        """Remove a role from a member"""
        # Check if bot can manage this role
        if role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                f"I can't manage the **{role.name}** role — it's higher than or equal to my highest role.",
                ephemeral=True,
            )
            return

        # Check if user can manage this role
        if role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message(
                f"You can't manage the **{role.name}** role — it's higher than or equal to your highest role.",
                ephemeral=True,
            )
            return

        # Check if member has the role
        if role not in member.roles:
            await interaction.response.send_message(
                f"**{member.name}** doesn't have the **{role.name}** role anyway.",
                ephemeral=True,
            )
            return

        # Remove the role using RoleService
        success = await self.bot.role_service.remove_role(
            member,
            role,
            reason=f"Removed by {interaction.user.name} via /removerole",
            actor_id=interaction.user.id,
        )

        if success:
            await interaction.response.send_message(
                f"✅ Removed **{role.name}** from **{member.name}**",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"❌ Failed to remove **{role.name}** from **{member.name}** — check logs",
                ephemeral=True,
            )

    @app_commands.command(name="listroles", description="List all roles or roles for a specific member")
    @app_commands.describe(
        member="The member to show roles for (leave empty for all server roles)",
    )
    async def listroles(
        self,
        interaction: discord.Interaction,
        member: discord.Member | None = None,
    ):
        """List roles"""
        if member:
            # Show member's roles
            roles = [r for r in member.roles if r.id != interaction.guild.id]  # Exclude @everyone
            if not roles:
                await interaction.response.send_message(
                    f"**{member.name}** has no roles (other than @everyone).",
                    ephemeral=True,
                )
                return

            roles_sorted = sorted(roles, key=lambda r: r.position, reverse=True)
            role_list = "\n".join([f"• {r.mention} (ID: {r.id})" for r in roles_sorted])

            embed = self.bot.embed_builder.info(
                title=f"Roles for {member.name}",
                description=role_list,
            )
            embed.set_footer(text=f"{len(roles)} role(s)")

            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            # Show all server roles
            roles = [r for r in interaction.guild.roles if r.id != interaction.guild.id]  # Exclude @everyone
            roles_sorted = sorted(roles, key=lambda r: r.position, reverse=True)

            # Split into chunks if too many roles (embed description limit is 4096 chars)
            role_chunks = []
            current_chunk = []
            current_length = 0

            for role in roles_sorted:
                role_str = f"• {role.mention} — {len(role.members)} member(s)\n"
                role_len = len(role_str)

                if current_length + role_len > 3900:  # Leave some buffer
                    role_chunks.append("\n".join(current_chunk))
                    current_chunk = [role_str]
                    current_length = role_len
                else:
                    current_chunk.append(role_str)
                    current_length += role_len

            if current_chunk:
                role_chunks.append("\n".join(current_chunk))

            # Send first chunk
            embed = self.bot.embed_builder.info(
                title=f"Server Roles ({len(roles)} total)",
                description=role_chunks[0] if role_chunks else "No roles found",
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

            # Send additional chunks if needed
            if len(role_chunks) > 1:
                for chunk in role_chunks[1:]:
                    embed = self.bot.embed_builder.neutral(description=chunk)
                    await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="roleinfo", description="Get detailed info about a role")
    @app_commands.describe(
        role="The role to get info about",
    )
    async def roleinfo(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
    ):
        """Get detailed information about a role"""
        # Build info embed
        embed = self.bot.embed_builder.info(title=f"Role Info: {role.name}")

        # Basic info
        embed.add_field(name="ID", value=str(role.id), inline=True)
        embed.add_field(name="Position", value=str(role.position), inline=True)
        embed.add_field(name="Members", value=str(len(role.members)), inline=True)

        # Colour
        colour_hex = f"#{role.colour.value:06x}" if role.colour.value else "None"
        embed.add_field(name="Colour", value=colour_hex, inline=True)

        # Attributes
        attrs = []
        if role.hoist:
            attrs.append("Hoisted (shown separately)")
        if role.mentionable:
            attrs.append("Mentionable")
        if role.managed:
            attrs.append("Managed (by bot/integration)")

        if attrs:
            embed.add_field(name="Attributes", value="\n".join(attrs), inline=False)

        # Created at
        created = f"<t:{int(role.created_at.timestamp())}:F>"
        embed.add_field(name="Created", value=created, inline=False)

        # Permissions (only show notable ones)
        perms = role.permissions
        notable_perms = []

        if perms.administrator:
            notable_perms.append("⚠️ Administrator")
        if perms.manage_guild:
            notable_perms.append("Manage Server")
        if perms.manage_roles:
            notable_perms.append("Manage Roles")
        if perms.manage_channels:
            notable_perms.append("Manage Channels")
        if perms.kick_members:
            notable_perms.append("Kick Members")
        if perms.ban_members:
            notable_perms.append("Ban Members")
        if perms.moderate_members:
            notable_perms.append("Moderate Members")
        if perms.manage_messages:
            notable_perms.append("Manage Messages")
        if perms.mention_everyone:
            notable_perms.append("Mention @everyone")

        if notable_perms:
            embed.add_field(name="Notable Permissions", value="\n".join(notable_perms), inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # Error handler
    @addrole.error
    @removerole.error
    async def role_management_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "You need 'Manage Roles' permission to use this command.", ephemeral=True
            )


async def setup(bot: GayborhoodBot):
    await bot.add_cog(RoleManagementCog(bot))
