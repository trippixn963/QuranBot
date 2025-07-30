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
from ..core.webhook_logger import LogLevel


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

    def __init__(self, logger: StructuredLogger, db_path: Path = None, webhook_logger=None):
        """
        Initialize the database service.
        
        Args:
            logger: Structured logger instance
            db_path: Path to SQLite database file
            webhook_logger: Optional webhook logger for critical events
        """
        self.logger = logger
        self.webhook_logger = webhook_logger
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
            
            # Send webhook notification for database initialization
            if self.webhook_logger:
                try:
                    stats = await self.db_manager.get_database_stats()
                    await self.webhook_logger.send_embed(
                        title="🗄️ SQLite Database Initialized",
                        description="QuranBot database service started successfully",
                        fields=[
                            ("📊 Database Size", f"{stats.get('database_size_mb', 0):.2f} MB", True),
                            ("📝 Total Records", str(stats.get('total_records', 0)), True),
                            ("📋 Tables", str(len(stats.get('table_counts', {}))), True),
                            ("🔧 WAL Mode", "Enabled" if stats.get('wal_info', {}).get('journal_mode') == 'wal' else "Disabled", True)
                        ],
                        color=0x00ff00,  # Green
                        thumbnail_url="https://cdn.discordapp.com/avatars/your-bot-id/avatar.png"
                    )
                except Exception as e:
                    await self.logger.debug("Failed to send database init webhook", {"error": str(e)})
            
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
            
            # Send webhook for significant playback changes
            if self.webhook_logger and ('surah_number' in kwargs or 'reciter' in kwargs):
                try:
                    await self.webhook_logger.send_embed(
                        title="📀 Playback State Updated",
                        description="SQLite database updated successfully",
                        fields=[
                            ("🎵 Surah", str(kwargs.get('surah_number', 'unchanged')), True),
                            ("🎤 Reciter", str(kwargs.get('reciter', 'unchanged')), True),
                            ("💾 Storage", "SQLite Database", True)
                        ],
                        color=0x0099ff,  # Blue
                        thumbnail_url="https://cdn.discordapp.com/avatars/your-bot-id/avatar.png"
                    )
                except Exception:
                    pass  # Don't fail on webhook errors
            
            return True
            
        except Exception as e:
            await self.logger.error(
                "Failed to update playback state",
                {"error": str(e), "fields": list(kwargs.keys())}
            )
            
            # Send critical database error webhook
            if self.webhook_logger:
                try:
                    await self.webhook_logger.send_embed(
                        title="🚨 Database Error - Playback State",
                        description="Critical SQLite operation failed!",
                        fields=[
                            ("❌ Error", str(e)[:100] + "..." if len(str(e)) > 100 else str(e), False),
                            ("🔧 Operation", "Update Playback State", True),
                            ("📝 Fields", str(list(kwargs.keys())), True),
                            ("⚠️ Impact", "Data may not be saved", True)
                        ],
                        color=0xff0000,  # Red
                        thumbnail_url="https://cdn.discordapp.com/avatars/your-bot-id/avatar.png"
                    )
                except Exception:
                    pass  # Don't fail on webhook errors
                    
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
            
            # Log backup event to webhook
            if self.webhook_logger:
                try:
                    from src.core.di_container import get_container
                    
                    container = get_container()
                    if container:
                        webhook_router = container.get("webhook_router")
                        if webhook_router:
                            await webhook_router.log_data_event(
                                event_type="database_backup",
                                title="💾 Database Backup",
                                description=f"Database backup {'completed successfully' if success else 'failed'}",
                                level=LogLevel.INFO if success else LogLevel.ERROR,
                                context={
                                    "backup_path": str(backup_path),
                                    "success": success,
                                    "backup_size_mb": backup_path.stat().st_size / (1024 * 1024) if backup_path.exists() else 0,
                                },
                            )
                except Exception as e:
                    await self.logger.error("Failed to log backup event to webhook", {"error": str(e)})
            
            return success
        except Exception as e:
            await self.logger.error("Database backup failed", {"error": str(e), "backup_path": str(backup_path)})
            return False
        
    async def cleanup_old_data(self, days_to_keep: int = 30) -> int:
        """Clean up old data"""
        return await self.db_manager.cleanup_old_data(days_to_keep) 