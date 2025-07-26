# =============================================================================
# QuranBot - Cache Service
# =============================================================================
# High-performance caching service with TTL support, LRU eviction, memory
# management, and multiple cache strategies for optimal performance.
# =============================================================================

import asyncio
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from functools import wraps
import gzip
import hashlib
import json
from pathlib import Path
import pickle
import time
from typing import Any, Generic, TypeVar
import weakref

from .di_container import DIContainer
from .structured_logger import StructuredLogger

T = TypeVar("T")


class CacheStrategy(str, Enum):
    """Cache eviction strategies"""

    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In, First Out
    TTL_ONLY = "ttl_only"  # Time-based only


class CacheLevel(str, Enum):
    """Cache storage levels"""

    MEMORY = "memory"  # In-memory cache
    DISK = "disk"  # Persistent disk cache
    HYBRID = "hybrid"  # Memory + disk


@dataclass
class CacheEntry:
    """Represents a single cache entry with metadata"""

    key: str
    value: Any
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    accessed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    access_count: int = field(default=0)
    ttl_seconds: int | None = field(default=None)
    size_bytes: int = field(default=0)
    compressed: bool = field(default=False)

    @property
    def is_expired(self) -> bool:
        """Check if the cache entry has expired"""
        if self.ttl_seconds is None:
            return False

        expiry_time = self.created_at + timedelta(seconds=self.ttl_seconds)
        return datetime.now(UTC) > expiry_time

    @property
    def age_seconds(self) -> float:
        """Get age of the entry in seconds"""
        return (datetime.now(UTC) - self.created_at).total_seconds()

    @property
    def time_since_access(self) -> float:
        """Get time since last access in seconds"""
        return (datetime.now(UTC) - self.accessed_at).total_seconds()

    def mark_accessed(self) -> None:
        """Mark the entry as accessed"""
        self.accessed_at = datetime.now(UTC)
        self.access_count += 1


@dataclass
class CacheConfig:
    """Configuration for cache service"""

    max_memory_mb: int = field(default=100)
    max_entries: int = field(default=1000)
    default_ttl_seconds: int = field(default=3600)  # 1 hour
    strategy: CacheStrategy = field(default=CacheStrategy.LRU)
    level: CacheLevel = field(default=CacheLevel.HYBRID)
    enable_compression: bool = field(default=True)
    compression_threshold_bytes: int = field(default=1024)  # 1KB
    disk_cache_directory: Path = field(default_factory=lambda: Path("cache"))
    cleanup_interval_seconds: int = field(default=300)  # 5 minutes
    enable_statistics: bool = field(default=True)
    enable_persistence: bool = field(default=True)


@dataclass
class CacheStatistics:
    """Cache performance statistics"""

    hits: int = field(default=0)
    misses: int = field(default=0)
    evictions: int = field(default=0)
    expired_removals: int = field(default=0)
    memory_usage_bytes: int = field(default=0)
    entry_count: int = field(default=0)
    compression_ratio: float = field(default=0.0)
    average_access_time_ms: float = field(default=0.0)

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def memory_usage_mb(self) -> float:
        """Get memory usage in MB"""
        return self.memory_usage_bytes / (1024 * 1024)


class CacheService(Generic[T]):
    """
    High-performance caching service with multiple strategies and storage levels.

    Features:
    - Multiple eviction strategies (LRU, LFU, FIFO, TTL-only)
    - Hybrid memory/disk storage
    - Automatic compression for large entries
    - TTL support with automatic expiration
    - Performance monitoring and statistics
    - Graceful degradation and error handling
    - Thread-safe operations
    """

    def __init__(
        self,
        container: DIContainer,
        config: CacheConfig | None = None,
        logger: StructuredLogger | None = None,
    ):
        """Initialize cache service with configuration"""
        self._container = container
        self._config = config or CacheConfig()
        self._logger = logger or StructuredLogger()

        # Cache storage
        self._memory_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._access_tracker: dict[str, int] = {}  # For LFU strategy

        # Performance tracking
        self._statistics = CacheStatistics()
        self._access_times: list[float] = []

        # Cleanup and maintenance
        self._cleanup_task: asyncio.Task | None = None
        self._shutdown_event = asyncio.Event()

        # Weak references for automatic cleanup
        self._weak_refs: weakref.WeakSet = weakref.WeakSet()

    async def initialize(self) -> None:
        """Initialize the cache service"""
        await self._logger.info(
            "Initializing cache service",
            {
                "strategy": self._config.strategy.value,
                "level": self._config.level.value,
                "max_memory_mb": self._config.max_memory_mb,
                "max_entries": self._config.max_entries,
            },
        )

        # Create disk cache directory if needed
        if self._config.level in [CacheLevel.DISK, CacheLevel.HYBRID]:
            self._config.disk_cache_directory.mkdir(parents=True, exist_ok=True)

        # Load persistent cache if enabled
        if self._config.enable_persistence:
            await self._load_persistent_cache()

        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        await self._logger.info(
            "Cache service initialized successfully",
            {
                "loaded_entries": len(self._memory_cache),
                "memory_usage_mb": self._statistics.memory_usage_mb,
            },
        )

    async def shutdown(self) -> None:
        """Shutdown the cache service and cleanup resources"""
        await self._logger.info("Shutting down cache service")

        # Signal shutdown
        self._shutdown_event.set()

        # Cancel cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Save persistent cache
        if self._config.enable_persistence:
            await self._save_persistent_cache()

        # Clear caches
        self._memory_cache.clear()
        self._access_tracker.clear()
        self._weak_refs.clear()

        await self._logger.info("Cache service shutdown complete")

    async def get(self, key: str, default: T | None = None) -> T | None:
        """
        Get value from cache by key.

        Args:
            key: Cache key
            default: Default value if not found

        Returns:
            Cached value or default
        """
        start_time = time.time()

        try:
            # Check memory cache first
            if key in self._memory_cache:
                entry = self._memory_cache[key]

                # Check if expired
                if entry.is_expired:
                    await self._remove_entry(key, reason="expired")
                    self._statistics.expired_removals += 1
                    self._statistics.misses += 1
                    return default

                # Update access tracking
                entry.mark_accessed()

                # Move to end for LRU strategy
                if self._config.strategy == CacheStrategy.LRU:
                    self._memory_cache.move_to_end(key)

                # Update LFU tracking
                if self._config.strategy == CacheStrategy.LFU:
                    self._access_tracker[key] = self._access_tracker.get(key, 0) + 1

                self._statistics.hits += 1

                # Decompress if needed
                value = (
                    await self._decompress_value(entry.value)
                    if entry.compressed
                    else entry.value
                )

                # Track access time
                access_time = (time.time() - start_time) * 1000
                self._access_times.append(access_time)
                if len(self._access_times) > 1000:  # Keep last 1000 measurements
                    self._access_times.pop(0)

                return value

            # Check disk cache if hybrid mode
            if self._config.level == CacheLevel.HYBRID:
                disk_value = await self._get_from_disk(key)
                if disk_value is not None:
                    # Promote to memory cache
                    await self.set(
                        key, disk_value, ttl_seconds=self._config.default_ttl_seconds
                    )
                    self._statistics.hits += 1
                    return disk_value

            self._statistics.misses += 1
            return default

        except Exception as e:
            await self._logger.error(
                "Cache get operation failed", {"key": key, "error": str(e)}
            )
            self._statistics.misses += 1
            return default

    async def set(self, key: str, value: T, ttl_seconds: int | None = None) -> bool:
        """
        Set value in cache with optional TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live in seconds

        Returns:
            True if successfully cached
        """
        try:
            ttl = ttl_seconds or self._config.default_ttl_seconds

            # Calculate size
            value_size = await self._calculate_size(value)

            # Compress large values if enabled
            compressed = False
            cached_value = value
            if (
                self._config.enable_compression
                and value_size > self._config.compression_threshold_bytes
            ):
                cached_value = await self._compress_value(value)
                compressed = True
                compressed_size = await self._calculate_size(cached_value)
                self._statistics.compression_ratio = (
                    (value_size - compressed_size) / value_size * 100
                )

            # Create cache entry
            entry = CacheEntry(
                key=key,
                value=cached_value,
                ttl_seconds=ttl,
                size_bytes=await self._calculate_size(cached_value),
                compressed=compressed,
            )

            # Check if we need to evict entries
            await self._ensure_capacity(entry.size_bytes)

            # Store in memory cache
            self._memory_cache[key] = entry

            # Update access tracking for LFU
            if self._config.strategy == CacheStrategy.LFU:
                self._access_tracker[key] = 1

            # Store on disk if needed
            if self._config.level in [CacheLevel.DISK, CacheLevel.HYBRID]:
                await self._save_to_disk(key, value, ttl)

            # Update statistics
            self._statistics.entry_count = len(self._memory_cache)
            self._statistics.memory_usage_bytes += entry.size_bytes

            return True

        except Exception as e:
            await self._logger.error(
                "Cache set operation failed", {"key": key, "error": str(e)}
            )
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete value from cache.

        Args:
            key: Cache key to delete

        Returns:
            True if deleted, False if not found
        """
        try:
            # Remove from memory
            if key in self._memory_cache:
                await self._remove_entry(key, reason="manual_delete")

                # Remove from disk
                if self._config.level in [CacheLevel.DISK, CacheLevel.HYBRID]:
                    await self._delete_from_disk(key)

                return True

            return False

        except Exception as e:
            await self._logger.error(
                "Cache delete operation failed", {"key": key, "error": str(e)}
            )
            return False

    async def clear(self) -> None:
        """Clear all cache entries"""
        try:
            # Clear memory cache
            self._memory_cache.clear()
            self._access_tracker.clear()

            # Clear disk cache
            if self._config.level in [CacheLevel.DISK, CacheLevel.HYBRID]:
                await self._clear_disk_cache()

            # Reset statistics
            self._statistics = CacheStatistics()

            await self._logger.info("Cache cleared successfully")

        except Exception as e:
            await self._logger.error("Cache clear operation failed", {"error": str(e)})

    async def get_statistics(self) -> CacheStatistics:
        """Get current cache statistics"""
        # Update memory usage
        self._statistics.memory_usage_bytes = sum(
            entry.size_bytes for entry in self._memory_cache.values()
        )

        # Update entry count
        self._statistics.entry_count = len(self._memory_cache)

        # Update average access time
        if self._access_times:
            self._statistics.average_access_time_ms = sum(self._access_times) / len(
                self._access_times
            )

        return self._statistics

    async def get_cache_info(self) -> dict[str, Any]:
        """Get detailed cache information"""
        stats = await self.get_statistics()

        return {
            "configuration": {
                "strategy": self._config.strategy.value,
                "level": self._config.level.value,
                "max_memory_mb": self._config.max_memory_mb,
                "max_entries": self._config.max_entries,
                "default_ttl_seconds": self._config.default_ttl_seconds,
                "compression_enabled": self._config.enable_compression,
            },
            "statistics": {
                "hits": stats.hits,
                "misses": stats.misses,
                "hit_rate": stats.hit_rate,
                "evictions": stats.evictions,
                "expired_removals": stats.expired_removals,
                "memory_usage_mb": stats.memory_usage_mb,
                "entry_count": stats.entry_count,
                "compression_ratio": stats.compression_ratio,
                "average_access_time_ms": stats.average_access_time_ms,
            },
            "entries": [
                {
                    "key": key,
                    "age_seconds": entry.age_seconds,
                    "access_count": entry.access_count,
                    "size_bytes": entry.size_bytes,
                    "compressed": entry.compressed,
                    "expires_in": (
                        entry.ttl_seconds - entry.age_seconds
                        if entry.ttl_seconds
                        else None
                    ),
                }
                for key, entry in list(self._memory_cache.items())[
                    :10
                ]  # First 10 entries
            ],
        }

    # =============================================================================
    # Private Methods
    # =============================================================================

    async def _ensure_capacity(self, new_entry_size: int) -> None:
        """Ensure cache has capacity for new entry"""
        # Check memory limit
        current_memory = sum(entry.size_bytes for entry in self._memory_cache.values())
        max_memory_bytes = self._config.max_memory_mb * 1024 * 1024

        # Check entry count limit
        current_entries = len(self._memory_cache)

        # Evict entries if necessary
        while (current_memory + new_entry_size > max_memory_bytes) or (
            current_entries >= self._config.max_entries
        ):
            if not self._memory_cache:
                break

            evicted_key = await self._select_eviction_candidate()
            if evicted_key:
                evicted_entry = self._memory_cache[evicted_key]
                current_memory -= evicted_entry.size_bytes
                current_entries -= 1
                await self._remove_entry(evicted_key, reason="eviction")
                self._statistics.evictions += 1
            else:
                break

    async def _select_eviction_candidate(self) -> str | None:
        """Select entry for eviction based on strategy"""
        if not self._memory_cache:
            return None

        if self._config.strategy == CacheStrategy.LRU:
            # First item is least recently used
            return next(iter(self._memory_cache))

        elif self._config.strategy == CacheStrategy.LFU:
            # Find least frequently used
            if self._access_tracker:
                return min(self._access_tracker.keys(), key=self._access_tracker.get)
            return next(iter(self._memory_cache))

        elif self._config.strategy == CacheStrategy.FIFO:
            # First item is oldest
            return next(iter(self._memory_cache))

        elif self._config.strategy == CacheStrategy.TTL_ONLY:
            # Find expired entry or oldest
            for key, entry in self._memory_cache.items():
                if entry.is_expired:
                    return key
            return next(iter(self._memory_cache))

        return next(iter(self._memory_cache))

    async def _remove_entry(self, key: str, reason: str) -> None:
        """Remove entry from cache"""
        if key in self._memory_cache:
            entry = self._memory_cache.pop(key)
            self._statistics.memory_usage_bytes -= entry.size_bytes

            if key in self._access_tracker:
                del self._access_tracker[key]

            await self._logger.debug(
                "Cache entry removed",
                {
                    "key": key,
                    "reason": reason,
                    "age_seconds": entry.age_seconds,
                    "access_count": entry.access_count,
                },
            )

    async def _cleanup_loop(self) -> None:
        """Background cleanup loop"""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self._config.cleanup_interval_seconds)
                await self._cleanup_expired_entries()

            except asyncio.CancelledError:
                break
            except Exception as e:
                await self._logger.error("Cache cleanup error", {"error": str(e)})

    async def _cleanup_expired_entries(self) -> None:
        """Remove expired cache entries"""
        expired_keys = []
        for key, entry in self._memory_cache.items():
            if entry.is_expired:
                expired_keys.append(key)

        for key in expired_keys:
            await self._remove_entry(key, reason="expired")
            self._statistics.expired_removals += 1

        if expired_keys:
            await self._logger.debug(
                "Removed expired cache entries", {"count": len(expired_keys)}
            )

    async def _calculate_size(self, value: Any) -> int:
        """Calculate approximate size of value in bytes"""
        try:
            return len(pickle.dumps(value))
        except (pickle.PicklingError, TypeError, AttributeError):
            # Fallback to string representation size if pickling fails
            return len(str(value).encode("utf-8"))

    async def _compress_value(self, value: Any) -> bytes:
        """Compress value using gzip"""
        try:
            pickled = pickle.dumps(value)
            return gzip.compress(pickled)
        except Exception as e:
            await self._logger.warning("Value compression failed", {"error": str(e)})
            return pickle.dumps(value)

    async def _decompress_value(self, compressed_value: bytes) -> Any:
        """Decompress value from gzip"""
        try:
            if isinstance(compressed_value, bytes):
                decompressed = gzip.decompress(compressed_value)
                return pickle.loads(decompressed)
            return compressed_value
        except Exception as e:
            await self._logger.warning("Value decompression failed", {"error": str(e)})
            return compressed_value

    async def _save_to_disk(self, key: str, value: Any, ttl: int) -> None:
        """Save entry to disk cache"""
        try:
            cache_file = (
                self._config.disk_cache_directory / f"{self._hash_key(key)}.cache"
            )

            entry_data = {
                "key": key,
                "value": value,
                "created_at": datetime.now(UTC).isoformat(),
                "ttl_seconds": ttl,
            }

            with open(cache_file, "wb") as f:
                if self._config.enable_compression:
                    compressed_data = gzip.compress(pickle.dumps(entry_data))
                    f.write(compressed_data)
                else:
                    pickle.dump(entry_data, f)

        except Exception as e:
            await self._logger.warning(
                "Failed to save cache entry to disk", {"key": key, "error": str(e)}
            )

    async def _get_from_disk(self, key: str) -> Any | None:
        """Get entry from disk cache"""
        try:
            cache_file = (
                self._config.disk_cache_directory / f"{self._hash_key(key)}.cache"
            )

            if not cache_file.exists():
                return None

            with open(cache_file, "rb") as f:
                if self._config.enable_compression:
                    compressed_data = f.read()
                    entry_data = pickle.loads(gzip.decompress(compressed_data))
                else:
                    entry_data = pickle.load(f)

            # Check if expired
            created_at = datetime.fromisoformat(entry_data["created_at"])
            ttl = entry_data["ttl_seconds"]

            if ttl and (datetime.now(UTC) - created_at).total_seconds() > ttl:
                await self._delete_from_disk(key)
                return None

            return entry_data["value"]

        except Exception as e:
            await self._logger.warning(
                "Failed to load cache entry from disk", {"key": key, "error": str(e)}
            )
            return None

    async def _delete_from_disk(self, key: str) -> None:
        """Delete entry from disk cache"""
        try:
            cache_file = (
                self._config.disk_cache_directory / f"{self._hash_key(key)}.cache"
            )
            if cache_file.exists():
                cache_file.unlink()
        except Exception as e:
            await self._logger.warning(
                "Failed to delete cache entry from disk", {"key": key, "error": str(e)}
            )

    async def _clear_disk_cache(self) -> None:
        """Clear all disk cache files"""
        try:
            for cache_file in self._config.disk_cache_directory.glob("*.cache"):
                cache_file.unlink()
        except Exception as e:
            await self._logger.warning("Failed to clear disk cache", {"error": str(e)})

    async def _save_persistent_cache(self) -> None:
        """Save cache state for persistence"""
        try:
            if not self._memory_cache:
                return

            persistence_file = self._config.disk_cache_directory / "cache_state.json"

            cache_state = {
                "entries": {
                    key: {
                        "value": entry.value,
                        "created_at": entry.created_at.isoformat(),
                        "ttl_seconds": entry.ttl_seconds,
                        "access_count": entry.access_count,
                    }
                    for key, entry in self._memory_cache.items()
                    if not entry.is_expired
                },
                "statistics": {
                    "hits": self._statistics.hits,
                    "misses": self._statistics.misses,
                    "evictions": self._statistics.evictions,
                },
            }

            with open(persistence_file, "w") as f:
                json.dump(cache_state, f, default=str)

        except Exception as e:
            await self._logger.warning(
                "Failed to save persistent cache", {"error": str(e)}
            )

    async def _load_persistent_cache(self) -> None:
        """Load cache state from persistence"""
        try:
            persistence_file = self._config.disk_cache_directory / "cache_state.json"

            if not persistence_file.exists():
                return

            with open(persistence_file) as f:
                cache_state = json.load(f)

            # Restore entries
            for key, entry_data in cache_state.get("entries", {}).items():
                created_at = datetime.fromisoformat(entry_data["created_at"])
                ttl = entry_data.get("ttl_seconds")

                # Skip expired entries
                if ttl and (datetime.now(UTC) - created_at).total_seconds() > ttl:
                    continue

                entry = CacheEntry(
                    key=key,
                    value=entry_data["value"],
                    created_at=created_at,
                    ttl_seconds=ttl,
                    access_count=entry_data.get("access_count", 0),
                )

                self._memory_cache[key] = entry

            # Restore statistics
            stats_data = cache_state.get("statistics", {})
            self._statistics.hits = stats_data.get("hits", 0)
            self._statistics.misses = stats_data.get("misses", 0)
            self._statistics.evictions = stats_data.get("evictions", 0)

        except Exception as e:
            await self._logger.warning(
                "Failed to load persistent cache", {"error": str(e)}
            )

    def _hash_key(self, key: str) -> str:
        """Generate hash for cache key"""
        return hashlib.md5(key.encode()).hexdigest()


# =============================================================================
# Decorator for Automatic Caching
# =============================================================================


def cached(
    ttl_seconds: int = 3600,
    key_prefix: str = "",
    cache_service: CacheService | None = None,
):
    """
    Decorator for automatic function result caching.

    Args:
        ttl_seconds: Time to live for cached results
        key_prefix: Prefix for cache keys
        cache_service: Cache service instance (will use global if None)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key_parts = [key_prefix, func.__name__]

            # Add arguments to key
            if args:
                key_parts.extend(str(arg) for arg in args)
            if kwargs:
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))

            cache_key = ":".join(key_parts)

            # Get cache service
            service = cache_service
            if service is None:
                # Try to get from DI container or use global instance
                try:
                    from .di_container import get_container

                    container = get_container()
                    service = container.get(CacheService)
                except:
                    # Fallback: execute function without caching
                    return (
                        await func(*args, **kwargs)
                        if asyncio.iscoroutinefunction(func)
                        else func(*args, **kwargs)
                    )

            # Try to get from cache
            cached_result = await service.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            await service.set(cache_key, result, ttl_seconds=ttl_seconds)
            return result

        return wrapper

    return decorator


# =============================================================================
# Global Cache Service Access
# =============================================================================

_global_cache_service: CacheService | None = None


async def get_cache_service() -> CacheService:
    """Get global cache service instance"""
    global _global_cache_service

    if _global_cache_service is None:
        from .di_container import get_container

        container = get_container()
        _global_cache_service = CacheService(container)
        await _global_cache_service.initialize()

    return _global_cache_service
