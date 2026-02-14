-- ──────────────────────────────────────────────
-- The Gayborhood Bot — Full Schema
-- ──────────────────────────────────────────────

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER PRIMARY KEY,
    applied_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Users ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    user_id         INTEGER PRIMARY KEY,
    username        TEXT,
    status          TEXT NOT NULL DEFAULT 'pending',
    rules_agreed    INTEGER NOT NULL DEFAULT 0,
    rules_agreed_at TEXT,
    rule_version    TEXT,
    rules_method    TEXT,
    intro_status    TEXT NOT NULL DEFAULT 'not_started',
    total_xp        INTEGER NOT NULL DEFAULT 0,
    level           INTEGER NOT NULL DEFAULT 0,
    messages_sent   INTEGER NOT NULL DEFAULT 0,
    vc_minutes      INTEGER NOT NULL DEFAULT 0,
    age_verified    INTEGER NOT NULL DEFAULT 0,
    age_verified_at TEXT,
    joined_at       TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── XP History ────────────────────────────────
CREATE TABLE IF NOT EXISTS xp_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(user_id),
    amount      INTEGER NOT NULL,
    source      TEXT NOT NULL,
    details     TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_xp_history_user ON xp_history(user_id);
CREATE INDEX IF NOT EXISTS idx_xp_history_source ON xp_history(source);

-- ── Intros ────────────────────────────────────
CREATE TABLE IF NOT EXISTS intros (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(user_id),
    age             INTEGER,
    preferred_name  TEXT,
    pronouns        TEXT,
    location        TEXT,
    region_key      TEXT,
    bio             TEXT,
    submission_num  INTEGER NOT NULL DEFAULT 1,
    status          TEXT NOT NULL DEFAULT 'submitted',
    reviewer_id     INTEGER,
    review_action   TEXT,
    review_reason   TEXT,
    reviewed_at     TEXT,
    welcome_msg_id  INTEGER,
    intro_msg_id    INTEGER,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_intros_user ON intros(user_id);
CREATE INDEX IF NOT EXISTS idx_intros_status ON intros(status);

-- ── Tickets ───────────────────────────────────
CREATE TABLE IF NOT EXISTS tickets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id      INTEGER UNIQUE,
    ticket_type     TEXT NOT NULL,
    owner_id        INTEGER NOT NULL,
    opener_id       INTEGER NOT NULL,
    reason          TEXT,
    status          TEXT NOT NULL DEFAULT 'open',
    claimed_by      INTEGER,
    claimed_at      TEXT,
    muted           INTEGER NOT NULL DEFAULT 0,
    mute_expires_at TEXT,
    nudge_count     INTEGER NOT NULL DEFAULT 0,
    last_nudge_at   TEXT,
    closed_by       INTEGER,
    closed_at       TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_tickets_owner ON tickets(owner_id);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);

-- ── Ticket Logs ───────────────────────────────
CREATE TABLE IF NOT EXISTS ticket_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id   INTEGER NOT NULL REFERENCES tickets(id),
    event       TEXT NOT NULL,
    actor_id    INTEGER,
    details     TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_ticket_logs_ticket ON ticket_logs(ticket_id);

-- ── Bully Insults ─────────────────────────────
CREATE TABLE IF NOT EXISTS bully_insults (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    text        TEXT NOT NULL UNIQUE,
    active      INTEGER NOT NULL DEFAULT 1,
    added_by    INTEGER,
    removed_by  INTEGER,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Bully Usage ───────────────────────────────
CREATE TABLE IF NOT EXISTS bully_usage (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    caller_id   INTEGER NOT NULL,
    target_id   INTEGER NOT NULL,
    insult_id   INTEGER REFERENCES bully_insults(id),
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_bully_usage_caller ON bully_usage(caller_id);
CREATE INDEX IF NOT EXISTS idx_bully_usage_target ON bully_usage(target_id);

-- ── Music Conversions ─────────────────────────
CREATE TABLE IF NOT EXISTS music_conversions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_url      TEXT NOT NULL,
    platform        TEXT NOT NULL,
    artist          TEXT,
    title           TEXT,
    youtube_url     TEXT,
    success         INTEGER NOT NULL DEFAULT 0,
    requested_by    INTEGER,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Auto Thread Configs ───────────────────────
CREATE TABLE IF NOT EXISTS auto_thread_configs (
    channel_id      INTEGER PRIMARY KEY,
    enabled         INTEGER NOT NULL DEFAULT 1,
    trigger_media   INTEGER NOT NULL DEFAULT 1,
    trigger_links   INTEGER NOT NULL DEFAULT 0,
    trigger_youtube INTEGER NOT NULL DEFAULT 0,
    name_format     TEXT NOT NULL DEFAULT '{username} - {file_type}',
    created_by      INTEGER,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Rule Acknowledgements ─────────────────────
CREATE TABLE IF NOT EXISTS rule_acknowledgements (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(user_id),
    rule_version    TEXT NOT NULL,
    method          TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_rule_ack_user ON rule_acknowledgements(user_id);

-- ── Milestones ────────────────────────────────
CREATE TABLE IF NOT EXISTS milestones (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(user_id),
    level       INTEGER NOT NULL,
    notified    INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, level)
);
CREATE INDEX IF NOT EXISTS idx_milestones_user ON milestones(user_id);

-- ── Timers ────────────────────────────────────
CREATE TABLE IF NOT EXISTS timers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timer_type  TEXT NOT NULL,
    fires_at    TEXT NOT NULL,
    payload     TEXT,
    fired       INTEGER NOT NULL DEFAULT 0,
    cancelled   INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_timers_fires ON timers(fires_at) WHERE fired = 0 AND cancelled = 0;

-- ── Audit Log ─────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type  TEXT NOT NULL,
    severity    TEXT NOT NULL DEFAULT 'info',
    actor_id    INTEGER,
    target_id   INTEGER,
    details     TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_audit_event ON audit_log(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_log(actor_id);

-- ── Sticky Messages ──────────────────────────
CREATE TABLE IF NOT EXISTS sticky_messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id  INTEGER NOT NULL,
    message_id  INTEGER NOT NULL,
    embed_type  TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Satisfaction Surveys ─────────────────────
CREATE TABLE IF NOT EXISTS satisfaction_surveys (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id   INTEGER REFERENCES tickets(id),
    user_id     INTEGER NOT NULL,
    rating      INTEGER,
    feedback    TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Achievements ──────────────────────────────
CREATE TABLE IF NOT EXISTS achievements (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    key             TEXT UNIQUE NOT NULL,
    name            TEXT NOT NULL,
    description     TEXT NOT NULL,
    icon            TEXT NOT NULL DEFAULT 'star',
    rarity          TEXT NOT NULL DEFAULT 'common',
    category        TEXT NOT NULL DEFAULT 'general',
    trigger_type    TEXT NOT NULL,
    trigger_value   INTEGER NOT NULL,
    xp_reward       INTEGER NOT NULL DEFAULT 0,
    active          INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS user_achievements (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(user_id),
    achievement_id  INTEGER NOT NULL REFERENCES achievements(id),
    unlocked_at     TEXT NOT NULL DEFAULT (datetime('now')),
    notified        INTEGER NOT NULL DEFAULT 0,
    UNIQUE(user_id, achievement_id)
);
CREATE INDEX IF NOT EXISTS idx_user_achievements_user ON user_achievements(user_id);

-- ── Daily Stats ───────────────────────────────
CREATE TABLE IF NOT EXISTS daily_stats (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    date                TEXT NOT NULL,
    user_id             INTEGER NOT NULL,
    messages_sent       INTEGER NOT NULL DEFAULT 0,
    vc_minutes          INTEGER NOT NULL DEFAULT 0,
    reactions_given     INTEGER NOT NULL DEFAULT 0,
    reactions_received  INTEGER NOT NULL DEFAULT 0,
    edits               INTEGER NOT NULL DEFAULT 0,
    longest_message     INTEGER NOT NULL DEFAULT 0,
    channels_active     TEXT,
    UNIQUE(date, user_id)
);
CREATE INDEX IF NOT EXISTS idx_daily_stats_date ON daily_stats(date);
CREATE INDEX IF NOT EXISTS idx_daily_stats_user ON daily_stats(user_id);

-- ── Message Tracking ──────────────────────────
CREATE TABLE IF NOT EXISTS message_tracking (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id      INTEGER NOT NULL,
    user_id         INTEGER NOT NULL,
    channel_id      INTEGER NOT NULL,
    char_count      INTEGER NOT NULL DEFAULT 0,
    word_count      INTEGER NOT NULL DEFAULT 0,
    has_attachment   INTEGER NOT NULL DEFAULT 0,
    reaction_count  INTEGER NOT NULL DEFAULT 0,
    edited          INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_msg_tracking_user ON message_tracking(user_id);
CREATE INDEX IF NOT EXISTS idx_msg_tracking_channel ON message_tracking(channel_id);
CREATE INDEX IF NOT EXISTS idx_msg_tracking_created ON message_tracking(created_at);

-- ── Channel Stats ─────────────────────────────
CREATE TABLE IF NOT EXISTS channel_stats (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT NOT NULL,
    channel_id      INTEGER NOT NULL,
    message_count   INTEGER NOT NULL DEFAULT 0,
    unique_users    INTEGER NOT NULL DEFAULT 0,
    UNIQUE(date, channel_id)
);
CREATE INDEX IF NOT EXISTS idx_channel_stats_date ON channel_stats(date);

-- ── Monthly Reports ───────────────────────────
CREATE TABLE IF NOT EXISTS monthly_reports (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    month           TEXT NOT NULL,
    report_data     TEXT NOT NULL,
    message_id      INTEGER,
    channel_id      INTEGER,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Word Frequency ────────────────────────────
CREATE TABLE IF NOT EXISTS word_frequency (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT NOT NULL,
    word        TEXT NOT NULL,
    count       INTEGER NOT NULL DEFAULT 1,
    UNIQUE(date, word)
);
CREATE INDEX IF NOT EXISTS idx_word_freq_date ON word_frequency(date);

-- ── Mention Tracking ──────────────────────────
CREATE TABLE IF NOT EXISTS mention_tracking (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT NOT NULL,
    mentioned_id    INTEGER NOT NULL,
    count           INTEGER NOT NULL DEFAULT 1,
    UNIQUE(date, mentioned_id)
);
CREATE INDEX IF NOT EXISTS idx_mention_date ON mention_tracking(date);
