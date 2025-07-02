# 📖 QuranBot - Discord 24/7 Quran Streaming Bot

<div align="center">
  <img src="images/BANNER (Still).png" alt="QuranBot Banner" width="800"/>
  
  [![MIT License](https://img.shields.io/github/license/JohnHamwi/QuranAudioBot)](LICENSE)
  [![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
  [![Last Commit](https://img.shields.io/github/last-commit/JohnHamwi/QuranAudioBot)](https://github.com/JohnHamwi/QuranAudioBot/commits/master)
  [![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
  [![Discord.py](https://img.shields.io/badge/discord.py-2.3.0%2B-blue)](https://discordpy.readthedocs.io/)
  [![Stability](https://img.shields.io/badge/stability-production%20ready-brightgreen)](https://github.com/JohnHamwi/QuranAudioBot)
</div>

> **🚨 Disclaimer:** This project is provided as-is, with no support or warranty. Issues and pull requests may not be reviewed or answered. See [SUPPORT.md](SUPPORT.md) for details.

A professional Discord bot for continuous Quran recitation with multiple reciters, interactive controls, and comprehensive monitoring. Built with enterprise-grade stability and reliability.

## 🌟 Key Features

### 🎵 **Audio Excellence**
- **24/7 Quran Streaming** - Continuous playback of all 114 surahs
- **Multiple Professional Reciters** - Support for 4+ high-quality reciters
- **Seamless Audio Transitions** - No gaps or interruptions between surahs
- **High-Quality Audio Processing** - FFmpeg-powered audio streaming

### 🎮 **Interactive Experience**
- **Rich Control Panel** - Beautiful Discord embeds with playback controls
- **Slash Commands** - Modern Discord interaction system
- **Real-time Status Updates** - Dynamic presence with current surah info
- **User Activity Tracking** - Monitor voice channel activity with duration tracking

### 🛡️ **Enterprise Stability** ⭐ **LATEST**
- **Robust Connection Handling** - Advanced voice connection management with heartbeat monitoring
- **Automatic Error Recovery** - Self-healing from network issues and Discord API hiccups
- **FFmpeg Process Management** - Comprehensive audio process cleanup prevents conflicts
- **Network Resilience** - Exponential backoff retry logic with configurable timeouts
- **Health Monitoring** - Real-time bot health and performance tracking
- **Auto-Reconnection** - Intelligent reconnection with connection stability monitoring
- **Playback Locking** - Prevents multiple surahs from playing simultaneously
- **Voice Session Management** - Handles Discord voice session expirations gracefully

### 🎨 **Professional UI**
- **Branded Embeds** - Consistent, beautiful Discord embeds
- **Avatar Integration** - User profile pictures in interactions
- **Dynamic Presence** - Themed emojis and real surah names
- **Rich Notifications** - Surah change alerts with reciter info

## 🎵 Supported Reciters

<div align="center">
  <table>
    <tr>
      <td><strong>Saad Al Ghamdi</strong></td>
      <td><strong>Maher Al Muaiqly</strong></td>
      <td><strong>Muhammad Al Luhaidan</strong></td>
      <td><strong>Rashid Al Afasy</strong></td>
    </tr>
    <tr>
      <td>Beautiful, clear recitation</td>
      <td>Popular and melodious</td>
      <td>Traditional style</td>
      <td>Modern and engaging</td>
    </tr>
    <tr>
      <td><strong>Abdul Basit Abdul Samad</strong></td>
      <td><strong>Yasser Al Dosari</strong></td>
      <td colspan="2"></td>
    </tr>
    <tr>
      <td>Legendary classical style</td>
      <td>Contemporary and powerful</td>
      <td colspan="2"></td>
    </tr>
  </table>
</div>

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- FFmpeg installed
- Discord Bot Token
- Discord Server with voice channel

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/JohnHamwi/QuranAudioBot.git
   cd QuranAudioBot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Setup environment**
   ```bash
   cp env_template.txt .env
   # Edit .env with your Discord bot configuration
   ```

4. **Add audio files**
   - Create `audio/` directory
   - Add reciter folders with MP3 files (1-114.mp3)

5. **Run the bot**
   ```bash
   python run.py
   ```

## ⚙️ Configuration

### Environment Variables (.env)

```env
# Discord Configuration
DISCORD_TOKEN=your_bot_token_here
TARGET_CHANNEL_ID=your_voice_channel_id
PANEL_CHANNEL_ID=your_control_panel_channel_id
LOGS_CHANNEL_ID=your_logs_channel_id

# Audio Configuration
AUDIO_FOLDER=audio
DEFAULT_RECITER=Saad Al Ghamdi
AUDIO_QUALITY=128k

# FFmpeg Configuration
FFMPEG_PATH=C:\ffmpeg\bin  # Windows
# FFMPEG_PATH=/usr/bin     # Linux/macOS
```

### Audio File Structure

```
audio/
├── Saad Al Ghamdi/
│   ├── 1.mp3
│   ├── 2.mp3
│   └── ... (114.mp3)
├── Maher Al Muaiqly/
│   ├── 1.mp3
│   └── ... (114.mp3)
└── ... (other reciters)
```

## 🎮 Commands

### Slash Commands

- `/control` - Open interactive control panel
- `/status` - Show bot status and health
- `/restart` - Restart the bot (Admin only)
- `/skip` - Skip current surah
- `/reconnect` - Reconnect to voice channel
- `/credits` - Show bot credits
- `/logs` - View recent logs

### Control Panel Features

- **Surah Selection** - Paginated surah browser with emojis
- **Reciter Selection** - Dropdown with available reciters
- **Playback Controls** - Play, pause, skip, loop
- **Real-time Status** - Current surah and reciter info

## 🏗️ Project Structure

```
QuranBot/
├── src/
│   ├── bot/
│   │   └── quran_bot.py          # Main bot implementation
│   ├── cogs/
│   │   ├── admin_commands/       # Admin slash commands
│   │   ├── user_commands/        # User slash commands
│   │   └── utility_commands/     # Utility commands
│   └── utils/
│       ├── config.py             # Configuration management
│       ├── logger.py             # Enhanced logging system
│       ├── health.py             # Health monitoring
│       ├── state_manager.py      # Bot state persistence
│       └── surah_mapper.py       # Surah name mapping
├── scripts/
│   ├── vps/                      # VPS management scripts
│   ├── windows/                  # Windows utilities
│   ├── linux/                    # Linux utilities
│   └── macos/                    # macOS utilities
├── audio/                        # Audio files (not in git)
├── logs/                         # Log files
├── backup/                       # Backup versions
├── requirements.txt              # Python dependencies
├── run.py                        # Entry point
└── README.md                     # This file
```

## 🖥️ VPS Deployment

### Automated Setup

```bash
# Upload files to VPS
scp -r . root@your-vps-ip:/opt/quranbot/

# Run setup script
ssh root@your-vps-ip "cd /opt/quranbot && chmod +x deploy_temp/setup_vps.sh && ./deploy_temp/setup_vps.sh"
```

### Manual Setup

1. **Install system dependencies**
   ```bash
   apt update && apt upgrade -y
   apt install -y python3 python3-pip python3-venv ffmpeg
   ```

2. **Setup Python environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Create systemd service**
   ```bash
   # Copy the service file from deploy_temp/setup_vps.sh
   systemctl daemon-reload
   systemctl enable quranbot
   systemctl start quranbot
   ```

### VPS Management Scripts

```bash
# Start bot
./scripts/vps/start_bot.sh

# Stop bot
./scripts/vps/stop_bot.sh

# Restart bot
./scripts/vps/restart_bot.sh

# Check status
./scripts/vps/status_bot.sh
```

## 🔧 Advanced Features

### Stability Improvements ⭐ **Latest**

- **Connection Monitoring** - Continuous heartbeat checks every 30 seconds
- **Robust Error Recovery** - Handles Discord API issues gracefully
- **FFmpeg Process Management** - Prevents audio conflicts and memory leaks
- **Network Resilience** - Exponential backoff for connection retries
- **Health Monitoring** - Real-time performance and error tracking
- **Playback Locking** - Ensures only one surah plays at a time
- **Voice Session Management** - Handles Discord session expirations

### Monitoring & Logging

- **Structured Logging** - Enhanced logging with user avatars and context
- **Performance Tracking** - Monitor operation timing and bottlenecks
- **Error Reporting** - Comprehensive error tracking and reporting
- **Health Dashboard** - Real-time bot health status

### User Experience

- **Voice Activity Tracking** - Monitor user joins/leaves with duration
- **Interaction Counting** - Track user engagement with the bot
- **Professional Embeds** - Beautiful, branded Discord embeds
- **Dynamic Presence** - Real-time status updates with surah info

## 📊 Performance Metrics

- **Uptime**: 99.9%+ with auto-reconnection
- **Audio Quality**: High-quality MP3 streaming
- **Response Time**: <1 second for commands
- **Memory Usage**: Optimized for 24/7 operation
- **Network Resilience**: Handles Discord API hiccups

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support information, see [SUPPORT.md](SUPPORT.md).

---

<div align="center">
  <p><strong>Built with ❤️ for the Muslim community</strong></p>
  <p>May Allah bless this project and all who use it</p>
  
  <img src="images/PFP (Full - Still).png" alt="QuranBot Profile" width="200"/>
</div> 