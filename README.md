# 📖 QuranBot - Discord 24/7 Quran Streaming Bot

> **🚨 Disclaimer:** This project is provided as-is, with no support or warranty. Issues and pull requests may not be reviewed or answered. See [SUPPORT.md](SUPPORT.md) for details.

A professional Discord bot for continuous Quran recitation with multiple reciters, interactive controls, and comprehensive monitoring.

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## 🤝 Contributing & Security

- See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.
- See [SECURITY.md](SECURITY.md) for security policy.
- See [SUPPORT.md](SUPPORT.md) for support policy.

---

## 🌟 Features

- **24/7 Quran Streaming** - Continuous playback of all 114 surahs
- **Multiple Reciters** - Support for 4+ professional reciters
- **Interactive Control Panel** - Rich Discord embed with playback controls
- **Slash Commands** - Modern Discord interaction system
- **Health Monitoring** - Real-time bot health and performance tracking
- **Auto-Reconnection** - Robust error handling and recovery
- **Rich Presence** - Dynamic Discord status updates
- **Comprehensive Logging** - Emoji-enhanced structured logging
- **VPS Ready** - Optimized for server deployment

## 🎵 Supported Reciters

- **Saad Al Ghamdi** - Beautiful, clear recitation
- **Maher Al Muaiqly** - Popular and melodious
- **Muhammad Al Luhaidan** - Traditional style
- **Rashid Al Afasy** - Modern and engaging

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- FFmpeg installed
- Discord Bot Token
- Discord Server with voice channel

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd QuranBot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Setup environment**
   ```bash
   cp .env.example .env
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

- **Surah Selection** - Paginated surah browser
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

# View logs
./scripts/vps/logs_bot.sh
```

## 📊 Monitoring & Logging

### Log Levels

- 🔍 **DEBUG** - Detailed debugging information
- ℹ️ **INFO** - General information
- ⚠️ **WARNING** - Warning messages
- ❌ **ERROR** - Error messages
- 🔥 **CRITICAL** - Critical errors

### Health Monitoring

- **Uptime tracking**
- **Memory usage**
- **CPU usage**
- **Connection status**
- **Audio playback status**
- **Error rate monitoring**

### Log Files

- **Daily rotation** - `logs/YYYY-MM-DD.log`
- **Console output** - Colored, emoji-enhanced
- **Structured data** - JSON-formatted for analysis

## 🔧 Development

### Code Style

- **Black** - Code formatting
- **Flake8** - Linting
- **Type hints** - Type annotations
- **Docstrings** - Comprehensive documentation

### Testing

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Format code
black src/

# Lint code
flake8 src/
```

### Adding New Reciters

1. **Add audio files** to `audio/Reciter Name/`
2. **Update config** in `src/utils/config.py`
3. **Test reciter** with control panel
4. **Update documentation**

## 🛠️ Troubleshooting

### Common Issues

**Bot won't connect to voice channel**
- Check channel permissions
- Verify bot token
- Ensure voice channel exists

**Audio not playing**
- Verify FFmpeg installation
- Check audio file format (MP3)
- Ensure file naming (1.mp3, 2.mp3, etc.)

**High memory usage**
- Monitor with `/status` command
- Check for memory leaks in logs
- Restart bot if necessary

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python run.py
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

- **Discord Server** - Join our community
- **Issues** - Report bugs on GitHub
- **Documentation** - Check the docs folder

## 🙏 Acknowledgments

- **Discord.py** - Excellent Discord API wrapper
- **FFmpeg** - Powerful audio processing
- **Quran Reciters** - Beautiful recitations
- **Community** - All contributors and users

---

**Made with ❤️ for the Muslim community** 