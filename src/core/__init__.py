# =============================================================================
# QuranBot - Core Module
# =============================================================================
# Core module for QuranBot containing fundamental architectural components.
# This module provides the core infrastructure components that support
# the modernized QuranBot architecture, including dependency injection
# and service management.
# =============================================================================

from .di_container import DIContainer
from .exceptions import *
from .security import (
    InputValidator,
    RateLimiter,
    SecurityService,
    rate_limit,
    require_admin,
    validate_input,
)
from .structured_logger import (
    LoggingService,
    StructuredFormatter,
    StructuredLogger,
    correlation_id,
    create_correlation_context,
    get_logging_service,
    log_with_correlation,
    set_logging_service,
)

__all__ = [
    "DIContainer",
    "StructuredLogger",
    "StructuredFormatter",
    "LoggingService",
    "correlation_id",
    "log_with_correlation",
    "create_correlation_context",
    "get_logging_service",
    "set_logging_service",
    "RateLimiter",
    "SecurityService",
    "InputValidator",
    "rate_limit",
    "require_admin",
    "validate_input",
    # All exceptions from exceptions.py
    "QuranBotError",
    "AudioError",
    "ConfigurationError",
    "StateError",
    "ValidationError",
    "RateLimitError",
    "DiscordAPIError",
    "WebhookError",
    "QuizError",
    "ServiceError",
    "SecurityError",
    "handle_errors",
]
