"""
Health monitoring system for the Discord Quran Bot.
Tracks bot performance, uptime, and operational metrics.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class BotMetrics:
    """Bot performance metrics."""
    start_time: datetime
    songs_played: int = 0
    errors_count: int = 0
    reconnections: int = 0
    last_activity: Optional[datetime] = None
    current_song: Optional[str] = None
    is_streaming: bool = False

class HealthMonitor:
    """Health monitoring system for the Quran Bot."""
    
    def __init__(self):
        """Initialize the health monitor."""
        self.metrics = BotMetrics(start_time=datetime.now())
        self.error_history: list = []
        self.performance_history: list = []
        
    def update_current_song(self, song_name: str) -> None:
        """Update the currently playing song."""
        self.metrics.current_song = song_name
        self.metrics.last_activity = datetime.now()
        self.metrics.songs_played += 1
        
    def record_error(self, error: Exception, context: str) -> None:
        """Record an error occurrence."""
        self.metrics.errors_count += 1
        self.metrics.last_activity = datetime.now()
        
        error_record = {
            'timestamp': datetime.now().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context
        }
        self.error_history.append(error_record)
        
        # Keep only last 100 errors
        if len(self.error_history) > 100:
            self.error_history = self.error_history[-100:]
            
    def record_reconnection(self) -> None:
        """Record a reconnection event."""
        self.metrics.reconnections += 1
        self.metrics.last_activity = datetime.now()
        
    def set_streaming_status(self, is_streaming: bool) -> None:
        """Update streaming status."""
        self.metrics.is_streaming = is_streaming
        self.metrics.last_activity = datetime.now()
        
    def get_uptime(self) -> timedelta:
        """Get bot uptime."""
        return datetime.now() - self.metrics.start_time
        
    def get_uptime_string(self) -> str:
        """Get formatted uptime string."""
        uptime = self.get_uptime()
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m {seconds}s"
        elif hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        else:
            return f"{minutes}m {seconds}s"
            
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status."""
        uptime = self.get_uptime()
        
        return {
            'status': 'healthy' if self.metrics.errors_count < 10 else 'warning',
            'uptime': self.get_uptime_string(),
            'uptime_seconds': uptime.total_seconds(),
            'songs_played': self.metrics.songs_played,
            'errors_count': self.metrics.errors_count,
            'reconnections': self.metrics.reconnections,
            'current_song': self.metrics.current_song,
            'is_streaming': self.metrics.is_streaming,
            'last_activity': self.metrics.last_activity.isoformat() if self.metrics.last_activity else None,
            'error_rate': self.metrics.errors_count / max(self.metrics.songs_played, 1),
            'start_time': self.metrics.start_time.isoformat()
        }
        
    def get_performance_summary(self) -> str:
        """Get a human-readable performance summary."""
        health = self.get_health_status()
        
        summary = f"""
🤖 Bot Health Summary:
⏱️  Uptime: {health['uptime']}
🎵 Songs Played: {health['songs_played']}
❌ Errors: {health['errors_count']}
🔌 Reconnections: {health['reconnections']}
🎵 Current Song: {health['current_song'] or 'None'}
📡 Streaming: {'✅ Yes' if health['is_streaming'] else '❌ No'}
📊 Error Rate: {health['error_rate']:.2%}
        """
        return summary.strip() 