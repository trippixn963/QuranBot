# =============================================================================
# QuranBot - Rate Limiter Service
# =============================================================================
# Manages rate limiting for AI mentions to prevent abuse
# =============================================================================

import asyncio
from datetime import datetime, timedelta
from typing import Any

from ...config import get_config
from ...core.logger import TreeLogger
from ..core.base_service import BaseService


class RateLimiter(BaseService):
    """
    Rate limiting service for AI mentions.

    Features:
    - Per-user rate limiting (1 per hour by default)
    - Developer bypass (unlimited)
    - Database persistence
    - Friendly cooldown messages
    """

    def __init__(self, bot):
        """Initialize rate limiter."""
        super().__init__("RateLimiter")
        self.bot = bot
        self.config = get_config()
        self.database_service = None

        TreeLogger.debug(
            "Rate Limiter instance created",
            {
                "rate_limit": self.config.ai_rate_limit_per_hour,
                "developer_id": self.config.developer_id,
            },
            service=self.service_name,
        )

        # Cache for recent checks (reduces database queries)
        self.cache: dict[int, datetime] = {}
        self.cache_duration = timedelta(minutes=5)

    async def _initialize(self) -> bool:
        """Initialize the rate limiter."""
        try:
            TreeLogger.info("Initializing Rate Limiter", service=self.service_name)

            # Get database service
            self.database_service = self.bot.services.get("database")
            if not self.database_service:
                raise Exception("Database service not available")

            # Create tables
            TreeLogger.debug("Creating rate limit tables", service=self.service_name)
            await self._create_tables()

            TreeLogger.info(
                "Rate Limiter initialized",
                {
                    "rate_limit": f"{self.config.ai_rate_limit_per_hour}/hour",
                    "developer_bypass": "enabled",
                },
                service=self.service_name,
            )

            return True

        except Exception as e:
            await self.error_handler.handle_error(
                e, {"operation": "rate_limiter_initialization"}
            )
            return False

    async def _start(self) -> bool:
        """Start the rate limiter."""
        TreeLogger.info("Rate Limiter started", service=self.service_name)

        # Start cache cleanup task
        asyncio.create_task(self._cache_cleanup_loop())

        return True

    async def _stop(self) -> bool:
        """Stop the rate limiter."""
        TreeLogger.info("Rate Limiter stopped", service=self.service_name)
        self.cache.clear()
        return True

    async def _health_check(self) -> dict[str, Any]:
        """Perform health check on rate limiter."""
        return {
            "is_healthy": True,
            "has_database": self.database_service is not None,
            "cache_size": len(self.cache),
            "rate_limit": self.config.ai_rate_limit_per_hour,
        }

    async def _create_tables(self) -> None:
        """Create necessary database tables."""
        TreeLogger.debug("Creating AI rate limits table", service=self.service_name)

        await self.database_service.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_rate_limits (
                user_id TEXT PRIMARY KEY,
                last_mention TIMESTAMP,
                mention_count INTEGER DEFAULT 0,
                total_mentions INTEGER DEFAULT 0,
                first_mention TIMESTAMP
            )
        """
        )

        await self.database_service.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_rate_limits_last_mention
            ON ai_rate_limits(last_mention)
        """
        )

        TreeLogger.debug(
            "Rate limit tables created successfully", service=self.service_name
        )

    async def check_mention_rate_limit(
        self, user_id: int, username: str
    ) -> tuple[bool, timedelta | None, str]:
        """
        Check if user can make an AI request (alias for check_user).

        Args:
            user_id: Discord user ID
            username: Username (not used, for compatibility)

        Returns:
            Tuple of (is_limited, time_until_next, message)
        """
        allowed, time_until_next = await self.check_user(user_id)

        if allowed:
            return False, None, ""  # Not limited
        else:
            message = f"You can send another message in {time_until_next.seconds // 60} minutes."
            return True, time_until_next, message  # Is limited

    async def check_user(self, user_id: int) -> tuple[bool, timedelta | None]:
        """
        Check if user can make an AI request.

        Args:
            user_id: Discord user ID

        Returns:
            Tuple of (allowed, time_until_next) where time_until_next is None if allowed
        """
        # Developer bypass
        if user_id == self.config.developer_id:
            TreeLogger.debug(
                "Developer bypass for rate limit",
                {"user_id": user_id},
                service=self.service_name,
            )
            return True, None

        # Check cache first
        if user_id in self.cache:
            last_mention = self.cache[user_id]
            time_since = datetime.now() - last_mention

            if time_since < timedelta(hours=1):
                time_until_next = timedelta(hours=1) - time_since
                TreeLogger.debug(
                    "Rate limit hit (from cache)",
                    {
                        "user_id": user_id,
                        "time_since": str(time_since),
                        "time_until_next": str(time_until_next),
                    },
                    service=self.service_name,
                )
                return False, time_until_next

            TreeLogger.debug(
                "Cache entry expired, checking database",
                {"user_id": user_id, "time_since": str(time_since)},
                service=self.service_name,
            )

        # Check database
        user_data = await self.database_service.fetch_one(
            """
            SELECT last_mention, mention_count
            FROM ai_rate_limits
            WHERE user_id = ?
        """,
            (str(user_id),),
        )

        now = datetime.now()

        if not user_data:
            # First time user
            TreeLogger.debug(
                "First time user, allowing mention",
                {"user_id": user_id},
                service=self.service_name,
            )
            return True, None

        # Parse last mention time
        last_mention = datetime.fromisoformat(user_data["last_mention"])
        time_since = now - last_mention

        # Check if enough time has passed
        if time_since >= timedelta(hours=1):
            TreeLogger.debug(
                "Rate limit expired, allowing mention",
                {"user_id": user_id, "time_since": str(time_since)},
                service=self.service_name,
            )
            return True, None

        # Calculate time until next allowed mention
        time_until_next = timedelta(hours=1) - time_since

        # Update cache
        self.cache[user_id] = last_mention

        TreeLogger.debug(
            "Rate limit active",
            {
                "user_id": user_id,
                "time_since": str(time_since),
                "time_until_next": str(time_until_next),
            },
            service=self.service_name,
        )

        return False, time_until_next

    async def record_mention(self, user_id: int, username: str) -> None:
        """
        Record a successful AI mention for rate limiting.

        Args:
            user_id: Discord user ID
            username: Discord username for logging
        """
        now = datetime.now()

        TreeLogger.debug(
            "Recording AI mention",
            {"user_id": user_id, "username": username},
            service=self.service_name,
        )

        # Update cache
        self.cache[user_id] = now

        # Update database
        await self.database_service.execute(
            """
            INSERT INTO ai_rate_limits (user_id, last_mention, mention_count, total_mentions, first_mention)
            VALUES (?, ?, 1, 1, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                last_mention = ?,
                mention_count = CASE
                    WHEN (julianday(?) - julianday(last_mention)) * 24 >= 1
                    THEN 1
                    ELSE mention_count + 1
                END,
                total_mentions = total_mentions + 1
        """,
            (
                str(user_id),
                now.isoformat(),
                now.isoformat(),
                now.isoformat(),
                now.isoformat(),
            ),
        )

        TreeLogger.info(
            "AI mention recorded",
            {"user": username, "user_id": user_id, "timestamp": now.isoformat()},
            service=self.service_name,
        )

    async def get_user_stats(self, user_id: int) -> dict[str, Any]:
        """Get rate limit statistics for a user."""
        TreeLogger.debug(
            "Fetching user rate limit stats",
            {"user_id": user_id},
            service=self.service_name,
        )

        stats = await self.database_service.fetch_one(
            """
            SELECT last_mention, mention_count, total_mentions, first_mention
            FROM ai_rate_limits
            WHERE user_id = ?
        """,
            (str(user_id),),
        )

        if not stats:
            return {
                "has_used": False,
                "total_mentions": 0,
                "last_mention": None,
                "can_mention_next": datetime.now(),
            }

        last_mention = datetime.fromisoformat(stats["last_mention"])
        time_since = datetime.now() - last_mention

        can_mention_next = (
            last_mention + timedelta(hours=1)
            if time_since < timedelta(hours=1)
            else datetime.now()
        )

        return {
            "has_used": True,
            "total_mentions": stats["total_mentions"],
            "last_mention": last_mention,
            "first_mention": (
                datetime.fromisoformat(stats["first_mention"])
                if stats["first_mention"]
                else None
            ),
            "can_mention_next": can_mention_next,
            "recent_mentions": stats["mention_count"],
        }

    def format_cooldown_message(self, time_remaining: timedelta) -> str:
        """Format a friendly cooldown message."""
        total_seconds = int(time_remaining.total_seconds())

        TreeLogger.debug(
            "Formatting cooldown message",
            {"time_remaining": str(time_remaining), "total_seconds": total_seconds},
            service=self.service_name,
        )

        if total_seconds < 60:
            return (
                f"Please wait {total_seconds} seconds before sending another message."
            )

        minutes = total_seconds // 60
        seconds = total_seconds % 60

        if minutes == 1:
            if seconds == 0:
                return "Please wait 1 minute before sending another message."
            return f"Please wait 1 minute and {seconds} seconds before sending another message."

        if seconds == 0:
            return f"Please wait {minutes} minutes before sending another message."

        return f"Please wait {minutes} minutes and {seconds} seconds before sending another message."

    async def _cache_cleanup_loop(self) -> None:
        """Periodically clean up expired cache entries."""
        while self.state == "running":
            try:
                now = datetime.now()
                expired_users = []

                for user_id, last_mention in self.cache.items():
                    if now - last_mention > timedelta(hours=1, minutes=5):
                        expired_users.append(user_id)

                for user_id in expired_users:
                    del self.cache[user_id]

                if expired_users:
                    TreeLogger.debug(
                        f"Cleaned {len(expired_users)} expired cache entries",
                        service=self.service_name,
                    )

                # Run every 5 minutes
                await asyncio.sleep(300)

            except Exception as e:
                TreeLogger.error(
                    "Error in cache cleanup",
                    e,
                    {"error_type": type(e).__name__, "cache_size": len(self.cache)},
                    service=self.service_name,
                )
                await self.error_handler.handle_error(
                    e, {"operation": "cache_cleanup_loop"}
                )
                await asyncio.sleep(300)

    async def _cleanup(self) -> None:
        """Clean up rate limiter resources."""
        try:
            TreeLogger.debug(
                "Cleaning up rate limiter resources", service=self.service_name
            )

            # Clear cache
            if hasattr(self, "cache"):
                cache_size = len(self.cache)
                self.cache.clear()
                TreeLogger.debug(
                    f"Cleared {cache_size} cache entries", service=self.service_name
                )

            # Cancel cleanup task if running
            if hasattr(self, "_cleanup_task") and self._cleanup_task:
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass
                TreeLogger.debug("Cleanup task cancelled", service=self.service_name)

            TreeLogger.info("Rate limiter cleanup completed", service=self.service_name)

        except Exception as e:
            TreeLogger.error(
                "Error during rate limiter cleanup",
                e,
                {"error_type": type(e).__name__},
                service=self.service_name,
            )
            # Don't raise - cleanup should be best effort
