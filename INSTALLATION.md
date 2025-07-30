# 🚀 QuranBot Installation Guide

Complete installation guide for setting up QuranBot on various platforms. This guide covers everything from basic setup to production deployment.

## 📋 **Table of Contents**
- [System Requirements](#-system-requirements)
- [Quick Start](#-quick-start)
- [Detailed Installation](#-detailed-installation)
- [Discord Bot Setup](#-discord-bot-setup)
- [Configuration](#-configuration)
- [Audio Files Setup](#-audio-files-setup)
- [Docker Installation](#-docker-installation)
- [Production Deployment](#-production-deployment)
- [Troubleshooting](#-troubleshooting)

---

## 🔧 **System Requirements**

### **Minimum Requirements**
- **Operating System**: Linux, macOS, or Windows 10+
- **Python**: 3.9 or higher
- **Memory**: 512MB RAM (1GB recommended)
- **Storage**: 2GB free space (for audio files and data)
- **Network**: Stable internet connection (1Mbps+ recommended)

### **Required Software**
- **Python 3.9+**: [Download here](https://python.org/downloads)
- **FFmpeg**: [Installation guide](https://ffmpeg.org/download.html)
- **Git**: [Download here](https://git-scm.com/downloads)

### **Platform-Specific Requirements**

#### **Ubuntu/Debian**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv ffmpeg git
```

#### **CentOS/RHEL/Fedora**
```bash
sudo dnf install python3 python3-pip ffmpeg git
# Or for older systems:
sudo yum install python3 python3-pip ffmpeg git
```

#### **macOS**
```bash
# Install Homebrew if not installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install requirements
brew install python ffmpeg git
```

#### **Windows**
1. Install Python from [python.org](https://python.org/downloads/)
2. Install FFmpeg:
   - Download from [ffmpeg.org](https://ffmpeg.org/download.html)
   - Add to PATH environment variable
3. Install Git from [git-scm.com](https://git-scm.com/downloads)

---

## ⚡ **Quick Start**

Get QuranBot running in 5 minutes:

```bash
# 1. Clone repository
git clone https://github.com/your-username/QuranBot.git
cd QuranBot

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure bot
cp config/.env.example config/.env
# Edit config/.env with your bot token and channel IDs

# 5. Run bot
python main.py
```

**🎉 That's it! Your bot should now be running.**

---

## 📖 **Detailed Installation**

### **Step 1: Repository Setup**

#### **Clone the Repository**
```bash
# Clone via HTTPS
git clone https://github.com/your-username/QuranBot.git

# Or clone via SSH (if you have SSH keys set up)
git clone git@github.com:your-username/QuranBot.git

# Navigate to directory
cd QuranBot
```

#### **Verify Installation**
```bash
# Check Python version
python --version  # Should be 3.9+

# Check FFmpeg installation
ffmpeg -version   # Should show FFmpeg information

# Check project structure
ls -la            # Should show main.py, src/, config/, etc.
```

### **Step 2: Python Environment Setup**

#### **Create Virtual Environment** (Recommended)
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Verify activation (should show (venv) in prompt)
which python              # Should point to venv/bin/python
```

#### **Install Dependencies**
```bash
# Upgrade pip
pip install --upgrade pip

# Install main dependencies
pip install -r requirements.txt

# Install development dependencies (optional)
pip install -r requirements-dev.txt
```

#### **Verify Installation**
```bash
# Check installed packages
pip list

# Test critical imports
python -c "import discord; print('Discord.py version:', discord.__version__)"
python -c "import asyncio; print('Asyncio available')"
```

---

## 🤖 **Discord Bot Setup**

### **Step 1: Create Discord Application**

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Enter name: "QuranBot" (or your preferred name)
4. Click "Create"

### **Step 2: Configure Bot**

1. Go to "Bot" section in left sidebar
2. Click "Add Bot"
3. Configure bot settings:
   - **Username**: QuranBot
   - **Avatar**: Upload Islamic-themed avatar (optional)
   - **Public Bot**: ❌ Disable (unless you want others to add your bot)

### **Step 3: Get Bot Token**

1. In "Bot" section, under "Token"
2. Click "Copy" to copy bot token
3. **⚠️ Keep this token secure! Never share it publicly.**

### **Step 4: Configure Bot Permissions**

#### **Required Permissions**
- `Send Messages` - For text responses
- `Use Slash Commands` - For modern Discord commands
- `Connect` - To join voice channels
- `Speak` - For audio playback
- `Add Reactions` - For interactive features

#### **Optional Permissions**
- `Manage Messages` - For message cleanup
- `Embed Links` - For rich embeds
- `Attach Files` - For file sharing
- `Use External Emojis` - For enhanced UI

### **Step 5: Bot Intents**

Enable these intents in the "Bot" section:
- **✅ Message Content Intent** - To read message content
- **✅ Server Members Intent** - For user management (if needed)
- **❌ Presence Intent** - Not needed for QuranBot

### **Step 6: Invite Bot to Server**

1. Go to "OAuth2" → "URL Generator"
2. Select scopes:
   - `bot`
   - `applications.commands`
3. Select permissions (same as Step 4)
4. Copy generated URL
5. Open URL in browser and invite bot to your server

---

## ⚙️ **Configuration**

### **Environment Configuration**

#### **Copy Example Configuration**
```bash
cp config/.env.example config/.env
```

#### **Edit Configuration File**
```bash
# Use your preferred editor
nano config/.env
# or
vim config/.env
# or
code config/.env  # VS Code
```

### **Essential Configuration Variables**

```bash
# =============================================================================
# DISCORD BOT CONFIGURATION
# =============================================================================

# Discord bot token from developer portal
DISCORD_TOKEN=your_discord_bot_token_here

# Discord server (guild) ID where bot operates
GUILD_ID=123456789012345678

# Voice channel ID for Quran recitation
TARGET_CHANNEL_ID=123456789012345678

# Text channel ID for control panel
PANEL_CHANNEL_ID=123456789012345678

# Text channel ID for daily verses
DAILY_VERSE_CHANNEL_ID=123456789012345678

# Your Discord user ID (for admin commands)
ADMIN_USER_ID=123456789012345678

# =============================================================================
# AUDIO CONFIGURATION
# =============================================================================

# Default reciter (see available options in config)
DEFAULT_RECITER=Saad Al Ghamdi

# Audio folder path
AUDIO_FOLDER=audio

# Default audio volume (0.0 to 1.0)
DEFAULT_VOLUME=0.5

# =============================================================================
# OPTIONAL FEATURES
# =============================================================================

# Enhanced webhook logging
USE_WEBHOOK_LOGGING=true
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_URL

# OpenAI integration for AI assistant
OPENAI_API_KEY=your_openai_api_key_here

# =============================================================================
# SYSTEM CONFIGURATION
# =============================================================================

# Environment (development/production)
ENVIRONMENT=production

# Logging level (DEBUG/INFO/WARNING/ERROR)
LOG_LEVEL=INFO

# Rate limiting (requests per minute per user)
RATE_LIMIT_PER_MINUTE=10
```

### **Configuration Validation**

```bash
# Test configuration
python -c "
from src.config import get_config_service
config = get_config_service()
print('✅ Configuration loaded successfully')
print(f'Discord Token: {'*'*20}{config.get_discord_token()[-4:]}')
print(f'Guild ID: {config.get_guild_id()}')
print(f'Target Channel: {config.get_target_channel_id()}')
"
```

---

## 🎵 **Audio Files Setup**

### **Audio Structure**

QuranBot expects audio files in this structure:
```
audio/
├── Saad Al Ghamdi/
│   ├── 001.mp3  # Al-Fatiha
│   ├── 002.mp3  # Al-Baqarah
│   └── ...      # Up to 114.mp3
├── Abdul Basit/
│   ├── 001.mp3
│   └── ...
└── Other Reciters/
    └── ...
```

### **Audio Requirements**

- **Format**: MP3, OGG, or FLAC
- **Quality**: 128kbps minimum (320kbps recommended)
- **Naming**: Use 3-digit numbers (001.mp3, 002.mp3, etc.)
- **Encoding**: UTF-8 metadata

### **Getting Audio Files**

#### **Option 1: Download from Islamic Websites**
- [Quran.com](https://quran.com) - Multiple reciters available
- [IslamicFinder](https://islamicfinder.org) - Audio downloads
- [TanzilNet](https://tanzil.net) - Various formats

#### **Option 2: Convert from Other Formats**
```bash
# Convert using FFmpeg
ffmpeg -i input.wav -c:a libmp3lame -b:a 192k output.mp3

# Batch conversion
for file in *.wav; do
    ffmpeg -i "$file" -c:a libmp3lame -b:a 192k "${file%.wav}.mp3"
done
```

#### **Option 3: Record Your Own**
If you have permission to record reciters, ensure:
- High-quality recording equipment
- Consistent audio levels
- Proper metadata tagging

### **Audio Validation**

```bash
# Test audio file structure
python -c "
from src.config import get_config_service
from pathlib import Path

config = get_config_service()
audio_folder = Path(config.get_audio_folder())

if audio_folder.exists():
    reciters = [d for d in audio_folder.iterdir() if d.is_dir()]
    print(f'✅ Found {len(reciters)} reciter folders')
    
    for reciter in reciters[:3]:  # Check first 3
        mp3_files = list(reciter.glob('*.mp3'))
        print(f'  📁 {reciter.name}: {len(mp3_files)} files')
else:
    print('❌ Audio folder not found')
"
```

---

## 🐳 **Docker Installation**

### **Option 1: Docker Compose** (Recommended)

#### **Using Provided Docker Files**
```bash
# Build and start containers
docker-compose up -d

# View logs
docker-compose logs -f quranbot

# Stop containers
docker-compose down
```

#### **Custom Docker Compose**
```yaml
# docker-compose.yml
version: '3.8'

services:
  quranbot:
    build: .
    container_name: quranbot
    restart: unless-stopped
    volumes:
      - ./config:/app/config
      - ./data:/app/data
      - ./audio:/app/audio
      - ./logs:/app/logs
    environment:
      - PYTHONUNBUFFERED=1
    networks:
      - quranbot_network

networks:
  quranbot_network:
    driver: bridge
```

### **Option 2: Manual Docker Build**

```bash
# Build image
docker build -t quranbot .

# Run container
docker run -d \
  --name quranbot \
  --restart unless-stopped \
  -v $(pwd)/config:/app/config:ro \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/audio:/app/audio:ro \
  -v $(pwd)/logs:/app/logs \
  quranbot

# View logs
docker logs -f quranbot
```

### **Docker Troubleshooting**

```bash
# Check container status
docker ps -a

# Enter container for debugging
docker exec -it quranbot /bin/bash

# Check container logs
docker logs --tail 100 quranbot

# Restart container
docker restart quranbot
```

---

## 🏭 **Production Deployment**

### **VPS Deployment**

#### **System Preparation**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install python3 python3-pip python3-venv ffmpeg git nginx -y

# Create user for bot
sudo useradd -m -s /bin/bash quranbot
sudo usermod -aG sudo quranbot
sudo su - quranbot
```

#### **Application Setup**
```bash
# Clone repository
cd /home/quranbot
git clone https://github.com/your-username/QuranBot.git
cd QuranBot

# Set up Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp config/.env.example config/.env
# Edit config/.env with production values
```

### **Process Management with PM2**

```bash
# Install PM2
npm install -g pm2

# Create PM2 ecosystem file
cat > ecosystem.config.js << 'EOF'
module.exports = {
  apps: [{
    name: 'quranbot',
    script: 'main.py',
    interpreter: 'python3',
    cwd: '/home/quranbot/QuranBot',
    instances: 1,
    exec_mode: 'fork',
    restart_delay: 5000,
    max_restarts: 10,
    min_uptime: '30s',
    env: {
      NODE_ENV: 'production',
      PYTHONPATH: '/home/quranbot/QuranBot'
    },
    log_file: 'logs/combined.log',
    out_file: 'logs/out.log',
    error_file: 'logs/error.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
  }]
};
EOF

# Start with PM2
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

### **Systemd Service** (Alternative to PM2)

```bash
# Create systemd service
sudo tee /etc/systemd/system/quranbot.service > /dev/null << 'EOF'
[Unit]
Description=QuranBot Discord Bot
After=network.target

[Service]
Type=simple
User=quranbot
WorkingDirectory=/home/quranbot/QuranBot
Environment=PATH=/home/quranbot/QuranBot/venv/bin
ExecStart=/home/quranbot/QuranBot/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable quranbot
sudo systemctl start quranbot

# Check status
sudo systemctl status quranbot
```

### **Reverse Proxy with Nginx** (Optional)

```bash
# Create Nginx configuration
sudo tee /etc/nginx/sites-available/quranbot << 'EOF'
server {
    listen 80;
    server_name your-domain.com;

    location /health {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        return 404;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/quranbot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 🔧 **Troubleshooting**

### **Common Issues**

#### **Bot Not Starting**

```bash
# Check Python version
python --version

# Check dependencies
pip list | grep discord

# Test basic import
python -c "import discord; print('OK')"

# Check configuration
python -c "from src.config import get_config_service; print('Config OK')"
```

#### **Audio Issues**

```bash
# Check FFmpeg
ffmpeg -version

# Test audio file
ffplay audio/Saad\ Al\ Ghamdi/001.mp3

# Check file permissions
ls -la audio/
```

#### **Discord Connection Issues**

```bash
# Test bot token
python -c "
import discord
import asyncio
import os

async def test_token():
    client = discord.Client(intents=discord.Intents.default())
    try:
        await client.login(os.getenv('DISCORD_TOKEN'))
        print('✅ Token is valid')
    except discord.LoginFailure:
        print('❌ Invalid token')
    finally:
        await client.close()

asyncio.run(test_token())
"
```

#### **Permission Issues**

```bash
# Check file permissions
ls -la config/.env
chmod 600 config/.env

# Check directory permissions
ls -la data/
mkdir -p data logs
chmod 755 data logs
```

### **Log Analysis**

```bash
# View recent logs
tail -f logs/quranbot.log

# Search for errors
grep -i error logs/quranbot.log

# Check Discord API errors
grep -i "discord" logs/quranbot.log | grep -i error
```

### **Performance Monitoring**

```bash
# Check system resources
htop
df -h
free -h

# Monitor bot process
ps aux | grep python
ps aux | grep main.py
```

### **Getting Help**

1. **Check Documentation**: Review all documentation files
2. **Search Issues**: Look through GitHub issues for similar problems
3. **Community Support**: Join Discord server for help
4. **Create Issue**: If problem persists, create detailed GitHub issue

---

## 📞 **Support & Resources**

### **Documentation**
- **[Main README](README.md)** - Project overview and features
- **[Contributing Guide](CONTRIBUTING.md)** - How to contribute
- **[Security Policy](SECURITY.md)** - Security guidelines
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Detailed troubleshooting

### **Community**
- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and community support
- **Discord Server**: Join our community at [discord.gg/syria](https://discord.gg/syria)

### **Resources**
- **[Discord.py Documentation](https://discordpy.readthedocs.io/)**
- **[FFmpeg Documentation](https://ffmpeg.org/documentation.html)**
- **[Python Virtual Environments](https://docs.python.org/3/tutorial/venv.html)**

---

## 🎉 **Success!**

If you've followed this guide, you should now have QuranBot running successfully! 

### **Next Steps**
1. **Test all features** - Try commands, audio playback, etc.
2. **Configure advanced features** - Set up webhooks, AI assistant
3. **Customize settings** - Adjust for your community's needs
4. **Join the community** - Connect with other QuranBot users
5. **Consider contributing** - Help improve QuranBot for everyone

**🕌 Welcome to the QuranBot community! May this bot serve your Islamic community well.**

---

*"And whoever does righteous deeds - whether male or female - while being a believer, those will enter Paradise and will not be wronged, [even as much as] the speck on a date seed."* - **Quran 4:124**