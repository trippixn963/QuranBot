# =============================================================================
# QuranBot - Core Module
# =============================================================================
# Core module for QuranBot containing fundamental architectural components.
# This module provides the core infrastructure components that support
# the modernized QuranBot architecture, including dependency injection
# and service management.
# =============================================================================

from .database import DatabaseManager
from .di_container import DIContainer
from .discord_optimizer import ConnectionPool, DiscordOptimizer, SmartRateLimiter
from .exceptions import *
from .health_monitor import HealthMonitor
from .heartbeat_monitor import HeartbeatMonitor

# New optimization modules
from .log_optimizer import BatchedLogWriter, LogCompressor, OptimizedLogManager
from .logger import (
    LoggingService,
    StructuredFormatter,
    StructuredLogger,
    correlation_id,
    create_correlation_context,
    get_logging_service,
    log_with_correlation,
    set_logging_service,
)
from .memory_optimizer import AdvancedMemoryOptimizer, ObjectPool, SmartGarbageCollector
from .scheduler import LegacyTaskMigrator, TaskPriority, UnifiedTaskScheduler
from .security import (
    InputValidator,
    RateLimiter,
    SecurityService,
    rate_limit,
    require_admin,
    validate_input,
)
from .smart_imports import ImportAnalyzer, LazyModule, SmartImportManager

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
    "DatabaseError",
    "handle_errors",
    "HealthMonitor",
    "HeartbeatMonitor",
    "DatabaseManager",
    # New optimization exports
    "OptimizedLogManager",
    "BatchedLogWriter",
    "LogCompressor",
    "UnifiedTaskScheduler",
    "TaskPriority",
    "LegacyTaskMigrator",
    "AdvancedMemoryOptimizer",
    "ObjectPool",
    "SmartGarbageCollector",
    "SmartImportManager",
    "LazyModule",
    "ImportAnalyzer",
    "DiscordOptimizer",
    "SmartRateLimiter",
    "ConnectionPool",
]
