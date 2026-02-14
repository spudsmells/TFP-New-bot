from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class User:
    user_id: int
    username: str | None = None
    status: str = "pending"
    rules_agreed: bool = False
    rules_agreed_at: str | None = None
    rule_version: str | None = None
    rules_method: str | None = None
    intro_status: str = "not_started"
    total_xp: int = 0
    level: int = 0
    messages_sent: int = 0
    vc_minutes: int = 0
    age_verified: bool = False
    age_verified_at: str | None = None
    joined_at: str | None = None
    created_at: str = ""
    updated_at: str = ""


@dataclass
class XPEntry:
    id: int = 0
    user_id: int = 0
    amount: int = 0
    source: str = ""
    details: str | None = None
    created_at: str = ""


@dataclass
class Intro:
    id: int = 0
    user_id: int = 0
    age: int | None = None
    preferred_name: str | None = None
    pronouns: str | None = None
    location: str | None = None
    region_key: str | None = None
    bio: str | None = None
    submission_num: int = 1
    status: str = "submitted"
    reviewer_id: int | None = None
    review_action: str | None = None
    review_reason: str | None = None
    reviewed_at: str | None = None
    welcome_msg_id: int | None = None
    intro_msg_id: int | None = None
    created_at: str = ""


@dataclass
class Ticket:
    id: int = 0
    channel_id: int | None = None
    ticket_type: str = "member"
    owner_id: int = 0
    opener_id: int = 0
    reason: str | None = None
    status: str = "open"
    claimed_by: int | None = None
    claimed_at: str | None = None
    muted: bool = False
    mute_expires_at: str | None = None
    nudge_count: int = 0
    last_nudge_at: str | None = None
    closed_by: int | None = None
    closed_at: str | None = None
    created_at: str = ""


@dataclass
class TicketLog:
    id: int = 0
    ticket_id: int = 0
    event: str = ""
    actor_id: int | None = None
    details: str | None = None
    created_at: str = ""


@dataclass
class BullyInsult:
    id: int = 0
    text: str = ""
    active: bool = True
    added_by: int | None = None
    removed_by: int | None = None
    created_at: str = ""


@dataclass
class MusicConversion:
    id: int = 0
    source_url: str = ""
    platform: str = ""
    artist: str | None = None
    title: str | None = None
    youtube_url: str | None = None
    success: bool = False
    requested_by: int | None = None
    created_at: str = ""


@dataclass
class AutoThreadConfig:
    channel_id: int = 0
    enabled: bool = True
    trigger_media: bool = True
    trigger_links: bool = False
    trigger_youtube: bool = False
    name_format: str = "{username} - {file_type}"
    created_by: int | None = None
    created_at: str = ""
    updated_at: str = ""


@dataclass
class Timer:
    id: int = 0
    timer_type: str = ""
    fires_at: str = ""
    payload: str | None = None
    fired: bool = False
    cancelled: bool = False
    created_at: str = ""


@dataclass
class AuditEntry:
    id: int = 0
    event_type: str = ""
    severity: str = "info"
    actor_id: int | None = None
    target_id: int | None = None
    details: str | None = None
    created_at: str = ""


@dataclass
class Milestone:
    id: int = 0
    user_id: int = 0
    level: int = 0
    notified: bool = False
    created_at: str = ""


@dataclass
class Achievement:
    id: int = 0
    key: str = ""
    name: str = ""
    description: str = ""
    icon: str = "star"
    rarity: str = "common"
    category: str = "general"
    trigger_type: str = ""
    trigger_value: int = 0
    xp_reward: int = 0
    active: bool = True
    created_at: str = ""


@dataclass
class UserAchievement:
    id: int = 0
    user_id: int = 0
    achievement_id: int = 0
    unlocked_at: str = ""
    notified: bool = False


@dataclass
class DailyStat:
    id: int = 0
    date: str = ""
    user_id: int = 0
    messages_sent: int = 0
    vc_minutes: int = 0
    reactions_given: int = 0
    reactions_received: int = 0
    edits: int = 0
    longest_message: int = 0
    channels_active: str | None = None


@dataclass
class MessageTracking:
    id: int = 0
    message_id: int = 0
    user_id: int = 0
    channel_id: int = 0
    char_count: int = 0
    word_count: int = 0
    has_attachment: bool = False
    reaction_count: int = 0
    edited: bool = False
    created_at: str = ""


@dataclass
class MonthlyReport:
    id: int = 0
    month: str = ""
    report_data: str = ""
    message_id: int | None = None
    channel_id: int | None = None
    created_at: str = ""
