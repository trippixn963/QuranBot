# =============================================================================
# QuranBot - Listening Statistics Manager
# =============================================================================
# Tracks user voice channel listening time and generates leaderboards
# =============================================================================

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .tree_log import log_error_with_traceback, log_perfect_tree_section

# =============================================================================
# Configuration
# =============================================================================

# Path to the listening stats data file
DATA_DIR = Path(__file__).parent.parent.parent / "data"
STATS_FILE = DATA_DIR / "listening_stats.json"

# =============================================================================
# Data Structure Classes
# =============================================================================


class UserStats:
    """Represents listening statistics for a single user"""

    def __init__(self, user_id: int, total_time: float = 0.0, sessions: int = 0):
        self.user_id = user_id
        self.total_time = total_time  # Total listening time in seconds
        self.sessions = sessions  # Number of listening sessions
        self.last_seen = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "user_id": self.user_id,
            "total_time": self.total_time,
            "sessions": self.sessions,
            "last_seen": self.last_seen,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "UserStats":
        """Create UserStats from dictionary"""
        stats = cls(
            user_id=data["user_id"],
            total_time=data.get("total_time", 0.0),
            sessions=data.get("sessions", 0),
        )
        stats.last_seen = data.get("last_seen", datetime.now(timezone.utc).isoformat())
        return stats


class ActiveSession:
    """Represents an active listening session"""

    def __init__(self, user_id: int, start_time: datetime):
        self.user_id = user_id
        self.start_time = start_time

    def get_duration(self) -> float:
        """Get current session duration in seconds"""
        return (datetime.now(timezone.utc) - self.start_time).total_seconds()

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {"user_id": self.user_id, "start_time": self.start_time.isoformat()}

    @classmethod
    def from_dict(cls, data: Dict) -> "ActiveSession":
        """Create ActiveSession from dictionary"""
        return cls(
            user_id=data["user_id"],
            start_time=datetime.fromisoformat(data["start_time"]),
        )


# =============================================================================
# Listening Statistics Manager
# =============================================================================


class ListeningStatsManager:
    """Manages user listening statistics and leaderboards"""

    def __init__(self):
        self.users: Dict[int, UserStats] = {}
        self.active_sessions: Dict[int, ActiveSession] = {}
        self.total_listening_time = 0.0
        self.total_sessions = 0
        self.last_updated = None

        # Ensure data directory exists
        DATA_DIR.mkdir(exist_ok=True)

        # Load existing data
        self.load_stats()

    def load_stats(self) -> None:
        """Load listening statistics from file"""
        try:
            if STATS_FILE.exists():
                with open(STATS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Load user stats
                for user_id_str, user_data in data.get("users", {}).items():
                    user_id = int(user_id_str)
                    self.users[user_id] = UserStats.from_dict(user_data)

                # Load active sessions
                for user_id_str, session_data in data.get(
                    "active_sessions", {}
                ).items():
                    user_id = int(user_id_str)
                    self.active_sessions[user_id] = ActiveSession.from_dict(
                        session_data
                    )

                # Load total stats
                total_stats = data.get("total_stats", {})
                self.total_listening_time = total_stats.get("total_listening_time", 0.0)
                self.total_sessions = total_stats.get("total_sessions", 0)
                self.last_updated = total_stats.get("last_updated")

                log_perfect_tree_section(
                    "Listening Stats - Loaded",
                    [
                        ("users_loaded", f"✅ {len(self.users)} users loaded"),
                        (
                            "active_sessions",
                            f"✅ {len(self.active_sessions)} active sessions",
                        ),
                        (
                            "total_time",
                            f"✅ Total listening time: {self.format_time(self.total_listening_time)}",
                        ),
                        ("total_sessions", f"✅ Total sessions: {self.total_sessions}"),
                    ],
                    "📊",
                )
            else:
                log_perfect_tree_section(
                    "Listening Stats - New File",
                    [
                        ("status", "📊 No existing stats file found"),
                        ("action", "✅ Starting with fresh statistics"),
                    ],
                    "📊",
                )

        except Exception as e:
            log_error_with_traceback(
                "Failed to load listening statistics",
                e,
                {"stats_file": str(STATS_FILE)},
            )

    def save_stats(self) -> None:
        """Save listening statistics to file"""
        try:
            data = {
                "users": {
                    str(user_id): user_stats.to_dict()
                    for user_id, user_stats in self.users.items()
                },
                "active_sessions": {
                    str(user_id): session.to_dict()
                    for user_id, session in self.active_sessions.items()
                },
                "total_stats": {
                    "total_listening_time": self.total_listening_time,
                    "total_sessions": self.total_sessions,
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                },
                "leaderboard_cache": {
                    "last_calculated": datetime.now(timezone.utc).isoformat(),
                    "top_users": self.get_top_users(10),
                },
            }

            with open(STATS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self.last_updated = datetime.now(timezone.utc).isoformat()

        except Exception as e:
            log_error_with_traceback(
                "Failed to save listening statistics",
                e,
                {"stats_file": str(STATS_FILE)},
            )

    def user_joined_voice(self, user_id: int) -> None:
        """Record when a user joins the voice channel"""
        try:
            # If user already has an active session, end it first
            if user_id in self.active_sessions:
                self.user_left_voice(user_id)

            # Start new session
            self.active_sessions[user_id] = ActiveSession(
                user_id=user_id, start_time=datetime.now(timezone.utc)
            )

            # Initialize user stats if not exists
            if user_id not in self.users:
                self.users[user_id] = UserStats(user_id)

            log_perfect_tree_section(
                "Voice Join Tracking",
                [
                    ("user_id", f"👤 User {user_id} joined voice channel"),
                    (
                        "session_start",
                        f"⏰ Session started at {datetime.now(timezone.utc).strftime('%H:%M:%S')}",
                    ),
                    ("total_users", f"📊 {len(self.active_sessions)} users in voice"),
                ],
                "🎧",
            )

        except Exception as e:
            log_error_with_traceback(
                "Failed to track voice channel join", e, {"user_id": user_id}
            )

    def user_left_voice(self, user_id: int) -> float:
        """Record when a user leaves the voice channel and return session duration"""
        try:
            if user_id not in self.active_sessions:
                return 0.0

            # Calculate session duration
            session = self.active_sessions[user_id]
            duration = session.get_duration()

            # Update user stats
            if user_id not in self.users:
                self.users[user_id] = UserStats(user_id)

            self.users[user_id].total_time += duration
            self.users[user_id].sessions += 1
            self.users[user_id].last_seen = datetime.now(timezone.utc).isoformat()

            # Update total stats
            self.total_listening_time += duration
            self.total_sessions += 1

            # Remove active session
            del self.active_sessions[user_id]

            # Save stats
            self.save_stats()

            log_perfect_tree_section(
                "Voice Leave Tracking",
                [
                    ("user_id", f"👤 User {user_id} left voice channel"),
                    (
                        "session_duration",
                        f"⏱️ Session duration: {self.format_time(duration)}",
                    ),
                    (
                        "total_time",
                        f"📊 User total time: {self.format_time(self.users[user_id].total_time)}",
                    ),
                    (
                        "total_sessions",
                        f"🔢 User total sessions: {self.users[user_id].sessions}",
                    ),
                ],
                "🎧",
            )

            return duration

        except Exception as e:
            log_error_with_traceback(
                "Failed to track voice channel leave", e, {"user_id": user_id}
            )
            return 0.0

    def get_user_stats(self, user_id: int) -> Optional[UserStats]:
        """Get statistics for a specific user"""
        return self.users.get(user_id)

    def get_top_users(self, limit: int = 10) -> List[Tuple[int, float, int]]:
        """Get top users by listening time"""
        # Include active session time for current rankings
        user_times = []

        for user_id, user_stats in self.users.items():
            total_time = user_stats.total_time

            # Add current session time if user is active
            if user_id in self.active_sessions:
                total_time += self.active_sessions[user_id].get_duration()

            user_times.append((user_id, total_time, user_stats.sessions))

        # Sort by total time (descending) and return top users
        user_times.sort(key=lambda x: x[1], reverse=True)
        return user_times[:limit]

    def format_time(self, seconds: float) -> str:
        """Format time in seconds to human-readable format"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            if hours < 24:
                return f"{hours}h {minutes}m"
            else:
                days = int(hours // 24)
                remaining_hours = int(hours % 24)
                return f"{days}d {remaining_hours}h"

    def get_leaderboard_data(self) -> Dict:
        """Get comprehensive leaderboard data"""
        top_users = self.get_top_users(10)

        return {
            "top_users": top_users,
            "total_listening_time": self.total_listening_time,
            "total_sessions": self.total_sessions,
            "active_users": len(self.active_sessions),
            "total_users": len(self.users),
            "last_updated": self.last_updated,
        }


# =============================================================================
# Global Instance
# =============================================================================

# Global statistics manager instance
listening_stats_manager = ListeningStatsManager()


# =============================================================================
# Utility Functions
# =============================================================================


def track_voice_join(user_id: int) -> None:
    """Track when a user joins the voice channel"""
    listening_stats_manager.user_joined_voice(user_id)


def track_voice_leave(user_id: int) -> float:
    """Track when a user leaves the voice channel"""
    return listening_stats_manager.user_left_voice(user_id)


def get_user_listening_stats(user_id: int) -> Optional[UserStats]:
    """Get listening statistics for a user"""
    return listening_stats_manager.get_user_stats(user_id)


def get_leaderboard_data() -> Dict:
    """Get leaderboard data for display"""
    return listening_stats_manager.get_leaderboard_data()


def format_listening_time(seconds: float) -> str:
    """Format listening time for display"""
    return listening_stats_manager.format_time(seconds)


# =============================================================================
# Export Functions
# =============================================================================

__all__ = [
    "ListeningStatsManager",
    "UserStats",
    "ActiveSession",
    "track_voice_join",
    "track_voice_leave",
    "get_user_listening_stats",
    "get_leaderboard_data",
    "format_listening_time",
    "listening_stats_manager",
]
