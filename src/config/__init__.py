# =============================================================================
# QuranBot - Configuration Management Module
# =============================================================================
# Configuration management module for QuranBot.
# This module provides centralized configuration management with:
# - Type-safe configuration using Pydantic
# - Environment variable loading and validation
# - Singleton configuration service
# - Consistent error handling
#
# Usage:
#     from src.config import BotConfig, ConfigService, get_config
#
#     # Get configuration service (singleton)
#     config_service = ConfigService()
#
#     # Get configuration directly
#     config = get_config()
#
#     # Access configuration values
#     token = config_service.get_discord_token()
#     guild_id = config_service.get_guild_id()
# =============================================================================

from .bot_config import BotConfig, LogLevel, ReciterName
from .config_service import ConfigService, get_config, get_config_service
from .exceptions import ConfigurationError, MissingConfigurationError, ValidationError

__all__ = [
    # Core configuration classes
    "BotConfig",
    "ConfigService",
    # Enums
    "LogLevel",
    "ReciterName",
    # Convenience functions
    "get_config",
    "get_config_service",
    # Exceptions
    "ConfigurationError",
    "MissingConfigurationError",
    "ValidationError",
]
