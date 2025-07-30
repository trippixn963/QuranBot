# QuranBot Configuration Migration Guide

## Overview

The QuranBot configuration system has been simplified to provide a **single source of truth** for all configuration settings. This replaces the previous complex multi-file configuration system with a single, easy-to-use module.

## What Changed

### Before (Complex System)
- Multiple configuration files: `bot_config.py`, `config_service.py`, `unified_config.py`
- Complex service patterns and dependency injection
- Scattered configuration logic across multiple modules
- Difficult to maintain and understand

### After (Unified System)
- **Single file**: `src/config/config.py`
- **Single class**: `QuranBotConfig`
- **Simple access**: `get_config()` function
- **Clear validation**: Built-in Pydantic validation
- **Easy to use**: Direct attribute access

## Migration Guide

### 1. Update Imports

**Old way:**
```python
from src.config import BotConfig, ConfigService
from src.config.bot_config import BotConfig
from src.config.config_service import ConfigService

# Get configuration
config_service = ConfigService()
config = config_service.config
token = config_service.get_discord_token()
```

**New way:**
```python
from src.config import get_config, QuranBotConfig
from src.config.config import get_config

# Get configuration
config = get_config()
token = config.discord_token
```

### 2. Configuration Access

**Old way:**
```python
# Service-based access
config_service = ConfigService()
token = config_service.get_discord_token()
guild_id = config_service.get_guild_id()
channel_id = config_service.get_target_channel_id()

# Direct access
config = BotConfig()
token = config.DISCORD_TOKEN
guild_id = config.GUILD_ID
```

**New way:**
```python
# Simple direct access
config = get_config()
token = config.discord_token
guild_id = config.guild_id
target_channel = config.target_channel_id

# Or use convenience functions
from src.config import get_discord_token, get_guild_id, get_target_channel_id
token = get_discord_token()
guild_id = get_guild_id()
channel_id = get_target_channel_id()
```

### 3. Admin User Checking

**Old way:**
```python
config_service = ConfigService()
is_admin = config_service.is_admin_user(user_id)
```

**New way:**
```python
# Direct access
config = get_config()
is_admin = config.is_admin_user(user_id)

# Or use convenience function
from src.config import is_admin
is_admin_user = is_admin(user_id)
```

### 4. Webhook URL Access

**Old way:**
```python
config = BotConfig()
webhook_url = config.get_webhook_url("bot_status")
```

**New way:**
```python
config = get_config()
webhook_url = config.get_webhook_url("bot_status")

# Or use convenience function
from src.config import get_webhook_url
webhook_url = get_webhook_url("bot_status")
```

### 5. Configuration Validation

**Old way:**
```python
config_service = ConfigService()
summary = config_service.validate_configuration()
```

**New way:**
```python
from src.config import validate_config, print_config_summary

# Get validation summary
summary = validate_config()

# Print formatted summary
print_config_summary()
```

## Configuration Fields

All configuration fields are now available as simple attributes:

### Core Discord Settings
- `config.discord_token` - Discord bot token
- `config.guild_id` - Discord server ID
- `config.target_channel_id` - Voice channel ID

### Optional Discord Settings
- `config.control_channel_id` - Control commands channel
- `config.panel_channel_id` - Control panel channel
- `config.logs_channel_id` - Bot logs channel
- `config.daily_verse_channel_id` - Daily verses channel
- `config.panel_access_role_id` - Panel access role

### Admin Settings
- `config.admin_user_ids` - Comma-separated admin user IDs
- `config.developer_id` - Developer user ID

### Audio Settings
- `config.audio_folder` - Audio files directory
- `config.default_reciter` - Default Quran reciter
- `config.ffmpeg_path` - FFmpeg executable path
- `config.audio_quality` - Audio quality setting
- `config.default_shuffle` - Default shuffle mode
- `config.default_loop` - Default loop mode

### Logging Settings
- `config.log_level` - Application log level
- `config.use_webhook_logging` - Enable webhook logging
- `config.webhook_bot_status` - Bot status webhook URL
- `config.webhook_quran_audio` - Quran audio webhook URL
- `config.webhook_commands_panel` - Commands panel webhook URL
- `config.webhook_user_activity` - User activity webhook URL
- `config.webhook_data_analytics` - Data analytics webhook URL
- `config.webhook_errors_alerts` - Errors alerts webhook URL
- `config.webhook_daily_reports` - Daily reports webhook URL
- `config.discord_webhook_url` - Legacy webhook URL

### Performance Settings
- `config.cache_ttl_seconds` - Cache time-to-live
- `config.rate_limit_per_minute` - Rate limit per minute
- `config.max_concurrent_audio` - Max concurrent audio streams
- `config.backup_interval_hours` - Backup interval

### Environment Settings
- `config.environment` - Application environment (development/production)

### Optional Integrations
- `config.openai_api_key` - OpenAI API key for Islamic AI
- `config.vps_host` - VPS host for deployment

## Convenience Functions

The simplified system provides these convenience functions:

```python
from src.config import (
    get_config,
    reload_config,
    validate_config,
    print_config_summary,
    is_admin,
    get_discord_token,
    get_guild_id,
    get_target_channel_id,
    get_audio_folder,
    get_ffmpeg_path,
    is_webhook_logging_enabled,
    get_webhook_url,
)
```

## Environment Variables

The configuration automatically loads from:
1. Environment variables
2. `config/.env` file
3. Default values defined in the configuration

All environment variable names are automatically mapped to configuration fields.

## Validation

The configuration includes comprehensive validation:
- Required fields validation
- Type checking
- Value range validation
- Custom validators for Discord tokens, webhook URLs, etc.
- Cross-field validation (e.g., webhook logging requires at least one webhook URL)

## Benefits

1. **Single Source of Truth**: All configuration in one place
2. **Type Safety**: Full Pydantic validation
3. **Easy to Use**: Simple attribute access
4. **Clear Documentation**: All fields documented with descriptions
5. **Automatic Validation**: Built-in validation with clear error messages
6. **Environment Support**: Automatic .env file loading
7. **Backward Compatibility**: Legacy imports still work with deprecation warnings

## Testing

Test the new configuration system:

```bash
# Activate virtual environment
source .venv/bin/activate

# Run configuration test
python test_simple_config.py

# Test configuration summary
python -c "from src.config.config import print_config_summary; print_config_summary()"

## Migration Checklist

- [ ] Update imports to use `get_config()` instead of `ConfigService()`
- [ ] Replace `config_service.get_*()` calls with direct attribute access
- [ ] Update webhook URL access to use `config.get_webhook_url()`
- [ ] Replace admin checking with `config.is_admin_user()` or `is_admin()`
- [ ] Update validation calls to use `validate_config()` and `print_config_summary()`
- [ ] Test configuration loading and validation
- [ ] Remove any remaining references to old configuration classes

## Current Structure

The configuration system is now clean and focused:

```
src/config/
├── config.py          # 🎯 Primary configuration (single source of truth)
├── __init__.py        # 📦 Main exports and access functions
└── exceptions.py      # 🔧 Exception classes for error handling
```

## Legacy Files Removed

The following legacy files have been removed to simplify the system:
- `bot_config.py` - Replaced by `config.py`
- `config_service.py` - Replaced by direct access functions
- `unified_config.py` - Replaced by `config.py`

This ensures a clean, single-source-of-truth configuration system. 