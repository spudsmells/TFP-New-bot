# The Gayborhood Bot — Documentation

A single Discord bot built to replace multiple existing bots. It handles onboarding, moderation, XP/leveling, tickets, introductions, achievements, monthly analytics, and more — all from one codebase.

---

## Table of Contents

1. [What the Bot Does](#what-the-bot-does)
2. [How It's Configured](#how-its-configured)
3. [All Slash Commands](#all-slash-commands)
4. [Button & Modal Interactions](#button--modal-interactions)
5. [Automatic Background Behavior](#automatic-background-behavior)
6. [Image Cards](#image-cards)
7. [Achievement System](#achievement-system)
8. [Monthly Stats & Reports](#monthly-stats--reports)
9. [Database Overview](#database-overview)
10. [Next Steps for Configuration](#next-steps-for-configuration)
11. [Next Steps for Development](#next-steps-for-development)

---

## What the Bot Does

The bot is organized into **15 independent features** (called cogs), each toggled on or off in config. Here's a plain-English summary of every feature:

### Onboarding (on by default)
When a new member joins the server, the bot assigns them a "Pending" role and DMs them the server rules with an "I Agree" button. If DMs are closed, it falls back to posting in a designated channel. Once agreed, the member can start their intro, open a support ticket, or request age verification. A welcome card image is posted in the welcome channel.

### Diagnostics (on by default)
Basic health commands: check the bot's ping, version, uptime, and reload the config file without restarting.

### XP System
Members earn XP from messages (10-20 XP per message, 60-second cooldown), voice chat (5 XP per minute), and receiving reactions on their messages (2 XP each, max 20 per message). XP determines your level using the formula `50 * level^2 + 50 * level`. The `/rank` command generates a visual image card showing your level, progress bar, rank, and stats. The `/leaderboard` command generates an image card of the top 10 members. Staff can give, take, set, reset, or bulk-import XP.

### Auto-Threads
Automatically creates discussion threads when someone posts media (images, videos, audio) or links in configured channels. Staff set up which channels get auto-threading and what triggers it.

### Introductions
New members fill out a 5-field modal (age, preferred name, pronouns, location, bio). The submission goes to a staff review channel where staff can approve, reject, kick, or ban. On approval, the member gets promoted from Pending to the main member role, receives a regional role based on their location (fuzzy-matched), gets a welcome message posted, and earns a 50 XP bonus. Members can submit up to 2 times if rejected.

### Bully Command
A fun command that sends a random friendly insult to a mentioned member. Rate-limited to prevent abuse (60-second cooldown). Staff can add, remove, toggle, and list insults. The bot detects abuse patterns (10+ uses in an hour triggers an alert).

### Music Conversion
Automatically detects Spotify, Apple Music, SoundCloud, Tidal, and Deezer links in messages and converts them to YouTube links so everyone can listen regardless of platform. Uses the Spotify API and yt-dlp. Rate-limited to 3 conversions per user per 10 minutes.

### Ticket System (3 cogs: Member, Staff, Lifecycle)
Members can open support tickets, which create private channels visible only to the member and staff. Staff can claim tickets, add other members, mute the ticket owner (30 minutes), and close tickets. Timers nudge members after 2 hours if they don't respond and remind staff after 12 hours about unclaimed tickets. Mutes auto-expire. Members can close their own tickets within 2 hours. Closed tickets get archived.

### Ticket Panel
A permanent "help desk" panel with 3 buttons (Start Intro, Open Support Ticket, Age Verification) that staff deploy to a channel. If the panel message gets deleted, the bot automatically reposts it.

### Age Verification
Members who reach Level 15 can request age verification. It creates a private ticket where they submit their ID for staff review. On approval, they get the Age Verified role and a 100 XP bonus.

### Milestones
When a member levels up, they receive a visual image card via DM showing their old level, new level, and any unlocks. The card is also posted in a configurable level-up channel. Milestone levels (5, 10, 15, 20, 25, 30, 40, 50, 75, 100) get special recognition.

### Achievements
An automatic badge/milestone system. Members earn achievements for reaching thresholds like 100 messages, Level 10, 1 hour of voice chat, etc. Each achievement has a rarity (Common, Rare, Epic, Legendary), an XP reward, and generates a visual image card when unlocked. Staff can also manually grant, revoke, create, and delete achievements. The bot ships with 29 pre-configured achievements.

### Monthly Stats
Tracks every message, edit, reaction, mention, and voice minute across the server. On the 1st of each month, it automatically generates a visual report card showing the winners in 10 categories: Most Messages, Most Active Days, Most Voice Time, Most @'d Member, Most Edits, Top Reactor, Longest Message, Most Popular Word, Most Reacted Image, and Most Active Channel. Winners get bonus XP. Stats are batched in memory and flushed to the database every 60 seconds for performance.

---

## How It's Configured

### Environment Variables (`.env` file)

| Variable | Required | Description |
|----------|----------|-------------|
| `DISCORD_TOKEN` | Yes | Your bot token from the Discord Developer Portal |
| `DISCORD_APP_ID` | Yes | Your application ID |
| `DATABASE_URL` | Yes | `sqlite:///bot.db` for SQLite, or a PostgreSQL URL |
| `SPOTIFY_CLIENT_ID` | No | For music link conversion |
| `SPOTIFY_CLIENT_SECRET` | No | For music link conversion |
| `YOUTUBE_API_KEY` | No | For music link conversion |
| `ENVIRONMENT` | No | `development` or `production` |

### Config File (`config.yaml`)

The config file controls everything the bot does. It can be hot-reloaded at runtime with `/reload-config`.

#### Guild & Roles

```yaml
guild_id: 000000000000000000     # Your server's ID

roles:
  pending: 000000000000000000    # Assigned to new members on join
  gaybor: 000000000000000000     # Main member role (given on intro approval)
  staff: 000000000000000000      # Staff role
  admin: 000000000000000000      # Admin role
  age_verified: 000000000000000000  # Given after age verification
  muted: 000000000000000000      # Applied during ticket mutes
  # Regional roles (auto-assigned from intro location):
  region_na_east: 000000000000000000
  region_na_west: 000000000000000000
  region_na_central: 000000000000000000
  region_eu: 000000000000000000
  region_uk: 000000000000000000
  region_oceania: 000000000000000000
  region_asia: 000000000000000000
  region_sa: 000000000000000000
  region_africa: 000000000000000000
  region_other: 000000000000000000
```

#### Channels

```yaml
channels:
  onboarding_fallback: 000000000000000000   # Used when DMs are closed
  staff_review: 000000000000000000          # Where intro submissions go for staff review
  welcome: 000000000000000000               # Where welcome cards are posted
  ticket_booth: 000000000000000000          # Where the help desk panel goes
  ticket_category: 000000000000000000       # Parent category for ticket channels
  ticket_archive_category: 000000000000000000  # Where closed tickets go
  staff_alerts: 000000000000000000          # Staff notifications
  bot_logs: 000000000000000000              # Bot activity logs
  levelup: 000000000000000000               # Level-up card announcements
```

#### Feature Flags

Every feature can be turned on/off independently. Set to `true` to enable, `false` to disable:

```yaml
features:
  diagnostics: true       # /ping, /version, /status, /reload-config
  onboarding: true        # Member join flow + rules DM
  xp: false               # XP system, /rank, /leaderboard
  auto_threads: false     # Auto-create threads for media/links
  intros: false           # Intro modal + staff review
  bully: false            # /bully command
  music: false            # Auto music link conversion
  tickets_member: false   # Member ticket creation
  tickets_staff: false    # Staff ticket commands
  age_verify: false       # Age verification flow
  ticket_lifecycle: false # Ticket nudge/mute timers
  ticket_panel: false     # Help desk panel
  milestones: false       # Level-up notifications + cards
  achievements: false     # Achievement system
  monthly_stats: false    # Monthly analytics + reports
```

#### XP Settings

```yaml
xp:
  message_min: 10                    # Min XP per message
  message_max: 20                    # Max XP per message
  message_cooldown_seconds: 60       # Wait time between XP awards
  voice_per_minute: 5                # XP per minute in voice
  reaction_xp: 2                     # XP per reaction (to message author)
  reaction_max_per_message: 20       # Cap reactions per message for XP
  intro_bonus: 50                    # Bonus XP when intro is approved
  age_verify_bonus: 100              # Bonus XP on age verification
  milestone_levels: [5, 10, 15, 20, 25, 30, 40, 50, 75, 100]
  age_verify_level: 15               # Required level for age verification
```

#### Threading Settings

```yaml
threading:
  max_threads_per_minute: 5          # Rate limit for thread creation
  default_name_format: "{username} - {file_type}"
  auto_archive_duration: 1440        # Minutes (24 hours)
```

#### Rate Limits

```yaml
rate_limits:
  bully_cooldown_seconds: 60         # Cooldown between /bully uses
  bully_abuse_threshold: 10          # Triggers staff alert
  bully_abuse_window_seconds: 3600   # Abuse detection window (1 hour)
  music_per_user: 3                  # Max music conversions per window
  music_window_seconds: 600          # Music rate limit window (10 min)
```

#### Ticket Settings

```yaml
tickets:
  member_nudge_hours: 2              # Nudge member if no response
  staff_reminder_hours: 12           # Remind staff about unclaimed tickets
  mute_default_minutes: 30           # Default mute duration
  member_close_window_hours: 2       # How long members can close their own ticket
```

#### Monthly Stats Settings

```yaml
monthly_stats:
  report_channel: 000000000000000000   # Where monthly reports are posted
  tracking_channels: []                 # Empty = track all channels
  excluded_channels: []                 # Channels to exclude from tracking
  batch_flush_seconds: 60              # How often in-memory stats flush to DB
  monthly_xp_rewards:                  # XP bonus for monthly winners
    most_messages: 500
    most_active_days: 500
    most_voice: 300
    most_mentioned: 200
    top_reactor: 200
```

#### Location Mapping

The `location_mapping` section maps keywords to regional roles. When a member writes "California" in their intro location, the bot fuzzy-matches it to `region_na_west` and assigns that role automatically.

---

## All Slash Commands

### Member Commands (everyone can use)

| Command | Description | Options |
|---------|-------------|---------|
| `/ping` | Check bot latency | None |
| `/version` | Show bot version | None |
| `/status` | Bot health check (uptime, latency, member count) | None |
| `/rank` | View your XP rank card | `member` (optional) — view someone else's |
| `/leaderboard` | View top 10 XP leaderboard | None |
| `/bully` | Send a friendly insult | `target` (required) — member to bully |
| `/achievements` | View unlocked achievements | `member` (optional) — view someone else's |
| `/achievement-list` | Browse all available achievements | None |
| `/monthly` | View current month's server stats or a member's stats | `member` (optional) |
| `/stats-channel` | View stats for a specific channel | `channel` (required) |

### Staff Commands (requires `manage_roles` or `manage_messages`)

| Command | Permission | Description | Options |
|---------|------------|-------------|---------|
| `/xp-give` | manage_roles | Give XP to a member | `member`, `amount` (1-10,000), `reason` (optional) |
| `/xp-take` | manage_roles | Remove XP from a member | `member`, `amount` (1-10,000), `reason` (optional) |
| `/ticket-create` | manage_messages | Open a ticket for a member | `member` |
| `/ticket-add` | manage_messages | Add a member to current ticket | `member` |
| `/ticket-list` | manage_messages | List all open tickets | None |
| `/bully-add` | manage_messages | Add a new insult | `text` (use `{target}` for mention) |
| `/bully-remove` | manage_messages | Remove an insult | `insult_id` |
| `/bully-list` | manage_messages | List all insults | None |
| `/bully-toggle` | manage_messages | Toggle insult active/inactive | `insult_id` |
| `/achievement-grant` | manage_roles | Grant an achievement | `member`, `key` |
| `/achievement-revoke` | manage_roles | Revoke an achievement | `member`, `key` |
| `/monthly-recap` | manage_roles | Regenerate last month's report | None |
| `/thread-setup` | manage_channels | Enable auto-threading | `channel`, `trigger_media`, `trigger_links`, `trigger_youtube`, `name_format` |
| `/thread-disable` | manage_channels | Disable auto-threading | `channel` |
| `/thread-enable` | manage_channels | Re-enable auto-threading | `channel` |
| `/thread-list` | manage_channels | List auto-thread configs | None |

### Admin Commands (requires `administrator`)

| Command | Description | Options |
|---------|-------------|---------|
| `/reload-config` | Hot-reload config.yaml | None |
| `/xp-set` | Set a member's total XP | `member`, `total_xp` (0-1,000,000) |
| `/xp-reset` | Reset a member's XP to 0 | `member` |
| `/xp-import` | Bulk import XP from CSV/JSON | `file` (attachment) |
| `/panel-deploy` | Deploy the help desk panel | `channel` (optional) |
| `/achievement-create` | Create a new achievement | `key`, `name`, `description`, `trigger_type`, `trigger_value`, `rarity`, `xp_reward` |
| `/achievement-delete` | Delete an achievement | `key` |

---

## Button & Modal Interactions

These are not slash commands — they're buttons and forms that appear in messages.

### Onboarding DM (sent to new members)
- **"I Agree to the Rules"** — Accepts rules, enables other buttons
- **"Start Intro"** — Opens the intro form
- **"Support Ticket"** — Creates a support ticket
- **"Age Verify"** — Starts age verification (if eligible)

### Intro Modal (form)
Five fields: Age (must be 18+), Preferred Name, Pronouns, Location, Bio (30-400 characters)

### Staff Intro Review (buttons per submission)
- **Approve** — Promotes member, assigns roles, posts welcome, awards XP
- **Reject** — Prompts for reason, member can resubmit (max 2 attempts)
- **Reject & Request Info** — Detailed rejection with info request
- **Kick** — Kicks member from server
- **Ban** — Bans member from server

### Ticket Channel (buttons in every ticket)
- **Claim Ticket** — Staff takes ownership
- **Close Ticket** — Archives the ticket (members have a 2-hour window to close their own)
- **Mute Member** — Mutes ticket owner for 30 minutes (toggleable)

### Help Desk Panel (permanent panel)
- **Open Support Ticket** — Creates a member ticket
- **Start Intro** — Opens the intro form
- **Age Verification** — Starts age verification

---

## Automatic Background Behavior

These things happen without anyone running a command:

| What Happens | When | How Often |
|---|---|---|
| XP from messages | Every message (after 60s cooldown) | Every message |
| XP from voice chat | Every minute in a voice channel | Every 60 seconds |
| XP from reactions | When someone reacts to a message | Every reaction (max 20/msg) |
| Auto-threading | When media/links posted in configured channels | Every qualifying message |
| Music link conversion | When a Spotify/Apple Music/etc. link is posted | Every qualifying message |
| Welcome card | When a new member joins | Every join |
| Level-up card | When a member reaches a new level | Every level-up |
| Achievement checks | On level-up + every 5 minutes for top 50 users | Ongoing |
| Ticket nudge | 2 hours after ticket opens with no staff claim | Once per ticket |
| Staff reminder | 12 hours after staff ticket with no claim | Once per ticket |
| Mute auto-expire | 30 minutes after mute is applied | Once per mute |
| Stats batch flush | Every 60 seconds | Continuous |
| Monthly report | 1st of every month at midnight UTC | Monthly |
| Ticket panel repost | When the panel message is deleted | On delete |

---

## Image Cards

The bot generates 6 types of visual image cards using Pillow. All cards have a dark theme with gradient backgrounds, glass-effect panels, and the server's pink/purple/gold color scheme.

| Card | Size | When Generated |
|------|------|----------------|
| **Rank Card** | 934 x 282 | `/rank` command |
| **Leaderboard Card** | 800 x variable | `/leaderboard` command |
| **Level-Up Card** | 800 x 250 | On level-up (DM + channel) |
| **Welcome Card** | 1024 x 400 | On member join |
| **Achievement Card** | 800 x 200 | On achievement unlock (DM + channel) |
| **Monthly Stats Card** | ~1200 x variable | 1st of month or `/monthly-recap` |

**Font setup**: Download the Inter font family from https://fonts.google.com/specimen/Inter and place `Inter-Regular.ttf`, `Inter-SemiBold.ttf`, `Inter-Bold.ttf`, and `Inter-ExtraBold.ttf` in `assets/fonts/`. The bot falls back to system fonts if these are missing.

---

## Achievement System

### How It Works
Achievements are automatically checked when a member levels up, hits a milestone, or during a 5-minute periodic scan of the top 50 active users. When earned, the member receives a DM with an image card and the event is posted in the bot logs channel.

### Pre-Configured Achievements (29 total)

**Social (Messages)**
| Achievement | Threshold | Rarity | XP Reward |
|-------------|-----------|--------|-----------|
| Chatty | 100 messages | Common | 50 |
| Chatterbox | 500 messages | Common | 100 |
| Motor Mouth | 1,000 messages | Rare | 200 |
| Keyboard Warrior | 5,000 messages | Epic | 500 |
| Chat Legend | 10,000 messages | Legendary | 1,000 |

**XP (Levels)**
| Achievement | Threshold | Rarity | XP Reward |
|-------------|-----------|--------|-----------|
| Getting Started | Level 5 | Common | 25 |
| Rising Star | Level 10 | Common | 50 |
| Dedicated | Level 25 | Rare | 150 |
| Veteran | Level 50 | Epic | 500 |
| Gayborhood Legend | Level 100 | Legendary | 2,000 |

**Voice Chat**
| Achievement | Threshold | Rarity | XP Reward |
|-------------|-----------|--------|-----------|
| Voice Debut | 1 hour | Common | 50 |
| Voice Regular | 5 hours | Common | 100 |
| Voice Addict | ~17 hours | Rare | 250 |
| Voice Legend | ~83 hours | Epic | 750 |
| Always On Mic | ~167 hours | Legendary | 1,500 |

**Reactions**
| Achievement | Threshold | Rarity | XP Reward |
|-------------|-----------|--------|-----------|
| Thumbs Up | 50 reactions | Common | 25 |
| Emote Enthusiast | 200 reactions | Common | 75 |
| Reaction King | 500 reactions | Rare | 150 |
| React Master | 1,000 reactions | Epic | 400 |

**Activity**
| Achievement | Threshold | Rarity | XP Reward |
|-------------|-----------|--------|-----------|
| Weekly Regular | 7 days | Common | 50 |
| Monthly Fixture | 30 days | Rare | 200 |
| Quarter Veteran | 90 days | Epic | 500 |
| Year-Round Gaybor | 365 days | Legendary | 2,000 |

**Staff**
| Achievement | Threshold | Rarity | XP Reward |
|-------------|-----------|--------|-----------|
| Welcome Wagon | 10 intros reviewed | Rare | 200 |
| Gatekeeper | 50 intros reviewed | Epic | 500 |
| Helpful Hand | 5 tickets closed | Rare | 150 |
| Support Hero | 25 tickets closed | Epic | 500 |
| Ticket Machine | 50 tickets closed | Legendary | 1,000 |

**Special**
| Achievement | Threshold | Rarity | XP Reward |
|-------------|-----------|--------|-----------|
| Verified | Complete age verification | Common | 100 |

### Trigger Types for Custom Achievements
When creating achievements with `/achievement-create`, these are the valid `trigger_type` values:
- `messages_sent` — Total messages sent
- `level_reached` — XP level reached
- `vc_minutes` — Total voice chat minutes
- `days_active` — Total days with activity
- `reactions_given` — Total reactions given
- `intros_reviewed` — Intros reviewed (staff)
- `tickets_closed` — Tickets closed (staff)
- `age_verified` — Age verification completed (set trigger_value to 1)
- `consecutive_days` — Consecutive days active
- `unique_channels` — Unique channels posted in

---

## Monthly Stats & Reports

### What's Tracked
Every message, edit, reaction, mention, and voice minute in the server is tracked. Data is accumulated in memory and flushed to the database every 60 seconds for performance.

### Monthly Report Categories
On the 1st of each month, the bot generates a report card with these 10 categories:

| Category | What It Measures |
|----------|------------------|
| Most Messages | Total messages sent in the month |
| Most Active Days | Days with at least 1 message |
| Most Voice Time | Total minutes in voice chat |
| Most @'d Member | Times mentioned by other members |
| Most Edits | Messages edited |
| Top Reactor | Reactions given to other messages |
| Longest Message | Single message with the most characters |
| Most Popular Word | Most-used word (excluding common words) |
| Most Reacted Image | Image attachment with the most reactions |
| Most Active Channel | Channel with the most messages |

### XP Rewards for Monthly Winners
Winners in each category get bonus XP (configurable in config.yaml):
- Most Messages: 500 XP
- Most Active Days: 500 XP
- Most Voice Time: 300 XP
- Most @'d Member: 200 XP
- Top Reactor: 200 XP

---

## Database Overview

The bot uses SQLite by default (or PostgreSQL if configured). It creates and manages 25 tables automatically on startup:

| Table | Purpose |
|-------|---------|
| `users` | Member profiles, XP, level, status, verification |
| `xp_history` | Every XP award with source and timestamp |
| `intros` | Intro submissions, review status, staff actions |
| `tickets` | Ticket channels, status, claims, mutes |
| `ticket_logs` | Every ticket event (created, claimed, closed, etc.) |
| `bully_insults` | Insult text, active status |
| `bully_usage` | Who bullied whom and when |
| `music_conversions` | Cached music link conversions |
| `auto_thread_configs` | Per-channel threading settings |
| `rule_acknowledgements` | Who agreed to rules and when |
| `milestones` | Recorded milestone levels per user |
| `timers` | Persistent timers (nudges, reminders, mute expiry) |
| `audit_log` | All significant bot actions |
| `achievements` | Achievement definitions and thresholds |
| `user_achievements` | Which users unlocked which achievements |
| `daily_stats` | Per-user daily message/voice/reaction counts |
| `message_tracking` | Per-message metadata (char count, attachments, reactions) |
| `channel_stats` | Per-channel daily message counts |
| `monthly_reports` | Generated monthly report data (JSON) |
| `word_frequency` | Per-day word usage counts |
| `mention_tracking` | Per-day mention counts |
| `sticky_messages` | Persistent panel messages |
| `schema_version` | Migration version tracking |

---

## Next Steps for Configuration

### 1. Set Up Your `.env` File
Copy `.env.example` to `.env` and fill in your Discord token, app ID, and database URL.

### 2. Fill In All IDs in `config.yaml`
Replace every `000000000000000000` with actual Discord role and channel IDs from your server. You need:
- Your server's guild ID
- Role IDs for: Pending, Gaybor (member), Staff, Admin, Age Verified, Muted, and all regional roles
- Channel IDs for: onboarding fallback, staff review, welcome, ticket booth, ticket category, ticket archive category, staff alerts, bot logs, level-up, and monthly report

### 3. Enable Features Gradually
Start with the defaults (`diagnostics` and `onboarding`), then enable features one at a time:
1. Enable `xp` first to get leveling working
2. Enable `milestones` for level-up notifications
3. Enable `intros` and configure the staff review channel
4. Enable `tickets_member`, `tickets_staff`, `ticket_lifecycle`, and `ticket_panel` together
5. Enable `achievements` once XP is flowing
6. Enable `monthly_stats` once the server is active
7. Enable `bully`, `music`, `auto_threads`, and `age_verify` as desired

### 4. Download Fonts (Optional)
Download Inter from https://fonts.google.com/specimen/Inter and place the `.ttf` files in `assets/fonts/` for the best-looking image cards. The bot works without them but uses fallback fonts.

### 5. Install Dependencies
```bash
pip install -r requirements.txt
```
Required: `discord.py>=2.4.0`, `aiohttp>=3.9.0`, `aiosqlite>=0.19.0`, `pyyaml>=6.0`, `python-dotenv>=1.0.0`, `better-profanity>=0.7.0`, `rapidfuzz>=3.0.0`, `Pillow>=10.0.0`

Optional: `asyncpg>=0.29.0` (for PostgreSQL), `yt-dlp>=2024.1.0` (for music conversion)

### 6. Run the Bot
```bash
python bot.py
```
Or use the included startup script: `bash scripts/run.sh`

---

## Next Steps for Development

Here are ideas for further development, roughly ordered by impact:

### High Priority
- **Personal stats cards** — `/stats` command generating an image card with a member's all-time stats (messages, voice, achievements, join date, etc.)
- **Weekly mini-reports** — Shorter weekly digest posted automatically
- **Streak tracking** — Track consecutive-day activity streaks and integrate with achievements (the `consecutive_days` trigger type exists but isn't actively computed yet)
- **Unique channels achievement** — Track how many different channels a member has posted in (the `unique_channels` trigger type exists but isn't actively computed yet)

### Medium Priority
- **Reaction leaderboard** — Track who receives the most reactions (not just who gives them)
- **Custom achievement icons** — Upload actual `.png` icons for each achievement instead of text emoji
- **Achievement progress tracking** — Show "You're 73% of the way to Chatterbox (365/500 messages)" in `/achievements`
- **Paginated views** — Add pagination buttons for `/achievements`, `/achievement-list`, and `/leaderboard` when there are many entries
- **Intro rewrite** — Allow members to update their intro after approval (with staff re-review)

### Lower Priority / Nice-to-Have
- **Server-wide stats dashboard** — A `/stats-server` command showing total messages, active members, growth over time
- **Birthday system** — Track member birthdays and post celebrations
- **Custom welcome backgrounds** — Allow staff to upload custom background images for welcome cards
- **Satisfaction surveys** — After a ticket is closed, DM the member a satisfaction survey (the database table already exists)
- **Ticket transcripts** — Generate and save full ticket conversation transcripts on close
- **Webhook-based audit logging** — Send audit logs to a Discord channel via webhook for real-time monitoring
- **Role rewards** — Automatically assign vanity roles at certain levels (e.g., Level 20 gets a custom color role)
- **Anti-spam** — Rate-limit message sending per user and auto-mute spammers
- **Scheduled announcements** — Staff can schedule messages to post at specific times
- **Music playlists** — Aggregate all converted music links into a weekly playlist
