# 🚀 PebbleHost Deployment Guide - Get Your Bot Live!

> Complete step-by-step guide to deploy The Gayborhood Bot on PebbleHost or similar hosting services

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Discord Bot Setup](#discord-bot-setup)
3. [PebbleHost Setup](#pebblehost-setup)
4. [Bot Installation](#bot-installation)
5. [Configuration](#configuration)
6. [First Launch](#first-launch)
7. [Testing Checklist](#testing-checklist)
8. [Troubleshooting](#troubleshooting)

---

## 📦 Prerequisites

### What You'll Need

- [ ] **Discord Developer Account** (free)
- [ ] **Test Discord Server** (create a dummy server for testing)
- [ ] **PebbleHost Account** (or similar: Pterodactyl, DigitalOcean, etc.)
- [ ] **Spotify Developer Account** (free, optional but recommended for music features)
- [ ] **GitHub Account** (to access the bot code)

### Recommended PebbleHost Plan

**For testing:**
- **Budget Bot Hosting** - $1/month
  - 512MB RAM (enough for testing)
  - 1GB storage
  - Python support

**For production:**
- **Premium Bot Hosting** - $3-5/month
  - 1-2GB RAM (handles larger servers)
  - 5GB storage
  - Better uptime

---

## 🤖 Discord Bot Setup

### Step 1: Create a Discord Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"**
3. Name it (e.g., "Gayborhood Bot - Test")
4. Click **"Create"**

### Step 2: Get Your Application ID

1. In the application page, go to **"General Information"**
2. Copy the **Application ID** (you'll need this later)
   ```
   Example: 1234567890123456789
   ```

### Step 3: Create the Bot User

1. Go to **"Bot"** tab in left sidebar
2. Click **"Add Bot"** → **"Yes, do it!"**
3. Under **Token**, click **"Reset Token"** → **"Yes, do it!"**
4. **Copy the token** (SAVE THIS! You can't see it again without resetting)
   ```
   Example: YOUR_BOT_TOKEN_WILL_BE_A_LONG_STRING_HERE
   ```

### Step 4: Configure Bot Permissions

Still in the **Bot** tab:

1. **Privileged Gateway Intents** - Enable these:
   - ✅ **Presence Intent**
   - ✅ **Server Members Intent**
   - ✅ **Message Content Intent**

2. **Bot Permissions** (we'll set these properly when inviting):
   - Administrator (for testing - simplifies things)
   - Or specific: Manage Roles, Manage Channels, Kick Members, Ban Members, etc.

### Step 5: Generate Invite Link

1. Go to **"OAuth2"** → **"URL Generator"**
2. **Scopes** - Select:
   - ✅ `bot`
   - ✅ `applications.commands`

3. **Bot Permissions** - Select:
   - ✅ **Administrator** (for testing - easier)
   - Or manually select: Manage Roles, Manage Channels, Kick Members, Ban Members, Manage Messages, Send Messages, Embed Links, Add Reactions, Read Message History, Use Slash Commands

4. **Copy the generated URL** at the bottom

5. **Invite to your test server:**
   - Paste URL in browser
   - Select your test server
   - Click **Authorize**

---

## 🎵 Spotify API Setup (Optional but Recommended)

### Step 1: Create Spotify App

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Log in with Spotify account (or create one)
3. Click **"Create App"**
4. Fill in:
   - **App Name:** "Gayborhood Bot Music Converter"
   - **App Description:** "Discord bot music link conversion"
   - **Redirect URI:** `http://localhost` (required but not used)
   - **APIs:** Web API
5. Click **"Save"**

### Step 2: Get Credentials

1. In your new app dashboard:
   - Copy **Client ID**
   - Click **"Show Client Secret"** → Copy **Client Secret**

**Save these for later!**

---

## 🖥️ PebbleHost Setup

### Step 1: Purchase & Create Server

1. Go to [PebbleHost](https://pebblehost.com/) (or your chosen host)
2. Purchase a **Bot Hosting** plan
3. In your panel, create a new server:
   - **Server Type:** Python Bot
   - **Python Version:** 3.11 or higher

### Step 2: Access Your Server

**Option A: Web File Manager**
- Use PebbleHost's built-in file manager

**Option B: SFTP** (recommended for large uploads)
- Download [FileZilla](https://filezilla-project.org/) or [WinSCP](https://winscp.net/)
- Use SFTP credentials from PebbleHost panel

**Option C: SSH** (for advanced users)
- Use credentials from PebbleHost panel
- Connect via SSH client

---

## 📂 Bot Installation

### Step 1: Upload Bot Files

**Method 1: GitHub (Recommended)**

If your host has Git access:

```bash
# SSH into your server
ssh user@your-server.pebblehost.com

# Clone the repository
git clone https://github.com/spudsmells/TFP-New-bot.git
cd TFP-New-bot

# Checkout the branch with new features
git checkout claude/review-bot-status-ILFKM
```

**Method 2: Manual Upload**

1. Download the repository as ZIP from GitHub
2. Extract locally
3. Upload all files via SFTP/File Manager to your server

### Step 2: Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install yt-dlp (for music conversion)
pip install yt-dlp

# Optional: Install spotipy for Spotify metadata
pip install spotipy
```

**If pip is not available:**
```bash
# Try pip3
pip3 install -r requirements.txt

# Or python -m pip
python -m pip install -r requirements.txt
```

---

## ⚙️ Configuration

### Step 1: Create Config File

```bash
# Copy the development example config
cp config.example.dev.yaml config.yaml
```

### Step 2: Edit config.yaml

Use your server's file editor or download, edit locally, and re-upload.

**Replace these values:**

```yaml
# === DISCORD CREDENTIALS ===
app_id: YOUR_APPLICATION_ID_HERE        # From Discord Developer Portal
guild_id: YOUR_TEST_SERVER_ID_HERE      # Right-click server icon → Copy ID

# === DATABASE ===
database_url: "sqlite:///bot.db"        # Keep as-is for testing

# === SPOTIFY API (Optional) ===
spotify_client_id: "your_spotify_client_id"
spotify_client_secret: "your_spotify_client_secret"

# === FEATURE FLAGS (Start Minimal for Testing) ===
features:
  diagnostics: true          # ✅ Keep enabled
  feature_toggle: true       # ✅ Keep enabled

  # Enable ONE feature at a time for testing
  onboarding: false
  intros: false
  age_verify: false
  xp: false
  milestones: false
  achievements: false
  tickets_member: false
  tickets_staff: false
  ticket_lifecycle: false
  ticket_panel: false
  bully: false
  music: false
  auto_threads: false
  monthly_stats: false

  # NEW FEATURES - Test these!
  moderation: false         # Start disabled, enable later
  roles: false
  channels: false
  sticky: false
  birthdays: false
  counting: false
  confessions: false
  bump: false

# === CHANNEL IDS (Get from your test server) ===
channels:
  rules: 0                  # Replace with actual channel ID
  welcome: 0                # Replace with actual channel ID
  intros: 0                 # Replace with actual channel ID
  staff_alerts: 0           # Replace with actual channel ID
  onboarding_fallback: 0    # Replace with actual channel ID
  mod_logs: 0               # Replace with actual channel ID

  # Phase 3 channels (when you enable those features)
  birthday_announcements: 0
  confession_review: 0
  confessions: 0
  bump_reminders: 0

# === ROLE IDS (Get from your test server) ===
roles:
  pending: 0                # Replace with actual role ID
  gaybor: 0                 # Replace with actual role ID
  staff: 0                  # Replace with actual role ID
  bump_reminder: 0          # Optional

# === EMBED BRANDING ===
embeds:
  footer_text: "TEST BOT - Development Environment"
  thumbnail_url: null

# === XP CONFIGURATION ===
xp:
  message_min: 5
  message_max: 15
  cooldown_seconds: 60
  base_level_xp: 100
  xp_multiplier: 1.5

# === RATE LIMITING ===
rate_limits:
  music_per_user: 3
  music_window_seconds: 600
```

### Step 3: Get Discord IDs

**Enable Developer Mode in Discord:**
1. Discord Settings → Advanced → Developer Mode → ON

**Get Server ID:**
1. Right-click your test server icon → Copy Server ID
2. Paste as `guild_id` in config

**Get Channel IDs:**
1. Right-click any channel → Copy Channel ID
2. Paste in `channels:` section

**Get Role IDs:**
1. Server Settings → Roles → Click a role → Copy ID (from URL)
2. Or use Developer Mode → Right-click role → Copy ID
3. Paste in `roles:` section

---

## 🔐 Bot Token Setup

### Create .env File

```bash
# Create a .env file in the bot root directory
nano .env
```

**Add your bot token:**
```env
DISCORD_BOT_TOKEN=YOUR_BOT_TOKEN_HERE
```

Replace `YOUR_BOT_TOKEN_HERE` with the token from Discord Developer Portal.

**Save and exit** (Ctrl+O, Enter, Ctrl+X)

**Verify .env is in .gitignore:**
```bash
# Check if .env is ignored
cat .gitignore | grep .env

# If not, add it
echo ".env" >> .gitignore
```

**NEVER commit your .env file to GitHub!**

---

## 🚀 First Launch

### Step 1: Run the Bot

```bash
# Make sure you're in the bot directory
cd TFP-New-bot

# Run the bot
python main.py
```

**Or if your host uses python3:**
```bash
python3 main.py
```

### Step 2: Check for Errors

**What you should see:**
```
INFO - Setting up Gayborhood Bot v3.0.0 ...
INFO - Database ready
INFO - Services initialized
INFO - Persistent views registered
INFO - Feature enabled: diagnostics -> cogs.diagnostics
INFO - Feature enabled: feature_toggle -> cogs.feature_toggle
INFO - Cog loaded: cogs.diagnostics
INFO - Cog loaded: cogs.feature_toggle
INFO - Bot ready! Logged in as YourBotName#1234
INFO - Serving guild: Your Test Server (123456789)
```

**If you see errors:**
- Check [Troubleshooting](#troubleshooting) section below

### Step 3: Test Basic Commands

In your Discord test server:

```
/ping
```
**Expected:** Bot responds with "🏓 Pong! Latency: X ms"

```
/status
```
**Expected:** Shows bot status, uptime, enabled features

```
/version
```
**Expected:** Shows bot version info

---

## ✅ Testing Checklist

### Phase 1: Core Features

- [ ] `/ping` responds
- [ ] `/status` shows correct info
- [ ] `/version` shows version
- [ ] `/features-list` shows all features (diagnostics + feature_toggle should be enabled)

### Phase 2: Enable One Feature

Edit `config.yaml`:
```yaml
features:
  diagnostics: true
  feature_toggle: true
  moderation: true        # ← Enable this
```

**Reload config:**
```
/reload-config
```

**Or restart bot:**
```bash
# Press Ctrl+C to stop
# Then run again
python main.py
```

**Test moderation commands:**
- [ ] `/kick` - Try kicking a test user (or yourself with another account)
- [ ] `/ban` - Test ban command
- [ ] `/mute` - Test mute
- [ ] `/warn` - Test warning system

### Phase 3: Enable More Features Gradually

**Week 1:**
```yaml
features:
  moderation: true
  roles: true
  channels: true
```

Test thoroughly before enabling more!

### Phase 4: Monitor Logs

```bash
# Check logs for errors
tail -f logs/bot.log

# Or if no logs directory, check console output
```

---

## 🔧 Troubleshooting

### Bot Won't Start

**Problem:** `ModuleNotFoundError: No module named 'discord'`

**Solution:**
```bash
pip install -r requirements.txt
```

---

**Problem:** `discord.errors.LoginFailure: Improper token has been passed`

**Solution:**
- Check your `.env` file has correct token
- Make sure no extra spaces or quotes around token
- Regenerate token in Discord Developer Portal if needed

---

**Problem:** `sqlite3.OperationalError: unable to open database file`

**Solution:**
```bash
# Create database directory if needed
mkdir -p data

# Or change database_url in config.yaml to:
database_url: "sqlite:///bot.db"
```

---

### Commands Not Showing Up

**Problem:** Slash commands don't appear in Discord

**Solution:**
1. Wait 5-10 minutes (Discord caches commands)
2. Try `/reload-config`
3. Restart bot
4. Kick and re-invite bot with proper scopes

**Check bot permissions:**
- Bot needs `applications.commands` scope
- Bot role must have "Use Application Commands" permission

---

### Permission Errors

**Problem:** `Missing Permissions` error when using commands

**Solution:**
- Give bot Administrator role (for testing)
- Or ensure bot has all required permissions
- Make sure bot's role is ABOVE roles it needs to manage

---

### Music Conversion Not Working

**Problem:** Music links not converting

**Solution:**
1. **Check yt-dlp installed:**
   ```bash
   yt-dlp --version
   ```
   If not: `pip install yt-dlp`

2. **Enable music feature:**
   ```yaml
   features:
     music: true
   ```

3. **Add Spotify credentials** (optional but helps)

---

### Database Errors

**Problem:** `database is locked` errors

**Solution:**
- Use PostgreSQL for production (SQLite doesn't handle concurrent writes well)
- For testing, SQLite is fine - just avoid hammering commands

---

### High Memory Usage

**Problem:** Bot using too much RAM

**Solution:**
- Disable unused features in config
- Use smaller PebbleHost plan for testing only
- Upgrade to bigger plan for production

---

## 🎯 Quick Reference

### Essential Commands

```bash
# Start bot
python main.py

# Stop bot
Ctrl + C

# View logs
tail -f logs/bot.log

# Check Python version
python --version

# Install dependencies
pip install -r requirements.txt

# Update bot (if using git)
git pull origin claude/review-bot-status-ILFKM
```

### Discord Commands

```
/ping                       # Test bot responsiveness
/status                     # View bot status
/version                    # View version info
/features-list              # See all features and their status
/feature-toggle             # Enable/disable features at runtime
/reload-config              # Reload config.yaml without restart
```

### Config File Locations

```
config.yaml                 # Main configuration
.env                        # Bot token (KEEP SECRET!)
bot.db                      # SQLite database
logs/bot.log               # Log file
requirements.txt           # Python dependencies
```

---

## 📊 Recommended Testing Flow

### Day 1: Basic Setup
1. ✅ Bot runs and connects to Discord
2. ✅ `/ping`, `/status`, `/version` work
3. ✅ Feature flag system works (`/features-list`)

### Day 2: Test Moderation
1. ✅ Enable `moderation` feature
2. ✅ Test kick, ban, mute, warn commands
3. ✅ Verify DM notifications work
4. ✅ Check audit logging

### Day 3: Test Roles & Channels
1. ✅ Enable `roles` and `channels`
2. ✅ Test role management commands
3. ✅ Test channel locks, slowmode, purge
4. ✅ Verify permissions work correctly

### Week 2+: Phase 3 Features
Follow the [PHASED_ROLLOUT.md](PHASED_ROLLOUT.md) guide for comprehensive testing.

---

## 🚨 Important Reminders

### Security

- ✅ **NEVER** share your bot token
- ✅ **NEVER** commit `.env` to GitHub
- ✅ Use environment variables for secrets
- ✅ Regenerate token if accidentally leaked

### Best Practices

- ✅ Test in dummy server FIRST
- ✅ Enable features ONE AT A TIME
- ✅ Monitor logs for errors
- ✅ Keep backups of config and database
- ✅ Use feature flags to disable broken features quickly

### Before Production

- ✅ Test all features thoroughly in staging
- ✅ Switch to PostgreSQL database
- ✅ Set up automated backups
- ✅ Remove "TEST BOT" branding
- ✅ Configure all channel/role IDs correctly
- ✅ Train staff on new commands
- ✅ Have rollback plan ready

---

## 📞 Getting Help

**If stuck:**

1. **Check logs** - Most errors are explained there
2. **Read error messages** - They usually tell you what's wrong
3. **Google the error** - Someone else has probably had it
4. **Check Discord.py docs** - [docs.pycord.dev](https://docs.pycord.dev/)
5. **Ask in Discord dev communities**

---

## 🎉 You're Ready!

Follow this guide step-by-step and you'll have a working bot in ~30 minutes!

**Start simple:**
- Get bot online ✅
- Test core commands ✅
- Enable ONE feature ✅
- Test thoroughly ✅
- Repeat ✅

**Good luck! 🚀**
