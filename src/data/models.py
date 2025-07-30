# =============================================================================
# QuranBot - Data Models
# =============================================================================
# This module defines Pydantic models for type safety and validation across
# the QuranBot application. All data structures use these models to ensure
# consistency and proper validation.
# =============================================================================

from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# =============================================================================
# Audio Service Models
# =============================================================================


class ReciterInfo(BaseModel):
    """Information about a Quranic reciter"""

    name: str = Field(..., description="Name of the reciter")
    folder_name: str = Field(..., description="Folder name in audio directory")
    total_surahs: int = Field(
        ..., ge=1, le=114, description="Number of available surahs"
    )
    file_count: int = Field(..., ge=0, description="Total number of audio files")
    audio_quality: str | None = Field(
        None, description="Audio quality (e.g., '128kbps', '320kbps')"
    )
    language: str = Field(default="Arabic", description="Language of recitation")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Saad Al Ghamdi",
                "folder_name": "Saad Al Ghamdi",
                "total_surahs": 114,
                "file_count": 114,
                "audio_quality": "128kbps",
                "language": "Arabic",
            }
        }
    )


class SurahInfo(BaseModel):
    """Information about a Quran surah"""

    number: int = Field(..., ge=1, le=114, description="Surah number (1-114)")
    name_arabic: str = Field(..., description="Arabic name of the surah")
    name_transliteration: str = Field(..., description="Transliterated name")
    name_english: str = Field(..., description="English translation of the name")
    verses_count: int = Field(..., ge=1, description="Number of verses in the surah")
    revelation_place: str = Field(
        ..., description="Place of revelation (Makkah/Madinah)"
    )
    revelation_order: int = Field(
        ..., ge=1, le=114, description="Chronological order of revelation"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "number": 1,
                "name_arabic": "الفاتحة",
                "name_transliteration": "Al-Fatiha",
                "name_english": "The Opening",
                "verses_count": 7,
                "revelation_place": "Makkah",
                "revelation_order": 5,
            }
        }
    )


class AudioFileInfo(BaseModel):
    """Information about an audio file"""

    file_path: Path = Field(..., description="Full path to the audio file")
    surah_number: int = Field(..., ge=1, le=114, description="Surah number")
    reciter: str = Field(..., description="Reciter name")
    duration_seconds: float | None = Field(
        None, ge=0, description="Duration in seconds"
    )
    file_size_bytes: int | None = Field(None, ge=0, description="File size in bytes")
    bitrate: str | None = Field(None, description="Audio bitrate")
    format: str = Field(default="mp3", description="Audio format")
    created_at: datetime | None = Field(None, description="File creation timestamp")
    last_modified: datetime | None = Field(
        None, description="Last modification timestamp"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file_path": "/audio/Saad Al Ghamdi/001.mp3",
                "surah_number": 1,
                "reciter": "Saad Al Ghamdi",
                "duration_seconds": 87.5,
                "file_size_bytes": 1048576,
                "bitrate": "128kbps",
                "format": "mp3",
            }
        }
    )


class PlaybackPosition(BaseModel):
    """Current playback position information"""

    surah_number: int = Field(..., ge=1, le=114, description="Current surah number")
    position_seconds: float = Field(
        default=0.0, ge=0, description="Position within the track"
    )
    total_duration: float | None = Field(None, ge=0, description="Total track duration")
    track_index: int = Field(default=0, ge=0, description="Index in current playlist")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def progress_percentage(self) -> float | None:
        """Calculate progress percentage if duration is available"""
        if self.total_duration and self.total_duration > 0:
            return min(100.0, (self.position_seconds / self.total_duration) * 100)
        return None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "surah_number": 1,
                "position_seconds": 45.5,
                "total_duration": 87.5,
                "track_index": 0,
                "progress_percentage": 52.0,
            }
        }
    )


class PlaybackMode(str, Enum):
    """Playback mode options"""

    NORMAL = "normal"
    SHUFFLE = "shuffle"
    LOOP_TRACK = "loop_track"
    LOOP_PLAYLIST = "loop_playlist"


class PlaybackState(BaseModel):
    """Complete playback state information"""

    is_playing: bool = Field(
        default=False, description="Whether audio is currently playing"
    )
    is_paused: bool = Field(default=False, description="Whether playback is paused")
    is_connected: bool = Field(
        default=False, description="Whether connected to voice channel"
    )
    current_reciter: str = Field(..., description="Currently selected reciter")
    current_position: PlaybackPosition = Field(
        ..., description="Current playback position"
    )
    mode: PlaybackMode = Field(
        default=PlaybackMode.NORMAL, description="Current playback mode"
    )
    volume: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Playback volume (0.0-1.0)"
    )
    queue: list[int] = Field(default_factory=list, description="Queue of surah numbers")
    voice_channel_id: int | None = Field(None, description="Connected voice channel ID")
    guild_id: int | None = Field(None, description="Guild ID")
    last_updated: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_state_consistency(self):
        """Ensure state consistency"""
        # Can't be both playing and paused
        if self.is_playing and self.is_paused:
            raise ValueError("Cannot be both playing and paused simultaneously")

        return self

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "is_playing": True,
                "is_paused": False,
                "is_connected": True,
                "current_reciter": "Saad Al Ghamdi",
                "mode": "normal",
                "volume": 1.0,
                "queue": [1, 2, 3],
                "voice_channel_id": 123456789,
                "guild_id": 987654321,
            }
        }
    )


class AudioCache(BaseModel):
    """Audio metadata cache entry"""

    reciter: str = Field(..., description="Reciter name")
    surah_number: int = Field(..., ge=1, le=114, description="Surah number")
    file_path: str = Field(..., description="File path")
    duration: float | None = Field(None, description="Duration in seconds")
    file_size: int | None = Field(None, description="File size in bytes")
    file_hash: str | None = Field(None, description="File hash for change detection")
    last_accessed: datetime = Field(default_factory=lambda: datetime.now(UTC))
    access_count: int = Field(default=0, description="Number of times accessed")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "reciter": "Saad Al Ghamdi",
                "surah_number": 1,
                "file_path": "/audio/Saad Al Ghamdi/001.mp3",
                "duration": 87.5,
                "file_size": 1048576,
                "file_hash": "abc123def456",
                "access_count": 5,
            }
        }
    )


class AudioServiceConfig(BaseModel):
    """Configuration for the audio service"""

    audio_base_folder: Path = Field(..., description="Base directory for audio files")
    ffmpeg_path: str = Field(..., description="Path to FFmpeg executable")
    default_reciter: str = Field(
        default="Saad Al Ghamdi", description="Default reciter for audio playback"
    )
    default_volume: float = Field(
        default=1.0, ge=0.0, le=2.0, description="Default volume level"
    )
    connection_timeout: float = Field(
        default=30.0, gt=0, description="Voice connection timeout in seconds"
    )
    playback_timeout: float = Field(
        default=300.0, gt=0, description="Playback timeout in seconds"
    )
    max_retry_attempts: int = Field(
        default=3, ge=1, description="Maximum retry attempts for connections"
    )
    retry_delay: float = Field(
        default=1.0, gt=0, description="Delay between retry attempts in seconds"
    )
    preload_metadata: bool = Field(
        default=True, description="Whether to preload metadata on startup"
    )
    cache_enabled: bool = Field(
        default=True, description="Whether to enable metadata caching"
    )
    playback_buffer_size: str = Field(
        default="2048k", description="FFmpeg buffer size for audio playback"
    )
    enable_reconnection: bool = Field(
        default=True, description="Whether to enable automatic reconnection"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "audio_base_folder": "/path/to/audio",
                "ffmpeg_path": "/usr/bin/ffmpeg",
                "default_reciter": "Saad Al Ghamdi",
                "default_volume": 1.0,
                "connection_timeout": 30.0,
                "playback_timeout": 300.0,
                "max_retry_attempts": 3,
                "retry_delay": 1.0,
            }
        }
    )


# =============================================================================
# Quiz System Models
# =============================================================================


class QuizDifficulty(str, Enum):
    """Quiz difficulty levels"""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class QuizCategory(str, Enum):
    """Quiz categories"""

    QURAN = "quran"
    HADITH = "hadith"
    ISLAMIC_HISTORY = "islamic_history"
    ISLAMIC_KNOWLEDGE = "islamic_knowledge"
    PROPHETS = "prophets"
    COMPANIONS = "companions"


class QuizChoice(BaseModel):
    """A quiz question choice"""

    letter: str = Field(..., pattern=r"^[A-F]$", description="Choice letter (A-F)")
    text: str = Field(..., min_length=1, description="Choice text")
    is_correct: bool = Field(
        default=False, description="Whether this is the correct answer"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"letter": "A", "text": "Al-Fatiha", "is_correct": True}
        }
    )


class QuizQuestion(BaseModel):
    """A quiz question with choices"""

    id: str = Field(..., description="Unique question identifier")
    category: QuizCategory = Field(..., description="Question category")
    difficulty: QuizDifficulty = Field(..., description="Question difficulty")
    question_text: str = Field(..., min_length=10, description="The question text")
    choices: list[QuizChoice] = Field(
        ..., min_length=2, max_length=6, description="Answer choices"
    )
    explanation: str | None = Field(
        None, description="Explanation of the correct answer"
    )
    source: str | None = Field(
        None, description="Source reference (e.g., Quran verse, Hadith)"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("choices")
    @classmethod
    def validate_choices(cls, v):
        """Ensure exactly one correct answer and unique letters"""
        correct_count = sum(1 for choice in v if choice.is_correct)
        if correct_count != 1:
            raise ValueError(
                f"Must have exactly one correct answer, found {correct_count}"
            )

        letters = [choice.letter for choice in v]
        if len(letters) != len(set(letters)):
            raise ValueError("Choice letters must be unique")

        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "quran_001",
                "category": "quran",
                "difficulty": "easy",
                "question_text": "What is the first surah of the Quran?",
                "choices": [
                    {"letter": "A", "text": "Al-Fatiha", "is_correct": True},
                    {"letter": "B", "text": "Al-Baqarah", "is_correct": False},
                    {"letter": "C", "text": "An-Nas", "is_correct": False},
                ],
            }
        }
    )


class UserQuizStats(BaseModel):
    """User quiz statistics"""

    user_id: int = Field(..., description="Discord user ID")
    total_questions: int = Field(
        default=0, ge=0, description="Total questions answered"
    )
    correct_answers: int = Field(
        default=0, ge=0, description="Number of correct answers"
    )
    streak: int = Field(default=0, ge=0, description="Current correct streak")
    best_streak: int = Field(default=0, ge=0, description="Best streak achieved")
    category_stats: dict[str, dict[str, int]] = Field(
        default_factory=dict, description="Stats by category"
    )
    last_quiz_date: datetime | None = Field(
        None, description="Last quiz participation date"
    )
    total_time_spent: float = Field(
        default=0.0, ge=0, description="Total time spent on quizzes (seconds)"
    )

    @property
    def accuracy_percentage(self) -> float:
        """Calculate accuracy percentage"""
        if self.total_questions == 0:
            return 0.0
        return (self.correct_answers / self.total_questions) * 100

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": 123456789,
                "total_questions": 50,
                "correct_answers": 42,
                "streak": 5,
                "best_streak": 12,
                "accuracy_percentage": 84.0,
            }
        }
    )


# =============================================================================
# State Management Models
# =============================================================================


class BotSession(BaseModel):
    """Information about a bot session"""

    session_id: str = Field(..., description="Unique session identifier")
    start_time: datetime = Field(default_factory=lambda: datetime.now(UTC))
    end_time: datetime | None = Field(None, description="Session end time")
    total_runtime: float = Field(
        default=0.0, ge=0, description="Total runtime in seconds"
    )
    commands_executed: int = Field(
        default=0, ge=0, description="Number of commands executed"
    )
    voice_connections: int = Field(
        default=0, ge=0, description="Number of voice connections"
    )
    errors_count: int = Field(
        default=0, ge=0, description="Number of errors encountered"
    )
    restart_reason: str | None = Field(None, description="Reason for session end")

    @property
    def duration_seconds(self) -> float:
        """Calculate session duration in seconds"""
        end = self.end_time or datetime.now(UTC)
        return (end - self.start_time).total_seconds()

    @property
    def is_active(self) -> bool:
        """Check if session is currently active"""
        return self.end_time is None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "session_2024_01_15_12_30_45",
                "start_time": "2024-01-15T12:30:45Z",
                "total_runtime": 3600.0,
                "commands_executed": 25,
                "voice_connections": 3,
                "errors_count": 1,
                "is_active": True,
            }
        }
    )


class BotStatistics(BaseModel):
    """Bot usage statistics"""

    total_runtime: float = Field(
        default=0.0, ge=0, description="Total runtime in seconds"
    )
    total_sessions: int = Field(default=0, ge=0, description="Number of sessions")
    total_commands: int = Field(default=0, ge=0, description="Total commands executed")
    total_voice_connections: int = Field(
        default=0, ge=0, description="Total voice connections"
    )
    total_errors: int = Field(default=0, ge=0, description="Total errors encountered")
    surahs_completed: int = Field(
        default=0, ge=0, description="Number of surahs completed"
    )
    favorite_reciter: str = Field(
        default="Saad Al Ghamdi", description="Most used reciter"
    )
    last_startup: datetime | None = Field(None, description="Last startup time")
    last_shutdown: datetime | None = Field(None, description="Last shutdown time")
    uptime_percentage: float = Field(
        default=0.0, ge=0, le=100, description="Uptime percentage"
    )
    average_session_duration: float = Field(
        default=0.0, ge=0, description="Average session duration"
    )

    @property
    def average_commands_per_session(self) -> float:
        """Calculate average commands per session"""
        if self.total_sessions == 0:
            return 0.0
        return self.total_commands / self.total_sessions

    @property
    def error_rate_percentage(self) -> float:
        """Calculate error rate percentage"""
        if self.total_commands == 0:
            return 0.0
        return (self.total_errors / self.total_commands) * 100

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_runtime": 86400.0,
                "total_sessions": 10,
                "total_commands": 250,
                "surahs_completed": 15,
                "favorite_reciter": "Saad Al Ghamdi",
                "uptime_percentage": 95.5,
                "average_commands_per_session": 25.0,
                "error_rate_percentage": 2.0,
            }
        }
    )


class StateSnapshot(BaseModel):
    """Complete state snapshot for backup purposes"""

    snapshot_id: str = Field(..., description="Unique snapshot identifier")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    playback_state: PlaybackState = Field(..., description="Current playback state")
    bot_statistics: BotStatistics = Field(..., description="Bot statistics")
    current_session: BotSession | None = Field(
        None, description="Current active session"
    )
    version: str = Field(default="3.0.0", description="State format version")
    checksum: str | None = Field(None, description="Data integrity checksum")

    @property
    def age_hours(self) -> float:
        """Calculate snapshot age in hours"""
        return (datetime.now(UTC) - self.created_at).total_seconds() / 3600

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "snapshot_id": "snapshot_2024_01_15_12_30_45",
                "created_at": "2024-01-15T12:30:45Z",
                "version": "3.0.0",
                "age_hours": 2.5,
            }
        }
    )


class StateServiceConfig(BaseModel):
    """Configuration for the state service"""

    data_directory: Path = Field(
        default=Path("data"), description="Directory for state files"
    )
    backup_directory: Path = Field(
        default=Path("backup"), description="Directory for backups"
    )
    enable_backups: bool = Field(default=True, description="Whether to create backups")
    backup_interval_hours: int = Field(
        default=24, ge=1, description="Backup interval in hours"
    )
    max_backups: int = Field(
        default=7, ge=1, description="Maximum number of backups to keep"
    )
    enable_integrity_checks: bool = Field(
        default=True, description="Whether to perform integrity checks"
    )
    atomic_writes: bool = Field(
        default=True, description="Whether to use atomic file writes"
    )
    compression_enabled: bool = Field(
        default=True, description="Whether to compress backup files"
    )
    auto_recovery: bool = Field(
        default=True, description="Whether to enable automatic recovery"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "data_directory": "/data",
                "backup_directory": "/backup",
                "enable_backups": True,
                "backup_interval_hours": 24,
                "max_backups": 7,
                "atomic_writes": True,
            }
        }
    )


class BackupInfo(BaseModel):
    """Information about a backup"""

    backup_id: str = Field(..., description="Unique backup identifier")
    file_path: Path = Field(..., description="Path to backup file")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    backup_type: str = Field(
        ..., description="Type of backup (manual, automatic, emergency)"
    )
    file_size: int = Field(..., ge=0, description="Backup file size in bytes")
    checksum: str | None = Field(
        None, description="File checksum for integrity verification"
    )
    description: str | None = Field(None, description="Backup description")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "backup_id": "backup_2024_01_15_12_30_45",
                "file_path": "/backups/backup_2024_01_15_12_30_45.zip",
                "backup_type": "automatic",
                "file_size": 2048576,
                "checksum": "abc123def456",
            }
        }
    )


class StateValidationResult(BaseModel):
    """Result of state validation"""

    is_valid: bool = Field(..., description="Whether the state is valid")
    errors: list[str] = Field(
        default_factory=list, description="List of validation errors"
    )
    warnings: list[str] = Field(
        default_factory=list, description="List of validation warnings"
    )
    corrected_fields: dict[str, Any] = Field(
        default_factory=dict, description="Fields that were auto-corrected"
    )
    validation_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def has_errors(self) -> bool:
        """Check if there are any errors"""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings"""
        return len(self.warnings) > 0

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "is_valid": True,
                "errors": [],
                "warnings": ["Volume was outside valid range, corrected to 1.0"],
                "corrected_fields": {"volume": 1.0},
            }
        }
    )


# =============================================================================
# Configuration Models
# =============================================================================


class DiscordConfig(BaseModel):
    """Discord-specific configuration"""

    token: str = Field(..., min_length=50, description="Discord bot token")
    guild_id: int = Field(..., description="Target guild ID")
    voice_channel_id: int = Field(..., description="Voice channel ID for audio")
    panel_channel_id: int = Field(..., description="Channel ID for control panel")
    logs_channel_id: int | None = Field(None, description="Channel ID for log messages")
    developer_id: int | None = Field(None, description="Developer user ID")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "token": "BOT_TOKEN_HERE",
                "guild_id": 123456789,
                "voice_channel_id": 987654321,
                "panel_channel_id": 111222333,
                "logs_channel_id": 444555666,
                "developer_id": 777888999,
            }
        }
    )


class WebhookConfig(BaseModel):
    """Webhook configuration for Discord logging"""

    url: str = Field(
        ...,
        pattern=r"^https://discord\.com/api/webhooks/\d+/[\w-]+$",
        description="Discord webhook URL",
    )
    enabled: bool = Field(
        default=True, description="Whether webhook logging is enabled"
    )
    rate_limit_per_minute: int = Field(
        default=30, ge=1, le=60, description="Rate limit for webhook messages"
    )
    retry_attempts: int = Field(
        default=3, ge=1, le=10, description="Number of retry attempts on failure"
    )
    timeout_seconds: int = Field(
        default=10, ge=1, le=60, description="Request timeout in seconds"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url": "https://discord.com/api/webhooks/123456789/abcdef123456",
                "enabled": True,
                "rate_limit_per_minute": 30,
                "retry_attempts": 3,
                "timeout_seconds": 10,
            }
        }
    )


# =============================================================================
# Monitoring and Analytics Models
# =============================================================================


class PerformanceMetrics(BaseModel):
    """Performance metrics for monitoring"""

    cpu_usage_percent: float = Field(
        ..., ge=0.0, le=100.0, description="CPU usage percentage"
    )
    memory_usage_mb: float = Field(..., ge=0.0, description="Memory usage in MB")
    memory_usage_percent: float = Field(
        ..., ge=0.0, le=100.0, description="Memory usage percentage"
    )
    disk_usage_gb: float = Field(..., ge=0.0, description="Disk usage in GB")
    network_latency_ms: float | None = Field(
        None, ge=0.0, description="Network latency in milliseconds"
    )
    uptime_seconds: float = Field(..., ge=0.0, description="Uptime in seconds")
    active_connections: int = Field(
        default=0, ge=0, description="Number of active connections"
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "cpu_usage_percent": 15.5,
                "memory_usage_mb": 128.0,
                "memory_usage_percent": 12.5,
                "disk_usage_gb": 1.2,
                "network_latency_ms": 45.0,
                "uptime_seconds": 86400,
                "active_connections": 3,
            }
        }
    )


class ErrorMetrics(BaseModel):
    """Error tracking metrics"""

    error_type: str = Field(..., description="Type of error")
    error_count: int = Field(default=1, ge=1, description="Number of occurrences")
    last_occurrence: datetime = Field(default_factory=lambda: datetime.now(UTC))
    first_occurrence: datetime = Field(default_factory=lambda: datetime.now(UTC))
    severity: str = Field(..., description="Error severity level")
    component: str = Field(..., description="Component where error occurred")
    resolved: bool = Field(default=False, description="Whether error has been resolved")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error_type": "VoiceConnectionError",
                "error_count": 3,
                "severity": "high",
                "component": "audio_service",
                "resolved": False,
            }
        }
    )


# =============================================================================
# API Response Models
# =============================================================================


class APIResponse(BaseModel):
    """Generic API response model"""

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    data: dict[str, Any] | None = Field(None, description="Response data")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    request_id: str | None = Field(None, description="Unique request identifier")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "data": {"result": "success"},
                "request_id": "req_abc123",
            }
        }
    )


class AudioStatusResponse(APIResponse):
    """Audio service status response"""

    playback_state: PlaybackState | None = Field(
        None, description="Current playback state"
    )
    available_reciters: list[str] = Field(
        default_factory=list, description="Available reciters"
    )
    connection_status: str = Field(..., description="Voice connection status")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Audio status retrieved",
                "connection_status": "connected",
                "available_reciters": ["Saad Al Ghamdi", "Mishary Rashid"],
            }
        }
    )


# =============================================================================
# Utility Models
# =============================================================================


class TimeRange(BaseModel):
    """Time range for queries and filters"""

    start_time: datetime = Field(..., description="Start of time range")
    end_time: datetime = Field(..., description="End of time range")

    @property
    def duration_seconds(self) -> float:
        """Calculate duration in seconds"""
        return (self.end_time - self.start_time).total_seconds()

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "start_time": "2024-01-01T00:00:00Z",
                "end_time": "2024-01-01T23:59:59Z",
                "duration_seconds": 86399,
            }
        }
    )


class PaginationParams(BaseModel):
    """Pagination parameters"""

    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        """Calculate offset for database queries"""
        return (self.page - 1) * self.per_page

    model_config = ConfigDict(
        json_schema_extra={"example": {"page": 1, "per_page": 20, "offset": 0}}
    )


class PaginatedResponse(BaseModel):
    """Paginated response wrapper"""

    items: list[Any] = Field(..., description="List of items for current page")
    pagination: dict[str, Any] = Field(..., description="Pagination metadata")

    @classmethod
    def create(cls, items: list[Any], params: PaginationParams, total_count: int):
        """Create paginated response with metadata"""
        total_pages = max(1, (total_count + params.per_page - 1) // params.per_page)

        return cls(
            items=items,
            pagination={
                "page": params.page,
                "per_page": params.per_page,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": params.page < total_pages,
                "has_prev": params.page > 1,
            },
        )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": ["item1", "item2", "item3"],
                "pagination": {
                    "page": 1,
                    "per_page": 20,
                    "total_count": 50,
                    "total_pages": 3,
                    "has_next": True,
                    "has_prev": False,
                },
            }
        }
    )
