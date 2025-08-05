# =============================================================================
# QuranBot - Services Package
# =============================================================================
# Organized service exports for better structure and maintainability
# =============================================================================

# Core Services
from .core.base_service import BaseService, ServiceStatus
from .core.database_service import DatabaseService
from .core.state_service import StateService

# Audio Services
from .audio.audio_service import AudioService
from .audio.metadata_cache import MetadataCache

# AI Services
from .ai.ai_service import AIService
from .ai.islamic_ai_service import IslamicAIService
from .ai.token_tracker import TokenTracker
from .ai.rate_limiter import RateLimiter
from .ai.openai_usage_tracker import OpenAIUsageTracker

# Bot Services
from .bot.presence_service import PresenceService
from .bot.user_interaction_logger import UserInteractionLogger

# Service Groups for better organization
CORE_SERVICES = {
    'database': DatabaseService,
    'state': StateService,
}

AUDIO_SERVICES = {
    'audio': AudioService,
    'metadata_cache': MetadataCache,
}

AI_SERVICES = {
    'ai': AIService,
    'islamic_ai': IslamicAIService,
    'token_tracker': TokenTracker,
    'rate_limiter': RateLimiter,
    'openai_usage': OpenAIUsageTracker,
}

BOT_SERVICES = {
    'presence': PresenceService,
    'user_logger': UserInteractionLogger,
}

# All services combined
ALL_SERVICES = {
    **CORE_SERVICES,
    **AUDIO_SERVICES,
    **AI_SERVICES,
    **BOT_SERVICES,
}

__all__ = [
    # Base
    'BaseService',
    'ServiceStatus',
    
    # Core
    'DatabaseService',
    'StateService',
    
    # Audio
    'AudioService',
    'MetadataCache',
    
    # AI
    'AIService',
    'IslamicAIService',
    'TokenTracker',
    'RateLimiter',
    'OpenAIUsageTracker',
    
    # Bot
    'PresenceService',
    'UserInteractionLogger',
    
    # Groups
    'CORE_SERVICES',
    'AUDIO_SERVICES',
    'AI_SERVICES',
    'BOT_SERVICES',
    'ALL_SERVICES',
]