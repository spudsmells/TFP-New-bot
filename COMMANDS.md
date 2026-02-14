# The Gayborhood Bot - Complete Command & Feature Guide

> A comprehensive cheat sheet for all bot features, slash commands, and systems

---

## 📋 Table of Contents

1. [Moderation Commands](#moderation-commands)
2. [Role Management](#role-management)
3. [Channel Management](#channel-management)
4. [Sticky Messages](#sticky-messages)
5. [Birthday System](#birthday-system)
6. [Counting Game](#counting-game)
7. [Confessions System](#confessions-system)
8. [Bump Reminders](#bump-reminders)
9. [XP & Leveling](#xp--leveling)
10. [Achievements](#achievements)
11. [Intro System](#intro-system)
12. [Tickets](#tickets)
13. [Diagnostics](#diagnostics)
14. [Configuration](#configuration)

---

## 🔨 Moderation Commands

### `/kick`
**Kick a member from the server**

- **Permission Required:** `Kick Members`
- **Parameters:**
  - `member` - The member to kick
  - `reason` (optional) - Reason for kicking (will be DMed to member)

**Example:**
```
/kick member:@BadUser reason:Spamming in general chat
```

**Features:**
- Attempts to DM the member before kicking
- Role hierarchy checks (can't kick higher roles)
- Audit logging
- Notifies if DM fails

---

### `/ban`
**Ban a member from the server**

- **Permission Required:** `Ban Members`
- **Parameters:**
  - `member` - The member to ban
  - `reason` (optional) - Reason for banning
  - `delete_days` (optional) - Days of messages to delete (0-7, default: 0)

**Example:**
```
/ban member:@Troll reason:Repeated harassment delete_days:7
```

**Features:**
- Attempts to DM member with appeal info
- Deletes message history if requested
- Role hierarchy checks
- Audit logging

---

### `/unban`
**Unban a user from the server**

- **Permission Required:** `Ban Members`
- **Parameters:**
  - `user_id` - The Discord user ID to unban
  - `reason` (optional) - Reason for unbanning

**Example:**
```
/unban user_id:123456789012345678 reason:Appeal approved
```

---

### `/mute` (Timeout)
**Timeout a member temporarily**

- **Permission Required:** `Moderate Members`
- **Parameters:**
  - `member` - The member to timeout
  - `duration` - Duration in minutes (1-40320, max 28 days)
  - `reason` (optional) - Reason for timeout

**Example:**
```
/mute member:@Annoying duration:60 reason:Spamming reactions
```

**Features:**
- Uses Discord's native timeout feature
- DMs member with duration
- Auto-expires after duration
- Nice time formatting (converts minutes to hours/days)

---

### `/unmute`
**Remove timeout from a member**

- **Permission Required:** `Moderate Members`
- **Parameters:**
  - `member` - The member to unmute
  - `reason` (optional) - Reason for removing timeout

**Example:**
```
/unmute member:@Reformed reason:Apologized in modmail
```

---

### `/warn`
**Warn a member (DM + audit log)**

- **Permission Required:** `Kick Members`
- **Parameters:**
  - `member` - The member to warn
  - `reason` - Warning message (required)

**Example:**
```
/warn member:@Newbie reason:Please don't use slurs, review the rules
```

**Features:**
- Sends formal warning DM to member
- Logs to audit trail
- Notifies if DM delivery fails

---

## 👥 Role Management

### `/addrole`
**Add a role to a member**

- **Permission Required:** `Manage Roles`
- **Parameters:**
  - `member` - The member to add role to
  - `role` - The role to add

**Example:**
```
/addrole member:@NewMember role:@Verified
```

**Features:**
- Role hierarchy validation
- Uses RoleService for safe operations
- Audit logging
- Prevents duplicate role assignment

---

### `/removerole`
**Remove a role from a member**

- **Permission Required:** `Manage Roles`
- **Parameters:**
  - `member` - The member to remove role from
  - `role` - The role to remove

**Example:**
```
/removerole member:@ExMod role:@Moderator
```

---

### `/listroles`
**List all roles or roles for a specific member**

- **Permission Required:** None
- **Parameters:**
  - `member` (optional) - Show roles for this member (omit for all server roles)

**Examples:**
```
/listroles                    # Show all server roles
/listroles member:@Someone    # Show Someone's roles
```

**Features:**
- Shows member count for each role
- Sorted by role hierarchy
- Automatically splits into multiple messages if too many roles

---

### `/roleinfo`
**Get detailed information about a role**

- **Permission Required:** None
- **Parameters:**
  - `role` - The role to get info about

**Example:**
```
/roleinfo role:@Moderator
```

**Shows:**
- Role ID and position
- Member count
- Colour (hex code)
- Attributes (hoisted, mentionable, managed)
- Creation date
- Notable permissions

---

## 📢 Channel Management

### `/slowmode`
**Set slowmode delay for a channel**

- **Permission Required:** `Manage Channels`
- **Parameters:**
  - `seconds` - Delay in seconds (0 to disable, max 21600 = 6 hours)
  - `channel` (optional) - Target channel (defaults to current)

**Examples:**
```
/slowmode seconds:10              # 10s slowmode in current channel
/slowmode seconds:0               # Disable slowmode
/slowmode seconds:300 channel:#general   # 5min slowmode in #general
```

**Features:**
- Nice time formatting in confirmation
- Audit logging
- Can be set on any text channel

---

### `/lock`
**Lock a channel (prevent @everyone from sending messages)**

- **Permission Required:** `Manage Channels`
- **Parameters:**
  - `channel` (optional) - Channel to lock (defaults to current)
  - `reason` (optional) - Reason for locking

**Example:**
```
/lock reason:Emergency situation - please stand by
```

**Features:**
- Denies send_messages permission for @everyone
- Posts lock notification embed in channel
- Audit logging
- Checks if already locked

---

### `/unlock`
**Unlock a channel**

- **Permission Required:** `Manage Channels`
- **Parameters:**
  - `channel` (optional) - Channel to unlock (defaults to current)
  - `reason` (optional) - Reason for unlocking

**Example:**
```
/unlock reason:Situation resolved
```

**Features:**
- Removes send_messages override
- Posts unlock notification embed
- Audit logging

---

### `/purge`
**Delete multiple messages in a channel**

- **Permission Required:** `Manage Messages`
- **Parameters:**
  - `amount` - Number of messages to delete (1-100)
  - `user` (optional) - Only delete messages from this user

**Examples:**
```
/purge amount:50                      # Delete last 50 messages
/purge amount:20 user:@Spammer        # Delete last 20 messages from @Spammer
```

**Features:**
- Deferred response (takes time to process)
- Audit logging with count
- Works only on messages < 14 days old (Discord limitation)

---

## 📌 Sticky Messages

Sticky messages automatically repost to stay at the bottom of a channel.

### `/sticky-set`
**Set a sticky message for current channel**

- **Permission Required:** `Manage Channels`
- **Parameters:**
  - `embed_type` - Type: `rules`, `welcome`, `info`, or `custom`
  - `title` (optional) - Custom title (required for custom type)
  - `description` (optional) - Custom description (required for custom type)

**Examples:**
```
/sticky-set embed_type:rules
/sticky-set embed_type:custom title:Important! description:Read this
```

**Predefined Types:**
- `rules` - Server rules reminder
- `welcome` - Welcome message
- `info` - General information
- `custom` - Your own title/description

**How it works:**
- Message automatically reposts when anyone sends a message
- Old sticky is deleted, new one is posted at bottom
- Survives bot restarts (database-backed)

---

### `/sticky-remove`
**Remove sticky message from current channel**

- **Permission Required:** `Manage Channels`

**Example:**
```
/sticky-remove
```

---

### `/sticky-list`
**List all sticky messages in the server**

- **Permission Required:** `Manage Channels`

**Example:**
```
/sticky-list
```

**Shows:**
- Channel, embed type, and message ID for each sticky

---

## 🎂 Birthday System

Track member birthdays with automatic announcements!

### `/birthday-set`
**Set your birthday**

- **Permission Required:** None
- **Parameters:**
  - `month` - Birth month (1-12)
  - `day` - Birth day (1-31)
  - `year` (optional) - Birth year (used to calculate age)

**Examples:**
```
/birthday-set month:3 day:15           # March 15 (no age shown)
/birthday-set month:7 day:4 year:1995  # July 4, 1995 (shows age)
```

**Features:**
- Automatic birthday announcements (hourly check)
- Optional age calculation if year provided
- Privacy-friendly (year is optional)
- DM notification on your birthday

---

### `/birthday-remove`
**Remove your birthday**

**Example:**
```
/birthday-remove
```

---

### `/birthday-toggle`
**Toggle birthday announcements on/off**

Keeps your birthday saved but disables/enables public announcements.

**Example:**
```
/birthday-toggle
```

---

### `/birthday-list`
**List upcoming birthdays**

Shows next 10 birthdays sorted by upcoming date.

**Example:**
```
/birthday-list
```

**Shows:**
- Display name
- Birthday date
- Days until birthday
- Age they'll turn (if year provided)

---

## 🔢 Counting Game

Count to infinity sequentially without messing up!

### How It Works

1. **Setup:** Configure a counting channel in `config.yaml`:
   ```yaml
   features:
     counting_channels:
       - 123456789012345678  # Channel ID
   ```

2. **Rules:**
   - Count sequentially: 1, 2, 3, 4, ...
   - Can't count twice in a row
   - Message must contain the correct number
   - Can include text: "1 let's go!" or just "1"

3. **Reactions:**
   - ✅ on correct number
   - ❌ on fail (message deleted)
   - 💯 at 100, 200, 300, etc.
   - 🎉 at 1000, 2000, 3000, etc.

4. **Fails Reset:**
   - Wrong number → reset to 0
   - Same user twice → reset to 0
   - No number in message → reset to 0

---

### `/counting-stats`
**Show counting statistics**

**Example:**
```
/counting-stats
```

**Shows:**
- Current count
- Highest count ever reached
- Total fails
- Last person who counted

---

### `/counting-reset`
**Reset counting stats (Staff only)**

- **Permission Required:** `Manage Channels`

**Example:**
```
/counting-reset
```

Resets current count and highest count to 0.

---

## 💭 Confessions System

Anonymous confessions with staff moderation!

### `/confess`
**Submit an anonymous confession**

- **Parameters:**
  - `confession` - Your confession (10-1000 characters)

**Example:**
```
/confess confession:I secretly love pineapple on pizza
```

**How it works:**

1. **User submits confession** → Validated for content
2. **Sent to staff review channel** with ✅/❌ reaction buttons
3. **Staff reviews:**
   - ✅ = Approved → Posted anonymously with number
   - ❌ = Rejected → Not posted
4. **User gets DM** notification (approved/rejected)
5. **If approved:** Posted in confessions channel as "Confession #X"

**Content Validation:**
- Length: 10-1000 characters
- No slurs (checked against `data/slurs.txt`)
- Moderate profanity check

**Configuration Required:**
```yaml
channels:
  confession_review: 123456789  # Staff review channel
  confessions: 987654321        # Public confessions channel
```

---

### `/confession-stats`
**Show confession statistics**

- **Permission Required:** `Manage Messages`

**Example:**
```
/confession-stats
```

**Shows:**
- Pending review count
- Total approved count

---

## 📣 Bump Reminders

Track server bumps and get reminders!

### How It Works

**Automatic Detection:**
- Bot detects when someone uses `/bump` (Disboard)
- Records bump in database
- Thanks the bumper
- Sets 2-hour reminder

**After 2 Hours:**
- Posts reminder in configured channel
- Mentions bump reminder role (if configured)
- Resets ready for next bump

**Configuration:**
```yaml
channels:
  bump_reminders: 123456789  # Where to post reminders

roles:
  bump_reminder: 987654321   # Role to ping (optional)
```

---

### `/bump-stats`
**Show server bump statistics**

**Example:**
```
/bump-stats
```

**Shows:**
- Total bumps
- Top 10 bumpers
- Time until next bump available

---

### `/bump-leaderboard`
**Show full bump leaderboard**

**Example:**
```
/bump-leaderboard
```

**Shows:**
- Top 20 bumpers
- 🥇🥈🥉 medals for top 3
- Bump counts

---

## ⭐ XP & Leveling

Earn XP and level up through participation!

### How to Earn XP

- **Messages:** 5-15 XP per message (60s cooldown)
- **Voice Chat:** XP per minute in VC
- **Intro Approval:** 100 XP bonus
- **Achievements:** Varies by achievement

### `/rank`
**Check your or someone's rank**

- **Parameters:**
  - `member` (optional) - Check this member's rank

**Examples:**
```
/rank              # Your rank
/rank member:@Someone   # Someone's rank
```

**Shows:**
- Current level and XP
- Progress to next level (progress bar)
- Server rank
- Message count and VC time
- Total XP

---

### `/leaderboard`
**View server XP leaderboard**

- **Parameters:**
  - `page` (optional) - Page number (default: 1)

**Example:**
```
/leaderboard
/leaderboard page:2
```

**Shows:**
- Top members by XP
- Level and total XP for each
- 🥇🥈🥉 for top 3

---

### `/give-xp`
**Manually give/remove XP (Staff)**

- **Permission Required:** `Manage Guild`
- **Parameters:**
  - `member` - Member to modify XP for
  - `amount` - XP amount (negative to remove)
  - `reason` - Reason for modification

**Example:**
```
/give-xp member:@EventWinner amount:500 reason:Won trivia night
```

---

## 🏆 Achievements

Unlock achievements for milestones and special actions!

### `/achievements`
**View your achievements**

**Example:**
```
/achievements
```

**Shows:**
- Unlocked achievements with icons
- Progress on locked achievements
- Rarity (common/rare/epic/legendary)

---

### `/achievement-info`
**Get info about a specific achievement**

- **Parameters:**
  - `achievement` - Achievement name or key

**Example:**
```
/achievement-info achievement:first_message
```

---

### Achievement Types

Achievements trigger automatically:

- **Message Milestones:** 100, 500, 1000, 5000 messages
- **Level Milestones:** Reach certain levels
- **Voice Activity:** Time in voice chat
- **Social:** React to messages, get reactions
- **Special:** Secret/hidden achievements

---

## 📝 Intro System

New member introduction workflow.

### User Commands

#### `/intro`
**Submit your introduction**

Opens modal with fields:
- Age
- Preferred name
- Pronouns
- Location
- Bio

**Features:**
- Bio validated (30-400 chars, no slurs/excessive profanity)
- Can resubmit if rejected
- Tracks submission number

---

### Staff Commands

#### `/intro-review`
**Review pending introductions**

- **Permission Required:** `Manage Messages`

**Shows:**
- List of pending intros
- Approval/rejection buttons

---

#### `/intro-approve`
**Approve an introduction**

- **Permission Required:** `Manage Messages`
- **Parameters:**
  - `user` - Member whose intro to approve

**Actions:**
1. Posts welcome card in welcome channel
2. Posts intro in intros channel
3. Adds regional role (if location matched)
4. Swaps Pending → Gaybor role
5. Grants 100 XP bonus
6. DMs member confirmation

---

#### `/intro-reject`
**Reject an introduction**

- **Permission Required:** `Manage Messages`
- **Parameters:**
  - `user` - Member whose intro to reject
  - `reason` - Rejection reason (sent to member)

**Actions:**
1. DMs member with reason
2. Allows resubmission
3. Logs rejection

---

## 🎫 Tickets

Support ticket system for members.

### Member Commands

#### `/ticket`
**Open a support ticket**

- **Parameters:**
  - `reason` - Why you need help (10-500 chars)

**Creates:**
- Private channel with member + staff
- Staff notification in alerts channel
- Auto-schedules nudge timer (2h)
- Auto-schedules staff reminder (12h if unclaimed)

---

#### `/ticket-close`
**Close your ticket**

Only works in ticket channels you own.

**Actions:**
1. Asks for confirmation
2. Closes ticket
3. Optionally sends satisfaction survey

---

### Staff Commands

#### `/ticket-claim`
**Claim a ticket**

- **Permission Required:** Ticket Staff role

Assigns ticket to you, notifies member.

---

#### `/ticket-unclaim`
**Unclaim a ticket**

- **Permission Required:** Ticket Staff role

Removes assignment.

---

#### `/ticket-add` / `/ticket-remove`
**Add/remove users from ticket**

- **Permission Required:** Ticket Staff role
- **Parameters:**
  - `member` - Member to add/remove

---

#### `/ticket-mute` / `/ticket-unmute`
**Temporarily mute/unmute ticket owner**

- **Permission Required:** Ticket Staff role
- **Parameters:**
  - `duration` (for mute) - Duration in minutes

Prevents member from sending messages in their ticket.

---

## 🔧 Diagnostics

### `/ping`
**Check bot latency**

**Example:**
```
/ping
```

Shows latency in milliseconds.

---

### `/version`
**Show bot version**

**Example:**
```
/version
```

---

### `/status`
**Bot health check**

**Example:**
```
/status
```

**Shows:**
- Uptime
- Latency
- Member count
- Database status
- Cogs loaded
- Version

---

### `/reload-config`
**Hot-reload config.yaml**

- **Permission Required:** `Administrator`

**Example:**
```
/reload-config
```

Reloads config without restarting bot.

---

## ⚙️ Configuration

### Required Config Sections

#### Channels
```yaml
channels:
  # Birthdays
  birthday_announcements: 123456789

  # Confessions
  confession_review: 123456789      # Staff review
  confessions: 123456789            # Public posts

  # Bump
  bump_reminders: 123456789

  # General
  onboarding_fallback: 123456789    # DM fallback channel
  staff_alerts: 123456789           # Staff notifications
```

#### Roles
```yaml
roles:
  bump_reminder: 123456789  # Pinged for bump reminders (optional)
```

#### Features
```yaml
features:
  counting_channels:
    - 123456789  # Channel ID for counting game
    - 987654321  # Can have multiple
```

#### Embeds
```yaml
embeds:
  footer_text: "The Gayborhood Bot"
  thumbnail_url: "https://example.com/logo.png"  # Optional
```

---

## 📊 Permission Reference

| Command | Permission Required |
|---------|-------------------|
| `/kick` | Kick Members |
| `/ban` / `/unban` | Ban Members |
| `/mute` / `/unmute` | Moderate Members |
| `/warn` | Kick Members |
| `/addrole` / `/removerole` | Manage Roles |
| `/slowmode` / `/lock` / `/unlock` | Manage Channels |
| `/purge` | Manage Messages |
| `/sticky-*` | Manage Channels |
| `/counting-reset` | Manage Channels |
| `/confession-stats` | Manage Messages |
| `/reload-config` | Administrator |

All other commands require no special permissions!

---

## 🎨 Embed Colour Reference

- **Success:** Green (0x43B581)
- **Error:** Red (0xF04747)
- **Warning:** Orange (0xFAA61A)
- **Info:** Purple (0xA78BFA)
- **Neutral:** Dark Grey (0x36393F)

---

## 💡 Tips & Tricks

1. **Most responses are ephemeral** - Only you see them unless stated otherwise
2. **Audit logging** - All important actions are logged to database
3. **DM fallback** - Bot will post in fallback channel if can't DM
4. **Role hierarchy** - Bot respects role hierarchy for all actions
5. **Timer persistence** - Timers survive bot restarts (database-backed)
6. **Sticky cache** - Sticky messages cached for performance
7. **Birthday checks** - Run every hour (hourly task)
8. **Bump detection** - Works with Disboard bot (ID: 302050872383242240)

---

## 🐛 Troubleshooting

**Bot not responding to commands?**
- Check bot has "Use Application Commands" permission
- Ensure commands are synced to guild

**Sticky messages not working?**
- Check bot has send/manage messages perms
- Verify channel is cached after restart

**Birthday announcements not posting?**
- Check `birthday_announcements` channel configured
- Verify channel exists and bot has perms

**Confessions not working?**
- Both `confession_review` and `confessions` channels must be set
- Staff need "Manage Messages" to approve/reject

**Bump reminders not triggering?**
- Only works with Disboard bot
- Requires message read permissions in bump channel

---

**Last Updated:** February 2026
**Bot Version:** Based on schema v3
**Need Help?** Use `/ticket` to open a support ticket!
