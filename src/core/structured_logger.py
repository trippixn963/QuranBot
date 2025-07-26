# =============================================================================
# QuranBot - Structured Logging System
# =============================================================================
# This module provides a modern structured logging system with JSON formatting,
# correlation ID context management, and async support for the QuranBot
# modernization project.
#
# Key Features:
# - JSON-formatted structured logging
# - Correlation ID context management using contextvars
# - Async logging support
# - Configurable log levels and filtering
# - Type-safe logging with context data
# - Integration with existing Discord logging
# =============================================================================

import asyncio
from contextvars import ContextVar
from datetime import UTC, datetime
import json
import logging
from pathlib import Path
import sys
from typing import Any
import uuid

# Context variable for correlation ID tracking
correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for structured logging output.

    This formatter converts log records into structured JSON format
    with consistent fields for timestamp, level, message, correlation ID,
    and additional context data.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record as structured JSON.

        Args:
            record: The log record to format

        Returns:
            JSON-formatted log string
        """
        # Get correlation ID from context
        corr_id = correlation_id.get() or str(uuid.uuid4())[:8]

        # Build structured log entry
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": corr_id,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add context data if present
        if hasattr(record, "context") and record.context:
            log_entry["context"] = record.context

        # Add exception info if present
        if record.exc_info and record.exc_info != (None, None, None):
            exc_type, exc_value, exc_traceback = record.exc_info
            log_entry["exception"] = {
                "type": exc_type.__name__ if exc_type else None,
                "message": str(exc_value) if exc_value else None,
                "traceback": (
                    self.formatException(record.exc_info) if record.exc_info else None
                ),
            }

        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "getMessage",
                "exc_info",
                "exc_text",
                "stack_info",
                "context",
            ]:
                log_entry[key] = value

        return json.dumps(log_entry, default=str, ensure_ascii=False)


class StructuredLogger:
    """
    Modern structured logger with JSON formatting and correlation ID support.

    This logger provides async-compatible structured logging with consistent
    JSON output format, correlation ID tracking, and configurable filtering.
    It's designed to replace the existing logging patterns in QuranBot with
    a more maintainable and searchable logging system.
    """

    def __init__(
        self,
        name: str,
        level: int | str = logging.INFO,
        log_file: Path | None = None,
        console_output: bool = True,
    ):
        """
        Initialize the structured logger.

        Args:
            name: Logger name (typically module name)
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Optional file path for log output
            console_output: Whether to output to console
        """
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)

        # Clear any existing handlers to avoid duplicates
        self._logger.handlers.clear()

        # Setup structured formatter
        formatter = StructuredFormatter()

        # Add console handler if requested
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self._logger.addHandler(console_handler)

        # Add file handler if specified
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)

    def set_correlation_id(self, corr_id: str | None = None) -> str:
        """
        Set correlation ID for request tracking.

        Args:
            corr_id: Optional correlation ID, generates new one if None

        Returns:
            The correlation ID that was set
        """
        if corr_id is None:
            corr_id = str(uuid.uuid4())

        correlation_id.set(corr_id)
        return corr_id

    def get_correlation_id(self) -> str:
        """
        Get current correlation ID.

        Returns:
            Current correlation ID or empty string if not set
        """
        return correlation_id.get()

    async def debug(self, message: str, context: dict[str, Any] | None = None) -> None:
        """
        Log debug message with optional context.

        Args:
            message: Log message
            context: Optional context data dictionary
        """
        await self._log(logging.DEBUG, message, context)

    async def info(self, message: str, context: dict[str, Any] | None = None) -> None:
        """
        Log info message with optional context.

        Args:
            message: Log message
            context: Optional context data dictionary
        """
        await self._log(logging.INFO, message, context)

    async def warning(
        self, message: str, context: dict[str, Any] | None = None
    ) -> None:
        """
        Log warning message with optional context.

        Args:
            message: Log message
            context: Optional context data dictionary
        """
        await self._log(logging.WARNING, message, context)

    async def error(
        self,
        message: str,
        context: dict[str, Any] | None = None,
        exc_info: bool = False,
    ) -> None:
        """
        Log error message with optional context and exception info.

        Args:
            message: Log message
            context: Optional context data dictionary
            exc_info: Whether to include exception information
        """
        await self._log(logging.ERROR, message, context, exc_info=exc_info)

    async def critical(
        self,
        message: str,
        context: dict[str, Any] | None = None,
        exc_info: bool = False,
    ) -> None:
        """
        Log critical message with optional context and exception info.

        Args:
            message: Log message
            context: Optional context data dictionary
            exc_info: Whether to include exception information
        """
        await self._log(logging.CRITICAL, message, context, exc_info=exc_info)

    async def _log(
        self,
        level: int,
        message: str,
        context: dict[str, Any] | None = None,
        exc_info: bool = False,
    ) -> None:
        """
        Internal async logging method.

        Args:
            level: Logging level
            message: Log message
            context: Optional context data
            exc_info: Whether to include exception information
        """
        # Capture current context including correlation ID and exception info
        current_correlation_id = correlation_id.get()
        exception_info = None
        if exc_info:
            exception_info = sys.exc_info()
            # Only include if there's actually an exception
            if exception_info == (None, None, None):
                exception_info = None

        # Run logging in thread pool to avoid blocking
        loop = asyncio.get_event_loop()

        await loop.run_in_executor(
            None,
            self._sync_log,
            level,
            message,
            context,
            exception_info,
            current_correlation_id,
        )

    def _sync_log(
        self,
        level: int,
        message: str,
        context: dict[str, Any] | None = None,
        exception_info: tuple | None = None,
        corr_id: str | None = None,
    ) -> None:
        """
        Synchronous logging implementation.

        Args:
            level: Logging level
            message: Log message
            context: Optional context data
            exception_info: Pre-captured exception information tuple
            corr_id: Correlation ID to set in context
        """
        # Set correlation ID in context if provided
        if corr_id:
            correlation_id.set(corr_id)

        # Create log record with context
        record = self._logger.makeRecord(
            name=self._logger.name,
            level=level,
            fn="",
            lno=0,
            msg=message,
            args=(),
            exc_info=exception_info,
        )

        # Add context to record
        if context:
            record.context = context

        # Handle the record
        self._logger.handle(record)


class LoggingService:
    """
    Centralized logging service for dependency injection.

    This service provides a single point of access to structured logging
    throughout the application, with support for different logger instances
    and consistent configuration.
    """

    def __init__(
        self,
        default_level: int | str = logging.INFO,
        log_directory: Path | None = None,
        console_output: bool = True,
    ):
        """
        Initialize the logging service.

        Args:
            default_level: Default logging level for new loggers
            log_directory: Directory for log files
            console_output: Whether to enable console output
        """
        self._default_level = default_level
        self._log_directory = log_directory or Path("logs")
        self._console_output = console_output
        self._loggers: dict[str, StructuredLogger] = {}

        # Ensure log directory exists
        self._log_directory.mkdir(parents=True, exist_ok=True)

    def get_logger(
        self,
        name: str,
        level: int | str | None = None,
        log_file: str | None = None,
    ) -> StructuredLogger:
        """
        Get or create a structured logger instance.

        Args:
            name: Logger name
            level: Optional logging level override
            log_file: Optional log file name (relative to log directory)

        Returns:
            StructuredLogger instance
        """
        if name not in self._loggers:
            # Determine log file path
            file_path = None
            if log_file:
                file_path = self._log_directory / log_file
            elif self._log_directory:
                # Create default log file based on logger name
                safe_name = name.replace(".", "_").replace("/", "_")
                file_path = self._log_directory / f"{safe_name}.log"

            # Create logger
            self._loggers[name] = StructuredLogger(
                name=name,
                level=level or self._default_level,
                log_file=file_path,
                console_output=self._console_output,
            )

        return self._loggers[name]

    def set_global_level(self, level: int | str) -> None:
        """
        Set logging level for all existing loggers.

        Args:
            level: New logging level
        """
        self._default_level = level
        for logger in self._loggers.values():
            logger._logger.setLevel(level)

    async def shutdown(self) -> None:
        """
        Shutdown all loggers and flush pending logs.
        """
        for logger in self._loggers.values():
            for handler in logger._logger.handlers:
                handler.flush()
                handler.close()


# Convenience functions for common logging patterns
async def log_with_correlation(
    logger: StructuredLogger,
    level: str,
    message: str,
    context: dict[str, Any] | None = None,
    correlation_id: str | None = None,
) -> str:
    """
    Log message with automatic correlation ID management.

    Args:
        logger: StructuredLogger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        context: Optional context data
        correlation_id: Optional correlation ID (generates new if None)

    Returns:
        The correlation ID used for this log entry
    """
    # Set correlation ID
    corr_id = logger.set_correlation_id(correlation_id)

    # Log based on level
    log_method = getattr(logger, level.lower())
    await log_method(message, context)

    return corr_id


def create_correlation_context(corr_id: str | None = None) -> str:
    """
    Create a new correlation context for request tracking.

    Args:
        corr_id: Optional correlation ID (generates new if None)

    Returns:
        The correlation ID that was set
    """
    if corr_id is None:
        corr_id = str(uuid.uuid4())

    correlation_id.set(corr_id)
    return corr_id


# Global logging service instance (will be initialized by DI container)
_logging_service: LoggingService | None = None


def get_logging_service() -> LoggingService | None:
    """
    Get the global logging service instance.

    Returns:
        LoggingService instance or None if not initialized
    """
    return _logging_service


def set_logging_service(service: LoggingService) -> None:
    """
    Set the global logging service instance.

    Args:
        service: LoggingService instance to set as global
    """
    global _logging_service
    _logging_service = service
