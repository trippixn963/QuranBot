# =============================================================================
# QuranBot - Core Package
# =============================================================================
# Foundation components for a production-ready Discord bot.
# Provides logging, dependency injection, error handling, and common patterns.
# =============================================================================

from .container import DIContainer
from .errors import (
    AudioError,
    BotError,
    DatabaseError,
    DiscordAPIError,
    ErrorCategory,
    ErrorHandler,
    ErrorSeverity,
    ResourceError,
    ServiceError,
    StateError,
    ValidationError,
)

# Import core components
from .logger import TreeLogger, log_event, setup_logging

__all__ = [
    # Logging
    "TreeLogger",
    "log_event",
    "setup_logging",
    # Error handling
    "BotError",
    "DatabaseError",
    "ServiceError",
    "AudioError",
    "StateError",
    "ResourceError",
    "ValidationError",
    "DiscordAPIError",
    "ErrorSeverity",
    "ErrorCategory",
    "ErrorHandler",
    # Dependency injection
    "DIContainer",
]
