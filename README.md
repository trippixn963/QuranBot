# QuranBot - Islamic Discord Companion

[![Version](https://img.shields.io/github/v/release/trippixn963/QuranBot)](https://github.com/trippixn963/QuranBot/releases)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Discord.py](https://img.shields.io/badge/discord.py-2.4.0-blue.svg)](https://discordpy.readthedocs.io/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A modern Discord bot serving as an Islamic companion, featuring Quran recitations, AI-powered assistance with Islamic knowledge, and interactive features for Muslim communities.

## ✨ Current Features

### 🎵 Audio System
- **Quran Recitation Playback** - High-quality audio streaming in voice channels
- **Control Panel** - Interactive buttons for play, pause, stop, and navigation
- **Queue Management** - Add multiple surahs to queue
- **Playback Modes** - Normal, shuffle, and repeat modes
- **Resume Functionality** - Continue playback from where you left off
- **Multiple Reciters** - Support for various renowned Quran reciters

### 🤖 AI Islamic Companion
- **Intelligent Responses** - OpenAI-powered responses with Islamic context
- **Emotional Intelligence** - Detects emotions and provides appropriate Islamic comfort
- **Memory System** - Remembers user interactions for personalized responses
- **Multi-language Support** - Automatic Arabic/English detection and response
- **Islamic Knowledge Base** - Contextual Quranic verses and hadith references
- **Rate Limiting** - Fair usage system (configurable per hour)

### 🎨 User Interface
- **Discord Embeds** - All responses use beautiful, consistent embeds
- **Bot Profile Integration** - Bot avatar shown in all interactions
- **Language Toggle** - Switch between English and Arabic responses
- **Interactive Buttons** - Easy-to-use controls for all features
- **Error Handling** - User-friendly error messages in embed format

### 🛠️ Technical Features
- **Service Architecture** - Modular, maintainable codebase
- **Comprehensive Logging** - Detailed logs with TreeLogger system
- **State Management** - Persistent bot state across restarts
- **Database Service** - SQLite for data persistence
- **Environment Configuration** - Secure .env file support
- **Error Recovery** - Robust error handling throughout

## 📋 Requirements

- Python 3.11 or higher
- Discord Bot Token
- OpenAI API Key (for AI features)
- FFmpeg (for audio playback)
- Active Discord server

## 🚀 Installation

1. **Clone the repository**
```bash
git clone https://github.com/trippixn963/QuranBot.git
cd QuranBot
```

2. **Install Poetry** (if not already installed)
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

3. **Install dependencies**
```bash
poetry install
```

4. **Configure environment**
Create a `.env` file in the root directory:
```env
# Required
DISCORD_TOKEN=your_discord_bot_token
DEVELOPER_ID=your_discord_user_id

# AI Configuration (Required for AI features)
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4
OPENAI_MAX_TOKENS=500
OPENAI_TEMPERATURE=0.7
OPENAI_MONTHLY_BUDGET=20.00

# Optional
COMMAND_PREFIX=!
DEFAULT_RECITER=Mishary Rashid Alafasy
AUDIO_QUALITY=high
AI_RATE_LIMIT_PER_HOUR=10
```

5. **Run the bot**
```bash
poetry run python main.py
```

## 📖 Usage

### Basic Commands
- **@BotName [question]** - Ask the AI Islamic companion
- Bot will respond with Islamic guidance, Quranic verses, or general help

### Audio Control (via buttons)
- **Play** - Start playing selected surah
- **Pause/Resume** - Pause or resume playback
- **Stop** - Stop playback and clear queue
- **Previous/Next** - Navigate between surahs
- **Search** - Search for specific surah
- **Queue** - View current queue
- **Shuffle/Repeat** - Toggle playback modes

## 🏗️ Architecture

```
QuranBot/
├── app/
│   ├── bot.py              # Main bot client
│   ├── config/             # Configuration management
│   ├── core/               # Core utilities (logging, errors)
│   ├── data/               # Data files and models
│   ├── handlers/           # Event handlers
│   ├── services/           # Service layer
│   │   ├── ai/            # AI-related services
│   │   ├── audio/         # Audio playback services
│   │   ├── bot/           # Bot utilities
│   │   └── core/          # Core services
│   └── ui/                # User interface components
├── data/                  # Runtime data
├── logs/                  # Application logs
├── tests/                 # Test suite
├── .env                   # Environment configuration
├── main.py               # Entry point
└── pyproject.toml        # Project configuration
```

## 🔧 Configuration

### AI Features
- Requires OpenAI API key
- Configurable model (gpt-4, gpt-3.5-turbo)
- Rate limiting per user per hour
- Monthly budget tracking

### Audio Features
- Supports multiple audio formats
- Configurable quality settings
- Automatic error recovery
- Metadata caching for performance

## 🚦 Bot Status

The bot includes:
- Automatic error recovery
- Comprehensive logging
- State persistence
- Performance monitoring
- User interaction tracking

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch from `development`
3. Commit your changes
4. Push to your fork
5. Open a Pull Request to `development`

### Development Setup
```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/QuranBot.git
cd QuranBot

# Add upstream remote
git remote add upstream https://github.com/trippixn963/QuranBot.git

# Create feature branch
git checkout -b feature/your-feature development
```

## 📝 Versioning

We use [Semantic Versioning](https://semver.org/):
- **PATCH** (0.0.X): Bug fixes
- **MINOR** (0.X.0): New features (backwards compatible)
- **MAJOR** (X.0.0): Breaking changes or major features

Current version: **1.0.0**

## 🐛 Known Limitations

- AI features require OpenAI API key
- Audio playback requires FFmpeg
- Bot must have proper Discord permissions
- One voice channel per server limitation

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Quran audio from everyayah.com
- Built with [discord.py](https://discordpy.readthedocs.io/)
- AI powered by [OpenAI](https://openai.com/)
- Developed for the Muslim Discord community

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/trippixn963/QuranBot/issues)
- **Discussions**: [GitHub Discussions](https://github.com/trippixn963/QuranBot/discussions)

---

**Developed with ❤️ by حَـــــنَّـــــا**
