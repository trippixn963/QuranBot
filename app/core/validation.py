"""Validation utilities for QuranBot.

Base validation classes and utilities to reduce code duplication across
services. Provides common validation patterns for file systems, configurations,
and user inputs.
"""

# dependencies, and data integrity checks.
# =============================================================================

from abc import ABC, abstractmethod
import asyncio
from collections.abc import Callable
import os
from pathlib import Path
import shutil
from typing import Any

from .errors import ErrorHandler
from .logger import TreeLogger


class ValidationResult:
    """
    Encapsulates the result of a validation check.

    Attributes
    ----------
    is_valid : bool
        Whether the validation passed
    errors : list
        List of error messages if validation failed
    warnings : list
        List of warning messages
    metadata : dict
        Additional metadata about the validation

    """

    def __init__(self):
        self.is_valid: bool = True
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.metadata: dict[str, Any] = {}

    def add_error(self, message: str) -> None:
        """Add an error and mark validation as failed."""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        """Add a warning (doesn't fail validation)."""
        self.warnings.append(message)

    def merge(self, other: "ValidationResult") -> None:
        """Merge another validation result into this one."""
        if not other.is_valid:
            self.is_valid = False
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.metadata.update(other.metadata)


class BaseValidator(ABC):
    """
    Abstract base class for validators.

    Provides common validation functionality and structure for
    implementing specific validators across different services.
    """

    def __init__(self, service_name: str):
        """Initialize base validator.

        Args
        ----
        service_name : str
            Name of the service using this validator

        """
        self.service_name = service_name
        self.error_handler = ErrorHandler()

    @abstractmethod
    async def validate(self) -> ValidationResult:
        """
        Perform validation checks.

        Returns:
            ValidationResult containing validation status and messages
        """
        pass

    async def validate_with_logging(self) -> bool:
        """
        Perform validation with comprehensive logging.

        Returns:
            bool: True if validation passed
        """
        try:
            TreeLogger.debug(
                f"Starting validation for {self.service_name}",
                service=self.service_name,
            )

            result = await self.validate()

            # Log errors
            for error in result.errors:
                TreeLogger.error(
                    f"Validation error: {error}", service=self.service_name
                )

            # Log warnings
            for warning in result.warnings:
                TreeLogger.warning(
                    f"Validation warning: {warning}", service=self.service_name
                )

            # Log result
            if result.is_valid:
                TreeLogger.success(
                    f"Validation passed for {self.service_name}",
                    {
                        "warnings_count": len(result.warnings),
                        "metadata": result.metadata,
                    },
                    service=self.service_name,
                )
            else:
                TreeLogger.error(
                    f"Validation failed for {self.service_name}",
                    {
                        "error_count": len(result.errors),
                        "warning_count": len(result.warnings),
                    },
                    service=self.service_name,
                )

            return result.is_valid

        except Exception as e:
            TreeLogger.error(
                f"Error during validation: {e}",
                {"error_type": type(e).__name__},
                service=self.service_name,
            )

            await self.error_handler.handle_error(
                e,
                {
                    "operation": "validate_with_logging",
                    "service_name": self.service_name,
                },
            )
            return False


class FileSystemValidator(BaseValidator):
    """
    Validates file system resources like directories and files.

    Common validation patterns for paths, permissions, and disk space.
    """

    def __init__(self, service_name: str):
        super().__init__(service_name)
        self.paths_to_validate: list[dict[str, Any]] = []

    def add_path(
        self,
        path: str | Path,
        path_type: str = "directory",
        create_if_missing: bool = True,
        required_space_mb: float | None = None,
    ) -> None:
        """
        Add a path to validate.

        Args:
            path: Path to validate
            path_type: "directory" or "file"
            create_if_missing: Whether to create directories if they don't exist
            required_space_mb: Required free space in MB
        """
        self.paths_to_validate.append(
            {
                "path": Path(path),
                "type": path_type,
                "create_if_missing": create_if_missing,
                "required_space_mb": required_space_mb,
            }
        )

    async def validate(self) -> ValidationResult:
        """Validate all configured paths."""
        result = ValidationResult()

        for path_config in self.paths_to_validate:
            path = path_config["path"]
            path_type = path_config["type"]

            # Check existence
            if not path.exists():
                if path_type == "directory" and path_config["create_if_missing"]:
                    try:
                        path.mkdir(parents=True, exist_ok=True)
                        result.metadata[f"{path}_created"] = True
                        TreeLogger.info(
                            f"Created directory: {path}", service=self.service_name
                        )
                    except Exception as e:
                        result.add_error(f"Failed to create directory {path}: {e}")
                        continue
                else:
                    result.add_error(f"{path_type.capitalize()} not found: {path}")
                    continue

            # Check permissions
            if not os.access(str(path), os.R_OK):
                result.add_error(f"No read permission for {path}")

            if path_type == "directory" and not os.access(str(path), os.W_OK):
                result.add_error(f"No write permission for {path}")

            # Check disk space
            if path_config["required_space_mb"]:
                free_space_mb = self._get_free_space_mb(path)
                if free_space_mb < path_config["required_space_mb"]:
                    result.add_warning(
                        f"Low disk space for {path}: {free_space_mb:.1f}MB free, "
                        f"{path_config['required_space_mb']:.1f}MB recommended"
                    )
                result.metadata[f"{path}_free_space_mb"] = free_space_mb

        return result

    def _get_free_space_mb(self, path: Path) -> float:
        """Get free disk space in MB for the given path."""
        try:
            stat = shutil.disk_usage(str(path))
            return stat.free / (1024 * 1024)
        except Exception:
            return 0.0


class DependencyValidator(BaseValidator):
    """
    Validates external dependencies like executables and libraries.
    """

    def __init__(self, service_name: str):
        super().__init__(service_name)
        self.dependencies: list[dict[str, Any]] = []

    def add_executable(
        self, name: str, test_command: str | None = None, required: bool = True
    ) -> None:
        """
        Add an executable dependency to validate.

        Args:
            name: Name of the executable
            test_command: Command to test the executable (e.g., "ffmpeg -version")
            required: Whether this dependency is required
        """
        self.dependencies.append(
            {
                "type": "executable",
                "name": name,
                "test_command": test_command or f"{name} --version",
                "required": required,
            }
        )

    def add_python_module(self, name: str, required: bool = True) -> None:
        """
        Add a Python module dependency to validate.

        Args:
            name: Name of the Python module
            required: Whether this dependency is required
        """
        self.dependencies.append({"type": "module", "name": name, "required": required})

    async def validate(self) -> ValidationResult:
        """Validate all configured dependencies."""
        result = ValidationResult()

        for dep in self.dependencies:
            if dep["type"] == "executable":
                await self._validate_executable(dep, result)
            elif dep["type"] == "module":
                await self._validate_module(dep, result)

        return result

    async def _validate_executable(
        self, dep: dict[str, Any], result: ValidationResult
    ) -> None:
        """Validate an executable dependency."""
        name = dep["name"]

        # Check if executable exists
        if not shutil.which(name):
            if dep["required"]:
                result.add_error(f"Required executable not found: {name}")
            else:
                result.add_warning(f"Optional executable not found: {name}")
            return

        # Test executable if command provided
        if dep["test_command"]:
            try:
                proc = await asyncio.create_subprocess_shell(
                    dep["test_command"],
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()

                if proc.returncode != 0:
                    result.add_warning(
                        f"Executable {name} test failed with code {proc.returncode}"
                    )
                else:
                    # Extract version if possible
                    output = stdout.decode().strip()
                    result.metadata[f"{name}_output"] = output[:100]  # First 100 chars

            except Exception as e:
                result.add_warning(f"Failed to test executable {name}: {e}")

    async def _validate_module(
        self, dep: dict[str, Any], result: ValidationResult
    ) -> None:
        """Validate a Python module dependency."""
        name = dep["name"]

        try:
            __import__(name)
            result.metadata[f"{name}_available"] = True
        except ImportError:
            if dep["required"]:
                result.add_error(f"Required Python module not found: {name}")
            else:
                result.add_warning(f"Optional Python module not found: {name}")


class ConfigurationValidator(BaseValidator):
    """
    Validates configuration values and constraints.
    """

    def __init__(self, service_name: str, config: Any):
        super().__init__(service_name)
        self.config = config
        self.checks: list[Callable] = []

    def add_check(
        self, check_func: Callable[[Any, ValidationResult], None], description: str
    ) -> None:
        """
        Add a custom configuration check.

        Args:
            check_func: Function that takes (config, result) and updates result
            description: Description of what this check validates
        """
        self.checks.append((check_func, description))

    def require_fields(self, *fields: str) -> None:
        """Add a check for required fields."""

        def check(config: Any, result: ValidationResult) -> None:
            for field in fields:
                if not hasattr(config, field) or getattr(config, field) is None:
                    result.add_error(f"Required configuration field missing: {field}")

        self.add_check(check, f"Required fields: {', '.join(fields)}")

    def validate_range(self, field: str, min_val: float, max_val: float) -> None:
        """Add a check for numeric range."""

        def check(config: Any, result: ValidationResult) -> None:
            if hasattr(config, field):
                value = getattr(config, field)
                if value is not None:
                    if value < min_val or value > max_val:
                        result.add_error(
                            f"Configuration {field}={value} outside valid range "
                            f"[{min_val}, {max_val}]"
                        )

        self.add_check(check, f"{field} in range [{min_val}, {max_val}]")

    async def validate(self) -> ValidationResult:
        """Run all configuration checks."""
        result = ValidationResult()

        for check_func, description in self.checks:
            try:
                TreeLogger.debug(
                    f"Running config check: {description}", service=self.service_name
                )
                check_func(self.config, result)
            except Exception as e:
                result.add_error(f"Configuration check failed ({description}): {e}")

        return result


class CompositeValidator(BaseValidator):
    """
    Combines multiple validators into one.

    Useful for services that need multiple types of validation.
    """

    def __init__(self, service_name: str):
        super().__init__(service_name)
        self.validators: list[BaseValidator] = []

    def add_validator(self, validator: BaseValidator) -> None:
        """Add a validator to the composite."""
        self.validators.append(validator)

    async def validate(self) -> ValidationResult:
        """Run all validators and combine results."""
        combined_result = ValidationResult()

        for validator in self.validators:
            result = await validator.validate()
            combined_result.merge(result)

        return combined_result


# Convenience function for common validation scenarios
async def validate_service_requirements(
    service_name: str,
    paths: list[dict[str, Any]] | None = None,
    executables: list[str] | None = None,
    config_checks: list[Callable] | None = None,
    config: Any | None = None,
) -> bool:
    """
    Validate common service requirements.

    Args:
        service_name: Name of the service
        paths: List of paths to validate
        executables: List of required executables
        config_checks: List of configuration check functions
        config: Configuration object

    Returns:
        bool: True if all validations pass
    """
    composite = CompositeValidator(service_name)

    # Add file system validation
    if paths:
        fs_validator = FileSystemValidator(service_name)
        for path_config in paths:
            fs_validator.add_path(**path_config)
        composite.add_validator(fs_validator)

    # Add dependency validation
    if executables:
        dep_validator = DependencyValidator(service_name)
        for exe in executables:
            dep_validator.add_executable(exe)
        composite.add_validator(dep_validator)

    # Add configuration validation
    if config_checks and config:
        config_validator = ConfigurationValidator(service_name, config)
        for check in config_checks:
            config_validator.add_check(check[0], check[1])
        composite.add_validator(config_validator)

    return await composite.validate_with_logging()
