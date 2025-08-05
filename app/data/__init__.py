# =============================================================================
# QuranBot - Data Models Package
# =============================================================================
# Comprehensive data models for QuranBot components.
# Provides type-safe, validated data structures for 24/7 operation.
# =============================================================================

# Import data models
from .models import (
    AudioFileInfo, ReciterInfo, SurahInfo, AudioQuality,
    BotState, UserStats, QuizStats, VerseInfo, DuaInfo,
    PlaybackPosition, AudioServiceConfig, PlaybackMode, PlaybackState
)

# Import knowledge base
from .knowledge import ISLAMIC_KNOWLEDGE_BASE

__all__ = [
    # Core models
    'AudioFileInfo',
    'ReciterInfo', 
    'SurahInfo',
    'AudioQuality',
    
    # State models
    'BotState',
    'UserStats',
    'QuizStats',
    
    # Content models
    'VerseInfo',
    'DuaInfo',
    
    # Playback models
    'PlaybackPosition',
    'AudioServiceConfig',
    'PlaybackMode',
    'PlaybackState',
    
    # Knowledge base
    'ISLAMIC_KNOWLEDGE_BASE'
]