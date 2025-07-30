# =============================================================================
# QuranBot - Configuration System (Single Source of Truth)
# =============================================================================
# Comprehensive configuration system with single source of truth.
# All configuration settings are centralized here with clear validation,
# type safety, and easy access patterns.
# =============================================================================

from enum import Enum
import os
from pathlib import Path
import subprocess
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

# Try to import BaseSettings from the correct location
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    try:
        from pydantic import BaseSettings

        # Create a simple SettingsConfigDict equivalent for older versions
        class SettingsConfigDict(dict):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

    except ImportError:
        # Fallback to BaseModel if BaseSettings is not available
        BaseSettings = BaseModel

        class SettingsConfigDict(dict):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)


class Environment(str, Enum):
    """Application environment types."""

    DEVELOPMENT = "development"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class CacheStrategy(str, Enum):
    """Cache eviction strategies"""

    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In, First Out
    TTL_ONLY = "ttl_only"  # Time-based only


class CacheLevel(str, Enum):
    """Cache storage levels"""

    MEMORY = "memory"  # In-memory cache
    DISK = "disk"  # Persistent disk cache
    HYBRID = "hybrid"  # Memory + disk


class ReciterName(str, Enum):
    """Available Quran reciters."""

    SAAD_AL_GHAMDI = "Saad Al Ghamdi"
    ABDUL_BASIT = "Abdul Basit Abdul Samad"
    MAHER_AL_MUAIQLY = "Maher Al Muaiqly"
    MUHAMMAD_AL_LUHAIDAN = "Muhammad Al Luhaidan"
    RASHID_AL_AFASY = "Rashid Al Afasy"
    YASSER_AL_DOSARI = "Yasser Al Dosari"
    MISHARY_AL_AFASY = "Mishary Al Afasy"
    AHMED_AL_AJMY = "Ahmed Al Ajmy"
    ALI_AL_HUDHAIFY = "Ali Al Hudhaify"
    SALAH_AL_BUDAIR = "Salah Al Budair"
    SAUD_AL_SHURAIM = "Saud Al Shuraim"
    ABDUR_RAHMAN_AL_SUDAIS = "Abdur Rahman Al Sudais"
    NASSER_AL_QATAMI = "Nasser Al Qatami"
    BANDAR_BALEELA = "Bandar Baleela"
    NABIL_AL_RIFAI = "Nabil Al Rifai"
    HANI_AL_RIFAI = "Hani Al Rifai"


class QuranBotConfig(BaseSettings):
    """
    Single Source of Truth Configuration for QuranBot.

    This is the definitive configuration class that contains all settings
    for the QuranBot application. It provides:

    - Type-safe configuration using Pydantic BaseSettings
    - Automatic environment variable loading from .env files
    - Comprehensive validation with clear error messages
    - Convenience properties and methods for common operations
    - Multi-channel webhook support for enhanced logging
    - Audio system configuration with path validation
    - Performance tuning and caching settings
    - Security configuration with rate limiting
    - OpenAI integration for Islamic AI features

    Configuration is loaded from:
    1. Environment variables
    2. config/.env file
    3. Default values defined in this class

    All settings are validated and type-safe using Pydantic.
    """

    # =============================================================================
    # CORE DISCORD SETTINGS (Required)
    # =============================================================================

    discord_token: str = Field(
        ..., description="Discord bot token", min_length=50, alias="DISCORD_TOKEN"
    )

    guild_id: int = Field(description="Discord guild/server ID", alias="GUILD_ID")

    connection_timeout: int = Field(
        default=30,
        description="Voice connection timeout in seconds",
        ge=5,
        le=120,
        alias="CONNECTION_TIMEOUT",
    )

    enable_reconnection: bool = Field(
        default=True,
        description="Enable automatic voice reconnection",
        alias="ENABLE_RECONNECTION",
    )

    target_channel_id: int = Field(
        ...,
        description="Voice channel ID for audio playback",
        gt=0,
        alias="TARGET_CHANNEL_ID",
    )

    # =============================================================================
    # OPTIONAL DISCORD SETTINGS
    # =============================================================================

    control_channel_id: int | None = Field(
        None,
        description="Channel ID for control commands",
        gt=0,
        alias="CONTROL_CHANNEL_ID",
    )

    panel_channel_id: int | None = Field(
        None, description="Channel ID for control panel", gt=0, alias="PANEL_CHANNEL_ID"
    )

    logs_channel_id: int | None = Field(
        None, description="Channel ID for bot logs", gt=0, alias="LOGS_CHANNEL_ID"
    )

    daily_verse_channel_id: int | None = Field(
        None,
        description="Channel ID for daily verses",
        gt=0,
        alias="DAILY_VERSE_CHANNEL_ID",
    )

    panel_access_role_id: int | None = Field(
        None, description="Role ID for panel access", gt=0, alias="PANEL_ACCESS_ROLE_ID"
    )

    # Additional channel aliases from .env file
    voice_channel_id: int | None = Field(
        None,
        description="Voice channel ID (alias for target_channel_id)",
        gt=0,
        alias="VOICE_CHANNEL_ID",
    )

    log_channel_id: int | None = Field(
        None,
        description="Log channel ID (alias for logs_channel_id)",
        gt=0,
        alias="LOG_CHANNEL_ID",
    )

    # =============================================================================
    # ADMIN SETTINGS
    # =============================================================================

    admin_user_ids: str = Field(
        default="", description="Comma-separated admin user IDs", alias="ADMIN_USER_ID"
    )

    developer_id: int | None = Field(
        None, description="Developer user ID", gt=0, alias="DEVELOPER_ID"
    )

    # =============================================================================
    # AUDIO SETTINGS
    # =============================================================================

    audio_folder: Path = Field(
        default=Path("audio"), description="Audio files directory", alias="AUDIO_FOLDER"
    )

    default_reciter: ReciterName = Field(
        default=ReciterName.SAAD_AL_GHAMDI,
        description="Default Quran reciter",
        alias="DEFAULT_RECITER",
    )

    ffmpeg_path: Path = Field(
        default=Path("/usr/bin/ffmpeg"),
        description="FFmpeg executable path",
        alias="FFMPEG_PATH",
    )

    audio_quality: str = Field(
        default="128k",
        description="Audio quality (e.g., 128k, 256k)",
        pattern=r"^\d+k$",
        alias="AUDIO_QUALITY",
    )

    default_shuffle: bool = Field(
        default=False, description="Enable shuffle by default", alias="DEFAULT_SHUFFLE"
    )

    default_loop: bool = Field(
        default=False, description="Enable loop by default", alias="DEFAULT_LOOP"
    )

    default_volume: float = Field(
        default=0.5,
        description="Default audio volume (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
        alias="DEFAULT_VOLUME",
    )

    preload_metadata: bool = Field(
        default=True,
        description="Preload audio metadata on startup",
        alias="PRELOAD_METADATA",
    )

    playback_buffer_size: int = Field(
        default=1024,
        description="Audio playback buffer size in bytes",
        ge=512,
        le=8192,
        alias="PLAYBACK_BUFFER_SIZE",
    )

    # =============================================================================
    # CACHE SETTINGS
    # =============================================================================

    cache_strategy: CacheStrategy = Field(
        default=CacheStrategy.LRU,
        description="Cache eviction strategy",
        alias="CACHE_STRATEGY",
    )

    cache_level: CacheLevel = Field(
        default=CacheLevel.HYBRID,
        description="Cache storage level",
        alias="CACHE_LEVEL",
    )

    cache_max_memory_mb: int = Field(
        default=100,
        description="Maximum cache memory usage in MB",
        ge=10,
        le=1000,
        alias="CACHE_MAX_MEMORY_MB",
    )

    cache_max_entries: int = Field(
        default=1000,
        description="Maximum number of cache entries",
        ge=100,
        le=10000,
        alias="CACHE_MAX_ENTRIES",
    )

    cache_default_ttl_seconds: int = Field(
        default=3600,
        description="Default cache TTL in seconds",
        ge=60,
        le=86400,
        alias="CACHE_DEFAULT_TTL_SECONDS",
    )

    cache_enable_compression: bool = Field(
        default=True,
        description="Enable cache compression",
        alias="CACHE_ENABLE_COMPRESSION",
    )

    cache_compression_threshold_bytes: int = Field(
        default=1024,
        description="Cache compression threshold in bytes",
        ge=512,
        le=10240,
        alias="CACHE_COMPRESSION_THRESHOLD_BYTES",
    )

    cache_disk_directory: Path = Field(
        default=Path("cache"),
        description="Cache disk storage directory",
        alias="CACHE_DISK_DIRECTORY",
    )

    cache_cleanup_interval_seconds: int = Field(
        default=300,
        description="Cache cleanup interval in seconds",
        ge=60,
        le=3600,
        alias="CACHE_CLEANUP_INTERVAL_SECONDS",
    )

    cache_enable_statistics: bool = Field(
        default=True,
        description="Enable cache statistics",
        alias="CACHE_ENABLE_STATISTICS",
    )

    cache_enable_persistence: bool = Field(
        default=True,
        description="Enable cache persistence",
        alias="CACHE_ENABLE_PERSISTENCE",
    )

    cache_enabled: bool = Field(
        default=True,
        description="Enable caching system",
        alias="CACHE_ENABLED",
    )

    # =============================================================================
    # LOGGING SETTINGS
    # =============================================================================

    log_level: LogLevel = Field(
        default=LogLevel.INFO, description="Application log level", alias="LOG_LEVEL"
    )

    use_webhook_logging: bool = Field(
        default=True,
        description="Use Discord webhook for logging",
        alias="USE_WEBHOOK_LOGGING",
    )

    # Multi-channel webhook URLs
    webhook_bot_status: str | None = Field(
        None,
        description="Webhook URL for bot status and health alerts",
        alias="WEBHOOK_BOT_STATUS",
    )

    webhook_quran_audio: str | None = Field(
        None,
        description="Webhook URL for Quran audio and playback events",
        alias="WEBHOOK_QURAN_AUDIO",
    )

    webhook_commands_panel: str | None = Field(
        None,
        description="Webhook URL for command usage and control panel interactions",
        alias="WEBHOOK_COMMANDS_PANEL",
    )

    webhook_user_activity: str | None = Field(
        None,
        description="Webhook URL for user engagement and Islamic activities",
        alias="WEBHOOK_USER_ACTIVITY",
    )

    webhook_data_analytics: str | None = Field(
        None,
        description="Webhook URL for database operations and analytics",
        alias="WEBHOOK_DATA_ANALYTICS",
    )

    webhook_errors_alerts: str | None = Field(
        None,
        description="Webhook URL for errors, warnings, and recovery events",
        alias="WEBHOOK_ERRORS_ALERTS",
    )

    webhook_daily_reports: str | None = Field(
        None,
        description="Webhook URL for daily reports and analytics summaries",
        alias="WEBHOOK_DAILY_REPORTS",
    )

    # Legacy single webhook support
    discord_webhook_url: str | None = Field(
        None,
        description="Legacy single Discord webhook URL",
        alias="DISCORD_WEBHOOK_URL",
    )

    # =============================================================================
    # PERFORMANCE SETTINGS
    # =============================================================================

    cache_ttl_seconds: int = Field(
        default=300,
        description="Cache time-to-live in seconds",
        ge=60,
        le=3600,
        alias="CACHE_TTL",
    )

    rate_limit_per_minute: int = Field(
        default=10,
        description="Commands per minute per user",
        ge=1,
        le=100,
        alias="RATE_LIMIT_PER_MINUTE",
    )

    max_concurrent_audio: int = Field(
        default=1,
        description="Max concurrent audio streams",
        ge=1,
        le=5,
        alias="MAX_CONCURRENT_AUDIO",
    )

    backup_interval_hours: int = Field(
        default=24,
        description="Backup interval in hours",
        ge=1,
        le=168,
        alias="BACKUP_INTERVAL_HOURS",
    )

    # =============================================================================
    # DATA SETTINGS
    # =============================================================================

    data_directory: Path = Field(
        default=Path("data"),
        description="Directory for data files",
        alias="DATA_DIRECTORY",
    )

    # =============================================================================
    # ENVIRONMENT SETTINGS
    # =============================================================================

    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Application environment",
        alias="ENVIRONMENT",
    )

    # =============================================================================
    # OPTIONAL INTEGRATIONS
    # =============================================================================

    openai_api_key: str | None = Field(
        None,
        description="OpenAI API key for Islamic AI",
        min_length=40,
        alias="OPENAI_API_KEY",
    )

    vps_host: str | None = Field(
        None, description="VPS host for deployment", alias="VPS_HOST"
    )

    # =============================================================================
    # VALIDATORS
    # =============================================================================

    @field_validator("discord_token")
    @classmethod
    def validate_discord_token(cls, v: str) -> str:
        """Validate Discord token format."""
        if not v or len(v) < 50:
            raise ValueError("Discord token must be at least 50 characters long")
        return v

    @field_validator("admin_user_ids", mode="before")
    @classmethod
    def parse_admin_user_ids(cls, v) -> str:
        """Parse admin user IDs from various formats."""
        if isinstance(v, str):
            if not v.strip():
                return ""
            # Validate that all parts are valid integers
            try:
                parts = [part.strip() for part in v.split(",") if part.strip()]
                for part in parts:
                    int(part)  # This will raise ValueError if invalid
                return v
            except ValueError as e:
                raise ValueError(f"Invalid user ID format: {e}")
        elif isinstance(v, list):
            try:
                return ",".join(str(int(uid)) for uid in v)
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid user ID in list: {e}")
        return str(v) if v else ""

    @field_validator("audio_folder")
    @classmethod
    def validate_audio_folder(cls, v: Path) -> Path:
        """Validate audio folder exists."""
        if not v.exists():
            raise ValueError(f"Audio folder does not exist: {v}")
        if not v.is_dir():
            raise ValueError(f"Audio folder path is not a directory: {v}")
        return v

    @field_validator("ffmpeg_path")
    @classmethod
    def validate_ffmpeg_path(cls, v: Path) -> Path:
        """Validate FFmpeg executable exists and is functional."""
        if not v.exists():
            raise ValueError(f"FFmpeg executable not found: {v}")

        if not os.access(v, os.X_OK):
            raise ValueError(f"FFmpeg executable is not executable: {v}")

        # Test FFmpeg functionality
        try:
            result = subprocess.run(
                [str(v), "-version"], capture_output=True, check=True, timeout=10
            )
            if b"ffmpeg version" not in result.stdout.lower():
                raise ValueError("FFmpeg executable does not appear to be valid")
        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
        ) as e:
            raise ValueError(f"FFmpeg executable test failed: {e}")

        return v

    @field_validator(
        "webhook_bot_status",
        "webhook_quran_audio",
        "webhook_commands_panel",
        "webhook_user_activity",
        "webhook_data_analytics",
        "webhook_errors_alerts",
        "webhook_daily_reports",
        "discord_webhook_url",
    )
    @classmethod
    def validate_webhook_url(cls, v: str | None) -> str | None:
        """Validate Discord webhook URL format."""
        if v is None:
            return v

        if not v.startswith("https://discord.com/api/webhooks/"):
            raise ValueError("Invalid Discord webhook URL format")

        return v

    @model_validator(mode="after")
    def validate_logging_config(self) -> "QuranBotConfig":
        """Validate logging configuration consistency."""
        if self.use_webhook_logging:
            # Check if we have at least one webhook URL
            webhook_urls = [
                self.webhook_bot_status,
                self.webhook_quran_audio,
                self.webhook_commands_panel,
                self.webhook_user_activity,
                self.webhook_data_analytics,
                self.webhook_errors_alerts,
                self.webhook_daily_reports,
                self.discord_webhook_url,
            ]

            if not any(url for url in webhook_urls):
                raise ValueError(
                    "At least one webhook URL is required when webhook logging is enabled"
                )

        return self

    # =============================================================================
    # CONVENIENCE PROPERTIES
    # =============================================================================

    @property
    def admin_user_id_list(self) -> list[int]:
        """Get admin user IDs as a list of integers."""
        if not self.admin_user_ids.strip():
            return []
        try:
            return [
                int(uid.strip())
                for uid in self.admin_user_ids.split(",")
                if uid.strip()
            ]
        except ValueError:
            return []

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == Environment.DEVELOPMENT

    @property
    def reciter_audio_folder(self) -> Path:
        """Get the audio folder for the default reciter."""
        return self.audio_folder / self.default_reciter

    @property
    def audio_base_folder(self) -> Path:
        """Get the audio base folder (alias for audio_folder)."""
        return self.audio_folder

    def is_admin_user(self, user_id: int) -> bool:
        """Check if a user ID is in the admin list."""
        return user_id in self.admin_user_id_list or user_id == self.developer_id

    def get_reciter_folder(self, reciter: ReciterName | None = None) -> Path:
        """Get the audio folder for a specific reciter."""
        reciter = reciter or self.default_reciter
        return self.audio_folder / reciter

    def get_available_reciters(self) -> list[ReciterName]:
        """Get list of available reciters."""
        return list(ReciterName)

    def get_reciter_names(self) -> list[str]:
        """Get list of reciter names as strings."""
        return [reciter.value for reciter in ReciterName]

    def is_valid_reciter(self, reciter_name: str) -> bool:
        """Check if a reciter name is valid."""
        return any(reciter.value == reciter_name for reciter in ReciterName)

    def get_reciter_by_name(self, reciter_name: str) -> ReciterName | None:
        """Get ReciterName enum by string name."""
        for reciter in ReciterName:
            if reciter.value == reciter_name:
                return reciter
        return None

    def get_webhook_url(self, event_type: str) -> str | None:
        """Get the appropriate webhook URL for a specific event type."""
        webhook_mapping = {
            "bot_status": self.webhook_bot_status,
            "quran_audio": self.webhook_quran_audio,
            "commands_panel": self.webhook_commands_panel,
            "user_activity": self.webhook_user_activity,
            "data_analytics": self.webhook_data_analytics,
            "errors_alerts": self.webhook_errors_alerts,
            "daily_reports": self.webhook_daily_reports,
        }

        # Return specific webhook URL or fallback to legacy
        return webhook_mapping.get(event_type) or self.discord_webhook_url

    def get_all_webhook_urls(self) -> dict[str, str | None]:
        """Get all webhook URLs as a dictionary."""
        return {
            "bot_status": self.webhook_bot_status,
            "quran_audio": self.webhook_quran_audio,
            "commands_panel": self.webhook_commands_panel,
            "user_activity": self.webhook_user_activity,
            "data_analytics": self.webhook_data_analytics,
            "errors_alerts": self.webhook_errors_alerts,
            "daily_reports": self.webhook_daily_reports,
            "legacy": self.discord_webhook_url,
        }

    def has_webhook_url(self, event_type: str) -> bool:
        """Check if a specific webhook URL is configured."""
        return bool(self.get_webhook_url(event_type))

    def get_configured_webhooks(self) -> list[str]:
        """Get list of configured webhook event types."""
        return [
            event_type
            for event_type in [
                "bot_status",
                "quran_audio",
                "commands_panel",
                "user_activity",
                "data_analytics",
                "errors_alerts",
                "daily_reports",
            ]
            if self.has_webhook_url(event_type)
        ]

    def get_validation_summary(self) -> dict[str, Any]:
        """Get a summary of configuration validation status."""
        has_webhook_urls = any(
            [
                self.webhook_bot_status,
                self.webhook_quran_audio,
                self.webhook_commands_panel,
                self.webhook_user_activity,
                self.webhook_data_analytics,
                self.webhook_errors_alerts,
                self.webhook_daily_reports,
                self.discord_webhook_url,
            ]
        )

        return {
            "discord_configured": bool(self.discord_token),
            "audio_configured": self.audio_folder.exists(),
            "ffmpeg_available": self.ffmpeg_path.exists(),
            "logging_configured": bool(
                not self.use_webhook_logging or has_webhook_urls
            ),
            "admin_users_count": len(self.admin_user_id_list),
            "reciter_folder_exists": self.reciter_audio_folder.exists(),
            "multi_channel_webhooks": bool(
                any(
                    [
                        self.webhook_bot_status,
                        self.webhook_quran_audio,
                        self.webhook_commands_panel,
                        self.webhook_user_activity,
                        self.webhook_data_analytics,
                        self.webhook_errors_alerts,
                        self.webhook_daily_reports,
                    ]
                )
            ),
            "configured_webhooks": self.get_configured_webhooks(),
            "available_reciters": len(self.get_available_reciters()),
            "environment": str(self.environment),
            "log_level": str(self.log_level),
        }

    def validate_audio_setup(self) -> dict[str, Any]:
        """Validate audio system configuration."""
        return {
            "audio_folder_exists": self.audio_folder.exists(),
            "audio_folder_is_directory": (
                self.audio_folder.is_dir() if self.audio_folder.exists() else False
            ),
            "ffmpeg_exists": self.ffmpeg_path.exists(),
            "ffmpeg_executable": (
                os.access(self.ffmpeg_path, os.X_OK)
                if self.ffmpeg_path.exists()
                else False
            ),
            "reciter_folder_exists": self.reciter_audio_folder.exists(),
            "default_reciter": str(self.default_reciter),
            "audio_quality": self.audio_quality,
        }

    def validate_discord_setup(self) -> dict[str, Any]:
        """Validate Discord configuration."""
        return {
            "token_configured": bool(self.discord_token),
            "token_length": len(self.discord_token) if self.discord_token else 0,
            "guild_id": self.guild_id,
            "target_channel_id": self.target_channel_id,
            "admin_users_count": len(self.admin_user_id_list),
            "developer_id": self.developer_id,
        }

    def validate_webhook_setup(self) -> dict[str, Any]:
        """Validate webhook configuration."""
        webhook_urls = self.get_all_webhook_urls()
        configured_webhooks = self.get_configured_webhooks()

        return {
            "webhook_logging_enabled": self.use_webhook_logging,
            "configured_webhooks": configured_webhooks,
            "total_webhooks": len(configured_webhooks),
            "webhook_urls": webhook_urls,
            "has_legacy_webhook": bool(self.discord_webhook_url),
        }

    # =============================================================================
    # PYDANTIC CONFIGURATION
    # =============================================================================

    model_config = SettingsConfigDict(
        env_file="config/.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


# =============================================================================
# CONFIGURATION INSTANCE
# =============================================================================

_config_instance: QuranBotConfig | None = None


def get_config() -> QuranBotConfig:
    """Get the global configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = QuranBotConfig()
    return _config_instance


def reload_config() -> QuranBotConfig:
    """Reload the configuration from environment variables."""
    global _config_instance
    _config_instance = QuranBotConfig()
    return _config_instance


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def is_admin(user_id: int) -> bool:
    """Check if a user ID is an admin."""
    return get_config().is_admin_user(user_id)


def get_discord_token() -> str:
    """Get Discord bot token."""
    return get_config().discord_token


def get_guild_id() -> int:
    """Get Discord guild ID."""
    return get_config().guild_id


def get_target_channel_id() -> int:
    """Get target voice channel ID."""
    return get_config().target_channel_id


def get_audio_folder() -> Path:
    """Get audio folder path."""
    return get_config().audio_folder


def get_ffmpeg_path() -> Path:
    """Get FFmpeg executable path."""
    return get_config().ffmpeg_path


def is_webhook_logging_enabled() -> bool:
    """Check if webhook logging is enabled."""
    return get_config().use_webhook_logging


def get_webhook_url(event_type: str = None) -> str | None:
    """Get webhook URL for specific event type."""
    return get_config().get_webhook_url(event_type)


def validate_config() -> dict[str, Any]:
    """Validate configuration and return summary."""
    config = get_config()
    return {
        "validation_summary": config.get_validation_summary(),
        "audio_setup": config.validate_audio_setup(),
        "discord_setup": config.validate_discord_setup(),
        "webhook_setup": config.validate_webhook_setup(),
    }


def print_config_summary():
    """Print configuration summary to console."""
    import json

    summary = validate_config()
    print("Configuration Summary:")
    print(json.dumps(summary, indent=2, default=str))
