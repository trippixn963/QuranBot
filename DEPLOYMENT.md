# 🚀 QuranBot Production Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying QuranBot to production environments, including VPS setup, configuration management, monitoring, and maintenance procedures.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Configuration](#configuration)
4. [VPS Deployment](#vps-deployment)
5. [Service Management](#service-management)
6. [Monitoring & Logging](#monitoring--logging)
7. [Backup & Recovery](#backup--recovery)
8. [Troubleshooting](#troubleshooting)
9. [Maintenance](#maintenance)

## Prerequisites

### System Requirements
- **OS**: Ubuntu 20.04 LTS or newer
- **RAM**: Minimum 2GB, Recommended 4GB
- **Storage**: Minimum 20GB free space
- **Network**: Stable internet connection
- **Python**: 3.11+ with pip and venv support

### Required Software
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python 3.11+
sudo apt install python3.11 python3.11-venv python3.11-dev python-is-python3 -y

# Install FFmpeg for audio processing
sudo apt install ffmpeg -y

# Install Git for code management
sudo apt install git -y

# Install system monitoring tools
sudo apt install htop iotop netstat-nat -y

# Install process manager
sudo apt install supervisor -y
```

### Discord Requirements
- Discord Bot Token
- Discord Server (Guild) with appropriate permissions
- 7 Discord Webhook URLs for multi-channel logging

## Environment Setup

### 1. Create Application User
```bash
# Create dedicated user for the bot
sudo useradd -m -s /bin/bash quranbot
sudo usermod -aG audio quranbot

# Switch to bot user
sudo su - quranbot
```

### 2. Clone Repository
```bash
# Clone the repository
git clone <your-repository-url> /home/quranbot/QuranBot
cd /home/quranbot/QuranBot

# Set proper permissions
chmod +x main.py
chmod -R 755 src/
```

### 3. Create Virtual Environment
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

## Configuration

### 1. Environment Variables
Create `/home/quranbot/QuranBot/.env`:

```bash
# === Core Bot Configuration ===
DISCORD_TOKEN=your_discord_bot_token_here
GUILD_ID=your_discord_server_id_here
ENVIRONMENT=production

# === Audio Configuration ===
AUDIO_FOLDER=/home/quranbot/QuranBot/audio
DEFAULT_RECITER=saad_al_ghamdi
FFMPEG_PATH=/usr/bin/ffmpeg
MAX_VOLUME=100

# === Database Configuration ===
DATABASE_URL=sqlite:///home/quranbot/QuranBot/data/quranbot.db

# === Security Configuration ===
RATE_LIMIT_ENABLED=true
MAX_REQUESTS_PER_MINUTE=30
BLOCKED_USERS=
BLOCKED_GUILDS=

# === Webhook Configuration (7 Channels) ===
WEBHOOK_BOT_STATUS=https://discord.com/api/webhooks/YOUR_BOT_STATUS_WEBHOOK
WEBHOOK_QURAN_AUDIO=https://discord.com/api/webhooks/YOUR_QURAN_AUDIO_WEBHOOK
WEBHOOK_COMMANDS_PANEL=https://discord.com/api/webhooks/YOUR_COMMANDS_PANEL_WEBHOOK
WEBHOOK_USER_ACTIVITY=https://discord.com/api/webhooks/YOUR_USER_ACTIVITY_WEBHOOK
WEBHOOK_DATA_ANALYTICS=https://discord.com/api/webhooks/YOUR_DATA_ANALYTICS_WEBHOOK
WEBHOOK_ERRORS_ALERTS=https://discord.com/api/webhooks/YOUR_ERRORS_ALERTS_WEBHOOK
WEBHOOK_DAILY_REPORTS=https://discord.com/api/webhooks/YOUR_DAILY_REPORTS_WEBHOOK

# === Fallback Webhook ===
FALLBACK_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_FALLBACK_WEBHOOK

# === Logging Configuration ===
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=/home/quranbot/QuranBot/logs/quranbot.log

# === Performance Configuration ===
CACHE_TTL=3600
MAX_CACHE_SIZE=1000
ENABLE_METRICS=true
```

### 2. Directory Structure
```bash
# Create required directories
mkdir -p /home/quranbot/QuranBot/{audio,data,logs,backups}

# Set permissions
chmod 755 /home/quranbot/QuranBot/{audio,data,logs,backups}
```

### 3. Audio Files Setup
```bash
# Place your Quran audio files in the audio directory
# Structure: audio/reciter_name/surah_number.mp3
# Example: audio/saad_al_ghamdi/001.mp3

# Ensure proper permissions
find /home/quranbot/QuranBot/audio -type f -name "*.mp3" -exec chmod 644 {} \;
```

## VPS Deployment

### 1. Systemd Service Configuration
Create `/etc/systemd/system/quranbot.service`:

```ini
[Unit]
Description=QuranBot Discord Audio Bot
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=quranbot
Group=quranbot
WorkingDirectory=/home/quranbot/QuranBot
Environment=PATH=/home/quranbot/QuranBot/.venv/bin
ExecStart=/home/quranbot/QuranBot/.venv/bin/python /home/quranbot/QuranBot/main.py
Restart=always
RestartSec=10
KillMode=mixed
TimeoutStopSec=30

# Resource limits
LimitNOFILE=65536
MemoryMax=2G
CPUQuota=200%

# Security settings
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/home/quranbot/QuranBot/data /home/quranbot/QuranBot/logs /home/quranbot/QuranBot/backups
PrivateTmp=yes
ProtectKernelTunables=yes
ProtectControlGroups=yes
RestrictSUIDSGID=yes

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=quranbot

[Install]
WantedBy=multi-user.target
```

### 2. Enable and Start Service
```bash
# Reload systemd configuration
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable quranbot

# Start the service
sudo systemctl start quranbot

# Check service status
sudo systemctl status quranbot
```

### 3. Firewall Configuration
```bash
# Allow SSH (if not already configured)
sudo ufw allow ssh

# Allow Discord API access (HTTPS outbound)
sudo ufw allow out 443

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

## Service Management

### Basic Commands
```bash
# Start the bot
sudo systemctl start quranbot

# Stop the bot
sudo systemctl stop quranbot

# Restart the bot
sudo systemctl restart quranbot

# Check status
sudo systemctl status quranbot

# View logs
sudo journalctl -u quranbot -f

# View recent logs
sudo journalctl -u quranbot --since="1 hour ago"
```

### Health Checks
```bash
# Check if process is running
ps aux | grep python | grep quranbot

# Check resource usage
htop -u quranbot

# Check network connections
sudo netstat -tulpn | grep python

# Check disk usage
df -h /home/quranbot/QuranBot/
```

## Monitoring & Logging

### 1. Log Rotation
Create `/etc/logrotate.d/quranbot`:

```
/home/quranbot/QuranBot/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    postrotate
        systemctl reload quranbot
    endscript
    su quranbot quranbot
}
```

### 2. System Monitoring Script
Create `/home/quranbot/QuranBot/scripts/monitor.sh`:

```bash
#!/bin/bash
# QuranBot monitoring script

LOGFILE="/home/quranbot/QuranBot/logs/monitor.log"
WEBHOOK_URL="YOUR_MONITORING_WEBHOOK_URL"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOGFILE"
}

check_service() {
    if ! systemctl is-active --quiet quranbot; then
        log_message "ERROR: QuranBot service is not running"
        # Send alert to Discord webhook
        curl -X POST "$WEBHOOK_URL" \
             -H "Content-Type: application/json" \
             -d '{"content": "🚨 **ALERT**: QuranBot service is DOWN! Attempting restart..."}'
        
        # Attempt restart
        systemctl restart quranbot
        sleep 10
        
        if systemctl is-active --quiet quranbot; then
            log_message "INFO: QuranBot service restarted successfully"
            curl -X POST "$WEBHOOK_URL" \
                 -H "Content-Type: application/json" \
                 -d '{"content": "✅ QuranBot service has been restarted successfully"}'
        else
            log_message "ERROR: Failed to restart QuranBot service"
            curl -X POST "$WEBHOOK_URL" \
                 -H "Content-Type: application/json" \
                 -d '{"content": "❌ **CRITICAL**: Failed to restart QuranBot service - Manual intervention required!"}'
        fi
    else
        log_message "INFO: QuranBot service is running normally"
    fi
}

check_disk_space() {
    USAGE=$(df /home/quranbot/QuranBot | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$USAGE" -gt 80 ]; then
        log_message "WARNING: Disk usage is at ${USAGE}%"
        curl -X POST "$WEBHOOK_URL" \
             -H "Content-Type: application/json" \
             -d "{\"content\": \"⚠️ **WARNING**: Disk usage is at ${USAGE}% - Consider cleanup\"}"
    fi
}

check_memory() {
    MEMORY_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    if [ "$MEMORY_USAGE" -gt 85 ]; then
        log_message "WARNING: Memory usage is at ${MEMORY_USAGE}%"
        curl -X POST "$WEBHOOK_URL" \
             -H "Content-Type: application/json" \
             -d "{\"content\": \"⚠️ **WARNING**: Memory usage is at ${MEMORY_USAGE}%\"}"
    fi
}

# Run checks
check_service
check_disk_space
check_memory

log_message "Monitoring check completed"
```

### 3. Cron Job for Monitoring
```bash
# Make script executable
chmod +x /home/quranbot/QuranBot/scripts/monitor.sh

# Add to crontab (runs every 5 minutes)
crontab -e
```

Add this line:
```
*/5 * * * * /home/quranbot/QuranBot/scripts/monitor.sh
```

## Backup & Recovery

### 1. Backup Script
Create `/home/quranbot/QuranBot/scripts/backup.sh`:

```bash
#!/bin/bash
# QuranBot backup script

BACKUP_DIR="/home/quranbot/QuranBot/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="quranbot_backup_$DATE.tar.gz"

# Create backup
tar -czf "$BACKUP_DIR/$BACKUP_FILE" \
    --exclude=".venv" \
    --exclude="logs" \
    --exclude="backups" \
    /home/quranbot/QuranBot/

# Keep only last 7 backups
cd "$BACKUP_DIR"
ls -t quranbot_backup_*.tar.gz | tail -n +8 | xargs rm -f --

echo "Backup created: $BACKUP_FILE"
```

### 2. Database Backup
```bash
# Backup SQLite database
cp /home/quranbot/QuranBot/data/quranbot.db /home/quranbot/QuranBot/backups/quranbot_db_$(date +%Y%m%d_%H%M%S).db
```

### 3. Recovery Process
```bash
# Stop the service
sudo systemctl stop quranbot

# Restore from backup
cd /home/quranbot
tar -xzf QuranBot/backups/quranbot_backup_YYYYMMDD_HHMMSS.tar.gz

# Restore permissions
chown -R quranbot:quranbot /home/quranbot/QuranBot
chmod +x /home/quranbot/QuranBot/main.py

# Start the service
sudo systemctl start quranbot
```

## Troubleshooting

### Common Issues

#### 1. Service Won't Start
```bash
# Check logs
sudo journalctl -u quranbot --no-pager -l

# Check configuration
cd /home/quranbot/QuranBot
source .venv/bin/activate
python -c "from src.config.bot_config import BotConfig; BotConfig()"

# Check permissions
ls -la /home/quranbot/QuranBot/
```

#### 2. Audio Playback Issues
```bash
# Check FFmpeg installation
ffmpeg -version

# Check audio files
ls -la /home/quranbot/QuranBot/audio/

# Test audio file
ffprobe /home/quranbot/QuranBot/audio/saad_al_ghamdi/001.mp3
```

#### 3. Database Issues
```bash
# Check database file
ls -la /home/quranbot/QuranBot/data/quranbot.db

# Test database connection
cd /home/quranbot/QuranBot
source .venv/bin/activate
python -c "from src.services.database_service import DatabaseService; print('DB OK')"
```

#### 4. Discord Connection Issues
```bash
# Test Discord token
cd /home/quranbot/QuranBot
source .venv/bin/activate
python -c "import discord; print('Discord.py version:', discord.__version__)"

# Check network connectivity
curl -I https://discord.com/api/v10/gateway
```

### Log Analysis
```bash
# View real-time logs
sudo journalctl -u quranbot -f

# Search for errors
sudo journalctl -u quranbot | grep -i error

# View logs from specific time
sudo journalctl -u quranbot --since "2024-01-01 12:00:00"

# Export logs to file
sudo journalctl -u quranbot > /tmp/quranbot_logs.txt
```

## Maintenance

### Regular Tasks

#### Daily
- Check service status
- Monitor resource usage
- Review error logs
- Verify webhook functionality

#### Weekly
- Update system packages
- Rotate logs
- Check backup integrity
- Review performance metrics

#### Monthly
- Update bot dependencies
- Clean old logs and backups
- Performance optimization review
- Security audit

### Update Procedure
```bash
# 1. Stop the service
sudo systemctl stop quranbot

# 2. Backup current installation
cd /home/quranbot
tar -czf QuranBot_backup_$(date +%Y%m%d).tar.gz QuranBot/

# 3. Pull updates
cd QuranBot
git pull origin main

# 4. Update dependencies
source .venv/bin/activate
pip install --upgrade -r requirements.txt

# 5. Run tests (if available)
python -m pytest tests/ --tb=short

# 6. Restart service
sudo systemctl start quranbot

# 7. Verify functionality
sudo systemctl status quranbot
```

### Performance Tuning
```bash
# Monitor resource usage
htop -u quranbot
iotop -u quranbot

# Check database performance
cd /home/quranbot/QuranBot
source .venv/bin/activate
python -c "
from src.services.database_service import DatabaseService
db = DatabaseService()
# Add performance monitoring code here
"

# Optimize SQLite database
sqlite3 /home/quranbot/QuranBot/data/quranbot.db "VACUUM; ANALYZE;"
```

## Security Considerations

### 1. File Permissions
```bash
# Set proper ownership
sudo chown -R quranbot:quranbot /home/quranbot/QuranBot

# Secure sensitive files
chmod 600 /home/quranbot/QuranBot/.env
chmod 755 /home/quranbot/QuranBot/main.py
```

### 2. Network Security
- Use UFW firewall
- Disable unnecessary services
- Keep system updated
- Monitor access logs

### 3. Bot Security
- Rotate Discord tokens regularly
- Use strong webhook URLs
- Monitor for unusual activity
- Implement rate limiting

## Support & Documentation

### Important Files
- **Configuration**: `/home/quranbot/QuranBot/.env`
- **Service File**: `/etc/systemd/system/quranbot.service`
- **Logs**: `/home/quranbot/QuranBot/logs/`
- **Database**: `/home/quranbot/QuranBot/data/quranbot.db`
- **Backups**: `/home/quranbot/QuranBot/backups/`

### Useful Commands Reference
```bash
# Service management
sudo systemctl {start|stop|restart|status} quranbot

# Log viewing
sudo journalctl -u quranbot {-f|--since="1 hour ago"|--no-pager}

# Process monitoring
ps aux | grep quranbot
htop -u quranbot

# Resource checks
df -h /home/quranbot/QuranBot/
free -h
```

### Contact Information
For support and issues:
- Check logs first: `sudo journalctl -u quranbot -f`
- Review configuration: `/home/quranbot/QuranBot/.env`
- Test components individually using the troubleshooting steps above

---

**Last Updated**: 2024-07-29  
**Version**: 1.0.0  
**Author**: QuranBot Development Team