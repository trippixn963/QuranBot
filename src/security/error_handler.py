# =============================================================================
# QuranBot - Secure Error Handler
# =============================================================================
# Secure error handling that prevents information disclosure while providing
# useful debugging information for developers and administrators.
# =============================================================================

from datetime import datetime
from enum import Enum
import logging
import secrets
import traceback
from typing import Any


class ErrorSeverity(Enum):
    """Error severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecureErrorHandler:
    """Secure error handling with information disclosure prevention."""

    def __init__(self, logger: logging.Logger, debug_mode: bool = False):
        self.logger = logger
        self.debug_mode = debug_mode
        self.error_codes = {
            # Authentication errors
            "AUTH_INVALID_TOKEN": "Invalid authentication token",
            "AUTH_INSUFFICIENT_PERMISSIONS": "Insufficient permissions",
            "AUTH_RATE_LIMITED": "Too many authentication attempts",
            # Input validation errors
            "INVALID_INPUT": "Invalid input provided",
            "INVALID_USER_ID": "Invalid user ID format",
            "INVALID_GUILD_ID": "Invalid guild ID format",
            "INVALID_SURAH_NUMBER": "Surah number must be between 1 and 114",
            # Audio system errors
            "AUDIO_PLAYBACK_FAILED": "Audio playback failed",
            "AUDIO_FILE_NOT_FOUND": "Audio file not found",
            "AUDIO_VOICE_CHANNEL_ERROR": "Voice channel connection error",
            # Quiz system errors
            "QUIZ_SESSION_NOT_FOUND": "Quiz session not found or expired",
            "QUIZ_INVALID_ANSWER": "Invalid quiz answer",
            "QUIZ_RATE_LIMITED": "Quiz rate limit exceeded",
            # AI system errors
            "AI_SERVICE_UNAVAILABLE": "AI service temporarily unavailable",
            "AI_RATE_LIMITED": "AI query rate limit exceeded",
            "AI_INVALID_QUESTION": "Invalid question format",
            # System errors
            "SYSTEM_ERROR": "Internal system error",
            "DATABASE_ERROR": "Database operation failed",
            "CONFIGURATION_ERROR": "Configuration error",
            "NETWORK_ERROR": "Network communication error",
        }

    def generate_error_id(self) -> str:
        """Generate unique error ID for tracking."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        random_suffix = secrets.token_hex(4)
        return f"ERR_{timestamp}_{random_suffix}"

    async def handle_error(
        self,
        error: Exception,
        context: dict[str, Any] = None,
        user_facing: bool = True,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Handle errors securely without information disclosure.

        Args:
            error: The exception that occurred
            context: Additional context information
            user_facing: Whether this error will be shown to users
            user_id: User ID for personalized error handling

        Returns:
            Dict containing error information appropriate for the audience
        """
        error_id = self.generate_error_id()
        error_code = self._get_error_code(error)
        severity = self._get_error_severity(error)

        # Sanitize context to remove sensitive information
        safe_context = self._sanitize_context(context or {})

        # Log full error details securely (internal only)
        await self._log_error_details(error, error_id, safe_context, user_id)

        if user_facing:
            return self._create_user_error_response(error_code, error_id, severity)
        else:
            return self._create_internal_error_response(error, error_id, safe_context)

    def _get_error_code(self, error: Exception) -> str:
        """Determine appropriate error code for exception."""
        error_type = type(error).__name__
        error_message = str(error).lower()

        # Map specific exceptions to error codes
        if hasattr(error, "code"):
            return error.code

        # Map by exception type
        type_mapping = {
            "ValueError": "INVALID_INPUT",
            "TypeError": "INVALID_INPUT",
            "PermissionError": "AUTH_INSUFFICIENT_PERMISSIONS",
            "FileNotFoundError": "AUDIO_FILE_NOT_FOUND",
            "ConnectionError": "NETWORK_ERROR",
            "TimeoutError": "NETWORK_ERROR",
        }

        if error_type in type_mapping:
            return type_mapping[error_type]

        # Map by error message content
        if "token" in error_message or "auth" in error_message:
            return "AUTH_INVALID_TOKEN"
        elif "permission" in error_message:
            return "AUTH_INSUFFICIENT_PERMISSIONS"
        elif "surah" in error_message:
            return "INVALID_SURAH_NUMBER"
        elif "user" in error_message and "id" in error_message:
            return "INVALID_USER_ID"
        elif "audio" in error_message or "playback" in error_message:
            return "AUDIO_PLAYBACK_FAILED"
        elif "quiz" in error_message:
            return "QUIZ_SESSION_NOT_FOUND"
        elif "database" in error_message or "db" in error_message:
            return "DATABASE_ERROR"

        return "SYSTEM_ERROR"

    def _get_error_severity(self, error: Exception) -> ErrorSeverity:
        """Determine error severity level."""
        error_type = type(error).__name__
        error_message = str(error).lower()

        # Critical errors
        if any(
            keyword in error_message
            for keyword in ["security", "injection", "unauthorized"]
        ):
            return ErrorSeverity.CRITICAL

        # High severity errors
        if (
            error_type in ["PermissionError", "SecurityError"]
            or "auth" in error_message
        ):
            return ErrorSeverity.HIGH

        # Medium severity errors
        if error_type in ["ValueError", "TypeError", "ConnectionError"]:
            return ErrorSeverity.MEDIUM

        # Default to low severity
        return ErrorSeverity.LOW

    def _sanitize_context(self, context: dict[str, Any]) -> dict[str, Any]:
        """Remove sensitive information from context."""
        from .validators import SecureValidator

        return SecureValidator.sanitize_log_data(context)

    async def _log_error_details(
        self,
        error: Exception,
        error_id: str,
        context: dict[str, Any],
        user_id: int | None,
    ):
        """Log detailed error information securely."""
        log_data = {
            "error_id": error_id,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Add stack trace in debug mode only
        if self.debug_mode:
            log_data["stack_trace"] = self._get_safe_traceback(error)

        # Log with appropriate level based on severity
        severity = self._get_error_severity(error)
        if severity == ErrorSeverity.CRITICAL:
            self.logger.critical("Critical error occurred", extra=log_data)
        elif severity == ErrorSeverity.HIGH:
            self.logger.error("High severity error occurred", extra=log_data)
        elif severity == ErrorSeverity.MEDIUM:
            self.logger.warning("Medium severity error occurred", extra=log_data)
        else:
            self.logger.info("Low severity error occurred", extra=log_data)

    def _get_safe_traceback(self, error: Exception) -> str:
        """Get sanitized stack trace."""
        try:
            tb_lines = traceback.format_exception(
                type(error), error, error.__traceback__
            )

            # Filter out sensitive information from traceback
            safe_lines = []
            for line in tb_lines:
                # Remove absolute paths, keep only relative paths
                if "/home/" in line or "/usr/" in line or "C:\\" in line:
                    # Extract just the filename and line number
                    parts = line.split("/")
                    if len(parts) > 1:
                        line = f".../{parts[-1]}"

                # Remove any potential sensitive data patterns
                line = re.sub(
                    r'token[=:]\s*["\']?[A-Za-z0-9._-]+["\']?',
                    "token=[REDACTED]",
                    line,
                    flags=re.IGNORECASE,
                )
                line = re.sub(
                    r'key[=:]\s*["\']?[A-Za-z0-9._-]+["\']?',
                    "key=[REDACTED]",
                    line,
                    flags=re.IGNORECASE,
                )

                safe_lines.append(line)

            return "".join(safe_lines)
        except Exception:
            return "Stack trace unavailable"

    def _create_user_error_response(
        self, error_code: str, error_id: str, severity: ErrorSeverity
    ) -> dict[str, Any]:
        """Create user-facing error response."""
        user_message = self.error_codes.get(error_code, "An unexpected error occurred")

        response = {
            "error": {
                "code": error_code,
                "message": user_message,
                "error_id": error_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
        }

        # Add helpful information for certain error types
        if error_code == "INVALID_SURAH_NUMBER":
            response["error"]["details"] = {
                "valid_range": "1-114",
                "help": "Please enter a surah number between 1 and 114",
            }
        elif error_code == "QUIZ_RATE_LIMITED":
            response["error"]["details"] = {
                "retry_after": 300,  # 5 minutes
                "help": "Please wait before starting another quiz",
            }
        elif error_code == "AI_RATE_LIMITED":
            response["error"]["details"] = {
                "retry_after": 3600,  # 1 hour
                "help": "You can ask one AI question per hour",
            }

        return response

    def _create_internal_error_response(
        self, error: Exception, error_id: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Create internal error response with more details."""
        return {
            "error_id": error_id,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "timestamp": datetime.utcnow().isoformat(),
            "severity": self._get_error_severity(error).value,
        }

    async def handle_validation_error(
        self, field: str, value: Any, constraint: str
    ) -> dict[str, Any]:
        """Handle input validation errors specifically."""
        error_id = self.generate_error_id()

        # Log validation error
        await self._log_error_details(
            ValueError(f"Validation failed for {field}"),
            error_id,
            {"field": field, "constraint": constraint},
            None,
        )

        return {
            "error": {
                "code": "INVALID_INPUT",
                "message": f"Invalid value for {field}",
                "error_id": error_id,
                "details": {
                    "field": field,
                    "constraint": constraint,
                },
                "timestamp": datetime.utcnow().isoformat(),
            }
        }

    async def handle_rate_limit_error(
        self, limit: int, window: int, retry_after: int
    ) -> dict[str, Any]:
        """Handle rate limiting errors specifically."""
        error_id = self.generate_error_id()

        return {
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Rate limit exceeded",
                "error_id": error_id,
                "details": {
                    "limit": limit,
                    "window": f"{window} seconds",
                    "retry_after": retry_after,
                },
                "timestamp": datetime.utcnow().isoformat(),
            }
        }
