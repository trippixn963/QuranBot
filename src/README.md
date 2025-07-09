# 🔧 Source Code Directory

This directory contains the core source code for QuranBot, organized in a modular architecture for maintainability and scalability.

## 📁 Directory Structure

```
src/
├── bot/                    # Core bot functionality
│   ├── __init__.py
│   └── main.py            # Main bot initialization and setup
├── commands/              # Discord slash commands
│   ├── __init__.py
│   ├── credits.py         # /credits command
│   ├── leaderboard.py     # /leaderboard command
│   └── verse.py           # /verse command
├── config/                # Configuration management
│   └── __init__.py
├── utils/                 # Utility modules and helpers
│   ├── __init__.py
│   ├── audio_manager.py   # Audio streaming and playback
│   ├── backup_manager.py  # Data backup system
│   ├── control_panel.py   # Discord control panel UI
│   ├── daily_verses.py    # Daily verse automation
│   ├── listening_stats.py # User listening statistics
│   ├── rich_presence.py   # Discord rich presence
│   ├── state_manager.py   # State persistence
│   ├── surah_mapper.py    # Surah name/number mapping
│   ├── surahs.json        # Complete Surah database
│   └── tree_log.py        # Enhanced logging system
└── version.py             # Centralized version management
```

## 🤖 Core Bot (`bot/`)

### `main.py`

**Main bot initialization and Discord client setup**

```python
# Key responsibilities:
- Discord bot client initialization
- Command tree registration
- Event handlers (on_ready, on_error)
- Startup sequence coordination
- Global error handling
```

## 🎯 Commands (`commands/`)

### Command Architecture

All commands use **Discord slash commands** (`@discord.app_commands.command`) - no prefix commands.

### `credits.py`

**Bot information and credits display**

- Bot version and feature overview
- Developer information and links
- Beta testing notice
- Clean, organized embed design

### `leaderboard.py`

**User listening statistics leaderboard**

- Top users by listening time
- Session count tracking
- Formatted time display (hours, minutes, seconds)
- Pagination for large user bases

### `verse.py`

**Daily verse display and management**

- Manual verse retrieval
- Formatted Arabic text and translation
- Surah name and verse number display
- Integration with daily verse system

### `quiz_manager.py`

**Quiz system and leaderboard**

- Dynamic quiz embeds with real-time updates
- Public results panel with correct/incorrect user lists
- Streak and points tracking
- Robust error handling and logging

## 🛠️ Utilities (`utils/`)

### Core Systems

#### `audio_manager.py` (52KB)

**Complete audio streaming system**

- Multi-reciter support (6 reciters available)
- Surah playback with seamless transitions
- Volume control and audio effects
- Queue management and shuffle functionality
- Discord voice channel integration

#### `state_manager.py` (55KB)

**Persistent state management**

- JSON file operations with atomic saves
- Backup-before-modify protection
- Error recovery and data validation
- Thread-safe state operations

#### `control_panel.py` (59KB)

**Discord control panel interface**

- Interactive buttons and dropdowns
- Real-time status updates
- Reciter selection and playback controls
- Volume and settings management

#### `listening_stats.py` (49KB)

**User activity tracking**

- Session time tracking
- User statistics aggregation
- Leaderboard data generation
- Activity monitoring and reporting

### Support Systems

#### `daily_verses.py` (22KB)

**Automated daily verse posting**

- EST timezone scheduling
- Verse queue management
- Automatic verse selection
- Embed formatting and posting

#### `backup_manager.py` (22KB)

**5-layer data protection system**

- Hourly automated backups
- ZIP compression with timestamps
- Automatic cleanup of old backups
- Corruption recovery mechanisms

#### `rich_presence.py` (30KB)

**Discord rich presence integration**

- Real-time status updates
- Current Surah display
- Listening time tracking
- Activity state management

#### `surah_mapper.py` (20KB)

**Surah name and number mapping**

- Arabic and English name mapping
- Surah number validation
- Name normalization and search
- Translation utilities

#### `tree_log.py` (24KB)

**Enhanced logging system**

- Tree-structured log formatting
- Color-coded log levels
- Comprehensive error tracking
- Development and production modes

### Data Files

#### `surahs.json` (34KB)

**Complete Surah database**

```json
{
  "1": {
    "name": "Al-Fatiha",
    "arabic": "الفاتحة",
    "verses": 7,
    "revelation": "Meccan"
  }
}
```

## 🔧 Configuration (`config/`)

### Configuration Management

- Environment variable handling
- Default value management
- Configuration validation
- Runtime configuration updates

## 📊 Version Management

### `version.py`

**Single source of truth for version information**

```python
# Centralized version management
BOT_VERSION = "2.3.2"
BOT_AUTHOR = "John (Discord: Trippixn)"
GITHUB_REPO_URL = "https://github.com/trippixn963/QuranBot"
```

## 🏗️ Architecture Principles

### Modular Design

- **Separation of Concerns**: Each module has a single responsibility
- **Loose Coupling**: Modules interact through well-defined interfaces
- **High Cohesion**: Related functionality grouped together

### Error Handling

- **Comprehensive Logging**: All operations logged with context
- **Graceful Degradation**: Bot continues operation despite errors
- **Automatic Recovery**: Self-healing mechanisms for common issues

### Data Protection

- **Atomic Operations**: Prevents data corruption
- **Backup Strategy**: Multiple layers of data protection
- **Validation**: Input and output validation throughout

### Performance

- **Async Operations**: Non-blocking Discord interactions
- **Efficient Caching**: Reduced file I/O operations
- **Resource Management**: Proper cleanup and memory management

## 🚀 Development Workflow

### Adding New Commands

1. Create new file in `commands/`
2. Use `@discord.app_commands.command` decorator
3. Import and register in `bot/main.py`
4. Add to command tree with `bot.tree.add_command()`

### Adding New Utilities

1. Create new file in `utils/`
2. Follow existing patterns and error handling
3. Add comprehensive logging
4. Include proper documentation

### Testing

- Use `tools/test_bot.py` for comprehensive testing
- All tests must pass before deployment
- Integration testing with Discord API

## 📚 Import Structure

### Common Imports

```python
# Standard library
import asyncio
import json
import logging
from datetime import datetime

# Discord
import discord
from discord.ext import commands

# Internal utilities
from utils.tree_log import tree_log
from utils.state_manager import StateManager
from version import BOT_VERSION, BOT_AUTHOR
```

### Import Guidelines

- Use absolute imports from `src/`
- Import only what's needed
- Group imports by type (standard, third-party, internal)
- Use centralized version imports

---

**Note**: This source code architecture enables maintainable, scalable, and robust Discord bot functionality with comprehensive error handling and data protection.
