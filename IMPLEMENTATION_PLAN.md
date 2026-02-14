# The Gayborhood Bot — Implementation Plan
## *or: how i learned to stop worrying and love the merge conflicts*

Right so this is where we're at innit. Been working on this bloody thing for ages and we're *almost* there. Just need to finish the bits I got too knackered to do and add the new shite that's been requested.

---

## Current State: What Actually Works

### ✅ Fully Implemented Features (the good bits)

**Core Systems That Don't Make Me Want to Scream:**
- **XP & Leveling** — messages, voice, reactions all award XP. Formula works (`50*level² + 50*level`). Cards look fit.
- **Support Tickets** — member & staff creation, claiming, muting, auto-nudges. Actually quite proud of this one ngl.
- **Age Verification** — Level 15 gate, creates special ticket, staff review. Does what it says on the tin.
- **Introductions** — 5-field modal, staff review with approve/reject/kick/ban, regional role assignment via fuzzy matching. Proper comprehensive.
- **Achievements** — Trigger-based unlocking, periodic sweeps, visual cards, 29 defaults seeded. Rarity tiers and all that.
- **Milestones** — Special level-up cards for milestone levels (5, 10, 15, etc). DM + channel post.
- **Monthly Stats** — Tracks literally everything, generates monthly report cards, awards XP to winners. Batched in memory for performance cos I'm not a muppet.
- **Auto-Threading** — Media/link detection, auto-creates discussion threads. Configurable af.
- **Music Conversion** — Spotify/Apple Music → YouTube. Works with yt-dlp. Rate limited so people don't abuse it.
- **Bully Command** — Random insults. Has abuse detection. It's camp and I love it.
- **Onboarding** — Rules DM, fallback channel, welcome cards. Assigns Pending role. Standard stuff.
- **Diagnostics** — `/ping`, `/status`, `/reload-config`. The boring essentials.
- **Rule Agreement** — Modal on join, version tracking. Required before they can do owt.

### ⚠️ Partially Done (the "i'll finish it later" pile)

**Role Management:**
- Auto-assignment works (Pending→Gaybor, regional roles from intro)
- **MISSING:** Manual `/role-assign`, `/role-remove` commands
- **MISSING:** Self-serve role selection menus (reaction roles, button panels)

**Moderation:**
- Can kick/ban through intro review
- Ticket muting exists but only for ticket channels
- **MISSING:** `/kick`, `/ban`, `/mute`, `/warn` commands
- **MISSING:** Infraction tracking system
- **MISSING:** Server-wide mute role application

**Sticky Messages:**
- Ticket panel auto-reposts if deleted
- **MISSING:** General `/sticky` command for arbitrary messages

**Bump System:**
- Nudge timers exist (2h member, 12h staff)
- **MISSING:** Traditional `/bump` command & scheduled reminders

### ❌ Completely Missing (the "fuck i forgot about that" list)

1. **Birthday System** — No tracking, no announcements, nothing. Needs adding.
2. **Counting Channel Regulation** — No cog for this whatsoever.
3. **Confessions** — Anonymous submission system doesn't exist.
4. **Thread Management** — No comment blocking, no thread-specific moderation.
5. **Channel Management** — No create/delete/edit commands for channels.
6. **General Role Menus** — No self-serve role selection panels.

---

## The Critical Bit: Missing Core Services

These 8 services are referenced in `core/bot.py` but don't actually exist. The bot **will crash on startup** without them. This is the first priority before anything else.

### 1. `services/audit_logger.py` - AuditLogger
**What it needs to do:**
- Log all significant bot actions to database (`audit_log` table)
- Severity levels: info, warning, error, critical
- Optional Discord webhook posting for real-time monitoring
- Methods: `log_intro_submission()`, `log_ticket_action()`, `log_xp_award()`, etc.

**Usage in codebase:**
- Called by RoleService, DMService, TimerService
- Logs intro approvals/rejections, role changes, XP modifications, ticket actions
- Already passed to service constructors

### 2. `services/dm_service.py` - DMService
**What it needs to do:**
- Send DMs to members with retry logic
- Fallback to configured channel if DM fails (closed DMs)
- Track failures in audit log
- Methods: `send_dm(user, content/embed)`, `send_with_fallback(user, content, fallback_channel)`

**Usage in codebase:**
- Onboarding rules DM
- Intro approval/rejection notifications
- Level-up milestone cards
- Achievement unlock cards
- Age verification instructions

### 3. `services/role_service.py` - RoleService
**What it needs to do:**
- Add/remove roles with permission error handling
- Audit log all role changes
- Batch role operations (swap multiple roles at once)
- Methods: `add_role(member, role, reason)`, `remove_role(member, role, reason)`, `swap_roles(member, add_roles, remove_roles, reason)`

**Usage in codebase:**
- Intro approval: swap Pending→Gaybor, add regional role
- Age verification: add age_verified role
- Onboarding: add Pending role on join

### 4. `services/embed_builder.py` - EmbedBuilder
**What it needs to do:**
- Create consistently-styled embeds with server branding
- Colour codes for: success (green), error (red), warning (yellow), info (blue/purple)
- Auto-add footer with bot name
- Auto-add thumbnail if configured
- Methods: `success(title, description)`, `error(title, description)`, `info(title, description)`, `warning(title, description)`

**Usage in codebase:**
- Everywhere. Literally every embed in every cog.
- Commands, notifications, error messages, staff alerts

### 5. `services/timer_service.py` - TimerService
**What it needs to do:**
- Schedule persistent timers that survive bot restarts
- Poll database every 30s for expired timers
- Execute timer actions: nudge member, remind staff, unmute user
- Methods: `schedule_timer(timer_type, execute_at, data)`, `cancel_timer(timer_id)`, `start_polling()`, `stop_polling()`

**Usage in codebase:**
- Ticket nudges (2h member response, 12h staff claim)
- Mute expiry (30min default, unmute user)
- Already has start/stop calls in bot.py

### 6. `services/content_filter.py` - ContentFilter
**What it needs to do:**
- Validate user-submitted text (intro bios, ticket reasons)
- Check for slurs using `data/slurs.txt`
- Profanity detection via better-profanity library
- Minimum length enforcement
- Methods: `validate_bio(text, min_length, max_length)`, `validate_reason(text)`, `check_profanity(text)`

**Usage in codebase:**
- Intro bio validation (30-400 chars, no slurs)
- Ticket reason validation

### 7. `services/welcome_generator.py` - WelcomeGenerator
**What it needs to do:**
- Generate randomised welcome messages from templates
- Variable substitution: `{name}`, `{pronouns}`, `{location}`, `{age}`
- Load templates from `data/welcome_templates.json`
- Methods: `generate_welcome(intro_data)`

**Usage in codebase:**
- Posted in #welcome channel when intro approved

### 8. `services/card_renderer.py` - CardRenderer
**What it needs to do:**
- Generate PNG image cards using Pillow
- 6 card types: rank, leaderboard, level-up, welcome, achievement, monthly stats
- Gradient backgrounds, glass-effect panels, progress bars
- Load fonts from `assets/fonts/` with system font fallback
- Methods: `render_rank_card(user_data)`, `render_leaderboard(top_users)`, `render_levelup(old_level, new_level)`, `render_achievement(achievement_data)`, `render_monthly_report(stats)`, `render_welcome(user_data)`

**Usage in codebase:**
- `/rank` and `/leaderboard` commands
- Milestone level-up notifications
- Achievement unlocks
- Monthly report generation
- Welcome cards on member join

---

## New Features To Implement

Right so here's what's been requested that doesn't exist yet. Gonna need to build these from scratch.

### 🎂 Birthday System

**Requirements:**
- Track member birthdays (day/month, optional year for age display)
- Daily check at midnight UTC for birthdays
- Post announcement in configured channel with mention
- Optional birthday role (auto-assign for 24h then remove)
- Commands: `/birthday-set`, `/birthday-remove`, `/birthday-list` (upcoming), `/birthday-check` (see specific user's bday)

**Database:**
- New table: `birthdays` (user_id, birth_day, birth_month, birth_year nullable, announced_year)
- Track which year we've announced so we don't spam

**Configuration:**
```yaml
birthdays:
  announcement_channel: 000000000000000000
  birthday_role: 000000000000000000  # optional, null if not used
  announcement_message: "🎂 Happy birthday to {mention}! Have a proper gay day x"
```

**Cog:** `cogs/birthdays.py`

---

### 🔢 Counting Channel Regulation

**Requirements:**
- Members post sequential numbers (1, 2, 3, ...)
- Bot validates each message is the correct next number
- Delete incorrect messages instantly
- Optional: prevent same user posting twice in a row
- Track high score (highest number reached before reset)
- Auto-reset on mistake or manual `/counting-reset`
- Stats: `/counting-stats` shows current count, high score, top contributors

**Database:**
- New table: `counting_channels` (channel_id, current_count, high_score, last_user_id, reset_count, prevent_double_counting bool)
- New table: `counting_contributions` (channel_id, user_id, count_contributed, mistakes_made)

**Configuration:**
```yaml
counting:
  channels: []  # list of channel IDs configured for counting
  prevent_double: true  # same user can't post twice in a row
  delete_mistakes: true
  save_mistakes: false  # whether to save deleted messages to a log channel
```

**Cog:** `cogs/counting.py`

---

### 🤐 Confessions System

**Requirements:**
- Anonymous message submission via `/confess` command (ephemeral)
- Modal with confession text
- Optional staff approval queue before posting
- Post to confession channel with random colour embed
- Confession numbering (#1, #2, etc)
- Members can react/comment on confessions
- Optional: `/confess-ban` to block users from confessing (staff)

**Database:**
- New table: `confessions` (id, user_id, content, status: pending/approved/rejected, posted_message_id, created_at, reviewed_by, reviewed_at)

**Configuration:**
```yaml
confessions:
  channel: 000000000000000000
  approval_required: true  # if false, posts immediately
  approval_channel: 000000000000000000  # where staff review before posting
  min_length: 10
  max_length: 500
  banned_users: []  # list of user IDs blocked from confessing
```

**Cog:** `cogs/confessions.py`

**Views:**
- ConfessionApprovalView (approve/reject buttons for staff)

---

### 🛡️ Moderation Suite

**Requirements:**
- `/kick <member> [reason]` — Kick with audit log
- `/ban <member> [reason] [delete_days]` — Ban with message deletion
- `/unban <user_id> [reason]` — Unban by user ID
- `/mute <member> [duration] [reason]` — Apply mute role, create timer for unmute
- `/unmute <member> [reason]` — Remove mute role, cancel timer
- `/warn <member> <reason>` — Issue warning, DM user, log in database
- `/warnings <member>` — View user's warning history
- `/clear-warnings <member>` — Clear warnings (admin only)
- All actions logged to audit log + posted in staff channel

**Database:**
- New table: `infractions` (id, user_id, type: warn/mute/kick/ban, reason, moderator_id, created_at, expires_at nullable, active bool)

**Configuration:**
```yaml
moderation:
  mute_role: 000000000000000000
  default_mute_duration: 3600  # seconds (1 hour)
  log_channel: 000000000000000000  # where mod actions are posted
  dm_on_action: true  # whether to DM user when actioned
```

**Cog:** `cogs/moderation.py`

---

### 📌 General Sticky Messages

**Requirements:**
- `/sticky <message>` — Make current message sticky (reposts if deleted, always at bottom)
- `/sticky-create <channel> <message>` — Create sticky in specified channel
- `/sticky-remove <channel>` — Remove sticky from channel
- `/sticky-list` — List all active stickies
- Auto-repost when new messages push it up

**Database:**
- Extend `sticky_messages` table to support arbitrary channels (currently only ticket panel)
- Add fields: content, embed_data (JSON), repost_threshold (messages before repost)

**Configuration:**
```yaml
sticky_messages:
  repost_after_messages: 5  # how many messages before sticky reposts
```

**Cog:** Extend `cogs/ticket_panel.py` or create new `cogs/sticky.py`

---

### 🧵 Thread Management

**Requirements:**
- `/thread-lock` — Lock thread (only staff can post)
- `/thread-unlock` — Unlock thread
- `/thread-archive` — Archive thread immediately
- `/thread-slowmode <seconds>` — Set slowmode in thread
- `/thread-block <member>` — Block member from commenting in thread (permission overwrite)
- `/thread-unblock <member>` — Unblock member
- Auto-archive threads after X days of inactivity (configurable)

**Database:**
- New table: `thread_blocks` (thread_id, user_id, blocked_by, reason, created_at)

**Configuration:**
```yaml
threading:
  max_threads_per_minute: 5
  default_name_format: "{username} - {file_type}"
  auto_archive_duration: 1440
  auto_archive_inactive_days: 7  # NEW: archive threads with no activity after X days
  slowmode_default: 0
```

**Cog:** Extend `cogs/auto_threads.py` with management commands

---

### 🎭 Role Selector Menus

**Requirements:**
- `/role-menu-create <channel> <title>` — Create self-serve role menu with buttons
- Modal to add roles: "Add roles (one per line, format: emoji role_id label)"
- Generates persistent button view with role toggle
- Members click buttons to add/remove roles
- Limit which roles can be self-assigned (configured list)
- Optional: max roles per category

**Database:**
- New table: `role_menus` (id, channel_id, message_id, title, description, created_by)
- New table: `role_menu_options` (menu_id, role_id, emoji, label, position)

**Configuration:**
```yaml
role_menus:
  allowed_roles: []  # list of role IDs that can be added to menus (empty = all)
  max_selections_per_menu: 0  # 0 = unlimited, otherwise enforce limit
```

**Cog:** `cogs/role_menus.py`

**Views:** `RoleMenuView` (dynamic buttons based on database config)

---

### 📊 Channel Management Commands

**Requirements:**
- `/channel-create <name> <type> [category] [topic]` — Create channel
- `/channel-delete <channel>` — Delete channel with confirmation
- `/channel-edit <channel> [name] [topic] [slowmode] [nsfw]` — Edit channel properties
- `/channel-clone <channel> [name]` — Clone channel with permissions
- `/channel-lock <channel>` — Deny send_messages for @everyone
- `/channel-unlock <channel>` — Allow send_messages for @everyone
- All actions logged to audit log

**Cog:** `cogs/channel_management.py`

---

### 👥 Role Management Commands

**Requirements:**
- `/role-create <name> [colour] [hoist] [mentionable]` — Create role
- `/role-delete <role>` — Delete role with confirmation
- `/role-edit <role> [name] [colour] [hoist] [mentionable]` — Edit role properties
- `/role-assign <member> <role>` — Assign role to member
- `/role-remove <member> <role>` — Remove role from member
- `/role-info <role>` — Show role info (member count, permissions, etc)
- `/role-members <role>` — List members with role
- All actions logged via RoleService

**Cog:** `cogs/role_management.py`

---

### 🔔 Bump Tracking & Reminders

**Requirements:**
- `/bump` — Manual bump command (posts to designated channel, sets 2h timer)
- Auto-reminder in channel when bump available
- Track last bump time, bump count per user
- Leaderboard: `/bump-stats` shows top bumpers
- Optional: reward XP for bumping

**Database:**
- New table: `bump_tracking` (id, user_id, bumped_at, bump_type: manual/disboard/other)

**Configuration:**
```yaml
bumping:
  bump_channel: 000000000000000000
  reminder_channel: 000000000000000000  # where to post "bump available" message
  bump_interval_hours: 2
  xp_reward: 20  # XP awarded per bump
  bump_role: 000000000000000000  # optional role to ping when bump available
```

**Cog:** `cogs/bumping.py`

---

## Configuration Strategy: Making It Actually Usable

One of the requirements is "easily configurable" so here's how we're gonna handle it:

### Centralised Config (`config.yaml`)

Every feature has its own section with sensible defaults. Example:

```yaml
guild_id: 000000000000000000

# Role IDs
roles:
  pending: 000000000000000000
  gaybor: 000000000000000000
  staff: 000000000000000000
  admin: 000000000000000000
  age_verified: 000000000000000000
  muted: 000000000000000000
  birthday: 000000000000000000  # NEW
  # Regional roles
  region_na_east: 000000000000000000
  # ... etc

# Channel IDs
channels:
  onboarding_fallback: 000000000000000000
  staff_review: 000000000000000000
  welcome: 000000000000000000
  ticket_booth: 000000000000000000
  ticket_category: 000000000000000000
  ticket_archive_category: 000000000000000000
  staff_alerts: 000000000000000000
  bot_logs: 000000000000000000
  levelup: 000000000000000000
  birthday_announcements: 000000000000000000  # NEW
  confession: 000000000000000000  # NEW
  confession_approval: 000000000000000000  # NEW
  moderation_log: 000000000000000000  # NEW
  bump_channel: 000000000000000000  # NEW
  bump_reminders: 000000000000000000  # NEW

# Feature flags (true/false to enable/disable)
features:
  diagnostics: true
  onboarding: true
  xp: true
  auto_threads: true
  intros: true
  bully: true
  music: true
  tickets_member: true
  tickets_staff: true
  age_verify: true
  ticket_lifecycle: true
  ticket_panel: true
  milestones: true
  achievements: true
  monthly_stats: true
  birthdays: true  # NEW
  counting: true  # NEW
  confessions: true  # NEW
  moderation: true  # NEW
  sticky: true  # NEW
  thread_management: true  # NEW
  role_menus: true  # NEW
  channel_management: true  # NEW
  role_management: true  # NEW
  bumping: true  # NEW

# Auto-reactions per channel
auto_reactions:
  "000000000000000000":  # channel ID
    - "👍"
    - "❤️"
    - "🔥"
  "111111111111111111":  # another channel
    - "⭐"

# Birthday settings
birthdays:
  announcement_channel: 000000000000000000
  birthday_role: null  # optional
  announcement_message: "🎂 Happy birthday {mention}! 🎉"
  check_time: "00:00"  # UTC time to check daily

# Counting settings
counting:
  channels:
    "000000000000000000":
      prevent_double: true
      delete_mistakes: true
      save_to_log: false
      log_channel: null

# Confession settings
confessions:
  channel: 000000000000000000
  approval_required: true
  approval_channel: 000000000000000000
  min_length: 10
  max_length: 500
  banned_users: []

# Moderation settings
moderation:
  mute_role: 000000000000000000
  default_mute_duration: 3600
  log_channel: 000000000000000000
  dm_on_action: true

# Bump settings
bumping:
  bump_channel: 000000000000000000
  reminder_channel: 000000000000000000
  bump_interval_hours: 2
  xp_reward: 20
  bump_role: null

# Role menu settings
role_menus:
  allowed_roles: []  # empty = all roles allowed
  max_selections_per_menu: 0  # 0 = unlimited

# Sticky message settings
sticky_messages:
  repost_after_messages: 5

# Thread management
thread_management:
  auto_archive_inactive_days: 7
  slowmode_default: 0
```

### Runtime Config Reload

The `/reload-config` command already exists and hot-reloads `config.yaml` without restarting the bot. Every cog that uses config should reference `self.bot.config` dynamically so changes take effect immediately.

### Database-Driven Config for Dynamic Features

Things that change frequently (role menus, auto-thread channels, counting channels, etc) are stored in the database:
- `auto_thread_configs` — per-channel threading settings
- `role_menus` + `role_menu_options` — role selection panels
- `counting_channels` — counting channel state
- `sticky_messages` — sticky message tracking

This lets staff configure without editing YAML.

---

## Implementation Order: A Sensible Bloody Plan

### Phase 1: Core Services (CRITICAL — bot won't start without these)

**Priority:** Blocking. Do first.

1. **`services/audit_logger.py`**
   - Methods: `log()`, with severity levels
   - Write to `audit_log` table
   - Optional webhook posting

2. **`services/embed_builder.py`**
   - Methods: `success()`, `error()`, `info()`, `warning()`, `custom()`
   - Consistent branding with footer/thumbnail

3. **`services/dm_service.py`**
   - Methods: `send_dm()`, `send_with_fallback()`
   - Retry logic, fallback channel posting
   - Log failures via AuditLogger

4. **`services/role_service.py`**
   - Methods: `add_role()`, `remove_role()`, `swap_roles()`
   - Permission error handling
   - Log all role changes via AuditLogger

5. **`services/content_filter.py`**
   - Methods: `validate_bio()`, `validate_reason()`, `check_profanity()`
   - Load slurs from `data/slurs.txt`
   - Use better-profanity library

6. **`services/timer_service.py`**
   - Methods: `schedule_timer()`, `cancel_timer()`, `start_polling()`, `stop_polling()`
   - 30s polling loop
   - Execute timer callbacks (nudge, unmute, etc)

7. **`services/welcome_generator.py`**
   - Methods: `generate_welcome(intro_data)`
   - Load templates from `data/welcome_templates.json`
   - Variable substitution

8. **`services/card_renderer.py`**
   - Methods: `render_rank_card()`, `render_leaderboard()`, `render_levelup()`, `render_achievement()`, `render_monthly_report()`, `render_welcome()`
   - Pillow-based image generation
   - Load fonts from `assets/fonts/` with fallback
   - Gradients, glass effects, progress bars

**Testing:** After Phase 1, bot should start without errors. All existing features should work.

---

### Phase 2: Essential Missing Features

**Priority:** High. These were supposed to be done already ffs.

1. **Moderation Suite** (`cogs/moderation.py`)
   - Commands: `/kick`, `/ban`, `/unban`, `/mute`, `/unmute`, `/warn`, `/warnings`, `/clear-warnings`
   - Database: `infractions` table
   - Integration with AuditLogger, DMService

2. **Role Management** (`cogs/role_management.py`)
   - Commands: `/role-create`, `/role-delete`, `/role-edit`, `/role-assign`, `/role-remove`, `/role-info`, `/role-members`
   - Use RoleService for all operations

3. **Channel Management** (`cogs/channel_management.py`)
   - Commands: `/channel-create`, `/channel-delete`, `/channel-edit`, `/channel-clone`, `/channel-lock`, `/channel-unlock`
   - Permission checks, confirmation modals for destructive actions

4. **General Sticky Messages** (extend `cogs/ticket_panel.py` or new `cogs/sticky.py`)
   - Commands: `/sticky`, `/sticky-create`, `/sticky-remove`, `/sticky-list`
   - Extend `sticky_messages` table

**Testing:** All admin/mod commands functional. Role/channel CRUD works.

---

### Phase 3: New Feature Set

**Priority:** Medium. New functionality requested.

1. **Birthday System** (`cogs/birthdays.py`)
   - Commands: `/birthday-set`, `/birthday-remove`, `/birthday-list`, `/birthday-check`
   - Database: `birthdays` table
   - Daily check task at midnight UTC
   - Birthday role auto-assign/remove

2. **Counting Channels** (`cogs/counting.py`)
   - Database: `counting_channels`, `counting_contributions`
   - Message listener for validation
   - Commands: `/counting-setup`, `/counting-reset`, `/counting-stats`
   - Delete invalid messages, track high scores

3. **Confessions** (`cogs/confessions.py`)
   - Commands: `/confess`, `/confess-ban`, `/confess-unban`
   - Database: `confessions` table
   - Approval queue with staff view
   - Anonymous posting with numbering

4. **Bump Tracking** (`cogs/bumping.py`)
   - Commands: `/bump`, `/bump-stats`
   - Database: `bump_tracking` table
   - 2h timer for reminders
   - XP rewards for bumping

**Testing:** All new features work independently. Config flags toggle them on/off.

---

### Phase 4: Advanced Features

**Priority:** Low. Nice-to-haves.

1. **Thread Management** (extend `cogs/auto_threads.py`)
   - Commands: `/thread-lock`, `/thread-unlock`, `/thread-archive`, `/thread-slowmode`, `/thread-block`, `/thread-unblock`
   - Database: `thread_blocks` table
   - Auto-archive inactive threads

2. **Role Selector Menus** (`cogs/role_menus.py`)
   - Commands: `/role-menu-create`, `/role-menu-delete`, `/role-menu-edit`
   - Database: `role_menus`, `role_menu_options`
   - Dynamic button view for role toggling
   - Persistent across restarts

3. **Auto-Reactions** (extend existing message listeners or new `cogs/auto_reactions.py`)
   - Config-driven: `auto_reactions` section in YAML maps channel IDs to emoji lists
   - React to messages in configured channels automatically
   - Ignore bot messages

**Testing:** All features complete. Full integration test.

---

### Phase 5: Polish & Documentation

1. **Update `BOT_DOCUMENTATION.md`**
   - Document all new commands
   - Add new config sections
   - Update feature list

2. **Create `.env.example`**
   - Template for environment variables
   - Comments explaining each variable

3. **Update `config.yaml`**
   - Add all new sections with sensible defaults
   - Comment every option

4. **Testing & Bug Fixes**
   - Full smoke test of every feature
   - Test config reload
   - Test feature flag toggling
   - Permission error handling

5. **Create deployment guide**
   - Installation steps
   - Discord bot setup
   - Config walkthrough
   - Troubleshooting

---

## Database Migrations Required

New tables needed (will add to `database/migrations/schema.sql`):

```sql
-- Birthdays
CREATE TABLE IF NOT EXISTS birthdays (
    user_id BIGINT PRIMARY KEY,
    birth_day INTEGER NOT NULL,
    birth_month INTEGER NOT NULL,
    birth_year INTEGER,  -- optional, for age display
    announced_year INTEGER,  -- track last year we announced
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Counting channels
CREATE TABLE IF NOT EXISTS counting_channels (
    channel_id BIGINT PRIMARY KEY,
    current_count INTEGER DEFAULT 0,
    high_score INTEGER DEFAULT 0,
    last_user_id BIGINT,
    reset_count INTEGER DEFAULT 0,
    prevent_double_counting BOOLEAN DEFAULT TRUE,
    delete_mistakes BOOLEAN DEFAULT TRUE,
    save_to_log BOOLEAN DEFAULT FALSE,
    log_channel_id BIGINT
);

CREATE TABLE IF NOT EXISTS counting_contributions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    count_contributed INTEGER DEFAULT 0,
    mistakes_made INTEGER DEFAULT 0,
    FOREIGN KEY (channel_id) REFERENCES counting_channels(channel_id)
);

-- Confessions
CREATE TABLE IF NOT EXISTS confessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id BIGINT NOT NULL,
    content TEXT NOT NULL,
    status TEXT DEFAULT 'pending',  -- pending, approved, rejected
    posted_message_id BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_by BIGINT,
    reviewed_at TIMESTAMP
);

-- Moderation infractions
CREATE TABLE IF NOT EXISTS infractions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id BIGINT NOT NULL,
    type TEXT NOT NULL,  -- warn, mute, kick, ban
    reason TEXT,
    moderator_id BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    active BOOLEAN DEFAULT TRUE
);

-- Role menus
CREATE TABLE IF NOT EXISTS role_menus (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    created_by BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS role_menu_options (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    menu_id INTEGER NOT NULL,
    role_id BIGINT NOT NULL,
    emoji TEXT NOT NULL,
    label TEXT NOT NULL,
    position INTEGER DEFAULT 0,
    FOREIGN KEY (menu_id) REFERENCES role_menus(id) ON DELETE CASCADE
);

-- Bump tracking
CREATE TABLE IF NOT EXISTS bump_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id BIGINT NOT NULL,
    bumped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    bump_type TEXT DEFAULT 'manual'  -- manual, disboard, other
);

-- Thread blocks
CREATE TABLE IF NOT EXISTS thread_blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    blocked_by BIGINT NOT NULL,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(thread_id, user_id)
);
```

---

## Summary: The Complete Feature Matrix

| Feature | Status | Phase | Cog/Service |
|---------|--------|-------|-------------|
| **EXISTING** |
| XP & Leveling | ✅ DONE | - | `cogs/xp.py` |
| Support Tickets | ✅ DONE | - | `cogs/tickets_member.py`, `tickets_staff.py`, `ticket_lifecycle.py` |
| Age Verification | ✅ DONE | - | `cogs/age_verify.py` |
| Introductions | ✅ DONE | - | `cogs/intros.py` |
| Achievements | ✅ DONE | - | `cogs/achievements.py` |
| Milestones | ✅ DONE | - | `cogs/milestones.py` |
| Monthly Stats | ✅ DONE | - | `cogs/monthly_stats.py` |
| Auto-Threading | ✅ DONE | - | `cogs/auto_threads.py` |
| Music Conversion | ✅ DONE | - | `cogs/music.py` |
| Bully Command | ✅ DONE | - | `cogs/bully.py` |
| Onboarding | ✅ DONE | - | `cogs/onboarding.py` |
| Rule Agreement | ✅ DONE | - | `cogs/onboarding.py` |
| Diagnostics | ✅ DONE | - | `cogs/diagnostics.py` |
| **CORE SERVICES** |
| AuditLogger | ❌ TODO | **Phase 1** | `services/audit_logger.py` |
| EmbedBuilder | ❌ TODO | **Phase 1** | `services/embed_builder.py` |
| DMService | ❌ TODO | **Phase 1** | `services/dm_service.py` |
| RoleService | ❌ TODO | **Phase 1** | `services/role_service.py` |
| ContentFilter | ❌ TODO | **Phase 1** | `services/content_filter.py` |
| TimerService | ❌ TODO | **Phase 1** | `services/timer_service.py` |
| WelcomeGenerator | ❌ TODO | **Phase 1** | `services/welcome_generator.py` |
| CardRenderer | ❌ TODO | **Phase 1** | `services/card_renderer.py` |
| **ESSENTIAL FEATURES** |
| Moderation (kick/ban/mute/warn) | ❌ TODO | **Phase 2** | `cogs/moderation.py` |
| Role Management Commands | ❌ TODO | **Phase 2** | `cogs/role_management.py` |
| Channel Management | ❌ TODO | **Phase 2** | `cogs/channel_management.py` |
| Sticky Messages (general) | ❌ TODO | **Phase 2** | `cogs/sticky.py` |
| **NEW FEATURES** |
| Birthday System | ❌ TODO | **Phase 3** | `cogs/birthdays.py` |
| Counting Channels | ❌ TODO | **Phase 3** | `cogs/counting.py` |
| Confessions | ❌ TODO | **Phase 3** | `cogs/confessions.py` |
| Bump Tracking | ❌ TODO | **Phase 3** | `cogs/bumping.py` |
| **ADVANCED FEATURES** |
| Thread Management | ❌ TODO | **Phase 4** | extend `cogs/auto_threads.py` |
| Role Selector Menus | ❌ TODO | **Phase 4** | `cogs/role_menus.py` |
| Auto-Reactions | ❌ TODO | **Phase 4** | `cogs/auto_reactions.py` |

---

## Final Thoughts

Right so that's the plan innit. Gonna be a proper comprehensive bot once this is all done. The architecture's solid, just need to actually finish the bloody thing.

**Estimated work:**
- Phase 1 (Core Services): ~2-3 days (critical path)
- Phase 2 (Essential): ~2 days
- Phase 3 (New Features): ~3 days
- Phase 4 (Advanced): ~2 days
- Phase 5 (Polish): ~1 day

**Total:** ~10-11 days of focused work, assuming no major catastrophes.

**Testing strategy:**
- Unit tests? Nah, we're living dangerously.
- Manual testing each phase before moving on.
- Full integration test at the end.
- Deploy to test server before production.

Let's bloody do this then.

---

*— written at 3am whilst slightly pissed, apologies for any bollocks*
