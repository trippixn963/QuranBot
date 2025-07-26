"""
Unit tests for the Dependency Injection Container.

This module contains comprehensive tests for the DIContainer class,
covering all functionality including service registration, resolution,
error handling, and edge cases.
"""

import threading
import time
from typing import Protocol
from unittest.mock import Mock

import pytest

from src.core.di_container import (
    CircularDependencyError,
    DIContainer,
    ServiceNotRegisteredError,
    ServiceRegistrationError,
)


# Test service interfaces and implementations
class ITestService(Protocol):
    """Test service interface."""

    def get_value(self) -> str:
        ...


class MockTestService:
    """Simple test service implementation."""

    def __init__(self, value: str = "test"):
        self.value = value

    def get_value(self) -> str:
        return self.value


class IDependentService(Protocol):
    """Service that depends on another service."""

    def get_dependency_value(self) -> str:
        ...


class MockDependentService:
    """Service that depends on TestService."""

    def __init__(self, test_service: ITestService):
        self.test_service = test_service

    def get_dependency_value(self) -> str:
        return f"dependent_{self.test_service.get_value()}"


class ICircularServiceA(Protocol):
    """First service in circular dependency."""

    def get_name(self) -> str:
        ...


class ICircularServiceB(Protocol):
    """Second service in circular dependency."""

    def get_name(self) -> str:
        ...


class MockCircularServiceA:
    """Service that creates circular dependency."""

    def __init__(self, service_b: ICircularServiceB):
        self.service_b = service_b

    def get_name(self) -> str:
        return "service_a"


class MockCircularServiceB:
    """Service that creates circular dependency."""

    def __init__(self, service_a: ICircularServiceA):
        self.service_a = service_a

    def get_name(self) -> str:
        return "service_b"


class TestDIContainer:
    """Test suite for DIContainer."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.container = DIContainer()

    def test_container_initialization(self):
        """Test that container initializes correctly."""
        assert self.container is not None
        assert len(self.container.get_registered_services()) == 0

    def test_register_singleton_with_instance(self):
        """Test registering a singleton service with an instance."""
        service_instance = MockTestService("singleton_test")

        self.container.register_singleton(ITestService, service_instance)

        assert self.container.is_registered(ITestService)
        assert self.container.get_registration_type(ITestService) == "singleton"

    def test_register_singleton_with_factory(self):
        """Test registering a singleton service with a factory function."""
        factory = lambda: MockTestService("factory_test")

        self.container.register_singleton(ITestService, factory)

        assert self.container.is_registered(ITestService)
        assert self.container.get_registration_type(ITestService) == "singleton"

    def test_register_transient(self):
        """Test registering a transient service."""
        factory = lambda: MockTestService("transient_test")

        self.container.register_transient(ITestService, factory)

        assert self.container.is_registered(ITestService)
        assert self.container.get_registration_type(ITestService) == "transient"

    def test_resolve_singleton_instance(self):
        """Test resolving a singleton service registered with an instance."""
        service_instance = MockTestService("singleton_instance")
        self.container.register_singleton(ITestService, service_instance)

        resolved1 = self.container.get(ITestService)
        resolved2 = self.container.get(ITestService)

        assert resolved1 is service_instance
        assert resolved2 is service_instance
        assert resolved1 is resolved2
        assert resolved1.get_value() == "singleton_instance"

    def test_resolve_singleton_factory(self):
        """Test resolving a singleton service registered with a factory."""
        factory = lambda: MockTestService("singleton_factory")
        self.container.register_singleton(ITestService, factory)

        resolved1 = self.container.get(ITestService)
        resolved2 = self.container.get(ITestService)

        assert resolved1 is resolved2  # Same instance
        assert resolved1.get_value() == "singleton_factory"

    def test_resolve_transient(self):
        """Test resolving a transient service."""
        factory = lambda: MockTestService("transient")
        self.container.register_transient(ITestService, factory)

        resolved1 = self.container.get(ITestService)
        resolved2 = self.container.get(ITestService)

        assert resolved1 is not resolved2  # Different instances
        assert resolved1.get_value() == "transient"
        assert resolved2.get_value() == "transient"

    def test_service_not_registered_error(self):
        """Test that ServiceNotRegisteredError is raised for unregistered services."""
        with pytest.raises(ServiceNotRegisteredError) as exc_info:
            self.container.get(ITestService)

        assert "ITestService is not registered" in str(exc_info.value)

    def test_duplicate_registration_error(self):
        """Test that duplicate service registration raises an error."""
        service_instance = MockTestService("test")
        self.container.register_singleton(ITestService, service_instance)

        with pytest.raises(ServiceRegistrationError) as exc_info:
            self.container.register_singleton(ITestService, service_instance)

        assert "ITestService is already registered" in str(exc_info.value)

    def test_duplicate_registration_different_types_error(self):
        """Test that registering same service as different types raises an error."""
        service_instance = MockTestService("test")
        self.container.register_singleton(ITestService, service_instance)

        with pytest.raises(ServiceRegistrationError) as exc_info:
            self.container.register_transient(
                ITestService, lambda: MockTestService("transient")
            )

        assert "ITestService is already registered" in str(exc_info.value)

    def test_transient_non_callable_factory_error(self):
        """Test that registering transient with non-callable factory raises an error."""
        with pytest.raises(ServiceRegistrationError) as exc_info:
            self.container.register_transient(ITestService, "not_callable")

        assert "Factory for ITestService must be callable" in str(exc_info.value)

    def test_circular_dependency_detection(self):
        """Test that circular dependencies are detected and raise an error."""
        # Register services that depend on each other
        self.container.register_singleton(
            ICircularServiceA,
            lambda: MockCircularServiceA(self.container.get(ICircularServiceB)),
        )
        self.container.register_singleton(
            ICircularServiceB,
            lambda: MockCircularServiceB(self.container.get(ICircularServiceA)),
        )

        with pytest.raises(CircularDependencyError) as exc_info:
            self.container.get(ICircularServiceA)

        assert "Circular dependency detected" in str(exc_info.value)
        assert "ICircularServiceA" in str(exc_info.value)
        assert "ICircularServiceB" in str(exc_info.value)

    def test_dependency_injection_chain(self):
        """Test that services can depend on other services."""
        # Register the dependency first
        self.container.register_singleton(ITestService, MockTestService("dependency"))

        # Register the dependent service
        self.container.register_singleton(
            IDependentService,
            lambda: MockDependentService(self.container.get(ITestService)),
        )

        dependent = self.container.get(IDependentService)

        assert dependent.get_dependency_value() == "dependent_dependency"

    def test_is_registered(self):
        """Test the is_registered method."""
        assert not self.container.is_registered(ITestService)

        self.container.register_singleton(ITestService, MockTestService("test"))

        assert self.container.is_registered(ITestService)

    def test_get_registration_type(self):
        """Test the get_registration_type method."""
        assert self.container.get_registration_type(ITestService) is None

        self.container.register_singleton(ITestService, MockTestService("test"))
        assert self.container.get_registration_type(ITestService) == "singleton"

        self.container.register_transient(
            IDependentService, lambda: MockDependentService(Mock())
        )
        assert self.container.get_registration_type(IDependentService) == "transient"

    def test_get_registered_services(self):
        """Test the get_registered_services method."""
        assert self.container.get_registered_services() == {}

        self.container.register_singleton(ITestService, MockTestService("test"))
        self.container.register_transient(
            IDependentService, lambda: MockDependentService(Mock())
        )

        services = self.container.get_registered_services()

        assert len(services) == 2
        assert services["ITestService"] == "singleton"
        assert services["IDependentService"] == "transient"

    def test_clear(self):
        """Test the clear method."""
        self.container.register_singleton(ITestService, MockTestService("test"))
        self.container.register_transient(
            IDependentService, lambda: MockDependentService(Mock())
        )

        assert len(self.container.get_registered_services()) == 2

        self.container.clear()

        assert len(self.container.get_registered_services()) == 0
        assert not self.container.is_registered(ITestService)
        assert not self.container.is_registered(IDependentService)

    def test_thread_safety_singleton(self):
        """Test that singleton resolution is thread-safe."""
        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            time.sleep(0.01)  # Small delay to increase chance of race condition
            return MockTestService(f"thread_test_{call_count}")

        self.container.register_singleton(ITestService, factory)

        results = []

        def resolve_service():
            service = self.container.get(ITestService)
            results.append(service)

        # Create multiple threads that resolve the same singleton
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=resolve_service)
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All results should be the same instance
        assert len(results) == 10
        first_instance = results[0]
        for result in results:
            assert result is first_instance

        # Factory should only be called once
        assert call_count == 1

    def test_thread_safety_transient(self):
        """Test that transient resolution is thread-safe."""
        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return MockTestService(f"transient_{call_count}")

        self.container.register_transient(ITestService, factory)

        results = []

        def resolve_service():
            service = self.container.get(ITestService)
            results.append(service)

        # Create multiple threads that resolve the transient service
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=resolve_service)
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All results should be different instances
        assert len(results) == 5
        for i, result in enumerate(results):
            for j, other_result in enumerate(results):
                if i != j:
                    assert result is not other_result

        # Factory should be called for each resolution
        assert call_count == 5

    def test_factory_exception_handling(self):
        """Test that exceptions in factory functions are properly handled."""

        def failing_factory():
            raise ValueError("Factory failed")

        self.container.register_singleton(ITestService, failing_factory)

        with pytest.raises(ValueError) as exc_info:
            self.container.get(ITestService)

        assert "Factory failed" in str(exc_info.value)

    def test_registration_exception_handling(self):
        """Test exception handling during service registration."""
        # Test with invalid factory for transient
        with pytest.raises(ServiceRegistrationError):
            self.container.register_transient(ITestService, None)

    def test_complex_dependency_chain(self):
        """Test a complex chain of dependencies."""

        # Create a chain: ServiceC -> ServiceB -> ServiceA
        class ServiceA:
            def get_name(self):
                return "A"

        class ServiceB:
            def __init__(self, service_a):
                self.service_a = service_a

            def get_name(self):
                return f"B->{self.service_a.get_name()}"

        class ServiceC:
            def __init__(self, service_b):
                self.service_b = service_b

            def get_name(self):
                return f"C->{self.service_b.get_name()}"

        # Register services
        self.container.register_singleton(ServiceA, ServiceA())
        self.container.register_singleton(
            ServiceB, lambda: ServiceB(self.container.get(ServiceA))
        )
        self.container.register_singleton(
            ServiceC, lambda: ServiceC(self.container.get(ServiceB))
        )

        # Resolve the top-level service
        service_c = self.container.get(ServiceC)

        assert service_c.get_name() == "C->B->A"


class TestDIContainerEdgeCases:
    """Test edge cases and error conditions for DIContainer."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.container = DIContainer()

    def test_empty_container_operations(self):
        """Test operations on an empty container."""
        assert not self.container.is_registered(ITestService)
        assert self.container.get_registration_type(ITestService) is None
        assert self.container.get_registered_services() == {}

        with pytest.raises(ServiceNotRegisteredError):
            self.container.get(ITestService)

    def test_none_values(self):
        """Test handling of None values in registration."""
        # Registering None as a singleton should work (it's a valid instance)
        self.container.register_singleton(ITestService, None)

        resolved = self.container.get(ITestService)
        assert resolved is None

    def test_lambda_with_closure(self):
        """Test lambda factories with closures."""
        captured_value = "captured"

        factory = lambda: MockTestService(captured_value)
        self.container.register_singleton(ITestService, factory)

        service = self.container.get(ITestService)
        assert service.get_value() == "captured"

    def test_multiple_containers_isolation(self):
        """Test that multiple containers are isolated from each other."""
        container1 = DIContainer()
        container2 = DIContainer()

        container1.register_singleton(ITestService, MockTestService("container1"))
        container2.register_singleton(ITestService, MockTestService("container2"))

        service1 = container1.get(ITestService)
        service2 = container2.get(ITestService)

        assert service1.get_value() == "container1"
        assert service2.get_value() == "container2"
        assert service1 is not service2
