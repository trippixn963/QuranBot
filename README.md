<div align="center">

![QuranBot Banner](<images/BANNER%20(ANIMATED).gif>)

# 🕌 QuranBot

**A Discord Bot for 24/7 Quran Audio Streaming with Interactive Control Panel**

[![Version](https://img.shields.io/badge/version-3.0.0-blue.svg)](#)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![No Support](https://img.shields.io/badge/support-NONE-red.svg)](#)
[![Muslim Ummah](https://img.shields.io/badge/built%20for-Muslim%20Ummah-green.svg)](#)

_Built with ❤️ for the Muslim Ummah - Shared as-is for educational purposes_

</div>

---

## 📝 Version History

### Latest Release: v3.0.0 (2025-07-08)

Major release with complete quiz system overhaul, leaderboard improvements, enhanced daily verses, and robust error handling.

**Key Features:**

- 📝 Dynamic quiz system with real-time updates
- 🏆 Points-based leaderboard with streaks
- 📊 Enhanced daily verses scheduling
- 🛡️ Comprehensive error handling
- 🎨 Polished UI/UX across all features

### Previous Versions

#### v2.3.2 (2025-01-07)

- ✨ Enhanced credits command spacing and readability
- 📱 Improved visual separators in embeds
- 🎨 Maintained clean, professional design

#### v2.3.1 (2025-01-07)

- 📖 Fixed truncated verses in daily verse database
- ✅ Complete Arabic text and translations
- 🔍 Eliminated truncation issues

#### v2.3.0 (2025-01-07)

- ⚡ Fixed command registration and timing
- 🕐 Added EST timezone support
- 👤 Enhanced embed styling with profile pictures

[View Full Changelog](CHANGELOG.md)

---

## ⚠️ No Support Policy

> **🚨 CRITICAL NOTICE: "TAKE AS IT IS" PROJECT**
>
> This repository is provided **AS-IS** with **ZERO SUPPORT**. It is shared for educational and reference purposes only.

**What this means:**

- ❌ **No bug reports** will be addressed
- ❌ **No feature requests** will be considered
- ❌ **No setup assistance** will be provided
- ❌ **No pull requests** will be reviewed
- ❌ **No issues** will be responded to
- ❌ **No documentation updates** will be made
- ❌ **No security patches** will be released

**✅ What you CAN do:**

- Fork the repository and modify it yourself
- Study the code for educational purposes
- Use it as a reference for your own projects
- Learn Discord bot development patterns

**Use at your own risk and responsibility.**

---

## 🌟 Features

### 🎵 **Audio Streaming**

- 🎵 **24/7 Audio Streaming** - Continuous Quran recitation in voice channels
- 🎯 **Multiple Reciters** - Support for 6 renowned Qaris with Arabic names
- 🔄 **Auto-Reconnection** - Automatic reconnection on voice disconnects
- 📖 **Beautiful Surah Names** - Displays chapters with emojis and Arabic transliterations

### 🎛️ **Interactive Control Panel**

- 📱 **Discord Control Panel** - Interactive control panel with buttons and dropdowns
- 🎮 **Surah Selection** - Browse and select from all 114 Surahs with pagination
- 🎤 **Reciter Selection** - Switch between different Qaris on-demand
- ⏭️ **Playback Controls** - Previous/Next track navigation
- 🔁 **Loop & Shuffle** - Toggle loop and shuffle modes with visual feedback
- 📊 **Real-time Progress** - Live progress tracking with time display and percentage
- 👤 **Last Activity Tracking** - Shows who last interacted with the bot and when

### 🔧 **Advanced Features**

- 💾 **State Management** - Automatically saves and resumes playback position
- 🔄 **Smart Resume** - Intelligently resumes from where you left off
- 📊 **Session Statistics** - Tracks bot usage and session information
- 🛡️ **Instance Management** - Prevents multiple bot instances running simultaneously
- 📝 **Comprehensive Logging** - Tree-style structured logging with timestamps
- 🗂️ **File-based Logging** - Organized logs by date with JSON and text formats

### ⚡ **Performance & Reliability**

- 🚀 **Optimized Performance** - Efficient audio streaming and memory management
- 🔧 **Easy Configuration** - Environment-based configuration management
- 🛡️ **Error Handling** - Comprehensive error handling with recovery mechanisms
- 📈 **Resource Monitoring** - Built-in resource usage monitoring

### 🛡️ **Data Protection & Backup**

- 💾 **Bulletproof Data Protection** - 5-layer protection system for all data files
- 📦 **Automated ZIP Backups** - EST-scheduled hourly backups with date/time naming
- 🔄 **Atomic File Operations** - Corruption-proof saves with automatic recovery
- 🚨 **Emergency Backup System** - Multiple fallback mechanisms for data safety
- 🗂️ **Perfect Tree Logging** - Comprehensive backup logging with full visibility

### 🎯 **Enhanced Audio Management**

- 🔍 **Missing Surah Detection** - Automatic detection and logging of incomplete reciter collections
- 🔄 **Smart Looping** - Default looping enabled for continuous playback
- 📊 **Audio File Indexing** - Intelligent mapping of surah numbers to available files
- 🎵 **Reciter Collection Analysis** - Complete analysis of available audio files per reciter

### 🧠 **Quiz System**

- 📝 **Dynamic Quiz Embeds** - Real-time updates as users answer
- 🏆 **Public Results Panel** - Shows correct/incorrect users and correct answer
- 🔥 **Streak & Points Tracking** - Tracks user streaks and points instantly
- 🏅 **Instant Leaderboard Updates** - Leaderboard reflects latest results immediately
- 🛡️ **Robust Error Handling** - Handles deleted messages, Discord API errors, and more
- 🌲 **Comprehensive Logging** - Perfect tree logging for all quiz actions

### 🏆 **Leaderboard**

- 📊 **Points-Based Sorting** - Sorted by quiz points, shows streak and listening time
- 🧹 **Clean Footer** - Only shows creator credits
- ⚡ **Instant Updates** - Always up to date after each quiz

### 🛡️ **Stability & Logging**

- 🌲 **Perfect Tree Logging** - For all major systems and errors
- 🛡️ **Traceback Logging** - For all exceptions and Discord errors
- 🛠️ **Consistent Error Handling** - Across all commands and background tasks

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- FFmpeg installed and accessible
- Discord Bot Token
- Voice channel permissions in your Discord server

### Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/trippixn963/QuranBot.git
   cd QuranBot
   ```

2. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Install FFmpeg**

   **macOS (Homebrew):**

   ```bash
   brew install ffmpeg
   ```

   **Ubuntu/Debian:**

   ```bash
   sudo apt update
   sudo apt install ffmpeg
   ```

   **Windows:** Download from https://ffmpeg.org/download.html

4. **Configure Environment**

   ```bash
   # Copy example configuration
   cp config/.env.example config/.env

   # Edit config/.env with your Discord credentials
   nano config/.env  # or use your preferred editor
   ```

5. **Add Audio Files**

   Place 114 Quran MP3 files (numbered 001.mp3 to 114.mp3) in:

   ```
   audio/Saad Al Ghamdi/
   ├── 001.mp3  # 🕌 Al-Fatiha (The Opening)
   ├── 002.mp3  # 🐄 Al-Baqarah (The Cow)
   ├── 003.mp3  # 👨‍👩‍👧‍👦 Aal-Imran (The Family of Imran)
   └── ... (continue to 114.mp3)
   ```

6. **Run the Bot**

   ```bash
   python main.py
   ```

## 📁 Project Structure

```
QuranBot/
├── 📁 src/                     # Core application code
│   ├── bot/main.py            # Main Discord bot implementation
│   ├── utils/
│   │   ├── tree_log.py        # Advanced logging system
│   │   ├── surah_mapper.py    # Surah name mapping with emojis
│   │   ├── control_panel.py   # Interactive Discord control panel
│   │   ├── state_manager.py   # Playback state persistence
│   │   ├── audio_manager.py   # Audio streaming management
│   │   └── rich_presence.py   # Discord rich presence
│   └── config/                # Configuration modules
├── 📁 config/                  # Configuration files
│   ├── .env.example           # Environment variables template
│   └── pyproject.toml         # Python project configuration
├── 📁 data/                    # Persistent data storage
│   ├── playback_state.json    # Current playback position
│   └── bot_stats.json         # Bot usage statistics
├── 📁 audio/                   # Quran audio files
│   ├── Saad Al Ghamdi/        # Default reciter
│   ├── Rashid Al Afasy/       # Alternative reciter
│   └── ... (other reciters)
├── 📁 images/                  # Visual assets
├── 📁 logs/                    # Organized log files by date
├── main.py                    # 🚀 Main entry point - START HERE
├── bot_manager.py             # 🛠️ Bot instance management utility
├── requirements.txt           # 📦 Python dependencies
└── CHANGELOG.md               # 📝 Version history
```

## ⚙️ Configuration

### Discord Bot Setup

1. **Create Discord Application**

   - Go to https://discord.com/developers/applications
   - Create new application
   - Go to "Bot" section and create bot
   - Copy the bot token

2. **Get Required IDs**

   - Enable Developer Mode in Discord (Settings > Advanced > Developer Mode)
   - Right-click your server → Copy ID (GUILD_ID)
   - Right-click voice channel → Copy ID (TARGET_CHANNEL_ID)
   - Right-click control panel channel → Copy ID (CONTROL_PANEL_CHANNEL_ID)
   - Right-click your user → Copy ID (ADMIN_USER_ID)

3. **Configure Environment**

   Edit `config/.env` with your Discord credentials:

   ```env
   # Required Settings
   DISCORD_TOKEN=your_discord_bot_token_here
   GUILD_ID=your_discord_server_id_here
   TARGET_CHANNEL_ID=your_voice_channel_id_here
   CONTROL_PANEL_CHANNEL_ID=your_control_panel_channel_id_here
   ADMIN_USER_ID=your_discord_user_id_here
   ```

## 🎵 Audio Setup

Place your Quran audio files in the `audio/` directory organized by reciter:

```
audio/
├── Saad Al Ghamdi/            # سعد الغامدي
│   ├── 001.mp3  # 🕌 Al-Fatiha (The Opening)
│   ├── 002.mp3  # 🐄 Al-Baqarah (The Cow)
│   ├── 036.mp3  # 💚 Ya-Sin (Ya-Sin)
│   └── ...
├── Rashid Al Afasy/           # راشد العفاسي
│   ├── 001.mp3
│   └── ...
├── Abdul Basit Abdul Samad/   # عبد الباسط عبد الصمد
│   ├── 001.mp3
│   └── ...
└── Other Reciters/
    └── ...
```

### Supported Reciters

The bot supports these renowned Qaris with Arabic names:

- **Saad Al Ghamdi** / سعد الغامدي
- **Rashid Al Afasy** / راشد العفاسي
- **Maher Al Muaiqly** / ماهر المعيقلي
- **Muhammad Al Luhaidan** / محمد اللحيدان
- **Abdul Basit Abdul Samad** / عبد الباسط عبد الصمد
- **Yasser Al Dosari** / ياسر الدوسري

## 🎛️ Control Panel Features

The interactive Discord control panel provides:

### 📱 **Real-time Display**

- **Current Surah:** Shows both English and Arabic names
- **Current Reciter:** Displays reciter with Arabic name
- **Progress Tracking:** Live time display and progress bar
- **Bot Thumbnail:** Shows bot's profile picture

### 🎮 **Interactive Controls**

- **⬅️ Prev Page / ➡️ Next Page:** Navigate surah selection pages
- **⏮️ Previous / ⏭️ Next:** Skip to previous/next surah
- **🔁 Loop / 🔀 Shuffle:** Toggle playback modes with visual feedback
- **🕌 Surah Dropdown:** Select from all 114 surahs with emojis
- **🎤 Reciter Dropdown:** Switch between available reciters

### 📊 **Smart Features**

- **Last Activity Tracking:** Shows who last used the bot and when
- **State Persistence:** Remembers position across restarts
- **Progress Clamping:** Prevents impossible time values
- **Dynamic Updates:** Real-time updates every 5 seconds

## 💾 State Management

The bot automatically saves and restores:

- **Current Surah Position:** Exact playback position
- **Selected Reciter:** Currently active reciter
- **Playback Settings:** Loop and shuffle preferences
- **Session Statistics:** Usage tracking and session data

State files are stored in the `data/` directory:

- `playback_state.json` - Current playback position
- `bot_stats.json` - Bot usage statistics

## 🛠️ Bot Management

Basic bot management using the included utility:

```bash
# Check if bot is running
python bot_manager.py status

# Stop the bot
python bot_manager.py stop

# Start the bot
python main.py
```

## 📊 Logging System

The bot features a beautiful tree-style logging system:

```
================================================================================
🚀 NEW BOT RUN STARTED
================================================================================
🎯 QuranBot v2.2.1 - Run ID: B331F430
├─ started_at: [07/05 10:28 PM EST]
├─ version: 2.2.1
├─ run_id: B331F430
└─ log_session: 2025-07-05

🎵 Rich Presence Manager Initialization
├─ ffmpeg_path: /opt/homebrew/bin/ffmpeg
└─ initialization: ✅ Rich Presence Manager ready

🎶 Progress (11/114)
├─ surah: 011. 🏘️ Hud (هود) - 123 verses
```

### Log Files

All logs are automatically saved to:

- `logs/YYYY-MM-DD/YYYY-MM-DD.log` - Human-readable text logs
- `logs/YYYY-MM-DD/YYYY-MM-DD.json` - Structured JSON logs
- `logs/YYYY-MM-DD/YYYY-MM-DD-errors.log` - Error-only logs

## 🚨 Important Notes

- **Single Guild Only:** This bot is designed for use in ONE Discord server only
- **Audio Files:** You must provide your own Quran MP3 files (114 files, numbered 001.mp3 to 114.mp3)
- **Security:** Keep your bot token secure and never share it publicly
- **Control Panel:** Set up a dedicated channel for the control panel
- **Permissions:** Ensure the bot has proper permissions in all required channels

## 📚 Dependencies

- `discord.py>=2.3.0` - Discord API wrapper
- `PyNaCl>=1.5.0` - Voice support
- `python-dotenv>=1.0.0` - Environment variable management
- `psutil>=5.9.0` - Process monitoring for instance management
- `pytz>=2023.3` - Timezone handling for logging

## 🛡️ Security

- ✅ Environment-based configuration
- ✅ No sensitive data in repository
- ✅ Comprehensive .gitignore for security
- ✅ Instance management prevents conflicts
- ✅ Secure token handling
- ✅ State file encryption ready

## 📋 Version History

### v2.3.2 (Latest)

### v2.3.1

### v2.3.0

- **⚡ Command Registration - Fixed /verse command registration and initialization timing**
- **🕐 EST Timezone Support - Added EST timezone support for all verse timers**
- **👤 Admin Profile Integration - Enhanced daily verse embeds with admin profile picture in footer**
- **📱 Message ID Tracking - Improved /verse command response with message ID tracking**
- **🛡️ Enhanced Error Handling - Better error handling and user feedback**

### v2.2.1

### v2.2.0

- **🛡️ Bulletproof Data Protection - Implemented 5-layer protection system for all data files**
- **📦 Automated ZIP Backup System - EST-scheduled hourly backups with intuitive date/time naming (e.g., "7/6 - 10PM.zip")**
- **🔍 Missing Surah Detection - Automatic detection and logging of incomplete reciter collections with range formatting**
- **🎯 Enhanced Audio Management - Intelligent mapping of surah numbers to available files with comprehensive analysis**
- **🗂️ Perfect Tree Logging - Complete backup logging with full visibility into all operations**
- **🔄 Smart Looping - Default looping enabled for continuous playback experience**
- **📊 Audio File Indexing - Intelligent surah-to-file mapping with missing file detection**
- **🚨 Emergency Backup System - Multiple fallback mechanisms for critical data protection**
- **🔄 Atomic File Operations - Corruption-proof saves with automatic recovery mechanisms**

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built for the Muslim community
- Inspired by the beauty of Quran recitation
- Developed with modern Python best practices
- Enhanced with interactive Discord features

## 📋 Repository Information

### 📁 **Important Files**

- 📖 [**Contributing Guidelines**](CONTRIBUTING.md) - How to contribute (educational purposes)
- 🔒 [**Security Policy**](SECURITY.md) - Security information and disclaimers
- 📋 [**Issue Templates**](.github/ISSUE_TEMPLATE/) - Bug reports and feature requests
- 🔍 [**CodeQL Analysis**](.github/workflows/codeql.yml) - Automated security scanning
- 🚫 [**Gitignore**](.gitignore) - Comprehensive Python/Discord bot gitignore

### 🏷️ **Repository Stats**

- **Language**: Python 3.11+
- **Framework**: Discord.py 2.3+
- **Audio Engine**: FFmpeg
- **Architecture**: Modular, object-oriented
- **Logging**: Custom tree-structured system
- **UI System**: Discord embeds and components

### 🎓 **Educational Value**

This repository demonstrates professional Discord bot development:

- ✅ **Clean Architecture** - Modular design with separation of concerns
- ✅ **Error Handling** - Comprehensive exception management
- ✅ **Logging Systems** - Professional logging patterns
- ✅ **State Management** - Persistent application state
- ✅ **UI/UX Design** - Modern Discord interface components
- ✅ **Audio Processing** - Real-time streaming implementation
- ✅ **Security Practices** - Environment-based configuration

---

<div align="center">

### 🔗 **Quick Links**

[![GitHub](https://img.shields.io/badge/GitHub-Repository-black?logo=github)](https://github.com/trippixn963/QuranBot)
[![License](https://img.shields.io/badge/License-MIT-green?logo=opensourceinitiative)](LICENSE)
[![Contributing](https://img.shields.io/badge/Contributing-Guidelines-blue?logo=github)](CONTRIBUTING.md)
[![Security](https://img.shields.io/badge/Security-Policy-red?logo=security)](SECURITY.md)

**May Allah bless this project and all who use it** 🤲

_"And it is He who sends down rain from the sky, and We produce thereby the vegetation of every kind"_ - Quran 6:99

<br>

![QuranBot Logo](<images/PFP%20(Cropped%20-%20Animated).gif>)

**🚨 Remember: This is a "TAKE AS IS" project with NO SUPPORT**

</div>
