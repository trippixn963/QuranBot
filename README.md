<div align="center">

![QuranBot Banner](<images/BANNER%20(ANIMATED).gif>)

# 🕌 QuranBot

**A Discord Bot for 24/7 Quran Audio Streaming**

> ⚠️ **IMPORTANT NOTICE - READ BEFORE USING**
>
> **This is an "AS-IS" open source release with NO SUPPORT provided.**
>
> ❌ **NO** bug fixes, security updates, or maintenance
> ❌ **NO** setup assistance or troubleshooting help
> ❌ **NO** feature requests or issue responses
> ❌ **NO** warranty or guarantee of functionality
>
> ✅ **Use only if you are experienced with Python/Discord bots**
> ✅ **You assume all responsibility for security and maintenance**
> ✅ **You can troubleshoot and fix issues independently**

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![Discord.py](https://img.shields.io/badge/discord.py-2.3.0%2B-blue.svg)](https://github.com/Rapptz/discord.py)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![No Support](https://img.shields.io/badge/support-none-red.svg)](#)

_Built with ❤️ for the Muslim Ummah - Shared as-is for educational purposes_

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

⚠️ **Prerequisites:** You must be experienced with Python, Discord bots, and server administration.

1. **Clone the Repository**

   ```bash
   git clone https://github.com/JohnHamwi/QuranBot.git
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
   ├── 001.mp3  # Al-Fatiha
   ├── 002.mp3  # Al-Baqarah
   ├── 003.mp3  # Aal-Imran
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
│   ├── utils/tree_log.py      # Logging system
│   └── config/                # Configuration modules
├── 📁 config/                  # Configuration files
│   ├── .env.example           # Environment variables template
│   └── pyproject.toml         # Python project configuration
├── 📁 audio/                   # Quran audio files
│   └── Saad Al Ghamdi/        # Default reciter (place 114 MP3 files here)
├── 📁 images/                  # Visual assets
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
   - Right-click your user → Copy ID (ADMIN_USER_ID)

3. **Configure Environment**

   Edit `config/.env` with your Discord credentials:

   ```env
   # Required Settings
   DISCORD_TOKEN=your_discord_bot_token_here
   GUILD_ID=your_discord_server_id_here
   TARGET_CHANNEL_ID=your_voice_channel_id_here
   ADMIN_USER_ID=your_discord_user_id_here

   # Optional Settings
   AUDIO_FOLDER=audio
   DEFAULT_RECITER=Saad Al Ghamdi
   FFMPEG_PATH=auto-detect
   ```

4. **Bot Permissions**

   Your bot needs these permissions:

   - Connect to voice channels
   - Speak in voice channels
   - Send messages
   - Read message history

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

## 🚨 Important Notes

- **Single Guild Only:** This bot is designed for use in ONE Discord server only
- **Audio Files:** You must provide your own Quran MP3 files (114 files, numbered 001.mp3 to 114.mp3)
- **No Support:** This is provided as-is with no support, updates, or bug fixes
- **Security:** Keep your bot token secure and never share it publicly

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

## ⚠️ No Support Policy

**This project is provided "AS-IS" with absolutely no support:**

- ❌ No bug reports will be addressed
- ❌ No feature requests will be considered
- ❌ No setup assistance will be provided
- ❌ No pull requests will be reviewed
- ❌ No issues will be responded to

**Use at your own risk and responsibility.**

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
