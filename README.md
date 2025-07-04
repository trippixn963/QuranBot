# 🕌 QuranBot

<div align="center">
  <img src="images/BANNER (ANIMATED).gif" alt="QuranBot Animated Banner" width="800"/>
  
  **24/7 Quran Streaming Bot with Interactive Controls**
  
  [![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/downloads/)
  [![Discord.py](https://img.shields.io/badge/Discord.py-2.3+-green.svg)](https://discordpy.readthedocs.io/)
  [![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
  [![Security](https://img.shields.io/badge/Security-Safe-brightgreen.svg)](SECURITY.md)
  
  *Built with ❤️ for the Muslim Ummah*
</div>

---

## 📖 Table of Contents
- [Features](#-features)
- [Quick Start](#-quick-start)
- [Project Structure](#-project-structure)
- [Configuration](#-configuration)
- [Commands](#-commands)
- [Security](#-security)
- [Contributing](#-contributing)
- [Support](#-support)
- [License](#-license)

## 🌟 Features

### 🎵 **Audio Streaming**
- **24/7 Quran Recitation** - Continuous stream of beautiful recitations
- **Multiple Reciters** - Choose from various renowned Qaris
- **Complete Quran** - All 114 surahs with proper Arabic pronunciation
- **Auto-Resume** - Remembers position after restarts

### 🎮 **Interactive Controls**
- **Discord UI** - Beautiful embeds with buttons and dropdowns
- **Real-time Control** - Play, pause, skip, previous, volume
- **Surah Selection** - Easy navigation through all surahs
- **Reciter Switching** - Change reciters without interruption

### 📊 **Smart Features**
- **Daily Verses** - Automated verse sharing with translations
- **Quran Questions** - Interactive knowledge testing
- **Progress Tracking** - Monitor listening progress
- **Health Monitoring** - System status and performance tracking

## 🚀 Quick Start

### Prerequisites
- Python 3.13+
- FFmpeg
- Discord Bot Token
- Server with voice channel permissions

### Basic Setup

1. **Clone & Install**
   ```bash
   git clone https://github.com/yourusername/QuranBot.git
   cd QuranBot
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   ```bash
   cp env_template.txt .env
   # Edit .env with your settings
   ```

3. **Add Audio Files**
   ```
   audio/
   ├── Reciter1/
   │   ├── 001.mp3  # Al-Fatiha
   │   ├── 002.mp3  # Al-Baqarah
   │   └── ...
   ├── Reciter2/
   └── ...
   ```

4. **Start Bot**
   ```bash
   python run.py
   ```

For detailed setup instructions, see [SECURITY_SETUP.md](SECURITY_SETUP.md).

## 📁 Project Structure

```
QuranBot/
├── 📂 src/                      # Source code
│   ├── bot/                     # Core bot functionality
│   ├── cogs/                    # Discord commands
│   │   ├── admin/              # Admin features
│   │   └── user/               # User features
│   ├── core/                    # Core systems
│   └── monitoring/              # Logging & health
│
├── 📂 data/                     # Bot data
│   ├── daily_verses_pool.json   # Verse database
│   ├── quran_questions.json     # Questions
│   └── custom_surah_mapping.json # Surah mappings
│
├── 📂 scripts/                  # Utility scripts
│   ├── local/                  # Local tools
│   └── vps/                    # Deployment tools
│
├── 📂 audio/                    # Quran MP3s
├── 📂 images/                   # Bot assets
├── 📂 logs/                     # Log files
│
├── 📄 run.py                    # Entry point
├── 📄 requirements.txt          # Dependencies
├── 📄 SECURITY_SETUP.md         # Security guide
└── 📄 README.md                 # This file
```

## ⚙️ Configuration

### Required Environment Variables
```env
# Core Settings
DISCORD_BOT_TOKEN=your_bot_token
DEVELOPER_ID=your_discord_id

# Channel IDs
AUDIO_CHANNEL_ID=voice_channel_id
PANEL_CHANNEL_ID=control_panel_channel_id
```

### Optional Settings
```env
# FFmpeg (Auto-detected if not set)
FFMPEG_PATH=path_to_ffmpeg

# Features
AUTO_VOICE_CONNECT=true
AUTO_RECONNECT=true
LOG_LEVEL=INFO
```

## 🎮 Commands

### User Commands
| Command        | Description                |
|---------------|----------------------------|
| `/credits`    | Show bot credits           |
| `/leaderboard`| Show Quran MCQ leaderboard |

*All other commands are restricted to the bot owner.*

### Admin/Owner Commands
| Command         | Description                                      |
|----------------|--------------------------------------------------|
| `/sendverse`   | Send a verse now (admin only)                    |
| `/versestatus` | Check daily verse status                         |
| `/status`      | Get comprehensive bot and system status          |
| `/info`        | Get bot logs and configuration                   |
| `/logs`        | View logs, system info, and bot status           |
| `/restart`     | Restart the Quran Bot                            |
| `/stop`        | Stop the Quran Bot                               |
| `/reconnect`   | Reconnect to voice channel                       |
| `/recreatepanel`| Recreate the control panel                      |

*Admin/owner commands are only available to the bot owner (you).*

## 🔒 Security

This bot follows security best practices:

### ✅ **Security Features**
- **No sensitive data in git** - All secrets excluded via .gitignore
- **Environment-based configuration** - Secure credential management
- **VPS deployment options** - Production-ready deployment
- **Regular security updates** - Automated dependency updates
- **Comprehensive logging** - Audit trail for all operations

### 🛡️ **Protected Data**
- Discord bot tokens
- SSH keys and certificates
- VPS credentials
- User session data
- Bot state files
- Audio files (large size)

### 📋 **Security Checklist**
- [x] Environment variables for secrets
- [x] .gitignore excludes sensitive files
- [x] No hardcoded credentials
- [x] Secure VPS deployment
- [x] Regular backup system
- [x] Health monitoring

See [SECURITY_SETUP.md](SECURITY_SETUP.md) for complete security documentation.

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### 🎯 **How to Contribute**
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 💬 Support

- 📖 [Documentation](docs/)
- 🐛 [Issue Tracker](../../issues)
- 💡 [Feature Requests](../../issues)
- 📧 [Email Support](mailto:support@quranbot.com)

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

---

<div align="center">
  <img src="images/PFP (Cropped - Animated).gif" alt="QuranBot Logo" width="100"/>
  
  **Made with ❤️ for the Muslim community**
  
  *May Allah bless this project and all who use it*
</div> 