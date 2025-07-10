# Environment Configuration Guide

This guide explains how to set up the environment configuration for QuranBot.

## Configuration File

Create a file named `.env` in the `config/` directory with the following structure:

```env
# =============================================================================
# QuranBot Environment Configuration
# =============================================================================

# Discord Bot Configuration
# Required: Your Discord bot token from Discord Developer Portal
DISCORD_TOKEN=your_bot_token_here

# Discord Channel IDs (Required)
# Get these IDs by enabling Developer Mode in Discord and right-clicking channels
TARGET_CHANNEL_ID=123456789012345678  # Channel for Quran recitations
PANEL_CHANNEL_ID=123456789012345678   # Channel for control panel
LOGS_CHANNEL_ID=123456789012345678    # Channel for bot logs
DAILY_VERSE_CHANNEL_ID=123456789012345678  # Channel for daily verses

# Admin User IDs (Required)
# Get these by right-clicking users with Developer Mode enabled
ADMIN_USER_ID=123456789012345678      # Bot administrator's Discord ID (receives quiz answers)
DEVELOPER_ID=123456789012345678       # Bot developer's Discord ID

# Guild ID (Required)
# Get this by right-clicking your server with Developer Mode enabled
GUILD_ID=123456789012345678           # Your Discord server ID

# Role ID (Required)
# Get this by right-clicking the role with Developer Mode enabled
PANEL_ACCESS_ROLE_ID=123456789012345678  # Role that can access control panel

# Audio Configuration (Optional - defaults shown)
AUDIO_FOLDER=audio                     # Directory containing audio files
DEFAULT_RECITER=Saad Al Ghamdi        # Default Quran reciter
AUDIO_QUALITY=128k                     # Audio quality for playback
DEFAULT_SHUFFLE=false                  # Whether to shuffle by default
DEFAULT_LOOP=false                     # Whether to loop by default

# FFmpeg Configuration (Optional)
# The bot will auto-detect FFmpeg if not specified
FFMPEG_PATH=/opt/homebrew/bin/ffmpeg   # Path to FFmpeg executable (macOS)
# FFMPEG_PATH=/usr/bin/ffmpeg          # Path to FFmpeg executable (Linux/VPS)

# Quiz System Configuration (Optional)
QUIZ_TIMEOUT=60                        # Quiz timeout in seconds (default: 60)
QUIZ_POINTS_CORRECT=1                  # Points awarded for correct answers
QUIZ_POINTS_INCORRECT=0                # Points deducted for incorrect answers
```

## Getting Discord IDs

1. Enable Developer Mode in Discord:
   - Open Discord Settings
   - Go to "App Settings" > "Advanced"
   - Enable "Developer Mode"

2. Get Channel IDs:
   - Right-click any channel
   - Click "Copy ID"

3. Get User IDs:
   - Right-click any user
   - Click "Copy ID"

4. Get Server (Guild) ID:
   - Right-click your server name
   - Click "Copy ID"

5. Get Role ID:
   - Go to Server Settings > Roles
   - Right-click the role
   - Click "Copy ID"

## New Features in v3.5.0

### Admin Answer Key System

The `ADMIN_USER_ID` configuration now serves a dual purpose:
- **Administrative Access**: Controls access to admin-only features
- **Quiz Answer Key**: Admin receives correct answers via DM before quiz timer starts

When a quiz question is posted:
1. The quiz question appears publicly in the channel
2. The admin user receives a private DM with the correct answer
3. The admin can participate in the quiz while having answer knowledge for moderation

### Enhanced Quiz System

- **Visual Progress Bar**: 20-block progress bar with color-coded time warnings
- **Time Warnings**: Automatic warnings at 30s, 20s, 10s, and 5s remaining
- **Paginated Leaderboard**: Shows top 30 users with 5 per page navigation
- **Enhanced Logging**: Comprehensive user interaction logging with EST timestamps

### Improved Verse System

- **Reaction Monitoring**: Tracks both authorized and unauthorized reactions
- **Enhanced Scheduling**: Better daily verse scheduling and formatting
- **User Interaction Logging**: Detailed logging of all verse interactions

## Important Notes

- **All Discord IDs are required** and must be valid
- **The bot will not start** if any required IDs are missing or set to "0"
- **Keep your bot token secret** and never share it publicly
- **Bot permissions required**: The bot needs proper permissions in all channels
- **Audio configuration is optional** and will use defaults if not specified
- **FFmpeg is required** for audio playback but will be auto-detected if not specified
- **Admin features**: Only the configured admin user receives quiz answer keys

## Environment-Specific Configuration

### Development (macOS)
```env
FFMPEG_PATH=/opt/homebrew/bin/ffmpeg
```

### Production (Linux/VPS)
```env
FFMPEG_PATH=/usr/bin/ffmpeg
```

## Troubleshooting

### Common Issues

1. **Bot won't start**: Check that all required IDs are set and valid
2. **Audio not working**: Verify FFmpeg path and audio file structure
3. **Quiz system not working**: Ensure admin user ID is correctly configured
4. **Permissions errors**: Verify bot has necessary permissions in all channels

### Validation

The bot will validate your configuration on startup and provide detailed error messages for any issues.
