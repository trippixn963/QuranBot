# =============================================================================
# QuranBot - SQLite State Service
# =============================================================================
# Modern state management using SQLite database instead of JSON files
# Provides robust, ACID-compliant state persistence with better performance
# =============================================================================

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
        
        Args:
            logger: Structured logger instance
            db_path: Path to SQLite database file
        """
        self.logger = logger
        self.db_service = QuranBotDatabaseService(logger=logger, db_path=db_path)
        self._is_initialized = False
        
    async def initialize(self) -> None:
        """Initialize the database service"""
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
        Load playback state from SQLite database.
        
        Returns:
            Dict containing playback state data
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
        Save playback state to SQLite database.
        
        Args:
            state: Playback state dictionary
            
        Returns:
            True if save successful
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
        Load bot statistics from SQLite database.
        
        Returns:
            Dict containing bot statistics
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
        
        Args:
            stats: Bot statistics dictionary
            
        Returns:
            True if save successful
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
        """Load quiz configuration from SQLite"""
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
        """Save quiz configuration to SQLite"""
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
        """Load quiz statistics from SQLite"""
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
        """Save quiz statistics to SQLite"""
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
        """Get metadata from cache"""
        return await self.db_service.get_metadata_cache(cache_key)
        
    async def set_metadata_cache(self, cache_key: str, **metadata) -> bool:
        """Set metadata in cache"""
        return await self.db_service.set_metadata_cache(cache_key, **metadata)
        
    async def clear_old_cache(self, days_old: int = 30) -> int:
        """Clear old cache entries"""
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
        """Log a system event"""
        return await self.db_service.log_system_event(event_type, event_data, severity)
        
    # ==========================================================================
    # DATABASE MANAGEMENT
    # ==========================================================================
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        return await self.db_service.get_database_stats()
        
    async def backup_database(self, backup_path: Path) -> bool:
        """Create database backup"""
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