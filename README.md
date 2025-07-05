<div align="center">

![QuranBot Banner](<images/BANNER%20(ANIMATED).gif>)

# 🕌 QuranBot

**A Professional Discord Bot for 24/7 Quran Audio Streaming**

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![Discord.py](https://img.shields.io/badge/discord.py-2.3.0%2B-blue.svg)](https://github.com/Rapptz/discord.py)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-organized-brightgreen.svg)](https://github.com/JohnHamwi/QuranAudioBot)

_Built with ❤️ for the Muslim Ummah_

**🌐 Join Our Community:** [discord.gg/syria](https://www.discord.gg/syria)

</div>

---

## 🌟 Features

- 🎵 **24/7 Audio Streaming** - Continuous Quran recitation in voice channels
- 🎯 **Multiple Reciters** - Support for various renowned Qaris
- 🔄 **Auto-Reconnection** - Automatic reconnection on voice disconnects
- 📊 **Beautiful Logging** - Tree-style structured logging with timestamps
- 🛡️ **Instance Management** - Prevents multiple bot instances running simultaneously
- 📝 **Comprehensive Logging** - File-based logging with date organization
- ⚡ **Optimized Performance** - Efficient audio streaming and memory management
- 🔧 **Easy Configuration** - Environment-based configuration management

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- FFmpeg installed and accessible
- Discord Bot Token
- Voice channel permissions in your Discord server

### Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/JohnHamwi/QuranBot.git
   cd QuranBot
   ```

2. **Set Up Development Environment**

   ```bash
   # Create virtual environment
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate

   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Install FFmpeg** (macOS with Homebrew)

   ```bash
   brew install ffmpeg
   ```

4. **Configure Environment**

   ```bash
   # Copy and edit configuration
   cp config/.env.template config/.env
   # Edit config/.env with your Discord bot token and channel IDs
   ```

5. **Add Audio Files**
   Place your Quran MP3 files in the audio directory:

   ```
   audio/
   ├── Saad Al Ghamdi/
   │   ├── 001.mp3  # Al-Fatiha
   │   ├── 002.mp3  # Al-Baqarah
   │   └── ... (114 total files)
   └── Other Reciters/
       └── ...
   ```

6. **Run Development Environment**

   ```bash
   # Quick start (recommended)
   ./run_dev.sh

   # Or manually
   source .venv/bin/activate
   python tools/test_bot.py  # Run tests first
   python main.py            # Start bot
   ```

## 📁 Project Structure

```
QuranBot/
├── 📁 src/                     # Core application code
│   ├── bot/                    # Discord bot implementation
│   ├── utils/                  # Utility functions (logging, etc.)
│   └── config/                 # Configuration modules
├── 📁 tools/                   # Development & deployment tools
│   ├── test_bot.py            # Comprehensive testing suite
│   ├── format_code.py         # Code formatting utility
│   ├── deploy_to_vps.py       # Safe deployment tool
│   └── update_version.py      # Version management helper
├── 📁 docs/                    # Documentation files
│   ├── DEV_SETUP.md           # Development setup guide
│   ├── DEVELOPMENT_WORKFLOW.md # Complete workflow guide
│   └── STYLE_GUIDE.md         # Coding standards & style
├── 📁 config/                  # Configuration files
│   ├── .env                   # Environment variables
│   └── pyproject.toml         # Python project configuration
├── 📁 scripts/                 # Executable scripts
│   └── run_dev.sh             # Development startup script
├── 📁 audio/                   # Quran audio files
│   └── Saad Al Ghamdi/        # Default reciter (114 MP3 files)
├── 📁 images/                  # Visual assets
│   ├── BANNER (ANIMATED).gif  # Animated banner
│   └── PFP (Cropped - Animated).gif # Logo
├── main.py                    # 🚀 Main entry point
├── bot_manager.py             # 🛠️ Bot instance management
├── run_dev.sh                 # 🚀 Quick development startup
└── requirements.txt           # 📦 Dependencies
```

## 🔧 Configuration

### Environment Variables

Copy `env_template.txt` to `.env` and configure the following:

```env
# Discord Bot Configuration
DISCORD_TOKEN=your_discord_bot_token_here

# Discord Channel IDs
TARGET_CHANNEL_ID=your_voice_channel_id_here
PANEL_CHANNEL_ID=your_control_panel_channel_id_here
LOGS_CHANNEL_ID=your_logs_channel_id_here
DAILY_VERSE_CHANNEL_ID=your_daily_verse_channel_id_here

# Admin Configuration
ADMIN_USER_ID=your_discord_user_id_here
GUILD_ID=your_discord_server_id_here
DEVELOPER_ID=your_discord_user_id_here

# Audio Configuration
AUDIO_FOLDER=audio
DEFAULT_RECITER=Saad Al Ghamdi
AUDIO_QUALITY=128k

# FFmpeg Configuration (Optional - auto-detects if not specified)
FFMPEG_PATH=auto-detect
```

### Getting Discord IDs

1. Enable Developer Mode in Discord Settings > Advanced > Developer Mode
2. Right-click on channels/servers/users and select "Copy ID"
3. For bot token: Discord Developer Portal > Your App > Bot > Token

## 🎵 Audio Setup

Place your Quran audio files in the `audio/` directory organized by reciter:

```
audio/
├── Saad Al Ghamdi/
│   ├── 001.mp3  # Al-Fatiha
│   ├── 002.mp3  # Al-Baqarah
│   └── ...
├── Abdul Basit Abdul Samad/
│   ├── 001.mp3
│   └── ...
└── Other Reciters/
    └── ...
```

## 🛠️ Development Tools

QuranBot includes comprehensive development tools for a professional workflow:

### Bot Management

```bash
# Check bot status
python bot_manager.py status

# Stop the bot
python bot_manager.py stop

# Restart the bot
python bot_manager.py restart

# Start the bot
python bot_manager.py start
```

### Testing & Quality Assurance

```bash
# Run comprehensive test suite (41 tests)
python tools/test_bot.py

# Format all code consistently
python tools/format_code.py

# Generate safe deployment guide
python tools/deploy_to_vps.py
```

### Version Management

```bash
# Update version and changelog
python tools/update_version.py
```

### Quick Development Startup

```bash
# One command to activate environment, run tests, and start bot
./run_dev.sh
```

## 📊 Logging System

The bot features a beautiful tree-style logging system:

```
🚀 Starting QuranBot v1.1.0...
├─ version: 1.1.0
├─ discord_token: ***HIDDEN***
├─ structure: Organized in src/ directory
└─ entry_point: main.py

🎯 QuranBot v1.1.0 Started
├─ bot_user: Quran#1550
├─ version: 1.1.0
├─ guild_id: 1228455909827805308
└─ target_channel_id: 1389675580253016144
```

### Log Files

All logs are automatically saved to:

- `logs/YYYY-MM-DD/YYYY-MM-DD.log` - Human-readable text logs
- `logs/YYYY-MM-DD/YYYY-MM-DD.json` - Structured JSON logs
- `logs/YYYY-MM-DD/YYYY-MM-DD-errors.log` - Error-only logs

## 🔄 Version Management

Update the bot version using:

```bash
python update_version.py
```

This tool will:

- Update version numbers in the code
- Add entries to CHANGELOG.md
- Guide you through documenting changes

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

## 📝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built for the Muslim community
- Inspired by the beauty of Quran recitation
- Developed with modern Python best practices

---

<div align="center">

**May Allah bless this project and all who use it** 🤲

_"And it is He who sends down rain from the sky, and We produce thereby the vegetation of every kind"_ - Quran 6:99

<br><br>

![QuranBot Logo](<images/PFP%20(Cropped%20-%20Animated).gif>)

</div>
