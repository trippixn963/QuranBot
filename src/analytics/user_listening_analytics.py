# =============================================================================
# QuranBot - User Listening History and Analytics System
# =============================================================================
# This module provides comprehensive user listening analytics, tracking detailed
# listening patterns, preferences, and behavioral insights for enhanced user
# =============================================================================

"""
experience and administrative oversight.
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict, Counter
import statistics
from pathlib import Path

from ..core.logger import StructuredLogger
from ..core.database import DatabaseManager
from ..services.database_service import QuranBotDatabaseService


class ListeningEventType(Enum):
    """Types of listening events tracked."""
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    SURAH_CHANGE = "surah_change"
    RECITER_CHANGE = "reciter_change"
    SKIP_FORWARD = "skip_forward"
    SKIP_BACKWARD = "skip_backward"
    LOOP_TOGGLE = "loop_toggle"
    SHUFFLE_TOGGLE = "shuffle_toggle"
    VOLUME_CHANGE = "volume_change"
    CONNECTION_JOIN = "connection_join"
    CONNECTION_LEAVE = "connection_leave"


@dataclass
class ListeningEvent:
    """Represents a single listening event with full context."""
    user_id: str
    guild_id: str
    event_type: ListeningEventType
    timestamp: datetime
    session_id: str
    
    # Audio context
    surah_number: Optional[int] = None
    surah_name: Optional[str] = None
    reciter: Optional[str] = None
    position_seconds: Optional[float] = None
    duration_seconds: Optional[float] = None
    
    # User context
    username: Optional[str] = None
    display_name: Optional[str] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['event_type'] = self.event_type.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ListeningEvent':
        """Create from dictionary."""
        data = data.copy()
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['event_type'] = ListeningEventType(data['event_type'])
        return cls(**data)


@dataclass
class ListeningSession:
    """Represents a complete listening session with analytics."""
    session_id: str
    user_id: str
    guild_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    
    # Session statistics
    total_duration_seconds: float = 0.0
    surahs_played: List[int] = field(default_factory=list)
    reciters_used: List[str] = field(default_factory=list)
    position_changes: int = 0
    skip_events: int = 0
    reciter_changes: int = 0
    
    # Session metadata
    initial_surah: Optional[int] = None
    final_surah: Optional[int] = None
    initial_reciter: Optional[str] = None
    final_reciter: Optional[str] = None
    peak_concurrent_listeners: int = 1
    
    @property
    def duration_minutes(self) -> float:
        """Session duration in minutes."""
        return self.total_duration_seconds / 60.0
    
    @property
    def unique_surahs_count(self) -> int:
        """Number of unique surahs played."""
        return len(set(self.surahs_played))
    
    @property
    def unique_reciters_count(self) -> int:
        """Number of unique reciters used."""
        return len(set(self.reciters_used))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        data = asdict(self)
        data['start_time'] = self.start_time.isoformat()
        if self.end_time:
            data['end_time'] = self.end_time.isoformat()
        return data


@dataclass
class UserListeningProfile:
    """Comprehensive user listening profile with preferences and patterns."""
    user_id: str
    username: Optional[str] = None
    display_name: Optional[str] = None
    
    # Listening statistics
    total_listening_time_seconds: float = 0.0
    total_sessions: int = 0
    average_session_duration_seconds: float = 0.0
    longest_session_duration_seconds: float = 0.0
    
    # Preferences
    favorite_surahs: List[Tuple[int, str, int]] = field(default_factory=list)  # (number, name, play_count)
    favorite_reciters: List[Tuple[str, int]] = field(default_factory=list)  # (reciter, play_count)
    preferred_listening_hours: List[int] = field(default_factory=list)  # Hours of day (0-23)
    
    # Behavioral patterns
    skip_frequency: float = 0.0  # Skips per session
    reciter_switching_frequency: float = 0.0  # Reciter changes per session
    session_completion_rate: float = 0.0  # Percentage of sessions completed
    
    # Temporal patterns
    most_active_day_of_week: Optional[str] = None
    most_active_hour_of_day: Optional[int] = None
    listening_streak_days: int = 0
    last_activity: Optional[datetime] = None
    first_activity: Optional[datetime] = None
    
    # Advanced analytics
    listening_consistency_score: float = 0.0  # 0-100 score
    exploration_score: float = 0.0  # How much they explore new content
    engagement_score: float = 0.0  # Overall engagement metric
    
    @property
    def total_listening_time_hours(self) -> float:
        """Total listening time in hours."""
        return self.total_listening_time_seconds / 3600.0
    
    @property
    def average_session_duration_minutes(self) -> float:
        """Average session duration in minutes."""
        return self.average_session_duration_seconds / 60.0


class UserListeningAnalytics:
    """
    Comprehensive user listening analytics system.
    
    This class provides detailed tracking and analysis of user listening
    behavior, preferences, and patterns for QuranBot audio sessions.
    
    Features:
    - Real-time listening event tracking
    - Session-based analytics with detailed metrics
    - User preference analysis and recommendation engine
    - Behavioral pattern recognition
    - Historical trend analysis
    - Privacy-conscious data handling with configurable retention
    """
    
    def __init__(
        self,
        database_service: QuranBotDatabaseService,
        logger: Optional[StructuredLogger] = None,
        data_retention_days: int = 365,
        enable_detailed_tracking: bool = True
    ):
        """
        Initialize the user listening analytics system.
        
        Args:
            database_service: Database service for data persistence
            logger: Optional structured logger instance
            data_retention_days: Number of days to retain detailed event data
            enable_detailed_tracking: Whether to enable detailed event tracking
        """
        self.db_service = database_service
        self._logger = logger or StructuredLogger("user_analytics")
        self.data_retention_days = data_retention_days
        self.enable_detailed_tracking = enable_detailed_tracking
        
        # In-memory session tracking
        self._active_sessions: Dict[str, ListeningSession] = {}
        self._session_events: Dict[str, List[ListeningEvent]] = defaultdict(list)
        
        # Cache for user profiles
        self._user_profiles_cache: Dict[str, UserListeningProfile] = {}
        self._cache_expiry: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(minutes=30)
        
        # Analytics processing queue
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._processing_task: Optional[asyncio.Task] = None
        
    async def initialize(self) -> None:
        """Initialize the analytics system and create database tables."""
        await self._ensure_tables_exist()
        
        # Start event processing task
        self._processing_task = asyncio.create_task(self._process_events_loop())
        
        await self._logger.info("User listening analytics initialized", context={
            "data_retention_days": self.data_retention_days,
            "detailed_tracking": self.enable_detailed_tracking
        })
    
    async def shutdown(self) -> None:
        """Shutdown the analytics system gracefully."""
        # Stop processing task
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
        
        # End all active sessions
        for session_id in list(self._active_sessions.keys()):
            await self.end_listening_session(session_id)
        
        await self._logger.info("User listening analytics shutdown completed")
    
    async def _ensure_tables_exist(self) -> None:
        """Ensure required database tables exist."""
        tables = {
            "listening_events": """
                CREATE TABLE IF NOT EXISTS listening_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    guild_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    session_id TEXT NOT NULL,
                    surah_number INTEGER,
                    surah_name TEXT,
                    reciter TEXT,
                    position_seconds REAL,
                    duration_seconds REAL,
                    username TEXT,
                    display_name TEXT,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """,
            "listening_sessions": """
                CREATE TABLE IF NOT EXISTS listening_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    guild_id TEXT NOT NULL,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME,
                    total_duration_seconds REAL DEFAULT 0,
                    surahs_played TEXT,
                    reciters_used TEXT,
                    position_changes INTEGER DEFAULT 0,
                    skip_events INTEGER DEFAULT 0,
                    reciter_changes INTEGER DEFAULT 0,
                    initial_surah INTEGER,
                    final_surah INTEGER,
                    initial_reciter TEXT,
                    final_reciter TEXT,
                    peak_concurrent_listeners INTEGER DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """,
            "user_listening_profiles": """
                CREATE TABLE IF NOT EXISTS user_listening_profiles (
                    user_id TEXT PRIMARY KEY,
                    username TEXT,
                    display_name TEXT,
                    total_listening_time_seconds REAL DEFAULT 0,
                    total_sessions INTEGER DEFAULT 0,
                    average_session_duration_seconds REAL DEFAULT 0,
                    longest_session_duration_seconds REAL DEFAULT 0,
                    favorite_surahs TEXT,
                    favorite_reciters TEXT,
                    preferred_listening_hours TEXT,
                    skip_frequency REAL DEFAULT 0,
                    reciter_switching_frequency REAL DEFAULT 0,
                    session_completion_rate REAL DEFAULT 0,
                    most_active_day_of_week TEXT,
                    most_active_hour_of_day INTEGER,
                    listening_streak_days INTEGER DEFAULT 0,
                    last_activity DATETIME,
                    first_activity DATETIME,
                    listening_consistency_score REAL DEFAULT 0,
                    exploration_score REAL DEFAULT 0,
                    engagement_score REAL DEFAULT 0,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
        }
        
        # Create indexes for performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_listening_events_user_timestamp ON listening_events(user_id, timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_listening_events_session ON listening_events(session_id)",
            "CREATE INDEX IF NOT EXISTS idx_listening_sessions_user ON listening_sessions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_listening_sessions_start_time ON listening_sessions(start_time)",
            "CREATE INDEX IF NOT EXISTS idx_user_profiles_last_activity ON user_listening_profiles(last_activity)"
        ]
        
        for table_name, query in tables.items():
            try:
                await self.db_service.db_manager.execute_query(query)
                await self._logger.debug(f"Ensured table exists: {table_name}")
            except Exception as e:
                await self._logger.error(f"Error creating table {table_name}", context={
                    "error": str(e)
                })
        
        for index_query in indexes:
            try:
                await self.db_service.db_manager.execute_query(index_query)
            except Exception as e:
                await self._logger.debug(f"Index creation note: {e}")
    
    async def track_listening_event(
        self,
        user_id: str,
        guild_id: str,
        event_type: ListeningEventType,
        session_id: str,
        **kwargs
    ) -> None:
        """
        Track a listening event for analytics.
        
        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID
            event_type: Type of event being tracked
            session_id: Unique session identifier
            **kwargs: Additional event data
        """
        if not self.enable_detailed_tracking:
            return
        
        event = ListeningEvent(
            user_id=user_id,
            guild_id=guild_id,
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            session_id=session_id,
            **kwargs
        )
        
        # Add to processing queue
        await self._event_queue.put(event)
        
        # Update active session
        if session_id in self._active_sessions:
            await self._update_session_from_event(session_id, event)
    
    async def start_listening_session(
        self,
        user_id: str,
        guild_id: str,
        session_id: str,
        username: Optional[str] = None,
        display_name: Optional[str] = None,
        initial_surah: Optional[int] = None,
        initial_reciter: Optional[str] = None
    ) -> None:
        """
        Start tracking a new listening session.
        
        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID  
            session_id: Unique session identifier
            username: User's Discord username
            display_name: User's display name
            initial_surah: Starting surah number
            initial_reciter: Starting reciter name
        """
        session = ListeningSession(
            session_id=session_id,
            user_id=user_id,
            guild_id=guild_id,
            start_time=datetime.now(timezone.utc),
            initial_surah=initial_surah,
            initial_reciter=initial_reciter
        )
        
        self._active_sessions[session_id] = session
        
        # Track session start event
        await self.track_listening_event(
            user_id=user_id,
            guild_id=guild_id,
            event_type=ListeningEventType.SESSION_START,
            session_id=session_id,
            username=username,
            display_name=display_name,
            surah_number=initial_surah,
            reciter=initial_reciter
        )
        
        await self._logger.debug("Started listening session", context={
            "session_id": session_id,
            "user_id": user_id,
            "initial_surah": initial_surah,
            "initial_reciter": initial_reciter
        })
    
    async def end_listening_session(
        self,
        session_id: str,
        final_surah: Optional[int] = None,
        final_reciter: Optional[str] = None
    ) -> Optional[ListeningSession]:
        """
        End a listening session and finalize analytics.
        
        Args:
            session_id: Session identifier to end
            final_surah: Final surah being played
            final_reciter: Final reciter being used
            
        Returns:
            Completed session object or None if session not found
        """
        if session_id not in self._active_sessions:
            await self._logger.warning("Attempted to end non-existent session", context={
                "session_id": session_id
            })
            return None
        
        session = self._active_sessions[session_id]
        session.end_time = datetime.now(timezone.utc)
        session.final_surah = final_surah
        session.final_reciter = final_reciter
        
        # Calculate total duration
        if session.end_time and session.start_time:
            session.total_duration_seconds = (
                session.end_time - session.start_time
            ).total_seconds()
        
        # Track session end event
        await self.track_listening_event(
            user_id=session.user_id,
            guild_id=session.guild_id,
            event_type=ListeningEventType.SESSION_END,
            session_id=session_id,
            surah_number=final_surah,
            reciter=final_reciter,
            metadata={"duration_seconds": session.total_duration_seconds}
        )
        
        # Save session to database
        await self._save_session_to_database(session)
        
        # Update user profile
        await self._update_user_profile_from_session(session)
        
        # Clean up
        completed_session = self._active_sessions.pop(session_id)
        if session_id in self._session_events:
            del self._session_events[session_id]
        
        await self._logger.debug("Ended listening session", context={
            "session_id": session_id,
            "user_id": session.user_id,
            "duration_minutes": session.duration_minutes,
            "surahs_played": session.unique_surahs_count
        })
        
        return completed_session
    
    async def get_user_listening_profile(
        self,
        user_id: str,
        force_refresh: bool = False
    ) -> Optional[UserListeningProfile]:
        """
        Get comprehensive listening profile for a user.
        
        Args:
            user_id: Discord user ID
            force_refresh: Force refresh from database
            
        Returns:
            User listening profile or None if no data
        """
        # Check cache first
        if not force_refresh and user_id in self._user_profiles_cache:
            cache_expiry = self._cache_expiry.get(user_id)
            if cache_expiry and datetime.now(timezone.utc) < cache_expiry:
                return self._user_profiles_cache[user_id]
        
        # Load from database
        try:
            result = await self.db_service.db_manager.execute_query(
                "SELECT * FROM user_listening_profiles WHERE user_id = ?",
                (user_id,)
            )
            
            if not result:
                return None
            
            row = result[0]
            profile = UserListeningProfile(
                user_id=row[0],
                username=row[1],
                display_name=row[2],
                total_listening_time_seconds=row[3] or 0.0,
                total_sessions=row[4] or 0,
                average_session_duration_seconds=row[5] or 0.0,
                longest_session_duration_seconds=row[6] or 0.0,
                favorite_surahs=json.loads(row[7] or "[]"),
                favorite_reciters=json.loads(row[8] or "[]"),
                preferred_listening_hours=json.loads(row[9] or "[]"),
                skip_frequency=row[10] or 0.0,
                reciter_switching_frequency=row[11] or 0.0,
                session_completion_rate=row[12] or 0.0,
                most_active_day_of_week=row[13],
                most_active_hour_of_day=row[14],
                listening_streak_days=row[15] or 0,
                last_activity=datetime.fromisoformat(row[16]) if row[16] else None,
                first_activity=datetime.fromisoformat(row[17]) if row[17] else None,
                listening_consistency_score=row[18] or 0.0,
                exploration_score=row[19] or 0.0,
                engagement_score=row[20] or 0.0
            )
            
            # Cache the profile
            self._user_profiles_cache[user_id] = profile
            self._cache_expiry[user_id] = datetime.now(timezone.utc) + self._cache_ttl
            
            return profile
            
        except Exception as e:
            await self._logger.error("Error loading user profile", context={
                "user_id": user_id,
                "error": str(e)
            })
            return None
    
    async def get_user_listening_history(
        self,
        user_id: str,
        days: int = 30,
        limit: int = 100
    ) -> List[ListeningSession]:
        """
        Get recent listening history for a user.
        
        Args:
            user_id: Discord user ID
            days: Number of days to look back
            limit: Maximum number of sessions to return
            
        Returns:
            List of recent listening sessions
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            results = await self.db_service.db_manager.execute_query(
                """
                SELECT * FROM listening_sessions 
                WHERE user_id = ? AND start_time >= ?
                ORDER BY start_time DESC
                LIMIT ?
                """,
                (user_id, cutoff_date.isoformat(), limit)
            )
            
            sessions = []
            for row in results:
                session = ListeningSession(
                    session_id=row[0],
                    user_id=row[1],
                    guild_id=row[2],
                    start_time=datetime.fromisoformat(row[3]),
                    end_time=datetime.fromisoformat(row[4]) if row[4] else None,
                    total_duration_seconds=row[5] or 0.0,
                    surahs_played=json.loads(row[6] or "[]"),
                    reciters_used=json.loads(row[7] or "[]"),
                    position_changes=row[8] or 0,
                    skip_events=row[9] or 0,
                    reciter_changes=row[10] or 0,
                    initial_surah=row[11],
                    final_surah=row[12],
                    initial_reciter=row[13],
                    final_reciter=row[14],
                    peak_concurrent_listeners=row[15] or 1
                )
                sessions.append(session)
            
            return sessions
            
        except Exception as e:
            await self._logger.error("Error loading user history", context={
                "user_id": user_id,
                "error": str(e)
            })
            return []
    
    async def get_listening_trends(
        self,
        user_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get listening trends and analytics.
        
        Args:
            user_id: Optional user ID for user-specific trends
            days: Number of days to analyze
            
        Returns:
            Dictionary containing trend analysis
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Base query conditions
            conditions = ["start_time >= ?"]
            params = [cutoff_date.isoformat()]
            
            if user_id:
                conditions.append("user_id = ?")
                params.append(user_id)
            
            where_clause = " AND ".join(conditions)
            
            # Get session statistics
            session_stats = await self.db_service.db_manager.execute_query(
                f"""
                SELECT 
                    COUNT(*) as total_sessions,
                    AVG(total_duration_seconds) as avg_duration,
                    SUM(total_duration_seconds) as total_duration,
                    COUNT(DISTINCT user_id) as unique_users
                FROM listening_sessions 
                WHERE {where_clause}
                """,
                tuple(params)
            )
            
            # Get daily activity
            daily_activity = await self.db_service.db_manager.execute_query(
                f"""
                SELECT 
                    DATE(start_time) as date,
                    COUNT(*) as sessions,
                    SUM(total_duration_seconds) as total_time,
                    COUNT(DISTINCT user_id) as unique_users
                FROM listening_sessions 
                WHERE {where_clause}
                GROUP BY DATE(start_time)
                ORDER BY date
                """,
                tuple(params)
            )
            
            # Get popular content
            popular_surahs = await self.db_service.db_manager.execute_query(
                f"""
                SELECT 
                    initial_surah,
                    COUNT(*) as play_count
                FROM listening_sessions 
                WHERE {where_clause} AND initial_surah IS NOT NULL
                GROUP BY initial_surah
                ORDER BY play_count DESC
                LIMIT 10
                """,
                tuple(params)
            )
            
            popular_reciters = await self.db_service.db_manager.execute_query(
                f"""
                SELECT 
                    initial_reciter,
                    COUNT(*) as play_count
                FROM listening_sessions 
                WHERE {where_clause} AND initial_reciter IS NOT NULL
                GROUP BY initial_reciter
                ORDER BY play_count DESC
                LIMIT 10
                """,
                tuple(params)
            )
            
            # Compile trends
            trends = {
                "analysis_period_days": days,
                "user_specific": user_id is not None,
                "summary": {
                    "total_sessions": session_stats[0][0] if session_stats else 0,
                    "average_session_duration_minutes": 
                        (session_stats[0][1] or 0) / 60 if session_stats else 0,
                    "total_listening_time_hours": 
                        (session_stats[0][2] or 0) / 3600 if session_stats else 0,
                    "unique_users": session_stats[0][3] if session_stats and not user_id else None
                },
                "daily_activity": [
                    {
                        "date": row[0],
                        "sessions": row[1],
                        "total_time_hours": row[2] / 3600,
                        "unique_users": row[3]
                    }
                    for row in daily_activity
                ],
                "popular_content": {
                    "surahs": [
                        {"surah_number": row[0], "play_count": row[1]}
                        for row in popular_surahs
                    ],
                    "reciters": [
                        {"reciter": row[0], "play_count": row[1]}
                        for row in popular_reciters
                    ]
                }
            }
            
            return trends
            
        except Exception as e:
            await self._logger.error("Error generating listening trends", context={
                "user_id": user_id,
                "days": days,
                "error": str(e)
            })
            return {"error": "Failed to generate trends"}
    
    async def get_user_recommendations(
        self,
        user_id: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate personalized recommendations based on listening history.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Dictionary containing recommended content
        """
        profile = await self.get_user_listening_profile(user_id)
        if not profile:
            return {"surahs": [], "reciters": [], "listening_times": []}
        
        try:
            # Get user's listening patterns
            recent_sessions = await self.get_user_listening_history(user_id, days=30)
            
            # Analyze preferences
            surah_counter = Counter()
            reciter_counter = Counter()
            hour_counter = Counter()
            
            for session in recent_sessions:
                if session.initial_surah:
                    surah_counter[session.initial_surah] += 1
                if session.initial_reciter:
                    reciter_counter[session.initial_reciter] += 1
                
                hour = session.start_time.hour
                hour_counter[hour] += 1
            
            # Generate recommendations
            recommendations = {
                "surahs": [
                    {
                        "surah_number": surah,
                        "play_count": count,
                        "recommendation_reason": "Based on your listening history"
                    }
                    for surah, count in surah_counter.most_common(5)
                ],
                "reciters": [
                    {
                        "reciter": reciter,
                        "play_count": count,
                        "recommendation_reason": "One of your preferred reciters"
                    }
                    for reciter, count in reciter_counter.most_common(3)
                ],
                "listening_times": [
                    {
                        "hour": hour,
                        "frequency": count,
                        "recommendation_reason": f"You often listen at {hour:02d}:00"
                    }
                    for hour, count in hour_counter.most_common(3)
                ]
            }
            
            return recommendations
            
        except Exception as e:
            await self._logger.error("Error generating recommendations", context={
                "user_id": user_id,
                "error": str(e)
            })
            return {"surahs": [], "reciters": [], "listening_times": []}
    
    async def _process_events_loop(self) -> None:
        """Background loop for processing listening events."""
        try:
            while True:
                try:
                    # Process events in batches for efficiency
                    events_batch = []
                    
                    # Get first event (blocking)
                    event = await self._event_queue.get()
                    events_batch.append(event)
                    
                    # Get additional events without blocking (batch processing)
                    while len(events_batch) < 10:  # Max batch size
                        try:
                            event = self._event_queue.get_nowait()
                            events_batch.append(event)
                        except asyncio.QueueEmpty:
                            break
                    
                    # Process batch
                    await self._process_events_batch(events_batch)
                    
                    # Mark tasks as done
                    for _ in events_batch:
                        self._event_queue.task_done()
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    await self._logger.error("Error in event processing loop", context={
                        "error": str(e)
                    })
                    await asyncio.sleep(1)  # Brief pause before retry
                    
        except asyncio.CancelledError:
            await self._logger.debug("Event processing loop cancelled")
    
    async def _process_events_batch(self, events: List[ListeningEvent]) -> None:
        """Process a batch of listening events."""
        if not events:
            return
        
        # Prepare batch insert
        event_records = []
        for event in events:
            event_data = event.to_dict()
            event_records.append((
                event.user_id,
                event.guild_id,
                event.event_type.value,
                event.timestamp.isoformat(),
                event.session_id,
                event.surah_number,
                event.surah_name,
                event.reciter,
                event.position_seconds,
                event.duration_seconds,
                event.username,
                event.display_name,
                json.dumps(event.metadata) if event.metadata else None
            ))
        
        # Batch insert events
        try:
            await self.db_service.db_manager.execute_many(
                """
                INSERT INTO listening_events (
                    user_id, guild_id, event_type, timestamp, session_id,
                    surah_number, surah_name, reciter, position_seconds, 
                    duration_seconds, username, display_name, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                event_records
            )
            
            await self._logger.debug(f"Processed {len(events)} listening events")
            
        except Exception as e:
            await self._logger.error("Error batch inserting events", context={
                "event_count": len(events),
                "error": str(e)
            })
    
    async def _update_session_from_event(
        self,
        session_id: str,
        event: ListeningEvent
    ) -> None:
        """Update session statistics from an event."""
        if session_id not in self._active_sessions:
            return
        
        session = self._active_sessions[session_id]
        
        # Update session data based on event type
        if event.event_type == ListeningEventType.SURAH_CHANGE:
            if event.surah_number and event.surah_number not in session.surahs_played:
                session.surahs_played.append(event.surah_number)
        
        elif event.event_type == ListeningEventType.RECITER_CHANGE:
            if event.reciter and event.reciter not in session.reciters_used:
                session.reciters_used.append(event.reciter)
            session.reciter_changes += 1
        
        elif event.event_type in [ListeningEventType.SKIP_FORWARD, ListeningEventType.SKIP_BACKWARD]:
            session.skip_events += 1
        
        # Track position changes for engagement metrics
        if event.position_seconds is not None:
            session.position_changes += 1
    
    async def _save_session_to_database(self, session: ListeningSession) -> None:
        """Save completed session to database."""
        try:
            await self.db_service.db_manager.execute_query(
                """
                INSERT OR REPLACE INTO listening_sessions (
                    session_id, user_id, guild_id, start_time, end_time,
                    total_duration_seconds, surahs_played, reciters_used,
                    position_changes, skip_events, reciter_changes,
                    initial_surah, final_surah, initial_reciter, final_reciter,
                    peak_concurrent_listeners
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.session_id,
                    session.user_id,
                    session.guild_id,
                    session.start_time.isoformat(),
                    session.end_time.isoformat() if session.end_time else None,
                    session.total_duration_seconds,
                    json.dumps(session.surahs_played),
                    json.dumps(session.reciters_used),
                    session.position_changes,
                    session.skip_events,
                    session.reciter_changes,
                    session.initial_surah,
                    session.final_surah,
                    session.initial_reciter,
                    session.final_reciter,
                    session.peak_concurrent_listeners
                )
            )
            
        except Exception as e:
            await self._logger.error("Error saving session to database", context={
                "session_id": session.session_id,
                "error": str(e)
            })
    
    async def _update_user_profile_from_session(self, session: ListeningSession) -> None:
        """Update user profile based on completed session."""
        try:
            # Get existing profile or create new one
            profile = await self.get_user_listening_profile(session.user_id)
            if not profile:
                profile = UserListeningProfile(user_id=session.user_id)
            
            # Update session statistics
            profile.total_sessions += 1
            profile.total_listening_time_seconds += session.total_duration_seconds
            
            # Update average session duration
            profile.average_session_duration_seconds = (
                profile.total_listening_time_seconds / profile.total_sessions
            )
            
            # Update longest session
            if session.total_duration_seconds > profile.longest_session_duration_seconds:
                profile.longest_session_duration_seconds = session.total_duration_seconds
            
            # Update activity timestamps
            profile.last_activity = session.end_time or session.start_time
            if not profile.first_activity:
                profile.first_activity = session.start_time
            
            # Update behavioral metrics
            if profile.total_sessions > 0:
                profile.skip_frequency = (
                    sum(s.skip_events for s in [session]) / profile.total_sessions
                )
                profile.reciter_switching_frequency = (
                    sum(s.reciter_changes for s in [session]) / profile.total_sessions
                )
            
            # Calculate engagement scores
            profile.engagement_score = self._calculate_engagement_score(profile)
            profile.exploration_score = self._calculate_exploration_score(profile)
            profile.listening_consistency_score = self._calculate_consistency_score(profile)
            
            # Save updated profile
            await self._save_user_profile(profile)
            
            # Update cache
            self._user_profiles_cache[session.user_id] = profile
            self._cache_expiry[session.user_id] = datetime.now(timezone.utc) + self._cache_ttl
            
        except Exception as e:
            await self._logger.error("Error updating user profile", context={
                "user_id": session.user_id,
                "session_id": session.session_id,
                "error": str(e)
            })
    
    async def _save_user_profile(self, profile: UserListeningProfile) -> None:
        """Save user profile to database."""
        try:
            await self.db_service.db_manager.execute_query(
                """
                INSERT OR REPLACE INTO user_listening_profiles (
                    user_id, username, display_name, total_listening_time_seconds,
                    total_sessions, average_session_duration_seconds, 
                    longest_session_duration_seconds, favorite_surahs, 
                    favorite_reciters, preferred_listening_hours, skip_frequency,
                    reciter_switching_frequency, session_completion_rate,
                    most_active_day_of_week, most_active_hour_of_day,
                    listening_streak_days, last_activity, first_activity,
                    listening_consistency_score, exploration_score, engagement_score,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile.user_id,
                    profile.username,
                    profile.display_name,
                    profile.total_listening_time_seconds,
                    profile.total_sessions,
                    profile.average_session_duration_seconds,
                    profile.longest_session_duration_seconds,
                    json.dumps(profile.favorite_surahs),
                    json.dumps(profile.favorite_reciters),
                    json.dumps(profile.preferred_listening_hours),
                    profile.skip_frequency,
                    profile.reciter_switching_frequency,
                    profile.session_completion_rate,
                    profile.most_active_day_of_week,
                    profile.most_active_hour_of_day,
                    profile.listening_streak_days,
                    profile.last_activity.isoformat() if profile.last_activity else None,
                    profile.first_activity.isoformat() if profile.first_activity else None,
                    profile.listening_consistency_score,
                    profile.exploration_score,
                    profile.engagement_score,
                    datetime.now(timezone.utc).isoformat()
                )
            )
            
        except Exception as e:
            await self._logger.error("Error saving user profile", context={
                "user_id": profile.user_id,
                "error": str(e)
            })
    
    def _calculate_engagement_score(self, profile: UserListeningProfile) -> float:
        """Calculate user engagement score (0-100)."""
        if profile.total_sessions == 0:
            return 0.0
        
        # Factors contributing to engagement
        factors = []
        
        # Session frequency (sessions per day since first activity)
        if profile.first_activity and profile.last_activity:
            days_active = (profile.last_activity - profile.first_activity).days + 1
            session_frequency = profile.total_sessions / days_active
            factors.append(min(session_frequency * 10, 25))  # Max 25 points
        
        # Average session duration (longer sessions = higher engagement)
        avg_duration_minutes = profile.average_session_duration_seconds / 60
        duration_score = min(avg_duration_minutes / 10, 25)  # Max 25 points
        factors.append(duration_score)
        
        # Low skip frequency (completing content = higher engagement)
        skip_score = max(0, 25 - (profile.skip_frequency * 5))  # Max 25 points
        factors.append(skip_score)
        
        # Listening consistency (regular listening = higher engagement)
        factors.append(profile.listening_consistency_score * 0.25)  # Max 25 points
        
        return min(sum(factors), 100.0)
    
    def _calculate_exploration_score(self, profile: UserListeningProfile) -> float:
        """Calculate user exploration score (0-100)."""
        if not profile.favorite_surahs and not profile.favorite_reciters:
            return 0.0
        
        # Calculate diversity
        unique_surahs = len(profile.favorite_surahs)
        unique_reciters = len(profile.favorite_reciters)
        
        # Normalize to 0-100 scale
        surah_score = min(unique_surahs * 2, 70)  # Max 70 points (35 unique surahs)
        reciter_score = min(unique_reciters * 10, 30)  # Max 30 points (3 unique reciters)
        
        return min(surah_score + reciter_score, 100.0)
    
    def _calculate_consistency_score(self, profile: UserListeningProfile) -> float:
        """Calculate listening consistency score (0-100)."""
        if profile.total_sessions < 2:
            return 0.0
        
        # This would require more historical data analysis
        # For now, return a basic score based on session frequency
        if profile.first_activity and profile.last_activity:
            days_span = (profile.last_activity - profile.first_activity).days + 1
            if days_span > 0:
                sessions_per_day = profile.total_sessions / days_span
                return min(sessions_per_day * 50, 100.0)
        
        return 50.0  # Default moderate consistency
    
    async def cleanup_old_data(self) -> None:
        """Clean up old analytics data based on retention policy."""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.data_retention_days)
            
            # Delete old events
            deleted_events = await self.db_service.db_manager.execute_query(
                "DELETE FROM listening_events WHERE timestamp < ?",
                (cutoff_date.isoformat(),)
            )
            
            # Delete old sessions
            deleted_sessions = await self.db_service.db_manager.execute_query(
                "DELETE FROM listening_sessions WHERE start_time < ?",
                (cutoff_date.isoformat(),)
            )
            
            await self._logger.info("Cleaned up old analytics data", context={
                "retention_days": self.data_retention_days,
                "deleted_events": deleted_events,
                "deleted_sessions": deleted_sessions
            })
            
        except Exception as e:
            await self._logger.error("Error cleaning up old data", context={
                "error": str(e)
            })


# Factory function for easy integration
async def create_user_analytics(
    database_service: QuranBotDatabaseService,
    logger: Optional[StructuredLogger] = None,
    **kwargs
) -> UserListeningAnalytics:
    """
    Create and initialize user listening analytics system.
    
    Args:
        database_service: Database service instance
        logger: Optional structured logger
        **kwargs: Additional configuration options
        
    Returns:
        Initialized UserListeningAnalytics instance
    """
    analytics = UserListeningAnalytics(
        database_service=database_service,
        logger=logger,
        **kwargs
    )
    
    await analytics.initialize()
    return analytics