# =============================================================================
# QuranBot - Configuration Package
# =============================================================================
# Contains configuration management and environment variable handling
#
# This package manages all bot configuration including:
# - Environment variable loading and validation
# - Default settings and fallback values
# - Configuration validation and error reporting
# - Runtime configuration updates and persistence
# =============================================================================

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Set

from dotenv import load_dotenv

from ..utils.tree_log import log_error_with_traceback, log_perfect_tree_section

# Load environment variables
env_path = Path(__file__).parent.parent.parent / "config" / ".env"
load_dotenv(env_path)


@dataclass
class BotConfig:
    """Main bot configuration settings"""

    # Discord credentials and IDs
    discord_token: str = field(default_factory=lambda: os.getenv("DISCORD_TOKEN", ""))
    guild_id: int = field(default_factory=lambda: int(os.getenv("GUILD_ID", "0")))
    developer_id: int = field(
        default_factory=lambda: int(os.getenv("DEVELOPER_ID", "0"))
    )

    # Channel configuration
    target_channel_id: int = field(
        default_factory=lambda: int(os.getenv("TARGET_CHANNEL_ID", "0"))
    )
    panel_channel_id: int = field(
        default_factory=lambda: int(os.getenv("PANEL_CHANNEL_ID", "0"))
    )
    daily_verse_channel_id: int = field(
        default_factory=lambda: int(os.getenv("DAILY_VERSE_CHANNEL_ID", "0"))
    )

    # Role configuration
    panel_access_role_id: int = field(
        default_factory=lambda: int(os.getenv("PANEL_ACCESS_ROLE_ID", "0"))
    )

    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate bot configuration.

        Returns:
            tuple[bool, list[str]]: (is_valid, error_messages)
        """
        errors = []

        # Check Discord token
        if not self.discord_token:
            errors.append("DISCORD_TOKEN is missing")
        elif len(self.discord_token) < 50:
            errors.append("DISCORD_TOKEN appears to be invalid (too short)")

        # Check Guild ID
        if self.guild_id == 0:
            errors.append("GUILD_ID is missing or invalid")

        # Check Channel IDs
        if self.target_channel_id == 0:
            errors.append("TARGET_CHANNEL_ID is missing or invalid")
        if self.panel_channel_id == 0:
            errors.append("PANEL_CHANNEL_ID is missing or invalid")
        if self.daily_verse_channel_id == 0:
            errors.append("DAILY_VERSE_CHANNEL_ID is missing or invalid")

        # Check Role ID
        if self.panel_access_role_id == 0:
            errors.append("PANEL_ACCESS_ROLE_ID is missing or invalid")

        return len(errors) == 0, errors


@dataclass
class AudioConfig:
    """Audio playback configuration settings"""

    # Audio paths and settings
    ffmpeg_path: str = field(default_factory=lambda: os.getenv("FFMPEG_PATH", "ffmpeg"))
    audio_folder: str = field(default="audio/Saad Al Ghamdi")

    # Playback defaults
    default_reciter: str = field(
        default_factory=lambda: os.getenv("DEFAULT_RECITER", "Saad Al Ghamdi")
    )
    default_shuffle: bool = field(
        default_factory=lambda: os.getenv("DEFAULT_SHUFFLE", "false").lower() == "true"
    )
    default_loop: bool = field(
        default_factory=lambda: os.getenv("DEFAULT_LOOP", "false").lower() == "true"
    )

    # Audio quality settings
    bitrate: int = field(default_factory=lambda: int(os.getenv("AUDIO_BITRATE", "128")))
    sample_rate: int = field(
        default_factory=lambda: int(os.getenv("AUDIO_SAMPLE_RATE", "48000"))
    )

    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate audio configuration.

        Returns:
            tuple[bool, list[str]]: (is_valid, error_messages)
        """
        errors = []

        # Check FFmpeg path
        if not Path(self.ffmpeg_path).exists() and not self.ffmpeg_path == "ffmpeg":
            errors.append(f"FFmpeg not found at: {self.ffmpeg_path}")

        # Check audio folder
        if not Path(self.audio_folder).exists():
            errors.append(f"Audio folder not found: {self.audio_folder}")

        # Validate bitrate
        if not 64 <= self.bitrate <= 384:
            errors.append(
                f"Invalid bitrate: {self.bitrate} (must be between 64 and 384)"
            )

        # Validate sample rate
        valid_sample_rates = {8000, 11025, 16000, 22050, 32000, 44100, 48000, 96000}
        if self.sample_rate not in valid_sample_rates:
            errors.append(f"Invalid sample rate: {self.sample_rate}")

        return len(errors) == 0, errors


@dataclass
class LoggingConfig:
    """Logging configuration settings"""

    # Log paths
    log_dir: Path = field(default_factory=lambda: Path("logs"))
    error_log: Path = field(init=False)
    debug_log: Path = field(init=False)

    # Log levels
    console_level: str = field(
        default_factory=lambda: os.getenv("CONSOLE_LOG_LEVEL", "INFO")
    )
    file_level: str = field(
        default_factory=lambda: os.getenv("FILE_LOG_LEVEL", "DEBUG")
    )

    # Retention settings
    max_log_size: int = field(
        default_factory=lambda: int(os.getenv("MAX_LOG_SIZE", "10485760"))
    )  # 10MB
    backup_count: int = field(
        default_factory=lambda: int(os.getenv("LOG_BACKUP_COUNT", "5"))
    )

    def __post_init__(self):
        """Initialize log file paths"""
        self.error_log = self.log_dir / "error.log"
        self.debug_log = self.log_dir / "debug.log"

    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate logging configuration.

        Returns:
            tuple[bool, list[str]]: (is_valid, error_messages)
        """
        errors = []

        # Create log directory if it doesn't exist
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Failed to create log directory: {e}")

        # Validate log levels
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.console_level not in valid_levels:
            errors.append(f"Invalid console log level: {self.console_level}")
        if self.file_level not in valid_levels:
            errors.append(f"Invalid file log level: {self.file_level}")

        # Validate retention settings
        if self.max_log_size < 1024:  # 1KB minimum
            errors.append(f"Invalid max log size: {self.max_log_size}")
        if not 1 <= self.backup_count <= 100:
            errors.append(f"Invalid backup count: {self.backup_count}")

        return len(errors) == 0, errors


class Config:
    """Central configuration manager"""

    def __init__(self):
        """Initialize configuration components"""
        self.bot = BotConfig()
        self.audio = AudioConfig()
        self.logging = LoggingConfig()

    def validate_all(self) -> tuple[bool, Dict[str, list[str]]]:
        """
        Validate all configuration components.

        Returns:
            tuple[bool, Dict[str, list[str]]]: (is_valid, {component: error_messages})
        """
        errors = {}

        # Validate bot config
        bot_valid, bot_errors = self.bot.validate()
        if not bot_valid:
            errors["bot"] = bot_errors

        # Validate audio config
        audio_valid, audio_errors = self.audio.validate()
        if not audio_valid:
            errors["audio"] = audio_errors

        # Validate logging config
        logging_valid, logging_errors = self.logging.validate()
        if not logging_valid:
            errors["logging"] = logging_errors

        # Log validation results
        if errors:
            log_perfect_tree_section(
                "Configuration Validation Failed",
                [(component, "\n".join(msgs)) for component, msgs in errors.items()],
                "❌",
            )
        else:
            log_perfect_tree_section(
                "Configuration Validation Successful",
                [("bot", "✅ Valid"), ("audio", "✅ Valid"), ("logging", "✅ Valid")],
                "✅",
            )

        return len(errors) == 0, errors


# Create global configuration instance
config = Config()

# Export configuration classes and instance
__all__ = [
    "BotConfig",
    "AudioConfig",
    "LoggingConfig",
    "Config",
    "config",
]
