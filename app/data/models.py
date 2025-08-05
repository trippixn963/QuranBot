# =============================================================================
# QuranBot - Production Data Models
# =============================================================================
# Type-safe, validated data models for all QuranBot components.
# Designed for corruption-proof 24/7 operation with comprehensive validation.
#
# Features:
# - Pydantic validation for data integrity
# - JSON serialization for database storage
# - Immutable data structures where appropriate
# - Clear field documentation and constraints
# - Migration-friendly design
# =============================================================================

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# Import centralized timezone configuration
from ..config.timezone import APP_TIMEZONE as EST

# =============================================================================
# Audio System Models
# =============================================================================


class PlaybackMode(str, Enum):
    """Audio playback modes."""

    SEQUENTIAL = "sequential"  # Play surahs in order
    SHUFFLE = "shuffle"  # Random surah order
    REPEAT_ONE = "repeat_one"  # Repeat current surah
    REPEAT_ALL = "repeat_all"  # Repeat all surahs


class PlaybackState(str, Enum):
    """Current playback states."""

    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    BUFFERING = "buffering"
    ERROR = "error"


class AudioQuality(str, Enum):
    """Audio quality presets."""

    LOW = "64k"
    MEDIUM = "128k"
    HIGH = "320k"


class ReciterInfo(BaseModel):
    """Information about a Quran reciter."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., description="Reciter's name in English")
    arabic_name: str = Field(..., description="Reciter's name in Arabic")
    directory: str = Field(..., description="Audio directory name")
    total_surahs: int = Field(
        default=114, ge=1, le=114, description="Total surahs available"
    )
    available_surahs: list[int] = Field(
        default_factory=list, description="List of available surah numbers"
    )
    audio_quality: AudioQuality = Field(
        default=AudioQuality.HIGH, description="Audio quality"
    )

    def has_surah(self, surah_number: int) -> bool:
        """Check if this reciter has a specific surah."""
        return (
            surah_number in self.available_surahs
            if self.available_surahs
            else 1 <= surah_number <= 114
        )


class AudioFileInfo(BaseModel):
    """Metadata for an audio file."""

    model_config = ConfigDict(frozen=True)

    file_path: str = Field(..., description="Full path to audio file")
    file_size: int = Field(..., ge=0, description="File size in bytes")
    duration_seconds: float = Field(..., ge=0.0, description="Duration in seconds")
    reciter: str = Field(..., description="Reciter name")
    surah_number: int = Field(..., ge=1, le=114, description="Surah number")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(EST), description="File creation time"
    )
    last_accessed: datetime = Field(
        default_factory=lambda: datetime.now(EST), description="Last access time"
    )

    def update_access_time(self) -> "AudioFileInfo":
        """Return new instance with updated access time."""
        return self.model_copy(update={"last_accessed": datetime.now(EST)})


class PlaybackPosition(BaseModel):
    """Current playback position information."""

    surah: int = Field(..., ge=1, le=114, description="Current surah number")
    position_seconds: float = Field(
        default=0.0, ge=0.0, description="Position within current surah in seconds"
    )
    total_duration_seconds: float | None = Field(
        default=0.0, ge=0.0, description="Total duration of current surah"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(EST),
        description="When this position was recorded",
    )

    @property
    def progress_percentage(self) -> float:
        """Get playback progress as percentage (0-100)."""
        if not self.total_duration_seconds or self.total_duration_seconds <= 0:
            return 0.0
        return min(100.0, (self.position_seconds / self.total_duration_seconds) * 100.0)

    @property
    def remaining_seconds(self) -> float:
        """Get remaining time in current surah."""
        if not self.total_duration_seconds:
            return 0.0
        return max(0.0, self.total_duration_seconds - self.position_seconds)


class AudioServiceConfig(BaseModel):
    """Configuration for the audio service."""

    audio_base_folder: Path = Field(
        default=Path("audio"), description="Base audio directory"
    )
    ffmpeg_path: Path = Field(
        default=Path("/opt/homebrew/bin/ffmpeg"), description="FFmpeg executable path"
    )
    default_volume: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Default audio volume"
    )
    default_reciter: str = Field(
        default="Saad Al Ghamdi", description="Default reciter name"
    )
    connection_timeout: float = Field(
        default=30.0, ge=5.0, description="Voice connection timeout"
    )
    playback_timeout: float = Field(
        default=300.0, ge=60.0, description="Playback operation timeout"
    )
    max_retry_attempts: int = Field(
        default=3, ge=1, le=10, description="Maximum retry attempts"
    )
    retry_delay: float = Field(default=1.0, ge=0.1, description="Delay between retries")
    ffmpeg_options: dict[str, Any] = Field(
        default_factory=dict, description="Additional FFmpeg options"
    )
    reconnect_attempts: int = Field(
        default=5, ge=1, description="Voice reconnection attempts"
    )
    reconnect_delay: float = Field(
        default=2.0, ge=0.5, description="Delay between reconnection attempts"
    )
    auto_resume: bool = Field(
        default=True, description="Automatically resume after disconnection"
    )
    continuous_play: bool = Field(
        default=True, description="Enable continuous audio playback"
    )
    cache_enabled: bool = Field(default=True, description="Enable metadata caching")
    preload_metadata: bool = Field(
        default=True, description="Preload metadata on startup"
    )
    playback_buffer_size: int = Field(
        default=1024, ge=512, le=8192, description="Audio buffer size"
    )
    enable_reconnection: bool = Field(
        default=True, description="Enable automatic reconnection"
    )


# =============================================================================
# Bot State Models
# =============================================================================


class BotState(BaseModel):
    """Global bot state information."""

    guild_id: int = Field(..., description="Discord guild ID")
    voice_channel_id: int | None = Field(None, description="Current voice channel ID")
    panel_channel_id: int | None = Field(None, description="Control panel channel ID")
    current_reciter: str = Field(..., description="Currently selected reciter")
    playback_mode: PlaybackMode = Field(
        default=PlaybackMode.SEQUENTIAL, description="Current playback mode"
    )
    playback_state: PlaybackState = Field(
        default=PlaybackState.STOPPED, description="Current playback state"
    )
    current_position: PlaybackPosition = Field(
        default_factory=lambda: PlaybackPosition(surah=1),
        description="Current playback position",
    )
    volume: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Current volume level"
    )
    loop_enabled: bool = Field(default=False, description="Loop mode enabled")
    shuffle_enabled: bool = Field(default=False, description="Shuffle mode enabled")
    last_activity: datetime = Field(
        default_factory=lambda: datetime.now(EST), description="Last bot activity"
    )

    def update_activity(self) -> "BotState":
        """Update last activity timestamp."""
        return self.model_copy(update={"last_activity": datetime.now(EST)})


class UserStats(BaseModel):
    """User statistics and achievements."""

    user_id: int = Field(..., description="Discord user ID")
    username: str = Field(..., description="Discord username")
    quiz_points: int = Field(default=0, ge=0, description="Total quiz points earned")
    quiz_correct: int = Field(default=0, ge=0, description="Correct quiz answers")
    quiz_total: int = Field(default=0, ge=0, description="Total quiz attempts")
    favorite_reciter: str | None = Field(None, description="User's favorite reciter")
    total_listening_time: float = Field(
        default=0.0, ge=0.0, description="Total listening time in seconds"
    )
    streak_days: int = Field(default=0, ge=0, description="Current daily streak")
    achievements: list[str] = Field(
        default_factory=list, description="Unlocked achievements"
    )
    first_seen: datetime = Field(
        default_factory=lambda: datetime.now(EST), description="First interaction date"
    )
    last_seen: datetime = Field(
        default_factory=lambda: datetime.now(EST), description="Last interaction date"
    )

    @property
    def quiz_accuracy(self) -> float:
        """Calculate quiz accuracy percentage."""
        if self.quiz_total == 0:
            return 0.0
        return (self.quiz_correct / self.quiz_total) * 100.0

    @property
    def listening_hours(self) -> float:
        """Get total listening time in hours."""
        return self.total_listening_time / 3600.0

    def add_quiz_result(self, correct: bool) -> "UserStats":
        """Add a quiz result and return updated stats."""
        return self.model_copy(
            update={
                "quiz_total": self.quiz_total + 1,
                "quiz_correct": self.quiz_correct + (1 if correct else 0),
                "quiz_points": self.quiz_points + (10 if correct else 0),
                "last_seen": datetime.now(EST),
            }
        )


class QuizStats(BaseModel):
    """Quiz system statistics."""

    total_questions_asked: int = Field(
        default=0, ge=0, description="Total questions asked"
    )
    total_correct_answers: int = Field(
        default=0, ge=0, description="Total correct answers"
    )
    total_participants: int = Field(
        default=0, ge=0, description="Total unique participants"
    )
    average_accuracy: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Overall accuracy percentage"
    )
    most_difficult_question: str | None = Field(
        None, description="Question with lowest accuracy"
    )
    easiest_question: str | None = Field(
        None, description="Question with highest accuracy"
    )
    last_reset: datetime = Field(
        default_factory=lambda: datetime.now(EST), description="Last statistics reset"
    )


# =============================================================================
# Content Models
# =============================================================================


class SurahInfo(BaseModel):
    """Information about a Quran surah."""

    model_config = ConfigDict(frozen=True)

    number: int = Field(..., ge=1, le=114, description="Surah number")
    name_arabic: str = Field(..., description="Surah name in Arabic")
    name_english: str = Field(..., description="Surah name in English")
    meaning: str = Field(..., description="Meaning of the surah name")
    verses_count: int = Field(..., ge=1, description="Number of verses")
    revelation_type: str = Field(..., description="Meccan or Medinan")
    revelation_order: int = Field(..., ge=1, le=114, description="Order of revelation")

    @property
    def is_meccan(self) -> bool:
        """Check if this surah is Meccan."""
        return self.revelation_type.lower() == "meccan"

    @property
    def is_medinan(self) -> bool:
        """Check if this surah is Medinan."""
        return self.revelation_type.lower() == "medinan"


class VerseInfo(BaseModel):
    """Information about a Quran verse."""

    model_config = ConfigDict(frozen=True)

    surah_number: int = Field(..., ge=1, le=114, description="Surah number")
    verse_number: int = Field(..., ge=1, description="Verse number within surah")
    arabic_text: str = Field(..., description="Arabic text of the verse")
    english_translation: str = Field(..., description="English translation")
    transliteration: str | None = Field(None, description="Transliteration")
    revelation_context: str | None = Field(None, description="Context of revelation")

    @property
    def verse_id(self) -> str:
        """Get unique verse identifier (surah:verse)."""
        return f"{self.surah_number}:{self.verse_number}"


class DuaInfo(BaseModel):
    """Information about Islamic supplications (duas)."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Unique dua identifier")
    title: str = Field(..., description="Dua title/name")
    category: str = Field(..., description="Dua category (morning, evening, etc.)")
    arabic_text: str = Field(..., description="Arabic text of the dua")
    english_translation: str = Field(..., description="English translation")
    transliteration: str = Field(..., description="Transliteration")
    source: str = Field(..., description="Source (Quran, Hadith, etc.)")
    benefits: str | None = Field(None, description="Benefits of reciting this dua")
    timing: str | None = Field(None, description="Recommended timing")

    @property
    def is_morning_dua(self) -> bool:
        """Check if this is a morning dua."""
        return "morning" in self.category.lower()

    @property
    def is_evening_dua(self) -> bool:
        """Check if this is an evening dua."""
        return "evening" in self.category.lower()


# =============================================================================
# Utility Functions
# =============================================================================


def create_default_bot_state(guild_id: int, voice_channel_id: int) -> BotState:
    """Create a default bot state for a server."""
    from ..config import get_config

    config = get_config()

    # Get string value from config's default reciter enum
    default_reciter_str = (
        str(config.default_reciter.value)
        if hasattr(config.default_reciter, "value")
        else str(config.default_reciter)
    )

    bot_state = BotState(
        guild_id=guild_id,
        voice_channel_id=voice_channel_id,
        current_reciter=default_reciter_str,
        playback_mode=PlaybackMode.SEQUENTIAL,
        playback_state=PlaybackState.STOPPED,
        current_position=PlaybackPosition(surah=1),
    )

    return bot_state


def create_new_user_stats(user_id: int, username: str) -> UserStats:
    """Create new user statistics entry."""
    user_stats = UserStats(user_id=user_id, username=username)

    return user_stats
