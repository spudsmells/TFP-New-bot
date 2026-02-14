"""Role service — manages role assignment without making a complete arse of it"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord

from core.errors import RoleError

if TYPE_CHECKING:
    from core.bot import GayborhoodBot
    from core.config import Config
    from services.audit_logger import AuditLogger

logger = logging.getLogger(__name__)


class RoleService:
    """
    Handles role assignment/removal with proper error handling and audit logging.

    Use this instead of doing member.add_roles() directly like a savage.
    """

    def __init__(self, bot: GayborhoodBot, config: Config, audit_logger: AuditLogger):
        self.bot = bot
        self.config = config
        self.audit = audit_logger

    async def add_role(
        self,
        member: discord.Member,
        role: discord.Role,
        reason: str | None = None,
        actor_id: int | None = None,
    ) -> bool:
        """
        Add role to member.

        Args:
            member: Member to add role to
            role: Role to add
            reason: Why we're doing this (for audit log)
            actor_id: Who's doing this (None for bot/system actions)

        Returns:
            True if successful, False if it failed
        """
        if role in member.roles:
            logger.debug("Member %s already has role %s", member.id, role.id)
            return True

        try:
            await member.add_roles(role, reason=reason or "Role assignment")
            logger.info("Added role %s to member %s", role.name, member.id)
            await self.audit.log_role_change(actor_id, member.id, role.id, "added")
            return True
        except discord.Forbidden:
            logger.error(
                "Missing permissions to add role %s to member %s",
                role.id,
                member.id,
            )
            await self.audit.log_error(
                "role_add_forbidden",
                f"Role {role.id} -> Member {member.id}",
            )
            return False
        except discord.HTTPException as e:
            logger.error("Failed to add role %s to member %s: %s", role.id, member.id, e)
            await self.audit.log_error(
                "role_add_failed",
                f"Role {role.id} -> Member {member.id}: {e}",
            )
            return False

    async def remove_role(
        self,
        member: discord.Member,
        role: discord.Role,
        reason: str | None = None,
        actor_id: int | None = None,
    ) -> bool:
        """
        Remove role from member.

        Args:
            member: Member to remove role from
            role: Role to remove
            reason: Why we're doing this
            actor_id: Who's doing this

        Returns:
            True if successful, False if it failed
        """
        if role not in member.roles:
            logger.debug("Member %s doesn't have role %s anyway", member.id, role.id)
            return True

        try:
            await member.remove_roles(role, reason=reason or "Role removal")
            logger.info("Removed role %s from member %s", role.name, member.id)
            await self.audit.log_role_change(actor_id, member.id, role.id, "removed")
            return True
        except discord.Forbidden:
            logger.error(
                "Missing permissions to remove role %s from member %s",
                role.id,
                member.id,
            )
            await self.audit.log_error(
                "role_remove_forbidden",
                f"Role {role.id} -> Member {member.id}",
            )
            return False
        except discord.HTTPException as e:
            logger.error(
                "Failed to remove role %s from member %s: %s",
                role.id,
                member.id,
                e,
            )
            await self.audit.log_error(
                "role_remove_failed",
                f"Role {role.id} -> Member {member.id}: {e}",
            )
            return False

    async def swap_roles(
        self,
        member: discord.Member,
        add_roles: list[discord.Role],
        remove_roles: list[discord.Role],
        reason: str | None = None,
        actor_id: int | None = None,
    ) -> bool:
        """
        Atomically swap roles (remove some, add others).

        More efficient than doing it one at a time.
        Commonly used for onboarding (Pending -> Gaybor + Regional role).

        Returns:
            True if all operations succeeded, False if any failed
        """
        # Filter out roles they already have or don't have
        actual_adds = [r for r in add_roles if r not in member.roles]
        actual_removes = [r for r in remove_roles if r in member.roles]

        if not actual_adds and not actual_removes:
            logger.debug("No role changes needed for member %s", member.id)
            return True

        try:
            # Do both operations atomically
            if actual_adds and actual_removes:
                await member.edit(
                    roles=[
                        r
                        for r in member.roles
                        if r not in actual_removes and r != member.guild.default_role
                    ]
                    + actual_adds,
                    reason=reason or "Role swap",
                )
            elif actual_adds:
                await member.add_roles(*actual_adds, reason=reason or "Role assignment")
            elif actual_removes:
                await member.remove_roles(*actual_removes, reason=reason or "Role removal")

            # Log each change
            for role in actual_adds:
                logger.info("Added role %s to member %s", role.name, member.id)
                await self.audit.log_role_change(actor_id, member.id, role.id, "added")

            for role in actual_removes:
                logger.info("Removed role %s from member %s", role.name, member.id)
                await self.audit.log_role_change(actor_id, member.id, role.id, "removed")

            return True

        except discord.Forbidden:
            logger.error(
                "Missing permissions to swap roles for member %s",
                member.id,
            )
            await self.audit.log_error(
                "role_swap_forbidden",
                f"Member {member.id}",
            )
            return False
        except discord.HTTPException as e:
            logger.error("Failed to swap roles for member %s: %s", member.id, e)
            await self.audit.log_error(
                "role_swap_failed",
                f"Member {member.id}: {e}",
            )
            return False

    async def add_role_or_raise(
        self,
        member: discord.Member,
        role: discord.Role,
        reason: str | None = None,
        actor_id: int | None = None,
    ) -> None:
        """
        Add role or raise RoleError if it fails.

        Use this when role assignment is critical and you need to handle failures.
        """
        success = await self.add_role(member, role, reason, actor_id)
        if not success:
            raise RoleError(member.id, role.id, "add", "Role assignment failed")

    async def remove_role_or_raise(
        self,
        member: discord.Member,
        role: discord.Role,
        reason: str | None = None,
        actor_id: int | None = None,
    ) -> None:
        """
        Remove role or raise RoleError if it fails.

        Use this when role removal is critical.
        """
        success = await self.remove_role(member, role, reason, actor_id)
        if not success:
            raise RoleError(member.id, role.id, "remove", "Role removal failed")
