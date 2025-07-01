# QuranBot 🤖📖

A professional, fully automated 24/7 Discord bot that streams Quran recitations in a specific voice channel. Features enhanced logging, dynamic rich presence, health monitoring, and interactive control panels.

## Features ✨

- **24/7 Quran Streaming** 📻 - Continuous playback of all 114 surahs
- **Dynamic Rich Presence** 🎮 - Shows current surah with elapsed/total time
- **Enhanced Logging** 📝 - Emoji-enhanced logs with structured data
- **Health Monitoring** 💚 - Hourly health reports and performance tracking
- **Interactive Control Panel** 🎛️ - User-friendly buttons and menus
- **Admin Commands** ⚙️ - Restart, status, skip, reconnect functionality
- **Graceful Shutdown** 🔄 - Clean state saving and disconnection
- **Cross-Platform** 💻 - Works on Windows, Linux, and macOS

## Commands 🎯

### Admin Commands (Restricted Access)
- `/restart` - Restart the bot
- `/status` - Show detailed bot status
- `/skip` - Skip current surah
- `/reconnect` - Reconnect to voice channel

### Utility Commands
- `/logs` - View recent bot logs

### User Commands
- `/panel` - Create interactive control panel (Voice channel users only)

## Control Panel Features 🎛️

The control panel provides an interactive interface with buttons for:
- **🎵 Now Playing** - Check current surah and bot status
- **📊 Bot Status** - View detailed bot information
- **📖 Surah List** - See available surahs and current playing

## Setup 🚀

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install FFmpeg**
   - **Windows**: Run `scripts/windows/check_and_update_ffmpeg.bat`
   - **Linux/macOS**: Run `scripts/linux/check_and_update_ffmpeg.sh`

3. **Configure Environment**
   - Copy `.env.example` to `.env`
   - Fill in your Discord bot token and channel IDs

4. **Download Quran Audio**
   - Place 114 MP3 files (001.mp3 to 114.mp3) in the `audio/` directory
   - Run validation script: `scripts/windows/validate_mp3s_with_ffmpeg.bat`

5. **Run the Bot**
   ```bash
   python run.py
   ```

## File Structure 📁

```
QuranBot/
├── audio/                 # Quran MP3 files (001.mp3 to 114.mp3)
├── logs/                  # Daily rotating log files
├── scripts/               # Cross-platform utility scripts
├── src/
│   ├── bot/
│   │   └── quran_bot.py   # Main bot implementation
│   ├── cogs/
│   │   ├── admin_commands/    # Admin-only commands
│   │   ├── utility_commands/  # Utility commands
│   │   └── user_commands/     # User control panel
│   └── utils/             # Utilities and helpers
├── run.py                 # Bot entry point
└── requirements.txt       # Python dependencies
```

## Configuration ⚙️

### Environment Variables (.env)
- `DISCORD_TOKEN` - Your Discord bot token
- `TARGET_CHANNEL_ID` - Voice channel ID for streaming
- `PANEL_CHANNEL_ID` - Text channel ID for control panel (default: 1389716643512455219)
- `LOGS_CHANNEL_ID` - Channel ID for health reports
- `ADMIN_USER_ID` - Your Discord user ID for admin commands

### Audio Files
- Format: MP3 files named `001.mp3` to `114.mp3`
- Location: `audio/` directory
- Validation: Use provided scripts to check file integrity

## Logging 📝

The bot uses enhanced logging with:
- **Emoji-enhanced messages** 🎯
- **Structured data** with extra fields
- **Daily rotating files** in `logs/` directory
- **Console output** with colors
- **Performance tracking** and error monitoring

## Health Monitoring 💚

- **Hourly health reports** sent to logs channel
- **Performance metrics** tracking
- **Connection status** monitoring
- **Audio playback** statistics
- **Error tracking** and reporting

## Troubleshooting 🔧

### Common Issues
1. **FFmpeg not found**: Run the FFmpeg installation script
2. **Audio files missing**: Download and place MP3 files in `audio/` directory
3. **Voice disconnections**: Bot automatically reconnects with exponential backoff
4. **Permission errors**: Ensure bot has proper Discord permissions

### Validation Scripts
- **Windows**: `scripts/windows/validate_mp3s_with_ffmpeg.bat`
- **Linux/macOS**: `scripts/linux/validate_mp3s_with_ffmpeg.sh`

## Development 🛠️

### Adding New Commands
1. Create command file in appropriate `cogs/` directory
2. Implement command with proper error handling
3. Add to bot's command loading list in `quran_bot.py`
4. Test thoroughly before deployment

### Logging Best Practices
- Use emoji-enhanced log messages
- Include structured data with `extra` field
- Use appropriate log levels (DEBUG, INFO, WARNING, ERROR)
- Track performance metrics where relevant

## License 📄

This project is licensed under the MIT License - see the LICENSE file for details.

## Support 💬

For support and questions:
- Check the troubleshooting section
- Review logs in the `logs/` directory
- Use the `/status` command for bot diagnostics
- Run validation scripts for audio file issues 