# =============================================================================
# QuranBot - Dependency Injection Container
# =============================================================================
# Lightweight, type-safe dependency injection for clean architecture.
# Manages service lifecycles and dependencies for a production Discord bot.
#
# Features:
# - Singleton and transient service registration
# - Type-safe service resolution
# - Async service lifecycle management
# - Circular dependency detection
# - Clean service shutdown for 24/7 operation
# =============================================================================

from collections.abc import Callable
from dataclasses import dataclass
import inspect
from typing import Any, TypeVar

from .logger import TreeLogger


T = TypeVar("T")


@dataclass
class ServiceRegistration:
    """Service registration metadata."""

    service_type: type
    factory: Callable
    singleton: bool
    instance: Any | None = None
    dependencies: set[type] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = set()


class DIContainer:
    """
    Lightweight dependency injection container for QuranBot.

    Manages service registration, resolution, and lifecycle for clean architecture.
    Designed for single-server Discord bot deployment with 24/7 reliability.
    """

    def __init__(self):
        """Initialize empty DI container."""
        self._registrations: dict[type, ServiceRegistration] = {}
        self._resolution_stack: set[type] = set()
        # Logger is now handled by log_event function

        # Register self for services that need DI container access
        self.register_singleton(DIContainer, self)

        TreeLogger.info(
            "Dependency Injection Container initialized",
            {"status": "initialized"},
            service="DIContainer",
        )

    def register_singleton(
        self, service_type: type[T], instance_or_factory: T | Callable[[], T]
    ) -> None:
        """
        Register a singleton service (single instance per container).

        Args:
            service_type: The service type/interface
            instance_or_factory: Pre-created instance or factory function
        """
        if callable(instance_or_factory) and not isinstance(
            instance_or_factory, service_type
        ):
            # Factory function
            registration = ServiceRegistration(
                service_type=service_type, factory=instance_or_factory, singleton=True
            )
        else:
            # Pre-created instance
            registration = ServiceRegistration(
                service_type=service_type,
                factory=lambda: instance_or_factory,
                singleton=True,
                instance=instance_or_factory,
            )

        self._registrations[service_type] = registration

        TreeLogger.success(
            f"Singleton service registered: {service_type.__name__}",
            {"type": "singleton", "factory": callable(instance_or_factory)},
            service="DIContainer",
        )

    def register_transient(
        self, service_type: type[T], factory: Callable[[], T]
    ) -> None:
        """
        Register a transient service (new instance per resolution).

        Args:
            service_type: The service type/interface
            factory: Factory function to create instances
        """
        registration = ServiceRegistration(
            service_type=service_type, factory=factory, singleton=False
        )

        self._registrations[service_type] = registration

        TreeLogger.success(
            f"Transient service registered: {service_type.__name__}",
            {"type": "transient"},
            service="DIContainer",
        )

    def register_factory(
        self,
        service_type: type[T],
        factory: Callable[["DIContainer"], T],
        singleton: bool = True,
    ) -> None:
        """
        Register a service with a factory that receives the DI container.

        Args:
            service_type: The service type/interface
            factory: Factory function that receives DIContainer as parameter
            singleton: Whether to register as singleton (default) or transient
        """

        def container_factory():
            return factory(self)

        registration = ServiceRegistration(
            service_type=service_type, factory=container_factory, singleton=singleton
        )

        self._registrations[service_type] = registration

        service_scope = "singleton" if singleton else "transient"
        TreeLogger.success(
            f"Factory service registered: {service_type.__name__}",
            {"type": service_scope, "factory": "container_aware"},
            service="DIContainer",
        )

    def get(self, service_type: type[T]) -> T:
        """
        Get a service instance by type.

        Args:
            service_type: The service type to resolve

        Returns:
            Service instance

        Raises:
            KeyError: If service is not registered
        """
        return self.get_service(service_type)

    def get_service(self, service_type: type[T]) -> T:
        """
        Resolve a service instance from the container.

        Args:
            service_type: The service type to resolve

        Returns:
            Service instance

        Raises:
            ValueError: If service is not registered or circular dependency detected
        """
        if service_type in self._resolution_stack:
            raise ValueError(
                f"Circular dependency detected for {service_type.__name__}"
            )

        if service_type not in self._registrations:
            raise ValueError(f"Service {service_type.__name__} is not registered")

        registration = self._registrations[service_type]

        # Return cached singleton instance if available
        if registration.singleton and registration.instance is not None:
            return registration.instance

        # Resolve dependencies and create instance
        self._resolution_stack.add(service_type)

        try:
            instance = registration.factory()

            # Cache singleton instance
            if registration.singleton:
                registration.instance = instance

            return instance

        except Exception as e:
            TreeLogger.error(
                f"Failed to resolve service: {service_type.__name__}",
                None,
                e,
                {
                    "registration_type": (
                        "singleton" if registration.singleton else "transient"
                    )
                },
                service="DIContainer",
            )
            raise
        finally:
            self._resolution_stack.discard(service_type)

    def is_registered(self, service_type: type) -> bool:
        """
        Check if a service type is registered.

        Args:
            service_type: The service type to check

        Returns:
            True if registered, False otherwise
        """
        return service_type in self._registrations

    def get_registered_services(self) -> dict[str, dict[str, Any]]:
        """
        Get information about all registered services.

        Returns:
            Dictionary of service information
        """
        services = {}
        for service_type, registration in self._registrations.items():
            services[service_type.__name__] = {
                "type": "singleton" if registration.singleton else "transient",
                "has_instance": registration.instance is not None,
                "dependencies": [dep.__name__ for dep in registration.dependencies],
            }
        return services

    def get_all_services(self) -> dict[str, Any]:
        """
        Get all registered services as a dictionary.

        Returns:
            Dictionary of service names to instances
        """
        services = {}
        for service_type, registration in self._registrations.items():
            if registration.instance is not None:
                services[service_type.__name__] = registration.instance
        return services
        """
        Get information about all registered services.

        Returns:
            Dictionary with service information
        """
        services = {}
        for service_type, registration in self._registrations.items():
            services[service_type.__name__] = {
                "type": "singleton" if registration.singleton else "transient",
                "has_instance": registration.instance is not None,
                "dependencies_count": len(registration.dependencies),
            }
        return services

    async def initialize_async_services(self) -> None:
        """
        Initialize all registered services that have async initialize() methods.
        Call this after all services are registered but before using the bot.
        """
        TreeLogger.info(
            "Initializing async services", {"status": "starting"}, service="DIContainer"
        )

        initialized_count = 0
        for service_type, registration in self._registrations.items():
            try:
                # Get or create instance
                instance = self.get(service_type)

                # Check if it has async initialize method
                if hasattr(instance, "initialize") and inspect.iscoroutinefunction(
                    instance.initialize
                ):
                    await instance.initialize()
                    initialized_count += 1

                    TreeLogger.success(
                        f"Async service initialized: {service_type.__name__}",
                        {"method": "initialize()"},
                        service="DIContainer",
                    )

            except Exception as e:
                TreeLogger.error(
                    f"Failed to initialize async service: {service_type.__name__}",
                    e,
                    None,
                    service="DIContainer",
                )
                raise

        TreeLogger.info(
            "Async Services Initialization Complete",
            {
                "total_services": len(self._registrations),
                "async_initialized": initialized_count,
                "status": "✅ Ready for operation",
            },
        )

    async def shutdown_async_services(self) -> None:
        """
        Shutdown all registered services that have async shutdown() methods.
        Call this during bot shutdown for clean resource cleanup.
        """
        TreeLogger.warning(
            "Shutting down async services",
            {"status": "starting_shutdown"},
            service="DIContainer",
        )

        shutdown_count = 0
        for service_type, registration in self._registrations.items():
            if registration.instance is None:
                continue

            try:
                instance = registration.instance

                # Check if it has async shutdown method
                if hasattr(instance, "shutdown") and inspect.iscoroutinefunction(
                    instance.shutdown
                ):
                    await instance.shutdown()
                    shutdown_count += 1

                    TreeLogger.success(
                        f"Service shutdown: {service_type.__name__}",
                        {"method": "shutdown()"},
                        service="DIContainer",
                    )

            except Exception as e:
                TreeLogger.error(
                    f"Error shutting down service: {service_type.__name__}",
                    e,
                    None,
                    service="DIContainer",
                )
                # Continue shutdown process even if one service fails

        TreeLogger.info(
            "Service Shutdown Complete",
            {
                "total_services": len(self._registrations),
                "shutdown_services": shutdown_count,
                "status": "✅ Clean shutdown",
            },
        )

    def clear(self) -> None:
        """
        Clear all service registrations and instances.
        Used for testing or complete container reset.
        """
        self._registrations.clear()
        self._resolution_stack.clear()

        # Re-register self
        self.register_singleton(DIContainer, self)

        TreeLogger.warning(
            "DI Container cleared", {"status": "cleared"}, service="DIContainer"
        )
