# =============================================================================
# QuranBot - Configuration Service Module
# =============================================================================
# Configuration service for centralized config access and management.
# Provides singleton access to bot configuration across the application.
# =============================================================================

from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from src.core.exceptions import ConfigurationError

from .bot_config import BotConfig, ReciterName


class ConfigService:
    """Centralized configuration service for QuranBot.

    This service provides:
    - Singleton access to configuration
    - Configuration validation and error handling
    - Environment-specific configuration loading
    - Configuration change detection and reloading
    """

    _instance: Optional["ConfigService"] = None
    _config: BotConfig | None = None

    def __new__(cls) -> "ConfigService":
        """Ensure singleton pattern for configuration service."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize configuration service."""
        if self._config is None:
            self._load_configuration()

    def _load_configuration(self) -> None:
        """Load configuration from environment and validate."""
        try:
            self._config = BotConfig()
        except Exception as e:
            raise ConfigurationError(
                f"Failed to load configuration: {e!s}",
                {"error_type": type(e).__name__},
            ) from e

    @property
    def config(self) -> BotConfig:
        """Get the current configuration instance.

        Returns:
            Current BotConfig instance

        Raises:
            ConfigurationError: If configuration is not loaded
        """
        if self._config is None:
            raise ConfigurationError("Configuration not loaded")
        return self._config

    def reload_configuration(self) -> None:
        """Reload configuration from environment variables.

        This method allows for runtime configuration updates without
        restarting the application.

        Raises:
            ConfigurationError: If configuration reload fails
        """
        try:
            old_config = self._config
            self._load_configuration()

            # Log configuration changes if needed
            if old_config and self._has_significant_changes(old_config, self._config):
                self._log_configuration_changes(old_config, self._config)

        except Exception as e:
            # Restore old configuration if reload fails
            if hasattr(self, "_config") and self._config is not None:
                # Keep the old configuration
                pass
            raise ConfigurationError(
                f"Failed to reload configuration: {e!s}",
                {"error_type": type(e).__name__},
            ) from e

    def _has_significant_changes(
        self, old_config: BotConfig, new_config: BotConfig
    ) -> bool:
        """Check if there are significant changes between configurations.

        Args:
            old_config: Previous configuration
            new_config: New configuration

        Returns:
            True if there are significant changes, False otherwise
        """
        significant_fields = [
            "discord_token",
            "guild_id",
            "target_channel_id",
            "panel_channel_id",
            "audio_folder",
            "default_reciter",
            "ffmpeg_path",
            "log_level",
        ]

        for field in significant_fields:
            if getattr(old_config, field, None) != getattr(new_config, field, None):
                return True

        return False

    def _log_configuration_changes(
        self, old_config: BotConfig, new_config: BotConfig
    ) -> None:
        """Log significant configuration changes.

        Args:
            old_config: Previous configuration
            new_config: New configuration
        """
        # This would integrate with the logging system
        # For now, we'll just track that changes occurred
        pass

    # =============================================================================
    # Configuration Access Methods
    # =============================================================================

    def get_discord_token(self) -> str:
        """Get Discord bot token.

        Returns:
            Discord bot token
        """
        return self.config.DISCORD_TOKEN

    def get_guild_id(self) -> int:
        """Get Discord guild (server) ID.

        Returns:
            Discord guild ID
        """
        return self.config.GUILD_ID

    def get_target_channel_id(self) -> int:
        """Get target voice channel ID.

        Returns:
            Target voice channel ID
        """
        return self.config.TARGET_CHANNEL_ID

    def get_panel_channel_id(self) -> int | None:
        """Get control panel channel ID.

        Returns:
            Panel channel ID or None if not configured
        """
        return self.config.PANEL_CHANNEL_ID

    def get_audio_folder(self, reciter: ReciterName | None = None) -> Path:
        """Get audio folder path for a specific reciter.

        Args:
            reciter: Reciter name, defaults to default reciter

        Returns:
            Path to audio folder
        """
        return self.config.get_reciter_audio_folder(reciter)

    def get_default_reciter(self) -> ReciterName:
        """Get default reciter.

        Returns:
            Default reciter name
        """
        return self.config.DEFAULT_RECITER

    def get_ffmpeg_path(self) -> Path:
        """Get FFmpeg executable path.

        Returns:
            Path to FFmpeg executable
        """
        return self.config.FFMPEG_PATH

    def get_admin_user_ids(self) -> list[int]:
        """Get list of admin user IDs.

        Returns:
            List of admin user IDs
        """
        return self.config.admin_user_ids.copy()

    def is_admin_user(self, user_id: int) -> bool:
        """Check if user is an admin.

        Args:
            user_id: Discord user ID to check

        Returns:
            True if user is admin, False otherwise
        """
        return self.config.is_admin_user(user_id)

    def get_rate_limit(self) -> int:
        """Get rate limit per minute.

        Returns:
            Rate limit per minute per user
        """
        return self.config.RATE_LIMIT_PER_MINUTE

    def get_cache_ttl(self) -> int:
        """Get cache time-to-live in seconds.

        Returns:
            Cache TTL in seconds
        """
        return self.config.CACHE_TTL

    def is_webhook_logging_enabled(self) -> bool:
        """Check if webhook logging is enabled.

        Returns:
            True if webhook logging is enabled, False otherwise
        """
        return self.config.USE_WEBHOOK_LOGGING

    def get_webhook_url(self) -> str | None:
        """Get Discord webhook URL for logging.

        Returns:
            Webhook URL or None if not configured
        """
        return self.config.DISCORD_WEBHOOK_URL

    def get_panel_access_role_id(self) -> int | None:
        """Get panel access role ID.

        Returns:
            Panel access role ID or None if not configured
        """
        return self.config.PANEL_ACCESS_ROLE_ID

    def get_voice_channel_id(self) -> int | None:
        """Get voice channel ID (alias for target channel).

        Returns:
            Voice channel ID or None if not configured
        """
        return self.config.VOICE_CHANNEL_ID or self.config.TARGET_CHANNEL_ID

    # =============================================================================
    # Configuration Validation Methods
    # =============================================================================

    def validate_configuration(self) -> dict[str, Any]:
        """Validate current configuration and return status.

        Returns:
            Dictionary containing validation results
        """
        try:
            validation_summary = self.config.get_validation_summary()

            # Additional runtime validations
            validation_summary.update(
                {
                    "environment_file_exists": Path("config/.env").exists(),
                    "all_required_channels_configured": all(
                        [
                            self.config.TARGET_CHANNEL_ID,
                            # PANEL_CHANNEL_ID is optional
                        ]
                    ),
                    "logging_properly_configured": (
                        not self.config.USE_WEBHOOK_LOGGING
                        or bool(self.config.DISCORD_WEBHOOK_URL)
                    ),
                }
            )

            # Calculate overall status
            critical_checks = [
                validation_summary["discord_configured"],
                validation_summary["audio_configured"],
                validation_summary["ffmpeg_available"],
                validation_summary["all_required_channels_configured"],
            ]

            validation_summary["overall_status"] = all(critical_checks)
            validation_summary["critical_issues"] = sum(
                1 for check in critical_checks if not check
            )

            return validation_summary

        except Exception as e:
            return {
                "overall_status": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "critical_issues": 1,
            }

    def get_configuration_errors(self) -> list[str]:
        """Get list of configuration errors.

        Returns:
            List of configuration error messages
        """
        errors = []

        try:
            # Test configuration loading
            test_config = BotConfig()
        except Exception as e:
            errors.append(f"Configuration loading failed: {e!s}")
            return errors

        # Additional validation checks
        validation = self.validate_configuration()

        if not validation.get("discord_configured", False):
            errors.append("Discord token is not properly configured")

        if not validation.get("audio_configured", False):
            errors.append("Audio folder is not properly configured")

        if not validation.get("ffmpeg_available", False):
            errors.append("FFmpeg is not available or not properly configured")

        if not validation.get("logging_properly_configured", False):
            errors.append("Logging configuration is incomplete")

        return errors

    # =============================================================================
    # Environment Detection Methods
    # =============================================================================

    def is_development_environment(self) -> bool:
        """Check if running in development environment.

        Returns:
            True if in development environment, False otherwise
        """
        # Use the config environment setting
        return self.config.ENVIRONMENT.lower() in ["dev", "development"]

    def is_production_environment(self) -> bool:
        """Check if running in production environment.

        Returns:
            True if in production environment, False otherwise
        """
        return not self.is_development_environment()

    def get_environment_name(self) -> str:
        """Get current environment name.

        Returns:
            Environment name (development/production)
        """
        return "development" if self.is_development_environment() else "production"

    # =============================================================================
    # Service Configuration Factory Methods
    # =============================================================================

    def create_audio_service_config(self) -> "AudioServiceConfig":
        """Create AudioServiceConfig from main configuration.

        Returns:
            AudioServiceConfig instance configured from BotConfig
        """
        from src.data.models import AudioServiceConfig

        return AudioServiceConfig(
            audio_base_folder=self.config.AUDIO_FOLDER,
            ffmpeg_path=str(self.config.FFMPEG_PATH),
            default_reciter=self.config.DEFAULT_RECITER,
            default_volume=1.0,
            connection_timeout=30.0,
            playback_timeout=300.0,
            max_retry_attempts=3,
            retry_delay=1.0,
            preload_metadata=True,
            cache_enabled=True,
            playback_buffer_size="2048k",
            enable_reconnection=True,
        )

    def create_state_service_config(self, project_root: Path) -> "StateServiceConfig":
        """Create StateServiceConfig from main configuration.

        Args:
            project_root: Project root directory path

        Returns:
            StateServiceConfig instance configured from BotConfig
        """
        from src.data.models import StateServiceConfig

        return StateServiceConfig(
            data_directory=project_root / "data",
            backup_directory=project_root / "backup",
            enable_backups=False,  # Disabled - using lightweight DataBackupService instead
            backup_interval_hours=self.config.BACKUP_INTERVAL_HOURS,
            max_backups=7,
            enable_integrity_checks=True,
            atomic_writes=True,
            compression_enabled=True,
            auto_recovery=True,
        )

    def create_cache_service_config(self) -> "CacheConfig":
        """Create CacheConfig from main configuration.

        Returns:
            CacheConfig instance configured from BotConfig
        """
        from src.core.cache_service import CacheConfig, CacheLevel, CacheStrategy

        return CacheConfig(
            strategy=CacheStrategy.LRU,
            level=CacheLevel.MEMORY,
            max_memory_mb=100,
            max_entries=1000,
            default_ttl_seconds=self.config.CACHE_TTL,
            enable_compression=True,
            compression_threshold_bytes=1024,
            enable_persistence=False,
            cleanup_interval_seconds=300,
        )

    def create_webhook_config(self) -> "WebhookConfig":
        """Create WebhookConfig from main configuration.

        Returns:
            WebhookConfig instance configured from BotConfig

        Raises:
            ConfigurationError: If webhook is enabled but URL is missing
        """
        from src.core.webhook_logger import WebhookConfig

        # Only create config if webhook logging is enabled
        if not self.config.USE_WEBHOOK_LOGGING:
            raise ConfigurationError("Webhook logging is disabled in configuration")

        if not self.config.DISCORD_WEBHOOK_URL:
            raise ConfigurationError(
                "Discord webhook URL is required for webhook logging"
            )

        return WebhookConfig(
            webhook_url=self.config.DISCORD_WEBHOOK_URL,
            owner_user_id=self.config.DEVELOPER_ID,
            max_logs_per_minute=min(
                self.config.RATE_LIMIT_PER_MINUTE, 15
            ),  # Be conservative with Discord
            max_embed_fields=25,
            max_field_length=1024,
            max_description_length=4096,
            request_timeout=30,
            retry_attempts=3,
            retry_delay=1.0,
            rate_limit_window=60,
            enable_pings=self.config.ENVIRONMENT
            == "production",  # Only ping in production
            timezone="US/Eastern",  # Matches user preference from memory
        )


# =============================================================================
# Global Configuration Service Instance
# =============================================================================


@lru_cache(maxsize=1)
def get_config_service() -> ConfigService:
    """Get the global configuration service instance.

    This function uses LRU cache to ensure singleton behavior
    and provides a convenient way to access configuration throughout
    the application.

    Returns:
        ConfigService instance
    """
    return ConfigService()


# Convenience function for direct config access
def get_config() -> BotConfig:
    """Get the current bot configuration.

    Returns:
        Current BotConfig instance
    """
    return get_config_service().config
