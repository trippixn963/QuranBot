# 🚀 QuranBot Modernized Deployment Guide

This guide covers deployment of the modernized QuranBot architecture with dependency injection, microservices, and enterprise-grade features.

## 📋 Prerequisites

### **System Requirements**

- **OS**: Ubuntu 20.04+ / Debian 11+ (recommended for production)
- **Python**: 3.11 or higher
- **Memory**: Minimum 2GB RAM (4GB recommended)
- **Storage**: 10GB+ for audio files and logs
- **Network**: Stable internet connection for Discord API

### **Required Software**

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11+
sudo apt install python3.11 python3.11-venv python3.11-dev python3-pip

# Install FFmpeg for audio processing
sudo apt install ffmpeg

# Install Git
sudo apt install git

# Install Poetry (Python dependency manager)
curl -sSL https://install.python-poetry.org | python3 -
export PATH="$HOME/.local/bin:$PATH"
```

## 🏗️ Production Deployment

### **1. Create Project Directory**

```bash
# Create application directory
sudo mkdir -p /opt/QuranBot
sudo chown $USER:$USER /opt/QuranBot
cd /opt/QuranBot
```

### **2. Clone Repository**

```bash
# Clone the latest code
git clone https://github.com/your-username/QuranBot.git .

# Verify modernized files exist
ls -la main_modernized.py src/core/ src/services/
```

### **3. Setup Python Environment**

```bash
# Create virtual environment
python3.11 -m venv .venv

# Activate environment
source .venv/bin/activate

# Install Poetry in the environment
pip install poetry

# Install dependencies (production only)
poetry install --only=main --no-dev

# Verify installation
python -c "import discord; print('Discord.py version:', discord.__version__)"
```

### **4. Configure Environment**

```bash
# Copy environment template
cp config/.env.example config/.env

# Edit configuration (use nano, vim, or your preferred editor)
nano config/.env
```

#### **Production Configuration**

```bash
# Environment
ENVIRONMENT=production

# Discord Configuration
DISCORD_TOKEN=YOUR_ACTUAL_BOT_TOKEN
GUILD_ID=YOUR_SERVER_ID

# Discord Users & Permissions
ADMIN_USER_ID=YOUR_USER_ID
DEVELOPER_ID=YOUR_USER_ID
PANEL_ACCESS_ROLE_ID=YOUR_PANEL_ROLE_ID

# Discord Channel IDs
TARGET_CHANNEL_ID=YOUR_VOICE_CHANNEL_ID
PANEL_CHANNEL_ID=YOUR_CONTROL_PANEL_CHANNEL_ID
LOGS_CHANNEL_ID=YOUR_LOG_CHANNEL_ID
DAILY_VERSE_CHANNEL_ID=YOUR_VERSE_CHANNEL_ID

# Audio Configuration
AUDIO_FOLDER=audio
DEFAULT_RECITER=Saad Al Ghamdi
AUDIO_QUALITY=128k
DEFAULT_SHUFFLE=false
DEFAULT_LOOP=false
FFMPEG_PATH=/usr/bin/ffmpeg

# Performance Configuration
CACHE_TTL=300
MAX_CONCURRENT_AUDIO=1
BACKUP_INTERVAL_HOURS=24

# Security Configuration
RATE_LIMIT_PER_MINUTE=10

# Logging Configuration
LOG_LEVEL=INFO
USE_WEBHOOK_LOGGING=true
DISCORD_WEBHOOK_URL=YOUR_WEBHOOK_URL

# VPS Configuration (if using VPS deployment)
VPS_HOST=root@YOUR_VPS_IP
```

### **5. Create Systemd Service**

```bash
# Create service file
sudo nano /etc/systemd/system/quranbot.service
```

#### **Service Configuration**

```ini
[Unit]
Description=QuranBot - Modern Discord Bot
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/QuranBot
Environment=PATH=/opt/QuranBot/.venv/bin
ExecStart=/opt/QuranBot/.venv/bin/python main_modernized.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=quranbot

# Resource limits
MemoryMax=2G
CPUQuota=50%

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/QuranBot

[Install]
WantedBy=multi-user.target
```

### **6. Enable and Start Service**

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable quranbot

# Start service
sudo systemctl start quranbot

# Check status
sudo systemctl status quranbot

# View logs
sudo journalctl -u quranbot -f
```

## 🔧 Configuration Management

### **Environment Variables Explained**

#### **Core Configuration**

- `ENVIRONMENT`: Set to `production` for production deployments
- `DISCORD_TOKEN`: Your bot's authentication token from Discord Developer Portal
- `GUILD_ID`: The Discord server ID where the bot operates

#### **Audio System**

- `FFMPEG_PATH`: Path to FFmpeg binary (`/usr/bin/ffmpeg` on Linux)
- `AUDIO_FOLDER`: Directory containing Quran audio files
- `DEFAULT_RECITER`: Default reciter for audio playback

#### **Performance Tuning**

- `CACHE_TTL`: Cache time-to-live in seconds (300 = 5 minutes)
- `MAX_CONCURRENT_AUDIO`: Maximum simultaneous audio streams (1 recommended)
- `BACKUP_INTERVAL_HOURS`: How often to create state backups

#### **Security Settings**

- `RATE_LIMIT_PER_MINUTE`: Commands per user per minute (10 recommended)
- `LOG_LEVEL`: Logging verbosity (`INFO` for production)

## 📊 Monitoring & Maintenance

### **Service Management**

```bash
# Check service status
sudo systemctl status quranbot

# Restart service
sudo systemctl restart quranbot

# Stop service
sudo systemctl stop quranbot

# View real-time logs
sudo journalctl -u quranbot -f

# View recent logs
sudo journalctl -u quranbot -n 100

# Check resource usage
systemctl show quranbot --property=MainPID
top -p $(systemctl show quranbot --property=MainPID --value)
```

### **Log Analysis**

```bash
# Check structured logs
tail -f /opt/QuranBot/logs/quranbot.log | jq '.'

# Search for errors
journalctl -u quranbot --since "1 hour ago" | grep ERROR

# Monitor performance
journalctl -u quranbot --since today | grep "performance"
```

### **Health Checks**

```bash
# Check if bot is responding
curl -f http://localhost:8080/health || echo "Health check failed"

# Verify Discord connection
sudo journalctl -u quranbot -n 50 | grep "Bot connected"

# Check audio service status
sudo journalctl -u quranbot -n 100 | grep "AudioService"
```

## 🔄 Updates & Maintenance

### **Updating the Bot**

```bash
# Stop service
sudo systemctl stop quranbot

# Backup current version
cp -r /opt/QuranBot /opt/QuranBot.backup.$(date +%Y%m%d)

# Pull latest changes
cd /opt/QuranBot
git pull origin main

# Update dependencies
source .venv/bin/activate
poetry install --only=main --no-dev

# Restart service
sudo systemctl start quranbot

# Verify update
sudo systemctl status quranbot
```

### **Configuration Updates**

```bash
# Edit configuration
nano /opt/QuranBot/config/.env

# Restart service to apply changes
sudo systemctl restart quranbot

# Verify changes
sudo journalctl -u quranbot -f
```

## 🛡️ Security Best Practices

### **File Permissions**

```bash
# Secure configuration files
chmod 600 /opt/QuranBot/config/.env
chown root:root /opt/QuranBot/config/.env

# Secure application directory
chmod -R 755 /opt/QuranBot
chown -R root:root /opt/QuranBot

# Make logs readable by monitoring tools
chmod 644 /opt/QuranBot/logs/*.log
```

### **Firewall Configuration**

```bash
# Basic firewall setup (adjust ports as needed)
sudo ufw enable
sudo ufw allow ssh
# Web ports not needed - bot operates via Discord only
```

### **Regular Maintenance**

```bash
# Weekly log rotation
sudo logrotate -f /etc/logrotate.d/quranbot

# Monthly dependency updates
poetry update

# Quarterly backup verification
ls -la /opt/QuranBot/backup/
```

## 🚨 Troubleshooting

### **Common Issues**

#### **Service Won't Start**

```bash
# Check logs for errors
sudo journalctl -u quranbot -n 50

# Verify Python environment
/opt/QuranBot/.venv/bin/python --version

# Test configuration
cd /opt/QuranBot
source .venv/bin/activate
python -c "from src.config.config_service import ConfigService; print('Config OK')"
```

#### **Audio Issues**

```bash
# Verify FFmpeg installation
ffmpeg -version

# Check audio folder permissions
ls -la /opt/QuranBot/audio/

# Test audio service
cd /opt/QuranBot
source .venv/bin/activate
python -c "from src.services.audio_service import AudioService; print('Audio Service OK')"
```

#### **Discord Connection Issues**

```bash
# Verify bot token
grep DISCORD_TOKEN /opt/QuranBot/config/.env

# Check Discord API status
curl -s https://discordstatus.com/api/v2/status.json | jq '.status.indicator'

# Test bot permissions
sudo journalctl -u quranbot | grep -i "permission\|forbidden\|unauthorized"
```

### **Performance Issues**

```bash
# Check memory usage
free -h
ps aux | grep python

# Monitor CPU usage
top -p $(pgrep -f main_modernized.py)

# Check disk space
df -h /opt/QuranBot
```

## 📚 Additional Resources

- **[Architecture Documentation](ARCHITECTURE.md)**: Understanding the modernized architecture
- **[Development Guide](DEVELOPMENT_GUIDE.md)**: Local development setup
- **[Troubleshooting Guide](TROUBLESHOOTING.md)**: Detailed troubleshooting steps
- **[VPS Management](VPS_MANAGEMENT.md)**: Advanced VPS management techniques

## 🆘 Emergency Procedures

### **Quick Recovery**

```bash
# Emergency restart
sudo systemctl restart quranbot

# Restore from backup
sudo systemctl stop quranbot
cp -r /opt/QuranBot.backup.YYYYMMDD/* /opt/QuranBot/
sudo systemctl start quranbot

# Emergency stop
sudo systemctl stop quranbot
```

### **Contact Information**

- **GitHub Issues**: [Report problems](https://github.com/your-username/QuranBot/issues)
- **Documentation**: [Full documentation](../docs/)
- **Community**: Discord support server

---

**🚀 Your modernized QuranBot is now ready for 24/7 production operation!**
