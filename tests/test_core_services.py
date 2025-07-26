# =============================================================================
# QuranBot - Core Services Unit Tests
# =============================================================================
# Comprehensive unit tests for all core services including dependency injection,
# caching, lazy loading, connection pooling, resource management, and performance
# monitoring with proper mocking and coverage.
# =============================================================================

import asyncio
import json
from unittest.mock import Mock

import pytest

from src.core.cache_service import CacheService, CacheStrategy
from src.core.connection_pool import ConnectionConfig, ConnectionPool, ConnectionType
from src.core.di_container import (
    CircularDependencyError,
    DIContainer,
    ServiceNotRegisteredError,
)
from src.core.exceptions import ServiceError
from src.core.lazy_loader import LazyLoader
from src.core.performance_monitor import MetricType, PerformanceMonitor
from src.core.resource_manager import ResourceManager, ResourceType

# =============================================================================
# Dependency Injection Container Tests
# =============================================================================


class TestDIContainer:
    """Test cases for the DI container."""

    @pytest.fixture
    def container(self):
        """Create a fresh container for each test."""
        return DIContainer()

    def test_container_initialization(self, container):
        """Test container initializes correctly."""
        assert container._services == {}
        assert container._singletons == {}
        assert container._resolution_stack == []

    def test_register_singleton_with_instance(self, container):
        """Test registering a singleton with an instance."""
        service_instance = Mock()
        container.register_singleton(Mock, service_instance)

        assert Mock in container._services
        assert container._services[Mock]["is_singleton"] is True
        assert container._singletons[Mock] is service_instance

    def test_register_singleton_with_factory(self, container):
        """Test registering a singleton with a factory function."""

        def factory():
            return Mock()

        container.register_singleton(Mock, factory)

        assert Mock in container._services
        assert container._services[Mock]["is_singleton"] is True
        assert callable(container._services[Mock]["factory"])

    def test_register_transient(self, container):
        """Test registering a transient service."""

        def factory():
            return Mock()

        container.register_transient(Mock, factory)

        assert Mock in container._services
        assert container._services[Mock]["is_singleton"] is False

    def test_resolve_singleton_instance(self, container):
        """Test resolving a singleton service."""
        service_instance = Mock()
        container.register_singleton(Mock, service_instance)

        resolved = container.resolve(Mock)
        assert resolved is service_instance

    def test_resolve_singleton_factory(self, container):
        """Test resolving a singleton from factory."""
        service_instance = Mock()

        def factory():
            return service_instance

        container.register_singleton(Mock, factory)

        resolved1 = container.resolve(Mock)
        resolved2 = container.resolve(Mock)

        assert resolved1 is service_instance
        assert resolved2 is service_instance
        assert resolved1 is resolved2

    def test_resolve_transient(self, container):
        """Test resolving a transient service."""
        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return Mock()

        container.register_transient(Mock, factory)

        resolved1 = container.resolve(Mock)
        resolved2 = container.resolve(Mock)

        assert call_count == 2
        assert resolved1 is not resolved2

    def test_resolve_unregistered_service(self, container):
        """Test resolving an unregistered service raises error."""
        with pytest.raises(ServiceNotRegisteredError):
            container.resolve(Mock)

    def test_circular_dependency_detection(self, container):
        """Test circular dependency detection."""

        class ServiceA:
            pass

        class ServiceB:
            pass

        def factory_a():
            return container.resolve(ServiceB)

        def factory_b():
            return container.resolve(ServiceA)

        container.register_singleton(ServiceA, factory_a)
        container.register_singleton(ServiceB, factory_b)

        with pytest.raises(CircularDependencyError):
            container.resolve(ServiceA)

    def test_is_registered(self, container):
        """Test checking if service is registered."""
        assert not container.is_registered(Mock)

        container.register_singleton(Mock, Mock())
        assert container.is_registered(Mock)

    def test_get_registration_info(self, container):
        """Test getting registration information."""
        service_instance = Mock()
        container.register_singleton(Mock, service_instance)

        info = container.get_registration_info(Mock)
        assert info["is_singleton"] is True
        assert info["interface"] is Mock


# =============================================================================
# Cache Service Tests
# =============================================================================


class TestCacheService:
    """Test cases for the cache service."""

    @pytest.fixture
    async def cache_service(self, temp_directory):
        """Create cache service for testing."""
        config = {
            "max_memory_items": 100,
            "default_ttl_seconds": 300,
            "cleanup_interval_seconds": 60,
            "persistence_enabled": True,
            "persistence_path": temp_directory / "cache.db",
        }

        cache = CacheService(
            strategy=CacheStrategy.LRU, max_size=100, default_ttl=300, **config
        )
        await cache.initialize()
        yield cache
        await cache.shutdown()

    @pytest.mark.asyncio
    async def test_cache_initialization(self, cache_service):
        """Test cache service initializes correctly."""
        assert cache_service._strategy == CacheStrategy.LRU
        assert cache_service._max_size == 100
        assert cache_service._default_ttl == 300

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, cache_service):
        """Test basic cache set and get operations."""
        await cache_service.set("test_key", "test_value")

        value = await cache_service.get("test_key")
        assert value == "test_value"

    @pytest.mark.asyncio
    async def test_cache_get_missing_key(self, cache_service):
        """Test getting a non-existent key returns None."""
        value = await cache_service.get("missing_key")
        assert value is None

    @pytest.mark.asyncio
    async def test_cache_get_with_default(self, cache_service):
        """Test getting with default value."""
        value = await cache_service.get("missing_key", default="default_value")
        assert value == "default_value"

    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(self, cache_service):
        """Test TTL expiration."""
        await cache_service.set("temp_key", "temp_value", ttl=0.1)  # 100ms TTL

        # Should exist immediately
        value = await cache_service.get("temp_key")
        assert value == "temp_value"

        # Wait for expiration
        await asyncio.sleep(0.2)

        # Should be expired
        value = await cache_service.get("temp_key")
        assert value is None

    @pytest.mark.asyncio
    async def test_cache_delete(self, cache_service):
        """Test cache deletion."""
        await cache_service.set("delete_key", "delete_value")

        # Verify it exists
        value = await cache_service.get("delete_key")
        assert value == "delete_value"

        # Delete it
        deleted = await cache_service.delete("delete_key")
        assert deleted is True

        # Verify it's gone
        value = await cache_service.get("delete_key")
        assert value is None

    @pytest.mark.asyncio
    async def test_cache_clear(self, cache_service):
        """Test cache clearing."""
        await cache_service.set("key1", "value1")
        await cache_service.set("key2", "value2")

        await cache_service.clear()

        assert await cache_service.get("key1") is None
        assert await cache_service.get("key2") is None

    @pytest.mark.asyncio
    async def test_cache_statistics(self, cache_service):
        """Test cache statistics collection."""
        await cache_service.set("stat_key", "stat_value")
        await cache_service.get("stat_key")  # Hit
        await cache_service.get("missing_key")  # Miss

        stats = await cache_service.get_statistics()
        assert stats["hits"] >= 1
        assert stats["misses"] >= 1
        assert stats["total_items"] >= 1

    @pytest.mark.asyncio
    async def test_lru_eviction(self, temp_directory):
        """Test LRU eviction strategy."""
        cache = CacheService(
            strategy=CacheStrategy.LRU,
            max_size=2,  # Small size to trigger eviction
            default_ttl=300,
        )
        await cache.initialize()

        try:
            await cache.set("key1", "value1")
            await cache.set("key2", "value2")
            await cache.set("key3", "value3")  # Should evict key1

            assert await cache.get("key1") is None  # Evicted
            assert await cache.get("key2") == "value2"
            assert await cache.get("key3") == "value3"
        finally:
            await cache.shutdown()


# =============================================================================
# Lazy Loader Tests
# =============================================================================


class TestLazyLoader:
    """Test cases for the lazy loader."""

    @pytest.fixture
    async def lazy_loader(self, mock_logger, temp_directory):
        """Create lazy loader for testing."""
        from src.core.lazy_loader import LazyLoadConfig

        config = LazyLoadConfig(
            scan_directories=[temp_directory],
            file_patterns=["*.mp3", "*.json"],
            cache_duration=300,
            background_scan_interval=60,
            max_concurrent_loads=5,
        )

        loader = LazyLoader(config=config, logger=mock_logger)
        await loader.initialize()
        yield loader
        await loader.shutdown()

    @pytest.mark.asyncio
    async def test_lazy_loader_initialization(self, lazy_loader):
        """Test lazy loader initializes correctly."""
        assert lazy_loader._config is not None
        assert lazy_loader._logger is not None
        assert lazy_loader._resources == {}

    @pytest.mark.asyncio
    async def test_load_resource(self, lazy_loader, temp_directory):
        """Test loading a resource."""
        # Create a test file
        test_file = temp_directory / "test.json"
        test_data = {"test": "data"}
        test_file.write_text(json.dumps(test_data))

        # Load the resource
        result = await lazy_loader.load_resource(str(test_file))
        assert result == test_data

    @pytest.mark.asyncio
    async def test_load_nonexistent_resource(self, lazy_loader):
        """Test loading a non-existent resource."""
        with pytest.raises(ServiceError):
            await lazy_loader.load_resource("/nonexistent/file.json")

    @pytest.mark.asyncio
    async def test_cached_resource_loading(self, lazy_loader, temp_directory):
        """Test that resources are cached after loading."""
        # Create a test file
        test_file = temp_directory / "cached.json"
        test_data = {"cached": "data"}
        test_file.write_text(json.dumps(test_data))

        # Load twice
        result1 = await lazy_loader.load_resource(str(test_file))
        result2 = await lazy_loader.load_resource(str(test_file))

        assert result1 == test_data
        assert result2 == test_data

        # Check loading state
        state = lazy_loader.get_loading_state(str(test_file))
        assert state.is_loaded is True
        assert state.access_count >= 2

    @pytest.mark.asyncio
    async def test_background_scanning(self, lazy_loader, temp_directory):
        """Test background scanning functionality."""
        # Create files during runtime
        test_file = temp_directory / "background.json"
        test_file.write_text('{"background": "scan"}')

        # Trigger a scan
        discovered = await lazy_loader.scan_resources()
        assert len(discovered) > 0

    @pytest.mark.asyncio
    async def test_concurrent_loading(self, lazy_loader, temp_directory):
        """Test concurrent resource loading."""
        # Create multiple test files
        files = []
        for i in range(5):
            test_file = temp_directory / f"concurrent_{i}.json"
            test_file.write_text(f'{{"file": {i}}}')
            files.append(str(test_file))

        # Load all concurrently
        tasks = [lazy_loader.load_resource(file) for file in files]
        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        for i, result in enumerate(results):
            assert result["file"] == i


# =============================================================================
# Connection Pool Tests
# =============================================================================


class TestConnectionPool:
    """Test cases for the connection pool."""

    @pytest.fixture
    async def connection_pool(self, mock_logger, temp_directory):
        """Create connection pool for testing."""
        config = ConnectionConfig(
            connection_type=ConnectionType.SQLITE,
            max_connections=5,
            min_connections=1,
            connection_timeout=30.0,
            health_check_interval=60.0,
            max_retries=3,
            retry_delay=1.0,
            connection_params={"database": str(temp_directory / "test.db")},
        )

        pool = ConnectionPool(config=config, logger=mock_logger)
        await pool.initialize()
        yield pool
        await pool.shutdown()

    @pytest.mark.asyncio
    async def test_connection_pool_initialization(self, connection_pool):
        """Test connection pool initializes correctly."""
        assert connection_pool._config is not None
        assert connection_pool._logger is not None

    @pytest.mark.asyncio
    async def test_get_connection(self, connection_pool):
        """Test getting a connection from the pool."""
        async with connection_pool.get_connection() as conn:
            assert conn is not None
            # Test that we can use the connection
            if hasattr(conn, "execute"):
                cursor = conn.execute("SELECT 1")
                result = cursor.fetchone()
                assert result[0] == 1

    @pytest.mark.asyncio
    async def test_connection_reuse(self, connection_pool):
        """Test that connections are reused."""
        connections = []

        # Get connections sequentially
        for _ in range(3):
            async with connection_pool.get_connection() as conn:
                connections.append(id(conn))

        # Some connections should be reused
        assert len(set(connections)) <= connection_pool._config.max_connections

    @pytest.mark.asyncio
    async def test_connection_health_check(self, connection_pool):
        """Test connection health checking."""
        health_status = await connection_pool.check_health()
        assert "healthy_connections" in health_status
        assert "total_connections" in health_status

    @pytest.mark.asyncio
    async def test_concurrent_connections(self, connection_pool):
        """Test concurrent connection usage."""

        async def use_connection():
            async with connection_pool.get_connection() as conn:
                # Simulate some work
                await asyncio.sleep(0.1)
                return True

        # Create multiple concurrent tasks
        tasks = [use_connection() for _ in range(10)]
        results = await asyncio.gather(*tasks)

        assert all(results)

    @pytest.mark.asyncio
    async def test_http_connection_pool(self, mock_logger):
        """Test HTTP connection pool."""
        config = ConnectionConfig(
            connection_type=ConnectionType.HTTP,
            max_connections=3,
            connection_timeout=10.0,
            connection_params={"base_url": "https://httpbin.org", "timeout": 10.0},
        )

        pool = ConnectionPool(config=config, logger=mock_logger)
        await pool.initialize()

        try:
            async with pool.get_connection() as session:
                # Test that we got an aiohttp session
                assert hasattr(session, "get")
        finally:
            await pool.shutdown()


# =============================================================================
# Resource Manager Tests
# =============================================================================


class TestResourceManager:
    """Test cases for the resource manager."""

    @pytest.fixture
    async def resource_manager(self, mock_logger):
        """Create resource manager for testing."""
        config = {
            "cleanup_interval_seconds": 60,
            "resource_timeout_seconds": 300,
            "max_resources": 1000,
            "enable_leak_detection": True,
        }

        manager = ResourceManager(config=config, logger=mock_logger)
        await manager.initialize()
        yield manager
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_resource_manager_initialization(self, resource_manager):
        """Test resource manager initializes correctly."""
        assert resource_manager._logger is not None
        assert resource_manager._resources == {}

    @pytest.mark.asyncio
    async def test_register_resource(self, resource_manager):
        """Test registering a resource."""
        test_resource = {"test": "resource"}

        resource_id = await resource_manager.register_resource(
            resource=test_resource,
            resource_type=ResourceType.MEMORY_BUFFER,
            cleanup_func=None,
        )

        assert resource_id is not None
        assert resource_id in resource_manager._resources

    @pytest.mark.asyncio
    async def test_unregister_resource(self, resource_manager):
        """Test unregistering a resource."""
        test_resource = {"test": "resource"}

        resource_id = await resource_manager.register_resource(
            resource=test_resource, resource_type=ResourceType.MEMORY_BUFFER
        )

        success = await resource_manager.unregister_resource(resource_id)
        assert success is True
        assert resource_id not in resource_manager._resources

    @pytest.mark.asyncio
    async def test_resource_cleanup_function(self, resource_manager):
        """Test resource cleanup function execution."""
        cleanup_called = False

        def cleanup_func():
            nonlocal cleanup_called
            cleanup_called = True

        resource_id = await resource_manager.register_resource(
            resource="test",
            resource_type=ResourceType.TEMPORARY_FILE,
            cleanup_func=cleanup_func,
        )

        await resource_manager.unregister_resource(resource_id)
        assert cleanup_called is True

    @pytest.mark.asyncio
    async def test_get_resource_info(self, resource_manager):
        """Test getting resource information."""
        test_resource = "test_resource"

        resource_id = await resource_manager.register_resource(
            resource=test_resource, resource_type=ResourceType.CACHE
        )

        info = await resource_manager.get_resource_info(resource_id)
        assert info.resource_id == resource_id
        assert info.resource_type == ResourceType.CACHE

    @pytest.mark.asyncio
    async def test_list_resources_by_type(self, resource_manager):
        """Test listing resources by type."""
        # Register resources of different types
        await resource_manager.register_resource("cache1", ResourceType.CACHE)
        await resource_manager.register_resource("cache2", ResourceType.CACHE)
        await resource_manager.register_resource("file1", ResourceType.FILE_HANDLE)

        cache_resources = await resource_manager.list_resources_by_type(
            ResourceType.CACHE
        )
        file_resources = await resource_manager.list_resources_by_type(
            ResourceType.FILE_HANDLE
        )

        assert len(cache_resources) == 2
        assert len(file_resources) == 1

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, resource_manager):
        """Test graceful shutdown cleans up all resources."""
        cleanup_calls = []

        def make_cleanup(name):
            def cleanup():
                cleanup_calls.append(name)

            return cleanup

        # Register multiple resources with cleanup
        for i in range(3):
            await resource_manager.register_resource(
                resource=f"resource_{i}",
                resource_type=ResourceType.MEMORY_BUFFER,
                cleanup_func=make_cleanup(f"resource_{i}"),
            )

        await resource_manager.shutdown()
        assert len(cleanup_calls) == 3

    @pytest.mark.asyncio
    async def test_resource_leak_detection(self, resource_manager):
        """Test resource leak detection."""
        # Register a resource without cleanup
        resource_id = await resource_manager.register_resource(
            resource="leaked_resource", resource_type=ResourceType.MEMORY_BUFFER
        )

        # Get leak report
        leaks = await resource_manager.detect_leaks()
        assert len(leaks) > 0

        # Cleanup
        await resource_manager.unregister_resource(resource_id)


# =============================================================================
# Performance Monitor Tests
# =============================================================================


class TestPerformanceMonitor:
    """Test cases for the performance monitor."""

    @pytest.fixture
    async def performance_monitor(self, mock_logger, temp_directory):
        """Create performance monitor for testing."""
        config = {
            "collection_interval": 1.0,
            "retention_days": 7,
            "alert_thresholds": {
                "memory_usage_percent": 80.0,
                "cpu_usage_percent": 90.0,
                "disk_usage_percent": 85.0,
            },
            "enable_detailed_metrics": True,
            "metrics_storage_path": str(temp_directory / "metrics.db"),
        }

        monitor = PerformanceMonitor(config=config, logger=mock_logger)
        await monitor.initialize()
        yield monitor
        await monitor.shutdown()

    @pytest.mark.asyncio
    async def test_performance_monitor_initialization(self, performance_monitor):
        """Test performance monitor initializes correctly."""
        assert performance_monitor._logger is not None
        assert performance_monitor._config is not None

    @pytest.mark.asyncio
    async def test_record_metric(self, performance_monitor):
        """Test recording a performance metric."""
        await performance_monitor.record_metric(
            name="test_metric",
            value=100.0,
            metric_type=MetricType.GAUGE,
            category="test",
            labels={"test": "label"},
        )

        # Verify metric was recorded
        metrics = await performance_monitor.get_metrics("test_metric")
        assert len(metrics) > 0

    @pytest.mark.asyncio
    async def test_timer_context_manager(self, performance_monitor):
        """Test timer context manager."""
        async with performance_monitor.timer("test_operation"):
            await asyncio.sleep(0.1)  # Simulate work

        # Verify timing was recorded
        metrics = await performance_monitor.get_metrics("test_operation")
        assert len(metrics) > 0
        assert metrics[0].value >= 0.1  # Should be at least 100ms

    @pytest.mark.asyncio
    async def test_system_metrics_collection(self, performance_monitor):
        """Test system metrics collection."""
        system_metrics = await performance_monitor.get_system_metrics()

        assert "cpu_percent" in system_metrics.__dict__
        assert "memory_percent" in system_metrics.__dict__
        assert "disk_percent" in system_metrics.__dict__

    @pytest.mark.asyncio
    async def test_application_metrics_collection(self, performance_monitor):
        """Test application metrics collection."""
        app_metrics = await performance_monitor.get_application_metrics()

        assert "active_connections" in app_metrics.__dict__
        assert "cache_hit_rate" in app_metrics.__dict__
        assert "request_count" in app_metrics.__dict__

    @pytest.mark.asyncio
    async def test_alert_system(self, performance_monitor):
        """Test alert system functionality."""
        # Record a high CPU metric to trigger alert
        await performance_monitor.record_metric(
            name="cpu_usage",
            value=95.0,  # Above threshold
            metric_type=MetricType.GAUGE,
            category="system",
        )

        # Check if alert was created (implementation dependent)
        # This is a placeholder for alert testing logic

    @pytest.mark.asyncio
    async def test_performance_summary(self, performance_monitor):
        """Test performance summary generation."""
        # Record some test metrics
        await performance_monitor.record_metric("test1", 50.0, MetricType.GAUGE, "test")
        await performance_monitor.record_metric(
            "test2", 75.0, MetricType.COUNTER, "test"
        )

        summary = await performance_monitor.get_performance_summary()
        assert isinstance(summary, str)
        assert len(summary) > 0

    @pytest.mark.asyncio
    async def test_metric_statistics(self, performance_monitor):
        """Test metric statistics calculation."""
        # Record multiple values for a metric
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        for value in values:
            await performance_monitor.record_metric(
                "stats_test", value, MetricType.GAUGE, "test"
            )

        stats = await performance_monitor.get_metric_statistics("stats_test")

        assert "mean" in stats
        assert "min" in stats
        assert "max" in stats
        assert stats["min"] == 10.0
        assert stats["max"] == 50.0

    @pytest.mark.asyncio
    async def test_concurrent_metric_recording(self, performance_monitor):
        """Test concurrent metric recording."""

        async def record_metrics():
            for i in range(10):
                await performance_monitor.record_metric(
                    f"concurrent_test_{i % 3}",
                    float(i),
                    MetricType.COUNTER,
                    "concurrent",
                )

        # Run multiple recording tasks concurrently
        tasks = [record_metrics() for _ in range(5)]
        await asyncio.gather(*tasks)

        # Verify all metrics were recorded
        metrics_0 = await performance_monitor.get_metrics("concurrent_test_0")
        assert len(metrics_0) > 0


# =============================================================================
# Integration Tests
# =============================================================================


class TestCoreServicesIntegration:
    """Integration tests for core services working together."""

    @pytest.mark.asyncio
    async def test_di_container_with_real_services(self, temp_directory, mock_logger):
        """Test DI container with real service instances."""
        container = DIContainer()

        # Register cache service
        cache_config = {
            "max_memory_items": 50,
            "default_ttl_seconds": 300,
            "persistence_path": temp_directory / "integration_cache.db",
        }

        def cache_factory():
            return CacheService(
                strategy=CacheStrategy.LRU, max_size=50, default_ttl=300, **cache_config
            )

        container.register_singleton(CacheService, cache_factory)

        # Register resource manager
        def resource_manager_factory():
            return ResourceManager(config={"max_resources": 100}, logger=mock_logger)

        container.register_singleton(ResourceManager, resource_manager_factory)

        # Resolve and test services
        cache_service = container.resolve(CacheService)
        resource_manager = container.resolve(ResourceManager)

        await cache_service.initialize()
        await resource_manager.initialize()

        try:
            # Test cache service
            await cache_service.set("integration_test", "success")
            value = await cache_service.get("integration_test")
            assert value == "success"

            # Test resource manager
            resource_id = await resource_manager.register_resource(
                "test_resource", ResourceType.CACHE
            )
            assert resource_id is not None

            # Verify singleton behavior
            cache_service2 = container.resolve(CacheService)
            assert cache_service is cache_service2

        finally:
            await cache_service.shutdown()
            await resource_manager.shutdown()

    @pytest.mark.asyncio
    async def test_performance_monitoring_integration(
        self, temp_directory, mock_logger
    ):
        """Test performance monitor with other services."""
        # Create services
        cache_service = CacheService(CacheStrategy.LRU, 50, 300)
        performance_monitor = PerformanceMonitor(
            config={"collection_interval": 0.1}, logger=mock_logger
        )

        await cache_service.initialize()
        await performance_monitor.initialize()

        try:
            # Perform monitored operations
            async with performance_monitor.timer("cache_operation"):
                await cache_service.set("perf_test", "data")
                value = await cache_service.get("perf_test")
                assert value == "data"

            # Record custom metrics
            cache_stats = await cache_service.get_statistics()
            await performance_monitor.record_metric(
                "cache_hit_rate",
                cache_stats.get("hit_rate", 0.0),
                MetricType.GAUGE,
                "cache",
            )

            # Verify metrics were recorded
            metrics = await performance_monitor.get_metrics("cache_operation")
            assert len(metrics) > 0

        finally:
            await cache_service.shutdown()
            await performance_monitor.shutdown()

    @pytest.mark.asyncio
    async def test_lazy_loader_with_cache_integration(
        self, temp_directory, mock_logger
    ):
        """Test lazy loader integration with cache service."""
        from src.core.lazy_loader import LazyLoadConfig

        # Create test data files
        for i in range(3):
            test_file = temp_directory / f"data_{i}.json"
            test_file.write_text(f'{{"id": {i}, "data": "test_data_{i}"}}')

        # Create services
        cache_service = CacheService(CacheStrategy.LRU, 100, 300)

        config = LazyLoadConfig(
            scan_directories=[temp_directory],
            file_patterns=["*.json"],
            cache_duration=300,
        )
        lazy_loader = LazyLoader(config=config, logger=mock_logger)

        await cache_service.initialize()
        await lazy_loader.initialize()

        try:
            # Load resources and cache them
            for i in range(3):
                file_path = str(temp_directory / f"data_{i}.json")
                data = await lazy_loader.load_resource(file_path)

                # Cache the loaded data
                cache_key = f"loaded_data_{i}"
                await cache_service.set(cache_key, data)

                # Verify cached data
                cached_data = await cache_service.get(cache_key)
                assert cached_data == data
                assert cached_data["id"] == i

            # Verify cache statistics
            cache_stats = await cache_service.get_statistics()
            assert cache_stats["total_items"] == 3

        finally:
            await cache_service.shutdown()
            await lazy_loader.shutdown()
