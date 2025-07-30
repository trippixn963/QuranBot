# =============================================================================
# QuranBot - Configuration Management Module
# =============================================================================
# Configuration system with single source of truth.
# All configuration is centralized in config.py for easy management.
# =============================================================================

# Primary configuration system
from .config import (  # Convenience functions
    Environment,
    LogLevel,
    QuranBotConfig,
    ReciterName,
    get_audio_folder,
    get_config,
    get_discord_token,
    get_ffmpeg_path,
    get_guild_id,
    get_target_channel_id,
    get_webhook_url,
    is_admin,
    is_webhook_logging_enabled,
    print_config_summary,
    reload_config,
    validate_config,
)

# =============================================================================
# PRIMARY EXPORTS
# =============================================================================

__all__ = [
    # Main configuration class and enums
    "QuranBotConfig",
    "Environment",
    "LogLevel",
    "ReciterName",
    # Configuration access functions
    "get_config",
    "reload_config",
    "validate_config",
    "print_config_summary",
    # Convenience functions
    "is_admin",
    "get_discord_token",
    "get_guild_id",
    "get_target_channel_id",
    "get_audio_folder",
    "get_ffmpeg_path",
    "is_webhook_logging_enabled",
    "get_webhook_url",
]
