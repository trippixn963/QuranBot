"""QuranBot - Bot Configuration Module.

Modern configuration management for QuranBot using Pydantic BaseSettings.
Handles environment variables, validation, and centralized bot settings.

This module provides comprehensive configuration management for QuranBot with:
- Type-safe configuration using Pydantic BaseSettings
- Automatic environment variable loading and validation
- Comprehensive field validation with custom validators
- Support for multiple webhook channels for enhanced logging
- Audio and performance configuration management
- Security and rate limiting settings
- OpenAI integration for Islamic AI Assistant

Classes:
    ReciterName: Enumeration of available Quran reciters
    LogLevel: Enumeration of logging levels
    BotConfig: Main configuration class with comprehensive settings
    
Features:
    - Environment file support (.env)
    - Discord API integration settings
    - Multi-channel webhook configuration
    - Audio system configuration with FFmpeg validation
    - Performance and caching settings
    - Security configuration with rate limiting
    - Comprehensive validation with detailed error messages
"""

from enum import Enum
import os
from pathlib import Path
import subprocess
from typing import Any, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.exceptions import ValidationError


class ReciterName(str, Enum):
    """Enumeration of available Quran reciters.
    
    Defines the available reciters for Quran audio playback with their
    exact folder names as used in the audio directory structure.
    
    Attributes:
        SAAD_AL_GHAMDI: Default reciter with clear pronunciation
        ABDUL_BASIT: Classical reciter with traditional style
        MAHER_AL_MUAIQLY: Popular contemporary reciter
        MUHAMMAD_AL_LUHAIDAN: Imam of Masjid an-Nabawi
        RASHID_AL_AFASY: Well-known Kuwaiti reciter
        YASSER_AL_DOSARI: Saudi reciter with melodious voice
    """

    SAAD_AL_GHAMDI = "Saad Al Ghamdi"
    ABDUL_BASIT = "Abdul Basit Abdul Samad"
    MAHER_AL_MUAIQLY = "Maher Al Muaiqly"
    MUHAMMAD_AL_LUHAIDAN = "Muhammad Al Luhaidan"
    RASHID_AL_AFASY = "Rashid Al Afasy"
    YASSER_AL_DOSARI = "Yasser Al Dosari"


class LogLevel(str, Enum):
    """Enumeration of logging levels.
    
    Standard logging levels for controlling log output verbosity.
    
    Attributes:
        DEBUG: Detailed diagnostic information
        INFO: General informational messages
        WARNING: Warning messages for potentially harmful situations
        ERROR: Error messages for problems that don't stop execution
        CRITICAL: Critical errors that may cause the application to stop
    """

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class BotConfig(BaseSettings):
    """Type-safe configuration with validation using Pydantic BaseSettings.

    This class provides centralized configuration management for QuranBot with
    comprehensive settings for all bot systems and features.

    The configuration system supports:
    - Automatic environment variable loading from .env files
    - Type safety with Pydantic validation
    - Custom validators for complex validation logic
    - Multi-channel webhook configuration for enhanced logging
    - Audio system configuration with path validation
    - Performance tuning and caching settings
    - Security configuration with rate limiting
    - OpenAI integration for Islamic AI features
    
    Configuration Sections:
        Discord: Bot token, guild/channel IDs, and Discord integration
        Environment: Application environment and deployment settings
        User: Admin user configuration and permissions
        Audio: Audio playback configuration and reciter settings
        Performance: Caching, concurrency, and optimization settings
        Security: Rate limiting and access control
        Logging: Multi-channel webhook configuration and log levels
        VPS: Deployment and hosting configuration
        OpenAI: Islamic AI Assistant integration
    """

    # =============================================================================
    # Discord Configuration
    # =============================================================================
    DISCORD_TOKEN: str = Field(..., description="Discord bot token for authentication")

    GUILD_ID: int = Field(
        ..., description="Discord server (guild) ID where the bot operates", gt=0
    )

    TARGET_CHANNEL_ID: int = Field(
        ..., description="Primary voice channel ID for audio playback", gt=0
    )

    CONTROL_CHANNEL_ID: int | None = Field(
        None, description="Channel ID for bot control commands", gt=0
    )

    VOICE_CHANNEL_ID: int | None = Field(
        None, description="Voice channel ID (alias for TARGET_CHANNEL_ID)", gt=0
    )

    LOG_CHANNEL_ID: int | None = Field(
        None, description="Channel ID for bot logging (alias for LOGS_CHANNEL_ID)", gt=0
    )

    PANEL_CHANNEL_ID: int | None = Field(
        None, description="Channel ID for bot control panel", gt=0
    )

    LOGS_CHANNEL_ID: int | None = Field(
        None, description="Channel ID for bot logging", gt=0
    )

    DAILY_VERSE_CHANNEL_ID: int | None = Field(
        None, description="Channel ID for daily verse posting", gt=0
    )

    PANEL_ACCESS_ROLE_ID: int | None = Field(
        None, description="Role ID required for panel access", gt=0
    )

    # =============================================================================
    # Environment Configuration
    # =============================================================================
    ENVIRONMENT: str = Field(
        default="development",
        description="Application environment (development/production)",
    )

    # =============================================================================
    # User Configuration
    # =============================================================================
    ADMIN_USER_ID: str = Field(
        default="", description="Comma-separated list of admin user IDs"
    )

    DEVELOPER_ID: int | None = Field(
        None, description="Developer user ID for special permissions", gt=0
    )

    # =============================================================================
    # Audio Configuration
    # =============================================================================
    AUDIO_FOLDER: Path = Field(
        default=Path("audio"), description="Base directory containing audio files"
    )

    DEFAULT_RECITER: ReciterName = Field(
        default=ReciterName.SAAD_AL_GHAMDI,
        description="Default reciter for audio playback",
    )

    FFMPEG_PATH: Path = Field(
        default=Path("/usr/bin/ffmpeg"), description="Path to FFmpeg executable"
    )

    AUDIO_QUALITY: str = Field(
        default="128k",
        description="Audio quality setting for playback",
        pattern=r"^\d+k$",
    )

    DEFAULT_SHUFFLE: bool = Field(
        default=False, description="Default shuffle mode setting"
    )

    DEFAULT_LOOP: bool = Field(default=False, description="Default loop mode setting")

    # =============================================================================
    # Performance Configuration
    # =============================================================================
    CACHE_TTL: int = Field(
        default=300, description="Cache time-to-live in seconds", ge=60, le=3600
    )

    MAX_CONCURRENT_AUDIO: int = Field(
        default=1, description="Maximum concurrent audio streams", ge=1, le=5
    )

    BACKUP_INTERVAL_HOURS: int = Field(
        default=24,
        description="Backup interval in hours",
        ge=1,
        le=168,  # Max 1 week
    )

    # =============================================================================
    # Security Configuration
    # =============================================================================
    RATE_LIMIT_PER_MINUTE: int = Field(
        default=10,
        description="Rate limit for commands per minute per user",
        ge=1,
        le=100,
    )

    # =============================================================================
    # Logging Configuration
    # =============================================================================
    LOG_LEVEL: LogLevel = Field(
        default=LogLevel.INFO, description="Logging level for the application"
    )

    USE_WEBHOOK_LOGGING: bool = Field(
        default=True, description="Whether to use webhook-based Discord logging"
    )

    # Multi-channel webhook URLs for enhanced logging
    WEBHOOK_BOT_STATUS: str | None = Field(
        None, description="Webhook URL for bot status and health alerts"
    )
    
    WEBHOOK_QURAN_AUDIO: str | None = Field(
        None, description="Webhook URL for Quran audio and playback events"
    )
    
    WEBHOOK_COMMANDS_PANEL: str | None = Field(
        None, description="Webhook URL for command usage and control panel interactions"
    )
    
    WEBHOOK_USER_ACTIVITY: str | None = Field(
        None, description="Webhook URL for user engagement and Islamic activities"
    )
    
    WEBHOOK_DATA_ANALYTICS: str | None = Field(
        None, description="Webhook URL for database operations and analytics"
    )
    
    WEBHOOK_ERRORS_ALERTS: str | None = Field(
        None, description="Webhook URL for errors, warnings, and recovery events"
    )
    
    WEBHOOK_DAILY_REPORTS: str | None = Field(
        None, description="Webhook URL for daily reports and analytics summaries"
    )
    
    # Legacy single webhook support (for backward compatibility)
    DISCORD_WEBHOOK_URL: str | None = Field(
        None, description="Legacy single Discord webhook URL (use specific channel webhooks instead)"
    )

    # =============================================================================
    # VPS Configuration
    # =============================================================================
    VPS_HOST: str | None = Field(None, description="VPS host for deployment")

    # =============================================================================
    # OpenAI Configuration (for Islamic AI Assistant)
    # =============================================================================
    OPENAI_API_KEY: str | None = Field(
        None, 
        description="OpenAI API key for Islamic AI Assistant (GPT-3.5 Turbo)",
        min_length=50  # OpenAI API keys are typically 51 characters
    )

    # =============================================================================
    # Validators
    # =============================================================================

    @field_validator("DISCORD_TOKEN")
    @classmethod
    def validate_discord_token(cls, v: str) -> str:
        """Validate Discord token format and length.
        
        Ensures the Discord token is properly formatted and meets minimum
        length requirements for valid bot tokens.
        
        Args:
            v: Discord token string
            
        Returns:
            str: Validated Discord token
            
        Raises:
            ValidationError: If token is empty or too short
        """
        if not v:
            raise ValidationError("DISCORD_TOKEN", v, "Discord token cannot be empty")

        # Remove common prefixes
        token_to_check = v
        if v.startswith("Bot "):
            token_to_check = v[4:]
        elif v.startswith("Bearer "):
            token_to_check = v[7:]

        if len(token_to_check) < 59:
            raise ValidationError(
                "DISCORD_TOKEN",
                v,
                "Discord token appears to be too short (minimum 59 characters)",
            )

        return v

    @field_validator("ADMIN_USER_ID", mode="before")
    @classmethod
    def parse_admin_user_ids(cls, v) -> str:
        """Parse and validate admin user IDs from comma-separated string.
        
        Handles various input formats including comma-separated strings,
        lists, and individual values, ensuring all user IDs are valid integers.
        
        Args:
            v: Admin user IDs in various formats
            
        Returns:
            str: Comma-separated string of validated user IDs
            
        Raises:
            ValidationError: If any user ID is not a valid integer
        """
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
                raise ValidationError(
                    "ADMIN_USER_ID", v, f"Invalid user ID format: {e}"
                )
        elif isinstance(v, list):
            try:
                return ",".join(str(int(uid)) for uid in v)
            except (ValueError, TypeError) as e:
                raise ValidationError(
                    "ADMIN_USER_ID", v, f"Invalid user ID in list: {e}"
                )
        return str(v) if v else ""

    @field_validator("AUDIO_FOLDER")
    @classmethod
    def validate_audio_folder(cls, v: Path) -> Path:
        """Validate audio folder exists and contains audio files.
        
        Ensures the audio folder exists, is a directory, and contains at least
        one audio file in supported formats (mp3, wav, ogg, m4a).
        
        Args:
            v: Path to audio folder
            
        Returns:
            Path: Validated audio folder path
            
        Raises:
            ValidationError: If folder doesn't exist, isn't a directory, or contains no audio files
        """
        if not v.exists():
            raise ValidationError(
                "AUDIO_FOLDER", str(v), f"Audio folder does not exist: {v}"
            )

        if not v.is_dir():
            raise ValidationError(
                "AUDIO_FOLDER", str(v), f"Audio folder path is not a directory: {v}"
            )

        # Check for at least one audio file
        audio_extensions = ["*.mp3", "*.wav", "*.ogg", "*.m4a"]
        has_audio_files = any(list(v.rglob(pattern)) for pattern in audio_extensions)

        if not has_audio_files:
            raise ValidationError(
                "AUDIO_FOLDER", str(v), f"No audio files found in folder: {v}"
            )

        return v

    @field_validator("FFMPEG_PATH")
    @classmethod
    def validate_ffmpeg_path(cls, v: Path) -> Path:
        """Validate FFmpeg executable exists and is functional.
        
        Performs comprehensive validation of the FFmpeg executable including:
        - File existence and execute permissions
        - Functional test by running 'ffmpeg -version'
        - Response validation to ensure it's actually FFmpeg
        
        Args:
            v: Path to FFmpeg executable
            
        Returns:
            Path: Validated FFmpeg executable path
            
        Raises:
            ValidationError: If FFmpeg is not found, not executable, or not functional
        """
        if not v.exists():
            raise ValidationError(
                "FFMPEG_PATH", str(v), f"FFmpeg executable not found: {v}"
            )

        if not os.access(v, os.X_OK):
            raise ValidationError(
                "FFMPEG_PATH", str(v), f"FFmpeg executable is not executable: {v}"
            )

        # Test FFmpeg functionality
        try:
            result = subprocess.run(
                [str(v), "-version"], capture_output=True, check=True, timeout=10
            )
            if b"ffmpeg version" not in result.stdout.lower():
                raise ValidationError(
                    "FFMPEG_PATH",
                    str(v),
                    "FFmpeg executable does not appear to be valid",
                )
        except subprocess.TimeoutExpired:
            raise ValidationError(
                "FFMPEG_PATH", str(v), "FFmpeg executable is not responding"
            )
        except subprocess.CalledProcessError as e:
            raise ValidationError(
                "FFMPEG_PATH",
                str(v),
                f"FFmpeg executable returned error: {e.returncode}",
            )
        except FileNotFoundError:
            raise ValidationError(
                "FFMPEG_PATH", str(v), "FFmpeg executable not found or not accessible"
            )

        return v

    @field_validator(
        "WEBHOOK_BOT_STATUS",
        "WEBHOOK_QURAN_AUDIO", 
        "WEBHOOK_COMMANDS_PANEL",
        "WEBHOOK_USER_ACTIVITY",
        "WEBHOOK_DATA_ANALYTICS",
        "WEBHOOK_ERRORS_ALERTS",
        "WEBHOOK_DAILY_REPORTS",
        "DISCORD_WEBHOOK_URL"
    )
    @classmethod
    def validate_webhook_url(cls, v: str | None) -> str | None:
        """Validate Discord webhook URL format for all webhook fields.
        
        Ensures webhook URLs follow the correct Discord webhook format.
        Applies to all webhook configuration fields.
        
        Args:
            v: Webhook URL string or None
            
        Returns:
            str | None: Validated webhook URL or None if not provided
            
        Raises:
            ValidationError: If URL format is invalid
        """
        if v is None:
            return v

        if not v.startswith("https://discord.com/api/webhooks/"):
            raise ValidationError(
                "webhook_url", v, "Invalid Discord webhook URL format"
            )

        return v

    @model_validator(mode="after")
    def validate_logging_configuration(self) -> "BotConfig":
        """Validate logging configuration consistency.
        
        Ensures that if webhook logging is enabled, at least one webhook URL
        is configured (either specific channel webhook or legacy single webhook).
        
        Returns:
            BotConfig: Validated configuration instance
            
        Raises:
            ValidationError: If webhook logging is enabled but no webhook URLs are configured
        """
        if self.USE_WEBHOOK_LOGGING:
            # Check if we have at least one webhook URL (new multi-channel or legacy single)
            webhook_urls = [
                self.WEBHOOK_BOT_STATUS,
                self.WEBHOOK_QURAN_AUDIO,
                self.WEBHOOK_COMMANDS_PANEL,
                self.WEBHOOK_USER_ACTIVITY,
                self.WEBHOOK_DATA_ANALYTICS,
                self.WEBHOOK_ERRORS_ALERTS,
                self.WEBHOOK_DAILY_REPORTS,
                self.DISCORD_WEBHOOK_URL  # Legacy fallback
            ]
            
            if not any(url for url in webhook_urls):
                raise ValidationError(
                    "webhook_configuration",
                    None,
                    "At least one webhook URL is required when webhook logging is enabled",
                )

        return self

    @model_validator(mode="after")
    def validate_channel_ids_unique(self) -> "BotConfig":
        """Validate that channel IDs are unique where required.
        
        Ensures that different bot functions don't use the same Discord channel,
        which could cause conflicts or confusion.
        
        Returns:
            BotConfig: Validated configuration instance
            
        Raises:
            ValidationError: If any channel ID is used multiple times
        """
        channel_ids = []
        channel_values = [
            ("TARGET_CHANNEL_ID", self.TARGET_CHANNEL_ID),
            ("PANEL_CHANNEL_ID", self.PANEL_CHANNEL_ID),
            ("LOGS_CHANNEL_ID", self.LOGS_CHANNEL_ID),
            ("DAILY_VERSE_CHANNEL_ID", self.DAILY_VERSE_CHANNEL_ID),
        ]

        for field_name, channel_id in channel_values:
            if channel_id is not None:
                if channel_id in channel_ids:
                    raise ValidationError(
                        field_name,
                        channel_id,
                        f"Channel ID {channel_id} is used multiple times",
                    )
                channel_ids.append(channel_id)

        return self

    # =============================================================================
    # Configuration Methods
    # =============================================================================

    @property
    def admin_user_ids(self) -> list[int]:
        """Parse admin user IDs from comma-separated string.

        Converts the comma-separated admin user ID string into a list of integers.
        Returns empty list if no admin users are configured or parsing fails.

        Returns:
            list[int]: List of admin user IDs
        """
        if not self.ADMIN_USER_ID.strip():
            return []
        try:
            return [
                int(uid.strip()) for uid in self.ADMIN_USER_ID.split(",") if uid.strip()
            ]
        except ValueError:
            return []

    def get_reciter_audio_folder(self, reciter: ReciterName | None = None) -> Path:
        """Get the audio folder path for a specific reciter.

        Constructs the full path to a reciter's audio folder based on the
        base audio folder and reciter name.

        Args:
            reciter: Reciter name, defaults to DEFAULT_RECITER if None

        Returns:
            Path: Full path to the reciter's audio folder
        """
        reciter = reciter or self.DEFAULT_RECITER
        return self.AUDIO_FOLDER / reciter.value

    def is_admin_user(self, user_id: int) -> bool:
        """Check if a user ID is in the admin list.

        Checks both the admin user list and the developer ID for admin privileges.

        Args:
            user_id: Discord user ID to check

        Returns:
            bool: True if user has admin privileges, False otherwise
        """
        return user_id in self.admin_user_ids or user_id == self.DEVELOPER_ID

    def get_webhook_url(self, event_type: str) -> str | None:
        """Get the appropriate webhook URL for a specific event type.
        
        Maps event types to their corresponding webhook URLs with fallback
        to the legacy single webhook URL for backward compatibility.
        
        Args:
            event_type: Type of event. Valid types:
                - 'bot_status': Bot lifecycle and health events
                - 'quran_audio': Audio playback and recitation events  
                - 'commands_panel': Command usage and control panel interactions
                - 'user_activity': User engagement and Islamic activities
                - 'data_analytics': Database operations and analytics
                - 'errors_alerts': Errors, warnings, and recovery events
                - 'daily_reports': Daily analytics and summary reports
                       
        Returns:
            str | None: Webhook URL for the event type, or fallback to legacy URL, or None
        """
        webhook_mapping = {
            "bot_status": self.WEBHOOK_BOT_STATUS,
            "quran_audio": self.WEBHOOK_QURAN_AUDIO,
            "commands_panel": self.WEBHOOK_COMMANDS_PANEL,
            "user_activity": self.WEBHOOK_USER_ACTIVITY,
            "data_analytics": self.WEBHOOK_DATA_ANALYTICS,
            "errors_alerts": self.WEBHOOK_ERRORS_ALERTS,
            "daily_reports": self.WEBHOOK_DAILY_REPORTS,
        }
        
        # Return specific webhook URL or fallback to legacy
        return webhook_mapping.get(event_type) or self.DISCORD_WEBHOOK_URL

    def get_validation_summary(self) -> dict[str, Any]:
        """Get a summary of configuration validation status.

        Provides a comprehensive overview of the configuration status including
        which components are properly configured and ready for use.

        Returns:
            dict[str, Any]: Dictionary containing validation summary with keys:
                - discord_configured: Whether Discord token is set
                - audio_configured: Whether audio folder exists
                - ffmpeg_available: Whether FFmpeg executable exists
                - logging_configured: Whether logging is properly configured
                - admin_users_count: Number of configured admin users
                - reciter_folder_exists: Whether default reciter folder exists
                - multi_channel_webhooks: Whether multi-channel webhooks are configured
        """
        # Check if we have any webhook URLs configured
        has_webhook_urls = any([
            self.WEBHOOK_BOT_STATUS,
            self.WEBHOOK_QURAN_AUDIO,
            self.WEBHOOK_COMMANDS_PANEL,
            self.WEBHOOK_USER_ACTIVITY,
            self.WEBHOOK_DATA_ANALYTICS,
            self.WEBHOOK_ERRORS_ALERTS,
            self.WEBHOOK_DAILY_REPORTS,
            self.DISCORD_WEBHOOK_URL
        ])
        
        return {
            "discord_configured": bool(self.DISCORD_TOKEN),
            "audio_configured": self.AUDIO_FOLDER.exists(),
            "ffmpeg_available": self.FFMPEG_PATH.exists(),
            "logging_configured": bool(
                not self.USE_WEBHOOK_LOGGING or has_webhook_urls
            ),
            "admin_users_count": len(self.admin_user_ids),
            "reciter_folder_exists": self.get_reciter_audio_folder().exists(),
            "multi_channel_webhooks": bool(any([
                self.WEBHOOK_BOT_STATUS,
                self.WEBHOOK_QURAN_AUDIO,
                self.WEBHOOK_COMMANDS_PANEL,
                self.WEBHOOK_USER_ACTIVITY,
                self.WEBHOOK_DATA_ANALYTICS,
                self.WEBHOOK_ERRORS_ALERTS,
                self.WEBHOOK_DAILY_REPORTS
            ])),
        }

    # =============================================================================
    # Pydantic Configuration
    # =============================================================================

    model_config = SettingsConfigDict(
        env_file="config/.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",  # Prevent extra fields
    )
