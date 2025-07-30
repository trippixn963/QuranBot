# =============================================================================
# QuranBot - Database Service
# =============================================================================
# High-level database service providing QuranBot-specific data operations
# built on top of the core DatabaseManager for safe, robust data access.
# =============================================================================

"""
This service provides comprehensive database operations for:
- Playback state management with SQLite persistence
- Quiz configuration and user statistics tracking
- Bot analytics and performance metrics
- Metadata caching for improved performance
- System event logging and audit trails
- Database maintenance and optimization

Classes:
    QuranBotDatabaseService: High-level database service with QuranBot-specific operations
    
Features:
    - Async/await support for all database operations
    - Comprehensive error handling with logging
    - Webhook integration for critical database events
    - Automatic data validation and sanitization
    - Built-in backup and maintenance capabilities
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.database import DatabaseManager
from ..core.logger import StructuredLogger
from ..core.exceptions import DatabaseError



class QuranBotDatabaseService:
    """
    High-level database service for QuranBot.
    
    Provides QuranBot-specific database operations while abstracting
    the underlying SQLite complexity. All methods are async and include
    proper error handling and logging.
    
    Features:
    - Playback state management
    - Quiz configuration and statistics
    - User statistics tracking
    - Metadata caching
    - Bot statistics and analytics
    """

    def __init__(self, logger: StructuredLogger, db_path: Path = None):
        """
        Initialize the database service.
        
        Args:
            logger: Structured logger instance
            db_path: Path to SQLite database file
        """
        self.logger = logger
        self.db_manager = DatabaseManager(logger=logger, db_path=db_path)
        self._is_initialized = False
        
    async def initialize(self) -> None:
        """Initialize the database service"""
        if not self._is_initialized:
            await self.db_manager.initialize()
            self._is_initialized = True
            
            await self.logger.info(
                "Database service initialized",
                {"db_path": str(self.db_manager.db_path)}
            )
            

            
    # ==========================================================================
    # PLAYBACK STATE OPERATIONS
    # ==========================================================================
    
    async def get_playback_state(self) -> Dict[str, Any]:
        """Get current playback state from database.
        
        Retrieves the persistent playback state including current surah,
        position, reciter, volume, and playback mode settings.
        
        Returns:
            Dict[str, Any]: Playback state data or default values if none exists
            
        Raises:
            DatabaseError: If database query fails
        """
        try:
            result = await self.db_manager.execute_query(
                "SELECT * FROM playback_state WHERE id = 1",
                fetch_one=True
            )
            
            if result:
                return dict(result)
            else:
                # Return default state if none exists
                return {
                    "surah_number": 1,
                    "position_seconds": 0.0,
                    "reciter": "Saad Al Ghamdi",
                    "volume": 1.0,
                    "is_playing": False,
                    "is_paused": False,
                    "loop_enabled": False,
                    "shuffle_enabled": False,
                    "playback_mode": "normal",
                    "total_duration": 0.0
                }
                
        except Exception as e:
            await self.logger.error("Failed to get playback state", {"error": str(e)})
            raise DatabaseError(f"Playback state retrieval failed: {e}")
            
    async def update_playback_state(self, **kwargs) -> bool:
        """
        Update playback state fields.
        
        Args:
            **kwargs: Fields to update (surah_number, position_seconds, etc.)
            
        Returns:
            True if update successful
        """
        try:
            # Build dynamic update query
            update_fields = []
            values = []
            
            valid_fields = {
                'surah_number', 'position_seconds', 'reciter', 'volume',
                'is_playing', 'is_paused', 'loop_enabled', 'shuffle_enabled',
                'playback_mode', 'total_duration'
            }
            
            for field, value in kwargs.items():
                if field in valid_fields:
                    update_fields.append(f"{field} = ?")
                    values.append(value)
                    
            if not update_fields:
                return True  # Nothing to update
                
            # Add timestamp
            update_fields.append("last_updated = ?")
            values.append(datetime.now(timezone.utc).isoformat())
            values.append(1)  # WHERE id = 1
            
            query = f"""
                UPDATE playback_state 
                SET {', '.join(update_fields)}
                WHERE id = ?
            """
            
            await self.db_manager.execute_query(query, tuple(values))
            
            await self.logger.debug(
                "Playback state updated",
                {"updated_fields": list(kwargs.keys())}
            )
            

            
            return True
            
        except Exception as e:
            await self.logger.error(
                "Failed to update playback state",
                {"error": str(e), "fields": list(kwargs.keys())}
            )
            

                    
            return False
            
    # ==========================================================================
    # BOT STATISTICS OPERATIONS
    # ==========================================================================
    
    async def get_bot_statistics(self) -> Dict[str, Any]:
        """Get bot statistics"""
        try:
            result = await self.db_manager.execute_query(
                "SELECT * FROM bot_statistics WHERE id = 1",
                fetch_one=True
            )
            
            return dict(result) if result else {}
            
        except Exception as e:
            await self.logger.error("Failed to get bot statistics", {"error": str(e)})
            raise DatabaseError(f"Bot statistics retrieval failed: {e}")
            
    async def update_bot_statistics(self, **kwargs) -> bool:
        """Update bot statistics"""
        try:
            # Build dynamic update query
            update_fields = []
            values = []
            
            valid_fields = {
                'total_runtime_hours', 'total_sessions', 'total_completed_sessions',
                'last_startup', 'last_shutdown', 'favorite_reciter'
            }
            
            for field, value in kwargs.items():
                if field in valid_fields:
                    update_fields.append(f"{field} = ?")
                    values.append(value)
                    
            if not update_fields:
                return True
                
            # Add timestamp
            update_fields.append("updated_at = ?")
            values.append(datetime.now(timezone.utc).isoformat())
            values.append(1)  # WHERE id = 1
            
            query = f"""
                UPDATE bot_statistics 
                SET {', '.join(update_fields)}
                WHERE id = ?
            """
            
            await self.db_manager.execute_query(query, tuple(values))
            return True
            
        except Exception as e:
            await self.logger.error("Failed to update bot statistics", {"error": str(e)})
            return False
            
    # ==========================================================================
    # QUIZ OPERATIONS
    # ==========================================================================
    
    async def get_quiz_config(self) -> Dict[str, Any]:
        """Get quiz configuration"""
        try:
            result = await self.db_manager.execute_query(
                "SELECT * FROM quiz_config WHERE id = 1",
                fetch_one=True
            )
            
            return dict(result) if result else {}
            
        except Exception as e:
            await self.logger.error("Failed to get quiz config", {"error": str(e)})
            raise DatabaseError(f"Quiz config retrieval failed: {e}")
            
    async def update_quiz_config(self, **kwargs) -> bool:
        """Update quiz configuration"""
        try:
            update_fields = []
            values = []
            
            valid_fields = {
                'send_interval_hours', 'enabled', 'channel_id', 'last_question_sent'
            }
            
            for field, value in kwargs.items():
                if field in valid_fields:
                    update_fields.append(f"{field} = ?")
                    values.append(value)
                    
            if not update_fields:
                return True
                
            update_fields.append("updated_at = ?")
            values.append(datetime.now(timezone.utc).isoformat())
            values.append(1)
            
            query = f"""
                UPDATE quiz_config 
                SET {', '.join(update_fields)}
                WHERE id = ?
            """
            
            await self.db_manager.execute_query(query, tuple(values))
            return True
            
        except Exception as e:
            await self.logger.error("Failed to update quiz config", {"error": str(e)})
            return False
            
    async def get_quiz_statistics(self) -> Dict[str, Any]:
        """Get global quiz statistics"""
        try:
            result = await self.db_manager.execute_query(
                "SELECT * FROM quiz_statistics WHERE id = 1",
                fetch_one=True
            )
            
            return dict(result) if result else {}
            
        except Exception as e:
            await self.logger.error("Failed to get quiz statistics", {"error": str(e)})
            raise DatabaseError(f"Quiz statistics retrieval failed: {e}")
            
    async def update_quiz_statistics(self, **kwargs) -> bool:
        """Update global quiz statistics"""
        try:
            update_fields = []
            values = []
            
            valid_fields = {
                'questions_sent', 'total_attempts', 'correct_answers', 
                'unique_participants', 'last_reset'
            }
            
            for field, value in kwargs.items():
                if field in valid_fields:
                    update_fields.append(f"{field} = ?")
                    values.append(value)
                    
            if not update_fields:
                return True
                
            update_fields.append("updated_at = ?")
            values.append(datetime.now(timezone.utc).isoformat())
            values.append(1)
            
            query = f"""
                UPDATE quiz_statistics 
                SET {', '.join(update_fields)}
                WHERE id = ?
            """
            
            await self.db_manager.execute_query(query, tuple(values))
            return True
            
        except Exception as e:
            await self.logger.error("Failed to update quiz statistics", {"error": str(e)})
            return False
            
    # ==========================================================================
    # USER QUIZ STATISTICS
    # ==========================================================================
    
    async def get_user_quiz_stats(self, user_id: str) -> Dict[str, Any]:
        """Get quiz statistics for a specific user"""
        try:
            result = await self.db_manager.execute_query(
                "SELECT * FROM user_quiz_stats WHERE user_id = ?",
                (user_id,),
                fetch_one=True
            )
            
            return dict(result) if result else {}
            
        except Exception as e:
            await self.logger.error("Failed to get user quiz stats", {"error": str(e), "user_id": user_id})
            raise DatabaseError(f"User quiz stats retrieval failed: {e}")
            
    async def update_user_quiz_stats(self, user_id: str, **kwargs) -> bool:
        """Update or create user quiz statistics"""
        try:
            # Check if user exists
            existing = await self.get_user_quiz_stats(user_id)
            
            if existing:
                # Update existing user
                update_fields = []
                values = []
                
                valid_fields = {
                    'username', 'display_name', 'correct_answers', 'total_attempts',
                    'streak', 'best_streak', 'points', 'last_answer', 'first_answer'
                }
                
                for field, value in kwargs.items():
                    if field in valid_fields:
                        update_fields.append(f"{field} = ?")
                        values.append(value)
                        
                if update_fields:
                    update_fields.append("updated_at = ?")
                    values.append(datetime.now(timezone.utc).isoformat())
                    values.append(user_id)
                    
                    query = f"""
                        UPDATE user_quiz_stats 
                        SET {', '.join(update_fields)}
                        WHERE user_id = ?
                    """
                    
                    await self.db_manager.execute_query(query, tuple(values))
            else:
                # Create new user
                query = """
                    INSERT INTO user_quiz_stats 
                    (user_id, username, display_name, correct_answers, total_attempts,
                     streak, best_streak, points, last_answer, first_answer)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                params = (
                    user_id,
                    kwargs.get('username'),
                    kwargs.get('display_name'),
                    kwargs.get('correct_answers', 0),
                    kwargs.get('total_attempts', 0),
                    kwargs.get('streak', 0),
                    kwargs.get('best_streak', 0),
                    kwargs.get('points', 0),
                    kwargs.get('last_answer'),
                    kwargs.get('first_answer')
                )
                
                await self.db_manager.execute_query(query, params)
                
            return True
            
        except Exception as e:
            await self.logger.error("Failed to update user quiz stats", {"error": str(e), "user_id": user_id})
            return False
            
    async def get_quiz_leaderboard(self, limit: int = 10, order_by: str = 'points') -> List[Dict[str, Any]]:
        """Get quiz leaderboard"""
        try:
            valid_order_fields = ['points', 'best_streak', 'correct_answers', 'total_attempts']
            if order_by not in valid_order_fields:
                order_by = 'points'
                
            query = f"""
                SELECT * FROM user_quiz_stats 
                ORDER BY {order_by} DESC 
                LIMIT ?
            """
            
            results = await self.db_manager.execute_query(query, (limit,), fetch_all=True)
            
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            await self.logger.error("Failed to get quiz leaderboard", {"error": str(e)})
            return []
            
    # ==========================================================================
    # METADATA CACHE OPERATIONS
    # ==========================================================================
    
    async def get_metadata_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get metadata from cache"""
        try:
            result = await self.db_manager.execute_query(
                "SELECT * FROM metadata_cache WHERE cache_key = ?",
                (cache_key,),
                fetch_one=True
            )
            
            if result:
                # Update access count and timestamp
                await self.db_manager.execute_query(
                    """
                    UPDATE metadata_cache 
                    SET last_accessed = ?, access_count = access_count + 1
                    WHERE cache_key = ?
                    """,
                    (datetime.now(timezone.utc).isoformat(), cache_key)
                )
                
                return dict(result)
            
            return None
            
        except Exception as e:
            await self.logger.error("Failed to get metadata cache", {"error": str(e), "cache_key": cache_key})
            return None
            
    async def set_metadata_cache(self, cache_key: str, **metadata) -> bool:
        """Set metadata in cache"""
        try:
            query = """
                INSERT OR REPLACE INTO metadata_cache
                (cache_key, file_path, reciter, surah_number, duration_seconds,
                 file_size, bitrate, sample_rate, channels, format)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            params = (
                cache_key,
                metadata.get('file_path', ''),
                metadata.get('reciter', ''),
                metadata.get('surah_number', 1),
                metadata.get('duration_seconds'),
                metadata.get('file_size'),
                metadata.get('bitrate'),
                metadata.get('sample_rate'),
                metadata.get('channels'),
                metadata.get('format')
            )
            
            await self.db_manager.execute_query(query, params)
            return True
            
        except Exception as e:
            await self.logger.error("Failed to set metadata cache", {"error": str(e), "cache_key": cache_key})
            return False
            
    async def clear_old_cache(self, days_old: int = 30) -> int:
        """Clear old cache entries"""
        try:
            query = """
                DELETE FROM metadata_cache 
                WHERE last_accessed < datetime('now', '-{} days')
                AND access_count < 5
            """.format(days_old)
            
            result = await self.db_manager.execute_query(query)
            
            await self.logger.info(
                "Old cache entries cleared",
                {"days_old": days_old}
            )
            
            return 0  # Would need to track row count
            
        except Exception as e:
            await self.logger.error("Failed to clear old cache", {"error": str(e)})
            return 0
            
    # ==========================================================================
    # SYSTEM EVENTS
    # ==========================================================================
    
    async def log_system_event(
        self, 
        event_type: str, 
        event_data: Dict[str, Any] = None,
        severity: str = 'info',
        correlation_id: str = None
    ) -> bool:
        """Log a system event to the database"""
        try:
            import json
            
            query = """
                INSERT INTO system_events (event_type, event_data, severity, correlation_id)
                VALUES (?, ?, ?, ?)
            """
            
            params = (
                event_type,
                json.dumps(event_data) if event_data else None,
                severity,
                correlation_id
            )
            
            await self.db_manager.execute_query(query, params)
            return True
            
        except Exception as e:
            await self.logger.error("Failed to log system event", {"error": str(e)})
            return False
            
    async def get_recent_events(self, limit: int = 100, event_type: str = None) -> List[Dict[str, Any]]:
        """Get recent system events"""
        try:
            if event_type:
                query = """
                    SELECT * FROM system_events 
                    WHERE event_type = ?
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """
                params = (event_type, limit)
            else:
                query = """
                    SELECT * FROM system_events 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """
                params = (limit,)
                
            results = await self.db_manager.execute_query(query, params, fetch_all=True)
            
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            await self.logger.error("Failed to get recent events", {"error": str(e)})
            return []
            
    # ==========================================================================
    # DATABASE MANAGEMENT
    # ==========================================================================
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        return await self.db_manager.get_database_stats()
        
    async def backup_database(self, backup_path: Path) -> bool:
        """Create database backup"""
        try:
            success = await self.db_manager.backup_database(backup_path)
            

            
            return success
        except Exception as e:
            await self.logger.error("Database backup failed", {"error": str(e), "backup_path": str(backup_path)})
            return False
        
    async def cleanup_old_data(self, days_to_keep: int = 30) -> int:
        """Clean up old data"""
        return await self.db_manager.cleanup_old_data(days_to_keep)
    
    # ==========================================================================
    # HISTORICAL DATA OPERATIONS FOR CHARTS
    # ==========================================================================
    
    async def record_bot_stats_snapshot(self, **stats) -> bool:
        """Record a snapshot of bot statistics for historical charts"""
        try:
            query = """
                INSERT INTO bot_stats_history 
                (total_runtime_hours, active_sessions, total_commands, total_messages,
                 memory_usage_mb, cpu_percent, gateway_latency, guild_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            params = (
                stats.get('total_runtime_hours', 0.0),
                stats.get('active_sessions', 0),
                stats.get('total_commands', 0),
                stats.get('total_messages', 0),
                stats.get('memory_usage_mb', 0.0),
                stats.get('cpu_percent', 0.0),
                stats.get('gateway_latency', 0.0),
                stats.get('guild_count', 0)
            )
            
            await self.db_manager.execute_query(query, params)
            return True
            
        except Exception as e:
            await self.logger.error(f"Failed to record bot stats snapshot: {e}")
            return False
    
    async def get_bot_stats_history(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get historical bot statistics for charts"""
        try:
            query = """
                SELECT * FROM bot_stats_history 
                WHERE timestamp > datetime('now', '-{} days')
                ORDER BY timestamp ASC
            """.format(days)
            
            results = await self.db_manager.execute_query(query, fetch_all=True)
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            await self.logger.error(f"Failed to get bot stats history: {e}")
            return []
    
    async def get_quiz_history(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get historical quiz statistics for trends"""
        try:
            query = """
                SELECT * FROM quiz_history 
                WHERE timestamp > datetime('now', '-{} days')
                ORDER BY timestamp ASC
            """.format(days)
            
            results = await self.db_manager.execute_query(query, fetch_all=True)
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            await self.logger.error(f"Failed to get quiz history: {e}")
            return []
    
    # ==========================================================================
    # USER PROFILES AND ACHIEVEMENTS
    # ==========================================================================
    
    async def record_user_activity(self, user_id: str, activity_type: str, activity_data: str = None, channel_id: str = None, guild_id: str = None) -> bool:
        """Record user activity for profiles"""
        try:
            query = """
                INSERT INTO user_activity (user_id, activity_type, activity_data, channel_id, guild_id)
                VALUES (?, ?, ?, ?, ?)
            """
            
            params = (user_id, activity_type, activity_data, channel_id, guild_id)
            await self.db_manager.execute_query(query, params)
            return True
            
        except Exception as e:
            await self.logger.error(f"Failed to record user activity: {e}")
            return False
    
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive user profile with activity and achievements"""
        try:
            # Get basic quiz stats
            quiz_stats = await self.get_user_quiz_stats(user_id)
            
            # Get recent activity
            activity_query = """
                SELECT activity_type, activity_data, timestamp, channel_id
                FROM user_activity 
                WHERE user_id = ?
                ORDER BY timestamp DESC 
                LIMIT 20
            """
            activity_results = await self.db_manager.execute_query(activity_query, (user_id,), fetch_all=True)
            activities = [dict(row) for row in activity_results] if activity_results else []
            
            # Get achievements
            achievements_query = """
                SELECT achievement_type, achievement_name, description, earned_at, points_awarded
                FROM user_achievements 
                WHERE user_id = ?
                ORDER BY earned_at DESC
            """
            achievement_results = await self.db_manager.execute_query(achievements_query, (user_id,), fetch_all=True)
            achievements = [dict(row) for row in achievement_results] if achievement_results else []
            
            # Calculate profile stats
            total_points = sum(a['points_awarded'] for a in achievements) + quiz_stats.get('points', 0)
            activity_count = len(activities)
            
            return {
                'user_id': user_id,
                'quiz_stats': quiz_stats,
                'recent_activity': activities,
                'achievements': achievements,
                'total_points': total_points,
                'activity_count': activity_count,
                'join_date': quiz_stats.get('first_answer'),
                'last_seen': activities[0]['timestamp'] if activities else quiz_stats.get('last_answer')
            }
            
        except Exception as e:
            await self.logger.error(f"Failed to get user profile: {e}")
            return {}
    
    async def award_achievement(self, user_id: str, achievement_type: str, achievement_name: str, description: str = None, points: int = 0) -> bool:
        """Award an achievement to a user"""
        try:
            # Check if user already has this achievement
            existing = await self.db_manager.execute_query(
                "SELECT id FROM user_achievements WHERE user_id = ? AND achievement_type = ?",
                (user_id, achievement_type),
                fetch_one=True
            )
            
            if existing:
                return False  # Already has this achievement
            
            query = """
                INSERT INTO user_achievements 
                (user_id, achievement_type, achievement_name, description, points_awarded)
                VALUES (?, ?, ?, ?, ?)
            """
            
            params = (user_id, achievement_type, achievement_name, description, points)
            await self.db_manager.execute_query(query, params)
            
            # Also record as user activity
            import json
            await self.record_user_activity(
                user_id, 
                'achievement_earned', 
                json.dumps({'achievement': achievement_name, 'points': points})
            )
            
            return True
            
        except Exception as e:
            await self.logger.error(f"Failed to award achievement: {e}")
            return False
    
    # ==========================================================================
    # LIVE AUDIO STATUS
    # ==========================================================================
    
    async def update_audio_status(self, **audio_data) -> bool:
        """Update live audio status"""
        try:
            # Build dynamic update query
            update_fields = []
            values = []
            
            valid_fields = {
                'current_surah', 'current_verse', 'reciter', 'is_playing',
                'current_position_seconds', 'total_duration_seconds', 'listeners_count'
            }
            
            for field, value in audio_data.items():
                if field in valid_fields:
                    update_fields.append(f"{field} = ?")
                    values.append(value)
            
            if not update_fields:
                return True
            
            # Add timestamp
            update_fields.append("last_updated = ?")
            values.append(datetime.now(timezone.utc).isoformat())
            values.append(1)  # WHERE id = 1
            
            query = f"""
                UPDATE audio_status 
                SET {', '.join(update_fields)}
                WHERE id = ?
            """
            
            await self.db_manager.execute_query(query, tuple(values))
            return True
            
        except Exception as e:
            await self.logger.error(f"Failed to update audio status: {e}")
            return False
    
    async def get_audio_status(self) -> Dict[str, Any]:
        """Get current live audio status"""
        try:
            result = await self.db_manager.execute_query(
                "SELECT * FROM audio_status WHERE id = 1",
                fetch_one=True
            )
            
            return dict(result) if result else {
                'current_surah': 1,
                'current_verse': 1,
                'reciter': 'Saad Al Ghamdi',
                'is_playing': False,
                'current_position_seconds': 0.0,
                'total_duration_seconds': 0.0,
                'listeners_count': 0,
                'last_updated': None
            }
            
        except Exception as e:
            await self.logger.error(f"Failed to get audio status: {e}")
            return {} 