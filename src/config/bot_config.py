# =============================================================================
# QuranBot - Bot Configuration Module
# =============================================================================
# Modern configuration management for QuranBot using Pydantic BaseSettings.
# Handles environment variables, validation, and centralized bot settings.
# =============================================================================

from enum import Enum
import os
from pathlib import Path
import subprocess
from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.exceptions import ValidationError


class ReciterName(str, Enum):
    """Enumeration of available reciters."""

    SAAD_AL_GHAMDI = "Saad Al Ghamdi"
    ABDUL_BASIT = "Abdul Basit Abdul Samad"
    MAHER_AL_MUAIQLY = "Maher Al Muaiqly"
    MUHAMMAD_AL_LUHAIDAN = "Muhammad Al Luhaidan"
    RASHID_AL_AFASY = "Rashid Al Afasy"
    YASSER_AL_DOSARI = "Yasser Al Dosari"


class LogLevel(str, Enum):
    """Enumeration of logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class BotConfig(BaseSettings):
    """Type-safe configuration with validation using Pydantic BaseSettings.

    This class provides centralized configuration management with:
    - Type safety and validation
    - Environment variable loading
    - Default values and constraints
    - Comprehensive error messages
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

    DISCORD_WEBHOOK_URL: str | None = Field(
        None, description="Discord webhook URL for logging"
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
        """Validate Discord token format and length."""
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
        """Parse and validate admin user IDs from comma-separated string."""
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
        """Validate audio folder exists and is accessible."""
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
        """Validate FFmpeg executable exists and is functional."""
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

    @field_validator("DISCORD_WEBHOOK_URL")
    @classmethod
    def validate_webhook_url(cls, v: str | None) -> str | None:
        """Validate Discord webhook URL format."""
        if v is None:
            return v

        if not v.startswith("https://discord.com/api/webhooks/"):
            raise ValidationError(
                "DISCORD_WEBHOOK_URL", v, "Invalid Discord webhook URL format"
            )

        return v

    @model_validator(mode="after")
    def validate_logging_configuration(self) -> "BotConfig":
        """Validate logging configuration consistency."""
        if self.USE_WEBHOOK_LOGGING and not self.DISCORD_WEBHOOK_URL:
            raise ValidationError(
                "DISCORD_WEBHOOK_URL",
                self.DISCORD_WEBHOOK_URL,
                "Discord webhook URL is required when webhook logging is enabled",
            )

        return self

    @model_validator(mode="after")
    def validate_channel_ids_unique(self) -> "BotConfig":
        """Validate that channel IDs are unique where required."""
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

        Returns:
            List of admin user IDs
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

        Args:
            reciter: Reciter name, defaults to default_reciter

        Returns:
            Path to the reciter's audio folder
        """
        reciter = reciter or self.DEFAULT_RECITER
        return self.AUDIO_FOLDER / reciter.value

    def is_admin_user(self, user_id: int) -> bool:
        """Check if a user ID is in the admin list.

        Args:
            user_id: Discord user ID to check

        Returns:
            True if user is an admin, False otherwise
        """
        return user_id in self.admin_user_ids or user_id == self.DEVELOPER_ID

    def get_validation_summary(self) -> dict[str, Any]:
        """Get a summary of configuration validation status.

        Returns:
            Dictionary containing validation summary information
        """
        return {
            "discord_configured": bool(self.DISCORD_TOKEN),
            "audio_configured": self.AUDIO_FOLDER.exists(),
            "ffmpeg_available": self.FFMPEG_PATH.exists(),
            "logging_configured": bool(
                not self.USE_WEBHOOK_LOGGING or self.DISCORD_WEBHOOK_URL
            ),
            "admin_users_count": len(self.admin_user_ids),
            "reciter_folder_exists": self.get_reciter_audio_folder().exists(),
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
