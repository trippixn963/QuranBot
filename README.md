# 🕌 QuranBot

<div align="center">
  <img src="images/PFP (Full - Still).png" alt="QuranBot Logo" width="200"/>
  
  **24/7 Quran Streaming Bot with Interactive Controls**
  
  [![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/downloads/)
  [![Discord.py](https://img.shields.io/badge/Discord.py-2.3+-green.svg)](https://discordpy.readthedocs.io/)
  [![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
  
  *Built with ❤️ for the Muslim Ummah*
</div>

---

## 🌟 Features

### 🎵 **24/7 Audio Streaming**
- **Continuous Quran Recitation** - Never-ending stream of beautiful recitations
- **Multiple Professional Reciters** - Choose from various renowned reciters
- **114 Complete Surahs** - Full Quran with proper Arabic pronunciation
- **Automatic Playback** - Seamless transitions between surahs

### 🎮 **Interactive Control Panel**
- **Beautiful Discord UI** - Rich embeds with buttons and select menus
- **Real-time Controls** - Play, pause, skip, loop, shuffle functionality
- **Surah Browser** - Easy navigation through all 114 surahs
- **Reciter Selection** - Switch between different reciters on-the-fly
- **Search Function** - Find specific surahs quickly

### 📖 **Daily Verse System**
- **Automatic Posting** - Sends verses every 3 hours
- **Beautiful Embeds** - Arabic text and English translation in separate code blocks
- **No Repeats** - Intelligent shuffling prevents immediate repeats
- **Dua Reactions** - Interactive emoji reactions for engagement

### ❓ **Quran Question System**
- **Multiple Choice Questions** - Interactive Quran knowledge tests
- **Bilingual Support** - Questions in both English and Arabic
- **Leaderboard System** - Track user scores and achievements
- **Timer System** - 1-minute countdown with dynamic updates

### 📊 **Advanced Monitoring**
- **Real-time Logging** - Comprehensive activity tracking
- **Health Monitoring** - System status and performance metrics
- **User Session Tracking** - Voice channel activity monitoring
- **Error Handling** - Robust error recovery and reporting

---

## 🚀 Quick Start

### Prerequisites
- Python 3.13+
- FFmpeg installed and in PATH
- Discord Bot Token
- Discord Server with appropriate permissions

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

3. **Set up environment variables**
   ```bash
   cp env_template.txt .env
   # Edit .env with your configuration
   ```

4. **Configure audio files**
   - Place Quran audio files in the `audio/` directory
   - Organize by reciter: `audio/reciter_name/surah_files.mp3`

5. **Run the bot**
   ```bash
   python run.py
   ```

---

## ⚙️ Configuration

### Environment Variables
```env
# Discord Configuration
DISCORD_TOKEN=your_discord_bot_token
TARGET_CHANNEL_ID=your_voice_channel_id
TARGET_GUILD_ID=your_guild_id
PANEL_CHANNEL_ID=your_control_panel_channel_id
DAILY_VERSE_CHANNEL_ID=your_daily_verse_channel_id
LOGS_CHANNEL_ID=your_logs_channel_id

# Admin Configuration
ADMIN_USER_IDS=user_id1,user_id2,user_id3
DEVELOPER_ID=your_developer_id

# Audio Configuration
AUDIO_FOLDER=audio
AUTO_VOICE_CONNECT=true
AUTO_RECONNECT=true

# Logging Configuration
LOG_LEVEL=INFO
```

### Required Permissions
- **Send Messages** - For embeds and responses
- **Use Slash Commands** - For bot commands
- **Connect** - To join voice channels
- **Speak** - To play audio
- **Manage Messages** - For control panel management
- **Add Reactions** - For daily verse interactions

---

## 📋 Available Commands

### User Commands (Everyone)
| Command | Description |
|---------|-------------|
| `/askquranquestion` | Ask a random Quran multiple choice question |
| `/leaderboard` | Show the Quran question leaderboard |
| `/versestatus` | Check daily verse status |

### Admin Commands (Admin Only)
| Command | Description |
|---------|-------------|
| `/admin restart` | Restart the Quran Bot |
| `/stop stop` | Stop the Quran Bot completely |
| `/credits` | Show bot credits and information |
| `/info` | Get bot logs and configuration |
| `/sendverse` | Send a verse now (Admin only) |

### Interactive Control Panel
- **Persistent UI** - Always available in designated channel
- **Surah Selection** - Browse and select different surahs
- **Reciter Selection** - Choose from available reciters
- **Playback Controls** - Play, pause, skip, previous, loop, shuffle
- **Search Function** - Search for specific surahs
- **Real-time Status** - Shows current playback status and timer

---

## 📁 Project Structure

```
QuranBot/
├── 📁 src/                          # Main source code
│   ├── 📁 bot/                      # Bot core functionality
│   │   └── quran_bot.py            # Main bot class
│   ├── 📁 cogs/                     # Discord command modules
│   │   ├── 📁 admin/               # Admin commands
│   │   │   ├── 📁 bot_control/     # Bot control commands
│   │   │   ├── 📁 monitoring/      # Monitoring commands
│   │   │   └── 📁 misc/            # Miscellaneous admin commands
│   │   └── 📁 user_commands/       # User-facing commands
│   │       ├── control_panel.py    # Interactive control panel
│   │       ├── daily_verse.py      # Daily verse system
│   │       └── quran_question.py   # Quran question system
│   ├── 📁 core/                     # Core functionality
│   │   ├── 📁 config/              # Configuration management
│   │   ├── 📁 mapping/             # Surah mapping utilities
│   │   └── 📁 state/               # State management
│   └── 📁 monitoring/               # Monitoring and logging
│       ├── 📁 health/              # Health monitoring
│       └── 📁 logging/             # Logging system
├── 📁 audio/                        # Quran audio files
├── 📁 data/                         # Data storage
│   ├── bot_state.json              # Bot state persistence
│   ├── daily_verses_pool.json      # Daily verse database
│   ├── quran_questions.json        # Question database
│   └── user_vc_sessions.json       # User session tracking
├── 📁 images/                       # Bot images and assets
├── 📁 logs/                         # Application logs
├── 📁 scripts/                      # Utility scripts
│   ├── 📁 windows/                 # Windows-specific scripts
│   ├── 📁 linux/                   # Linux-specific scripts
│   ├── 📁 macos/                   # macOS-specific scripts
│   └── 📁 vps/                     # VPS management scripts
├── requirements.txt                 # Python dependencies
├── run.py                          # Bot entry point
└── README.md                       # This file
```

---

## 🎯 Key Features Explained

### Daily Verse System
- **Automatic Scheduling** - Posts verses every 3 hours automatically
- **Beautiful Formatting** - Arabic and English text in separate black code blocks
- **Smart Shuffling** - Prevents immediate repeats until all verses are used
- **Interactive Elements** - Dua emoji reactions for user engagement

### Quran Question System
- **Bilingual Questions** - Questions in both English and Arabic
- **Multiple Choice** - 4 options with A, B, C, D format
- **Timer System** - 1-minute countdown with 10-second updates
- **Score Tracking** - Persistent leaderboard with user mentions
- **Answer Reveal** - Shows correct answer and user responses

### Control Panel Features
- **Real-time Updates** - Live status updates every 10 seconds
- **Surah Navigation** - Paginated browsing through all 114 surahs
- **Reciter Switching** - Change reciters without interrupting playback
- **Playback Controls** - Full media control functionality
- **Search Capability** - Find surahs by name or number

### Monitoring & Logging
- **Comprehensive Logging** - Detailed activity tracking
- **Health Monitoring** - System performance metrics
- **User Session Tracking** - Voice channel activity
- **Error Recovery** - Automatic reconnection and error handling
- **Discord Integration** - Real-time logs sent to Discord channels

---

## 🔧 Development

### Local Development
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run with development settings
python run.py
```

### VPS Deployment
```bash
# Use VPS management scripts
./scripts/vps/vps_manager.py
```

### Audio File Management
```bash
# Validate audio files
python scripts/windows/validate_audio_files.py

# Check FFmpeg status
./scripts/windows/check_ffmpeg_status.bat
```

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Quran Audio** - Professional recitations from various reciters
- **Discord.py** - Excellent Discord API wrapper
- **FFmpeg** - Powerful audio processing
- **Muslim Community** - For inspiration and support

---

<div align="center">
  <p><strong>Built with ❤️ for the Muslim community</strong></p>
  <p>May Allah bless this project and all who use it</p>
  
  <img src="images/PFP (Full - Still).png" alt="QuranBot Profile" width="200"/>
</div> 