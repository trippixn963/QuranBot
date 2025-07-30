# =============================================================================
# QuranBot - Custom Exception Hierarchy
# =============================================================================
# This module provides a comprehensive exception hierarchy for QuranBot with
# context support, structured logging integration, and specific exception types
# for different error categories.
#
# Key Features:
# - Base QuranBotError class with context support
# - Specific exception types for different error categories
# - Integration with structured logging system
# - Global error handler decorator
# - Type-safe error handling patterns
# =============================================================================

from collections.abc import Callable
from datetime import UTC, datetime
import functools
import traceback
from typing import Any, TypeVar

from .logger import StructuredLogger

# Type variable for decorated functions
F = TypeVar("F", bound=Callable[..., Any])


class QuranBotError(Exception):
    """
    Base exception class for all QuranBot-specific errors.

    This class provides a foundation for all custom exceptions in QuranBot,
    including context support for debugging and structured error information.
    All QuranBot exceptions should inherit from this class.
    """

    def __init__(
        self,
        message: str,
        context: dict[str, Any] | None = None,
        original_error: Exception | None = None,
    ):
        """
        Initialize QuranBot error with context support.

        Args:
            message: Human-readable error message
            context: Additional context information about the error
            original_error: Original exception that caused this error (if any)
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.original_error = original_error
        self.timestamp = datetime.now(UTC)

        # Add original error info to context if provided
        if original_error:
            self.context.update(
                {
                    "original_error_type": type(original_error).__name__,
                    "original_error_message": str(original_error),
                }
            )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert exception to dictionary for logging and serialization.

        Returns:
            Dictionary representation of the exception
        """
        return {
            "error_type": type(self).__name__,
            "message": self.message,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "original_error": str(self.original_error) if self.original_error else None,
        }

    def __str__(self) -> str:
        """String representation of the error."""
        if self.context:
            return f"{self.message} (Context: {self.context})"
        return self.message


class AudioError(QuranBotError):
    """
    Exception raised for audio-related errors.

    This includes errors in audio file loading, playback, format issues,
    reciter management, and audio state management.
    """

    def __init__(
        self,
        message: str,
        audio_file: str | None = None,
        reciter: str | None = None,
        surah_number: int | None = None,
        context: dict[str, Any] | None = None,
        original_error: Exception | None = None,
    ):
        """
        Initialize audio error with audio-specific context.

        Args:
            message: Error message
            audio_file: Path to audio file that caused the error
            reciter: Name of reciter involved in the error
            surah_number: Surah number if applicable
            context: Additional context information
            original_error: Original exception that caused this error
        """
        audio_context = context or {}

        # Add audio-specific context
        if audio_file:
            audio_context["audio_file"] = audio_file
        if reciter:
            audio_context["reciter"] = reciter
        if surah_number:
            audio_context["surah_number"] = surah_number

        super().__init__(message, audio_context, original_error)


class ConfigurationError(QuranBotError):
    """
    Exception raised for configuration-related errors.

    This includes missing configuration values, invalid configuration formats,
    environment variable issues, and configuration validation failures.
    """

    def __init__(
        self,
        message: str,
        config_field: str | None = None,
        config_value: Any | None = None,
        env_var: str | None = None,
        context: dict[str, Any] | None = None,
        original_error: Exception | None = None,
    ):
        """
        Initialize configuration error with config-specific context.

        Args:
            message: Error message
            config_field: Name of configuration field that caused the error
            config_value: Value that caused the error
            env_var: Environment variable name if applicable
            context: Additional context information
            original_error: Original exception that caused this error
        """
        config_context = context or {}

        # Add configuration-specific context
        if config_field:
            config_context["config_field"] = config_field
        if config_value is not None:
            config_context["config_value"] = str(config_value)
        if env_var:
            config_context["env_var"] = env_var

        super().__init__(message, config_context, original_error)


class StateError(QuranBotError):
    """
    Exception raised for state management errors.

    This includes errors in saving/loading state, state corruption,
    backup failures, and state validation issues.
    """

    def __init__(
        self,
        message: str,
        state_type: str | None = None,
        state_file: str | None = None,
        operation: str | None = None,
        context: dict[str, Any] | None = None,
        original_error: Exception | None = None,
    ):
        """
        Initialize state error with state-specific context.

        Args:
            message: Error message
            state_type: Type of state (e.g., 'playback', 'quiz', 'user')
            state_file: Path to state file that caused the error
            operation: Operation being performed (e.g., 'save', 'load', 'validate')
            context: Additional context information
            original_error: Original exception that caused this error
        """
        state_context = context or {}

        # Add state-specific context
        if state_type:
            state_context["state_type"] = state_type
        if state_file:
            state_context["state_file"] = state_file
        if operation:
            state_context["operation"] = operation

        super().__init__(message, state_context, original_error)


class ValidationError(QuranBotError):
    """
    Exception raised for data validation errors.

    This includes Pydantic validation failures, input validation errors,
    and data format validation issues.
    """

    def __init__(
        self,
        message: str,
        field_name: str | None = None,
        field_value: Any | None = None,
        validation_rule: str | None = None,
        context: dict[str, Any] | None = None,
        original_error: Exception | None = None,
    ):
        """
        Initialize validation error with validation-specific context.

        Args:
            message: Error message
            field_name: Name of field that failed validation
            field_value: Value that failed validation
            validation_rule: Validation rule that was violated
            context: Additional context information
            original_error: Original exception that caused this error
        """
        validation_context = context or {}

        # Add validation-specific context
        if field_name:
            validation_context["field_name"] = field_name
        if field_value is not None:
            validation_context["field_value"] = str(field_value)
        if validation_rule:
            validation_context["validation_rule"] = validation_rule

        super().__init__(message, validation_context, original_error)


class RateLimitError(QuranBotError):
    """
    Exception raised for rate limiting violations.

    This includes Discord API rate limits, command rate limits,
    and custom rate limiting implementations.
    """

    def __init__(
        self,
        message: str,
        user_id: int | None = None,
        command: str | None = None,
        limit_type: str | None = None,
        retry_after: float | None = None,
        context: dict[str, Any] | None = None,
        original_error: Exception | None = None,
    ):
        """
        Initialize rate limit error with rate limit-specific context.

        Args:
            message: Error message
            user_id: Discord user ID that hit the rate limit
            command: Command that triggered the rate limit
            limit_type: Type of rate limit (e.g., 'discord_api', 'command', 'user')
            retry_after: Seconds to wait before retrying
            context: Additional context information
            original_error: Original exception that caused this error
        """
        rate_limit_context = context or {}

        # Add rate limit-specific context
        if user_id:
            rate_limit_context["user_id"] = user_id
        if command:
            rate_limit_context["command"] = command
        if limit_type:
            rate_limit_context["limit_type"] = limit_type
        if retry_after:
            rate_limit_context["retry_after"] = retry_after

        super().__init__(message, rate_limit_context, original_error)


class ServiceError(QuranBotError):
    """
    Exception raised for service-level errors.

    This includes dependency injection errors, service initialization failures,
    and inter-service communication issues.
    """

    def __init__(
        self,
        message: str,
        service_name: str | None = None,
        operation: str | None = None,
        context: dict[str, Any] | None = None,
        original_error: Exception | None = None,
    ):
        """
        Initialize service error with service-specific context.

        Args:
            message: Error message
            service_name: Name of service that caused the error
            operation: Operation being performed when error occurred
            context: Additional context information
            original_error: Original exception that caused this error
        """
        service_context = context or {}

        # Add service-specific context
        if service_name:
            service_context["service_name"] = service_name
        if operation:
            service_context["operation"] = operation

        super().__init__(message, service_context, original_error)


class DiscordAPIError(QuranBotError):
    """
    Exception for Discord API-related errors.

    This covers API failures, permission errors, webhook failures,
    and Discord service issues.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        discord_error: str | None = None,
        endpoint: str | None = None,
        context: dict[str, Any] | None = None,
        original_error: Exception | None = None,
    ):
        api_context = context or {}

        # Add Discord API-specific context
        if status_code:
            api_context["status_code"] = status_code
        if discord_error:
            api_context["discord_error"] = discord_error
        if endpoint:
            api_context["endpoint"] = endpoint

        super().__init__(message, api_context, original_error)


class WebhookError(DiscordAPIError):
    """
    Specific exception for Discord webhook errors.

    This covers webhook failures, invalid URLs, and webhook rate limits.
    """

    def __init__(self, message: str, webhook_url: str | None = None, **kwargs):
        context = kwargs.get("context", {})
        if webhook_url:
            context["webhook_url"] = webhook_url
        kwargs["context"] = context
        super().__init__(message, **kwargs)


class VoiceConnectionError(AudioError):
    """
    Specific exception for voice connection failures.

    This covers voice channel connection issues, permission problems,
    and voice client management errors.
    """

    def __init__(
        self,
        message: str,
        voice_channel_id: int | None = None,
        guild_id: int | None = None,
        **kwargs,
    ):
        context = kwargs.get("context", {})
        if voice_channel_id:
            context["voice_channel_id"] = voice_channel_id
        if guild_id:
            context["guild_id"] = guild_id
        kwargs["context"] = context
        super().__init__(message, **kwargs)


class FFmpegError(AudioError):
    """
    Specific exception for FFmpeg processing errors.

    This covers audio encoding/decoding issues, FFmpeg process failures,
    and audio format problems.
    """

    def __init__(
        self,
        message: str,
        ffmpeg_command: str | None = None,
        ffmpeg_output: str | None = None,
        **kwargs,
    ):
        context = kwargs.get("context", {})
        if ffmpeg_command:
            context["ffmpeg_command"] = ffmpeg_command
        if ffmpeg_output:
            context["ffmpeg_output"] = ffmpeg_output
        kwargs["context"] = context
        super().__init__(message, **kwargs)


class QuizError(QuranBotError):
    """
    Exception for quiz system errors.

    This covers quiz loading failures, question validation errors,
    scoring issues, and quiz state management problems.
    """

    def __init__(
        self,
        message: str,
        quiz_id: str | None = None,
        question_id: str | None = None,
        user_id: int | None = None,
        context: dict[str, Any] | None = None,
        original_error: Exception | None = None,
    ):
        quiz_context = context or {}

        # Add quiz-specific context
        if quiz_id:
            quiz_context["quiz_id"] = quiz_id
        if question_id:
            quiz_context["question_id"] = question_id
        if user_id:
            quiz_context["user_id"] = user_id

        super().__init__(message, quiz_context, original_error)


class BackupError(StateError):
    """
    Specific exception for backup operation failures.

    This covers backup creation, restoration, and validation failures.
    """

    def __init__(
        self,
        message: str,
        backup_path: str | None = None,
        backup_type: str | None = None,
        **kwargs,
    ):
        context = kwargs.get("context", {})
        if backup_path:
            context["backup_path"] = backup_path
        if backup_type:
            context["backup_type"] = backup_type
        kwargs["context"] = context
        super().__init__(message, **kwargs)


def handle_errors(
    logger: StructuredLogger, reraise: bool = True, log_level: str = "error"
) -> Callable[[F], F]:
    """
    Decorator for consistent error handling with structured logging.

    This decorator provides a centralized way to handle exceptions across
    the application, ensuring consistent logging and error reporting.

    Args:
        logger: StructuredLogger instance for error logging
        reraise: Whether to reraise the exception after logging
        log_level: Log level to use for error logging

    Returns:
        Decorated function with error handling

    Example:
        @handle_errors(logger)
        async def my_function():
            # Function implementation
            pass
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except QuranBotError as e:
                # Log QuranBot-specific errors with full context
                await getattr(logger, log_level)(
                    f"QuranBot error in {func.__name__}: {e.message}",
                    {
                        "function": func.__name__,
                        "error_type": type(e).__name__,
                        "error_context": e.context,
                        "timestamp": e.timestamp.isoformat(),
                        "args": [str(arg) for arg in args],
                        "kwargs": {k: str(v) for k, v in kwargs.items()},
                    },
                )

                if reraise:
                    raise
                return None

            except Exception as e:
                # Log unexpected errors and wrap in QuranBotError
                await getattr(logger, log_level)(
                    f"Unexpected error in {func.__name__}: {e!s}",
                    {
                        "function": func.__name__,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "traceback": traceback.format_exc(),
                        "args": [str(arg) for arg in args],
                        "kwargs": {k: str(v) for k, v in kwargs.items()},
                    },
                    exc_info=True,
                )

                if reraise:
                    # Wrap unexpected errors in QuranBotError
                    raise ServiceError(
                        f"Unexpected error in {func.__name__}",
                        service_name=func.__module__,
                        operation=func.__name__,
                        context={
                            "original_error_type": type(e).__name__,
                            "original_error_message": str(e),
                        },
                        original_error=e,
                    )
                return None

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except QuranBotError as e:
                # For sync functions, we can't use async logging
                # So we'll use the underlying logger directly
                logger._logger.error(
                    f"QuranBot error in {func.__name__}: {e.message}",
                    extra={
                        "context": {
                            "function": func.__name__,
                            "error_type": type(e).__name__,
                            "error_context": e.context,
                            "timestamp": e.timestamp.isoformat(),
                            "args": [str(arg) for arg in args],
                            "kwargs": {k: str(v) for k, v in kwargs.items()},
                        }
                    },
                )

                if reraise:
                    raise
                return None

            except Exception as e:
                # Log unexpected errors and wrap in QuranBotError
                logger._logger.error(
                    f"Unexpected error in {func.__name__}: {e!s}",
                    extra={
                        "context": {
                            "function": func.__name__,
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                            "traceback": traceback.format_exc(),
                            "args": [str(arg) for arg in args],
                            "kwargs": {k: str(v) for k, v in kwargs.items()},
                        }
                    },
                    exc_info=True,
                )

                if reraise:
                    # Wrap unexpected errors in QuranBotError
                    raise ServiceError(
                        f"Unexpected error in {func.__name__}",
                        service_name=func.__module__,
                        operation=func.__name__,
                        context={
                            "original_error_type": type(e).__name__,
                            "original_error_message": str(e),
                        },
                        original_error=e,
                    )
                return None

        # Return appropriate wrapper based on whether function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def create_error_context(operation: str, **kwargs) -> dict[str, Any]:
    """
    Create standardized error context dictionary.

    Args:
        operation: Operation being performed when error occurred
        **kwargs: Additional context key-value pairs

    Returns:
        Standardized error context dictionary
    """
    context = {
        "operation": operation,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    context.update(kwargs)
    return context


class SecurityError(QuranBotError):
    """Raised when security violations occur"""

    def __init__(
        self,
        message: str,
        user_id: int | None = None,
        guild_id: int | None = None,
        reason: str | None = None,
        **context,
    ):
        super().__init__(message, **context)
        self.user_id = user_id
        self.guild_id = guild_id
        self.reason = reason


class DatabaseError(QuranBotError):
    """Raised when database operations fail"""

    def __init__(
        self,
        message: str,
        operation: str | None = None,
        table: str | None = None,
        query: str | None = None,
        **context,
    ):
        super().__init__(message, **context)
        self.operation = operation
        self.table = table
        self.query = query


# Import asyncio at the end to avoid circular imports
import asyncio
