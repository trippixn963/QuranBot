# Cursor AI Assistant Context for QuranBot Project

## Project Overview
- **Project Name:** QuranBot/QuranAudioBot
- **GitHub Repository:** https://github.com/JohnHamwi/QuranAudioBot
- **Developer Email:** john.hamwi10@gmail.com
- **Current Version:** v1.1.0
- **Platform:** Discord Bot for Quran audio playback

## User Preferences & Requirements

### Development Preferences
- **Never run multiple bot instances simultaneously** - Bot includes built-in instance detection
- **Every file must include logging, debugging, and error handling** - Comprehensive tracebacks and logs required
- **Tree structured (tree/JSON-like) logs** for readability in every file
- **Minimal, targeted edits** - Don't replace entire files during refactoring
- **Periodic progress updates** on ongoing tasks

### Deployment Preferences
- **Commands should only be run on VPS, not local machine**
- **Never move data folder to VPS** - Avoid overriding stored information
- **Never override or overwrite data on VPS** during operations

### Feature Preferences
- **Use `/leaderboard` instead of `/quranleaderboard`** for Quran MCQ leaderboard
- **Arabic and English text in separate black boxes** for question embeds (similar to verse embeds)

## Project Structure & Key Files

### Core Files
- `main.py` - Main bot entry point with instance detection
- `bot_manager.py` - Bot management utility (start/stop/restart/status)
- `src/utils/tree_log.py` - Tree-structured logging system
- `requirements.txt` - Dependencies (discord.py, python-dotenv, etc.)

### Configuration
- `.env` - Single configuration file (not committed to repo)
- `env_template.txt` - Template for environment variables
- Uses `python-dotenv` for environment variable loading

### Logging System
- **Run Separation:** Each bot run gets unique ID (e.g., `DB257D45`)
- **Visual Separators:** 80-character lines between runs
- **Tree Structure:** Hierarchical logging with emojis and indentation
- **Line Breaks:** Automatic spacing between tree sections
- **Daily Log Files:** Organized by date in `logs/` directory

## Recent Implementation Details

### Instance Management
- Built-in process detection prevents multiple instances
- Automatic cleanup of existing instances with user confirmation
- Bot manager utility for easy start/stop/restart operations

### Logging Enhancements
- **Run ID System:** Unique 8-character hex IDs for each run
- **Run Headers:** Detailed start information with timestamp, version, run ID
- **Section Spacing:** Automatic blank lines between tree sections
- **Run End Logging:** Completion tracking with reason codes

### GitHub Repository Features
- Comprehensive `.gitignore` excluding sensitive files
- Professional README with badges and setup instructions
- MIT License included
- GitHub releases with version tags (v1.1.0, v1.1.1)
- Security-focused approach with no sensitive data exposure

## Current State
- Bot successfully connects to Discord and plays audio
- Voice channel connection working (`🕋┃Quran` channel)
- Audio playback from `audio/Saad Al Ghamdi` folder
- 114 audio files detected and playing
- Instance detection and management fully functional
- Enhanced logging with run separation and spacing

## Development Environment
- **Python Dependencies:** discord.py, python-dotenv
- **External Dependencies:** FFmpeg for audio processing
- **Discord API:** Voice connection and audio streaming
- **Log Format:** Tree-structured with EST timestamps

## Key Functions in tree_log.py
- `log_run_separator()` - Creates run separators
- `log_run_header()` - Logs run start information
- `log_run_end()` - Logs run completion
- `log_spacing()` - Adds section spacing
- `log_tree()` - Main tree logging function
- `log_info()`, `log_success()`, `log_error()` - Specific log types

## Mac Migration Notes
- Pull latest from GitHub: `git pull origin master`
- Create `.env` file using `env_template.txt` as reference
- Ensure FFmpeg is installed and accessible
- Run bot with: `python main.py`
- Use bot manager: `python bot_manager.py status/start/stop/restart`

## Instructions for New Cursor Instance
When working with this project on Mac, please:
1. Follow all user preferences listed above
2. Maintain the tree-structured logging format
3. Use minimal edits instead of full file replacements
4. Include comprehensive error handling and logging
5. Respect the VPS-only deployment preference
6. Maintain the instance detection system
7. Follow the established project structure and conventions

This context file contains all the essential information needed to continue development seamlessly on your Mac. 