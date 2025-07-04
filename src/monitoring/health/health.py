"""
Health monitoring system for the Discord Quran Bot.
Tracks bot performance, uptime, and operational metrics.

This module provides comprehensive health monitoring including:
- Bot performance metrics tracking
- Error monitoring and history
- Uptime calculation and formatting
- Health status assessment
- Performance summaries and reporting

Features:
    - Real-time performance tracking
    - Error rate calculation
    - Uptime monitoring
    - Health status assessment
    - Performance history tracking
    - Comprehensive error handling
    - Detailed logging and monitoring

Author: John (Discord: Trippxin)
Version: 2.0.0
"""

import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from ..logging.log_helpers import log_function_call, log_operation


@dataclass
class BotMetrics:
    """
    Bot performance metrics data class.

    This class holds all the performance metrics for the bot
    including uptime, surahs played, errors, and current status.

    Attributes:
        start_time (datetime): When the bot started
        surahs_played (int): Total number of surahs played
        errors_count (int): Total number of errors encountered
        reconnections (int): Total number of reconnections
        last_activity (Optional[datetime]): Last activity timestamp
        current_surah (Optional[str]): Currently playing surah
        is_streaming (bool): Whether the bot is currently streaming
    """

    start_time: datetime
    surahs_played: int = 0
    errors_count: int = 0
    reconnections: int = 0
    last_activity: Optional[datetime] = None
    current_surah: Optional[str] = None
    is_streaming: bool = False


class HealthMonitor:
    """
    Health monitoring system for the Quran Bot.

    This class provides comprehensive health monitoring capabilities
    including performance tracking, error monitoring, and health
    status assessment.

    Features:
        - Real-time performance tracking
        - Error monitoring and history
        - Uptime calculation and formatting
        - Health status assessment
        - Performance summaries and reporting
    """

    def __init__(self):
        """
        Initialize the health monitor.

        Sets up the monitoring system with initial metrics
        and prepares for tracking bot performance.
        """
        try:
            self.metrics = BotMetrics(start_time=datetime.now())
            self.error_history: List[Dict[str, Any]] = []
            self.performance_history: List[Dict[str, Any]] = []

            from ..logging.logger import logger

            logger.info("🏥 Health monitor initialized")

        except Exception as e:
            from ..logging.logger import logger

            logger.error(f"❌ Failed to initialize health monitor: {e}")
            logger.error(
                f"🔍 Health monitor init error traceback: {traceback.format_exc()}"
            )
            raise

    @log_function_call
    def update_current_song(self, song_name: str) -> None:
        """
        Update the currently playing song.

        Args:
            song_name (str): Name of the currently playing song
        """
        try:
            self.metrics.current_surah = song_name
            self.metrics.last_activity = datetime.now()
            self.metrics.surahs_played += 1

            from ..logging.logger import logger

            logger.debug(f"🎵 Updated current song: {song_name}")

        except Exception as e:
            from ..logging.logger import logger

            logger.error(f"❌ Error updating current song: {e}")

    @log_function_call
    def record_error(self, error: Exception, context: str) -> None:
        """
        Record an error occurrence.

        Args:
            error (Exception): The error that occurred
            context (str): Context where the error occurred
        """
        try:
            self.metrics.errors_count += 1
            self.metrics.last_activity = datetime.now()

            error_record = {
                "timestamp": datetime.now().isoformat(),
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context,
                "traceback": traceback.format_exc(),
            }
            self.error_history.append(error_record)

            # Keep only last 100 errors to prevent memory issues
            if len(self.error_history) > 100:
                self.error_history = self.error_history[-100:]

            from ..logging.logger import logger

            logger.debug(f"❌ Error recorded: {type(error).__name__} in {context}")

        except Exception as e:
            from ..logging.logger import logger

            logger.error(f"❌ Error recording error: {e}")

    @log_function_call
    def record_reconnection(self) -> None:
        """
        Record a reconnection event.

        This method tracks when the bot reconnects to voice channels,
        which is important for monitoring connection stability.
        """
        try:
            self.metrics.reconnections += 1
            self.metrics.last_activity = datetime.now()

            from ..logging.logger import logger

            logger.debug(
                f"🔌 Reconnection recorded (total: {self.metrics.reconnections})"
            )

        except Exception as e:
            from ..logging.logger import logger

            logger.error(f"❌ Error recording reconnection: {e}")

    @log_function_call
    def set_streaming_status(self, is_streaming: bool) -> None:
        """
        Update streaming status.

        Args:
            is_streaming (bool): Whether the bot is currently streaming
        """
        try:
            self.metrics.is_streaming = is_streaming
            self.metrics.last_activity = datetime.now()

            from ..logging.logger import logger

            status = "✅ Streaming" if is_streaming else "❌ Not streaming"
            logger.debug(f"📡 Streaming status updated: {status}")

        except Exception as e:
            from ..logging.logger import logger

            logger.error(f"❌ Error updating streaming status: {e}")

    @log_function_call
    def get_uptime(self) -> timedelta:
        """
        Get bot uptime.

        Returns:
            timedelta: Time since bot started
        """
        try:
            return datetime.now() - self.metrics.start_time
        except Exception as e:
            from ..logging.logger import logger

            logger.error(f"❌ Error calculating uptime: {e}")
            return timedelta(0)

    @log_function_call
    def get_uptime_string(self) -> str:
        """
        Get formatted uptime string.

        Returns:
            str: Human-readable uptime string (e.g., "2d 5h 30m 15s")
        """
        try:
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

        except Exception as e:
            from ..logging.logger import logger

            logger.error(f"❌ Error formatting uptime: {e}")
            return "Unknown"

    @log_function_call
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get comprehensive health status.

        This method provides a complete overview of the bot's health
        including uptime, performance metrics, and error rates.

        Returns:
            Dict[str, Any]: Dictionary containing comprehensive health status
        """
        try:
            uptime = self.get_uptime()

            # Calculate error rate safely
            error_rate = 0.0
            if self.metrics.surahs_played > 0:
                error_rate = self.metrics.errors_count / self.metrics.surahs_played

            # Determine overall health status
            if self.metrics.errors_count < 5:
                status = "healthy"
            elif self.metrics.errors_count < 10:
                status = "warning"
            else:
                status = "critical"

            return {
                "status": status,
                "uptime": self.get_uptime_string(),
                "uptime_seconds": uptime.total_seconds(),
                "songs_played": self.metrics.surahs_played,
                "surahs_played": self.metrics.surahs_played,
                "errors_count": self.metrics.errors_count,
                "reconnections": self.metrics.reconnections,
                "current_song": self.metrics.current_surah,
                "current_surah": self.metrics.current_surah,
                "is_streaming": self.metrics.is_streaming,
                "last_activity": (
                    self.metrics.last_activity.isoformat()
                    if self.metrics.last_activity
                    else None
                ),
                "error_rate": error_rate,
                "start_time": self.metrics.start_time.isoformat(),
                "recent_errors": self.error_history[-5:] if self.error_history else [],
            }

        except Exception as e:
            from ..logging.logger import logger

            logger.error(f"❌ Error getting health status: {e}")
            return {
                "status": "error",
                "error": str(e),
                "uptime": "Unknown",
                "uptime_seconds": 0,
                "songs_played": 0,
                "surahs_played": 0,
                "errors_count": 0,
                "reconnections": 0,
                "current_song": None,
                "current_surah": None,
                "is_streaming": False,
                "last_activity": None,
                "error_rate": 0.0,
                "start_time": datetime.now().isoformat(),
                "recent_errors": [],
            }

    @log_function_call
    def get_performance_summary(self) -> str:
        """
        Get a human-readable performance summary.

        Returns:
            str: Formatted performance summary string
        """
        try:
            health = self.get_health_status()

            # Determine status emoji
            status_emoji = {
                "healthy": "✅",
                "warning": "⚠️",
                "critical": "🚨",
                "error": "❌",
            }.get(health["status"], "❓")

            summary = f"""
🤖 Bot Health Summary:
{status_emoji} Status: {health['status'].upper()}
⏱️  Uptime: {health['uptime']}
🎵 Songs Played: {health['songs_played']}
❌ Errors: {health['errors_count']}
🔌 Reconnections: {health['reconnections']}
🎵 Current Song: {health['current_song'] or 'None'}
📡 Streaming: {'✅ Yes' if health['is_streaming'] else '❌ No'}
📊 Error Rate: {health['error_rate']:.2%}
            """
            return summary.strip()

        except Exception as e:
            from ..logging.logger import logger

            logger.error(f"❌ Error generating performance summary: {e}")
            return "❌ Error generating performance summary"

    def get_error_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent error history.

        Args:
            limit (int): Maximum number of errors to return

        Returns:
            List[Dict[str, Any]]: List of recent error records
        """
        try:
            return self.error_history[-limit:] if self.error_history else []
        except Exception as e:
            from ..logging.logger import logger

            logger.error(f"❌ Error getting error history: {e}")
            return []

    def clear_error_history(self) -> None:
        """
        Clear the error history.

        This method can be used to reset error tracking
        after resolving issues.
        """
        try:
            self.error_history.clear()
            from ..logging.logger import logger

            logger.info("🧹 Error history cleared")
        except Exception as e:
            from ..logging.logger import logger

            logger.error(f"❌ Error clearing error history: {e}")
