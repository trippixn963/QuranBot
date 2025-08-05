# =============================================================================
# QuranBot - Core Package  
# =============================================================================
# Foundation components for a production-ready Discord bot.
# Provides logging, dependency injection, error handling, and common patterns.
# =============================================================================

# Import core components
from .logger import TreeLogger, log_event, setup_logging
from .errors import (
    BotError, DatabaseError, ServiceError, AudioError, 
    StateError, ResourceError, ValidationError, DiscordAPIError,
    ErrorSeverity, ErrorCategory, ErrorHandler
)
from .container import DIContainer

__all__ = [
    # Logging
    'TreeLogger',
    'log_event',
    'setup_logging',
    
    # Error handling
    'BotError',
    'DatabaseError',
    'ServiceError', 
    'AudioError',
    'StateError',
    'ResourceError',
    'ValidationError',
    'DiscordAPIError',
    'ErrorSeverity',
    'ErrorCategory', 
    'ErrorHandler',
    
    # Dependency injection
    'DIContainer'
]