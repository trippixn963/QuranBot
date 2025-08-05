# =============================================================================
# QuranBot - Data Models Package
# =============================================================================
# Comprehensive data models for QuranBot components.
# Provides type-safe, validated data structures for 24/7 operation.
# =============================================================================

# Import knowledge base
from .knowledge import ISLAMIC_KNOWLEDGE_BASE

# Import data models
from .models import (
    AudioFileInfo,
    AudioQuality,
    AudioServiceConfig,
    BotState,
    DuaInfo,
    PlaybackMode,
    PlaybackPosition,
    PlaybackState,
    QuizStats,
    ReciterInfo,
    SurahInfo,
    UserStats,
    VerseInfo,
)

__all__ = [
    # Core models
    "AudioFileInfo",
    "ReciterInfo",
    "SurahInfo",
    "AudioQuality",
    # State models
    "BotState",
    "UserStats",
    "QuizStats",
    # Content models
    "VerseInfo",
    "DuaInfo",
    # Playback models
    "PlaybackPosition",
    "AudioServiceConfig",
    "PlaybackMode",
    "PlaybackState",
    # Knowledge base
    "ISLAMIC_KNOWLEDGE_BASE",
]
