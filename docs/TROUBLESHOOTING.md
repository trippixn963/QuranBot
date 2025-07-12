# 🔧 QuranBot Troubleshooting Guide

*"And whoever fears Allah - He will make for him a way out."* - **Quran 65:2**

## Overview

This guide provides solutions to common issues encountered while running QuranBot, both in development and production environments. It covers everything from basic setup problems to advanced deployment issues.

---

## 📋 Quick Diagnostics

### Health Check Commands

```bash
# Check bot status (VPS)
qb-status

# Check recent logs
qb-logs | tail -50

# Check error logs
qb-errors | tail -20

# Check system resources
htop
df -h
free -h
```

### Dashboard Health Check

```bash
# Check dashboard service
sudo systemctl status quranbot-dashboard.service

# Test dashboard endpoints
curl http://localhost:8080/api/status
curl http://localhost:8080/api/system
```

---

## 🚨 Common Issues & Solutions

### 1. Bot Connection Issues

#### **Issue: Bot Not Connecting to Discord**

**Symptoms:**
- Bot appears offline in Discord
- "Invalid token" errors in logs
- Connection timeout errors

**Solutions:**

```bash
# 1. Verify bot token
echo $DISCORD_TOKEN
# Should output your bot token (if empty, token not set)

# 2. Check token validity
# Go to Discord Developer Portal > Your App > Bot
# Regenerate token if needed

# 3. Update environment file
nano config/.env
# Ensure DISCORD_TOKEN=your_actual_bot_token

# 4. Restart bot service
qb-restart

# 5. Check bot permissions in Discord server
# Bot needs: Send Messages, Use Slash Commands, Connect, Speak
```

**Recent Fix Applied:**
- Enhanced role management with retry logic for Discord rate limiting
- Improved connection handling with automatic reconnection

#### **Issue: Bot Connects But Commands Don't Work**

**Symptoms:**
- Bot shows as online
- Slash commands not appearing
- "Application did not respond" errors

**Solutions:**

```bash
# 1. Check guild ID configuration
grep GUILD_ID config/.env
# Should match your Discord server ID

# 2. Verify bot permissions
# Required: Use Slash Commands, Send Messages

# 3. Re-sync commands (in bot code)
# Bot automatically syncs commands on startup

# 4. Check logs for command registration errors
qb-logs | grep -i "command\|sync"
```

---

### 2. Audio Playback Issues

#### **Issue: Audio Not Playing**

**Symptoms:**
- Bot joins voice channel but no audio
- FFmpeg errors in logs
- "Audio source not found" errors

**Solutions:**

```bash
# 1. Check FFmpeg installation
which ffmpeg
ffmpeg -version

# 2. Install FFmpeg if missing
# Ubuntu/Debian:
sudo apt update && sudo apt install ffmpeg

# macOS:
brew install ffmpeg

# 3. Verify FFmpeg path in config
grep FFMPEG_PATH config/.env
# Should be: /usr/bin/ffmpeg (Linux) or /opt/homebrew/bin/ffmpeg (macOS)

# 4. Check audio files exist
ls -la audio/Saad\ Al\ Ghamdi/
# Should show .mp3 files: 001.mp3, 002.mp3, etc.

# 5. Test audio file format
file audio/Saad\ Al\ Ghamdi/001.mp3
# Should show: Audio file with codec MP3

# 6. Check file permissions
sudo chown -R $(whoami):$(whoami) audio/
chmod -R 644 audio/*/*.mp3
```

**Recent Fix Applied:**
- Enhanced audio status detection for dashboard
- Improved surah name display with proper transliteration
- Fixed voice connection status detection

#### **Issue: Audio Cuts Out or Stops Unexpectedly**

**Symptoms:**
- Audio starts but stops after a few seconds
- "Broken pipe" errors
- Bot disconnects from voice channel

**Solutions:**

```bash
# 1. Check system resources
free -h
# Ensure sufficient RAM available

# 2. Check audio file integrity
ffmpeg -v error -i audio/Saad\ Al\ Ghamdi/001.mp3 -f null -
# Should show no errors for valid files

# 3. Increase voice client timeout (in code)
# Already implemented in recent updates

# 4. Check network stability
ping discord.com
# Should show consistent response times

# 5. Restart audio system
qb-restart
```

---

### 3. Dashboard Issues

#### **Issue: Dashboard Not Accessible**

**Symptoms:**
- Cannot access http://your-ip:8080
- Connection refused errors
- Dashboard shows as offline

**Solutions:**

```bash
# 1. Check dashboard service status
sudo systemctl status quranbot-dashboard.service

# 2. Check if port is listening
sudo netstat -tlnp | grep 8080
# Should show python process listening on port 8080

# 3. Check firewall settings
sudo ufw status
# Port 8080 should be allowed

# 4. Allow dashboard port
sudo ufw allow 8080

# 5. Restart dashboard service
sudo systemctl restart quranbot-dashboard.service

# 6. Check dashboard logs
sudo journalctl -u quranbot-dashboard.service -f
```

**Recent Fix Applied:**
- Fixed timezone mismatch between bot and dashboard (EST alignment)
- Enhanced dashboard error handling and logging
- Improved API endpoint reliability

#### **Issue: Dashboard Shows Incorrect Data**

**Symptoms:**
- Audio status shows "None"
- Leaderboard not updating
- Statistics appear incorrect

**Solutions:**

```bash
# 1. Check data file permissions
ls -la data/
# Files should be readable by dashboard user

# 2. Verify data file format
python3 -c "import json; print(json.load(open('data/quiz_stats.json')))"
# Should parse without errors

# 3. Restart both bot and dashboard
qb-restart
sudo systemctl restart quranbot-dashboard.service

# 4. Clear browser cache
# Ctrl+F5 or Cmd+Shift+R

# 5. Check API endpoints directly
curl http://localhost:8080/api/audio
curl http://localhost:8080/api/leaderboard
```

**Recent Fix Applied:**
- Enhanced audio status with proper surah name display
- Fixed leaderboard username resolution
- Improved real-time data synchronization

---

### 4. Command-Specific Issues

#### **Issue: /interval Command Not Working**

**Symptoms:**
- ImportError: cannot import name 'daily_verses_manager'
- Command fails with module errors
- Intervals not being saved

**Solutions:**

```bash
# 1. Check recent logs for import errors
qb-logs | grep -i "interval\|import"

# 2. Verify utils module structure
ls -la src/utils/
# Should include daily_verses.py

# 3. Check for typos in import statements
grep -r "daily_verses_manager" src/
# Should be "daily_verse_manager" (singular)

# 4. Restart bot to reload modules
qb-restart
```

**Recent Fix Applied:**
- Fixed import mismatch: `daily_verses_manager` → `daily_verse_manager`
- Fixed timezone import: `timezone.utc` → `pytz.UTC`

#### **Issue: Quiz Questions Missing Explanations**

**Symptoms:**
- Quiz results don't show explanation boxes
- Automated quizzes missing context
- Manual quizzes work but scheduled ones don't

**Solutions:**

```bash
# 1. Check quiz data structure
python3 -c "
import json
with open('data/quiz_questions.json') as f:
    q = json.load(f)[0]
    print('explanation' in q)
"
# Should print True

# 2. Verify quiz manager code
grep -A 5 -B 5 "explanation" src/utils/quiz_manager.py

# 3. Check scheduler implementation
grep -A 10 "quiz_question_data" src/utils/quiz_manager.py
```

**Recent Fix Applied:**
- Added explanation field to automated quiz scheduler
- Enhanced quiz data structure validation

---

### 5. Role Management Issues

#### **Issue: Users Keep "Listening to Quran" Role After Leaving**

**Symptoms:**
- Role not removed when user leaves voice channel
- Users accumulate role without being in channel
- Role assignment appears to work but removal doesn't

**Solutions:**

```bash
# 1. Check recent role management logs
qb-logs | grep -i "role\|listening"

# 2. Verify role ID configuration
grep PANEL_ACCESS_ROLE_ID config/.env

# 3. Check Discord rate limiting
qb-logs | grep -i "rate\|limit"

# 4. Test role assignment manually
# Use Discord's role management to verify bot permissions
```

**Recent Fix Applied:**
- Enhanced role management with retry logic (3 attempts with exponential backoff)
- Added member refresh before role operations
- Improved rate limit handling with wait and retry
- Better verification of role assignment/removal success

---

### 6. Log and Data Issues

#### **Issue: Log Files Not Accessible**

**Symptoms:**
- Local logs directory empty
- Log rotation not working
- Cannot access recent bot logs

**Solutions:**

```bash
# 1. Check log directory structure
ls -la logs/

# 2. Verify log file permissions
ls -la logs/$(date '+%Y-%m-%d')/

# 3. Check log configuration
grep -i "log" src/bot/main.py

# 4. Check disk space
df -h

# 5. Restart bot to reinitialize logging
python main.py
```

**Recent Fix Applied:**
- Enhanced log directory management
- Improved error handling in log process
- Added automatic log rotation

#### **Issue: Dashboard Shows Wrong Timezone**

**Symptoms:**
- Dashboard logs show UTC time
- Bot logs show EST time
- Time mismatch after midnight

**Solutions:**

```bash
# 1. Check timezone configuration
grep -i timezone src/utils/daily_verses.py

# 2. Verify EST timezone usage
python3 -c "
import pytz
from datetime import datetime
est = pytz.timezone('America/New_York')
print(datetime.now(est))
"

# 3. Restart dashboard service
sudo systemctl restart quranbot-dashboard.service
```

**Recent Fix Applied:**
- Synchronized dashboard timezone with bot (EST/America/New_York)
- Added EST helper functions for consistent time handling
- Fixed midnight log file switching issue

---

### 7. Memory and Performance Issues

#### **Issue: High Memory Usage**

**Symptoms:**
- Bot using excessive RAM
- System becomes slow
- Out of memory errors

**Solutions:**

```bash
# 1. Check memory usage
free -h
ps aux --sort=-%mem | head -10

# 2. Check for memory leaks
# Monitor memory usage over time
watch -n 5 'ps aux | grep python | grep -v grep'

# 3. Restart bot service
qb-restart

# 4. Check log file sizes
du -sh logs/*
# Large log files can consume memory

# 5. Clean old logs
find logs/ -name "*.log" -mtime +7 -delete
```

**Solutions Applied:**
- Implemented automatic log rotation
- Enhanced garbage collection in audio manager
- Optimized data structure usage

#### **Issue: Bot Becomes Unresponsive**

**Symptoms:**
- Commands don't respond
- Bot appears online but inactive
- High CPU usage

**Solutions:**

```bash
# 1. Check CPU usage
htop
# Look for python processes using high CPU

# 2. Check for infinite loops in logs
qb-logs | grep -i "loop\|error" | tail -20

# 3. Check async task status
# Look for deadlocks or hanging tasks in logs

# 4. Force restart
sudo systemctl stop quranbot.service
sleep 5
sudo systemctl start quranbot.service

# 5. Check for corrupted data files
python3 -c "
import json
import os
for f in os.listdir('data/'):
    if f.endswith('.json'):
        try:
            with open(f'data/{f}') as file:
                json.load(file)
            print(f'{f}: OK')
        except Exception as e:
            print(f'{f}: ERROR - {e}')
"
```

---

### 8. Database and State Issues

#### **Issue: Corrupted State Files**

**Symptoms:**
- Bot starts from beginning despite previous state
- JSON decode errors
- State not saving properly

**Solutions:**

```bash
# 1. Check state file integrity
python3 -c "
import json
try:
    with open('data/playback_state.json') as f:
        state = json.load(f)
    print('State file OK:', state.keys())
except Exception as e:
    print('State file corrupted:', e)
"

# 2. Restore from backup
ls -la backup/
# Find recent backup and restore

# 3. Reset state (last resort)
rm data/playback_state.json
qb-restart
# Bot will create fresh state
```

**Prevention Applied:**
- Atomic file writes to prevent corruption
- Automatic backup creation before state changes
- Data integrity verification on load

---

### 9. Network and Connectivity Issues

#### **Issue: Discord API Rate Limiting**

**Symptoms:**
- "Rate limited" errors in logs
- Commands delayed or failing
- Bot temporarily unresponsive

**Solutions:**

```bash
# 1. Check rate limit logs
qb-logs | grep -i "rate\|limit"

# 2. Reduce command frequency
# Avoid rapid successive commands

# 3. Check for command loops
qb-logs | grep -i "loop\|repeat"

# 4. Wait for rate limit to reset
# Usually 1-60 seconds depending on endpoint
```

**Mitigation Applied:**
- Enhanced rate limit handling with exponential backoff
- Intelligent retry mechanisms
- Request queuing for high-frequency operations

---

### 10. Service Management Issues

#### **Issue: Bot Process Not Starting**

**Symptoms:**
- Bot offline after system restart
- Process not running
- Manual start required

**Solutions:**

```bash
# 1. Check if bot process is running
ps aux | grep python | grep main.py

# 2. Check for error messages
python main.py

# 3. Check file permissions
ls -la main.py src/

# 4. Verify Python environment
which python3
python3 --version

# 5. Check dependencies
pip list | grep discord
```

#### **Issue: Configuration Problems**

**Symptoms:**
- Bot starts but doesn't respond
- Permission errors
- Configuration not loading

**Solutions:**

```bash
# 1. Check environment variables
echo $DISCORD_TOKEN | head -c 10

# 2. Verify config file
ls -la config/.env

# 3. Check file structure
tree -L 2 src/

# 4. Validate configuration
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv('config/.env')
print('DISCORD_TOKEN:', 'Set' if os.getenv('DISCORD_TOKEN') else 'Missing')
"
```

---

## 🔍 Advanced Diagnostics

### Log Analysis Commands

```bash
# Search for specific errors
qb-logs | grep -i "error\|exception\|failed"

# Check recent activity
qb-logs | tail -100 | grep -v "INFO"

# Monitor real-time logs
qb-logs -f

# Check specific time period
qb-logs | grep "2024-07-12 14:"

# Search for user activity
qb-logs | grep "user_id.*123456"

# Check memory-related issues
qb-logs | grep -i "memory\|oom\|malloc"
```

### System Resource Monitoring

```bash
# Monitor system resources
watch -n 2 'free -h && echo "---" && df -h && echo "---" && ps aux | grep python | head -5'

# Check disk I/O
iostat -x 1

# Monitor network activity
nethogs

# Check open files
lsof | grep python | wc -l
```

### Database Integrity Checks

```bash
# Verify all JSON files
for file in data/*.json; do
    echo "Checking $file..."
    python3 -c "import json; json.load(open('$file')); print('✓ Valid')" || echo "✗ Invalid"
done

# Check backup integrity
for file in backup/*.zip; do
    echo "Checking $file..."
    unzip -t "$file" >/dev/null && echo "✓ Valid" || echo "✗ Corrupted"
done
```

---

## 📞 Getting Help

### Before Seeking Help

1. **Check this troubleshooting guide** for your specific issue
2. **Review recent logs** for error messages
3. **Test basic functionality** (bot connection, simple commands)
4. **Verify configuration** (environment variables, file permissions)
5. **Try restarting services** as a first step

### Information to Provide

When reporting issues, include:

```bash
# System information
uname -a
python3 --version
ffmpeg -version

# Bot status
qb-status

# Recent logs (last 50 lines)
qb-logs | tail -50

# Error logs
qb-errors | tail -20

# Configuration (remove sensitive data)
cat config/.env | sed 's/DISCORD_TOKEN=.*/DISCORD_TOKEN=***HIDDEN***/'

# File permissions
ls -la data/ logs/ audio/
```

### Support Channels

- **GitHub Issues**: For bug reports and feature requests
- **Documentation**: Check all docs/ files first
- **Bot Management**: Use built-in management scripts
- **Community**: Discord server (if available)

---

## 🛡️ Prevention Best Practices

### Regular Maintenance

```bash
# Weekly maintenance script
#!/bin/bash
echo "=== QuranBot Weekly Maintenance ==="

# Check disk space
df -h

# Clean old logs (keep 7 days)
find logs/ -name "*.log" -mtime +7 -delete

# Check service status
qb-status

# Verify backup system
ls -la backup/ | tail -5

# Check for updates
cd /opt/DiscordBots/QuranBot
git fetch origin
git status

echo "=== Maintenance Complete ==="
```

### Monitoring Setup

```bash
# Set up automated health checks
cat > check_bot_health.sh << 'EOF'
#!/bin/bash
# Check QuranBot health
ps aux | grep "python.*main.py" || echo "Bot not running"
EOF
chmod +x check_bot_health.sh
```

### Backup Verification

```bash
# Daily backup verification
#!/bin/bash
LATEST_BACKUP=$(ls -t backup/*.zip | head -1)
if unzip -t "$LATEST_BACKUP" >/dev/null 2>&1; then
    echo "✓ Latest backup is valid: $LATEST_BACKUP"
else
    echo "✗ Latest backup is corrupted: $LATEST_BACKUP"
    # Send alert or notification
fi
```

---

## 🤲 Final Notes

*"And Allah is with those who are patient."* - **Quran 2:153**

Remember that troubleshooting is part of the learning process. Each issue resolved makes the bot more stable and reliable for the Muslim community it serves.

### Emergency Recovery

If all else fails and you need to completely reset:

```bash
# 1. Stop all services
sudo systemctl stop quranbot.service
sudo systemctl stop quranbot-dashboard.service

# 2. Backup current state
cp -r /opt/DiscordBots/QuranBot /opt/DiscordBots/QuranBot.emergency.backup

# 3. Fresh deployment
cd /opt/DiscordBots
rm -rf QuranBot
git clone https://github.com/yourusername/QuranBot.git QuranBot
cd QuranBot

# 4. Restore configuration
cp /opt/DiscordBots/QuranBot.emergency.backup/config/.env config/

# 5. Restore data (if needed)
cp -r /opt/DiscordBots/QuranBot.emergency.backup/data/* data/
cp -r /opt/DiscordBots/QuranBot.emergency.backup/audio/* audio/

# 6. Reinstall and restart
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl start quranbot.service
sudo systemctl start quranbot-dashboard.service
```

May Allah grant success in resolving all technical difficulties and make this bot a source of continuous benefit for the Muslim ummah. 