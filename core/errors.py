class BotError(Exception):
    """Base exception for all bot errors."""


class ConfigError(BotError):
    """Raised when configuration is invalid or missing."""


class DatabaseError(BotError):
    """Raised when a database operation fails."""


class MigrationError(DatabaseError):
    """Raised when a schema migration fails."""


class DMFailedError(BotError):
    """Raised when a DM cannot be sent after all retries."""

    def __init__(self, user_id: int, reason: str = "unknown"):
        self.user_id = user_id
        self.reason = reason
        super().__init__(f"DM to {user_id} failed: {reason}")


class RoleError(BotError):
    """Raised when a role operation fails."""

    def __init__(self, user_id: int, role_id: int, action: str, reason: str = "unknown"):
        self.user_id = user_id
        self.role_id = role_id
        self.action = action
        self.reason = reason
        super().__init__(f"Role {action} for {user_id} (role {role_id}) failed: {reason}")


class ContentFilterError(BotError):
    """Raised when content fails validation."""

    def __init__(self, reasons: list[str]):
        self.reasons = reasons
        super().__init__(f"Content filtered: {', '.join(reasons)}")


class TicketError(BotError):
    """Raised when a ticket operation fails."""


class IntroError(BotError):
    """Raised when an intro operation fails."""


class RateLimitError(BotError):
    """Raised when a user exceeds rate limits."""

    def __init__(self, user_id: int, action: str, retry_after: float):
        self.user_id = user_id
        self.action = action
        self.retry_after = retry_after
        super().__init__(f"Rate limited: {user_id} on {action}, retry after {retry_after:.1f}s")
