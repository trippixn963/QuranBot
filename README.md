# QuranBot - Islamic Discord Companion

A feature-rich Discord bot that serves as an Islamic companion, providing Quran recitations, Islamic knowledge, prayer reminders, and AI-powered assistance.

## Features

### 🎵 Audio Playback
- High-quality Quran recitations from multiple renowned reciters
- Smart queue management with shuffle and repeat modes
- Voice channel controls with intuitive buttons
- Resume playback from where you left off

### 🤖 AI Islamic Companion
- Humanized AI responses with Islamic knowledge
- Emotional intelligence for providing comfort and guidance
- Multi-language support (Arabic/English)
- Contextual Quranic verses and hadith references

### 📖 Islamic Knowledge
- Daily verse broadcasts
- Islamic quiz system
- Prayer time reminders
- Comprehensive Islamic knowledge base

### 🎮 User Interface
- Beautiful Discord embeds with consistent styling
- Interactive control panels with buttons
- Language toggle for bilingual support
- User-friendly error messages

## Installation

### Prerequisites
- Python 3.11 or higher
- Discord Bot Token
- OpenAI API Key (for AI features)
- FFmpeg (for audio playback)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/trippixn963/QuranBot.git
cd QuranBot
```

2. Install dependencies using Poetry:
```bash
poetry install
```

3. Create a `.env` file in the root directory:
```env
# Discord Configuration
DISCORD_TOKEN=your_discord_bot_token
DEVELOPER_ID=your_discord_user_id

# AI Configuration (Optional)
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4
OPENAI_MAX_TOKENS=500
OPENAI_TEMPERATURE=0.7

# Bot Settings
COMMAND_PREFIX=!
DEFAULT_RECITER=Mishary Rashid Alafasy
AUDIO_QUALITY=high
```

4. Run the bot:
```bash
poetry run python main.py
```

## Commands

### Audio Commands
- `!play [surah]` - Play a Surah
- `!pause` - Pause playback
- `!resume` - Resume playback
- `!stop` - Stop playback
- `!skip` - Skip to next in queue
- `!queue` - View current queue

### Islamic Commands
- `!verse` - Get a random verse
- `!quiz` - Start an Islamic quiz
- `!prayer` - Get prayer times
- `@bot [question]` - Ask the AI Islamic companion

### Utility Commands
- `!help` - Show help menu
- `!ping` - Check bot latency
- `!stats` - View bot statistics

## Project Structure

```
QuranBot/
├── app/
│   ├── bot/              # Bot core and client
│   ├── commands/         # Command implementations
│   ├── config/           # Configuration management
│   ├── core/             # Core utilities (logging, errors)
│   ├── handlers/         # Event and interaction handlers
│   ├── services/         # Service layer (audio, AI, database)
│   └── ui/               # UI components (embeds, buttons)
├── data/                 # Data files
├── tests/               # Test suite
├── main.py              # Entry point
└── pyproject.toml       # Project configuration
```

## Development

### Branch Structure
- `master` - Stable, production-ready code
- `development` - Active development and improvements

### Contributing
1. Fork the repository
2. Create a feature branch from `development`
3. Commit your changes
4. Push to your fork
5. Create a Pull Request to `development`

### Testing
Run tests using pytest:
```bash
poetry run pytest
```

## Features in Development
- Voice note transcription
- Advanced quiz system with leaderboards
- Scheduled reminders
- Multi-server configuration

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments
- Quran audio from everyayah.com
- Islamic knowledge sourced from authentic sources
- Built with discord.py and OpenAI

## Support
For issues and feature requests, please use the GitHub issue tracker.

---
Developed with ❤️ by حَـــــنَّـــــا