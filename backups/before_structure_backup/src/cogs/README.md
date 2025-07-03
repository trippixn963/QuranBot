# QuranBot Admin Commands

This directory contains admin-only slash commands for managing the QuranBot.

## Security Setup

### Admin User ID Configuration
The admin user ID is stored securely in the `.env` file:
```
ADMIN_USER_ID=your_discord_user_id_here
```

**Important**: Never commit your actual Discord user ID to version control. The `.env` file should be in your `.gitignore`.

## Command Structure

Each command is in its own file for better organization and security:

### Admin Commands (`admin_commands/`)

#### `/restart` (`restart.py`)
- **Description**: Restart the QuranBot
- **Usage**: Immediately stops the bot (will be restarted by process manager)
- **Admin Only**: ✅

#### `/status` (`status.py`)
- **Description**: Get comprehensive bot and system status
- **Shows**: Bot info, voice status, streaming status, current song, health info, system resources (CPU, RAM, bot memory), latency
- **Admin Only**: ✅

#### `/skip` (`skip.py`)
- **Description**: Skip to the next surah
- **Action**: Stops current playback and moves to next surah
- **Admin Only**: ✅

#### `/reconnect` (`reconnect.py`)
- **Description**: Reconnect to voice channel
- **Action**: Disconnects and reconnects to voice channel
- **Admin Only**: ✅

### Utility Commands (`utility_commands/`)

#### `/info [lines]` (`logs.py`)
- **Description**: Get bot logs and configuration
- **Parameters**: `lines` (optional, default: 10, max: 30)
- **Shows**: Bot configuration and recent log entries
- **Admin Only**: ✅

## Security Features

- **Environment Variable**: Admin ID stored securely in `.env` file
- **User ID Verification**: All commands check against the admin user ID from environment
- **Ephemeral Responses**: All command responses are private (only visible to admin)
- **Error Handling**: Proper error messages for unauthorized access
- **Safe Config Display**: Configuration command hides sensitive information

## Usage Examples

```
/status          # Check bot health and system status
/info 20         # Get config and last 20 lines of logs
/skip            # Skip to next surah
/reconnect       # Reconnect to voice channel
/restart         # Restart the bot
```

## Adding New Commands

To add new admin commands:

1. Create a new command file in the appropriate directory (`admin_commands/` or `utility_commands/`)
2. Use the `@app_commands.check(is_admin)` decorator
3. Implement the `is_admin` function that reads from environment variable
4. Add error handling for unauthorized access
5. Add the command to the `commands_to_load` list in `src/bot/quran_bot.py`

Example structure:
```python
import discord
from discord import app_commands
import os

# Get admin ID from environment variable
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '0'))

def is_admin(interaction: discord.Interaction) -> bool:
    """Check if the user is the admin."""
    return interaction.user.id == ADMIN_USER_ID

@app_commands.command(name="command_name", description="Description (Admin only)")
@app_commands.check(is_admin)
async def command_name(interaction: discord.Interaction):
    # Command implementation
    pass

@command_name.error
async def command_error(interaction: discord.Interaction, error):
    # Error handling
    pass

async def setup(bot):
    """Setup the command."""
    bot.tree.add_command(command_name)
```

## VPS Deployment

For VPS deployment:

1. Set your Discord user ID in the `.env` file on the VPS
2. Ensure the `.env` file is not committed to version control
3. All commands will be available via Discord slash commands
4. Use `/status` to monitor bot health and system resources remotely
5. Use `/info` to check configuration and recent logs
6. Use `/reconnect` to fix voice connection issues 