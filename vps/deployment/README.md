# DiscordBots Deployment Guide

This guide covers deploying QuranBot to the `/opt/DiscordBots/QuranBot` structure on your VPS for scalable multi-bot management.

## Quick Start

1. **Deploy QuranBot to VPS:**
   ```bash
   ./vps/deployment/deploy-to-discordbots.sh
   ```

2. **Set up Multi-Bot Dashboard:**
   ```bash
   # On your VPS (as root):
   ./vps/nginx/setup-ip-multi-bot.sh
   ```

3. **Access your dashboards:**
   - Main Dashboard: `http://159.89.90.90/`
   - QuranBot: `http://159.89.90.90/quranbot/`

## Directory Structure

```
/opt/DiscordBots/QuranBot/
├── src/                    # Python source code
│   ├── bot/               # Bot core
│   ├── commands/          # Discord commands
│   └── utils/             # Utilities and managers
├── config/                # Configuration files
│   └── .env              # Environment variables
├── logs/                  # Bot logs
├── audio/                 # Audio files
├── backup/                # Backup files
├── data/                  # Data files
├── images/                # Bot images
├── tests/                 # Test files
├── tools/                 # Development tools
├── vps_logs/              # VPS-specific logs
├── main.py                # Main entry point
├── requirements.txt       # Python dependencies
└── .venv/                 # Virtual environment
```

## Deployment Features

### ✅ Complete File Transfer
- All Python source code
- Configuration files (including .env)
- Audio files and media
- Data and backup files
- Test files and tools

### ✅ Environment Setup
- Python virtual environment creation
- Dependency installation
- FFmpeg path correction for Linux
- Proper file permissions

### ✅ Service Management
- Systemd service creation
- Auto-start on boot
- Resource limits (512MB RAM, 50% CPU)
- Security hardening

### ✅ Multi-Bot Ready
- Scalable directory structure
- Nginx reverse proxy
- Port-based routing
- Future bot support

## Usage

### Deploy QuranBot
```bash
# Run from your local QuranBot directory
./vps/deployment/deploy-to-discordbots.sh
```

**What it does:**
1. Creates `/opt/DiscordBots/QuranBot/` structure
2. Transfers all files via rsync
3. Sets up Python virtual environment
4. Installs dependencies
5. Creates systemd service
6. Tests deployment

### Set up Multi-Bot Dashboard
```bash
# Run on VPS as root
./vps/nginx/setup-ip-multi-bot.sh
```

**What it provides:**
- Main dashboard at `http://YOUR_VPS_IP/`
- Individual bot dashboards at `http://YOUR_VPS_IP/botname/`
- Real-time status checking
- Professional web interface
- Mobile-responsive design

## Bot Management

### Start/Stop Bot
```bash
# Start bot
sudo systemctl start quranbot

# Stop bot
sudo systemctl stop quranbot

# Restart bot
sudo systemctl restart quranbot

# Check status
sudo systemctl status quranbot
```

### View Logs
```bash
# Real-time logs
sudo journalctl -u quranbot -f

# Recent logs
sudo journalctl -u quranbot -n 100

# Logs since yesterday
sudo journalctl -u quranbot --since yesterday
```

### Update Bot
```bash
# Re-run deployment script
./vps/deployment/deploy-to-discordbots.sh

# Restart service
sudo systemctl restart quranbot
```

## Dashboard Access

### Main Dashboard
- **URL:** `http://159.89.90.90/`
- **Features:**
  - Overview of all bots
  - Real-time status checking
  - Professional interface
  - Mobile responsive

### QuranBot Dashboard
- **URL:** `http://159.89.90.90/quranbot/`
- **Features:**
  - Bot status and controls
  - System monitoring
  - User activity tracking
  - Audio management
  - Log viewer

## Adding More Bots

### Directory Structure
```bash
# Create new bot directory
sudo mkdir -p /opt/DiscordBots/MusicBot
sudo mkdir -p /opt/DiscordBots/GameBot
```

### Port Assignment
- QuranBot: Port 8080
- MusicBot: Port 8081
- GameBot: Port 8082
- Future bots: Port 8083+

### Nginx Configuration
The IP-based setup automatically routes:
- `/musicbot/` → `localhost:8081`
- `/gamebot/` → `localhost:8082`

## Troubleshooting

### Connection Issues
```bash
# Check if bot is running
sudo systemctl status quranbot

# Check if dashboard is accessible
curl http://localhost:8080/api/status

# Check Nginx status
sudo systemctl status nginx
```

### File Permissions
```bash
# Fix permissions
sudo chown -R root:root /opt/DiscordBots/QuranBot
sudo chmod -R 755 /opt/DiscordBots/QuranBot
sudo chmod 600 /opt/DiscordBots/QuranBot/config/.env
```

### Dependencies
```bash
# Reinstall dependencies
cd /opt/DiscordBots/QuranBot
source .venv/bin/activate
pip install -r requirements.txt
```

## Security Notes

- Bot runs as root user (change if needed)
- .env file has restricted permissions (600)
- Nginx provides security headers
- Systemd service has resource limits
- Private tmp directory for bot processes

## Future Expansion

This structure supports:
- Multiple Discord bots
- Centralized management
- Scalable architecture
- Professional dashboards
- Easy maintenance

Add new bots by:
1. Creating `/opt/DiscordBots/BotName/` directory
2. Assigning unique port number
3. Creating systemd service
4. Updating Nginx configuration (if needed)

## Support

For issues:
1. Check systemd logs: `journalctl -u quranbot`
2. Check Nginx logs: `/var/log/nginx/multi_bots_*.log`
3. Verify file permissions and paths
4. Test network connectivity 