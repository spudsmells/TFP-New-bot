# ⚡ Quick Start Checklist

> Get your bot running in 10 minutes!

---

## ✅ Pre-Flight Checklist

### 1. Create Discord Bot (5 min)

- [ ] Go to [Discord Developer Portal](https://discord.com/developers/applications)
- [ ] Create new application
- [ ] Copy **Application ID**
- [ ] Create bot user → Copy **Bot Token**
- [ ] Enable intents: **Server Members**, **Message Content**, **Presence**
- [ ] Generate invite link with `bot` + `applications.commands` scopes
- [ ] Invite to test server

### 2. Setup Files (2 min)

```bash
# Clone repository
git clone https://github.com/spudsmells/TFP-New-bot.git
cd TFP-New-bot

# Install dependencies
pip install -r requirements.txt
pip install yt-dlp spotipy  # Optional: for music features
```

### 3. Configure .env (1 min)

```bash
# Copy example
cp .env.example .env

# Edit .env and add:
# - DISCORD_TOKEN
# - DISCORD_APP_ID
# - DATABASE_URL
```

**Example .env:**
```env
DISCORD_TOKEN=YOUR_BOT_TOKEN_GOES_HERE
DISCORD_APP_ID=1234567890123456789
DATABASE_URL=sqlite:///bot.db
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
ENVIRONMENT=development
```

### 4. Configure config.yaml (2 min)

```bash
# Copy example
cp config.example.dev.yaml config.yaml

# Edit config.yaml and add:
# - guild_id (your test server ID)
# - Channel IDs
# - Role IDs
```

**Minimal config.yaml:**
```yaml
guild_id: YOUR_SERVER_ID_HERE

features:
  diagnostics: true
  feature_toggle: true

channels:
  rules: 0
  welcome: 0
  intros: 0
  staff_alerts: 0
  onboarding_fallback: 0
  mod_logs: 0

roles:
  pending: 0
  gaybor: 0
  staff: 0

embeds:
  footer_text: "TEST BOT"
  thumbnail_url: null

xp:
  message_min: 5
  message_max: 15
  cooldown_seconds: 60
  base_level_xp: 100
  xp_multiplier: 1.5
```

### 5. Launch! (10 seconds)

```bash
python bot.py
```

**Expected output:**
```
INFO - Starting Gayborhood Bot v3.0.0
INFO - Database ready
INFO - Services initialized
INFO - Bot ready! Logged in as YourBotName#1234
```

### 6. Test (1 min)

In Discord:
```
/ping
/status
/features-list
```

**If all work → You're live!** 🎉

---

## 🔥 Common Issues

**"Missing required environment variables"**
→ Check your `.env` file has all required values

**"ModuleNotFoundError"**
→ Run `pip install -r requirements.txt`

**"Improper token"**
→ Check DISCORD_TOKEN in `.env` (no spaces, no quotes)

**Commands not appearing**
→ Wait 5 minutes, Discord caches slash commands

---

## 📚 Next Steps

1. **Read full guide:** [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
2. **Plan testing:** [PHASED_ROLLOUT.md](PHASED_ROLLOUT.md)
3. **Enable features:** Use `/feature-toggle` or edit `config.yaml`
4. **Monitor:** Check `/status` and logs

---

**That's it! You're ready to start testing features!** 🚀
