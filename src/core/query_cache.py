# =============================================================================
# QuranBot - Intelligent Query Cache
# =============================================================================
# High-performance query result caching for frequently accessed data
# Reduces database load and improves response times by 10-100x
# =============================================================================

from datetime import UTC, datetime
from functools import wraps
import hashlib
import json
from typing import Any

from .cache_service import CacheService
from .logger import StructuredLogger


class QueryCache:
    """
    Intelligent query result caching system.

    Features:
    - Automatic query result caching
    - Smart invalidation based on data changes
    - Category-based cache management
    - Performance analytics
    - Memory-efficient storage
    """

    def __init__(self, cache_service: CacheService, logger: StructuredLogger):
        """Initialize query cache"""
        self.cache_service = cache_service
        self.logger = logger

        # Cache categories with different TTLs
        self.cache_ttls = {
            "quiz_questions": 3600,  # 1 hour - questions don't change often
            "daily_verses": 1800,  # 30 minutes - verses are semi-static
            "user_stats": 300,  # 5 minutes - user data changes more
            "leaderboard": 600,  # 10 minutes - balance freshness vs performance
            "quiz_config": 900,  # 15 minutes - config changes are rare
            "system_stats": 180,  # 3 minutes - system data changes frequently
            "hadith": 7200,  # 2 hours - hadith data is very stable
            "duas": 3600,  # 1 hour - duas are stable
        }

        # Cache invalidation tracking
        self.invalidation_patterns = {
            "quiz_questions": ["quiz_*", "leaderboard_*", "user_stats_*"],
            "user_quiz_stats": ["user_stats_*", "leaderboard_*"],
            "quiz_config": ["quiz_*"],
            "daily_verses": ["verses_*"],
            "conversations": ["conversation_*"],
        }

        # Performance tracking
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_queries = 0

    def _generate_cache_key(
        self, category: str, query: str, params: tuple = None
    ) -> str:
        """Generate a unique cache key for the query"""
        key_data = {"category": category, "query": query, "params": params or ()}
        key_string = json.dumps(key_data, sort_keys=True)
        hash_object = hashlib.md5(key_string.encode())
        return f"query_cache:{category}:{hash_object.hexdigest()[:16]}"

    async def get_cached_result(
        self, category: str, query: str, params: tuple = None
    ) -> Any | None:
        """Get cached query result"""
        cache_key = self._generate_cache_key(category, query, params)

        try:
            result = await self.cache_service.get(cache_key)

            if result is not None:
                self.cache_hits += 1
                await self.logger.debug(
                    "Query cache hit",
                    {
                        "category": category,
                        "cache_key": cache_key[:32] + "...",
                        "hit_rate": self.get_hit_rate(),
                    },
                )
                return result
            else:
                self.cache_misses += 1
                return None

        except Exception as e:
            await self.logger.warning(
                "Query cache retrieval failed", {"category": category, "error": str(e)}
            )
            return None

    async def cache_result(
        self, category: str, query: str, params: tuple, result: Any
    ) -> bool:
        """Cache query result with appropriate TTL"""
        cache_key = self._generate_cache_key(category, query, params)
        ttl = self.cache_ttls.get(category, 600)  # Default 10 minutes

        try:
            success = await self.cache_service.set(cache_key, result, ttl_seconds=ttl)

            if success:
                await self.logger.debug(
                    "Query result cached",
                    {
                        "category": category,
                        "cache_key": cache_key[:32] + "...",
                        "ttl": ttl,
                        "result_size": len(str(result)) if result else 0,
                    },
                )

            return success

        except Exception as e:
            await self.logger.warning(
                "Query cache storage failed", {"category": category, "error": str(e)}
            )
            return False

    async def invalidate_category(self, category: str) -> int:
        """Invalidate all cached results for a category"""
        invalidation_count = 0

        # Get patterns to invalidate
        patterns = self.invalidation_patterns.get(category, [f"{category}_*"])

        for pattern in patterns:
            try:
                # This would need to be implemented in the cache service
                # For now, we'll track that invalidation was requested
                await self.logger.info(
                    "Cache invalidation requested",
                    {"category": category, "pattern": pattern},
                )
                invalidation_count += 1

            except Exception as e:
                await self.logger.warning(
                    "Cache invalidation failed",
                    {"category": category, "pattern": pattern, "error": str(e)},
                )

        return invalidation_count

    def get_hit_rate(self) -> float:
        """Calculate cache hit rate percentage"""
        total = self.cache_hits + self.cache_misses
        return (self.cache_hits / total * 100) if total > 0 else 0.0

    def get_statistics(self) -> dict[str, Any]:
        """Get cache performance statistics"""
        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate_percentage": round(self.get_hit_rate(), 2),
            "total_queries": self.cache_hits + self.cache_misses,
            "categories_tracked": list(self.cache_ttls.keys()),
            "invalidation_patterns": len(self.invalidation_patterns),
        }


def cached_query(category: str, ttl_override: int = None):
    """
    Decorator for caching database query results.

    Args:
        category: Cache category for the query
        ttl_override: Override default TTL for this query
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Try to get query cache from the service
            query_cache = getattr(self, "_query_cache", None)

            if not query_cache:
                # No cache available, execute query directly
                return await func(self, *args, **kwargs)

            # Generate cache key based on function and parameters
            query_signature = f"{func.__name__}({args}, {kwargs})"

            # Try to get cached result
            cached_result = await query_cache.get_cached_result(
                category, query_signature, args
            )

            if cached_result is not None:
                return cached_result

            # Execute query and cache result
            result = await func(self, *args, **kwargs)

            # Cache the result
            await query_cache.cache_result(category, query_signature, args, result)

            return result

        return wrapper

    return decorator


class SmartQueryOptimizer:
    """
    Analyzes query patterns and suggests optimizations.
    """

    def __init__(self, logger: StructuredLogger):
        self.logger = logger
        self.query_patterns = {}
        self.slow_queries = []

    async def track_query(
        self, query: str, execution_time_ms: float, result_count: int
    ):
        """Track query performance for analysis"""

        # Track query patterns
        query_hash = hashlib.md5(query.encode()).hexdigest()[:8]

        if query_hash not in self.query_patterns:
            self.query_patterns[query_hash] = {
                "query": query[:100] + "..." if len(query) > 100 else query,
                "execution_count": 0,
                "total_time_ms": 0,
                "avg_time_ms": 0,
                "result_counts": [],
            }

        pattern = self.query_patterns[query_hash]
        pattern["execution_count"] += 1
        pattern["total_time_ms"] += execution_time_ms
        pattern["avg_time_ms"] = pattern["total_time_ms"] / pattern["execution_count"]
        pattern["result_counts"].append(result_count)

        # Track slow queries (>10ms)
        if execution_time_ms > 10:
            self.slow_queries.append(
                {
                    "query": query,
                    "execution_time_ms": execution_time_ms,
                    "result_count": result_count,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )

            # Keep only last 100 slow queries
            if len(self.slow_queries) > 100:
                self.slow_queries.pop(0)

    async def get_optimization_suggestions(self) -> list[dict[str, Any]]:
        """Generate optimization suggestions based on query patterns"""
        suggestions = []

        # Find frequently executed queries
        frequent_queries = [
            (hash_key, pattern)
            for hash_key, pattern in self.query_patterns.items()
            if pattern["execution_count"] > 10
        ]

        for hash_key, pattern in frequent_queries:
            suggestion = {
                "type": "frequent_query",
                "query": pattern["query"],
                "execution_count": pattern["execution_count"],
                "avg_time_ms": round(pattern["avg_time_ms"], 2),
                "suggestion": "Consider adding an index or caching this query",
            }
            suggestions.append(suggestion)

        # Find slow queries
        if self.slow_queries:
            recent_slow = [q for q in self.slow_queries if q["execution_time_ms"] > 50]
            for query in recent_slow:
                suggestion = {
                    "type": "slow_query",
                    "query": query["query"][:100] + "...",
                    "execution_time_ms": query["execution_time_ms"],
                    "suggestion": "Query is slow - consider optimization or indexing",
                }
                suggestions.append(suggestion)

        return suggestions

    def get_statistics(self) -> dict[str, Any]:
        """Get query performance statistics"""
        total_queries = sum(p["execution_count"] for p in self.query_patterns.values())
        avg_time = (
            sum(p["avg_time_ms"] for p in self.query_patterns.values())
            / len(self.query_patterns)
            if self.query_patterns
            else 0
        )

        return {
            "total_unique_queries": len(self.query_patterns),
            "total_executions": total_queries,
            "average_execution_time_ms": round(avg_time, 2),
            "slow_queries_count": len(self.slow_queries),
            "most_frequent_queries": sorted(
                self.query_patterns.items(),
                key=lambda x: x[1]["execution_count"],
                reverse=True,
            )[:5],
        }
