"""
QuranBot Redis Distributed Caching System.

This module provides a comprehensive Redis-based caching solution that replaces
the in-memory caching system with distributed caching capabilities, perfect for
scaling across multiple instances and maintaining cache coherence.
"""

import json
import pickle
import hashlib
import asyncio
from typing import Any, Dict, List, Optional, Union, Callable, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging
from contextlib import asynccontextmanager

try:
    import redis.asyncio as redis
    from redis.asyncio import ConnectionPool, Redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from ..core.logger import StructuredLogger


class CacheSerializer(Enum):
    """Serialization methods for cache values."""
    JSON = "json"
    PICKLE = "pickle"
    STRING = "string"


@dataclass
class CacheConfig:
    """Configuration for Redis cache connection and behavior."""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    username: Optional[str] = None
    ssl: bool = False
    ssl_ca_certs: Optional[str] = None
    max_connections: int = 50
    retry_on_timeout: bool = True
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    health_check_interval: int = 30
    key_prefix: str = "quranbot"
    default_ttl: int = 3600  # 1 hour
    max_key_length: int = 250
    compression_threshold: int = 1024  # Compress values larger than 1KB


@dataclass 
class CacheEntry:
    """Represents a cache entry with metadata."""
    key: str
    value: Any
    ttl: Optional[int] = None
    serializer: CacheSerializer = CacheSerializer.JSON
    created_at: datetime = field(default_factory=datetime.utcnow)
    accessed_at: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    tags: List[str] = field(default_factory=list)


class RedisCacheManager:
    """
    Advanced Redis-based caching manager for QuranBot.
    
    Features:
    - Distributed caching across multiple bot instances
    - Multiple serialization formats (JSON, Pickle, String)
    - TTL management with automatic expiration
    - Cache tagging for bulk operations
    - Compression for large values
    - Connection pooling and retry logic
    - Performance metrics integration
    - Pipeline operations for batch processing
    """
    
    def __init__(self, config: CacheConfig, logger: Optional[StructuredLogger] = None):
        """
        Initialize Redis cache manager.
        
        Args:
            config: Cache configuration settings
            logger: Optional structured logger instance
            
        Raises:
            ImportError: If redis package is not installed
            ConnectionError: If Redis connection cannot be established
        """
        if not REDIS_AVAILABLE:
            raise ImportError(
                "Redis not available. Install with: pip install redis"
            )
        
        self.config = config
        self._logger = logger or StructuredLogger("redis_cache")
        self._redis: Optional[Redis] = None
        self._connection_pool: Optional[ConnectionPool] = None
        self._connected = False
        
        # Performance tracking
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0,
            "total_requests": 0
        }
        
        # Serialization handlers
        self._serializers = {
            CacheSerializer.JSON: self._json_serialize,
            CacheSerializer.PICKLE: self._pickle_serialize,
            CacheSerializer.STRING: self._string_serialize
        }
        
        self._deserializers = {
            CacheSerializer.JSON: self._json_deserialize,
            CacheSerializer.PICKLE: self._pickle_deserialize,
            CacheSerializer.STRING: self._string_deserialize
        }
    
    async def connect(self) -> None:
        """
        Establish connection to Redis server.
        
        Raises:
            ConnectionError: If connection cannot be established
        """
        try:
            # Create connection pool
            self._connection_pool = ConnectionPool(
                host=self.config.host,
                port=self.config.port,
                db=self.config.db,
                password=self.config.password,
                username=self.config.username,
                ssl=self.config.ssl,
                ssl_ca_certs=self.config.ssl_ca_certs,
                max_connections=self.config.max_connections,
                retry_on_timeout=self.config.retry_on_timeout,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                health_check_interval=self.config.health_check_interval,
                decode_responses=False  # We handle encoding ourselves
            )
            
            # Create Redis client
            self._redis = Redis(connection_pool=self._connection_pool)
            
            # Test connection
            await self._redis.ping()
            self._connected = True
            
            await self._logger.info("Redis cache connected successfully", context={
                "host": self.config.host,
                "port": self.config.port,
                "db": self.config.db,
                "max_connections": self.config.max_connections
            })
            
        except Exception as e:
            self._connected = False
            await self._logger.error("Failed to connect to Redis", context={
                "error": str(e),
                "host": self.config.host,
                "port": self.config.port
            })
            raise ConnectionError(f"Redis connection failed: {e}")
    
    async def disconnect(self) -> None:
        """Close Redis connection and cleanup resources."""
        try:
            if self._redis:
                await self._redis.close()
            
            if self._connection_pool:
                await self._connection_pool.disconnect()
            
            self._connected = False
            await self._logger.info("Redis cache disconnected")
            
        except Exception as e:
            await self._logger.error("Error disconnecting from Redis", context={
                "error": str(e)
            })
    
    def _build_key(self, key: str) -> str:
        """
        Build a prefixed cache key.
        
        Args:
            key: Original cache key
            
        Returns:
            Prefixed cache key
        """
        prefixed_key = f"{self.config.key_prefix}:{key}"
        
        # Ensure key length doesn't exceed Redis limits
        if len(prefixed_key) > self.config.max_key_length:
            # Use hash for very long keys
            key_hash = hashlib.md5(prefixed_key.encode()).hexdigest()
            prefixed_key = f"{self.config.key_prefix}:hash:{key_hash}"
        
        return prefixed_key
    
    def _serialize_value(
        self, 
        value: Any, 
        serializer: CacheSerializer
    ) -> bytes:
        """
        Serialize a value for storage in Redis.
        
        Args:
            value: Value to serialize
            serializer: Serialization method to use
            
        Returns:
            Serialized value as bytes
        """
        try:
            serialized = self._serializers[serializer](value)
            
            # Compress large values
            if len(serialized) > self.config.compression_threshold:
                import zlib
                compressed = zlib.compress(serialized)
                # Add compression marker
                return b"COMPRESSED:" + compressed
            
            return serialized
            
        except Exception as e:
            raise ValueError(f"Serialization failed: {e}")
    
    def _deserialize_value(
        self, 
        data: bytes, 
        serializer: CacheSerializer
    ) -> Any:
        """
        Deserialize a value from Redis storage.
        
        Args:
            data: Serialized data from Redis
            serializer: Serialization method used
            
        Returns:
            Deserialized value
        """
        try:
            # Check for compression
            if data.startswith(b"COMPRESSED:"):
                import zlib
                data = zlib.decompress(data[11:])  # Remove "COMPRESSED:" prefix
            
            return self._deserializers[serializer](data)
            
        except Exception as e:
            raise ValueError(f"Deserialization failed: {e}")
    
    # Serialization methods
    def _json_serialize(self, value: Any) -> bytes:
        """Serialize value as JSON."""
        return json.dumps(value, default=str).encode('utf-8')
    
    def _json_deserialize(self, data: bytes) -> Any:
        """Deserialize JSON value."""
        return json.loads(data.decode('utf-8'))
    
    def _pickle_serialize(self, value: Any) -> bytes:
        """Serialize value using pickle."""
        return pickle.dumps(value)
    
    def _pickle_deserialize(self, data: bytes) -> Any:
        """Deserialize pickle value."""
        return pickle.loads(data)
    
    def _string_serialize(self, value: Any) -> bytes:
        """Serialize value as string."""
        return str(value).encode('utf-8')
    
    def _string_deserialize(self, data: bytes) -> Any:
        """Deserialize string value."""
        return data.decode('utf-8')
    
    async def get(
        self, 
        key: str, 
        default: Any = None,
        serializer: CacheSerializer = CacheSerializer.JSON
    ) -> Any:
        """
        Retrieve a value from cache.
        
        Args:
            key: Cache key
            default: Default value if key not found
            serializer: Serialization method used for the value
            
        Returns:
            Cached value or default
        """
        if not self._connected:
            await self._logger.warning("Redis not connected, returning default")
            return default
        
        try:
            redis_key = self._build_key(key)
            data = await self._redis.get(redis_key)
            
            self._stats["total_requests"] += 1
            
            if data is None:
                self._stats["misses"] += 1
                await self._logger.debug("Cache miss", context={"key": key})
                return default
            
            self._stats["hits"] += 1
            value = self._deserialize_value(data, serializer)
            
            await self._logger.debug("Cache hit", context={
                "key": key,
                "size_bytes": len(data)
            })
            
            return value
            
        except Exception as e:
            self._stats["errors"] += 1
            await self._logger.error("Cache get error", context={
                "key": key,
                "error": str(e)
            })
            return default
    
    async def set(
        self, 
        key: str, 
        value: Any,
        ttl: Optional[int] = None,
        serializer: CacheSerializer = CacheSerializer.JSON,
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        Store a value in cache.
        
        Args:
            key: Cache key
            value: Value to store
            ttl: Time to live in seconds (uses default if None)
            serializer: Serialization method to use
            tags: Optional tags for bulk operations
            
        Returns:
            True if successful, False otherwise
        """
        if not self._connected:
            await self._logger.warning("Redis not connected, cache set ignored")
            return False
        
        try:
            redis_key = self._build_key(key)
            serialized_value = self._serialize_value(value, serializer)
            
            # Use default TTL if not specified
            cache_ttl = ttl or self.config.default_ttl
            
            # Store the value
            result = await self._redis.setex(redis_key, cache_ttl, serialized_value)
            
            # Handle tags if provided
            if tags:
                await self._handle_tags(key, tags, cache_ttl)
            
            self._stats["sets"] += 1
            self._stats["total_requests"] += 1
            
            await self._logger.debug("Cache set", context={
                "key": key,
                "ttl": cache_ttl,
                "size_bytes": len(serialized_value),
                "tags": tags or []
            })
            
            return bool(result)
            
        except Exception as e:
            self._stats["errors"] += 1
            await self._logger.error("Cache set error", context={
                "key": key,
                "error": str(e)
            })
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete a value from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key was deleted, False otherwise
        """
        if not self._connected:
            return False
        
        try:
            redis_key = self._build_key(key)
            result = await self._redis.delete(redis_key)
            
            self._stats["deletes"] += 1
            self._stats["total_requests"] += 1
            
            await self._logger.debug("Cache delete", context={
                "key": key,
                "existed": bool(result)
            })
            
            return bool(result)
            
        except Exception as e:
            self._stats["errors"] += 1
            await self._logger.error("Cache delete error", context={
                "key": key,
                "error": str(e)
            })
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache.
        
        Args:
            key: Cache key to check
            
        Returns:
            True if key exists, False otherwise
        """
        if not self._connected:
            return False
        
        try:
            redis_key = self._build_key(key)
            result = await self._redis.exists(redis_key)
            return bool(result)
            
        except Exception as e:
            await self._logger.error("Cache exists error", context={
                "key": key,
                "error": str(e)
            })
            return False
    
    async def ttl(self, key: str) -> int:
        """
        Get time to live for a key.
        
        Args:
            key: Cache key
            
        Returns:
            TTL in seconds (-1 if no expiry, -2 if key doesn't exist)
        """
        if not self._connected:
            return -2
        
        try:
            redis_key = self._build_key(key)
            return await self._redis.ttl(redis_key)
            
        except Exception as e:
            await self._logger.error("Cache TTL error", context={
                "key": key,
                "error": str(e)
            })
            return -2
    
    async def expire(self, key: str, seconds: int) -> bool:
        """
        Set expiration time for a key.
        
        Args:
            key: Cache key
            seconds: Expiration time in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self._connected:
            return False
        
        try:
            redis_key = self._build_key(key)
            result = await self._redis.expire(redis_key, seconds)
            return bool(result)
            
        except Exception as e:
            await self._logger.error("Cache expire error", context={
                "key": key,
                "error": str(e)
            })
            return False
    
    async def get_multiple(
        self, 
        keys: List[str],
        serializer: CacheSerializer = CacheSerializer.JSON
    ) -> Dict[str, Any]:
        """
        Get multiple values from cache in a single operation.
        
        Args:
            keys: List of cache keys
            serializer: Serialization method used
            
        Returns:
            Dictionary mapping keys to their values (missing keys excluded)
        """
        if not self._connected or not keys:
            return {}
        
        try:
            redis_keys = [self._build_key(key) for key in keys]
            values = await self._redis.mget(redis_keys)
            
            result = {}
            for i, (key, value) in enumerate(zip(keys, values)):
                if value is not None:
                    try:
                        result[key] = self._deserialize_value(value, serializer)
                        self._stats["hits"] += 1
                    except Exception as e:
                        await self._logger.error("Error deserializing cached value", context={
                            "key": key,
                            "error": str(e)
                        })
                else:
                    self._stats["misses"] += 1
            
            self._stats["total_requests"] += len(keys)
            
            await self._logger.debug("Cache multi-get", context={
                "requested_keys": len(keys),
                "found_keys": len(result)
            })
            
            return result
            
        except Exception as e:
            self._stats["errors"] += 1
            await self._logger.error("Cache multi-get error", context={
                "keys": keys,
                "error": str(e)
            })
            return {}
    
    async def set_multiple(
        self, 
        mapping: Dict[str, Any],
        ttl: Optional[int] = None,
        serializer: CacheSerializer = CacheSerializer.JSON
    ) -> bool:
        """
        Set multiple values in cache using pipeline for efficiency.
        
        Args:
            mapping: Dictionary of key-value pairs to store
            ttl: Time to live in seconds
            serializer: Serialization method to use
            
        Returns:
            True if all operations successful, False otherwise
        """
        if not self._connected or not mapping:
            return False
        
        try:
            cache_ttl = ttl or self.config.default_ttl
            
            # Use pipeline for batch operations
            async with self._redis.pipeline() as pipe:
                for key, value in mapping.items():
                    redis_key = self._build_key(key)
                    serialized_value = self._serialize_value(value, serializer)
                    pipe.setex(redis_key, cache_ttl, serialized_value)
                
                results = await pipe.execute()
            
            success = all(results)
            self._stats["sets"] += len(mapping)
            self._stats["total_requests"] += len(mapping)
            
            await self._logger.debug("Cache multi-set", context={
                "keys_count": len(mapping),
                "ttl": cache_ttl,
                "success": success
            })
            
            return success
            
        except Exception as e:
            self._stats["errors"] += 1
            await self._logger.error("Cache multi-set error", context={
                "keys_count": len(mapping),
                "error": str(e)
            })
            return False
    
    async def delete_multiple(self, keys: List[str]) -> int:
        """
        Delete multiple keys from cache.
        
        Args:
            keys: List of cache keys to delete
            
        Returns:
            Number of keys deleted
        """
        if not self._connected or not keys:
            return 0
        
        try:
            redis_keys = [self._build_key(key) for key in keys]
            deleted_count = await self._redis.delete(*redis_keys)
            
            self._stats["deletes"] += deleted_count
            self._stats["total_requests"] += len(keys)
            
            await self._logger.debug("Cache multi-delete", context={
                "requested_keys": len(keys),
                "deleted_keys": deleted_count
            })
            
            return deleted_count
            
        except Exception as e:
            self._stats["errors"] += 1
            await self._logger.error("Cache multi-delete error", context={
                "keys": keys,
                "error": str(e)
            })
            return 0
    
    async def clear_by_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.
        
        Args:
            pattern: Redis pattern (supports * and ? wildcards)
            
        Returns:
            Number of keys deleted
        """
        if not self._connected:
            return 0
        
        try:
            search_pattern = self._build_key(pattern)
            keys = []
            
            # Use SCAN to find matching keys (more efficient than KEYS)
            async for key in self._redis.scan_iter(match=search_pattern):
                keys.append(key)
            
            if keys:
                deleted_count = await self._redis.delete(*keys)
                self._stats["deletes"] += deleted_count
                
                await self._logger.debug("Cache pattern delete", context={
                    "pattern": pattern,
                    "deleted_keys": deleted_count
                })
                
                return deleted_count
            
            return 0
            
        except Exception as e:
            self._stats["errors"] += 1
            await self._logger.error("Cache pattern delete error", context={
                "pattern": pattern,
                "error": str(e)
            })
            return 0
    
    async def _handle_tags(self, key: str, tags: List[str], ttl: int) -> None:
        """Handle tag associations for cache entries."""
        try:
            # Store tags in separate sets for bulk operations
            async with self._redis.pipeline() as pipe:
                for tag in tags:
                    tag_key = self._build_key(f"tag:{tag}")
                    pipe.sadd(tag_key, key)
                    pipe.expire(tag_key, ttl + 60)  # Tags live slightly longer
                
                await pipe.execute()
                
        except Exception as e:
            await self._logger.error("Error handling cache tags", context={
                "key": key,
                "tags": tags,
                "error": str(e)
            })
    
    async def delete_by_tags(self, tags: List[str]) -> int:
        """
        Delete all cache entries associated with given tags.
        
        Args:
            tags: List of tags
            
        Returns:
            Number of keys deleted
        """
        if not self._connected or not tags:
            return 0
        
        try:
            keys_to_delete = set()
            
            # Collect keys from all tag sets
            for tag in tags:
                tag_key = self._build_key(f"tag:{tag}")
                tag_members = await self._redis.smembers(tag_key)
                
                for member in tag_members:
                    if isinstance(member, bytes):
                        member = member.decode('utf-8')
                    keys_to_delete.add(self._build_key(member))
            
            if keys_to_delete:
                deleted_count = await self._redis.delete(*keys_to_delete)
                
                # Clean up tag sets
                tag_keys = [self._build_key(f"tag:{tag}") for tag in tags]
                await self._redis.delete(*tag_keys)
                
                await self._logger.debug("Cache tag delete", context={
                    "tags": tags,
                    "deleted_keys": deleted_count
                })
                
                return deleted_count
            
            return 0
            
        except Exception as e:
            self._stats["errors"] += 1
            await self._logger.error("Cache tag delete error", context={
                "tags": tags,
                "error": str(e)
            })
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache performance statistics.
        
        Returns:
            Dictionary containing cache statistics
        """
        stats = self._stats.copy()
        
        # Calculate hit rate
        total_gets = stats["hits"] + stats["misses"]
        if total_gets > 0:
            stats["hit_rate"] = stats["hits"] / total_gets
        else:
            stats["hit_rate"] = 0.0
        
        # Add Redis info if connected
        if self._connected:
            try:
                redis_info = await self._redis.info("memory")
                stats["redis_memory_used"] = redis_info.get("used_memory", 0)
                stats["redis_memory_human"] = redis_info.get("used_memory_human", "0B")
                
                keyspace_info = await self._redis.info("keyspace")
                db_info = keyspace_info.get(f"db{self.config.db}", {})
                if isinstance(db_info, dict):
                    stats["total_keys"] = db_info.get("keys", 0)
                else:
                    stats["total_keys"] = 0
                
            except Exception as e:
                await self._logger.error("Error getting Redis stats", context={
                    "error": str(e)
                })
        
        stats["connected"] = self._connected
        
        return stats
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Redis connection.
        
        Returns:
            Dictionary containing health status
        """
        health = {
            "connected": self._connected,
            "healthy": False,
            "latency_ms": None,
            "error": None
        }
        
        if not self._connected:
            health["error"] = "Not connected to Redis"
            return health
        
        try:
            # Measure ping latency
            start_time = asyncio.get_event_loop().time()
            await self._redis.ping()
            end_time = asyncio.get_event_loop().time()
            
            health["latency_ms"] = (end_time - start_time) * 1000
            health["healthy"] = True
            
        except Exception as e:
            health["error"] = str(e)
            health["healthy"] = False
        
        return health
    
    @asynccontextmanager
    async def pipeline(self):
        """
        Context manager for Redis pipeline operations.
        
        Usage:
            async with cache.pipeline() as pipe:
                pipe.set("key1", "value1")
                pipe.set("key2", "value2")
                results = await pipe.execute()
        """
        if not self._connected:
            raise ConnectionError("Redis not connected")
        
        async with self._redis.pipeline() as pipe:
            yield pipe


# Factory function for easy integration
async def create_redis_cache(
    config: Optional[CacheConfig] = None,
    logger: Optional[StructuredLogger] = None
) -> Optional[RedisCacheManager]:
    """
    Create and initialize a Redis cache manager.
    
    Args:
        config: Cache configuration (uses defaults if None)
        logger: Optional structured logger
        
    Returns:
        RedisCacheManager instance or None if Redis is not available
    """
    if not REDIS_AVAILABLE:
        if logger:
            await logger.warning("Redis not available - caching disabled")
        return None
    
    try:
        cache_config = config or CacheConfig()
        cache_manager = RedisCacheManager(cache_config, logger)
        await cache_manager.connect()
        return cache_manager
        
    except Exception as e:
        if logger:
            await logger.error("Failed to create Redis cache", context={
                "error": str(e)
            })
        return None