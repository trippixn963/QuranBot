# 🚀 QuranBot VPS Deployment Guide

*"And whoever relies upon Allah - then He is sufficient for him. Indeed, Allah will accomplish His purpose."* - **Quran 65:3**

## Overview

This guide provides comprehensive instructions for deploying QuranBot to a VPS (Virtual Private Server) for 24/7 operation. The deployment includes the bot service, web dashboard, monitoring, and automated management tools.

---

## 📋 Prerequisites

### VPS Requirements
- **Operating System**: Ubuntu 20.04+ (recommended)
- **RAM**: Minimum 1GB, recommended 2GB+
- **Storage**: Minimum 5GB free space
- **Network**: Stable internet connection
- **Access**: SSH access with sudo privileges

### Local Requirements
- Git installed
- SSH key configured for VPS access
- Discord bot token and server configuration

---

## 🏗️ Infrastructure Setup

### 1. VPS Provider Setup
We recommend **DigitalOcean** for reliable performance:

```bash
# Example DigitalOcean droplet creation
# - Ubuntu 22.04 LTS
# - 2GB RAM / 1 vCPU
# - 50GB SSD
# - $12/month (as of 2024)
```

### 2. Initial VPS Configuration

```bash
# Connect to your VPS
ssh root@your-vps-ip

# Update system packages
apt update && apt upgrade -y

# Install essential packages
apt install -y git python3 python3-pip python3-venv ffmpeg nginx ufw

# Configure firewall
ufw allow ssh
ufw allow 80
ufw allow 8080
ufw --force enable

# Create bot user (optional but recommended)
adduser quranbot
usermod -aG sudo quranbot
```

---

## 🤖 Bot Deployment

### 1. Clone Repository

```bash
# Switch to bot user (if created)
su - quranbot

# Clone the repository
git clone https://github.com/yourusername/QuranBot.git
cd QuranBot

# Or use the automated deployment script
curl -sSL https://raw.githubusercontent.com/yourusername/QuranBot/master/vps/deployment/deploy.sh | bash
```

### 2. Automated Deployment

The easiest method is using our automated deployment script:

```bash
# Download and run deployment script
wget https://raw.githubusercontent.com/yourusername/QuranBot/master/vps/deployment/deploy.sh
chmod +x deploy.sh
sudo ./deploy.sh

# Follow the interactive prompts
```

### 3. Manual Deployment

If you prefer manual setup:

```bash
# Create project directory
sudo mkdir -p /opt/DiscordBots/QuranBot
sudo chown $(whoami):$(whoami) /opt/DiscordBots/QuranBot
cd /opt/DiscordBots/QuranBot

# Clone repository
git clone https://github.com/yourusername/QuranBot.git .

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create configuration
cp config/.env.example config/.env
nano config/.env
```

---

## ⚙️ Configuration

### 1. Environment Configuration

Edit `config/.env` with your Discord bot settings:

```bash
# Discord Bot Configuration
DISCORD_TOKEN=your_discord_bot_token_here
GUILD_ID=your_discord_server_id
TARGET_CHANNEL_ID=voice_channel_id_for_audio
PANEL_CHANNEL_ID=text_channel_id_for_control_panel
LOGS_CHANNEL_ID=text_channel_id_for_logs
DEVELOPER_ID=your_discord_user_id

# Audio Configuration
FFMPEG_PATH=/usr/bin/ffmpeg
DEFAULT_RECITER=Saad Al Ghamdi
DEFAULT_SHUFFLE=false
DEFAULT_LOOP=false

# Optional Settings
DAILY_VERSE_CHANNEL_ID=0
PANEL_ACCESS_ROLE_ID=0
```

### 2. Audio Files Setup

```bash
# Ensure audio directory exists
mkdir -p audio

# Audio files should be organized as:
# audio/Reciter Name/001.mp3, 002.mp3, etc.
# Example structure:
# audio/
# ├── Saad Al Ghamdi/
# │   ├── 001.mp3  # Al-Fatihah
# │   ├── 002.mp3  # Al-Baqarah
# │   └── ...
# └── Abdul Basit Abdul Samad/
#     ├── 001.mp3
#     └── ...
```

---

## 🔧 Service Configuration

### 1. Bot Service Setup

```bash
# Copy systemd service file
sudo cp vps/systemd/quranbot.service /etc/systemd/system/

# Edit service file if needed
sudo nano /etc/systemd/system/quranbot.service

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable quranbot.service
sudo systemctl start quranbot.service
```

### 2. Dashboard Service Setup

```bash
# Copy dashboard service file
sudo cp vps/systemd/quranbot-dashboard.service /etc/systemd/system/

# Enable and start dashboard
sudo systemctl enable quranbot-dashboard.service
sudo systemctl start quranbot-dashboard.service
```

### 3. Nginx Configuration (Optional)

For custom domain or subdomain access:

```bash
# Run nginx setup script
sudo vps/nginx/setup-quranbot-nginx.sh your-domain.com

# Or for IP-based access with multiple bots
sudo vps/nginx/setup-ip-multi-bot.sh
```

---

## 🛠️ Management Tools

### 1. Shell Aliases

Install convenient management aliases:

```bash
# Install aliases
vps/scripts/manage_quranbot.sh aliases

# Reload shell
source ~/.bashrc

# Available commands:
qb-status    # Check bot status
qb-start     # Start bot service
qb-stop      # Stop bot service
qb-restart   # Restart bot service
qb-logs      # View bot logs
qb-errors    # View error logs
qb-dashboard # Access dashboard
qb-update    # Update bot from GitHub
```

### 2. Log Synchronization

Set up automatic log syncing to local machine:

```bash
# On your local machine
cd QuranBot
vps/scripts/local_log_sync.sh daemon

# This will continuously sync VPS logs to ./vps_logs/
```

### 3. Web Dashboard

Access the web dashboard at:
- **IP Access**: `http://your-vps-ip:8080`
- **Domain Access**: `http://your-domain.com` (if nginx configured)

---

## 📊 Monitoring & Maintenance

### 1. Service Status Monitoring

```bash
# Check all services
qb-status

# Check individual services
sudo systemctl status quranbot.service
sudo systemctl status quranbot-dashboard.service

# View real-time logs
qb-logs -f
```

### 2. Resource Monitoring

```bash
# Check system resources
htop

# Check disk usage
df -h

# Check memory usage
free -h

# Check bot-specific resource usage
ps aux | grep python
```

### 3. Automated Backups

The bot automatically creates backups:
- **Location**: `/opt/DiscordBots/QuranBot/backup/`
- **Schedule**: Hourly ZIP backups
- **Retention**: 7 days automatic cleanup

### 4. Log Management

- **Bot Logs**: `/opt/DiscordBots/QuranBot/logs/YYYY-MM-DD/`
- **Dashboard Logs**: `/opt/DiscordBots/QuranBot/web_dashboard/logs/YYYY-MM-DD/`
- **System Logs**: `journalctl -u quranbot.service`

---

## 🔄 Updates & Maintenance

### 1. Updating the Bot

```bash
# Using management script
qb-update

# Or manually
cd /opt/DiscordBots/QuranBot
git pull origin master
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart quranbot.service
sudo systemctl restart quranbot-dashboard.service
```

### 2. Backup Before Updates

```bash
# Create manual backup
cp -r /opt/DiscordBots/QuranBot /opt/DiscordBots/QuranBot.backup.$(date +%Y%m%d)

# Or use the backup manager
cd /opt/DiscordBots/QuranBot
python -c "from src.utils.backup_manager import BackupManager; BackupManager().create_manual_backup()"
```

---

## 🚨 Troubleshooting

### Common Issues

1. **Bot Not Starting**
   ```bash
   # Check service status
   sudo systemctl status quranbot.service
   
   # Check logs
   qb-logs
   
   # Check configuration
   cat config/.env
   ```

2. **Audio Not Playing**
   ```bash
   # Check FFmpeg installation
   which ffmpeg
   
   # Check audio files
   ls -la audio/
   
   # Check permissions
   sudo chown -R $(whoami):$(whoami) audio/
   ```

3. **Dashboard Not Accessible**
   ```bash
   # Check dashboard service
   sudo systemctl status quranbot-dashboard.service
   
   # Check port availability
   sudo netstat -tlnp | grep 8080
   
   # Check firewall
   sudo ufw status
   ```

4. **High Memory Usage**
   ```bash
   # Restart services
   qb-restart
   
   # Check for memory leaks
   ps aux --sort=-%mem | head
   ```

### Log Analysis

```bash
# Search for specific errors
qb-logs | grep -i error

# Check recent activity
qb-logs | tail -100

# Monitor real-time
qb-logs -f
```

---

## 🔐 Security Considerations

### 1. Firewall Configuration

```bash
# Essential ports only
sudo ufw allow ssh
sudo ufw allow 80    # HTTP (if using nginx)
sudo ufw allow 8080  # Dashboard (optional, can be restricted)

# Restrict dashboard access to specific IPs
sudo ufw allow from YOUR_IP to any port 8080
```

### 2. SSH Security

```bash
# Disable password authentication (use keys only)
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
sudo systemctl restart ssh
```

### 3. Bot Token Security

```bash
# Ensure .env file permissions
chmod 600 config/.env

# Never commit .env to git
echo "config/.env" >> .gitignore
```

---

## 📞 Support & Resources

### Management Commands Quick Reference

```bash
qb-status     # Check status
qb-start      # Start bot
qb-stop       # Stop bot  
qb-restart    # Restart bot
qb-logs       # View logs
qb-errors     # View errors
qb-dashboard  # Dashboard URL
qb-update     # Update from GitHub
```

### Important Paths

- **Bot Directory**: `/opt/DiscordBots/QuranBot/`
- **Configuration**: `/opt/DiscordBots/QuranBot/config/.env`
- **Logs**: `/opt/DiscordBots/QuranBot/logs/`
- **Audio**: `/opt/DiscordBots/QuranBot/audio/`
- **Backups**: `/opt/DiscordBots/QuranBot/backup/`

### Service Files

- **Bot Service**: `/etc/systemd/system/quranbot.service`
- **Dashboard Service**: `/etc/systemd/system/quranbot-dashboard.service`

---

## 🎯 Next Steps

After successful deployment:

1. **Test Bot Functionality**: Join voice channel and test audio commands
2. **Configure Dashboard**: Access web dashboard and verify all features
3. **Set Up Monitoring**: Configure log syncing and alerts
4. **Schedule Backups**: Verify automatic backup system
5. **Performance Tuning**: Monitor resources and optimize as needed

---

*May Allah bless your efforts in serving the Muslim community with this Islamic bot. Remember to make du'a for the success of this project and all those who benefit from it.*

**"And it is He who created the heavens and earth in truth. And the day He says, 'Be,' and it is, His word is the truth."** - *Quran 6:73* 