# =============================================================================
# QuranBot - Dependency Injection Container
# =============================================================================
# Dependency Injection Container for QuranBot.
# This module provides a lightweight dependency injection container that manages
# service registration and resolution throughout the application. It supports
# both singleton and transient service lifetimes with proper error handling.
# =============================================================================

from collections.abc import Callable
from functools import wraps
import inspect
import threading
from typing import Any, TypeVar

T = TypeVar("T")


class DIError(Exception):
    """Base exception for dependency injection errors."""

    pass


class ServiceNotRegisteredError(DIError):
    """Raised when attempting to resolve an unregistered service."""

    pass


class CircularDependencyError(DIError):
    """Raised when a circular dependency is detected during resolution."""

    pass


class ServiceRegistrationError(DIError):
    """Raised when service registration fails."""

    pass


class DIContainer:
    """
    Dependency injection container for service management.

    Provides centralized service registration and resolution with support for:
    - Singleton services (single instance per container)
    - Transient services (new instance per resolution)
    - Factory functions for complex service creation
    - Circular dependency detection
    - Thread-safe operations
    - Proper error handling and reporting

    Example:
        container = DIContainer()

        # Register singleton service
        container.register_singleton(ConfigService, config_instance)

        # Register transient service with factory
        container.register_transient(AudioService, lambda: AudioService(container.get(ConfigService)))

        # Resolve service
        audio_service = container.get(AudioService)
    """

    def __init__(self):
        """Initialize the dependency injection container."""
        self._singletons: dict[type, Any] = {}
        self._transient_factories: dict[type, Callable] = {}
        self._resolution_stack: set = set()
        self._lock = threading.RLock()

    def register_singleton(
        self, interface: type[T], implementation: T | Callable[[], T]
    ) -> None:
        """
        Register a singleton service.

        Singleton services are created once and reused for all subsequent requests.
        The implementation can be either an instance or a factory function.

        Args:
            interface: The service interface/type to register
            implementation: The service instance or factory function

        Raises:
            ServiceRegistrationError: If registration fails

        Example:
            # Register with instance
            container.register_singleton(ConfigService, config_instance)

            # Register with factory
            container.register_singleton(DatabaseService, lambda: DatabaseService(config))
        """
        with self._lock:
            try:
                if (
                    interface in self._singletons
                    or interface in self._transient_factories
                ):
                    raise ServiceRegistrationError(
                        f"Service {interface.__name__} is already registered"
                    )

                # Store the implementation directly - we'll determine if it's a factory during resolution
                self._singletons[interface] = implementation

            except Exception as e:
                raise ServiceRegistrationError(
                    f"Failed to register singleton {interface.__name__}: {e!s}"
                )

    def register_transient(self, interface: type[T], factory: Callable[[], T]) -> None:
        """
        Register a transient service factory.

        Transient services are created fresh for each resolution request.
        A factory function must be provided to create new instances.

        Args:
            interface: The service interface/type to register
            factory: Factory function that creates service instances

        Raises:
            ServiceRegistrationError: If registration fails

        Example:
            container.register_transient(
                AudioService,
                lambda: AudioService(container.get(ConfigService))
            )
        """
        with self._lock:
            try:
                if (
                    interface in self._singletons
                    or interface in self._transient_factories
                ):
                    raise ServiceRegistrationError(
                        f"Service {interface.__name__} is already registered"
                    )

                if not callable(factory):
                    raise ServiceRegistrationError(
                        f"Factory for {interface.__name__} must be callable"
                    )

                self._transient_factories[interface] = factory

            except Exception as e:
                raise ServiceRegistrationError(
                    f"Failed to register transient {interface.__name__}: {e!s}"
                )

    def get(self, interface: type[T]) -> T:
        """
        Resolve a service instance.

        Returns the appropriate service instance based on its registration type:
        - Singleton: Returns the same instance for all requests
        - Transient: Creates a new instance for each request

        Args:
            interface: The service interface/type to resolve

        Returns:
            The resolved service instance

        Raises:
            ServiceNotRegisteredError: If the service is not registered
            CircularDependencyError: If a circular dependency is detected

        Example:
            config_service = container.get(ConfigService)
            audio_service = container.get(AudioService)
        """
        with self._lock:
            # Check for circular dependencies
            if interface in self._resolution_stack:
                dependency_chain = " -> ".join(
                    [cls.__name__ for cls in self._resolution_stack]
                )
                raise CircularDependencyError(
                    f"Circular dependency detected: {dependency_chain} -> {interface.__name__}"
                )

            try:
                self._resolution_stack.add(interface)

                # Try singleton first
                if interface in self._singletons:
                    service = self._singletons[interface]

                    # Check if it's a factory function by trying to determine if it's a lambda or function
                    # that should be called to create the service instance
                    if callable(service) and self._is_factory_function(service):
                        instance = service()
                        self._singletons[interface] = instance
                        return instance
                    else:
                        return service

                # Try transient factory
                elif interface in self._transient_factories:
                    factory = self._transient_factories[interface]
                    return factory()

                else:
                    raise ServiceNotRegisteredError(
                        f"Service {interface.__name__} is not registered"
                    )

            finally:
                self._resolution_stack.discard(interface)

    def is_registered(self, interface: type[T]) -> bool:
        """
        Check if a service is registered.

        Args:
            interface: The service interface/type to check

        Returns:
            True if the service is registered, False otherwise
        """
        with self._lock:
            return (
                interface in self._singletons or interface in self._transient_factories
            )

    def get_registration_type(self, interface: type[T]) -> str | None:
        """
        Get the registration type of a service.

        Args:
            interface: The service interface/type to check

        Returns:
            'singleton', 'transient', or None if not registered
        """
        with self._lock:
            if interface in self._singletons:
                return "singleton"
            elif interface in self._transient_factories:
                return "transient"
            else:
                return None

    def clear(self) -> None:
        """
        Clear all registered services.

        This method removes all service registrations and should be used
        carefully, typically only in testing scenarios.
        """
        with self._lock:
            self._singletons.clear()
            self._transient_factories.clear()
            self._resolution_stack.clear()

    def get_registered_services(self) -> dict[str, str]:
        """
        Get a dictionary of all registered services and their types.

        Returns:
            Dictionary mapping service names to their registration types
        """
        with self._lock:
            services = {}

            for interface in self._singletons:
                services[interface.__name__] = "singleton"

            for interface in self._transient_factories:
                services[interface.__name__] = "transient"

            return services

    def _is_factory_function(self, obj: Any) -> bool:
        """
        Determine if an object is a factory function that should be called.

        This method tries to distinguish between:
        - Factory functions (lambdas, regular functions) that should be called
        - Service instances that should be returned directly

        Args:
            obj: The object to check

        Returns:
            True if the object should be called as a factory, False otherwise
        """
        if not callable(obj):
            return False

        # Check if it's a lambda function
        if hasattr(obj, "__name__") and obj.__name__ == "<lambda>":
            return True

        # Check if it's a regular function (not a method or class)
        if inspect.isfunction(obj):
            return True

        # Check if it's a method or bound method
        if inspect.ismethod(obj):
            return True

        # If it has a __call__ method but is not a type/class, it might be a callable object
        # that we should treat as a factory
        if callable(obj) and not inspect.isclass(obj):
            # Additional check: if it doesn't have typical service attributes,
            # it's likely a factory function
            if not hasattr(obj, "__dict__") or len(obj.__dict__) == 0:
                return True

        return False


def inject(interface: type[T]) -> Callable:
    """
    Decorator for automatic dependency injection.

    This decorator can be used to automatically inject dependencies into
    function parameters. It requires a global container instance to be available.

    Args:
        interface: The service interface/type to inject

    Returns:
        Decorator function

    Example:
        @inject(ConfigService)
        def some_function(config: ConfigService):
            # config will be automatically injected
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # This would require a global container instance
            # Implementation depends on how the container is made available globally
            raise NotImplementedError("Global container injection not implemented yet")

        return wrapper

    return decorator
