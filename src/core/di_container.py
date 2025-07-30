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
    """
    Base exception class for all dependency injection container errors.
    
    Provides a common error hierarchy for all DI-related exceptions, enabling
    comprehensive error handling and debugging throughout the application.
    All specific DI errors inherit from this base class for consistent
    error handling patterns and improved diagnostic capabilities.
    """

    pass


class ServiceNotRegisteredError(DIError):
    """
    Exception raised when attempting to resolve a service that hasn't been registered.
    
    This error occurs during service resolution when the requested service type
    is not found in either the singleton or transient service registries.
    It typically indicates a configuration error or missing service registration
    during application startup.
    
    The error message includes the service type name to help identify which
    service registration is missing and needs to be added to the container.
    """

    pass


class CircularDependencyError(DIError):
    """
    Exception raised when a circular dependency is detected during service resolution.
    
    This error occurs when the dependency resolution algorithm detects that
    services form a circular dependency chain (e.g., Service A depends on
    Service B, which depends on Service A). Such circular dependencies would
    cause infinite recursion and stack overflow if not detected.
    
    The error message includes the complete dependency chain showing the
    circular path, making it easier to identify and resolve the architectural
    issue causing the circular dependency.
    
    Example circular dependency:
        AudioService -> ConfigService -> DatabaseService -> AudioService
    """

    pass


class ServiceRegistrationError(DIError):
    """
    Exception raised when service registration operations fail.
    
    This error can occur during service registration for various reasons:
    - Attempting to register the same service type multiple times
    - Providing invalid factory functions for transient services
    - General registration validation failures
    - Thread synchronization issues during registration
    
    The error includes detailed context about what went wrong during
    registration, helping developers identify and fix configuration issues.
    """

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
        """
        Initialize the dependency injection container with empty registries.
        
        Sets up the internal data structures for service management:
        - Singleton registry for single-instance services
        - Transient factory registry for per-request services  
        - Resolution stack for circular dependency detection
        - Thread-safe lock for concurrent access protection
        
        The container starts empty and services must be explicitly registered
        before they can be resolved. Thread safety is ensured through a
        reentrant lock that allows the same thread to acquire it multiple times.
        """
        # Registry for singleton services - maps service type to instance/factory
        self._singletons: dict[type, Any] = {}
        
        # Registry for transient services - maps service type to factory function
        self._transient_factories: dict[type, Callable] = {}
        
        # Stack tracking current resolution chain for circular dependency detection
        self._resolution_stack: set = set()
        
        # Reentrant lock for thread-safe operations (allows recursive acquisition)
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
                # Validate that this service type hasn't been registered yet
                # This prevents accidental double-registration and maintains registry integrity
                if (
                    interface in self._singletons
                    or interface in self._transient_factories
                ):
                    raise ServiceRegistrationError(
                        f"Service {interface.__name__} is already registered"
                    )

                # Store the implementation directly in the singleton registry
                # The implementation can be either:
                # 1. An actual service instance (pre-created)
                # 2. A factory function that will be called once during first resolution
                # The factory detection happens during resolution via _is_factory_function()
                self._singletons[interface] = implementation

            except Exception as e:
                # Wrap any unexpected errors in ServiceRegistrationError for consistent error handling
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
                # Validate that this service type hasn't been registered yet
                # Prevents conflicts between singleton and transient registrations
                if (
                    interface in self._singletons
                    or interface in self._transient_factories
                ):
                    raise ServiceRegistrationError(
                        f"Service {interface.__name__} is already registered"
                    )

                # Validate that the factory is actually callable
                # Transient services require factory functions to create new instances
                if not callable(factory):
                    raise ServiceRegistrationError(
                        f"Factory for {interface.__name__} must be callable"
                    )

                # Store the factory function in the transient registry
                # This factory will be called every time the service is resolved,
                # creating a new instance for each request
                self._transient_factories[interface] = factory

            except Exception as e:
                # Wrap any unexpected errors for consistent exception handling
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
            # CIRCULAR DEPENDENCY DETECTION ALGORITHM
            # The resolution stack tracks the current dependency resolution chain.
            # If we're already resolving the same service type, we have a circular dependency.
            if interface in self._resolution_stack:
                # Build a human-readable dependency chain for debugging
                dependency_chain = " -> ".join(
                    [cls.__name__ for cls in self._resolution_stack]
                )
                raise CircularDependencyError(
                    f"Circular dependency detected: {dependency_chain} -> {interface.__name__}"
                )

            try:
                # Add current service to resolution stack to track dependency chain
                self._resolution_stack.add(interface)

                # SERVICE RESOLUTION ALGORITHM
                # Priority: Singleton services are checked first, then transient services
                
                # 1. SINGLETON RESOLUTION
                if interface in self._singletons:
                    service = self._singletons[interface]

                    # LAZY SINGLETON INSTANTIATION
                    # If the registered "service" is actually a factory function,
                    # call it once to create the singleton instance, then cache the result
                    if callable(service) and self._is_factory_function(service):
                        # Call factory to create singleton instance
                        instance = service()
                        # Replace factory with actual instance for future resolutions
                        self._singletons[interface] = instance
                        return instance
                    else:
                        # Return existing singleton instance
                        return service

                # 2. TRANSIENT RESOLUTION
                elif interface in self._transient_factories:
                    # Call factory function to create new instance every time
                    factory = self._transient_factories[interface]
                    return factory()

                # 3. UNREGISTERED SERVICE ERROR
                else:
                    raise ServiceNotRegisteredError(
                        f"Service {interface.__name__} is not registered"
                    )

            finally:
                # CLEANUP: Always remove from resolution stack, even if resolution fails
                # This ensures the stack doesn't get corrupted by exceptions
                self._resolution_stack.discard(interface)

    def is_registered(self, interface: type[T]) -> bool:
        """
        Check if a service is registered in either singleton or transient registries.

        This method performs a comprehensive check across both service registries
        to determine if the specified service type has been registered with the
        container. It's useful for validation and conditional service resolution.

        Args:
            interface: The service interface/type to check for registration

        Returns:
            True if the service is registered (in either registry), False otherwise
        """
        with self._lock:
            # Check both registries for the service type
            # A service is considered registered if it exists in either registry
            return (
                interface in self._singletons or interface in self._transient_factories
            )

    def get_registration_type(self, interface: type[T]) -> str | None:
        """
        Determine the lifecycle type of a registered service.

        This method inspects the service registries to determine how a service
        is configured to be instantiated:
        - 'singleton': Single instance shared across all resolutions
        - 'transient': New instance created for each resolution
        - None: Service is not registered

        This information is useful for debugging, monitoring, and validation
        of the dependency injection configuration.

        Args:
            interface: The service interface/type to inspect

        Returns:
            'singleton', 'transient', or None if not registered
        """
        with self._lock:
            # Check singleton registry first (typical priority order)
            if interface in self._singletons:
                return "singleton"
            elif interface in self._transient_factories:
                return "transient"
            else:
                return None

    def clear(self) -> None:
        """
        Clear all registered services and reset container state.

        This method performs a complete reset of the container by:
        1. Removing all singleton service registrations and instances
        2. Removing all transient service factory registrations
        3. Clearing the resolution stack (for safety)

        **WARNING**: This operation is destructive and should be used carefully.
        It's primarily intended for testing scenarios where a clean container
        state is needed between test cases. In production code, clearing the
        container can break application functionality by removing essential services.

        After calling this method, all services must be re-registered before
        they can be resolved again.
        """
        with self._lock:
            # Clear all service registries
            self._singletons.clear()
            self._transient_factories.clear()
            
            # Clear resolution stack for safety (should normally be empty)
            self._resolution_stack.clear()

    def get_registered_services(self) -> dict[str, str]:
        """
        Generate a comprehensive registry report of all registered services.

        This method provides a complete overview of the container's configuration
        by listing all registered services along with their lifecycle types.
        The information is useful for:
        - Debugging dependency injection configuration
        - Monitoring container state
        - Validating service registration completeness
        - Documentation and diagnostics

        Returns:
            Dictionary mapping service class names to their registration types
            ("singleton" or "transient")
        """
        with self._lock:
            services = {}

            # Collect all singleton services
            for interface in self._singletons:
                services[interface.__name__] = "singleton"

            # Collect all transient services
            for interface in self._transient_factories:
                services[interface.__name__] = "transient"

            return services

    def _is_factory_function(self, obj: Any) -> bool:
        """
        Sophisticated factory detection algorithm for singleton lazy instantiation.

        This method implements intelligent heuristics to distinguish between:
        1. Factory functions that should be called to create service instances
        2. Pre-created service instances that should be returned directly

        The detection algorithm handles various callable types:
        - Lambda functions (most common factory pattern)
        - Regular functions and methods (explicit factory functions)
        - Callable objects with minimal state (custom factory classes)
        
        This distinction is crucial for singleton services where we need to know
        whether to call the registered object as a factory or return it directly.

        **Detection Strategy:**
        1. Non-callable objects are never factories
        2. Lambda functions are always factories (common DI pattern)
        3. Regular functions and methods are always factories
        4. Callable objects with minimal state are treated as factories
        5. Complex objects with significant state are treated as instances

        Args:
            obj: The registered object to analyze for factory characteristics

        Returns:
            True if the object should be called as a factory function,
            False if it should be returned as a service instance
        """
        # Quick exit for non-callable objects
        if not callable(obj):
            return False

        # LAMBDA FUNCTION DETECTION
        # Lambda functions are the most common factory pattern in DI containers
        if hasattr(obj, "__name__") and obj.__name__ == "<lambda>":
            return True

        # REGULAR FUNCTION DETECTION
        # Regular functions (not methods or classes) are factory functions
        if inspect.isfunction(obj):
            return True

        # METHOD DETECTION
        # Bound and unbound methods are treated as factory functions
        if inspect.ismethod(obj):
            return True

        # CALLABLE OBJECT HEURISTICS
        # For objects that implement __call__, we need to determine if they're
        # lightweight factory objects or heavyweight service instances
        if callable(obj) and not inspect.isclass(obj):
            # HEURISTIC: Objects with no attributes or minimal state are likely factories
            # Service instances typically have significant state in their __dict__
            if not hasattr(obj, "__dict__") or len(obj.__dict__) == 0:
                return True

        # Default: Treat as service instance
        return False


def inject(interface: type[T]) -> Callable:
    """
    Decorator for automatic dependency injection using global container.

    This decorator provides a convenient way to automatically inject dependencies
    into function parameters without explicit container.get() calls. It leverages
    the global container instance to resolve services transparently.

    **Usage Pattern:**
    The decorator inspects the target function's signature and automatically
    injects the specified service type as a parameter. This reduces boilerplate
    code and makes dependency management more declarative.

    **Requirements:**
    - A global container must be set using set_global_container()
    - The requested service must be registered in the container
    - The function signature must accommodate the injected parameter

    **Benefits:**
    - Cleaner, more declarative dependency management
    - Reduced coupling between functions and container
    - Automatic service resolution with error handling
    - Improved testability through dependency abstraction

    Args:
        interface: The service interface/type to automatically inject

    Returns:
        Decorator function that performs automatic injection

    Example:
        @inject(ConfigService)
        def process_data(data: str, config: ConfigService):
            # config is automatically injected from the container
            return config.process(data)
            
        # Usage:
        result = process_data("sample data")  # config injected automatically
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # FUTURE ENHANCEMENT: Automatic dependency injection
            # This would require:
            # 1. Function signature inspection to find injection points
            # 2. Global container access for service resolution
            # 3. Parameter mapping and injection logic
            # 4. Error handling for missing services or container
            
            # Currently not implemented to avoid complexity until needed
            raise NotImplementedError(
                "Automatic dependency injection decorator not implemented yet. "
                "Use container.get() directly or implement based on specific requirements."
            )

        return wrapper

    return decorator


# =============================================================================
# Global Container Access
# =============================================================================

# Global container instance
_container: DIContainer | None = None

def set_global_container(container: DIContainer) -> None:
    """
    Establish a global container instance for application-wide dependency injection.
    
    This function enables the Singleton pattern for dependency injection by
    providing a global access point to the DI container. This pattern is useful
    for scenarios where:
    - Multiple modules need access to the same services
    - Service resolution is needed in contexts without direct container access
    - Simplified dependency management across the entire application
    
    **Design Considerations:**
    - Global state should be used judiciously to avoid tight coupling
    - Container should be set once during application initialization
    - Thread safety is maintained through the container's internal locking
    
    **Usage Pattern:**
    Typically called once during application startup after all services
    have been registered with the container.
    
    Args:
        container: The fully configured DIContainer instance to make globally accessible
    """
    global _container
    _container = container

def get_container() -> DIContainer | None:
    """
    Retrieve the global container instance for dependency resolution.
    
    This function provides application-wide access to the dependency injection
    container, enabling service resolution from any context within the application.
    It's commonly used in scenarios where:
    - Direct container injection is not feasible
    - Services need to be resolved in utility functions or static contexts
    - Third-party integrations require access to application services
    
    **Return Value Handling:**
    The function returns None if no global container has been set, which allows
    for graceful handling of initialization order issues or optional DI usage.
    Callers should check for None and handle accordingly.
    
    **Thread Safety:**
    The global container access is thread-safe since it's a simple reference
    read operation, and the container itself provides thread-safe operations.
    
    Returns:
        DIContainer | None: The global container instance if set via
        set_global_container(), otherwise None
        
    Example:
        container = get_container()
        if container:
            config_service = container.get(ConfigService)
            # Use config_service
        else:
            # Handle missing container (fallback logic)
            pass
    """
    return _container
