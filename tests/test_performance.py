# =============================================================================
# QuranBot - Performance Tests
# =============================================================================
# Comprehensive test suite for performance optimizations including cache
# performance, lazy loading, connection pooling, and resource management.
# =============================================================================

import asyncio
from datetime import UTC
import gc
from pathlib import Path
import statistics
import tempfile
import time
from unittest.mock import AsyncMock, Mock

import pytest

from src.core.cache_service import CacheConfig, CacheService
from src.core.connection_pool import ConnectionConfig, ConnectionPool, ConnectionType
from src.core.di_container import DIContainer
from src.core.lazy_loader import AudioFileResource, LazyLoadConfig, LazyLoader
from src.core.performance_monitor import MetricType, PerformanceMonitor
from src.core.resource_manager import ResourceManager, ResourceType
from src.core.structured_logger import StructuredLogger

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
async def mock_logger():
    """Create a mock structured logger"""
    logger = Mock(spec=StructuredLogger)
    logger.info = AsyncMock()
    logger.warning = AsyncMock()
    logger.error = AsyncMock()
    logger.debug = AsyncMock()
    return logger


@pytest.fixture
def mock_container():
    """Create a mock DI container"""
    container = Mock(spec=DIContainer)
    return container


@pytest.fixture
def temp_directory():
    """Create temporary directory for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
async def cache_service(mock_container, mock_logger, temp_directory):
    """Create cache service for testing"""
    config = CacheConfig(
        max_memory_mb=10,
        max_entries=100,
        default_ttl_seconds=60,
        disk_cache_directory=temp_directory / "cache",
    )

    service = CacheService(mock_container, config, mock_logger)
    await service.initialize()

    yield service

    await service.shutdown()


@pytest.fixture
async def lazy_loader(mock_container, mock_logger, temp_directory):
    """Create lazy loader for testing"""
    config = LazyLoadConfig(
        background_scan_enabled=False,  # Disable for testing
        enable_preloading=False,
        enable_file_watching=False,
    )

    # Create mock cache service
    mock_cache = Mock()
    mock_cache.get = AsyncMock(return_value=None)
    mock_cache.set = AsyncMock(return_value=True)

    loader = LazyLoader(mock_container, config, mock_cache, mock_logger)
    await loader.initialize()

    yield loader

    await loader.shutdown()


@pytest.fixture
async def connection_pool(mock_container, mock_logger, temp_directory):
    """Create connection pool for testing"""
    config = ConnectionConfig(
        connection_type=ConnectionType.SQLITE,
        connection_string=str(temp_directory / "test.db"),
        max_connections=5,
        min_connections=1,
        enable_health_checks=False,  # Disable for testing
    )

    pool = ConnectionPool(mock_container, config, mock_logger)
    await pool.initialize()

    yield pool

    await pool.shutdown()


@pytest.fixture
async def resource_manager(mock_container, mock_logger):
    """Create resource manager for testing"""
    manager = ResourceManager(mock_container, mock_logger)
    await manager.initialize()

    yield manager

    await manager.shutdown()


@pytest.fixture
async def performance_monitor(mock_container, mock_logger):
    """Create performance monitor for testing"""
    monitor = PerformanceMonitor(
        mock_container,
        mock_logger,
        collection_interval=1,  # Fast collection for testing
        enable_detailed_profiling=False,
    )
    await monitor.initialize()

    yield monitor

    await monitor.shutdown()


# =============================================================================
# Cache Performance Tests
# =============================================================================


class TestCachePerformance:
    """Test cache service performance optimizations"""

    @pytest.mark.asyncio
    async def test_cache_hit_performance(self, cache_service):
        """Test cache hit performance is faster than cache miss"""
        # Warm up cache
        await cache_service.set("test_key", "test_value")

        # Measure cache hit time
        hit_times = []
        for _ in range(100):
            start = time.time()
            result = await cache_service.get("test_key")
            hit_times.append(time.time() - start)
            assert result == "test_value"

        # Measure cache miss time
        miss_times = []
        for i in range(100):
            start = time.time()
            result = await cache_service.get(f"missing_key_{i}")
            miss_times.append(time.time() - start)
            assert result is None

        avg_hit_time = statistics.mean(hit_times)
        avg_miss_time = statistics.mean(miss_times)

        # Cache hits should be consistently faster than misses
        assert avg_hit_time < avg_miss_time

        # Cache hits should be very fast (< 1ms on average)
        assert avg_hit_time < 0.001

    @pytest.mark.asyncio
    async def test_cache_memory_efficiency(self, cache_service):
        """Test cache memory usage efficiency"""
        initial_stats = await cache_service.get_statistics()
        initial_memory = initial_stats.memory_usage_mb

        # Add many items to cache
        data_size = "x" * 1024  # 1KB per item
        item_count = 50

        for i in range(item_count):
            await cache_service.set(f"key_{i}", data_size)

        final_stats = await cache_service.get_statistics()
        final_memory = final_stats.memory_usage_mb

        memory_used = final_memory - initial_memory
        expected_memory = (item_count * len(data_size)) / (1024 * 1024)

        # Memory usage should be reasonable (within 2x of expected)
        assert memory_used < expected_memory * 2

        # All items should be cached
        assert final_stats.entry_count == item_count

    @pytest.mark.asyncio
    async def test_cache_eviction_performance(self, cache_service):
        """Test cache eviction doesn't significantly impact performance"""
        # Fill cache to capacity
        max_entries = cache_service._config.max_entries

        # Add items up to capacity
        add_times = []
        for i in range(max_entries):
            start = time.time()
            await cache_service.set(f"key_{i}", f"value_{i}")
            add_times.append(time.time() - start)

        # Add more items that will trigger eviction
        eviction_times = []
        for i in range(max_entries, max_entries + 20):
            start = time.time()
            await cache_service.set(f"key_{i}", f"value_{i}")
            eviction_times.append(time.time() - start)

        avg_add_time = statistics.mean(add_times)
        avg_eviction_time = statistics.mean(eviction_times)

        # Eviction should not be significantly slower (within 3x)
        assert avg_eviction_time < avg_add_time * 3

    @pytest.mark.asyncio
    async def test_cache_concurrent_access(self, cache_service):
        """Test cache performance under concurrent access"""

        async def cache_worker(worker_id: int, operation_count: int):
            times = []
            for i in range(operation_count):
                start = time.time()

                # Mix of reads and writes
                if i % 3 == 0:
                    await cache_service.set(f"worker_{worker_id}_key_{i}", f"value_{i}")
                else:
                    await cache_service.get(f"worker_{worker_id}_key_{i // 3}")

                times.append(time.time() - start)

            return times

        # Run multiple workers concurrently
        worker_count = 10
        operations_per_worker = 50

        start_time = time.time()
        tasks = [
            cache_worker(worker_id, operations_per_worker)
            for worker_id in range(worker_count)
        ]

        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        # Analyze results
        all_times = []
        for worker_times in results:
            all_times.extend(worker_times)

        avg_operation_time = statistics.mean(all_times)
        total_operations = worker_count * operations_per_worker

        # Operations should complete reasonably fast
        assert avg_operation_time < 0.01  # < 10ms per operation

        # Should achieve good throughput
        operations_per_second = total_operations / total_time
        assert operations_per_second > 100  # > 100 ops/sec

    @pytest.mark.asyncio
    async def test_cache_compression_efficiency(self, cache_service):
        """Test cache compression improves memory efficiency"""
        # Create compressible data (repeated pattern)
        large_data = "This is a repeated pattern. " * 1000  # ~28KB

        # Store without compression
        cache_service._config.enable_compression = False
        await cache_service.set("uncompressed", large_data)

        # Store with compression
        cache_service._config.enable_compression = True
        await cache_service.set("compressed", large_data)

        stats = await cache_service.get_statistics()

        # Compression should save significant space
        assert stats.compression_ratio > 50  # At least 50% compression

    @pytest.mark.asyncio
    async def test_cache_ttl_efficiency(self, cache_service):
        """Test TTL expiration doesn't impact performance significantly"""
        # Add items with short TTL
        ttl_items = 50
        for i in range(ttl_items):
            await cache_service.set(f"ttl_key_{i}", f"value_{i}", ttl_seconds=1)

        # Wait for expiration
        await asyncio.sleep(2)

        # Trigger cleanup and measure performance
        cleanup_times = []
        for i in range(20):
            start = time.time()
            await cache_service.get(f"ttl_key_{i}")  # This should trigger cleanup
            cleanup_times.append(time.time() - start)

        avg_cleanup_time = statistics.mean(cleanup_times)

        # Cleanup should be fast
        assert avg_cleanup_time < 0.005  # < 5ms


# =============================================================================
# Lazy Loading Performance Tests
# =============================================================================


class TestLazyLoadingPerformance:
    """Test lazy loading service performance"""

    @pytest.mark.asyncio
    async def test_lazy_load_vs_eager_load_performance(
        self, lazy_loader, temp_directory
    ):
        """Compare lazy loading vs eager loading performance"""
        # Create test audio files
        audio_dir = temp_directory / "audio" / "test_reciter"
        audio_dir.mkdir(parents=True)

        # Create multiple audio files
        file_count = 20
        for i in range(1, file_count + 1):
            audio_file = audio_dir / f"{i:03d}.mp3"
            audio_file.write_text(f"mock audio data for surah {i}")

        # Test eager loading (load all at once)
        eager_start = time.time()

        # Simulate eager loading by creating and loading all resources
        eager_resources = []
        for i in range(1, file_count + 1):
            resource = AudioFileResource(
                file_path=audio_dir / f"{i:03d}.mp3",
                reciter="test_reciter",
                surah_number=i,
            )
            eager_resources.append(resource)

        # Load all resources
        for resource in eager_resources:
            await resource.load()

        eager_time = time.time() - eager_start

        # Test lazy loading (load on demand)
        lazy_start = time.time()

        # Register resources but don't load
        for i in range(1, file_count + 1):
            resource = AudioFileResource(
                file_path=audio_dir / f"{i:03d}.mp3",
                reciter="test_reciter",
                surah_number=i,
            )
            await lazy_loader.register_resource(resource)

        # Load only a few resources (simulating on-demand access)
        access_count = 5
        for i in range(1, access_count + 1):
            await lazy_loader.load_resource(f"audio:test_reciter:{i}")

        lazy_time = time.time() - lazy_start

        # Lazy loading should be significantly faster for partial access
        assert lazy_time < eager_time * 0.5  # At least 2x faster

    @pytest.mark.asyncio
    async def test_lazy_load_caching_performance(self, lazy_loader, temp_directory):
        """Test lazy loading with caching improves repeated access"""
        # Create test resource
        audio_dir = temp_directory / "audio" / "cached_reciter"
        audio_dir.mkdir(parents=True)
        audio_file = audio_dir / "001.mp3"
        audio_file.write_text("mock audio data")

        resource = AudioFileResource(
            file_path=audio_file, reciter="cached_reciter", surah_number=1
        )
        await lazy_loader.register_resource(resource)

        # First load (from disk)
        first_load_times = []
        for _ in range(5):
            start = time.time()
            await lazy_loader.load_resource("audio:cached_reciter:1")
            first_load_times.append(time.time() - start)

        # Subsequent loads (from cache)
        cached_load_times = []
        for _ in range(10):
            start = time.time()
            await lazy_loader.load_resource("audio:cached_reciter:1")
            cached_load_times.append(time.time() - start)

        avg_first_load = statistics.mean(first_load_times)
        avg_cached_load = statistics.mean(cached_load_times)

        # Cached loads should be significantly faster
        assert avg_cached_load < avg_first_load * 0.1  # At least 10x faster

    @pytest.mark.asyncio
    async def test_lazy_load_memory_efficiency(self, lazy_loader, temp_directory):
        """Test lazy loading uses memory efficiently"""
        # Create many test resources
        audio_dir = temp_directory / "audio" / "memory_test_reciter"
        audio_dir.mkdir(parents=True)

        resource_count = 100
        for i in range(1, resource_count + 1):
            audio_file = audio_dir / f"{i:03d}.mp3"
            audio_file.write_text(f"mock audio data {i}" * 100)  # Make files larger

            resource = AudioFileResource(
                file_path=audio_file, reciter="memory_test_reciter", surah_number=i
            )
            await lazy_loader.register_resource(resource)

        # Get initial memory usage
        import psutil

        process = psutil.Process()
        initial_memory = process.memory_info().rss

        # Load only a subset of resources
        loaded_count = 10
        for i in range(1, loaded_count + 1):
            await lazy_loader.load_resource(f"audio:memory_test_reciter:{i}")

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be proportional to loaded resources, not total
        # This is a rough check since memory usage depends on many factors
        assert memory_increase < 50 * 1024 * 1024  # Less than 50MB increase

    @pytest.mark.asyncio
    async def test_concurrent_lazy_loading(self, lazy_loader, temp_directory):
        """Test lazy loading performance under concurrent access"""
        # Create test resources
        audio_dir = temp_directory / "audio" / "concurrent_reciter"
        audio_dir.mkdir(parents=True)

        resource_count = 50
        for i in range(1, resource_count + 1):
            audio_file = audio_dir / f"{i:03d}.mp3"
            audio_file.write_text(f"concurrent test data {i}")

            resource = AudioFileResource(
                file_path=audio_file, reciter="concurrent_reciter", surah_number=i
            )
            await lazy_loader.register_resource(resource)

        async def concurrent_loader(start_id: int, count: int):
            times = []
            for i in range(start_id, start_id + count):
                start = time.time()
                await lazy_loader.load_resource(f"audio:concurrent_reciter:{i}")
                times.append(time.time() - start)
            return times

        # Run concurrent loaders
        worker_count = 5
        resources_per_worker = 10

        start_time = time.time()
        tasks = [
            concurrent_loader(i * resources_per_worker + 1, resources_per_worker)
            for i in range(worker_count)
        ]

        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        # Analyze results
        all_times = []
        for worker_times in results:
            all_times.extend(worker_times)

        avg_load_time = statistics.mean(all_times)
        total_loads = worker_count * resources_per_worker

        # Concurrent loading should be efficient
        assert avg_load_time < 0.1  # < 100ms per load
        loads_per_second = total_loads / total_time
        assert loads_per_second > 10  # > 10 loads/sec


# =============================================================================
# Connection Pool Performance Tests
# =============================================================================


class TestConnectionPoolPerformance:
    """Test connection pool performance optimizations"""

    @pytest.mark.asyncio
    async def test_connection_pool_vs_new_connections(
        self, connection_pool, temp_directory
    ):
        """Compare pooled vs new connections performance"""
        # Test pooled connections
        pooled_times = []
        for _ in range(20):
            start = time.time()
            async with connection_pool.get_connection() as conn:
                # Simulate work
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                cursor.close()
            pooled_times.append(time.time() - start)

        # Test new connections each time
        import sqlite3

        db_path = temp_directory / "new_connections.db"

        new_connection_times = []
        for _ in range(20):
            start = time.time()
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            conn.close()
            new_connection_times.append(time.time() - start)

        avg_pooled_time = statistics.mean(pooled_times)
        avg_new_connection_time = statistics.mean(new_connection_times)

        # Pooled connections should be faster
        assert avg_pooled_time < avg_new_connection_time

    @pytest.mark.asyncio
    async def test_connection_pool_concurrency(self, connection_pool):
        """Test connection pool performance under high concurrency"""

        async def db_worker(worker_id: int, query_count: int):
            times = []
            for i in range(query_count):
                start = time.time()
                async with connection_pool.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT ?", (worker_id * 1000 + i,))
                    cursor.fetchone()
                    cursor.close()
                times.append(time.time() - start)
            return times

        # Run many concurrent workers
        worker_count = 20
        queries_per_worker = 25

        start_time = time.time()
        tasks = [
            db_worker(worker_id, queries_per_worker)
            for worker_id in range(worker_count)
        ]

        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        # Analyze results
        all_times = []
        for worker_times in results:
            all_times.extend(worker_times)

        avg_query_time = statistics.mean(all_times)
        total_queries = worker_count * queries_per_worker
        queries_per_second = total_queries / total_time

        # Should handle concurrent load efficiently
        assert avg_query_time < 0.05  # < 50ms per query
        assert queries_per_second > 50  # > 50 queries/sec

    @pytest.mark.asyncio
    async def test_connection_pool_resource_efficiency(self, connection_pool):
        """Test connection pool doesn't leak resources"""
        initial_metrics = await connection_pool.get_metrics()
        initial_connections = initial_metrics.total_connections

        # Perform many operations
        for _ in range(100):
            async with connection_pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                cursor.close()

        final_metrics = await connection_pool.get_metrics()
        final_connections = final_metrics.total_connections

        # Connection count should be stable (within reasonable bounds)
        assert abs(final_connections - initial_connections) <= 2

        # Success rate should be high
        assert final_metrics.success_rate > 0.95  # > 95% success rate


# =============================================================================
# Resource Manager Performance Tests
# =============================================================================


class TestResourceManagerPerformance:
    """Test resource manager performance"""

    @pytest.mark.asyncio
    async def test_resource_registration_performance(self, resource_manager):
        """Test resource registration is fast"""
        registration_times = []
        resource_count = 1000

        for i in range(resource_count):
            start = time.time()
            resource_id = await resource_manager.register_resource(
                resource=f"test_resource_{i}",
                resource_type=ResourceType.MEMORY_BUFFER,
                cleanup_callbacks=[lambda: None],
            )
            registration_times.append(time.time() - start)

        avg_registration_time = statistics.mean(registration_times)

        # Registration should be very fast
        assert avg_registration_time < 0.001  # < 1ms per registration

        # All resources should be registered
        stats = await resource_manager.get_statistics()
        assert stats.total_resources == resource_count

    @pytest.mark.asyncio
    async def test_resource_cleanup_performance(self, resource_manager):
        """Test resource cleanup is efficient"""
        # Register many resources
        resource_ids = []
        resource_count = 500

        for i in range(resource_count):
            resource_id = await resource_manager.register_resource(
                resource=f"cleanup_test_{i}", resource_type=ResourceType.MEMORY_BUFFER
            )
            resource_ids.append(resource_id)

        # Measure cleanup time
        cleanup_times = []
        for resource_id in resource_ids[:100]:  # Test subset
            start = time.time()
            await resource_manager.unregister_resource(resource_id)
            cleanup_times.append(time.time() - start)

        avg_cleanup_time = statistics.mean(cleanup_times)

        # Cleanup should be fast
        assert avg_cleanup_time < 0.01  # < 10ms per cleanup

    @pytest.mark.asyncio
    async def test_graceful_shutdown_performance(self, resource_manager):
        """Test graceful shutdown completes in reasonable time"""
        # Register resources with dependencies
        resource_count = 100

        # Create resources with some dependencies
        for i in range(resource_count):
            dependencies = set()
            if i > 0 and i % 10 == 0:
                # Every 10th resource depends on previous one
                dependencies.add(f"test_resource_{i-1}")

            await resource_manager.register_resource(
                resource=f"test_resource_{i}",
                resource_type=ResourceType.SERVICE,
                resource_id=f"test_resource_{i}",
                dependencies=dependencies,
            )

        # Measure shutdown time
        start_time = time.time()
        await resource_manager.initiate_shutdown(timeout=30.0)
        shutdown_time = time.time() - start_time

        # Shutdown should complete in reasonable time
        assert shutdown_time < 10.0  # < 10 seconds

        # All resources should be cleaned up
        stats = await resource_manager.get_statistics()
        assert stats.total_resources == 0

    @pytest.mark.asyncio
    async def test_resource_leak_detection_performance(self, resource_manager):
        """Test leak detection doesn't impact performance significantly"""
        # Register resources that look like leaks
        leak_count = 50
        for i in range(leak_count):
            resource_id = await resource_manager.register_resource(
                resource=f"potential_leak_{i}", resource_type=ResourceType.MEMORY_BUFFER
            )

            # Make resources look old and idle
            resource_info = await resource_manager.get_resource_info(resource_id)
            if resource_info:
                # Manually set old timestamps (normally this would be done by time passage)
                from datetime import datetime, timedelta

                old_time = datetime.now(UTC) - timedelta(hours=2)
                resource_info.created_at = old_time
                resource_info.last_accessed = old_time
                await resource_manager.mark_resource_idle(resource_id)

        # Measure leak detection time
        start_time = time.time()
        leaks = await resource_manager.detect_resource_leaks()
        detection_time = time.time() - start_time

        # Detection should be fast even with many resources
        assert detection_time < 1.0  # < 1 second

        # Should detect some leaks
        assert len(leaks) > 0


# =============================================================================
# Performance Monitor Tests
# =============================================================================


class TestPerformanceMonitorPerformance:
    """Test performance monitor efficiency"""

    @pytest.mark.asyncio
    async def test_metric_recording_performance(self, performance_monitor):
        """Test metric recording is fast and doesn't impact performance"""
        recording_times = []
        metric_count = 1000

        for i in range(metric_count):
            start = time.time()
            await performance_monitor.record_metric(
                f"test_metric_{i % 10}",
                i * 1.5,
                MetricType.GAUGE,  # Reuse metric names
            )
            recording_times.append(time.time() - start)

        avg_recording_time = statistics.mean(recording_times)

        # Metric recording should be very fast
        assert avg_recording_time < 0.001  # < 1ms per recording

    @pytest.mark.asyncio
    async def test_timer_operation_overhead(self, performance_monitor):
        """Test timing operations has minimal overhead"""

        # Test operation without timing
        def test_operation():
            return sum(range(1000))

        # Measure operation without timing
        baseline_times = []
        for _ in range(100):
            start = time.time()
            test_operation()
            baseline_times.append(time.time() - start)

        # Measure operation with timing
        timed_times = []
        for _ in range(100):
            start = time.time()
            timer_id = await performance_monitor.start_timer("test_operation")
            test_operation()
            await performance_monitor.end_timer(timer_id)
            timed_times.append(time.time() - start)

        avg_baseline = statistics.mean(baseline_times)
        avg_timed = statistics.mean(timed_times)

        overhead = avg_timed - avg_baseline
        overhead_percentage = (overhead / avg_baseline) * 100

        # Timing overhead should be minimal (< 10% of operation time)
        assert overhead_percentage < 10

    @pytest.mark.asyncio
    async def test_concurrent_monitoring_performance(self, performance_monitor):
        """Test monitoring doesn't degrade under concurrent load"""

        async def monitoring_worker(worker_id: int, operation_count: int):
            times = []
            for i in range(operation_count):
                start = time.time()

                # Mix of different monitoring operations
                if i % 3 == 0:
                    await performance_monitor.record_metric(
                        f"worker_{worker_id}_counter", i
                    )
                elif i % 3 == 1:
                    timer_id = await performance_monitor.start_timer(
                        f"worker_{worker_id}_operation"
                    )
                    await asyncio.sleep(0.001)  # Simulate work
                    await performance_monitor.end_timer(timer_id)
                else:
                    await performance_monitor.get_system_metrics()

                times.append(time.time() - start)

            return times

        # Run concurrent monitoring workers
        worker_count = 10
        operations_per_worker = 50

        start_time = time.time()
        tasks = [
            monitoring_worker(worker_id, operations_per_worker)
            for worker_id in range(worker_count)
        ]

        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        # Analyze results
        all_times = []
        for worker_times in results:
            all_times.extend(worker_times)

        avg_operation_time = statistics.mean(all_times)
        total_operations = worker_count * operations_per_worker
        operations_per_second = total_operations / total_time

        # Monitoring should handle concurrent load efficiently
        assert avg_operation_time < 0.01  # < 10ms per operation
        assert operations_per_second > 100  # > 100 ops/sec


# =============================================================================
# Integration Performance Tests
# =============================================================================


class TestIntegrationPerformance:
    """Test performance of integrated components"""

    @pytest.mark.asyncio
    async def test_full_stack_performance(
        self,
        cache_service,
        lazy_loader,
        connection_pool,
        resource_manager,
        performance_monitor,
        temp_directory,
    ):
        """Test performance when all optimization components work together"""
        # Create test scenario: audio file discovery and caching
        audio_dir = temp_directory / "audio" / "integration_reciter"
        audio_dir.mkdir(parents=True)

        # Create test audio files
        file_count = 30
        for i in range(1, file_count + 1):
            audio_file = audio_dir / f"{i:03d}.mp3"
            audio_file.write_text(f"integration test audio {i}" * 50)

        # Register resources with resource manager
        resource_ids = []
        for i in range(1, file_count + 1):
            resource = AudioFileResource(
                file_path=audio_file, reciter="integration_reciter", surah_number=i
            )

            # Register with lazy loader
            await lazy_loader.register_resource(resource)

            # Register with resource manager
            resource_id = await resource_manager.register_resource(
                resource=resource, resource_type=ResourceType.SERVICE
            )
            resource_ids.append(resource_id)

        # Test integrated workflow
        workflow_times = []

        for i in range(1, 11):  # Test loading 10 files
            start = time.time()

            # Start performance monitoring
            timer_id = await performance_monitor.start_timer("integration_workflow")

            # Try cache first
            cache_key = f"audio_metadata:integration_reciter:{i}"
            cached_data = await cache_service.get(cache_key)

            if cached_data is None:
                # Load via lazy loader
                data = await lazy_loader.load_resource(f"audio:integration_reciter:{i}")

                # Cache the result
                if data:
                    await cache_service.set(cache_key, data, ttl_seconds=300)

            # Use connection pool for database operation
            async with connection_pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT ?", (i,))
                cursor.fetchone()
                cursor.close()

            # Record metrics
            await performance_monitor.record_metric("files_processed", i)

            # End timing
            await performance_monitor.end_timer(timer_id)

            workflow_times.append(time.time() - start)

        # Analyze integrated performance
        avg_workflow_time = statistics.mean(workflow_times)

        # Get performance summary
        summary = await performance_monitor.get_performance_summary()

        # Integrated workflow should be efficient
        assert avg_workflow_time < 0.1  # < 100ms per workflow

        # Cache should improve performance over time (later operations faster)
        first_half_avg = statistics.mean(workflow_times[:5])
        second_half_avg = statistics.mean(workflow_times[5:])
        assert (
            second_half_avg <= first_half_avg
        )  # Should be same or better due to caching

        # System should remain healthy
        assert summary["system_metrics"]["cpu_percent"] < 80
        assert summary["system_metrics"]["memory_percent"] < 80

    @pytest.mark.asyncio
    async def test_memory_efficiency_integration(
        self, cache_service, lazy_loader, resource_manager, performance_monitor
    ):
        """Test memory efficiency of integrated system"""
        import psutil

        process = psutil.Process()

        # Get baseline memory
        gc.collect()  # Force garbage collection
        baseline_memory = process.memory_info().rss

        # Create many resources
        resource_count = 200
        resource_ids = []

        for i in range(resource_count):
            # Create test resource
            test_data = f"test_data_{i}" * 100  # Make it substantial

            # Register with resource manager
            resource_id = await resource_manager.register_resource(
                resource=test_data, resource_type=ResourceType.MEMORY_BUFFER
            )
            resource_ids.append(resource_id)

            # Add to cache
            await cache_service.set(f"test_key_{i}", test_data)

            # Record metric
            await performance_monitor.record_metric("resource_created", i)

        # Measure memory after creation
        gc.collect()
        peak_memory = process.memory_info().rss
        memory_increase = peak_memory - baseline_memory

        # Clean up half the resources
        cleanup_count = resource_count // 2
        for i in range(cleanup_count):
            await resource_manager.unregister_resource(resource_ids[i])

        # Force cache cleanup
        await cache_service.clear()

        # Measure memory after cleanup
        gc.collect()
        final_memory = process.memory_info().rss
        memory_recovered = peak_memory - final_memory

        # Should recover significant memory after cleanup
        recovery_percentage = (memory_recovered / memory_increase) * 100
        assert recovery_percentage > 30  # Should recover at least 30% of memory

        # Final memory should be reasonable
        final_increase = final_memory - baseline_memory
        assert final_increase < memory_increase * 0.8  # Should be less than 80% of peak


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
