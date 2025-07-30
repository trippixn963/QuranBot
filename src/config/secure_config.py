# =============================================================================
# QuranBot - Security-Hardened Configuration
# =============================================================================
# Security-hardened configuration system with comprehensive input validation,
# secure defaults, and protection against common configuration vulnerabilities.
# =============================================================================

import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator

# Try to import BaseSettings from the correct location
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    try:
        from pydantic import BaseSettings
        class SettingsConfigDict(dict):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
    except ImportError:
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


class ReciterName(str, Enum):
    """Available Quran reciters."""
    SAAD_AL_GHAMDI = "Saad Al Ghamdi"
    ABDUL_BASIT = "Abdul Basit Abdul Samad"
    MAHER_AL_MUAIQLY = "Maher Al Muaiqly"
    MUHAMMAD_AL_LUHAIDAN = "Muhammad Al Luhaidan"
    RASHID_AL_AFASY = "Rashid Al Afasy"
    YASSER_AL_DOSARI = "Yasser Al Dosari"


class SecureQuranBotConfig(BaseSettings):
    """
    Security-hardened configuration for QuranBot.
    
    This configuration class implements comprehensive security measures:
    - Secure input validation for all fields
    - Protection against injection attacks
    - Secure defaults and constraints
    - Sensitive data handling
    """
    
    # =============================================================================
    # CORE DISCORD SETTINGS (Required)
    # =============================================================================
    
    discord_token: str = Field(
        ..., 
        description="Discord bot token",
        min_length=50
    )
    
    guild_id: int = Field(
        ..., 
        description="Discord server (guild) ID",
        gt=4194304,  # Minimum Discord snowflake
        lt=2**63     # Maximum 64-bit integer
    )
    
    target_channel_id: int = Field(
        ..., 
        description="Voice channel ID for audio playback",
        gt=4194304,
        lt=2**63
    )
    
    # =============================================================================
    # OPTIONAL DISCORD SETTINGS
    # =============================================================================
    
    panel_channel_id: Optional[int] = Field(
        None, 
        description="Channel ID for control panel",
        gt=4194304,
        lt=2**63
    )
    
    logs_channel_id: Optional[int] = Field(
        None, 
        description="Channel ID for bot logs",
        gt=4194304,
        lt=2**63
    )
    
    daily_verse_channel_id: Optional[int] = Field(
        None, 
        description="Channel ID for daily verses",
        gt=4194304,
        lt=2**63
    )
    
    panel_access_role_id: Optional[int] = Field(
        None, 
        description="Role ID for panel access",
        gt=4194304,
        lt=2**63
    )
    
    # =============================================================================
    # ADMIN SETTINGS
    # =============================================================================
    
    admin_user_ids: str = Field(
        default="", 
        description="Comma-separated admin user IDs",
        max_length=1000  # Reasonable limit
    )
    
    developer_id: Optional[int] = Field(
        None, 
        description="Developer user ID",
        gt=4194304,
        lt=2**63
    )
    
    # =============================================================================
    # AUDIO SETTINGS
    # =============================================================================
    
    audio_folder: Path = Field(
        default=Path("audio"), 
        description="Audio files directory"
    )
    
    default_reciter: ReciterName = Field(
        default=ReciterName.SAAD_AL_GHAMDI,
        description="Default Quran reciter"
    )
    
    ffmpeg_path: Path = Field(
        default=Path("/usr/bin/ffmpeg"), 
        description="FFmpeg executable path"
    )
    
    audio_quality: str = Field(
        default="128k",
        description="Audio quality (e.g., 128k, 256k)",
        pattern=r"^\d+k$",
        max_length=10
    )
    
    default_shuffle: bool = Field(
        default=False,
        description="Enable shuffle by default"
    )
    
    default_loop: bool = Field(
        default=False,
        description="Enable loop by default"
    )
    
    # =============================================================================
    # LOGGING SETTINGS
    # =============================================================================
    
    log_level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Application log level"
    )
    
    use_webhook_logging: bool = Field(
        default=True,
        description="Use Discord webhook for logging"
    )
    
    discord_webhook_url: Optional[str] = Field(
        None,
        description="Discord webhook URL for logging",
        max_length=200  # Reasonable webhook URL length
    )
    
    # =============================================================================
    # PERFORMANCE SETTINGS
    # =============================================================================
    
    cache_ttl_seconds: int = Field(
        default=300,
        description="Cache time-to-live in seconds",
        ge=60,
        le=3600
    )
    
    rate_limit_per_minute: int = Field(
        default=10,
        description="Commands per minute per user",
        ge=1,
        le=100
    )
    
    max_concurrent_audio: int = Field(
        default=1,
        description="Max concurrent audio streams",
        ge=1,
        le=5
    )
    
    backup_interval_hours: int = Field(
        default=24,
        description="Backup interval in hours",
        ge=1,
        le=168
    )
    
    # =============================================================================
    # ENVIRONMENT SETTINGS
    # =============================================================================
    
    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Application environment"
    )
    
    # =============================================================================
    # OPTIONAL INTEGRATIONS
    # =============================================================================
    
    openai_api_key: Optional[str] = Field(
        None,
        description="OpenAI API key for Islamic AI",
        min_length=40,
        max_length=100
    )
    
    vps_host: Optional[str] = Field(
        None,
        description="VPS host for deployment",
        max_length=100
    )
    
    # =============================================================================
    # SECURITY VALIDATION
    # =============================================================================
    
    @field_validator("discord_token")
    @classmethod
    def validate_discord_token(cls, v: str) -> str:
        """Securely validate Discord token format."""
        try:
            from src.security.validators import SecureValidator
            return SecureValidator.validate_discord_token(v)
        except ImportError:
            # Fallback validation if security module not available
            if not v or len(v) < 50:
                raise ValueError("Discord token must be at least 50 characters")
            # Basic format check
            if any(char in v for char in ['<', '>', '"', "'", '&', '\x00']):
                raise ValueError("Discord token contains invalid characters")
            return v
    
    @field_validator("guild_id", "target_channel_id", "panel_channel_id", 
                    "logs_channel_id", "daily_verse_channel_id", 
                    "panel_access_role_id", "developer_id")
    @classmethod
    def validate_discord_ids(cls, v: Optional[int]) -> Optional[int]:
        """Validate Discord IDs (snowflakes)."""
        if v is None:
            return v
        
        try:
            from src.security.validators import SecureValidator
            if hasattr(SecureValidator, 'validate_user_id'):
                return SecureValidator.validate_user_id(v)
        except ImportError:
            pass
        
        # Fallback validation
        if not (4194304 <= v < 2**63):
            raise ValueError("Discord ID out of valid range")
        return v
    
    @field_validator("admin_user_ids", mode="before")
    @classmethod
    def validate_admin_user_ids(cls, v) -> str:
        """Securely validate admin user IDs."""
        if not v:
            return ""
        
        try:
            from src.security.validators import SecureValidator
            user_ids = SecureValidator.validate_admin_user_ids(str(v))
            return ",".join(map(str, user_ids))
        except ImportError:
            # Fallback validation
            if isinstance(v, str):
                if not v.strip():
                    return ""
                # Basic validation
                parts = [part.strip() for part in v.split(",") if part.strip()]
                for part in parts:
                    if not part.isdigit() or len(part) < 17 or len(part) > 19:
                        raise ValueError(f"Invalid user ID format: {part}")
                return v
            return str(v) if v else ""
    
    @field_validator("discord_webhook_url")
    @classmethod
    def validate_webhook_url(cls, v: Optional[str]) -> Optional[str]:
        """Securely validate Discord webhook URL."""
        if v is None:
            return v
        
        try:
            from src.security.validators import SecureValidator
            return SecureValidator.validate_webhook_url(v)
        except ImportError:
            # Fallback validation
            if not v.startswith("https://discord.com/api/webhooks/"):
                raise ValueError("Invalid Discord webhook URL format")
            return v
    
    @field_validator("openai_api_key")
    @classmethod
    def validate_openai_key(cls, v: Optional[str]) -> Optional[str]:
        """Securely validate OpenAI API key."""
        if v is None:
            return v
        
        try:
            from src.security.validators import SecureValidator
            return SecureValidator.validate_openai_key(v)
        except ImportError:
            # Fallback validation
            if not v.startswith("sk-") or len(v) < 40:
                raise ValueError("Invalid OpenAI API key format")
            return v
    
    @field_validator("audio_folder")
    @classmethod
    def validate_audio_folder(cls, v: Path) -> Path:
        """Validate audio folder exists and is secure."""
        # Convert to Path if string
        if isinstance(v, str):
            v = Path(v)
        
        # Security check - prevent path traversal
        if '..' in str(v) or str(v).startswith('/'):
            raise ValueError("Invalid audio folder path - potential path traversal")
        
        # Check if folder exists
        if not v.exists():
            raise ValueError(f"Audio folder does not exist: {v}")
        
        if not v.is_dir():
            raise ValueError(f"Audio folder is not a directory: {v}")
        
        return v
    
    @field_validator("ffmpeg_path")
    @classmethod
    def validate_ffmpeg_path(cls, v: Path) -> Path:
        """Validate FFmpeg executable securely."""
        if isinstance(v, str):
            v = Path(v)
        
        # Security check - only allow absolute paths to prevent injection
        if not v.is_absolute():
            raise ValueError("FFmpeg path must be absolute")
        
        # Check if file exists and is executable
        if not v.exists():
            raise ValueError(f"FFmpeg executable not found: {v}")
        
        if not os.access(v, os.X_OK):
            raise ValueError(f"FFmpeg executable is not executable: {v}")
        
        return v
    
    @field_validator("vps_host")
    @classmethod
    def validate_vps_host(cls, v: Optional[str]) -> Optional[str]:
        """Validate VPS host format."""
        if v is None:
            return v
        
        # Basic format validation
        if '@' in v:
            # Format: user@host
            user, host = v.split('@', 1)
            if not user or not host:
                raise ValueError("Invalid VPS host format")
            # Check for dangerous characters
            dangerous_chars = ['<', '>', '"', "'", '&', ';', '|', '`']
            if any(char in v for char in dangerous_chars):
                raise ValueError("VPS host contains dangerous characters")
        
        return v
    
    @model_validator(mode="after")
    def validate_security_constraints(self) -> "SecureQuranBotConfig":
        """Validate security constraints across fields."""
        # Ensure webhook logging has URL if enabled
        if self.use_webhook_logging and not self.discord_webhook_url:
            raise ValueError("Webhook URL required when webhook logging is enabled")
        
        # Ensure channel IDs are unique
        channel_ids = [
            self.target_channel_id,
            self.panel_channel_id,
            self.logs_channel_id,
            self.daily_verse_channel_id
        ]
        
        # Remove None values and check for duplicates
        valid_channel_ids = [cid for cid in channel_ids if cid is not None]
        if len(valid_channel_ids) != len(set(valid_channel_ids)):
            raise ValueError("Channel IDs must be unique")
        
        # Production environment security checks
        if self.environment == Environment.PRODUCTION:
            if self.log_level == LogLevel.DEBUG:
                raise ValueError("Debug logging not allowed in production")
            
            if not self.use_webhook_logging:
                raise ValueError("Webhook logging required in production")
        
        return self
    
    # =============================================================================
    # COMPUTED PROPERTIES
    # =============================================================================
    
    @property
    def admin_user_id_list(self) -> List[int]:
        """Get admin user IDs as a list of integers."""
        if not self.admin_user_ids.strip():
            return []
        try:
            return [int(uid.strip()) for uid in self.admin_user_ids.split(",") if uid.strip()]
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
        return self.audio_folder / self.default_reciter.value
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    def is_admin_user(self, user_id: int) -> bool:
        """Check if a user ID is an admin."""
        return user_id in self.admin_user_id_list or user_id == self.developer_id
    
    def get_reciter_folder(self, reciter: Optional[ReciterName] = None) -> Path:
        """Get audio folder path for a specific reciter."""
        reciter = reciter or self.default_reciter
        return self.audio_folder / reciter.value
    
    def get_security_summary(self) -> Dict[str, Any]:
        """Get security configuration summary."""
        return {
            "environment": self.environment.value,
            "webhook_logging_enabled": self.use_webhook_logging,
            "debug_logging": self.log_level == LogLevel.DEBUG,
            "admin_users_count": len(self.admin_user_id_list),
            "openai_enabled": bool(self.openai_api_key),
            "production_ready": (
                self.is_production and 
                self.use_webhook_logging and 
                self.log_level != LogLevel.DEBUG
            ),
            "security_features": [
                "Input validation",
                "Path traversal protection", 
                "Secure token validation",
                "Rate limiting configured",
                "Webhook URL validation"
            ]
        }
    
    # =============================================================================
    # PYDANTIC CONFIGURATION
    # =============================================================================
    
    if hasattr(BaseSettings, 'model_config'):
        model_config = SettingsConfigDict(
            env_file="config/.env",
            env_file_encoding="utf-8",
            case_sensitive=False,
            use_enum_values=True,
            validate_assignment=True,
            extra="forbid",  # Prevent extra fields for security
        )
    else:
        class Config:
            env_file = "config/.env"
            env_file_encoding = "utf-8"
            case_sensitive = False
            use_enum_values = True
            validate_assignment = True
            extra = "forbid"


# =============================================================================
# SECURE CONFIGURATION INSTANCE
# =============================================================================

_secure_config_instance: Optional[SecureQuranBotConfig] = None


def get_secure_config() -> SecureQuranBotConfig:
    """
    Get the global secure configuration instance (singleton).
    
    Returns:
        SecureQuranBotConfig: The global secure configuration instance
    """
    global _secure_config_instance
    if _secure_config_instance is None:
        _secure_config_instance = SecureQuranBotConfig()
    return _secure_config_instance


def reload_secure_config() -> SecureQuranBotConfig:
    """
    Reload secure configuration from environment/files.
    
    Returns:
        SecureQuranBotConfig: The reloaded secure configuration instance
    """
    global _secure_config_instance
    _secure_config_instance = SecureQuranBotConfig()
    return _secure_config_instance