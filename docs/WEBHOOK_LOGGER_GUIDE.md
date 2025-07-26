# Modern Webhook Logger Guide

## Overview

The QuranBot's webhook logger has been completely overhauled with a modern, async-first architecture that integrates seamlessly with the dependency injection container. This new implementation fixes all the major issues with the old webhook logger and provides much better reliability and performance.

## Key Improvements

### ✅ **What's Fixed**

- **Modern Architecture**: Clean, modular design with proper separation of concerns
- **DI Integration**: Fully integrated with the dependency injection container
- **Type Safety**: Comprehensive type hints and validation throughout
- **Memory Efficient**: Smart rate limiting that doesn't leak memory
- **Proper Async**: Non-blocking operations that don't affect bot performance
- **Error Handling**: Graceful fallbacks and comprehensive error recovery
- **Testable**: 100% test coverage with comprehensive test suite
- **Configuration Driven**: All settings configurable through the config system

### ❌ **What Was Terrible Before**

- Massive monolithic class with too many responsibilities
- Global variables and singleton pattern abuse
- No integration with modern architecture
- Hardcoded values and inflexible configuration
- Silent failures with no proper error handling
- Memory leaks in rate limiting cache
- Blocking operations that slowed down the bot
- No tests and impossible to test due to tight coupling

## Architecture

### Components

```
ModernWebhookLogger
├── WebhookConfig          # Type-safe configuration
├── RateLimitTracker      # Memory-efficient rate limiting
├── WebhookFormatter      # Message formatting for Discord
├── WebhookSender         # HTTP request handling with retries
└── Integration           # DI container and lifecycle management
```

### Key Features

1. **Async-First Design**: All operations are properly async and non-blocking
2. **Rate Limiting**: Sliding window rate limiting that prevents Discord API abuse
3. **Retry Logic**: Exponential backoff with configurable retry attempts
4. **Error Recovery**: Graceful handling of network issues and Discord rate limits
5. **Resource Management**: Proper cleanup and lifecycle management
6. **Type Safety**: Full type hints and runtime validation

## Configuration

The webhook logger is configured through the existing config system:

```python
# Environment variables in config/.env
USE_WEBHOOK_LOGGING=true
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_URL
RATE_LIMIT_PER_MINUTE=15
ENVIRONMENT=production  # Enables owner pings in production
```

The config service automatically creates a `WebhookConfig` instance:

```python
# Automatic configuration creation
webhook_config = config_service.create_webhook_config()
```

Configuration options:

- `webhook_url`: Discord webhook URL (required)
- `owner_user_id`: User ID to ping for critical errors
- `max_logs_per_minute`: Rate limit (default: 10)
- `request_timeout`: HTTP timeout in seconds (default: 30)
- `retry_attempts`: Number of retry attempts (default: 3)
- `enable_pings`: Whether to ping owner for errors (default: production only)
- `timezone`: Timezone for timestamps (default: "US/Eastern")

## Usage

### Dependency Injection Setup

The webhook logger is automatically registered in the DI container during bot initialization:

```python
# In main.py - automatically handled
if config_service.config.USE_WEBHOOK_LOGGING:
    webhook_config = config_service.create_webhook_config()
    webhook_factory = lambda: ModernWebhookLogger(
        config=webhook_config,
        logger=structured_logger,
        container=container
    )
    container.register_singleton(ModernWebhookLogger, webhook_factory)
```

### Using the Webhook Logger

Get the logger from the DI container and use it:

```python
# Get from DI container
webhook_logger = container.get(ModernWebhookLogger)

# Error logging with owner ping
await webhook_logger.log_error(
    title="Audio Service Error",
    description="Failed to connect to voice channel",
    exception=connection_error,
    context={
        "channel_id": 123456789,
        "guild_id": 987654321,
        "retry_count": 3
    },
    ping_owner=True
)

# Critical errors with automatic ping
await webhook_logger.log_critical(
    title="Bot Crash",
    description="Critical error caused bot restart",
    exception=critical_exception,
    context={"error_code": "FATAL_001"}
)

# System events
await webhook_logger.log_system(
    title="Bot Started",
    description="QuranBot has started successfully",
    context={
        "version": BOT_VERSION,
        "startup_time": "3.2s",
        "services_loaded": 8
    }
)

# QuranBot command usage tracking
await webhook_logger.log_quran_command_usage(
    command_name="quiz",
    user_name=user.display_name,
    user_id=user.id,
    user_avatar_url=user.display_avatar.url,
    command_details={
        "guild": guild.name,
        "channel": channel.name
    }
)

# Success notifications
await webhook_logger.log_success(
    title="Backup Complete",
    description="Successfully created automated backup",
    context={
        "backup_size": "45.2 MB",
        "duration": "1.3s"
    }
)
```

### Available QuranBot-Specific Methods

```python
# QuranBot command usage (verse, quiz, credits, interval, leaderboard)
await webhook_logger.log_quran_command_usage(
    command_name="quiz",
    user_name=user.display_name,
    user_id=user.id,
    user_avatar_url=user.display_avatar.url,
    command_details={"difficulty": "medium"}
)

# Quran quiz activities
await webhook_logger.log_quran_quiz_activity(
    user_name=user.display_name,
    user_id=user.id,
    question_text="What is the first surah?",
    user_answer="Al-Fatiha",
    correct_answer="Al-Fatiha",
    is_correct=True,
    user_avatar_url=user.display_avatar.url,
    quiz_stats={"streak": 5, "score": 100}
)

# QuranBot voice channel activity (join/leave during recitation)
await webhook_logger.log_voice_channel_activity(
    activity_type="join",
    user_name=member.display_name,
    user_id=member.id,
    channel_name="Quran Recitation",
    user_avatar_url=member.display_avatar.url,
    additional_info={"current_surah": "Al-Fatiha"}
)

# Control panel interactions (play/pause, skip, reciter change, etc.)
await webhook_logger.log_control_panel_interaction(
    interaction_type="button_click",
    user_name=user.display_name,
    user_id=user.id,
    action_performed="Skip to Next Surah",
    user_avatar_url=user.display_avatar.url,
    panel_details={"from_surah": 1, "to_surah": 2}
)

# Audio playback events (surah changes, reciter changes, etc.)
await webhook_logger.log_audio_event(
    event_type="surah_change",
    event_description="Automatic progression to Al-Baqarah",
    audio_details={"surah": 2, "reciter": "Saad Al Ghamdi"}
)

# Bot lifecycle events (automatic)
await webhook_logger.log_bot_startup(
    version="3.5.1",
    startup_duration=3.2,
    services_loaded=8,
    guild_count=1
)

await webhook_logger.log_bot_shutdown(
    reason="Graceful shutdown requested",
    uptime="2.5 hours",
    final_stats={"guilds_connected": 1}
)

await webhook_logger.log_bot_crash(
    error_message="Critical runtime error occurred",
    exception=exception,
    crash_context={"uptime_seconds": 9000},
    ping_owner=True  # Pings owner for crashes
)

# Discord connection events
await webhook_logger.log_discord_disconnect(
    disconnect_reason="Network timeout",
    reconnect_attempts=3,
    downtime_duration=45.2
)

await webhook_logger.log_discord_reconnect(
    reconnect_duration=12.5,
    was_successful=True,
    attempts_made=2
)

# Voice connection issues
await webhook_logger.log_voice_connection_issue(
    issue_type="connection_failed",
    channel_name="Quran Recitation",
    error_details="Permission denied",
    recovery_action="Retrying with different permissions"
)

# Standard system events
await webhook_logger.log_error("Title", "Description", exception=e)
await webhook_logger.log_system("Bot Started", "All services loaded")
await webhook_logger.log_success("Backup Complete", "Data saved successfully")
```

### User Avatars and Rich Embeds

The webhook logger supports displaying user avatars and rich media in Discord embeds:

```python
# QuranBot command usage
await webhook_logger.log_quran_command_usage(
    command_name="verse",
    user_name=user.display_name,
    user_id=user.id,
    user_avatar_url=user.display_avatar.url,
    command_details={
        "surah": 1,
        "verse": 1,
        "guild": ctx.guild.name
    }
)

# QuranBot quiz activity with user avatar
await webhook_logger.log_quran_quiz_activity(
    user_name=user.display_name,
    user_id=user.id,
    question_text="What is the first surah of the Quran?",
    user_answer="Al-Fatiha",
    correct_answer="Al-Fatiha",
    is_correct=True,
    user_avatar_url=user.display_avatar.url,
    quiz_stats={
        "difficulty": "easy",
        "streak": 5,
        "total_score": 150
    }
)

# QuranBot voice channel activity
await webhook_logger.log_voice_channel_activity(
    activity_type="join",
    user_name=member.display_name,
    user_id=member.id,
    channel_name="Quran Recitation",
    user_avatar_url=member.display_avatar.url,
    additional_info={
        "current_surah": "Al-Fatiha",
        "reciter": "Saad Al Ghamdi",
        "listeners": 5
    }
)

# Control panel interactions
await webhook_logger.log_control_panel_interaction(
    interaction_type="button_click",
    user_name=user.display_name,
    user_id=user.id,
    action_performed="Skip to Next Surah",
    user_avatar_url=user.display_avatar.url,
    panel_details={
        "from_surah": "Al-Fatiha",
        "to_surah": "Al-Baqarah",
        "reciter": "Saad Al Ghamdi"
    }
)

# Audio playback events
await webhook_logger.log_audio_event(
    event_type="surah_change",
    event_description="Automatic progression to next surah",
    audio_details={
        "previous_surah": "Al-Fatiha",
        "current_surah": "Al-Baqarah",
        "reciter": "Saad Al Ghamdi",
        "playback_mode": "continuous"
    }
)

# Custom message with avatar and images
message = WebhookMessage(
    title="Custom User Activity",
    description="User completed a special achievement",
    level=LogLevel.SUCCESS,
    author_name=user.display_name,
    author_icon_url=user.display_avatar.url,
    author_url=f"https://discord.com/users/{user.id}",
    thumbnail_url="https://example.com/achievement_badge.png",
    fields=[
        EmbedField("Achievement", "First Quiz Completed", True),
        EmbedField("Score", "100/100", True)
    ]
)
await webhook_logger._send_message(message)
```

#### Avatar and Image Options

- **`author_name`**: User's name displayed in the embed author section
- **`author_icon_url`**: User's avatar URL (shows next to the name)
- **`author_url`**: Clickable link on the user's name (usually Discord profile)
- **`thumbnail_url`**: Small image in the top-right corner of the embed
- **`image_url`**: Large image at the bottom of the embed

#### Getting Discord User Avatar URLs

```python
# From a Discord user object
user_avatar_url = user.display_avatar.url

# From a member object
member_avatar_url = member.display_avatar.url

# Fallback to default avatar if user has no custom avatar
avatar_url = user.avatar.url if user.avatar else user.default_avatar.url

# Guild-specific avatar (if user has server avatar)
if hasattr(user, 'guild_avatar') and user.guild_avatar:
    avatar_url = user.guild_avatar.url
else:
    avatar_url = user.display_avatar.url
```

## Automatic Bot Lifecycle Events

The webhook logger **automatically** sends notifications for key bot lifecycle events without any manual code needed:

### **🚀 Bot Startup**

Automatically sent when QuranBot connects to Discord:

```
┌─────────────────────────────────────────┐
│ 🚀 QuranBot Started                     │
│                                         │
│ **QuranBot v3.5.1** has started        │
│ successfully and is ready for 24/7     │
│ Quran recitation                        │
│                                         │
│ Version: 3.5.1                          │
│ Startup Time: 3.2s                     │
│ Services Loaded: 8                      │
│ Connected Guilds: 1                     │
│ Mode: 100% Automated Continuous        │
│ Started: 2 minutes ago                  │
└─────────────────────────────────────────┘
```

### **⏹️ Bot Shutdown**

Automatically sent during graceful shutdown:

```
┌─────────────────────────────────────────┐
│ ⏹️ QuranBot Shutdown                    │
│                                         │
│ **QuranBot is shutting down**          │
│                                         │
│ Graceful shutdown requested            │
│                                         │
│ Shutdown Reason: Graceful shutdown     │
│ Shutdown Time: Just now                │
│ Uptime: 2.5 hours                      │
│ Guilds Connected: 1                    │
└─────────────────────────────────────────┘
```

### **💥 Bot Crashes**

Automatically sent with owner ping when bot crashes:

```
┌─────────────────────────────────────────┐
│ 🆘 @JohnHamwi **QURANBOT CRASHED** 🆘  │ ← Owner ping
│                                         │
│ 💥 QuranBot Crashed                     │
│                                         │
│ 🚨 **CRITICAL ERROR** 🚨               │
│                                         │
│ **QuranBot has crashed and is no       │
│ longer running**                        │
│                                         │
│ Critical runtime error occurred        │
│                                         │
│ Crash Time: Just now                   │
│ Impact: 🚨 QuranBot is down            │
│ Exception Type: ConnectionResetError    │
│ Exception Message: Connection lost...   │
│ Uptime Seconds: 9000                   │
└─────────────────────────────────────────┘
```

### **🔌 Discord Connection Issues**

Automatically tracked and reported:

```
┌─────────────────────────────────────────┐
│ 🔌 Discord Disconnection               │
│                                         │
│ **QuranBot lost connection to Discord** │
│                                         │
│ Network timeout                         │
│                                         │
│ Disconnect Reason: Network timeout     │
│ Disconnect Time: 30 seconds ago        │
│ Reconnect Attempts: 3                  │
│ Downtime: 45.2s                        │
└─────────────────────────────────────────┘
```

### **✅ Discord Reconnection**

Automatically sent when connection is restored:

```
┌─────────────────────────────────────────┐
│ ✅ Discord Reconnected                  │
│                                         │
│ **QuranBot successfully reconnected    │
│ to Discord**                           │
│                                         │
│ Quran recitation service restored      │
│                                         │
│ Reconnect Time: Just now               │
│ Duration: 12.5s                        │
│ Attempts: 2                            │
│ Status: ✅ Online                      │
└─────────────────────────────────────────┘
```

### **🔊 Voice Connection Issues**

Automatically logged when voice channel problems occur:

```
┌─────────────────────────────────────────┐
│ 🔴 Voice Channel Issue                  │
│                                         │
│ **QuranBot encountered a voice         │
│ channel issue**                        │
│                                         │
│ Recitation service may be affected     │
│                                         │
│ Issue Type: Connection Failed          │
│ Channel: Quran Recitation             │
│ Time: Just now                         │
│ Error Details: Permission denied       │
│ Recovery Action: Retrying with...      │
└─────────────────────────────────────────┘
```

### **🎯 What Gets Tracked Automatically:**

- ✅ **Bot startup** with version, startup time, and service count
- ✅ **Bot shutdown** with reason, uptime, and final stats
- ✅ **Bot crashes** with full exception details and owner ping
- ✅ **Discord disconnections** with reconnection attempts
- ✅ **Discord reconnections** with success/failure status
- ✅ **Voice channel issues** during Quran recitation
- ✅ **Critical Discord events** with error context

### **📱 Owner Notifications:**

The webhook logger automatically pings you [[memory:2874293]] for:

- 🆘 **Bot crashes** (with full error details)
- 🚨 **Critical errors** (runtime failures)

Other events are logged without pings to avoid spam.

## Advanced Features

### Rate Limiting

The webhook logger uses a sliding window rate limiter that:

- Prevents Discord API abuse
- Doesn't leak memory like the old cache-based system
- Automatically handles Discord's rate limits
- Provides retry-after information

```python
# Rate limiting is automatic - no manual handling needed
for i in range(20):
    await webhook_logger.log_info(f"Message {i}", "Description")
    # Only the first 10 (or configured limit) will be sent
    # Others are automatically dropped with debug logging
```

### Error Handling

The logger gracefully handles all error conditions:

```python
# Network issues - automatic retries with exponential backoff
# Discord rate limits - respects retry-after headers
# Invalid webhooks - logs errors and continues
# Service shutdown - clean resource cleanup

# All methods return bool indicating success
success = await webhook_logger.log_error("Title", "Description")
if not success:
    # Handle failure case if needed
    pass
```

### Custom Context Data

Add structured context to any log message:

```python
await webhook_logger.log_error(
    title="Database Error",
    description="Failed to save user data",
    context={
        "table": "user_preferences",
        "user_id": 123456,
        "operation": "UPDATE",
        "error_code": "DB_001",
        "retry_count": 2,
        "duration_ms": 1500
    }
)
```

### Exception Integration

Automatically format exception information:

```python
try:
    risky_operation()
except Exception as e:
    await webhook_logger.log_error(
        title="Operation Failed",
        description="The risky operation encountered an error",
        exception=e,  # Automatically formatted
        context={"operation": "risky_operation"}
    )
```

## Integration Examples

### Audio Service Integration

```python
class AudioService:
    def __init__(self, container, ...):
        self.webhook_logger = container.get(ModernWebhookLogger)

    async def connect_to_voice_channel(self, channel_id, guild_id):
        try:
            # Connection logic...
            await self.webhook_logger.log_success(
                "Voice Connected",
                f"Successfully connected to voice channel",
                context={
                    "channel_id": channel_id,
                    "guild_id": guild_id
                }
            )
        except Exception as e:
            await self.webhook_logger.log_error(
                "Voice Connection Failed",
                "Failed to connect to voice channel",
                exception=e,
                context={"channel_id": channel_id, "guild_id": guild_id}
            )
```

### Command Error Handling

```python
@bot.event
async def on_command_error(ctx, error):
    webhook_logger = container.get(ModernWebhookLogger)

    await webhook_logger.log_error(
        title="Command Error",
        description=f"Error in command: {ctx.command}",
        exception=error,
        context={
            "user_id": ctx.author.id,
            "guild_id": ctx.guild.id if ctx.guild else None,
            "channel_id": ctx.channel.id,
            "command": str(ctx.command)
        }
    )
```

### QuranBot Command Integration

```python
@bot.command(name="quiz")
async def quiz_command(ctx):
    webhook_logger = container.get(ModernWebhookLogger)

    # Log QuranBot command usage
    await webhook_logger.log_quran_command_usage(
        command_name="quiz",
        user_name=ctx.author.display_name,
        user_id=ctx.author.id,
        user_avatar_url=ctx.author.display_avatar.url,
        command_details={
            "channel": ctx.channel.name,
            "guild": ctx.guild.name if ctx.guild else "DM"
        }
    )

    # ... quiz logic ...

    # Log Quran quiz results
    await webhook_logger.log_quran_quiz_activity(
        user_name=ctx.author.display_name,
        user_id=ctx.author.id,
        question_text=question,
        user_answer=user_answer,
        correct_answer=correct_answer,
        is_correct=is_correct,
        user_avatar_url=ctx.author.display_avatar.url,
        quiz_stats={
            "time_taken": f"{response_time:.1f}s",
            "difficulty": question_difficulty,
            "current_streak": current_streak,
            "total_score": user_total_score
        }
    )

@bot.command(name="verse")
async def verse_command(ctx, surah: int = 1, verse: int = 1):
    webhook_logger = container.get(ModernWebhookLogger)

    # Log verse command usage
    await webhook_logger.log_quran_command_usage(
        command_name="verse",
        user_name=ctx.author.display_name,
        user_id=ctx.author.id,
        user_avatar_url=ctx.author.display_avatar.url,
        command_details={
            "surah": surah,
            "verse": verse,
            "channel": ctx.channel.name
        }
    )
```

### QuranBot Voice Channel Monitoring

```python
@bot.event
async def on_voice_state_update(member, before, after):
    webhook_logger = container.get(ModernWebhookLogger)
    config = container.get(ConfigService).config

    # Only log activity for the QuranBot voice channel
    target_channel_id = config.TARGET_CHANNEL_ID

    if before.channel is None and after.channel is not None and after.channel.id == target_channel_id:
        # User joined QuranBot voice channel
        await webhook_logger.log_voice_channel_activity(
            activity_type="join",
            user_name=member.display_name,
            user_id=member.id,
            channel_name=after.channel.name,
            user_avatar_url=member.display_avatar.url,
            additional_info={
                "current_listeners": len(after.channel.members),
                "current_surah": audio_service.get_current_surah(),
                "current_reciter": audio_service.get_current_reciter()
            }
        )
    elif before.channel is not None and after.channel is None and before.channel.id == target_channel_id:
        # User left QuranBot voice channel
        await webhook_logger.log_voice_channel_activity(
            activity_type="leave",
            user_name=member.display_name,
            user_id=member.id,
            channel_name=before.channel.name,
            user_avatar_url=member.display_avatar.url,
            additional_info={
                "remaining_listeners": len(before.channel.members) - 1
            }
        )
```

### Control Panel Integration

```python
# In your control panel button handlers
async def on_skip_next_button(interaction):
    webhook_logger = container.get(ModernWebhookLogger)

    # Log control panel interaction
    await webhook_logger.log_control_panel_interaction(
        interaction_type="button_click",
        user_name=interaction.user.display_name,
        user_id=interaction.user.id,
        action_performed="Skip to Next Surah",
        user_avatar_url=interaction.user.display_avatar.url,
        panel_details={
            "previous_surah": current_surah,
            "new_surah": next_surah,
            "reciter": current_reciter
        }
    )

async def on_reciter_change(interaction, new_reciter):
    webhook_logger = container.get(ModernWebhookLogger)

    await webhook_logger.log_control_panel_interaction(
        interaction_type="button_click",
        user_name=interaction.user.display_name,
        user_id=interaction.user.id,
        action_performed="Change Reciter",
        user_avatar_url=interaction.user.display_avatar.url,
        panel_details={
            "previous_reciter": old_reciter,
            "new_reciter": new_reciter,
            "current_surah": current_surah
        }
    )
```

### Audio Service Integration

```python
class AudioService:
    async def set_surah(self, surah_number: int):
        # ... audio logic ...

        # Log surah change
        webhook_logger = self.container.get(ModernWebhookLogger)
        await webhook_logger.log_audio_event(
            event_type="surah_change",
            event_description=f"Surah changed to {surah_info.name}",
            audio_details={
                "surah_number": surah_number,
                "surah_name": surah_info.name,
                "reciter": self.current_reciter,
                "triggered_by": "user_command"  # or "automatic"
            }
        )

    async def set_reciter(self, reciter_name: str):
        # ... reciter change logic ...

        webhook_logger = self.container.get(ModernWebhookLogger)
        await webhook_logger.log_audio_event(
            event_type="reciter_change",
            event_description=f"Reciter changed to {reciter_name}",
            audio_details={
                "previous_reciter": old_reciter,
                "new_reciter": reciter_name,
                "current_surah": current_surah
            }
        )
```

### Startup/Shutdown Notifications

```python
class ModernizedQuranBot:
    async def initialize(self):
        # ... initialization logic ...

        webhook_logger = self.container.get(ModernWebhookLogger)
        await webhook_logger.log_system(
            "Bot Initialization Complete",
            "All services loaded and bot is ready",
            context={
                "version": BOT_VERSION,
                "services": len(self.container._singletons),
                "startup_time": f"{startup_duration:.1f}s"
            }
        )

    async def shutdown(self):
        webhook_logger = self.container.get(ModernWebhookLogger)
        await webhook_logger.log_system(
            "Bot Shutdown",
            "Graceful shutdown initiated",
            context={"uptime": uptime_str}
        )

        # Webhook logger cleanup is automatic in DI container
```

## Testing

The webhook logger is fully testable with comprehensive test coverage:

```python
# Run webhook logger tests
pytest tests/test_webhook_logger.py -v

# Run with coverage
pytest tests/test_webhook_logger.py --cov=src.core.webhook_logger
```

Test categories:

- Configuration validation
- Rate limiting behavior
- Message formatting
- Error handling
- Integration scenarios
- End-to-end workflows

## Migration from Old System

### Automatic Migration

The new webhook logger is automatically used when enabled in configuration. No code changes required for basic functionality.

### Old System Removal

The old webhook logger files should be removed:

- `src/utils/discord_webhook_logger.py` (old implementation)
- `src/utils/unified_discord_logger.py` (old unified interface)

### Configuration Migration

Update your `.env` file:

```bash
# Old configuration (still works)
USE_WEBHOOK_LOGGING=true
DISCORD_WEBHOOK_URL=your_webhook_url

# New configuration options (optional)
RATE_LIMIT_PER_MINUTE=15
ENVIRONMENT=production
```

## Performance Benefits

### Memory Usage

- **Old System**: Unbounded cache growth, memory leaks
- **New System**: Fixed memory usage, efficient sliding window

### Network Performance

- **Old System**: No retry logic, poor error handling
- **New System**: Smart retries, exponential backoff, Discord rate limit handling

### Bot Performance

- **Old System**: Blocking operations, global state pollution
- **New System**: Fully async, clean architecture, no blocking

### Error Recovery

- **Old System**: Silent failures, no fallbacks
- **New System**: Comprehensive error handling, graceful degradation

## Troubleshooting

### Common Issues

1. **Webhook not sending messages**

   ```python
   # Check configuration
   config = container.get(ConfigService).config
   print(f"Webhook enabled: {config.USE_WEBHOOK_LOGGING}")
   print(f"Webhook URL configured: {bool(config.DISCORD_WEBHOOK_URL)}")

   # Check initialization
   webhook_logger = container.get(ModernWebhookLogger)
   print(f"Initialized: {webhook_logger.initialized}")
   ```

2. **Rate limiting too restrictive**

   ```bash
   # Increase rate limit in .env
   RATE_LIMIT_PER_MINUTE=20
   ```

3. **Not receiving ping notifications**
   ```bash
   # Ensure production environment and correct user ID
   ENVIRONMENT=production
   DEVELOPER_ID=your_discord_user_id
   ```

### Debug Mode

Enable debug logging to see webhook activity:

```python
# In configuration
LOG_LEVEL=DEBUG

# Check logs for webhook debug messages
tail -f logs/quranbot.log | grep webhook
```

## Best Practices

1. **Use Appropriate Log Levels**
   - `log_critical()` for bot crashes and critical failures
   - `log_error()` for recoverable errors that need attention
   - `log_warning()` for potential issues
   - `log_system()` for important bot events
   - `log_success()` for significant positive events

2. **Provide Context**

   ```python
   # Good - provides useful context
   await webhook_logger.log_error(
       "Database Connection Failed",
       "Failed to connect to user database",
       context={
           "database": "user_data",
           "host": db_host,
           "timeout": timeout_seconds,
           "retry_count": retries
       }
   )

   # Bad - minimal context
   await webhook_logger.log_error("Error", "Database failed")
   ```

3. **Handle Return Values When Needed**

   ```python
   # For critical notifications, check success
   success = await webhook_logger.log_critical(
       "Critical System Error",
       "Database completely unavailable"
   )
   if not success:
       # Maybe use alternative notification method
       logger.critical("Failed to send critical webhook alert")
   ```

4. **Rate Limit Awareness**

   ```python
   # Don't log in tight loops
   for item in large_list:
       # This will be rate limited
       await webhook_logger.log_info("Processing", f"Item {item}")

   # Better - batch or summarize
   await webhook_logger.log_info(
       "Batch Processing Complete",
       f"Processed {len(large_list)} items",
       context={"duration": duration, "errors": error_count}
   )
   ```

The modern webhook logger provides a robust, reliable, and maintainable solution for Discord notifications that integrates seamlessly with QuranBot's modernized architecture.
