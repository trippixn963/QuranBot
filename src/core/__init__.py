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
from .health_monitor import HealthMonitor
from .heartbeat_monitor import HeartbeatMonitor
from .database import DatabaseManager

# New optimization modules
from .log_optimizer import OptimizedLogManager, BatchedLogWriter, LogCompressor
from .unified_scheduler import UnifiedTaskScheduler, TaskPriority, LegacyTaskMigrator
from .memory_optimizer import AdvancedMemoryOptimizer, ObjectPool, SmartGarbageCollector
from .smart_imports import SmartImportManager, LazyModule, ImportAnalyzer
from .discord_optimizer import DiscordOptimizer, SmartRateLimiter, ConnectionPool

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
