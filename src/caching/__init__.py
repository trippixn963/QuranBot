"""
QuranBot Caching Module.

This module provides both in-memory and distributed Redis caching capabilities
with seamless fallback and unified interface.
"""

from .redis_cache import (
    RedisCacheManager,
    CacheConfig,
    CacheEntry,
    CacheSerializer,
    create_redis_cache,
    REDIS_AVAILABLE
)

__all__ = [
    "RedisCacheManager",
    "CacheConfig", 
    "CacheEntry",
    "CacheSerializer",
    "create_redis_cache",
    "REDIS_AVAILABLE"
]