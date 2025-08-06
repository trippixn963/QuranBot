# =============================================================================
# QuranBot - Base Service
# =============================================================================
# Base service class providing common functionality for all bot services.
# Includes retry mechanisms, error handling, and lifecycle management.
# =============================================================================

from abc import ABC, abstractmethod
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import time
from typing import Any

from ...config.timezone import APP_TIMEZONE
from ...core.errors import ErrorHandler, ErrorSeverity, ServiceError
from ...core.logger import TreeLogger, log_event


class ServiceState(Enum):
    """Service lifecycle states."""

    CREATED = "created"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    CLEANING_UP = "cleaning_up"
    CLEANED_UP = "cleaned_up"


# Alias for backward compatibility
ServiceStatus = ServiceState


@dataclass
class ServiceHealth:
    """Service health information with detailed metrics."""

    state: ServiceState
    uptime_seconds: float
    last_heartbeat: datetime
    error_count: int = 0
    warning_count: int = 0
    retry_count: int = 0
    performance_metrics: dict[str, Any] = field(default_factory=dict)
    resource_usage: dict[str, Any] = field(default_factory=dict)
    is_healthy: bool = True
    health_score: float = 100.0
    last_error: str | None = None
    last_error_time: datetime | None = None


class BaseService(ABC):
    """
    Base service class with retry mechanisms and robust error handling.
    Provides common functionality for all bot services including initialization,
    startup, shutdown, health monitoring, and error recovery.
    """

    def __init__(self, service_name: str, logger=None, error_handler=None):
        """
        Initialize base service with error handling and retry logic.

        Args:
            service_name: Name of the service for identification
            logger: (Optional) Logger instance for structured logging
            error_handler: (Optional) Error handler for centralized error management
        """
        self.service_name = service_name
        # Logger and error_handler are now optional since we use log_event
        self.logger = logger
        self.error_handler = error_handler if error_handler else ErrorHandler()

        # Service state management
        self.state = ServiceState.CREATED
        self.start_time: datetime | None = None
        self.initialization_time: datetime | None = None

        # retry configuration
        self.retry_config = {
            "max_retries": 3,
            "base_delay": 1.0,
            "max_delay": 30.0,
            "backoff_factor": 2.0,
            "jitter": 0.1,
        }

        # Health monitoring
        self.health = ServiceHealth(
            state=ServiceState.CREATED,
            uptime_seconds=0.0,
            last_heartbeat=datetime.now(APP_TIMEZONE),
        )

        # Performance tracking
        self.performance_metrics = {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "average_response_time": 0.0,
            "last_operation_time": None,
        }

        # Resource monitoring
        self.resource_limits = {
            "max_memory_mb": 512,
            "max_cpu_percent": 80,
            "max_disk_usage_percent": 90,
        }

        # Note: Cannot use async logger in __init__ - will log during initialize()

    async def initialize(self) -> None:
        """
        Initialize service with retry mechanisms and error recovery.
        Implements exponential backoff with jitter for robust initialization.
        """
        if self.state != ServiceState.CREATED:
            TreeLogger.error(
                f"Service '{self.service_name}' already initialized",
                context={"current_state": self.state.value},
                service="system",
            )
            return

        self.state = ServiceState.INITIALIZING
        self.initialization_time = datetime.now(APP_TIMEZONE)

        TreeLogger.section(
            f"Initializing service '{self.service_name}'", service="system"
        )

        try:
            # Attempt initialization with retry logic
            await self._retry_operation(
                operation=self._initialize,
                operation_name="service_initialization",
                context={
                    "service_name": self.service_name,
                    "initialization_time": self.initialization_time.isoformat(),
                },
            )

            self.state = ServiceState.INITIALIZED
            self.health.state = ServiceState.INITIALIZED

            TreeLogger.success(
                f"Service '{self.service_name}' initialized successfully",
                {
                    "initialization_duration_ms": self._get_initialization_duration_ms(),
                    "health_score": self.health.health_score,
                },
            )

        except Exception as e:
            self.state = ServiceState.ERROR
            self.health.state = ServiceState.ERROR
            self.health.last_error = str(e)
            self.health.last_error_time = datetime.now(APP_TIMEZONE)

            await self.error_handler.handle_error(
                e,
                {
                    "operation": "service_initialization",
                    "service_name": self.service_name,
                    "initialization_duration_ms": self._get_initialization_duration_ms(),
                },
            )

            raise ServiceError(
                f"Failed to initialize service '{self.service_name}': {e}",
                service_name=self.service_name,
                operation="initialize",
            )

    async def start(self) -> None:
        """
        Start service with error handling and health monitoring.
        Implements graceful startup with fallback mechanisms.
        """
        if self.state not in [ServiceState.INITIALIZED, ServiceState.STOPPED]:
            TreeLogger.error(
                f"Service '{self.service_name}' cannot start from state: {self.state.value}",
                context={"required_state": ServiceState.INITIALIZED.value},
                service="system",
            )
            return

        self.state = ServiceState.STARTING
        self.start_time = datetime.now(APP_TIMEZONE)

        TreeLogger.section(f"Starting service '{self.service_name}'", service="system")

        try:
            # Attempt startup with retry logic
            await self._retry_operation(
                operation=self._start,
                operation_name="service_startup",
                context={
                    "service_name": self.service_name,
                    "start_time": self.start_time.isoformat(),
                },
            )

            self.state = ServiceState.RUNNING
            self.health.state = ServiceState.RUNNING
            self.health.last_heartbeat = datetime.now(APP_TIMEZONE)

            TreeLogger.success(
                f"Service '{self.service_name}' started successfully",
                {
                    "startup_duration_ms": self._get_startup_duration_ms(),
                    "health_score": self.health.health_score,
                },
            )

        except Exception as e:
            self.state = ServiceState.ERROR
            self.health.state = ServiceState.ERROR
            self.health.last_error = str(e)
            self.health.last_error_time = datetime.now(APP_TIMEZONE)

            await self.error_handler.handle_error(
                e,
                {
                    "operation": "service_startup",
                    "service_name": self.service_name,
                    "startup_duration_ms": self._get_startup_duration_ms(),
                },
            )

            raise ServiceError(
                f"Failed to start service '{self.service_name}': {e}",
                service_name=self.service_name,
                operation="start",
            )

    async def stop(self) -> None:
        """
        Stop service gracefully with error handling.
        Implements graceful shutdown with resource cleanup.
        """
        # If already stopped or cleaned up, just return silently
        if self.state in [ServiceState.STOPPED, ServiceState.CLEANED_UP]:
            TreeLogger.debug(
                f"Service '{self.service_name}' already stopped/cleaned up",
                context={"current_state": self.state.value},
                service="system",
            )
            return

        if self.state not in [ServiceState.RUNNING, ServiceState.ERROR]:
            TreeLogger.error(
                f"Service '{self.service_name}' cannot stop from state: {self.state.value}",
                context={"current_state": self.state.value},
                service="system",
            )
            return

        self.state = ServiceState.STOPPING

        TreeLogger.section(f"Stopping service '{self.service_name}'", service="system")

        try:
            # Attempt graceful shutdown
            await self._retry_operation(
                operation=self._stop,
                operation_name="service_shutdown",
                context={
                    "service_name": self.service_name,
                    "uptime_seconds": self._get_uptime_seconds(),
                },
            )

            self.state = ServiceState.STOPPED
            self.health.state = ServiceState.STOPPED

            TreeLogger.success(
                f"Service '{self.service_name}' stopped successfully",
                {
                    "total_uptime_seconds": self._get_uptime_seconds(),
                    "final_health_score": self.health.health_score,
                },
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "service_shutdown",
                    "service_name": self.service_name,
                    "uptime_seconds": self._get_uptime_seconds(),
                },
            )

            # Force cleanup even if stop fails
            await self._force_cleanup()

    async def cleanup(self) -> None:
        """
        Clean up service resources with error handling.
        Implements comprehensive resource cleanup and state reset.
        """
        if self.state == ServiceState.CLEANED_UP:
            return

        self.state = ServiceState.CLEANING_UP

        TreeLogger.section(
            f"Cleaning up service '{self.service_name}'", service="system"
        )

        try:
            # Attempt cleanup with retry logic
            await self._retry_operation(
                operation=self._cleanup,
                operation_name="service_cleanup",
                context={
                    "service_name": self.service_name,
                    "final_state": self.state.value,
                },
            )

            self.state = ServiceState.CLEANED_UP
            self.health.state = ServiceState.CLEANED_UP

            TreeLogger.success(
                f"Service '{self.service_name}' cleaned up successfully",
                {
                    "total_lifetime_seconds": self._get_total_lifetime_seconds(),
                    "final_health_score": self.health.health_score,
                },
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "service_cleanup",
                    "service_name": self.service_name,
                    "final_state": self.state.value,
                },
            )

            # Force cleanup even if cleanup fails
            await self._force_cleanup()

    async def health_check(self) -> dict[str, Any]:
        """
        Perform comprehensive health check with metrics.
        Returns detailed health information including performance and resource usage.
        """
        try:
            # Update health metrics
            self._update_health_metrics()

            # Perform service-specific health check
            service_health = await self._health_check()

            # Combine base and service-specific health data
            health_data = {
                "service_name": self.service_name,
                "state": self.state.value,
                "health_score": self.health.health_score,
                "is_healthy": self.health.is_healthy,
                "uptime_seconds": self._get_uptime_seconds(),
                "last_heartbeat": self.health.last_heartbeat.isoformat(),
                "performance_metrics": self.performance_metrics,
                "resource_usage": self._get_resource_usage(),
                "error_stats": {
                    "total_errors": self.health.error_count,
                    "total_warnings": self.health.warning_count,
                    "retry_count": self.health.retry_count,
                    "last_error": self.health.last_error,
                    "last_error_time": (
                        self.health.last_error_time.isoformat()
                        if self.health.last_error_time
                        else None
                    ),
                },
                **service_health,
            }

            # Update health score based on metrics
            self._calculate_health_score(health_data)

            return health_data

        except Exception as e:
            await self.error_handler.handle_error(
                e, {"operation": "health_check", "service_name": self.service_name}
            )

            return {
                "service_name": self.service_name,
                "state": self.state.value,
                "health_score": 0.0,
                "is_healthy": False,
                "error": str(e),
            }

    async def _retry_operation(
        self,
        operation: callable,
        operation_name: str,
        context: dict[str, Any],
        max_retries: int | None = None,
    ) -> Any:
        """
        Execute operation with retry logic including exponential backoff and jitter.

        Args:
            operation: Async function to execute
            operation_name: Name of operation for logging
            context: Additional context for error handling
            max_retries: Maximum retry attempts (uses service default if None)

        Returns:
            Operation result

        Raises:
            ServiceError: If operation fails after all retries
        """
        max_retries = max_retries or self.retry_config["max_retries"]
        base_delay = self.retry_config["base_delay"]
        max_delay = self.retry_config["max_delay"]
        backoff_factor = self.retry_config["backoff_factor"]
        jitter = self.retry_config["jitter"]

        last_error = None

        for attempt in range(max_retries + 1):
            try:
                start_time = time.time()
                result = await operation()
                operation_time = time.time() - start_time

                # Update performance metrics
                self._update_performance_metrics(operation_time, True)

                return result

            except Exception as e:
                last_error = e
                operation_time = (
                    time.time() - start_time if "start_time" in locals() else 0
                )

                # Update performance metrics
                self._update_performance_metrics(operation_time, False)

                # Update health metrics
                self.health.error_count += 1
                self.health.last_error = str(e)
                self.health.last_error_time = datetime.now(APP_TIMEZONE)

                # Check if we should retry
                if attempt < max_retries and self._should_retry_operation(e, context):
                    # Calculate delay with exponential backoff and jitter
                    delay = min(base_delay * (backoff_factor**attempt), max_delay)
                    jitter_amount = delay * jitter * (2 * (time.time() % 1) - 1)
                    final_delay = delay + jitter_amount

                    self.health.retry_count += 1

                    log_event(
                        "WARNING",
                        f"Retrying {operation_name} (attempt {attempt + 1}/{max_retries + 1})",
                        {
                            **context,
                            "attempt": attempt + 1,
                            "max_retries": max_retries,
                            "delay_seconds": final_delay,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        },
                    )

                    await asyncio.sleep(final_delay)
                    continue
                else:
                    # Log final error
                    await self.error_handler.handle_error(
                        e,
                        {
                            **context,
                            "operation_name": operation_name,
                            "final_attempt": attempt + 1,
                            "total_retries": self.health.retry_count,
                        },
                    )
                    break

        # If we get here, all retries failed
        if last_error:
            raise ServiceError(
                f"Operation '{operation_name}' failed after {max_retries + 1} attempts",
                service_name=self.service_name,
                operation=operation_name,
                severity=ErrorSeverity.ERROR,
            )

    def _should_retry_operation(
        self, error: Exception, context: dict[str, Any]
    ) -> bool:
        """
        Determine if operation should be retried based on error type and context.

        Args:
            error: The exception that occurred
            context: Operation context

        Returns:
            True if operation should be retried, False otherwise
        """
        error_type = type(error).__name__.lower()

        # Don't retry critical errors
        if any(
            keyword in error_type
            for keyword in ["critical", "fatal", "permission", "validation"]
        ):
            return False

        # Don't retry configuration errors
        if any(
            keyword in error_type for keyword in ["config", "environment", "missing"]
        ):
            return False

        # Don't retry if service is in error state
        if self.state == ServiceState.ERROR:
            return False

        return True

    def _update_health_metrics(self) -> None:
        """Update health metrics including uptime and heartbeat."""
        now = datetime.now(APP_TIMEZONE)

        if self.start_time:
            self.health.uptime_seconds = (now - self.start_time).total_seconds()

        self.health.last_heartbeat = now

    def _update_performance_metrics(self, operation_time: float, success: bool) -> None:
        """Update performance metrics for monitoring."""
        self.performance_metrics["total_operations"] += 1

        if success:
            self.performance_metrics["successful_operations"] += 1
        else:
            self.performance_metrics["failed_operations"] += 1

        # Update average response time
        current_avg = self.performance_metrics["average_response_time"]
        total_ops = self.performance_metrics["total_operations"]

        if total_ops == 1:
            self.performance_metrics["average_response_time"] = operation_time
        else:
            self.performance_metrics["average_response_time"] = (
                current_avg * (total_ops - 1) + operation_time
            ) / total_ops

        self.performance_metrics["last_operation_time"] = datetime.now(
            APP_TIMEZONE
        ).isoformat()

    def _get_resource_usage(self) -> dict[str, Any]:
        """Get current resource usage metrics."""
        try:
            import psutil

            process = psutil.Process()
            memory_info = process.memory_info()

            return {
                "memory_mb": memory_info.rss / 1024 / 1024,
                "cpu_percent": process.cpu_percent(),
                "disk_usage_percent": (
                    psutil.disk_usage("/").percent
                    if hasattr(psutil, "disk_usage")
                    else 0
                ),
            }
        except ImportError:
            return {
                "memory_mb": 0,
                "cpu_percent": 0,
                "disk_usage_percent": 0,
                "note": "psutil not available",
            }

    def _calculate_health_score(self, health_data: dict[str, Any]) -> None:
        """Calculate comprehensive health score based on various metrics."""
        score = 100.0

        # Deduct points for errors
        if self.health.error_count > 0:
            score -= min(self.health.error_count * 5, 30)  # Max 30 points for errors

        # Deduct points for warnings
        if self.health.warning_count > 0:
            score -= min(
                self.health.warning_count * 2, 20
            )  # Max 20 points for warnings

        # Deduct points for retries
        if self.health.retry_count > 0:
            score -= min(self.health.retry_count * 3, 15)  # Max 15 points for retries

        # Deduct points for poor performance
        avg_response_time = self.performance_metrics.get("average_response_time", 0)
        if avg_response_time > 5.0:  # More than 5 seconds average
            score -= min(
                (avg_response_time - 5.0) * 2, 20
            )  # Max 20 points for slow performance

        # Deduct points for resource usage
        resource_usage = self._get_resource_usage()
        memory_mb = resource_usage.get("memory_mb", 0)
        if memory_mb > self.resource_limits["max_memory_mb"]:
            score -= min((memory_mb - self.resource_limits["max_memory_mb"]) / 10, 15)

        # Ensure score doesn't go below 0
        score = max(score, 0.0)

        self.health.health_score = score
        self.health.is_healthy = score >= 70.0  # Consider healthy if score >= 70

    def _get_initialization_duration_ms(self) -> float:
        """Get initialization duration in milliseconds."""
        if self.initialization_time and self.state in [
            ServiceState.INITIALIZED,
            ServiceState.STARTING,
            ServiceState.RUNNING,
            ServiceState.STOPPING,
            ServiceState.STOPPED,
        ]:
            return (
                datetime.now(APP_TIMEZONE)
                - self.initialization_time.replace(tzinfo=APP_TIMEZONE)
            ).total_seconds() * 1000
        return 0.0

    def _get_startup_duration_ms(self) -> float:
        """Get startup duration in milliseconds."""
        if self.start_time and self.state in [
            ServiceState.RUNNING,
            ServiceState.STOPPING,
            ServiceState.STOPPED,
        ]:
            return (
                datetime.now(APP_TIMEZONE)
                - self.start_time.replace(tzinfo=APP_TIMEZONE)
            ).total_seconds() * 1000
        return 0.0

    def _get_uptime_seconds(self) -> float:
        """Get service uptime in seconds."""
        if self.start_time:
            return (
                datetime.now(APP_TIMEZONE)
                - self.start_time.replace(tzinfo=APP_TIMEZONE)
            ).total_seconds()
        return 0.0

    def _get_total_lifetime_seconds(self) -> float:
        """Get total service lifetime in seconds."""
        if self.initialization_time:
            return (
                datetime.now(APP_TIMEZONE)
                - self.initialization_time.replace(tzinfo=APP_TIMEZONE)
            ).total_seconds()
        return 0.0

    async def _force_cleanup(self) -> None:
        """Force cleanup when normal cleanup fails."""
        try:
            await self._cleanup()
        except Exception as e:
            log_event(
                "ERROR",
                f"Force cleanup failed for service '{self.service_name}'",
                {"error": str(e)},
            )

    # =========================================================================
    # Abstract Methods (must be implemented by subclasses)
    # =========================================================================

    @abstractmethod
    async def _initialize(self) -> None:
        """Initialize service-specific components."""
        pass

    @abstractmethod
    async def _start(self) -> None:
        """Start service-specific functionality."""
        pass

    @abstractmethod
    async def _stop(self) -> None:
        """Stop service-specific functionality."""
        pass

    @abstractmethod
    async def _cleanup(self) -> None:
        """Clean up service-specific resources."""
        pass

    @abstractmethod
    async def _health_check(self) -> dict[str, Any]:
        """Perform service-specific health check."""
        pass
