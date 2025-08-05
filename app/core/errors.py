# =============================================================================
# QuranBot - Error Handling System
# =============================================================================
# Comprehensive error handling with categorization, context tracking,
# and user-friendly error messages for robust bot operation.
# =============================================================================

import traceback
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from ..config.timezone import APP_TIMEZONE

from .logger import TreeLogger


class ErrorSeverity(Enum):
    """Error severity levels for categorization and handling."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    FATAL = "fatal"


class ErrorCategory(Enum):
    """Error categories for better organization and handling."""
    # System Errors
    SYSTEM = "system"
    CONFIGURATION = "configuration"
    DEPENDENCY = "dependency"
    
    # Service Errors
    SERVICE = "service"
    DATABASE = "database"
    AUDIO = "audio"
    STATE = "state"
    
    # Network Errors
    NETWORK = "network"
    DISCORD_API = "discord_api"
    VOICE_CONNECTION = "voice_connection"
    
    # User Errors
    USER_INPUT = "user_input"
    PERMISSION = "permission"
    VALIDATION = "validation"
    
    # Resource Errors
    RESOURCE = "resource"
    MEMORY = "memory"
    DISK_SPACE = "disk_space"
    FILE_SYSTEM = "file_system"
    
    # Unknown/Other
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """error context with detailed information."""
    operation: str
    service: Optional[str] = None
    user_id: Optional[int] = None
    guild_id: Optional[int] = None
    channel_id: Optional[int] = None
    severity: ErrorSeverity = ErrorSeverity.ERROR
    category: ErrorCategory = ErrorCategory.UNKNOWN
    retry_count: int = 0
    max_retries: int = 3
    is_recoverable: bool = True
    user_friendly_message: Optional[str] = None
    technical_details: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(APP_TIMEZONE))
    correlation_id: Optional[str] = None
    additional_context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self, service: Optional[str] = None) -> Dict[str, Any]:
        """Convert context to dictionary for logging."""
        result = {
            "operation": self.operation,
            "service": service or self.service,
            "user_id": self.user_id,
            "guild_id": self.guild_id,
            "channel_id": self.channel_id,
            "severity": self.severity.value,
            "category": self.category.value,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "is_recoverable": self.is_recoverable,
            "user_friendly_message": self.user_friendly_message,
            "technical_details": self.technical_details,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "additional_context": self.additional_context
        }
        return result


class BotError(Exception):
    """Base exception class for all bot errors with context."""
    
    def __init__(self, message: str, context: Optional[ErrorContext] = None, 
                 original_error: Optional[Exception] = None,
                 operation: str = "unknown",
                 severity: ErrorSeverity = ErrorSeverity.ERROR,
                 category: ErrorCategory = ErrorCategory.UNKNOWN,
                 service: Optional[str] = None,
                 **kwargs):
        super().__init__(message)
        
        # If context is provided, use it; otherwise create from parameters
        if context is not None:
            self.context = context
        else:
            self.context = ErrorContext(
                operation=operation,
                service=service,
                severity=severity,
                category=category,
                **kwargs
            )
        
        self.original_error = original_error
        self.traceback = traceback.format_exc()
        
        # Generate correlation ID if not provided
        if not self.context.correlation_id:
            self.context.correlation_id = f"err_{int(datetime.now().timestamp())}"
    
    def get_user_message(self) -> str:
        """Get user-friendly error message."""
        if self.context.user_friendly_message:
            return self.context.user_friendly_message
        
        # Generate user-friendly message based on category
        if self.context.category == ErrorCategory.DISCORD_API:
            return "Discord connection issue. Please try again in a moment."
        elif self.context.category == ErrorCategory.VOICE_CONNECTION:
            return "Voice channel connection problem. Please check permissions."
        elif self.context.category == ErrorCategory.DATABASE:
            return "Database operation failed. Please contact support."
        elif self.context.category == ErrorCategory.AUDIO:
            return "Audio playback issue. Please try again."
        elif self.context.category == ErrorCategory.PERMISSION:
            return "You don't have permission to perform this action."
        elif self.context.category == ErrorCategory.VALIDATION:
            return "Invalid input provided. Please check your request."
        else:
            return "An unexpected error occurred. Please try again."
    
    def is_critical(self) -> bool:
        """Check if error is critical (requires immediate attention)."""
        return self.context.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.FATAL]
    
    def is_recoverable(self) -> bool:
        """Check if error is recoverable."""
        return self.context.is_recoverable and self.context.retry_count < self.context.max_retries
    
    def should_retry(self) -> bool:
        """Check if operation should be retried."""
        return self.is_recoverable() and self.context.retry_count < self.context.max_retries


class ServiceError(BotError):
    """Service-specific errors with context."""
    
    def __init__(self, message: str, service_name: str, operation: str = "unknown",
                 severity: ErrorSeverity = ErrorSeverity.ERROR, 
                 is_recoverable: bool = True, **kwargs):
        context = ErrorContext(
            operation=operation,
            service=service_name,
            category=ErrorCategory.SERVICE,
            severity=severity,
            is_recoverable=is_recoverable,
            **kwargs
        )
        super().__init__(message, context)


class DatabaseError(BotError):
    """Database-specific errors with context."""
    
    def __init__(self, message: str, operation: str = "unknown",
                 severity: ErrorSeverity = ErrorSeverity.ERROR,
                 is_recoverable: bool = True, **kwargs):
        context = ErrorContext(
            operation=operation,
            service="DatabaseService",
            category=ErrorCategory.DATABASE,
            severity=severity,
            is_recoverable=is_recoverable,
            **kwargs
        )
        super().__init__(message, context)


class AudioError(BotError):
    """Audio-specific errors with context."""
    
    def __init__(self, message: str, operation: str = "unknown",
                 severity: ErrorSeverity = ErrorSeverity.ERROR,
                 is_recoverable: bool = True, **kwargs):
        context = ErrorContext(
            operation=operation,
            service="AudioService",
            category=ErrorCategory.AUDIO,
            severity=severity,
            is_recoverable=is_recoverable,
            **kwargs
        )
        super().__init__(message, context)


class StateError(BotError):
    """State-specific errors with context."""
    
    def __init__(self, message: str, operation: str = "unknown",
                 severity: ErrorSeverity = ErrorSeverity.ERROR,
                 is_recoverable: bool = True, **kwargs):
        context = ErrorContext(
            operation=operation,
            service="StateService",
            category=ErrorCategory.STATE,
            severity=severity,
            is_recoverable=is_recoverable,
            **kwargs
        )
        super().__init__(message, context)


class ConfigurationError(BotError):
    """Configuration-specific errors with context."""
    
    def __init__(self, message: str, operation: str = "unknown",
                 severity: ErrorSeverity = ErrorSeverity.CRITICAL,
                 is_recoverable: bool = False, **kwargs):
        context = ErrorContext(
            operation=operation,
            service="ConfigurationService",
            category=ErrorCategory.CONFIGURATION,
            severity=severity,
            is_recoverable=is_recoverable,
            **kwargs
        )
        super().__init__(message, context)


class NetworkError(BotError):
    """Network-specific errors with context."""
    
    def __init__(self, message: str, operation: str = "unknown",
                 severity: ErrorSeverity = ErrorSeverity.WARNING,
                 is_recoverable: bool = True, **kwargs):
        context = ErrorContext(
            operation=operation,
            category=ErrorCategory.NETWORK,
            severity=severity,
            is_recoverable=is_recoverable,
            **kwargs
        )
        super().__init__(message, context)


class DiscordAPIError(BotError):
    """Discord API-specific errors with context."""
    
    def __init__(self, message: str, operation: str = "unknown",
                 severity: ErrorSeverity = ErrorSeverity.WARNING,
                 is_recoverable: bool = True, **kwargs):
        context = ErrorContext(
            operation=operation,
            category=ErrorCategory.DISCORD_API,
            severity=severity,
            is_recoverable=is_recoverable,
            **kwargs
        )
        super().__init__(message, context)


class ValidationError(BotError):
    """Validation-specific errors with context."""
    
    def __init__(self, message: str, operation: str = "unknown",
                 severity: ErrorSeverity = ErrorSeverity.INFO,
                 is_recoverable: bool = True, **kwargs):
        context = ErrorContext(
            operation=operation,
            category=ErrorCategory.VALIDATION,
            severity=severity,
            is_recoverable=is_recoverable,
            **kwargs
        )
        super().__init__(message, context)


class PermissionError(BotError):
    """Permission-specific errors with context."""
    
    def __init__(self, message: str, operation: str = "unknown",
                 severity: ErrorSeverity = ErrorSeverity.WARNING,
                 is_recoverable: bool = False, **kwargs):
        context = ErrorContext(
            operation=operation,
            category=ErrorCategory.PERMISSION,
            severity=severity,
            is_recoverable=is_recoverable,
            **kwargs
        )
        super().__init__(message, context)


class ResourceError(BotError):
    """Resource-specific errors with context."""
    
    def __init__(self, message: str, operation: str = "unknown",
                 severity: ErrorSeverity = ErrorSeverity.ERROR,
                 is_recoverable: bool = True, **kwargs):
        context = ErrorContext(
            operation=operation,
            category=ErrorCategory.RESOURCE,
            severity=severity,
            is_recoverable=is_recoverable,
            **kwargs
        )
        super().__init__(message, context)


class ErrorHandler:
    """error handler with categorization, retry logic, and detailed logging."""
    
    def __init__(self, logger=None):
        # Logger parameter is now optional since we use log_event
        self.logger = logger
        self.error_stats = {
            "total_errors": 0,
            "errors_by_category": {},
            "errors_by_severity": {},
            "recovered_errors": 0,
            "critical_errors": 0
        }
        self.retry_strategies = {
            ErrorCategory.NETWORK: {"max_retries": 5, "backoff_factor": 2},
            ErrorCategory.DISCORD_API: {"max_retries": 3, "backoff_factor": 1.5},
            ErrorCategory.DATABASE: {"max_retries": 3, "backoff_factor": 2},
            ErrorCategory.AUDIO: {"max_retries": 2, "backoff_factor": 1.5},
            ErrorCategory.STATE: {"max_retries": 2, "backoff_factor": 1.5}
        }
    
    async def handle_error(self, error: Exception, context: Optional[Dict[str, Any]] = None,
                          operation: Optional[str] = None) -> None:
        """Handle errors with categorization and logging."""
        try:
            # Create error context
            error_context = self._create_error_context(error, context, operation)
            
            # Update error statistics
            self._update_error_stats(error_context)
            
            # Log error with detailed context
            await self._log_error(error, error_context)
            
            # Handle critical errors
            if error_context.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.FATAL]:
                await self._handle_critical_error(error, error_context)
            
            # Log user-friendly message if available
            if error_context.user_friendly_message:
                TreeLogger.success(
                    f"User notification: {error_context.user_friendly_message}",
                    {"correlation_id": error_context.correlation_id}
                , service="ErrorHandler")
                
        except Exception as e:
            # Fallback error handling
            TreeLogger.error("Error in error handler", context={"error": str(e)})
    
    def _create_error_context(self, error: Exception, context: Optional[Dict[str, Any]], 
                            operation: Optional[str]) -> ErrorContext:
        """Create error context from exception and additional context."""
        # Extract operation from context or error
        op = operation or context.get("operation", "unknown") if context else "unknown"
        
        # Determine error category and severity
        category, severity = self._categorize_error(error, context)
        
        # Create error context with valid parameters only
        valid_context_params = {}
        if context:
            # Only include parameters that ErrorContext accepts
            valid_keys = {
                'service', 'user_id', 'guild_id', 'channel_id', 'retry_count', 
                'max_retries', 'is_recoverable', 'user_friendly_message', 
                'technical_details', 'correlation_id'
            }
            valid_context_params = {k: v for k, v in context.items() if k in valid_keys}
            
            # Handle special cases
            if 'service_name' in context:
                valid_context_params['service'] = context['service_name']
        
        error_context = ErrorContext(
            operation=op,
            severity=severity,
            category=category,
            **valid_context_params
        )
        
        # Add technical details
        error_context.technical_details = str(error)
        
        return error_context
    
    def _categorize_error(self, error: Exception, context: Optional[Dict[str, Any]]) -> tuple[ErrorCategory, ErrorSeverity]:
        """
        Categorize error by type and determine appropriate severity level.
        
        This method performs intelligent error categorization by:
        - Analyzing error type and message content
        - Determining appropriate error category
        - Setting severity based on error impact
        - Considering context for better classification
        - Providing consistent error handling across the application
        
        Args:
            error: The exception to categorize
            context: Additional context for better categorization
            
        Returns:
            Tuple of (ErrorCategory, ErrorSeverity) for the error
        """
        error_type = type(error).__name__
        error_message = str(error).lower()
        
        # STEP 1: Network and API Error Detection
        # Check for shutdown-related errors first
        # ClientConnectionResetError during shutdown is expected
        if error_type == "ClientConnectionResetError" and "cannot write to closing transport" in error_message:
            return ErrorCategory.NETWORK, ErrorSeverity.DEBUG
        
        # Check for Discord API and network-related errors first
        # These are typically recoverable and should be retried
        if any(network_error in error_message for network_error in [
            "connection", "timeout", "network", "socket", "dns", "ssl"
        ]) or error_type in ["ConnectionError", "TimeoutError", "socket.error"]:
            return ErrorCategory.NETWORK, ErrorSeverity.WARNING
        
        # STEP 2: Discord API Error Detection
        # Identify Discord-specific API errors
        # These often indicate temporary API issues
        if any(discord_error in error_message for discord_error in [
            "discord", "api", "rate limit", "forbidden", "not found", "unauthorized"
        ]) or error_type in ["HTTPException", "Forbidden", "NotFound"]:
            return ErrorCategory.DISCORD_API, ErrorSeverity.WARNING
        
        # STEP 3: Voice Connection Error Detection
        # Identify voice channel and audio-related errors
        # These are critical for audio bot functionality
        if any(voice_error in error_message for voice_error in [
            "voice", "audio", "playback", "channel", "guild", "permission"
        ]) or error_type in ["VoiceError", "AudioError"]:
            return ErrorCategory.VOICE_CONNECTION, ErrorSeverity.ERROR
        
        # STEP 4: Database and State Error Detection
        # Identify data persistence and state management errors
        # These affect bot state recovery and persistence
        if any(db_error in error_message for db_error in [
            "database", "sql", "state", "file", "json", "corruption"
        ]) or error_type in ["DatabaseError", "StateError", "JSONDecodeError"]:
            return ErrorCategory.DATABASE, ErrorSeverity.ERROR
        
        # STEP 5: Configuration Error Detection
        # Identify configuration and setup-related errors
        # These are critical as they prevent bot startup
        if any(config_error in error_message for config_error in [
            "config", "environment", "token", "guild", "channel", "missing"
        ]) or error_type in ["ConfigurationError", "KeyError", "ValueError"]:
            return ErrorCategory.CONFIGURATION, ErrorSeverity.CRITICAL
        
        # STEP 6: Permission and User Input Error Detection
        # Identify permission and user interaction errors
        # These are typically user-facing issues
        if any(perm_error in error_message for perm_error in [
            "permission", "access", "denied", "forbidden", "unauthorized"
        ]) or error_type in ["PermissionError", "AccessDenied"]:
            return ErrorCategory.PERMISSION, ErrorSeverity.WARNING
        
        # STEP 7: Validation Error Detection
        # Identify data validation and format errors
        # These are usually recoverable with proper input
        if any(validation_error in error_message for validation_error in [
            "validation", "invalid", "format", "type", "range", "length"
        ]) or error_type in ["ValidationError", "TypeError", "ValueError"]:
            return ErrorCategory.VALIDATION, ErrorSeverity.INFO
        
        # STEP 8: Resource Error Detection
        # Identify resource and system-level errors
        # These may indicate system issues
        if any(resource_error in error_message for resource_error in [
            "memory", "disk", "space", "resource", "file", "io"
        ]) or error_type in ["MemoryError", "OSError", "IOError"]:
            return ErrorCategory.RESOURCE, ErrorSeverity.ERROR
        
        # STEP 9: Service Error Detection
        # Identify service-specific errors
        # These are internal service issues
        if any(service_error in error_message for service_error in [
            "service", "initialization", "startup", "shutdown", "cleanup"
        ]) or error_type in ["ServiceError", "RuntimeError"]:
            return ErrorCategory.SERVICE, ErrorSeverity.ERROR
        
        # STEP 10: Context-Aware Categorization
        # Use additional context to improve categorization
        if context:
            # Check for specific service context
            service_name = context.get("service_name", "").lower()
            if "audio" in service_name:
                return ErrorCategory.AUDIO, ErrorSeverity.ERROR
            elif "state" in service_name:
                return ErrorCategory.STATE, ErrorSeverity.ERROR
            elif "database" in service_name:
                return ErrorCategory.DATABASE, ErrorSeverity.ERROR
            
            # Check for operation-specific context
            operation = context.get("operation", "").lower()
            if "voice" in operation or "audio" in operation:
                return ErrorCategory.VOICE_CONNECTION, ErrorSeverity.ERROR
            elif "config" in operation or "setup" in operation:
                return ErrorCategory.CONFIGURATION, ErrorSeverity.CRITICAL
        
        # STEP 11: Default Categorization
        # Fallback to unknown category for unrecognized errors
        # This ensures all errors are handled consistently
        return ErrorCategory.UNKNOWN, ErrorSeverity.ERROR
    
    def _update_error_stats(self, error_context: ErrorContext) -> None:
        """Update error statistics."""
        self.error_stats["total_errors"] += 1
        
        # Update category stats
        category = error_context.category.value
        self.error_stats["errors_by_category"][category] = \
            self.error_stats["errors_by_category"].get(category, 0) + 1
        
        # Update severity stats
        severity = error_context.severity.value
        self.error_stats["errors_by_severity"][severity] = \
            self.error_stats["errors_by_severity"].get(severity, 0) + 1
        
        # Update critical errors count
        if error_context.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.FATAL]:
            self.error_stats["critical_errors"] += 1
    
    async def _log_error(self, error: Exception, error_context: ErrorContext) -> None:
        """Log error with detailed context."""
        log_context = {
            **error_context.to_dict(),
            "error_type": type(error).__name__,
            "traceback": traceback.format_exc()
        }
        
        # Use appropriate log level based on severity
        if error_context.severity == ErrorSeverity.DEBUG:
            TreeLogger.debug(
                f"Expected error in {error_context.operation}: {str(error)}",
                context={k: v for k, v in log_context.items() if k != "traceback"}
            )
        else:
            # Use TreeLogger.print_error for robust error logging
            TreeLogger.error(
                f"Error in {error_context.operation}: {str(error)}",
                context=log_context
            )
    
    def _get_log_level(self, severity: ErrorSeverity) -> str:
        """Get log level based on error severity."""
        severity_map = {
            ErrorSeverity.DEBUG: "debug",
            ErrorSeverity.INFO: "info",
            ErrorSeverity.WARNING: "warning",
            ErrorSeverity.ERROR: "error",
            ErrorSeverity.CRITICAL: "error",
            ErrorSeverity.FATAL: "error"
        }
        return severity_map.get(severity, "error")
    
    async def _handle_critical_error(self, error: Exception, error_context: ErrorContext) -> None:
        """Handle critical errors with immediate attention."""
        TreeLogger.error(
            f"CRITICAL ERROR: {error_context.operation}",
            context={
                **error_context.to_dict(service="ErrorHandler"),
                "requires_immediate_attention": True,
                "bot_restart_recommended": error_context.severity == ErrorSeverity.FATAL
            }
        )
    
    async def safe_execute(self, operation: Callable, context: Dict[str, Any],
                          max_retries: int = 3, backoff_factor: float = 1.5) -> Any:
        """
        Execute operation with comprehensive retry logic and error handling.
        
        This method performs robust operation execution including:
        - Async/sync operation detection and execution
        - Exponential backoff retry strategy
        - Error context creation and tracking
        - Retry decision logic and timing
        - Comprehensive error logging and recovery
        - Performance monitoring and metrics
        
        Args:
            operation: Function to execute (async or sync)
            context: Additional context for error handling
            max_retries: Maximum number of retry attempts
            backoff_factor: Exponential backoff multiplier
            
        Returns:
            Result of the operation if successful
            
        Raises:
            Exception: If operation fails after all retries
        """
        last_error = None
        
        # STEP 1: Retry Loop with Exponential Backoff
        # Attempt operation multiple times with increasing delays
        # This handles transient failures and network issues
        for attempt in range(max_retries + 1):
            try:
                # STEP 2: Async/Sync Operation Detection and Execution
                # Detect operation type and execute accordingly
                # This handles both async and sync operations seamlessly
                if asyncio.iscoroutinefunction(operation):
                    return await operation()
                else:
                    return operation()
                    
            except Exception as e:
                # STEP 3: Error Tracking and Context Creation
                # Track the last error and create comprehensive error context
                # This provides detailed debugging information
                last_error = e
                
                # STEP 4: Error Context Creation with Retry Information
                # Create detailed error context for logging and debugging
                # This includes retry attempt information and operation details
                error_context = ErrorContext(
                    operation=context.get("operation", "unknown"),
                    retry_count=attempt,
                    max_retries=max_retries,
                    **{k: v for k, v in context.items() if k != "operation"}
                )
                
                # STEP 5: Retry Decision Logic and Timing
                # Determine if operation should be retried based on error type
                # This prevents unnecessary retries for permanent failures
                if attempt < max_retries and self._should_retry(e, error_context):
                    TreeLogger.error(
                        f"Retrying {error_context.operation} (attempt {attempt + 1}/{max_retries + 1})",
                        None,
                        {
                            **error_context.to_dict(),
                            "retry_delay": backoff_factor ** attempt
                        },
                        service="ErrorHandler"
                    )
                    
                    # STEP 6: Exponential Backoff Wait
                    # Wait with exponential backoff before retry
                    # This prevents overwhelming the system with rapid retries
                    await asyncio.sleep(backoff_factor ** attempt)
                    continue
                else:
                    # STEP 7: Final Error Handling and Logging
                    # Log final error and raise exception
                    # This provides comprehensive error information for debugging
                    await self.handle_error(e, context)
                    raise
        
        # STEP 8: All Retries Exhausted
        # If we get here, all retries failed
        # This ensures the last error is properly raised
        if last_error:
            raise last_error
    
    def _should_retry(self, error: Exception, error_context: ErrorContext) -> bool:
        """Determine if error should be retried."""
        # Don't retry critical errors
        if error_context.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.FATAL]:
            return False
        
        # Don't retry non-recoverable errors
        if not error_context.is_recoverable:
            return False
        
        # Don't retry permission errors
        if error_context.category == ErrorCategory.PERMISSION:
            return False
        
        # Don't retry validation errors
        if error_context.category == ErrorCategory.VALIDATION:
            return False
        
        return True
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get current error statistics."""
        return {
            **self.error_stats,
            "error_rate": self._calculate_error_rate(),
            "recovery_rate": self._calculate_recovery_rate()
        }
    
    def _calculate_error_rate(self) -> float:
        """Calculate error rate (errors per minute)."""
        # This would need to be implemented with time tracking
        return 0.0
    
    def _calculate_recovery_rate(self) -> float:
        """Calculate error recovery rate."""
        if self.error_stats["total_errors"] == 0:
            return 100.0
        
        return (self.error_stats["recovered_errors"] / self.error_stats["total_errors"]) * 100