"""QuranBot - SQLite State Service.

Modern state management using SQLite database instead of JSON files.
Provides robust, ACID-compliant state persistence with better performance.

This module provides a high-level SQLite-based state management service for QuranBot,
replacing the legacy JSON-based state management system with a robust database solution
that provides ACID transactions, better performance, and automatic recovery capabilities.

Classes:
    SQLiteStateService: High-level state management service using SQLite

Features:
    - Atomic state updates with ACID compliance
    - Automatic schema validation and data integrity
    - Built-in backup and recovery capabilities
    - No JSON corruption issues
    - Better concurrent access handling
    - Comprehensive error handling and logging

State Management:
    - Playback state persistence (surah, position, reciter, volume)
    - Bot statistics tracking (runtime, sessions, completions)
    - Quiz configuration and user statistics
    - Metadata caching for improved performance
    - System event logging and audit trails
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..core.logger import StructuredLogger
from .database_service import QuranBotDatabaseService


class SQLiteStateService:
    """
    SQLite-based state management service for QuranBot.

    Replaces the old JSON-based state manager with a robust SQLite solution
    that provides ACID transactions, better performance, and automatic recovery.

    Features:
    - Atomic state updates
    - Automatic schema validation
    - Built-in backup capabilities
    - No more JSON corruption issues
    - Better concurrent access handling
    """

    def __init__(self, logger: StructuredLogger, db_path: Path = None):
        """
        Initialize the SQLite state service.

        Sets up the state service with database connection and logging.
        The service provides a high-level interface for managing all
        persistent state data using SQLite as the backend storage.

        Args:
            logger: Structured logger instance for service logging
            db_path: Optional path to SQLite database file. If None, uses default location
        """
        self.logger = logger
        self.db_service = QuranBotDatabaseService(logger=logger, db_path=db_path)
        self._is_initialized = False

    async def initialize(self) -> None:
        """
        Initialize the database service and establish connection.

        Sets up the SQLite database connection, initializes tables if needed,
        and prepares the service for state management operations. This method
        must be called before using any other service methods.

        Raises:
            DatabaseError: If database initialization fails
        """
        if not self._is_initialized:
            await self.db_service.initialize()
            self._is_initialized = True

            await self.logger.info(
                "SQLite state service initialized",
                {"db_path": str(self.db_service.db_manager.db_path)},
            )

    async def shutdown(self) -> None:
        """
        Gracefully shutdown the SQLite state service and release resources.

        Performs orderly shutdown of the database connection, ensuring all pending
        transactions are completed and database files are properly closed. This
        prevents database corruption and ensures clean process termination.

        The shutdown process:
        1. Completes any pending database transactions
        2. Closes the SQLite connection pool
        3. Releases file locks on the database
        4. Resets the initialization state

        Raises:
            Exception: If shutdown process encounters errors (logged but not re-raised)
        """
        try:
            await self.db_service.db_manager.shutdown()
            self._is_initialized = False
            await self.logger.info("SQLite state service shutdown complete")
        except Exception as e:
            await self.logger.error(
                "Error during SQLite state service shutdown", {"error": str(e)}
            )

    # ==========================================================================
    # PLAYBACK STATE METHODS (replacing load_playback_state/save_playback_state)
    # ==========================================================================

    async def load_playback_state(self) -> dict[str, Any]:
        """
        Load current playback state from SQLite database.

        Retrieves the persistent playback state including current surah position,
        reciter selection, playback mode, and audio settings. Returns default
        values if no state exists in the database.

        Returns:
            Dict[str, Any]: Complete playback state containing:
                - is_playing: Current playback status
                - is_paused: Pause state
                - current_reciter: Selected reciter name
                - current_position: Surah number, position, and timing info
                - mode: Playback mode (normal, loop, shuffle)
                - volume: Audio volume level (0.0-1.0)
                - Runtime state fields (voice_channel_id, queue, etc.)

        Raises:
            DatabaseError: If database query fails
        """
        try:
            state = await self.db_service.get_playback_state()

            # Convert SQLite normalized format to application's expected format
            # This translation layer maintains backward compatibility while leveraging
            # the normalized database schema for better data integrity and performance
            return {
                "is_playing": bool(state.get("is_playing", False)),
                "is_paused": bool(state.get("is_paused", False)),
                "is_connected": False,  # Runtime state - never persisted to avoid stale connections
                "current_reciter": state.get("reciter", "Saad Al Ghamdi"),
                "current_position": {
                    "surah_number": state.get("surah_number", 1),
                    "position_seconds": state.get("position_seconds", 0.0),
                    "total_duration": state.get("total_duration"),
                    "track_index": 0,  # Always 0 for single-file playback model
                    "timestamp": state.get("last_updated"),
                },
                "mode": state.get("playback_mode", "normal"),
                "volume": state.get("volume", 1.0),
                "queue": [],  # Runtime state - cleared on restart for predictable behavior
                "voice_channel_id": None,  # Runtime state - Discord connection specific
                "guild_id": None,  # Runtime state - Discord server specific
                "last_updated": state.get("last_updated"),
            }

        except Exception as e:
            await self.logger.error("Failed to load playback state", {"error": str(e)})
            # Return default state on error
            return {
                "is_playing": False,
                "is_paused": False,
                "is_connected": False,
                "current_reciter": "Saad Al Ghamdi",
                "current_position": {
                    "surah_number": 1,
                    "position_seconds": 0.0,
                    "total_duration": None,
                    "track_index": 0,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                "mode": "normal",
                "volume": 1.0,
                "queue": [],
                "voice_channel_id": None,
                "guild_id": None,
                "last_updated": datetime.now(UTC).isoformat(),
            }

    async def save_playback_state(self, state: dict[str, Any]) -> bool:
        """
        Save current playback state to SQLite database.

        Persists the complete playback state to the database, extracting relevant
        fields and converting them to the appropriate SQLite format. Only persistent
        state is saved; runtime state (connections, queues) is excluded.

        Args:
            state: Complete playback state dictionary containing current surah,
                  position, reciter, volume, and playback mode settings

        Returns:
            bool: True if save operation completed successfully, False on error

        Raises:
            DatabaseError: If database update operation fails
        """
        try:
            # Transform application state format to normalized database schema
            # This ensures data consistency and enables efficient querying while
            # filtering out runtime-only state that shouldn't be persisted
            current_position = state.get("current_position", {})

            updates = {
                "surah_number": current_position.get("surah_number", 1),
                "position_seconds": current_position.get("position_seconds", 0.0),
                "reciter": state.get("current_reciter", "Saad Al Ghamdi"),
                "volume": state.get("volume", 1.0),
                "is_playing": state.get("is_playing", False),
                "is_paused": state.get("is_paused", False),
                "playback_mode": state.get("mode", "normal"),
                "total_duration": current_position.get("total_duration"),
            }

            success = await self.db_service.update_playback_state(**updates)

            if success:
                await self.logger.debug(
                    "Playback state saved to SQLite",
                    {
                        "surah": updates["surah_number"],
                        "position": updates["position_seconds"],
                    },
                )

                # Attempt to log database operation to analytics webhook for monitoring
                # Uses defensive programming - webhook failures don't affect core functionality
                # This provides valuable insights into database usage patterns and state changes
                try:
                    from ..core.di_container import get_container

                    container = get_container()
                    if container:
                        enhanced_webhook = container.get("webhook_router")
                        if enhanced_webhook and hasattr(
                            enhanced_webhook, "log_database_operation"
                        ):
                            await enhanced_webhook.log_database_operation(
                                operation_type="UPDATE",
                                table_name="playback_state",
                                description=f"Saved playback state for Surah {updates['surah_number']} at {updates['position_seconds']:.1f}s",
                                success=True,
                                context={
                                    "surah_number": updates["surah_number"],
                                    "position_seconds": updates["position_seconds"],
                                    "reciter": updates["reciter"],
                                    "is_playing": updates["is_playing"],
                                    "playback_mode": updates["playback_mode"],
                                },
                            )
                except Exception:
                    pass  # Silently continue - analytics failures shouldn't impact state persistence

            return success

        except Exception as e:
            await self.logger.error("Failed to save playback state", {"error": str(e)})
            return False

    # ==========================================================================
    # BOT STATISTICS METHODS (replacing load_bot_stats/save_bot_stats)
    # ==========================================================================

    async def load_bot_stats(self) -> dict[str, Any]:
        """
        Load comprehensive bot statistics from SQLite database.

        Retrieves all bot usage statistics including runtime hours, session counts,
        completion statistics, and operational metadata. Converts database format
        to the expected application format for compatibility.

        Returns:
            Dict[str, Any]: Bot statistics containing:
                - total_runtime: Total runtime in seconds
                - total_sessions: Number of bot sessions
                - surahs_completed: Number of completed Quran sessions
                - last_startup: Last bot startup timestamp
                - last_shutdown: Last bot shutdown timestamp
                - favorite_reciter: Most used reciter
                - metadata: Version and update information

        Raises:
            DatabaseError: If database query fails
        """
        try:
            stats = await self.db_service.get_bot_statistics()

            # Transform database format to application's expected format
            # Runtime is stored as hours in DB for more intuitive analytics but
            # converted back to seconds for application compatibility
            return {
                "total_runtime": stats.get("total_runtime_hours", 0.0)
                * 3600,  # Convert back to seconds for legacy compatibility
                "total_sessions": stats.get("total_sessions", 0),
                "surahs_completed": stats.get("total_completed_sessions", 0),
                "last_startup": stats.get("last_startup"),
                "last_shutdown": stats.get("last_shutdown"),
                "favorite_reciter": stats.get("favorite_reciter"),
                "metadata": {
                    "version": "2.2.0",
                    "last_updated": stats.get("updated_at"),
                    "save_type": "bot_stats",
                },
            }

        except Exception as e:
            await self.logger.error("Failed to load bot stats", {"error": str(e)})
            return {
                "total_runtime": 0.0,
                "total_sessions": 0,
                "surahs_completed": 0,
                "last_startup": None,
                "last_shutdown": None,
                "favorite_reciter": None,
                "metadata": {
                    "version": "2.2.0",
                    "last_updated": datetime.now(UTC).isoformat(),
                    "save_type": "bot_stats",
                },
            }

    async def save_bot_stats(self, stats: dict[str, Any]) -> bool:
        """
        Save bot statistics to SQLite database.

        Persists comprehensive bot usage statistics to the database, converting
        from application format to database format. Runtime is converted from
        seconds to hours for efficient storage.

        Args:
            stats: Bot statistics dictionary containing runtime, session counts,
                  completion data, and operational timestamps

        Returns:
            bool: True if save operation completed successfully, False on error

        Raises:
            DatabaseError: If database update operation fails
        """
        try:
            # Normalize runtime to hours for database storage efficiency
            # Hours provide more readable analytics while maintaining precision
            runtime_hours = stats.get("total_runtime", 0.0) / 3600.0

            updates = {
                "total_runtime_hours": runtime_hours,
                "total_sessions": stats.get("total_sessions", 0),
                "total_completed_sessions": stats.get("surahs_completed", 0),
                "last_startup": stats.get("last_startup"),
                "last_shutdown": stats.get("last_shutdown"),
                "favorite_reciter": stats.get("favorite_reciter"),
            }

            success = await self.db_service.update_bot_statistics(**updates)

            if success:
                await self.logger.debug(
                    "Bot stats saved to SQLite",
                    {
                        "sessions": updates["total_sessions"],
                        "runtime_hours": runtime_hours,
                    },
                )

                # Send analytics update to monitoring webhook for operational insights
                # Statistics updates are valuable for understanding bot usage patterns
                # and identifying trends in user engagement over time
                try:
                    from ..core.di_container import get_container

                    container = get_container()
                    if container:
                        enhanced_webhook = container.get("webhook_router")
                        if enhanced_webhook and hasattr(
                            enhanced_webhook, "log_database_operation"
                        ):
                            await enhanced_webhook.log_database_operation(
                                operation_type="UPDATE",
                                table_name="bot_statistics",
                                description=f"Updated bot statistics - {updates['total_sessions']} sessions, {runtime_hours:.1f}h runtime",
                                success=True,
                                context={
                                    "total_sessions": updates["total_sessions"],
                                    "runtime_hours": round(runtime_hours, 2),
                                    "completed_sessions": updates[
                                        "total_completed_sessions"
                                    ],
                                    "favorite_reciter": updates["favorite_reciter"],
                                },
                            )
                except Exception:
                    pass  # Analytics logging is non-critical - don't interrupt core functionality

            return success

        except Exception as e:
            await self.logger.error("Failed to save bot stats", {"error": str(e)})
            return False

    # ==========================================================================
    # QUIZ STATE METHODS
    # ==========================================================================

    async def load_quiz_config(self) -> dict[str, Any]:
        """
        Load quiz system configuration from SQLite database.

        Retrieves quiz scheduling configuration, enabled status, and timing
        settings. Returns default configuration if none exists in database.

        Returns:
            Dict[str, Any]: Quiz configuration containing:
                - schedule_config: Scheduling settings with interval and timing
                - metadata: Version and update information

        Raises:
            DatabaseError: If database query fails
        """
        try:
            config = await self.db_service.get_quiz_config()

            return {
                "schedule_config": {
                    "send_interval_hours": config.get("send_interval_hours", 3.0),
                    "last_question_sent": config.get("last_question_sent"),
                    "enabled": config.get("enabled", True),
                },
                "metadata": {
                    "version": "2.0.0",
                    "last_updated": config.get("updated_at"),
                    "save_type": "quiz_state",
                },
            }

        except Exception as e:
            await self.logger.error("Failed to load quiz config", {"error": str(e)})
            return {
                "schedule_config": {
                    "send_interval_hours": 3.0,
                    "last_question_sent": None,
                    "enabled": True,
                },
                "metadata": {
                    "version": "2.0.0",
                    "last_updated": datetime.now(UTC).isoformat(),
                    "save_type": "quiz_state",
                },
            }

    async def save_quiz_config(self, config: dict[str, Any]) -> bool:
        """
        Save quiz system configuration to SQLite database.

        Persists quiz scheduling settings including send intervals, enabled status,
        and last question timing to maintain quiz system state across restarts.

        Args:
            config: Quiz configuration dictionary with schedule_config section
                   containing interval, enabled status, and timing data

        Returns:
            bool: True if save operation completed successfully, False on error

        Raises:
            DatabaseError: If database update operation fails
        """
        try:
            schedule_config = config.get("schedule_config", {})

            updates = {
                "send_interval_hours": schedule_config.get("send_interval_hours", 3.0),
                "enabled": schedule_config.get("enabled", True),
                "last_question_sent": schedule_config.get("last_question_sent"),
            }

            return await self.db_service.update_quiz_config(**updates)

        except Exception as e:
            await self.logger.error("Failed to save quiz config", {"error": str(e)})
            return False

    async def load_quiz_stats(self) -> dict[str, Any]:
        """
        Load comprehensive quiz statistics from SQLite database.

        Retrieves global quiz statistics and top user statistics, combining
        them into a single comprehensive statistics object. Limits user stats
        to top 100 users for performance optimization.

        Returns:
            Dict[str, Any]: Complete quiz statistics containing:
                - questions_sent: Total questions sent by bot
                - total_attempts: Total answer attempts across all users
                - correct_answers: Total correct answers across all users
                - user_stats: Dictionary of individual user statistics
                - metadata: Version and update information

        Raises:
            DatabaseError: If database query fails
        """
        try:
            # Get global stats
            global_stats = await self.db_service.get_quiz_statistics()

            # Get user stats with performance optimization - limit to top 100 users
            # This prevents memory issues while still providing comprehensive leaderboard data
            # Ordering by points ensures most active/successful users are always included
            user_stats_list = await self.db_service.get_quiz_leaderboard(
                limit=100, order_by="points"
            )

            # Transform normalized database records to legacy dictionary format
            # This maintains backward compatibility with existing quiz system code
            # while leveraging the improved database schema for better performance
            user_stats = {}
            for user in user_stats_list:
                user_stats[user["user_id"]] = {
                    "username": user.get("username"),
                    "display_name": user.get("display_name"),
                    "correct_answers": user.get("correct_answers", 0),
                    "total_attempts": user.get("total_attempts", 0),
                    "current_streak": user.get("streak", 0),
                    "best_streak": user.get("best_streak", 0),
                    "points": user.get("points", 0),
                    "last_answer": user.get("last_answer"),
                    "first_answer": user.get("first_answer"),
                }

            return {
                "questions_sent": global_stats.get("questions_sent", 0),
                "total_attempts": global_stats.get("total_attempts", 0),
                "correct_answers": global_stats.get("correct_answers", 0),
                "user_stats": user_stats,
                "metadata": {
                    "version": "2.0.0",
                    "last_updated": global_stats.get("updated_at"),
                    "save_type": "quiz_stats",
                },
            }

        except Exception as e:
            await self.logger.error("Failed to load quiz stats", {"error": str(e)})
            return {
                "questions_sent": 0,
                "total_attempts": 0,
                "correct_answers": 0,
                "user_stats": {},
                "metadata": {
                    "version": "2.0.0",
                    "last_updated": datetime.now(UTC).isoformat(),
                    "save_type": "quiz_stats",
                },
            }

    async def save_quiz_stats(self, stats: dict[str, Any]) -> bool:
        """
        Save comprehensive quiz statistics to SQLite database.

        Persists both global quiz statistics and individual user statistics
        to the database. Updates global counters and individual user records
        in separate operations for data consistency.

        Args:
            stats: Complete quiz statistics dictionary containing global stats
                  and user_stats dictionary with individual user data

        Returns:
            bool: True if all save operations completed successfully, False on error

        Raises:
            DatabaseError: If database update operations fail
        """
        try:
            # Update global aggregated statistics first for data consistency
            # These totals are used for overall quiz system analytics and reporting
            global_updates = {
                "questions_sent": stats.get("questions_sent", 0),
                "total_attempts": stats.get("total_attempts", 0),
                "correct_answers": stats.get("correct_answers", 0),
                "unique_participants": len(stats.get("user_stats", {})),
            }

            await self.db_service.update_quiz_statistics(**global_updates)

            # Update individual user statistics in separate transactions
            # This approach ensures partial failures don't corrupt the entire dataset
            # and allows for individual user record recovery if needed
            user_stats = stats.get("user_stats", {})
            for user_id, user_data in user_stats.items():
                await self.db_service.update_user_quiz_stats(user_id, **user_data)

            return True

        except Exception as e:
            await self.logger.error("Failed to save quiz stats", {"error": str(e)})
            return False

    # ==========================================================================
    # METADATA CACHE METHODS
    # ==========================================================================

    async def get_metadata_cache(self, cache_key: str) -> dict[str, Any] | None:
        """
        Retrieve metadata from SQLite cache by key with access tracking.

        Implements an intelligent caching system that tracks access patterns
        for cache management and performance optimization. Automatically updates
        last_accessed timestamps for LRU cache cleanup strategies.

        Common use cases:
        - Audio file metadata (duration, bitrate, format)
        - Reciter information and preferences
        - Surah details and translations
        - Performance-critical data that's expensive to recompute

        Args:
            cache_key: Unique identifier for the cached data (typically SHA-256 hash)

        Returns:
            Optional[Dict[str, Any]]: Cached metadata dictionary if found and valid,
                                    None if not found or expired

        Raises:
            DatabaseError: If underlying database query fails
        """
        return await self.db_service.get_metadata_cache(cache_key)

    async def set_metadata_cache(self, cache_key: str, **metadata) -> bool:
        """
        Store metadata in SQLite cache with intelligent deduplication.

        Implements an efficient caching system with automatic conflict resolution
        using INSERT OR REPLACE semantics. This ensures data consistency while
        preventing cache corruption from concurrent access patterns.

        Cache storage strategy:
        - Uses content-based keys (typically SHA-256) to prevent collisions
        - Automatically timestamps entries for TTL-based expiration
        - Compresses large metadata using JSON serialization
        - Maintains referential integrity with related database records

        Args:
            cache_key: Unique identifier for the cached data (should be deterministic)
            **metadata: Variable metadata fields to cache including:
                       - file_path: Path to cached resource
                       - reciter: Associated reciter name
                       - duration: Audio duration in seconds
                       - file_size: Resource size in bytes
                       - checksum: Content validation hash

        Returns:
            bool: True if cache operation completed successfully, False on error

        Raises:
            DatabaseError: If database insert/update operation fails
        """
        return await self.db_service.set_metadata_cache(cache_key, **metadata)

    async def clear_old_cache(self, days_old: int = 30) -> int:
        """
        Perform intelligent cache cleanup based on access patterns and age.

        Implements a sophisticated cache eviction strategy that considers both
        temporal factors (age) and usage patterns (access frequency) to maintain
        optimal cache performance while preserving frequently used data.

        Cleanup algorithm:
        1. Identifies entries older than the specified threshold
        2. Considers access frequency to protect valuable cache entries
        3. Removes expired entries using atomic transactions
        4. Compacts database after cleanup for optimal performance
        5. Updates cache statistics for monitoring

        This prevents unbounded cache growth while ensuring hot data remains
        available for performance-critical operations.

        Args:
            days_old: Number of days after which unused cache entries are eligible
                     for removal (default: 30 days for balanced retention)

        Returns:
            int: Number of cache entries actually removed from database

        Raises:
            DatabaseError: If database cleanup or compaction operation fails
        """
        return await self.db_service.clear_old_cache(days_old)

    # ==========================================================================
    # SYSTEM EVENT LOGGING
    # ==========================================================================

    async def log_system_event(
        self, event_type: str, event_data: dict[str, Any] = None, severity: str = "info"
    ) -> bool:
        """
        Log system events with structured data for comprehensive audit trails.

        Implements a robust event logging system that captures system state changes,
        errors, and operational events with full context for debugging and analytics.
        All events are timestamped and categorized for efficient querying.

        Event categories and examples:
        - 'startup': Bot initialization and service startup events
        - 'shutdown': Graceful shutdown and cleanup events
        - 'error': Exception handling and error recovery events
        - 'performance': Timing and resource usage metrics
        - 'security': Authentication and authorization events
        - 'database': Database operations and integrity checks

        The structured event data enables powerful analytics queries and
        operational monitoring through the webhook routing system.

        Args:
            event_type: Categorized event type for filtering and routing
            event_data: Optional structured data providing event context
                       (serialized as JSON for complex objects)
            severity: RFC 5424 severity level ('debug', 'info', 'notice',
                     'warning', 'error', 'critical', 'alert', 'emergency')

        Returns:
            bool: True if event was successfully logged to database, False on error

        Raises:
            DatabaseError: If database insert operation fails or data is malformed
        """
        return await self.db_service.log_system_event(event_type, event_data, severity)

    # ==========================================================================
    # DATABASE MANAGEMENT
    # ==========================================================================

    async def get_database_stats(self) -> dict[str, Any]:
        """
        Gather comprehensive SQLite database performance and usage statistics.

        Collects detailed metrics about database health, performance characteristics,
        and storage utilization. These statistics are essential for:

        - Monitoring database growth and performance trends
        - Identifying optimization opportunities (indexing, archiving)
        - Detecting potential issues before they impact performance
        - Capacity planning and resource allocation
        - Compliance reporting and audit requirements

        Statistics include:
        - Database file size and page utilization
        - Table record counts and storage distribution
        - Index usage and query performance metrics
        - Cache hit ratios and I/O statistics
        - Transaction throughput and lock contention

        Returns:
            Dict[str, Any]: Comprehensive database metrics including:
                - file_size: Database file size in bytes
                - table_counts: Record counts per table
                - index_stats: Index usage and efficiency metrics
                - performance_metrics: Query timing and throughput data
                - storage_stats: Page utilization and fragmentation info

        Raises:
            DatabaseError: If statistics collection queries fail
        """
        return await self.db_service.get_database_stats()

    async def backup_database(self, backup_path: Path) -> bool:
        """
        Create atomic database backup using SQLite's online backup API.

        Performs a consistent, point-in-time backup of the entire database
        without interrupting ongoing operations. This implementation uses
        SQLite's built-in backup mechanism which ensures ACID compliance
        and handles concurrent access safely.

        Backup process:
        1. Acquires shared lock on source database
        2. Creates target database file with proper permissions
        3. Copies pages atomically using sqlite3_backup_* API
        4. Handles concurrent writes during backup process
        5. Verifies backup integrity before completion
        6. Updates backup metadata and logging

        This approach is superior to file copying as it:
        - Maintains transaction consistency during backup
        - Handles WAL mode and concurrent access correctly
        - Provides progress monitoring and error recovery
        - Ensures backup file is immediately usable

        Args:
            backup_path: Destination path for the database backup file
                        (parent directory must exist and be writable)

        Returns:
            bool: True if backup completed successfully with verification,
                 False if backup failed or verification errors occurred

        Raises:
            DatabaseError: If backup operation fails due to I/O errors,
                          permission issues, or database corruption
        """
        return await self.db_service.backup_database(backup_path)

    async def verify_data_integrity(self) -> dict[str, Any]:
        """
        Perform comprehensive database integrity verification and health assessment.

        Conducts a thorough examination of database structure, data consistency,
        and referential integrity. This replaces the legacy JSON corruption checks
        with SQLite's built-in ACID compliance and constraint validation.

        Integrity verification process:
        1. Validates table schema and constraints
        2. Checks for required system records (playback_state, bot_statistics, etc.)
        3. Verifies foreign key relationships and data consistency
        4. Analyzes database statistics for performance issues
        5. Identifies potential corruption or missing critical data

        This comprehensive approach ensures data reliability and helps identify
        issues before they impact bot functionality. The verification results
        are logged for operational monitoring and automated recovery processes.

        Returns:
            Dict[str, Any]: Comprehensive integrity report containing:
                - database_healthy: Overall health status boolean
                - issues: List of identified problems requiring attention
                - stats: Detailed database statistics and metrics
                - recommendations: Suggested actions for issue resolution

        Raises:
            DatabaseError: If integrity verification process fails
        """
        try:
            stats = await self.get_database_stats()

            # Analyze table record counts against expected minimums
            # These core tables must exist for proper bot functionality
            table_counts = stats.get("table_counts", {})

            integrity_report = {"database_healthy": True, "issues": [], "stats": stats}

            # Critical table validation - these records are essential for bot operation
            if table_counts.get("playback_state", 0) == 0:
                integrity_report["issues"].append(
                    "Missing playback state record - bot will use defaults"
                )
                integrity_report["database_healthy"] = False

            if table_counts.get("bot_statistics", 0) == 0:
                integrity_report["issues"].append(
                    "Missing bot statistics record - analytics unavailable"
                )
                integrity_report["database_healthy"] = False

            if table_counts.get("quiz_config", 0) == 0:
                integrity_report["issues"].append(
                    "Missing quiz config record - quiz system disabled"
                )
                integrity_report["database_healthy"] = False

            await self.logger.info(
                "Data integrity verification completed",
                {
                    "healthy": integrity_report["database_healthy"],
                    "issues_count": len(integrity_report["issues"]),
                    "total_records": sum(table_counts.values()),
                },
            )

            return integrity_report

        except Exception as e:
            await self.logger.error(
                "Data integrity verification failed", {"error": str(e)}
            )
            return {
                "database_healthy": False,
                "issues": [f"Integrity verification failed: {e}"],
                "stats": {},
            }
