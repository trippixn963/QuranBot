# =============================================================================
# QuranBot - User Analytics Service
# =============================================================================
# Comprehensive user analytics and session tracking for QuranBot
# Tracks user engagement, feature usage patterns, and retention metrics
# =============================================================================

import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from pathlib import Path
import time
from typing import Any, Dict, List, Optional

from ..core.logger import StructuredLogger
from ..core.webhook_logger import LogLevel


@dataclass
class UserSession:
    """User session data"""
    user_id: int
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    commands_used: List[str] = None
    features_accessed: List[str] = None
    guild_id: Optional[int] = None


@dataclass
class FeatureUsage:
    """Feature usage tracking"""
    feature_name: str
    user_id: int
    timestamp: float
    context: Dict[str, Any] = None


@dataclass
class UserRetention:
    """User retention metrics"""
    user_id: int
    first_seen: float
    last_seen: float
    total_sessions: int
    total_duration: float
    days_active: int
    commands_used: List[str] = None


class UserAnalyticsService:
    """Comprehensive user analytics and session tracking service"""
    
    def __init__(self, logger: StructuredLogger, data_dir: Path = None):
        self.logger = logger
        self.data_dir = data_dir or Path("data")
        self.analytics_file = self.data_dir / "user_analytics.json"
        
        # Session tracking
        self.active_sessions: Dict[int, UserSession] = {}
        self.session_history: deque[UserSession] = deque(maxlen=10000)
        
        # Feature usage tracking
        self.feature_usage: deque[FeatureUsage] = deque(maxlen=50000)
        self.command_usage_counts: Dict[str, int] = defaultdict(int)
        
        # Retention tracking
        self.user_retention: Dict[int, UserRetention] = {}
        
        # Analytics thresholds
        self.session_timeout = 1800  # 30 minutes
        self.peak_usage_threshold = 10  # commands per hour
        self.retention_threshold = 7  # days
        
        # Background tasks
        self.cleanup_task: Optional[asyncio.Task] = None
        self.analytics_task: Optional[asyncio.Task] = None
        
    async def initialize(self):
        """Initialize the analytics service"""
        await self._load_data()
        await self._start_background_tasks()
        
        await self.logger.info("User analytics service initialized")
        
        # Log initialization to webhook
        try:
            from src.core.di_container import get_container
            
            container = get_container()
            if container:
                webhook_router = container.get("webhook_router")
                if webhook_router:
                    await webhook_router.log_data_event(
                        event_type="user_analytics_initialized",
                        title="📊 User Analytics Initialized",
                        description="User analytics service started successfully",
                        level=LogLevel.INFO,
                        context={
                            "active_sessions": len(self.active_sessions),
                            "total_sessions": len(self.session_history),
                            "feature_usage_count": len(self.feature_usage),
                            "user_retention_count": len(self.user_retention),
                        },
                    )
        except Exception as e:
            await self.logger.error("Failed to log analytics initialization to webhook", {"error": str(e)})
    
    async def start_user_session(self, user_id: int, guild_id: Optional[int] = None):
        """Start tracking a user session"""
        current_time = time.time()
        
        # End any existing session
        if user_id in self.active_sessions:
            await self.end_user_session(user_id)
        
        # Create new session
        session = UserSession(
            user_id=user_id,
            start_time=current_time,
            commands_used=[],
            features_accessed=[],
            guild_id=guild_id
        )
        
        self.active_sessions[user_id] = session
        
        await self.logger.info(
            "User session started",
            {"user_id": user_id, "guild_id": guild_id}
        )
    
    async def end_user_session(self, user_id: int):
        """End a user session and calculate metrics"""
        if user_id not in self.active_sessions:
            return
        
        session = self.active_sessions[user_id]
        current_time = time.time()
        
        # Calculate session duration
        session.end_time = current_time
        session.duration = current_time - session.start_time
        
        # Move to history
        self.session_history.append(session)
        del self.active_sessions[user_id]
        
        # Update retention data
        await self._update_user_retention(user_id, session)
        
        await self.logger.info(
            "User session ended",
            {
                "user_id": user_id,
                "duration": session.duration,
                "commands_used": len(session.commands_used),
                "features_accessed": len(session.features_accessed)
            }
        )
        
        # Log session end to webhook for long sessions
        if session.duration > 3600:  # 1 hour
            try:
                from src.core.di_container import get_container
                
                container = get_container()
                if container:
                    webhook_router = container.get("webhook_router")
                    if webhook_router:
                        await webhook_router.log_user_event(
                            event_type="long_user_session",
                            title="⏱️ Long User Session",
                            description=f"User {user_id} had a long session",
                            level=LogLevel.INFO,
                            context={
                                "user_id": user_id,
                                "duration_hours": session.duration / 3600,
                                "commands_used": session.commands_used,
                                "features_accessed": session.features_accessed,
                                "guild_id": session.guild_id,
                            },
                        )
            except Exception as e:
                await self.logger.error("Failed to log long session to webhook", {"error": str(e)})
    
    async def track_command_usage(self, user_id: int, command_name: str, context: Dict[str, Any] = None):
        """Track command usage for analytics"""
        current_time = time.time()
        
        # Update active session
        if user_id in self.active_sessions:
            session = self.active_sessions[user_id]
            if command_name not in session.commands_used:
                session.commands_used.append(command_name)
        
        # Track feature usage
        feature_usage = FeatureUsage(
            feature_name=command_name,
            user_id=user_id,
            timestamp=current_time,
            context=context
        )
        
        self.feature_usage.append(feature_usage)
        self.command_usage_counts[command_name] += 1
        
        # Check for peak usage
        await self._check_peak_usage(command_name)
        
        await self.logger.info(
            "Command usage tracked",
            {"user_id": user_id, "command": command_name}
        )
    
    async def track_feature_access(self, user_id: int, feature_name: str, context: Dict[str, Any] = None):
        """Track feature access for analytics"""
        current_time = time.time()
        
        # Update active session
        if user_id in self.active_sessions:
            session = self.active_sessions[user_id]
            if feature_name not in session.features_accessed:
                session.features_accessed.append(feature_name)
        
        # Track feature usage
        feature_usage = FeatureUsage(
            feature_name=feature_name,
            user_id=user_id,
            timestamp=current_time,
            context=context
        )
        
        self.feature_usage.append(feature_usage)
        
        await self.logger.info(
            "Feature access tracked",
            {"user_id": user_id, "feature": feature_name}
        )
    
    async def _update_user_retention(self, user_id: int, session: UserSession):
        """Update user retention metrics"""
        current_time = time.time()
        
        if user_id not in self.user_retention:
            # New user
            retention = UserRetention(
                user_id=user_id,
                first_seen=session.start_time,
                last_seen=current_time,
                total_sessions=1,
                total_duration=session.duration or 0,
                days_active=1,
                commands_used=session.commands_used.copy() if session.commands_used else []
            )
            self.user_retention[user_id] = retention
            
            # Log new user to webhook
            try:
                from src.core.di_container import get_container
                
                container = get_container()
                if container:
                    webhook_router = container.get("webhook_router")
                    if webhook_router:
                        await webhook_router.log_user_event(
                            event_type="new_user_registered",
                            title="👋 New User Registered",
                            description=f"New user {user_id} started using the bot",
                            level=LogLevel.INFO,
                            context={
                                "user_id": user_id,
                                "guild_id": session.guild_id,
                                "session_duration": session.duration,
                                "commands_used": session.commands_used,
                            },
                        )
            except Exception as e:
                await self.logger.error("Failed to log new user to webhook", {"error": str(e)})
        else:
            # Existing user
            retention = self.user_retention[user_id]
            retention.last_seen = current_time
            retention.total_sessions += 1
            retention.total_duration += session.duration or 0
            
            # Update commands used
            if session.commands_used:
                for cmd in session.commands_used:
                    if cmd not in retention.commands_used:
                        retention.commands_used.append(cmd)
            
            # Calculate days active
            days_since_first = (current_time - retention.first_seen) / 86400
            retention.days_active = max(retention.days_active, int(days_since_first))
    
    async def _check_peak_usage(self, command_name: str):
        """Check for peak usage patterns"""
        current_time = time.time()
        hour_ago = current_time - 3600
        
        # Count recent usage
        recent_usage = sum(
            1 for usage in self.feature_usage
            if usage.feature_name == command_name and usage.timestamp > hour_ago
        )
        
        if recent_usage >= self.peak_usage_threshold:
            # Log peak usage to webhook
            try:
                from src.core.di_container import get_container
                
                container = get_container()
                if container:
                    webhook_router = container.get("webhook_router")
                    if webhook_router:
                        await webhook_router.log_user_event(
                            event_type="peak_command_usage",
                            title="📈 Peak Command Usage",
                            description=f"High usage detected for command {command_name}",
                            level=LogLevel.INFO,
                            context={
                                "command_name": command_name,
                                "usage_count": recent_usage,
                                "threshold": self.peak_usage_threshold,
                                "time_period": "1 hour",
                            },
                        )
            except Exception as e:
                await self.logger.error("Failed to log peak usage to webhook", {"error": str(e)})
    
    async def get_user_analytics(self, user_id: int) -> Dict[str, Any]:
        """Get analytics for a specific user"""
        retention = self.user_retention.get(user_id)
        active_session = self.active_sessions.get(user_id)
        
        # Get user's recent sessions
        user_sessions = [
            s for s in self.session_history
            if s.user_id == user_id
        ][-10:]  # Last 10 sessions
        
        # Get user's feature usage
        user_features = [
            f for f in self.feature_usage
            if f.user_id == user_id
        ][-50:]  # Last 50 feature uses
        
        return {
            "user_id": user_id,
            "retention": retention.__dict__ if retention else None,
            "active_session": active_session.__dict__ if active_session else None,
            "recent_sessions": [s.__dict__ for s in user_sessions],
            "recent_features": [f.__dict__ for f in user_features],
            "total_sessions": len(user_sessions),
            "total_features": len(user_features)
        }
    
    async def get_popular_features(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get most popular features in the last N hours"""
        current_time = time.time()
        cutoff_time = current_time - (hours * 3600)
        
        # Count feature usage
        feature_counts = defaultdict(int)
        for usage in self.feature_usage:
            if usage.timestamp > cutoff_time:
                feature_counts[usage.feature_name] += 1
        
        # Sort by popularity
        popular_features = [
            {"feature": feature, "count": count}
            for feature, count in sorted(
                feature_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]  # Top 10
        ]
        
        return popular_features
    
    async def get_peak_usage_times(self, days: int = 7) -> Dict[str, Any]:
        """Get peak usage times over the last N days"""
        current_time = time.time()
        cutoff_time = current_time - (days * 86400)
        
        # Group usage by hour
        hourly_usage = defaultdict(int)
        for usage in self.feature_usage:
            if usage.timestamp > cutoff_time:
                hour = datetime.fromtimestamp(usage.timestamp).hour
                hourly_usage[hour] += 1
        
        # Find peak hours
        if hourly_usage:
            peak_hour = max(hourly_usage.items(), key=lambda x: x[1])
            avg_usage = sum(hourly_usage.values()) / len(hourly_usage)
        else:
            peak_hour = (0, 0)
            avg_usage = 0
        
        return {
            "peak_hour": peak_hour[0],
            "peak_usage": peak_hour[1],
            "average_usage": avg_usage,
            "hourly_breakdown": dict(hourly_usage)
        }
    
    async def _start_background_tasks(self):
        """Start background analytics tasks"""
        self.cleanup_task = asyncio.create_task(self._cleanup_old_data())
        self.analytics_task = asyncio.create_task(self._generate_analytics_reports())
    
    async def _cleanup_old_data(self):
        """Clean up old analytics data"""
        while True:
            try:
                await asyncio.sleep(3600)  # Every hour
                
                current_time = time.time()
                cutoff_time = current_time - (30 * 86400)  # 30 days
                
                # Clean old feature usage
                self.feature_usage = deque(
                    [f for f in self.feature_usage if f.timestamp > cutoff_time],
                    maxlen=50000
                )
                
                # Clean old sessions
                self.session_history = deque(
                    [s for s in self.session_history if s.start_time > cutoff_time],
                    maxlen=10000
                )
                
                await self._save_data()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                await self.logger.error("Error in analytics cleanup", {"error": str(e)})
    
    async def _generate_analytics_reports(self):
        """Generate periodic analytics reports"""
        while True:
            try:
                await asyncio.sleep(86400)  # Daily
                
                # Generate daily report
                popular_features = await self.get_popular_features(24)
                peak_times = await self.get_peak_usage_times(1)
                
                # Log daily analytics to webhook
                try:
                    from src.core.di_container import get_container
                    
                    container = get_container()
                    if container:
                        webhook_router = container.get("webhook_router")
                        if webhook_router:
                            await webhook_router.log_data_event(
                                event_type="daily_analytics_report",
                                title="📊 Daily Analytics Report",
                                description="Daily user analytics summary",
                                level=LogLevel.INFO,
                                context={
                                    "active_sessions": len(self.active_sessions),
                                    "total_users": len(self.user_retention),
                                    "popular_features": popular_features[:5],
                                    "peak_hour": peak_times["peak_hour"],
                                    "peak_usage": peak_times["peak_usage"],
                                },
                            )
                except Exception as e:
                    await self.logger.error("Failed to log daily analytics to webhook", {"error": str(e)})
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                await self.logger.error("Error generating analytics report", {"error": str(e)})
    
    async def _save_data(self):
        """Save analytics data to disk"""
        try:
            data = {
                "user_retention": {
                    str(uid): retention.__dict__
                    for uid, retention in self.user_retention.items()
                },
                "command_usage_counts": dict(self.command_usage_counts),
                "last_saved": time.time()
            }
            
            self.analytics_file.write_text(json.dumps(data, indent=2))
            
        except Exception as e:
            await self.logger.error("Failed to save analytics data", {"error": str(e)})
    
    async def _load_data(self):
        """Load analytics data from disk"""
        try:
            if self.analytics_file.exists():
                data = json.loads(self.analytics_file.read_text())
                
                # Load user retention
                for uid_str, retention_data in data.get("user_retention", {}).items():
                    uid = int(uid_str)
                    self.user_retention[uid] = UserRetention(**retention_data)
                
                # Load command usage counts
                self.command_usage_counts.update(data.get("command_usage_counts", {}))
                
        except Exception as e:
            await self.logger.error("Failed to load analytics data", {"error": str(e)})
    
    async def shutdown(self):
        """Shutdown the analytics service"""
        if self.cleanup_task:
            self.cleanup_task.cancel()
        if self.analytics_task:
            self.analytics_task.cancel()
        
        await self._save_data()
        await self.logger.info("User analytics service shutdown")


# Global instance
_user_analytics_service: Optional[UserAnalyticsService] = None


def get_user_analytics_service() -> Optional[UserAnalyticsService]:
    """Get the global user analytics service instance"""
    return _user_analytics_service


async def initialize_user_analytics(logger: StructuredLogger, data_dir: Path = None) -> UserAnalyticsService:
    """Initialize the global user analytics service"""
    global _user_analytics_service
    
    if _user_analytics_service is None:
        _user_analytics_service = UserAnalyticsService(logger, data_dir)
        await _user_analytics_service.initialize()
    
    return _user_analytics_service 