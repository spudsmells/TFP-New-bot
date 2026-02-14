from enum import Enum, IntEnum

VERSION = "1.0.0"
BOT_NAME = "The Gayborhood Bot"


class UserStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    KICKED = "kicked"
    BANNED = "banned"


class IntroStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    RESUBMITTED = "resubmitted"


class TicketType(str, Enum):
    MEMBER = "member"
    STAFF = "staff"
    AGE_VERIFY = "age_verify"


class TicketStatus(str, Enum):
    OPEN = "open"
    CLAIMED = "claimed"
    MUTED = "muted"
    CLOSED = "closed"
    ARCHIVED = "archived"


class TicketLogEvent(str, Enum):
    CREATED = "created"
    CLAIMED = "claimed"
    UNCLAIMED = "unclaimed"
    NUDGE_SENT = "nudge_sent"
    MUTED = "muted"
    UNMUTED = "unmuted"
    MEMBER_ADDED = "member_added"
    MESSAGE_SENT = "message_sent"
    CLOSED = "closed"
    ARCHIVED = "archived"


class XPSource(str, Enum):
    MESSAGE = "message"
    VOICE = "voice"
    REACTION = "reaction"
    BONUS = "bonus"
    PENALTY = "penalty"
    IMPORT = "import"


class TimerType(str, Enum):
    TICKET_MEMBER_NUDGE = "ticket_member_nudge"
    TICKET_STAFF_REMINDER = "ticket_staff_reminder"
    TICKET_MUTE_EXPIRE = "ticket_mute_expire"


class AuditSeverity(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class EmbedColor(IntEnum):
    SUCCESS = 0x57F287
    ERROR = 0xED4245
    WARNING = 0xFEE75C
    INFO = 0x5865F2
    STAFF = 0xEB459E
    WELCOME = 0xFF69B4
    XP = 0xF1C40F
    TICKET = 0x3498DB
    ACHIEVEMENT = 0xE91E63


class AchievementRarity(str, Enum):
    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class AchievementTrigger(str, Enum):
    MESSAGES_SENT = "messages_sent"
    LEVEL_REACHED = "level_reached"
    VC_MINUTES = "vc_minutes"
    DAYS_ACTIVE = "days_active"
    REACTIONS_GIVEN = "reactions_given"
    INTROS_REVIEWED = "intros_reviewed"
    TICKETS_CLOSED = "tickets_closed"
    AGE_VERIFIED = "age_verified"
    CONSECUTIVE_DAYS = "consecutive_days"
    UNIQUE_CHANNELS = "unique_channels"


class CardColor:
    """RGBA tuples for Pillow card rendering."""
    BG_PRIMARY = (30, 30, 46, 255)
    BG_SECONDARY = (24, 24, 37, 255)
    BG_PANEL = (40, 40, 60, 180)
    ACCENT_PINK = (255, 105, 180, 255)
    ACCENT_GOLD = (241, 196, 15, 255)
    ACCENT_PURPLE = (88, 101, 242, 255)
    ACCENT_GREEN = (87, 242, 135, 255)
    ACCENT_RED = (237, 66, 69, 255)
    TEXT_PRIMARY = (255, 255, 255, 255)
    TEXT_SECONDARY = (180, 180, 200, 255)
    TEXT_MUTED = (120, 120, 140, 255)
    PROGRESS_BG = (50, 50, 70, 200)
    PROGRESS_FILL = (255, 105, 180, 255)
    PROGRESS_FILL_END = (148, 103, 255, 255)

    RARITY_COLORS = {
        "common": (180, 180, 200, 255),
        "rare": (88, 101, 242, 255),
        "epic": (148, 103, 255, 255),
        "legendary": (241, 196, 15, 255),
    }
