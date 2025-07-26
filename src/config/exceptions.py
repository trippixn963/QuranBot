"""Configuration-related exceptions for QuranBot.

This module provides configuration-specific exceptions that extend
the core exception hierarchy for consistent error handling.
"""

from typing import Any

from src.core.exceptions import ConfigurationError
from src.core.exceptions import ValidationError as CoreValidationError

# Re-export core exceptions for backward compatibility
__all__ = ["ConfigurationError", "ValidationError", "MissingConfigurationError"]


class ValidationError(CoreValidationError):
    """Exception raised when configuration validation fails.

    This extends the core ValidationError with configuration-specific
    context and field information.
    """

    def __init__(self, field: str, value: Any, message: str):
        """Initialize validation error with field details.

        Args:
            field: Name of the configuration field that failed validation
            value: The invalid value that was provided
            message: Detailed error message
        """
        super().__init__(
            f"Configuration validation failed for '{field}': {message}",
            context={
                "validation_field": field,
                "validation_value": str(value),
                "config_field": field,
                "config_value": value,
            },
        )
        self.field = field
        self.value = value


class MissingConfigurationError(ConfigurationError):
    """Exception raised when required configuration is missing."""

    def __init__(self, field: str, env_var: str | None = None):
        """Initialize missing configuration error.

        Args:
            field: Name of the missing configuration field
            env_var: Environment variable name if applicable
        """
        message = f"Required configuration '{field}' is missing"
        if env_var:
            message += f" (environment variable: {env_var})"

        super().__init__(message, context={"config_field": field, "env_var": env_var})
        self.field = field
        self.env_var = env_var
