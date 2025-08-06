# QuranBot - Interactive Islamic Discord Companion

[![Version](https://img.shields.io/github/v/release/trippixn963/QuranBot)](https://github.com/trippixn963/QuranBot/releases)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Discord.py](https://img.shields.io/badge/discord.py-2.4.0-blue.svg)](https://discordpy.readthedocs.io/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A comprehensive Discord bot serving as an interactive Islamic companion, featuring professional Quran recitations in stage channels, multi-user quiz system, AI-powered Islamic guidance, and engaging community features for Muslim Discord servers.

## ✨ Features

### 🎮 Interactive Quiz System *(NEW in v3.0.0)*
- **Multi-User Quiz Experience** - Multiple users can answer simultaneously with real-time participation tracking
- **60-Second Timer** - Full duration quiz with live countdown and automatic results
- **Islamic Knowledge Questions** - Comprehensive database of Quran, Hadith, and Islamic history questions
- **Letter-Only Buttons** - Clean A/B/C/D interface with unique colors (Blue/Green/Red/Gray)
- **Auto-Deletion** - Both questions and results automatically delete after 60 seconds
- **Economy Integration** - Earn coins through UnbelievaBoat for correct answers
- **Performance Tracking** - Response time tracking and leaderboard statistics
- **Anti-Cheat System** - Results only shown after timeout to prevent cheating

### 🎙️ Professional Stage Integration *(NEW in v3.0.0)*
- **Stage Channel Streaming** - Professional audio streaming in Discord stage channels
- **Auto-Start Stages** - Creates stage instances without @everyone notifications
- **Dynamic Stage Topics** - Shows current Surah name with matching emoji
- **Speaker Management** - Auto-mutes all speakers except bot for clean audio experience
- **Message Cleanup** - Automatically removes stage topic changes and user messages
- **Control Panel Integration** - Stage channel control panel for easy management

### 🎵 Enhanced Audio System
- **High-Quality Recitation** - Crystal clear Quran audio streaming
- **Multiple Reciters** - Support for various renowned Quran reciters (Mishary, Sudais, Al-Luhaidan, etc.)
- **Smart Playback Control** - Interactive control panel with play, pause, stop, skip
- **Queue Management** - Add multiple surahs with shuffle and repeat modes
- **Resume Functionality** - Continue playback from where you left off
- **Metadata Display** - Real-time surah information and progress tracking

### 🤖 AI Islamic Companion *(Enhanced in v2.0.0)*
- **Intelligent Islamic Responses** - OpenAI-powered guidance with authentic Islamic context
- **Developer Recognition** - Special personalized responses for the bot creator
- **Emotional Intelligence** - Detects emotions and provides appropriate Islamic comfort
- **Memory System** - Remembers user interactions for personalized guidance
- **Multi-Language Support** - Automatic Arabic/English detection and bilingual responses
- **Islamic Knowledge Base** - Contextual Quranic verses, Hadith references, and scholarly insights
- **Rate Limiting** - Fair usage system with configurable hourly limits

### 💰 Economy Integration *(NEW in v3.0.0)*
- **UnbelievaBoat Integration** - Seamless coin reward system for quiz participation
- **Performance-Based Rewards** - Higher rewards for faster and correct answers
- **Configurable Rewards** - Adjustable coin amounts for correct/incorrect answers
- **Anti-Spam Protection** - Prevents reward farming and maintains fair distribution

### 🎨 User Interface *(Enhanced in v2.0.0)*
- **Consistent Design** - Beautiful Discord embeds across all features
- **Unified Developer Footer** - Consistent branding and attribution
- **Interactive Controls** - User-friendly buttons and dropdowns for all features
- **Real-Time Updates** - Live embed updates for quiz participation and audio status
- **Error Handling** - Comprehensive user-friendly error messages
- **Multi-Language Display** - Arabic and English text formatting

### 🛠️ Technical Excellence
- **Modular Architecture** - Clean, maintainable service-based codebase
- **Comprehensive Logging** - Advanced TreeLogger system with detailed debugging
- **Database Integration** - SQLite for quiz statistics, user progress, and state management
- **State Persistence** - Maintains bot state across restarts and updates
- **Error Recovery** - Robust error handling with automatic recovery mechanisms
- **Performance Optimization** - Efficient async operations and resource management

## 📋 Requirements

- Python 3.11 or higher
- Discord Bot Token (with appropriate permissions)
- OpenAI API Key (for AI features)
- UnbelievaBoat API Token (for economy features) *(Optional)*
- FFmpeg (for audio playback)
- Active Discord server with stage channels (recommended)

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
GUILD_ID=your_server_id
VOICE_CHANNEL_ID=your_stage_channel_id
PANEL_CHANNEL_ID=your_control_panel_channel_id

# AI Configuration (Required for AI features)
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4
OPENAI_MAX_TOKENS=500
OPENAI_TEMPERATURE=0.7
OPENAI_MONTHLY_BUDGET=20.00

# Economy Integration (Optional - for quiz rewards)
UNBELIEVABOAT_API_TOKEN=your_unbelievaboat_token
QUIZ_REWARD_CORRECT=50
QUIZ_REWARD_INCORRECT=10

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

### 🎮 Quiz System *(NEW)*
- **`/question`** - Start an interactive Islamic knowledge quiz
- Multiple users can participate simultaneously
- Questions cover Quran, Hadith, Islamic history, and jurisprudence
- Earn coins through UnbelievaBoat for correct answers
- Real-time participation tracking with 60-second timer

### 🤖 AI Islamic Companion
- **@BotName [question]** - Ask the AI Islamic companion anything
- Get responses with Quranic verses, Hadith references, and Islamic guidance
- Supports both English and Arabic questions
- Provides emotional support with Islamic perspective
- Contextual responses based on conversation history

### 🎵 Audio Control (Stage Integration)
- **Control Panel** - Interactive buttons in your designated control channel
- **Play/Pause/Stop** - Full playback control with stage integration
- **Reciter Selection** - Choose from multiple renowned reciters
- **Surah Navigation** - Previous/Next with search functionality
- **Queue Management** - Add multiple surahs with shuffle/repeat modes
- **Stage Management** - Automatic stage topic updates and speaker control

### 🔧 Admin Features
- **Automatic Setup** - Bot automatically configures stage channels and control panels
- **Message Cleanup** - Auto-removes unwanted messages in stage channels
- **Economy Integration** - Configurable UnbelievaBoat reward system
- **State Persistence** - Maintains settings across bot restarts

## 🏗️ Architecture

```
QuranBot/
├── app/
│   ├── bot.py              # Main bot client
│   ├── commands/           # Slash commands (quiz system)
│   ├── config/             # Configuration management
│   ├── core/               # Core utilities (logging, errors)
│   ├── data/               # Data files and models
│   ├── handlers/           # Event handlers
│   ├── services/           # Service layer
│   │   ├── ai/            # AI-related services
│   │   ├── audio/         # Audio playback services
│   │   ├── bot/           # Bot utilities
│   │   ├── core/          # Core services
│   │   ├── economy/       # UnbelievaBoat integration
│   │   └── quiz/          # Quiz system services
│   └── ui/                # User interface components
│       ├── base/          # Base UI components
│       ├── control_panel/ # Audio control interface
│       ├── islamic/       # Islamic UI components
│       ├── quiz/          # Quiz interface components
│       └── search/        # Surah search components
├── data/                  # Runtime data and databases
├── logs/                  # Application logs
├── tests/                 # Test suite
├── .env                   # Environment configuration
├── main.py               # Entry point
└── pyproject.toml        # Project configuration
```

## 🔧 Configuration

### 🎮 Quiz System
- Customizable quiz questions database (`data/quiz_questions.json`)
- Configurable reward amounts for UnbelievaBoat integration
- Adjustable timer duration and difficulty levels
- Question categories: Quran, Hadith, Islamic History, Jurisprudence

### 🎙️ Stage Integration
- Automatic stage channel detection and setup
- Dynamic stage topic updates with Surah information
- Configurable speaker management and message cleanup
- Control panel channel customization

### 🤖 AI Features
- OpenAI API integration with multiple model support
- Rate limiting per user with configurable hourly limits
- Monthly budget tracking and usage monitoring
- Contextual Islamic knowledge base integration

### 🎵 Audio Features
- Multiple reciter support with high-quality audio streaming
- Configurable audio quality and format settings
- Automatic error recovery and reconnection
- Metadata caching for improved performance

### 💰 Economy Integration
- UnbelievaBoat API integration for coin rewards
- Configurable reward structures for quiz participation
- Anti-spam protection and fair distribution mechanisms

## 🚦 Bot Status & Monitoring

The bot includes comprehensive monitoring and management:
- **Health Monitoring** - Real-time service status tracking
- **Automatic Error Recovery** - Robust error handling with auto-restart capabilities
- **Performance Analytics** - Quiz participation metrics and audio streaming statistics
- **State Persistence** - Maintains all settings and progress across restarts
- **User Activity Tracking** - Interaction logging for community insights
- **Resource Management** - Efficient memory and CPU usage optimization

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

Current version: **3.0.0**

## 🐛 Known Limitations

- AI features require OpenAI API key (configurable budget recommended)
- Audio playback requires FFmpeg installation
- Quiz economy features require UnbelievaBoat integration setup
- Stage channels require Discord server boost level for optimal experience
- Bot requires comprehensive Discord permissions (manage messages, manage channels, etc.)
- Single server configuration per bot instance (multi-server support planned)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Quran Audio**: High-quality recitations from [everyayah.com](https://everyayah.com/)
- **Discord Integration**: Built with [discord.py](https://discordpy.readthedocs.io/) library
- **AI Intelligence**: Powered by [OpenAI](https://openai.com/) GPT models
- **Economy System**: [UnbelievaBoat](https://unbelievaboat.com/) API integration
- **Islamic Knowledge**: Curated from authentic Islamic sources and scholarly works
- **Community**: Developed with ❤️ for the global Muslim Discord community

## 🌟 Recent Updates

### v3.0.0 - Quiz System Overhaul & Stage Integration
- Complete quiz system rewrite with multi-user support
- Professional stage channel integration
- UnbelievaBoat economy rewards
- Enhanced control panel and message management

### v2.0.0 - Enhanced Features & Stability
- Developer recognition system
- Unified UI design across all features
- Improved error handling and recovery
- Enhanced AI response quality

### v1.0.0 - Initial Release
- Core audio streaming functionality
- AI Islamic companion
- Basic control panel interface

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/trippixn963/QuranBot/issues)
- **Discussions**: [GitHub Discussions](https://github.com/trippixn963/QuranBot/discussions)

---

**Developed with ❤️ by حَـــــنَّـــــا**
