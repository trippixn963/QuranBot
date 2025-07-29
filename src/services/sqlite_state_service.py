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

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from ..core.structured_logger import StructuredLogger
from ..core.exceptions import DatabaseError
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
                {"db_path": str(self.db_service.db_manager.db_path)}
            )
            
    # ==========================================================================
    # PLAYBACK STATE METHODS (replacing load_playback_state/save_playback_state)
    # ==========================================================================
    
    async def load_playback_state(self) -> Dict[str, Any]:
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
            
            # Convert SQLite format to expected format
            return {
                "is_playing": bool(state.get("is_playing", False)),
                "is_paused": bool(state.get("is_paused", False)),
                "is_connected": False,  # This is runtime state, not persistent
                "current_reciter": state.get("reciter", "Saad Al Ghamdi"),
                "current_position": {
                    "surah_number": state.get("surah_number", 1),
                    "position_seconds": state.get("position_seconds", 0.0),
                    "total_duration": state.get("total_duration"),
                    "track_index": 0,
                    "timestamp": state.get("last_updated")
                },
                "mode": state.get("playback_mode", "normal"),
                "volume": state.get("volume", 1.0),
                "queue": [],  # Runtime state
                "voice_channel_id": None,  # Runtime state
                "guild_id": None,  # Runtime state
                "last_updated": state.get("last_updated")
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
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                "mode": "normal",
                "volume": 1.0,
                "queue": [],
                "voice_channel_id": None,
                "guild_id": None,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
    async def save_playback_state(self, state: Dict[str, Any]) -> bool:
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
            # Extract data for SQLite format
            current_position = state.get("current_position", {})
            
            updates = {
                "surah_number": current_position.get("surah_number", 1),
                "position_seconds": current_position.get("position_seconds", 0.0),
                "reciter": state.get("current_reciter", "Saad Al Ghamdi"),
                "volume": state.get("volume", 1.0),
                "is_playing": state.get("is_playing", False),
                "is_paused": state.get("is_paused", False),
                "playback_mode": state.get("mode", "normal"),
                "total_duration": current_position.get("total_duration")
            }
            
            success = await self.db_service.update_playback_state(**updates)
            
            if success:
                await self.logger.debug(
                    "Playback state saved to SQLite",
                    {"surah": updates["surah_number"], "position": updates["position_seconds"]}
                )
            
            return success
            
        except Exception as e:
            await self.logger.error("Failed to save playback state", {"error": str(e)})
            return False
            
    # ==========================================================================
    # BOT STATISTICS METHODS (replacing load_bot_stats/save_bot_stats)
    # ==========================================================================
    
    async def load_bot_stats(self) -> Dict[str, Any]:
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
            
            # Convert to expected format
            return {
                "total_runtime": stats.get("total_runtime_hours", 0.0) * 3600,  # Convert back to seconds
                "total_sessions": stats.get("total_sessions", 0),
                "surahs_completed": stats.get("total_completed_sessions", 0),
                "last_startup": stats.get("last_startup"),
                "last_shutdown": stats.get("last_shutdown"),
                "favorite_reciter": stats.get("favorite_reciter"),
                "metadata": {
                    "version": "2.2.0",
                    "last_updated": stats.get("updated_at"),
                    "save_type": "bot_stats"
                }
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
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "save_type": "bot_stats"
                }
            }
            
    async def save_bot_stats(self, stats: Dict[str, Any]) -> bool:
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
            # Convert seconds to hours for storage
            runtime_hours = stats.get("total_runtime", 0.0) / 3600.0
            
            updates = {
                "total_runtime_hours": runtime_hours,
                "total_sessions": stats.get("total_sessions", 0),
                "total_completed_sessions": stats.get("surahs_completed", 0),
                "last_startup": stats.get("last_startup"),
                "last_shutdown": stats.get("last_shutdown"),
                "favorite_reciter": stats.get("favorite_reciter")
            }
            
            success = await self.db_service.update_bot_statistics(**updates)
            
            if success:
                await self.logger.debug(
                    "Bot stats saved to SQLite",
                    {"sessions": updates["total_sessions"], "runtime_hours": runtime_hours}
                )
            
            return success
            
        except Exception as e:
            await self.logger.error("Failed to save bot stats", {"error": str(e)})
            return False
            
    # ==========================================================================
    # QUIZ STATE METHODS 
    # ==========================================================================
    
    async def load_quiz_config(self) -> Dict[str, Any]:
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
                    "enabled": config.get("enabled", True)
                },
                "metadata": {
                    "version": "2.0.0",
                    "last_updated": config.get("updated_at"),
                    "save_type": "quiz_state"
                }
            }
            
        except Exception as e:
            await self.logger.error("Failed to load quiz config", {"error": str(e)})
            return {
                "schedule_config": {
                    "send_interval_hours": 3.0,
                    "last_question_sent": None,
                    "enabled": True
                },
                "metadata": {
                    "version": "2.0.0",
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "save_type": "quiz_state"
                }
            }
            
    async def save_quiz_config(self, config: Dict[str, Any]) -> bool:
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
                "last_question_sent": schedule_config.get("last_question_sent")
            }
            
            return await self.db_service.update_quiz_config(**updates)
            
        except Exception as e:
            await self.logger.error("Failed to save quiz config", {"error": str(e)})
            return False
            
    async def load_quiz_stats(self) -> Dict[str, Any]:
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
            
            # Get user stats (limit to top 100 for performance)
            user_stats_list = await self.db_service.get_quiz_leaderboard(limit=100, order_by='points')
            
            # Convert user stats to dictionary format
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
                    "first_answer": user.get("first_answer")
                }
            
            return {
                "questions_sent": global_stats.get("questions_sent", 0),
                "total_attempts": global_stats.get("total_attempts", 0),
                "correct_answers": global_stats.get("correct_answers", 0),
                "user_stats": user_stats,
                "metadata": {
                    "version": "2.0.0",
                    "last_updated": global_stats.get("updated_at"),
                    "save_type": "quiz_stats"
                }
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
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "save_type": "quiz_stats"
                }
            }
            
    async def save_quiz_stats(self, stats: Dict[str, Any]) -> bool:
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
            # Update global stats
            global_updates = {
                "questions_sent": stats.get("questions_sent", 0),
                "total_attempts": stats.get("total_attempts", 0),
                "correct_answers": stats.get("correct_answers", 0),
                "unique_participants": len(stats.get("user_stats", {}))
            }
            
            await self.db_service.update_quiz_statistics(**global_updates)
            
            # Update user stats
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
    
    async def get_metadata_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve metadata from SQLite cache by key.
        
        Looks up cached metadata using the provided cache key and updates
        access statistics for cache management. Used for caching audio file
        metadata and other frequently accessed data.
        
        Args:
            cache_key: Unique identifier for the cached data
            
        Returns:
            Optional[Dict[str, Any]]: Cached metadata dictionary if found, None otherwise
            
        Raises:
            DatabaseError: If database query fails
        """
        return await self.db_service.get_metadata_cache(cache_key)
        
    async def set_metadata_cache(self, cache_key: str, **metadata) -> bool:
        """
        Store metadata in SQLite cache with specified key.
        
        Caches metadata for improved performance, typically used for audio file
        metadata, reciter information, and other frequently accessed data.
        
        Args:
            cache_key: Unique identifier for the cached data
            **metadata: Metadata fields to cache (file_path, reciter, duration, etc.)
            
        Returns:
            bool: True if cache operation completed successfully, False on error
            
        Raises:
            DatabaseError: If database insert operation fails
        """
        return await self.db_service.set_metadata_cache(cache_key, **metadata)
        
    async def clear_old_cache(self, days_old: int = 30) -> int:
        """
        Remove old metadata cache entries from SQLite database.
        
        Cleans up cache entries that haven't been accessed recently to maintain
        optimal database performance and storage efficiency.
        
        Args:
            days_old: Number of days after which unused cache entries are removed
            
        Returns:
            int: Number of cache entries removed (currently returns 0)
            
        Raises:
            DatabaseError: If database cleanup operation fails
        """
        return await self.db_service.clear_old_cache(days_old)
        
    # ==========================================================================
    # SYSTEM EVENT LOGGING
    # ==========================================================================
    
    async def log_system_event(
        self, 
        event_type: str, 
        event_data: Dict[str, Any] = None,
        severity: str = 'info'
    ) -> bool:
        """
        Log a system event to the SQLite database.
        
        Records system events for audit trails, debugging, and analytics.
        Events are stored with timestamps, severity levels, and optional data.
        
        Args:
            event_type: Type/category of the system event
            event_data: Optional dictionary containing event-specific data
            severity: Event severity level ('info', 'warning', 'error', etc.)
            
        Returns:
            bool: True if event logging completed successfully, False on error
            
        Raises:
            DatabaseError: If database insert operation fails
        """
        return await self.db_service.log_system_event(event_type, event_data, severity)
        
    # ==========================================================================
    # DATABASE MANAGEMENT
    # ==========================================================================
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """
        Retrieve comprehensive SQLite database statistics.
        
        Gathers database performance metrics, storage usage, and table statistics
        for monitoring and optimization purposes.
        
        Returns:
            Dict[str, Any]: Database statistics including size, record counts,
                           table information, and performance metrics
                           
        Raises:
            DatabaseError: If database statistics query fails
        """
        return await self.db_service.get_database_stats()
        
    async def backup_database(self, backup_path: Path) -> bool:
        """
        Create a backup of the SQLite database.
        
        Performs a complete database backup to the specified path for data
        recovery and archival purposes. Uses SQLite's built-in backup API
        for consistency and reliability.
        
        Args:
            backup_path: Path where the database backup should be created
            
        Returns:
            bool: True if backup completed successfully, False on error
            
        Raises:
            DatabaseError: If backup operation fails
        """
        return await self.db_service.backup_database(backup_path)
        
    async def verify_data_integrity(self) -> Dict[str, Any]:
        """
        Verify data integrity (replaces the JSON verification method).
        
        Returns:
            Dict with integrity check results
        """
        try:
            stats = await self.get_database_stats()
            
            # Check if we have the expected core records
            table_counts = stats.get('table_counts', {})
            
            integrity_report = {
                "database_healthy": True,
                "issues": [],
                "stats": stats
            }
            
            # Check for essential records
            if table_counts.get('playback_state', 0) == 0:
                integrity_report["issues"].append("Missing playback state record")
                integrity_report["database_healthy"] = False
                
            if table_counts.get('bot_statistics', 0) == 0:
                integrity_report["issues"].append("Missing bot statistics record")
                integrity_report["database_healthy"] = False
                
            if table_counts.get('quiz_config', 0) == 0:
                integrity_report["issues"].append("Missing quiz config record")
                integrity_report["database_healthy"] = False
                
            await self.logger.info(
                "Data integrity check completed",
                {
                    "healthy": integrity_report["database_healthy"],
                    "issues_count": len(integrity_report["issues"])
                }
            )
            
            return integrity_report
            
        except Exception as e:
            await self.logger.error("Data integrity check failed", {"error": str(e)})
            return {
                "database_healthy": False,
                "issues": [f"Integrity check failed: {e}"],
                "stats": {}
            } 