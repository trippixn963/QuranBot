# =============================================================================
# QuranBot - Configuration Management
# =============================================================================
# Type-safe configuration using Pydantic v2 for Python 3.13 compatibility.
# All settings are validated and environment-aware with comprehensive logging.
# =============================================================================

from datetime import datetime
from enum import Enum
import os
from pathlib import Path
import shutil
import time
from typing import Any

from dotenv import load_dotenv
from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings

from .timezone import APP_TIMEZONE


# Configuration loading timing and logging
_config_load_start = time.time()
_env_load_result = load_dotenv()
_config_load_time = time.time() - _config_load_start

# Store configuration loading metadata
_config_metadata = {
    "env_file_loaded": _env_load_result,
    "load_time_ms": f"{_config_load_time * 1000:.1f}",
    "env_file_path": (
        str(Path(".env").absolute()) if Path(".env").exists() else "Not found"
    ),
    "total_env_vars": len(os.environ),
    "bot_env_vars": len(
        [
            k
            for k in os.environ.keys()
            if k.startswith(
                (
                    "DISCORD_",
                    "GUILD_",
                    "VOICE_",
                    "PANEL_",
                    "DEVELOPER_",
                    "AUDIO_",
                    "FFMPEG_",
                    "OPENAI_",
                    "ENVIRONMENT",
                    "LOG_",
                )
            )
        ]
    ),
    "load_timestamp": datetime.now(APP_TIMEZONE).isoformat(),
}


# =============================================================================
# Configuration Enums
# =============================================================================


class Environment(str, Enum):
    """Application environment types."""

    DEVELOPMENT = "development"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Structured logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ReciterName(str, Enum):
    """Available Quran reciters - mapped to audio folder names."""

    SAAD_AL_GHAMDI = "Saad Al Ghamdi"
    ABDUL_BASIT = "Abdul Basit Abdul Samad"
    MAHER_AL_MUAIQLY = "Maher Al Muaiqly"
    MUHAMMAD_AL_LUHAIDAN = "Muhammad Al Luhaidan"
    RASHID_AL_AFASY = "Rashid Al Afasy"
    YASSER_AL_DOSARI = "Yasser Al Dosari"


# =============================================================================
# Main Configuration Class
# =============================================================================


class QuranBotConfig(BaseSettings):
    """
    Single Source of Truth Configuration for QuranBot.

    Designed for single-server deployment with production-ready defaults.
    All settings are validated and type-safe using Pydantic v1.

    Configuration Priority:
    1. Environment variables (.env file)
    2. Default values defined here

    This bot is designed for ONE Discord server only.
    """

    # =========================================================================
    # Discord Server Configuration (REQUIRED)
    # =========================================================================

    discord_token: str = Field(
        ...,
        description="Discord bot token from Developer Portal",
        json_schema_extra={"env": "DISCORD_TOKEN"},
    )

    guild_id: int = Field(
        ...,
        description="Your Discord server (guild) ID",
        gt=0,
        json_schema_extra={"env": "GUILD_ID"},
    )

    voice_channel_id: int = Field(
        ...,
        description="Voice channel ID for Quran audio playback",
        gt=0,
        json_schema_extra={"env": "VOICE_CHANNEL_ID"},
    )

    panel_channel_id: int = Field(
        ...,
        description="Channel ID for control panel display",
        gt=0,
        json_schema_extra={"env": "PANEL_CHANNEL_ID"},
    )


    # =========================================================================
    # Optional Discord Channels
    # =========================================================================

    daily_verse_channel_id: int | None = Field(
        None,
        description="Channel ID for daily verse messages",
        gt=0,
        json_schema_extra={"env": "DAILY_VERSE_CHANNEL_ID"},
    )

    # =========================================================================
    # Administration
    # =========================================================================

    developer_id: int | None = Field(
        None,
        description="Developer Discord user ID",
        gt=0,
        json_schema_extra={"env": "DEVELOPER_ID"},
    )


    # =========================================================================
    # Audio System Configuration
    # =========================================================================

    default_reciter: ReciterName = Field(
        default=ReciterName.SAAD_AL_GHAMDI,
        description="Default Quran reciter for audio playback",
        json_schema_extra={"env": "DEFAULT_RECITER"},
    )

    default_volume: float = Field(
        default=1.0,
        description="Default audio volume (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
        json_schema_extra={"env": "DEFAULT_VOLUME"},
    )

    audio_quality: str = Field(
        default="128k",
        description="FFmpeg audio quality setting",
        pattern=r"^\d+k$",
        json_schema_extra={"env": "AUDIO_QUALITY"},
    )

    # =========================================================================
    # System Paths (Auto-detected with fallbacks)
    # =========================================================================

    audio_folder: Path = Field(
        default=Path("audio"),
        description="Audio files directory",
        json_schema_extra={"env": "AUDIO_FOLDER"},
    )

    data_folder: Path = Field(
        default=Path("data"),
        description="Data storage directory",
        json_schema_extra={"env": "DATA_FOLDER"},
    )

    logs_folder: Path = Field(
        default=Path("logs"),
        description="Logs storage directory",
        json_schema_extra={"env": "LOGS_FOLDER"},
    )

    ffmpeg_path: Path = Field(
        default=Path("ffmpeg"),  # Will auto-detect actual path
        description="FFmpeg executable path (auto-detected)",
        json_schema_extra={"env": "FFMPEG_PATH"},
    )

    # =========================================================================
    # Performance & Reliability (24/7 Operation)
    # =========================================================================

    connection_timeout: int = Field(
        default=30,
        description="Voice connection timeout in seconds",
        ge=5,
        le=120,
        json_schema_extra={"env": "CONNECTION_TIMEOUT"},
    )

    reconnect_attempts: int = Field(
        default=5,
        description="Maximum reconnection attempts",
        ge=1,
        le=10,
        json_schema_extra={"env": "RECONNECT_ATTEMPTS"},
    )

    playback_buffer_size: int = Field(
        default=1024,
        description="Audio playback buffer size in bytes",
        ge=512,
        le=8192,
        json_schema_extra={"env": "PLAYBACK_BUFFER_SIZE"},
    )

    health_check_interval: int = Field(
        default=60,
        description="Health check interval in seconds",
        ge=30,
        le=300,
        json_schema_extra={"env": "HEALTH_CHECK_INTERVAL"},
    )

    startup_timeout: float = Field(
        default=30.0,
        description="Bot startup timeout in seconds",
        ge=10.0,
        le=120.0,
        json_schema_extra={"env": "STARTUP_TIMEOUT"},
    )

    shutdown_timeout: float = Field(
        default=10.0,
        description="Graceful shutdown timeout in seconds",
        ge=5.0,
        le=30.0,
        json_schema_extra={"env": "SHUTDOWN_TIMEOUT"},
    )

    retry_base_delay: float = Field(
        default=1.0,
        description="Base delay for retry logic in seconds",
        ge=0.5,
        le=5.0,
        json_schema_extra={"env": "RETRY_BASE_DELAY"},
    )

    retry_max_delay: float = Field(
        default=30.0,
        description="Maximum delay for retry logic in seconds",
        ge=5.0,
        le=120.0,
        json_schema_extra={"env": "RETRY_MAX_DELAY"},
    )

    retry_backoff_factor: float = Field(
        default=2.0,
        description="Backoff multiplier for retry delays",
        ge=1.5,
        le=5.0,
        json_schema_extra={"env": "RETRY_BACKOFF_FACTOR"},
    )

    # =========================================================================
    # Backup Configuration
    # =========================================================================

    backup_retention_days: int = Field(
        default=7,
        description="Number of days to retain database backups",
        ge=1,
        le=30,
        json_schema_extra={"env": "BACKUP_RETENTION_DAYS"},
    )

    backup_max_count: int = Field(
        default=50,
        description="Maximum number of backup files to retain",
        ge=10,
        le=200,
        json_schema_extra={"env": "BACKUP_MAX_COUNT"},
    )

    backup_cleanup_on_startup: bool = Field(
        default=True,
        description="Clean up old backups on startup",
        json_schema_extra={"env": "BACKUP_CLEANUP_ON_STARTUP"},
    )

    # =========================================================================
    # External Services (Optional)
    # =========================================================================

    openai_api_key: str | None = Field(
        None,
        description="OpenAI API key for Islamic AI features",
        json_schema_extra={"env": "OPENAI_API_KEY"},
    )

    openai_model: str = Field(
        default="gpt-3.5-turbo",
        description="OpenAI model to use for AI responses",
        json_schema_extra={"env": "OPENAI_MODEL"},
    )

    openai_max_tokens: int = Field(
        default=800,
        description="Maximum tokens for AI responses",
        ge=100,
        le=2000,
        json_schema_extra={"env": "OPENAI_MAX_TOKENS"},
    )

    openai_temperature: float = Field(
        default=0.7,
        description="AI response creativity (0=focused, 1=creative)",
        ge=0.0,
        le=1.0,
        json_schema_extra={"env": "OPENAI_TEMPERATURE"},
    )

    openai_monthly_budget: float = Field(
        default=10.0,
        description="Monthly budget limit in USD",
        ge=0.0,
        le=1000.0,
        json_schema_extra={"env": "OPENAI_MONTHLY_BUDGET"},
    )

    ai_rate_limit_per_hour: int = Field(
        default=1,
        description="AI mentions allowed per hour per user",
        ge=1,
        le=10,
        json_schema_extra={"env": "AI_RATE_LIMIT_PER_HOUR"},
    )

    ai_use_knowledge_base: bool = Field(
        default=True,
        description="Use Islamic knowledge base for enhanced AI responses",
        json_schema_extra={"env": "AI_USE_KNOWLEDGE_BASE"},
    )

    # =========================================================================
    # UnbelievaBoat Economy Integration
    # =========================================================================
    
    unbelievaboat_token: str | None = Field(
        None,
        description="UnbelievaBoat API token for economy integration",
        json_schema_extra={"env": "UNBELIEVABOAT_TOKEN"},
    )
    
    quiz_reward_easy: int = Field(
        default=100,
        description="Reward for easy quiz questions (1-2 stars)",
        ge=0,
        le=10000,
        json_schema_extra={"env": "QUIZ_REWARD_EASY"},
    )
    
    quiz_reward_medium: int = Field(
        default=250,
        description="Reward for medium quiz questions (3 stars)",
        ge=0,
        le=10000,
        json_schema_extra={"env": "QUIZ_REWARD_MEDIUM"},
    )
    
    quiz_reward_hard: int = Field(
        default=500,
        description="Reward for hard quiz questions (4-5 stars)",
        ge=0,
        le=10000,
        json_schema_extra={"env": "QUIZ_REWARD_HARD"},
    )

    vps_host: str | None = Field(
        None,
        description="VPS host for deployment",
        json_schema_extra={"env": "VPS_HOST"},
    )

    # =========================================================================
    # Environment Configuration
    # =========================================================================

    environment: Environment = Field(
        default=Environment.PRODUCTION,
        description="Application environment",
        json_schema_extra={"env": "ENVIRONMENT"},
    )

    log_level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Logging level for structured logs",
        json_schema_extra={"env": "LOG_LEVEL"},
    )

    # =========================================================================
    # Validators
    # =========================================================================

    @field_validator("discord_token")
    def validate_discord_token(cls, v: str) -> str:
        """Validate Discord token format and security."""
        if not v:
            raise ValueError(
                "Discord token is required. Get your token from Discord Developer Portal."
            )

        # Allow test tokens for testing environments
        if v.startswith("test_token_"):
            return v

        # Validate production token format
        if len(v) < 50:
            raise ValueError(
                "Invalid Discord token. Get your token from Discord Developer Portal."
            )
        return v

    @field_validator("openai_api_key")
    def validate_openai_api_key(cls, v: str | None) -> str | None:
        """Validate OpenAI API key format."""
        if v is None or v == "":
            return None
        # Allow test keys for testing
        if v.startswith("sk-test"):
            return v
        if not v.startswith("sk-") or len(v) < 40:
            raise ValueError(
                "Invalid OpenAI API key format. Should start with 'sk-' and be at least 40 characters."
            )
        return v

    @field_validator("audio_folder")
    def validate_audio_folder(cls, v: Path) -> Path:
        """Ensure audio folder exists and is accessible."""
        # Allow test paths for testing
        if str(v).startswith("test_"):
            return v

        if not v.exists():
            raise ValueError(
                f"Audio folder not found: {v}. Please ensure audio files are present."
            )
        if not v.is_dir():
            raise ValueError(f"Audio folder path is not a directory: {v}")
        return v

    @field_validator("ffmpeg_path")
    def validate_ffmpeg_path(cls, v: Path) -> Path:
        """cross-platform FFmpeg detection with comprehensive logging."""
        import platform
        import subprocess

        detection_info = {
            "os_system": platform.system(),
            "os_release": platform.release(),
            "architecture": platform.machine(),
            "python_platform": platform.platform(),
            "provided_path": str(v),
            "provided_path_exists": v.exists(),
            "detection_method": None,
            "final_path": None,
            "tested_paths": [],
            "path_verification": {},
        }

        def log_detection_info():
            """Log comprehensive ffmpeg detection information."""
            try:
                from ..core.logger import TreeLogger, log_event

                TreeLogger.info(
                    "🎵 FFmpeg Detection & Verification",
                    {
                        "Operating System": f"{detection_info['os_system']} {detection_info['os_release']}",
                        "Architecture": detection_info["architecture"],
                        "Platform": detection_info["python_platform"],
                        "Detection Method": detection_info["detection_method"],
                        "Final Path": detection_info["final_path"],
                        "Path Exists": (
                            "✅ Yes"
                            if Path(detection_info["final_path"]).exists()
                            else "❌ No"
                        ),
                        "Executable": (
                            "✅ Yes"
                            if os.access(detection_info["final_path"], os.X_OK)
                            else "❌ No"
                        ),
                    },
                )

                if detection_info["tested_paths"]:
                    TreeLogger.info(
                        "📂 Tested Paths",
                        {
                            f"path_{i+1}": f"{path} ({'✅ Found' if found else '❌ Not found'})"
                            for i, (path, found) in enumerate(
                                detection_info["tested_paths"]
                            )
                        },
                        service="Config",
                    )

                # Verify ffmpeg functionality
                try:
                    result = subprocess.run(
                        [detection_info["final_path"], "-version"],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        check=False,
                    )
                    if result.returncode == 0:
                        version_line = result.stdout.split("\n")[0]
                        TreeLogger.info(
                            "✅ FFmpeg Functionality Verified",
                            {
                                "Version": version_line.replace("ffmpeg version ", ""),
                                "Status": "Ready for audio processing",
                                "Test Result": "✅ Successful",
                            },
                        )
                    else:
                        TreeLogger.warning(
                            "⚠️ FFmpeg Execution Warning",
                            {
                                "Path": detection_info["final_path"],
                                "Return Code": result.returncode,
                                "Error": (
                                    result.stderr[:200] if result.stderr else "Unknown"
                                ),
                            },
                            service="Config",
                        )
                except Exception as test_error:
                    TreeLogger.error(
                        "❌ FFmpeg Test Failed",
                        None,
                        {
                            "Path": detection_info["final_path"],
                            "Test Error": str(test_error)[:200],
                            "Recommendation": "Check FFmpeg installation",
                        },
                    )

            except ImportError:
                # Fallback to stderr if TreeLogger not available during config loading
                import sys

                sys.stderr.write(
                    f"FFmpeg detected: {detection_info['final_path']} (Method: {detection_info['detection_method']})\\n"
                )
                sys.stderr.flush()

        # Strategy 1: Check if provided path exists and is executable
        if v.exists() and os.access(v, os.X_OK):
            detection_info["detection_method"] = "provided_path_valid"
            detection_info["final_path"] = str(v)
            log_detection_info()
            return v
        elif v.exists():
            detection_info["tested_paths"].append((str(v), True))
            detection_info["path_verification"][str(v)] = "exists_but_not_executable"
        else:
            detection_info["tested_paths"].append((str(v), False))
            detection_info["path_verification"][str(v)] = "does_not_exist"

        # Strategy 2: Use system PATH detection
        detected_ffmpeg = shutil.which("ffmpeg")
        if detected_ffmpeg:
            detected_path = Path(detected_ffmpeg)
            detection_info["tested_paths"].append((str(detected_path), True))
            if os.access(detected_path, os.X_OK):
                detection_info["detection_method"] = "system_path"
                detection_info["final_path"] = str(detected_path)
                log_detection_info()
                return detected_path
            else:
                detection_info["path_verification"][
                    str(detected_path)
                ] = "found_in_path_but_not_executable"

        # Strategy 3: OS-specific common installation paths
        os_system = platform.system().lower()

        if os_system == "darwin":  # macOS
            macos_paths = [
                Path("/opt/homebrew/bin/ffmpeg"),  # Apple Silicon Homebrew
                Path("/usr/local/bin/ffmpeg"),  # Intel Homebrew
                Path("/usr/local/opt/ffmpeg/bin/ffmpeg"),  # Homebrew alternate
                Path("/opt/local/bin/ffmpeg"),  # MacPorts
                Path("/Applications/ffmpeg"),  # Manual installation
            ]
            common_paths = macos_paths
            detection_info["os_specific_paths"] = "macOS paths"

        elif os_system == "linux":  # Linux/VPS
            linux_paths = [
                Path("/usr/bin/ffmpeg"),  # Standard Ubuntu/Debian
                Path("/usr/local/bin/ffmpeg"),  # Compiled from source
                Path("/snap/bin/ffmpeg"),  # Snap installation
                Path("/usr/local/ffmpeg/bin/ffmpeg"),  # Custom installation
                Path("/opt/ffmpeg/bin/ffmpeg"),  # Alternative location
                Path("/home/*/bin/ffmpeg"),  # User installation
            ]
            common_paths = linux_paths
            detection_info["os_specific_paths"] = "Linux paths"

        elif os_system == "windows":  # Windows
            windows_paths = [
                Path("C:/ffmpeg/bin/ffmpeg.exe"),
                Path("C:/Program Files/ffmpeg/bin/ffmpeg.exe"),
                Path("C:/Program Files (x86)/ffmpeg/bin/ffmpeg.exe"),
                Path("ffmpeg.exe"),  # If in PATH
            ]
            common_paths = windows_paths
            detection_info["os_specific_paths"] = "Windows paths"

        else:  # Unknown OS
            common_paths = [
                Path("/usr/bin/ffmpeg"),
                Path("/usr/local/bin/ffmpeg"),
                Path("/opt/homebrew/bin/ffmpeg"),
            ]
            detection_info["os_specific_paths"] = f"Generic paths for {os_system}"

        # Test OS-specific paths
        for path in common_paths:
            path_exists = path.exists()
            detection_info["tested_paths"].append((str(path), path_exists))

            if path_exists:
                if os.access(path, os.X_OK):
                    detection_info["detection_method"] = f"os_specific_path_{os_system}"
                    detection_info["final_path"] = str(path)
                    log_detection_info()
                    return path
                else:
                    detection_info["path_verification"][
                        str(path)
                    ] = "exists_but_not_executable"
            else:
                detection_info["path_verification"][str(path)] = "does_not_exist"

        # Strategy 4: Try to find ffmpeg recursively in common directories
        search_dirs = []
        if os_system == "darwin":
            search_dirs = ["/opt/homebrew", "/usr/local", "/opt/local"]
        elif os_system == "linux":
            search_dirs = ["/usr", "/usr/local", "/opt"]

        for search_dir in search_dirs[:2]:  # Limit search to avoid performance issues
            try:
                for root, dirs, files in os.walk(search_dir):
                    if "ffmpeg" in files:
                        candidate = Path(root) / "ffmpeg"
                        if os.access(candidate, os.X_OK):
                            detection_info["detection_method"] = (
                                f"recursive_search_{search_dir}"
                            )
                            detection_info["final_path"] = str(candidate)
                            detection_info["tested_paths"].append(
                                (str(candidate), True)
                            )
                            log_detection_info()
                            return candidate
                    # Don't go too deep to avoid performance issues
                    if root.count(os.sep) - search_dir.count(os.sep) > 3:
                        dirs.clear()
            except (PermissionError, OSError):
                continue

        # If we get here, ffmpeg was not found
        detection_info["detection_method"] = "not_found"
        detection_info["final_path"] = "not_found"

        try:
            from ..core.logger import log_event

            TreeLogger.error(
                "❌ FFmpeg Detection Failed",
                None,
                {
                    "Operating System": f"{detection_info['os_system']} {detection_info['os_release']}",
                    "Searched Paths": len(detection_info["tested_paths"]),
                    "Recommendation": "Install FFmpeg using package manager",
                    "macOS": "brew install ffmpeg",
                    "Ubuntu/Debian": "sudo apt install ffmpeg",
                    "CentOS/RHEL": "sudo yum install ffmpeg",
                    "Manual": "Specify FFMPEG_PATH in .env file",
                },
            )
        except ImportError:
            pass

        raise ValueError(
            f"FFmpeg not found on {os_system}. Tested {len(detection_info['tested_paths'])} paths. "
            f"Please install FFmpeg or specify FFMPEG_PATH environment variable."
        )

    @field_validator("developer_id")
    def validate_developer_id(cls, v: int | None) -> int | None:
        """Ensure developer_id is valid if provided."""
        if v is not None and v <= 0:
            raise ValueError("DEVELOPER_ID must be a positive integer if provided.")
        return v

    # =========================================================================
    # Utility Properties
    # =========================================================================

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == Environment.DEVELOPMENT

    def get_reciter_folder(self, reciter: ReciterName | None = None) -> Path:
        """Get the audio folder path for a specific reciter."""
        reciter = reciter or self.default_reciter
        return self.audio_folder / reciter.value

    def get_database_path(self) -> Path:
        """Get the main database file path."""
        return self.data_folder / "databases" / "quranbot.db"

    def get_backup_folder(self) -> Path:
        """Get the backup directory path."""
        return self.data_folder / "backups"

    def get_logs_folder_for_date(self, date_str: str) -> Path:
        """Get the logs folder for a specific date (YYYY-MM-DD format)."""
        return self.logs_folder / date_str
    
    def get_quiz_reward(self, difficulty: int) -> int:
        """Get the reward amount for a quiz question based on difficulty."""
        if difficulty <= 2:
            return self.quiz_reward_easy
        elif difficulty == 3:
            return self.quiz_reward_medium
        else:
            return self.quiz_reward_hard

    # =========================================================================
    # Pydantic Configuration
    # =========================================================================

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "validate_default": True,
    }


# =============================================================================
# Configuration Validation and Logging
# =============================================================================


def validate_configuration_with_logging(config: QuranBotConfig) -> dict[str, Any]:
    """
    Validate configuration with comprehensive logging and reporting.

    Returns:
        Dict containing validation results and metrics
    """
    validation_start = time.time()
    validation_results = {
        "validation_time_ms": 0.0,
        "total_fields": 0,
        "validated_fields": 0,
        "warnings": [],
        "errors": [],
        "field_details": {},
        "path_validations": {},
        "security_checks": {},
    }

    try:
        # Count total fields
        validation_results["total_fields"] = len(QuranBotConfig.model_fields)

        # Validate required Discord fields
        discord_fields = {
            "discord_token": config.discord_token,
            "guild_id": config.guild_id,
            "voice_channel_id": config.voice_channel_id,
            "panel_channel_id": config.panel_channel_id,
            "developer_id": config.developer_id,
        }

        for field_name, field_value in discord_fields.items():
            if field_value:
                validation_results["field_details"][field_name] = "✅ Valid"
                validation_results["validated_fields"] += 1
            else:
                validation_results["field_details"][field_name] = "❌ Missing"
                validation_results["errors"].append(
                    f"Required field {field_name} is missing"
                )

        # Validate paths
        path_fields = {
            "audio_folder": config.audio_folder,
            "data_folder": config.data_folder,
            "logs_folder": config.logs_folder,
            "ffmpeg_path": config.ffmpeg_path,
        }

        for path_name, path_value in path_fields.items():
            try:
                if path_value.exists():
                    validation_results["path_validations"][path_name] = "✅ Exists"

                    # Check permissions
                    if path_value.is_dir():
                        # Test write permission for directories
                        test_file = path_value / ".write_test"
                        try:
                            test_file.touch()
                            test_file.unlink()
                            validation_results["path_validations"][
                                f"{path_name}_writable"
                            ] = "✅ Writable"
                        except Exception:
                            validation_results["path_validations"][
                                f"{path_name}_writable"
                            ] = "❌ Not writable"
                            validation_results["warnings"].append(
                                f"Directory {path_name} is not writable"
                            )
                    elif path_value.is_file():
                        # Check if file is executable (for ffmpeg)
                        if path_name == "ffmpeg_path" and os.access(
                            path_value, os.X_OK
                        ):
                            validation_results["path_validations"][
                                f"{path_name}_executable"
                            ] = "✅ Executable"
                        elif path_name == "ffmpeg_path":
                            validation_results["path_validations"][
                                f"{path_name}_executable"
                            ] = "❌ Not executable"
                            validation_results["warnings"].append(
                                "FFmpeg is not executable"
                            )
                else:
                    validation_results["path_validations"][path_name] = "❌ Missing"
                    if path_name in ["audio_folder", "ffmpeg_path"]:
                        validation_results["errors"].append(
                            f"Critical path {path_name} does not exist"
                        )
                    else:
                        validation_results["warnings"].append(
                            f"Path {path_name} will be created automatically"
                        )

            except Exception as e:
                validation_results["path_validations"][path_name] = f"❌ Error: {e}"
                validation_results["errors"].append(
                    f"Path validation failed for {path_name}: {e}"
                )

        # Security checks
        if config.discord_token:
            if len(config.discord_token) < 50:
                validation_results["security_checks"][
                    "discord_token_length"
                ] = "⚠️ Suspiciously short"
                validation_results["warnings"].append(
                    "Discord token appears to be too short"
                )
            else:
                validation_results["security_checks"][
                    "discord_token_length"
                ] = "✅ Appropriate length"

        if config.openai_api_key:
            if config.openai_api_key.startswith("sk-"):
                validation_results["security_checks"][
                    "openai_key_format"
                ] = "✅ Valid format"
            else:
                validation_results["security_checks"][
                    "openai_key_format"
                ] = "⚠️ Invalid format"
                validation_results["warnings"].append(
                    "OpenAI API key format appears invalid"
                )

        # Environment-specific validations
        if config.is_production:
            if config.log_level == LogLevel.DEBUG:
                validation_results["warnings"].append(
                    "DEBUG logging enabled in production environment"
                )

            validation_results["security_checks"][
                "production_ready"
            ] = "✅ Production mode"
        else:
            validation_results["security_checks"][
                "production_ready"
            ] = "⚠️ Development mode"

        # Audio system validation
        if config.audio_folder.exists():
            reciter_folders = [f for f in config.audio_folder.iterdir() if f.is_dir()]
            validation_results["field_details"][
                "available_reciters"
            ] = f"✅ {len(reciter_folders)} found"

            if len(reciter_folders) == 0:
                validation_results["errors"].append(
                    "No reciter folders found in audio directory"
                )

        validation_results["validation_time_ms"] = (
            time.time() - validation_start
        ) * 1000

        return validation_results

    except Exception as e:
        validation_results["validation_time_ms"] = (
            time.time() - validation_start
        ) * 1000
        validation_results["errors"].append(f"Validation process failed: {e}")
        return validation_results


def log_configuration_loading():
    """Log configuration loading process with detailed information."""
    try:
        # This would typically use TreeLogger, but we need to avoid circular imports
        # The actual logging will be done by the caller
        return {
            "config_metadata": _config_metadata,
            "loading_summary": {
                "env_file_found": Path(".env").exists(),
                "env_vars_loaded": _config_metadata["bot_env_vars"],
                "load_time_ms": _config_metadata["load_time_ms"],
                "timestamp": _config_metadata["load_timestamp"],
            },
        }
    except Exception as e:
        return {
            "error": f"Failed to log configuration loading: {e}",
            "config_metadata": _config_metadata,
        }


# =============================================================================
# Global Configuration Instance with Error Handling
# =============================================================================

_config_instance: QuranBotConfig | None = None
_config_load_errors: list[str] = []
_config_load_warnings: list[str] = []


def get_config() -> QuranBotConfig:
    """
    Get the global configuration instance with comprehensive error handling.

    Returns:
        QuranBotConfig: The validated configuration instance

    Raises:
        ValidationError: If configuration validation fails
    """
    global _config_instance, _config_load_errors, _config_load_warnings

    if _config_instance is None:
        config_creation_start = time.time()

        try:
            _config_instance = QuranBotConfig()

            # Perform comprehensive validation
            validation_results = validate_configuration_with_logging(_config_instance)
            _config_load_errors.extend(validation_results.get("errors", []))
            _config_load_warnings.extend(validation_results.get("warnings", []))

            # Store validation metadata
            _config_metadata.update(
                {
                    "creation_time_ms": f"{(time.time() - config_creation_start) * 1000:.1f}",
                    "validation_results": validation_results,
                    "total_errors": len(_config_load_errors),
                    "total_warnings": len(_config_load_warnings),
                }
            )

        except ValidationError as e:
            # Store validation errors for later reporting
            _config_load_errors.extend([str(error) for error in e.errors()])
            _config_metadata.update(
                {
                    "creation_failed": True,
                    "creation_time_ms": f"{(time.time() - config_creation_start) * 1000:.1f}",
                    "validation_error_count": len(e.errors()),
                }
            )
            raise
        except Exception as e:
            _config_load_errors.append(f"Unexpected configuration error: {e}")
            _config_metadata.update(
                {
                    "creation_failed": True,
                    "creation_time_ms": f"{(time.time() - config_creation_start) * 1000:.1f}",
                    "unexpected_error": str(e),
                }
            )
            raise

    return _config_instance


def reload_config() -> QuranBotConfig:
    """
    Reload configuration from environment variables with comprehensive logging.

    Returns:
        QuranBotConfig: The reloaded configuration instance
    """
    global _config_instance, _config_load_errors, _config_load_warnings

    reload_start = time.time()

    try:
        # Clear previous instance and errors
        _config_instance = None
        _config_load_errors.clear()
        _config_load_warnings.clear()

        # Reload environment variables
        env_reload_result = load_dotenv(override=True)

        # Update metadata
        _config_metadata.update(
            {
                "last_reload": datetime.now(APP_TIMEZONE).isoformat(),
                "env_reload_result": env_reload_result,
                "reload_time_ms": f"{(time.time() - reload_start) * 1000:.1f}",
            }
        )

        # Get new configuration instance
        return get_config()

    except Exception as e:
        _config_load_errors.append(f"Configuration reload failed: {e}")
        _config_metadata.update(
            {
                "reload_failed": True,
                "reload_error": str(e),
                "reload_time_ms": f"{(time.time() - reload_start) * 1000:.1f}",
            }
        )
        raise


def get_config_metadata() -> dict[str, Any]:
    """
    Get comprehensive configuration metadata for logging and debugging.

    Returns:
        Dict containing configuration loading metadata, errors, and warnings
    """
    return {
        "metadata": _config_metadata.copy(),
        "errors": _config_load_errors.copy(),
        "warnings": _config_load_warnings.copy(),
        "instance_created": _config_instance is not None,
        "current_timestamp": datetime.now(APP_TIMEZONE).isoformat(),
    }


def validate_critical_config() -> tuple[bool, list[str]]:
    """
    Validate critical configuration fields required for bot operation.

    Returns:
        Tuple of (is_valid, list_of_critical_errors)
    """
    critical_errors = []

    try:
        config = get_config()

        # Check absolutely required fields
        if not config.discord_token:
            critical_errors.append("Discord token is required")

        if not config.guild_id:
            critical_errors.append("Guild ID is required")

        if not config.developer_id:
            critical_errors.append("Developer ID is required")

        if not config.audio_folder.exists():
            critical_errors.append("Audio folder must exist")

        if not config.ffmpeg_path.exists():
            critical_errors.append("FFmpeg must be installed and accessible")

        return len(critical_errors) == 0, critical_errors

    except Exception as e:
        critical_errors.append(f"Configuration validation failed: {e}")
        return False, critical_errors
