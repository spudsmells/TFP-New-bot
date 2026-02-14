# Phased Rollout Strategy - Testing & Deployment Guide

> How to safely test and deploy all new features without breaking everything

---

## 🎯 Overview

You've got **8 new cogs** with 30+ commands to test. This guide walks you through a safe, phased rollout strategy so you can test features incrementally without overwhelming your server or breaking existing functionality.

---

## 🔧 Feature Flag System

### How It Works

All features can be toggled on/off via `config.yaml`:

```yaml
features:
  diagnostics: true        # ✅ Enabled
  moderation: false        # ❌ Disabled
  birthdays: true          # ✅ Enabled
```

**Benefits:**
- ✅ Enable features one at a time
- ✅ Test in isolation
- ✅ No code changes needed
- ✅ Can disable instantly if issues arise
- ✅ Different configs for dev/staging/prod

---

## 📁 Environment Configs

Three example configs provided:

### 1. `config.example.dev.yaml`
- **Purpose:** Local development testing
- **Default:** All features DISABLED
- **Use:** Enable only what you're actively developing/testing

### 2. `config.example.staging.yaml`
- **Purpose:** Pre-production testing with real users
- **Default:** Core features ON, new features phased in
- **Use:** Test new features before production rollout

### 3. `config.example.production.yaml`
- **Purpose:** Live server
- **Default:** Only battle-tested features enabled
- **Use:** Production server after staging validation

---

## 🎮 Runtime Feature Management

New commands for managing features without bot restarts:

### `/features-list`
**View all features and their status**

**Permission:** Administrator

**Shows:**
- All available features grouped by category
- Current enabled/disabled status
- Quick reference for what's active

**Example output:**
```
Core
  diagnostics: ✅ Enabled
  feature_toggle: ✅ Enabled

Moderation (Phase 2)
  moderation: ❌ Disabled
  roles: ❌ Disabled
  channels: ❌ Disabled
  sticky: ❌ Disabled

Community (Phase 3)
  birthdays: ✅ Enabled
  counting: ❌ Disabled
```

---

### `/feature-toggle`
**Enable or disable a feature at runtime**

**Permission:** Administrator

**Parameters:**
- `feature` - Feature name (e.g., "moderation")
- `enabled` - True to enable, False to disable

**Examples:**
```
/feature-toggle feature:moderation enabled:true   # Enable moderation
/feature-toggle feature:birthdays enabled:false   # Disable birthdays
```

**What it does:**
1. Updates config in memory
2. Loads/unloads the cog
3. Syncs slash commands
4. Logs to audit trail

**Note:** Changes are **in-memory only**. To persist, edit `config.yaml` and use `/reload-config`.

---

### `/feature-reload`
**Reload a feature cog (apply code changes)**

**Permission:** Administrator

**Parameters:**
- `feature` - Feature to reload

**Example:**
```
/feature-reload feature:moderation
```

**Use case:** You've fixed a bug in the moderation cog. Reload it without restarting the bot.

---

### `/reload-config`
**Reload config.yaml without restarting**

**Permission:** Administrator

**Example:**
```
/reload-config
```

**Use case:** You've edited `config.yaml` to enable new features. Apply changes without downtime.

---

## 📅 Recommended Testing Timeline

### Week 1: Phase 2 - Moderation Suite

**Goal:** Test all moderation commands thoroughly

**Enable:**
```yaml
features:
  moderation: true
  roles: true
  channels: true
  sticky: false  # Save for Week 2
```

**Test Plan:**

#### Day 1-2: Moderation Commands
- [ ] `/kick` - Test with different scenarios
- [ ] `/ban` - Test message deletion (1, 3, 7 days)
- [ ] `/unban` - Test unbanning
- [ ] `/mute` - Test various durations (5min, 1hr, 1day)
- [ ] `/unmute` - Test early unmute
- [ ] `/warn` - Test DM delivery and fallback

**Verification:**
- Check DMs are sent correctly
- Verify fallback channel posting works
- Confirm audit logging works
- Test role hierarchy (can't ban higher roles)
- Test permission checks

#### Day 3-4: Role Management
- [ ] `/addrole` - Add various roles
- [ ] `/removerole` - Remove roles
- [ ] `/listroles` - View server roles
- [ ] `/roleinfo` - Check role details

**Verification:**
- Role hierarchy respected
- Audit logging works
- Error handling for managed roles

#### Day 5-6: Channel Management
- [ ] `/slowmode` - Test 0s, 10s, 5min, 1hr
- [ ] `/lock` - Lock channels, verify @everyone can't post
- [ ] `/unlock` - Unlock channels
- [ ] `/purge` - Delete 10, 50, 100 messages
- [ ] `/purge` with user filter

**Verification:**
- Permissions set correctly
- Lock/unlock notifications work
- Purge counts are accurate

#### Day 7: Sticky Messages
```yaml
features:
  sticky: true
```

- [ ] `/sticky-set` - Test all types (rules, welcome, info, custom)
- [ ] Post messages - Verify sticky reposts
- [ ] `/sticky-remove` - Remove sticky
- [ ] `/sticky-list` - View all stickies

**Verification:**
- Messages repost correctly
- Old messages deleted
- Survives bot restart
- Performance OK with frequent posting

---

### Week 2: Phase 3 Part 1 - Birthdays & Counting

**Enable:**
```yaml
features:
  birthdays: true
  counting: true
```

#### Day 1-3: Birthday System
- [ ] `/birthday-set` - Set birthdays with/without year
- [ ] `/birthday-remove` - Remove birthday
- [ ] `/birthday-toggle` - Toggle announcements
- [ ] `/birthday-list` - View upcoming birthdays
- [ ] Wait for hourly task to run
- [ ] Verify announcements post correctly

**Verification:**
- Age calculation correct
- Announcements post to right channel
- Hourly task runs without errors
- Upcoming list sorted correctly

#### Day 4-7: Counting Game
```yaml
features:
  counting_channels:
    - YOUR_CHANNEL_ID  # Set up test counting channel
```

- [ ] Count 1, 2, 3... verify ✅ reactions
- [ ] Test fail scenarios:
  - Wrong number (expect: ❌, reset)
  - Same user twice (expect: reset)
  - No number in message (expect: reset)
- [ ] Reach milestone 100 (expect: 💯)
- [ ] `/counting-stats` - View stats
- [ ] `/counting-reset` - Reset as staff

**Verification:**
- Validation works correctly
- Resets happen properly
- Stats track accurately
- Milestones celebrate

---

### Week 3: Phase 3 Part 2 - Confessions

**Enable:**
```yaml
features:
  confessions: true

channels:
  confession_review: YOUR_REVIEW_CHANNEL_ID
  confessions: YOUR_PUBLIC_CHANNEL_ID
```

#### Day 1-2: Submission & Review
- [ ] `/confess` - Submit test confessions
- [ ] Check review channel gets message
- [ ] Test ✅ approval (verify posts publicly)
- [ ] Test ❌ rejection (verify doesn't post)
- [ ] Verify submitter gets DM notification

#### Day 3-4: Content Validation
- [ ] Test with too short text (expect: error)
- [ ] Test with too long text (expect: error)
- [ ] Test with slurs from `data/slurs.txt` (expect: rejected)
- [ ] Test with excessive profanity (expect: rejected)

#### Day 5-7: Staff Training & Edge Cases
- [ ] Train staff on review process
- [ ] Test multiple pending confessions
- [ ] Test confession numbering (sequential)
- [ ] `/confession-stats` - View stats
- [ ] Stress test with 10+ confessions

**Verification:**
- Anonymity preserved (no user ID leaks)
- Numbering sequential
- DMs sent correctly
- Staff can review efficiently

---

### Week 4: Phase 3 Part 3 - Bump Reminders

**Enable:**
```yaml
features:
  bump: true

channels:
  bump_reminders: YOUR_BUMP_CHANNEL_ID

roles:
  bump_reminder: YOUR_ROLE_ID  # Optional
```

#### Day 1-3: Bump Detection
- [ ] Use `/bump` (Disboard command)
- [ ] Verify bot detects bump
- [ ] Check thank you message appears
- [ ] Verify stats recorded
- [ ] `/bump-stats` - View stats

#### Day 4-5: Reminders
- [ ] Wait 2 hours after bump
- [ ] Verify reminder posts automatically
- [ ] Check role mention works (if configured)
- [ ] Test with multiple bumps

#### Day 6-7: Leaderboard
- [ ] Have multiple users bump
- [ ] `/bump-leaderboard` - View top bumpers
- [ ] Verify medals (🥇🥈🥉) for top 3
- [ ] Verify counts are accurate

**Verification:**
- Disboard detection works
- 2-hour timer accurate
- Reminders post correctly
- Leaderboard sorts properly

---

## 🚨 Troubleshooting & Rollback

### If Something Breaks

#### Quick Disable
```
/feature-toggle feature:problematic_feature enabled:false
```

#### Or Edit Config & Reload
1. Edit `config.yaml` - set feature to `false`
2. `/reload-config` - apply changes
3. Feature immediately disabled

#### Full Rollback
```bash
# Checkout previous commit
git log --oneline  # Find commit hash
git checkout <hash>

# Or revert specific changes
git revert <commit-hash>

# Restart bot
```

---

### Common Issues

**"Commands not showing up"**
- Solution: `/reload-config` then wait ~5min for Discord cache

**"Permission denied errors"**
- Check bot has required permissions in server
- Verify role hierarchy (bot role must be high enough)

**"Sticky messages not reposting"**
- Check bot has manage messages permission
- Verify channel cache loaded (restart may help)

**"Birthdays not announcing"**
- Check `birthday_announcements` channel configured
- Verify hourly task is running (`/status` shows tasks)

**"Counting not detecting fails"**
- Check counting channel ID in `features.counting_channels`
- Verify message content has numbers

**"Confessions not posting"**
- Check both `confession_review` AND `confessions` channels set
- Verify staff have manage messages permission

**"Bump not detecting"**
- Only works with Disboard bot (ID: 302050872383242240)
- Check bot can read messages in bump channel

---

## ✅ Pre-Production Checklist

Before enabling features in production:

### Phase 2: Moderation
- [ ] All commands tested with real scenarios
- [ ] Staff trained on new commands
- [ ] DM fallback channel configured
- [ ] Audit logging verified
- [ ] Permission hierarchy tested
- [ ] Sticky message performance acceptable

### Phase 3: Community Features
- [ ] Birthday announcements tested for 1 week
- [ ] Counting game validated with real usage
- [ ] Confession moderation workflow established
- [ ] Bump reminders tested with Disboard
- [ ] All channels configured correctly
- [ ] Performance acceptable under load

### General
- [ ] Database backups configured
- [ ] Monitoring set up (`/status` checks)
- [ ] Staff know how to disable features
- [ ] Rollback plan documented
- [ ] Config files backed up

---

## 📊 Metrics to Monitor

### During Testing
- Command usage count (via audit log)
- Error rates (check logs)
- Response times (`/status` latency)
- Database query performance
- Member feedback

### Success Criteria
- ✅ No critical errors for 1 week
- ✅ Staff comfortable with features
- ✅ Positive member feedback
- ✅ Performance acceptable (<100ms latency)
- ✅ All edge cases handled

---

## 🎓 Staff Training

### Before Rollout
1. **Demo session** - Show all new commands
2. **Practice server** - Let staff test in staging
3. **Documentation** - Share COMMANDS.md
4. **Emergency procedures** - How to disable features

### Key Points
- Features can be toggled on/off
- Use `/reload-config` for config changes
- Check `/status` for bot health
- Audit log tracks all actions

---

## 🚀 Production Deployment

### Final Steps

1. **Backup everything**
   ```bash
   cp config.yaml config.yaml.backup
   sqlite3 bot.db ".backup bot.db.backup"
   ```

2. **Use production config**
   ```bash
   cp config.example.production.yaml config.yaml
   # Edit with real IDs
   ```

3. **Enable core features first**
   ```yaml
   features:
     diagnostics: true
     feature_toggle: true
     # ... stable features ...
   ```

4. **Enable new features gradually**
   - Week 1: Moderation
   - Week 2: Birthdays
   - Week 3: Counting
   - Week 4: Confessions & Bump

5. **Monitor closely**
   - Check `/status` hourly
   - Review audit logs daily
   - Watch for errors in logs
   - Gather user feedback

6. **Document issues**
   - Track bugs in GitHub issues
   - Note user feedback
   - Log performance metrics

---

## 📝 Summary

**Golden Rule:** Enable features ONE AT A TIME

**Testing Flow:**
1. Dev → Enable & test locally
2. Staging → Test with limited users
3. Production → Gradual rollout
4. Monitor → Watch for issues
5. Iterate → Fix bugs, improve

**Safety Nets:**
- Feature flags for instant disable
- `/reload-config` for no-downtime changes
- Audit logging for tracking
- Backup configs for rollback

---

**Good luck with testing! 🚀**

Remember: It's better to take 4 weeks and do it right than rush and break everything. Your members will thank you for a smooth rollout!
