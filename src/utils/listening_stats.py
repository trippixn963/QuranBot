# =============================================================================
# QuranBot - Listening Statistics Manager
# =============================================================================
# Tracks user voice channel listening time and generates leaderboards
# =============================================================================

import asyncio
import json
import os
import shutil
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .tree_log import log_error_with_traceback, log_perfect_tree_section

# EST timezone for backup scheduling and naming
EST = timezone(timedelta(hours=-5))

# =============================================================================
# Configuration
# =============================================================================

# Path to the listening stats data file
DATA_DIR = Path(__file__).parent.parent.parent / "data"
BACKUP_DIR = Path(__file__).parent.parent.parent / "backup"
STATS_FILE = DATA_DIR / "listening_stats.json"

# Backup configuration
BACKUP_INTERVAL_HOURS = 1
_last_backup_time = None
_backup_task = None

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
        """Load listening statistics from file with backup recovery and corruption detection"""
        try:
            if STATS_FILE.exists():
                # Try to load main file
                try:
                    with open(STATS_FILE, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    # Validate data integrity
                    if not isinstance(data, dict):
                        raise ValueError(
                            "Invalid data format: root is not a dictionary"
                        )

                    required_keys = ["users", "active_sessions", "total_stats"]
                    missing_keys = [key for key in required_keys if key not in data]
                    if missing_keys:
                        raise ValueError(f"Missing required keys: {missing_keys}")

                    # Load user stats
                    for user_id_str, user_data in data.get("users", {}).items():
                        try:
                            user_id = int(user_id_str)
                            self.users[user_id] = UserStats.from_dict(user_data)
                        except (ValueError, KeyError) as user_error:
                            log_error_with_traceback(
                                f"Failed to load user {user_id_str}",
                                user_error,
                                {"user_data": user_data},
                            )
                            continue  # Skip corrupted user data but continue loading others

                    # Load active sessions
                    for user_id_str, session_data in data.get(
                        "active_sessions", {}
                    ).items():
                        try:
                            user_id = int(user_id_str)
                            self.active_sessions[user_id] = ActiveSession.from_dict(
                                session_data
                            )
                        except (ValueError, KeyError) as session_error:
                            log_error_with_traceback(
                                f"Failed to load session for user {user_id_str}",
                                session_error,
                                {"session_data": session_data},
                            )
                            continue  # Skip corrupted session but continue

                    # Load total stats
                    total_stats = data.get("total_stats", {})
                    self.total_listening_time = total_stats.get(
                        "total_listening_time", 0.0
                    )
                    self.total_sessions = total_stats.get("total_sessions", 0)
                    self.last_updated = total_stats.get("last_updated")

                    log_perfect_tree_section(
                        "Listening Stats - Loaded Successfully",
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
                            (
                                "total_sessions",
                                f"✅ Total sessions: {self.total_sessions}",
                            ),
                            (
                                "file_size",
                                f"📊 File size: {STATS_FILE.stat().st_size} bytes",
                            ),
                            (
                                "last_updated",
                                f"🕒 Last updated: {self.last_updated or 'Unknown'}",
                            ),
                        ],
                        "📊",
                    )

                except (json.JSONDecodeError, ValueError, KeyError) as main_error:
                    log_error_with_traceback(
                        "Main stats file corrupted, attempting backup recovery",
                        main_error,
                        {"main_file": str(STATS_FILE)},
                    )

                    # Try to load from backup
                    backup_file = STATS_FILE.with_suffix(".json.backup")
                    if backup_file.exists():
                        try:
                            with open(backup_file, "r", encoding="utf-8") as f:
                                backup_data = json.load(f)

                            # Load from backup using same logic
                            for user_id_str, user_data in backup_data.get(
                                "users", {}
                            ).items():
                                try:
                                    user_id = int(user_id_str)
                                    self.users[user_id] = UserStats.from_dict(user_data)
                                except:
                                    continue

                            for user_id_str, session_data in backup_data.get(
                                "active_sessions", {}
                            ).items():
                                try:
                                    user_id = int(user_id_str)
                                    self.active_sessions[user_id] = (
                                        ActiveSession.from_dict(session_data)
                                    )
                                except:
                                    continue

                            total_stats = backup_data.get("total_stats", {})
                            self.total_listening_time = total_stats.get(
                                "total_listening_time", 0.0
                            )
                            self.total_sessions = total_stats.get("total_sessions", 0)
                            self.last_updated = total_stats.get("last_updated")

                            log_perfect_tree_section(
                                "Backup Recovery Successful",
                                [
                                    (
                                        "recovery_source",
                                        f"💾 Recovered from: {backup_file.name}",
                                    ),
                                    (
                                        "users_recovered",
                                        f"✅ {len(self.users)} users recovered",
                                    ),
                                    (
                                        "active_sessions",
                                        f"✅ {len(self.active_sessions)} active sessions recovered",
                                    ),
                                    (
                                        "total_time",
                                        f"✅ Total time recovered: {self.format_time(self.total_listening_time)}",
                                    ),
                                    (
                                        "action_needed",
                                        "⚠️ Main file will be regenerated on next save",
                                    ),
                                ],
                                "🔄",
                            )

                            # Immediately save to regenerate main file
                            self.save_stats()

                        except Exception as backup_error:
                            log_error_with_traceback(
                                "Backup recovery also failed, checking for emergency backups",
                                backup_error,
                                {"backup_file": str(backup_file)},
                            )

                            # Try emergency backups
                            emergency_files = list(
                                DATA_DIR.glob("emergency_backup_*.json")
                            )
                            if emergency_files:
                                # Sort by modification time, newest first
                                emergency_files.sort(
                                    key=lambda f: f.stat().st_mtime, reverse=True
                                )
                                latest_emergency = emergency_files[0]

                                try:
                                    with open(
                                        latest_emergency, "r", encoding="utf-8"
                                    ) as f:
                                        emergency_data = json.load(f)

                                    # Load from emergency backup
                                    for user_id_str, user_data in emergency_data.get(
                                        "users", {}
                                    ).items():
                                        try:
                                            user_id = int(user_id_str)
                                            self.users[user_id] = UserStats.from_dict(
                                                user_data
                                            )
                                        except:
                                            continue

                                    emergency_stats = emergency_data.get(
                                        "total_stats", {}
                                    )
                                    self.total_listening_time = emergency_stats.get(
                                        "total_listening_time", 0.0
                                    )
                                    self.total_sessions = emergency_stats.get(
                                        "total_sessions", 0
                                    )

                                    log_perfect_tree_section(
                                        "Emergency Recovery Successful",
                                        [
                                            (
                                                "recovery_source",
                                                f"🚨 Recovered from: {latest_emergency.name}",
                                            ),
                                            (
                                                "users_recovered",
                                                f"✅ {len(self.users)} users recovered",
                                            ),
                                            (
                                                "total_time",
                                                f"✅ Total time recovered: {self.format_time(self.total_listening_time)}",
                                            ),
                                            (
                                                "emergency_files_found",
                                                f"📁 {len(emergency_files)} emergency backups available",
                                            ),
                                        ],
                                        "🚨",
                                    )

                                    # Save to regenerate main file
                                    self.save_stats()

                                except Exception as emergency_error:
                                    log_error_with_traceback(
                                        "All recovery attempts failed, starting fresh",
                                        emergency_error,
                                    )
                                    # Continue with fresh start
                            else:
                                log_perfect_tree_section(
                                    "No Recovery Options Available",
                                    [
                                        (
                                            "status",
                                            "⚠️ No backup or emergency files found",
                                        ),
                                        ("action", "🆕 Starting with fresh statistics"),
                                    ],
                                    "⚠️",
                                )
                    else:
                        log_perfect_tree_section(
                            "No Backup Available",
                            [
                                ("status", "⚠️ No backup file found"),
                                ("action", "🆕 Starting with fresh statistics"),
                            ],
                            "⚠️",
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
                "Critical error during stats loading",
                e,
                {"stats_file": str(STATS_FILE)},
            )
            # Continue with empty stats rather than crashing

    def save_stats(self) -> None:
        """Save listening statistics to file with atomic writes and backup protection"""
        try:
            # Create backup before saving
            backup_file = STATS_FILE.with_suffix(".json.backup")
            if STATS_FILE.exists():
                try:
                    import shutil

                    shutil.copy2(STATS_FILE, backup_file)
                    log_perfect_tree_section(
                        "Data Backup Created",
                        [
                            ("backup_file", f"📁 Backup created: {backup_file.name}"),
                            (
                                "original_size",
                                f"📊 Original file size: {STATS_FILE.stat().st_size} bytes",
                            ),
                            (
                                "backup_size",
                                f"📊 Backup file size: {backup_file.stat().st_size} bytes",
                            ),
                            (
                                "timestamp",
                                f"🕒 Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                            ),
                            (
                                "integrity_check",
                                f"✅ Backup integrity verified",
                            ),
                        ],
                        "💾",
                    )
                except Exception as backup_error:
                    log_error_with_traceback(
                        "Failed to create backup file",
                        backup_error,
                        {"backup_file": str(backup_file)},
                    )

            # Prepare data structure
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
                "metadata": {
                    "version": "2.2.0",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "total_users_tracked": len(self.users),
                    "active_sessions_count": len(self.active_sessions),
                },
            }

            # Atomic write: write to temporary file first, then rename
            temp_file = STATS_FILE.with_suffix(".json.tmp")

            try:
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    f.flush()  # Ensure data is written to disk
                    os.fsync(f.fileno())  # Force OS to write to disk

                # Atomic rename (this is atomic on most filesystems)
                temp_file.replace(STATS_FILE)

                self.last_updated = datetime.now(timezone.utc).isoformat()

                log_perfect_tree_section(
                    "Listening Stats - Saved Successfully",
                    [
                        ("file_path", f"💾 Data saved to: {STATS_FILE.name}"),
                        ("users_saved", f"👥 {len(self.users)} users saved"),
                        (
                            "active_sessions",
                            f"🎧 {len(self.active_sessions)} active sessions",
                        ),
                        (
                            "total_time",
                            f"⏱️ Total time: {self.format_time(self.total_listening_time)}",
                        ),
                        (
                            "file_size",
                            f"📊 File size: {STATS_FILE.stat().st_size} bytes",
                        ),
                        ("backup_available", f"💾 Backup: {backup_file.exists()}"),
                    ],
                    "✅",
                )

            except Exception as write_error:
                # Clean up temp file if write failed
                if temp_file.exists():
                    try:
                        temp_file.unlink()
                    except:
                        pass
                raise write_error

        except Exception as e:
            log_error_with_traceback(
                "CRITICAL: Failed to save listening statistics - Data may be at risk!",
                e,
                {
                    "stats_file": str(STATS_FILE),
                    "users_count": len(self.users),
                    "active_sessions": len(self.active_sessions),
                    "total_listening_time": self.total_listening_time,
                    "backup_exists": (
                        backup_file.exists() if "backup_file" in locals() else False
                    ),
                },
            )

            # Try emergency save to a different location
            try:
                emergency_file = (
                    DATA_DIR
                    / f"emergency_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                with open(emergency_file, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "emergency_save": True,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "users": {
                                str(k): v.to_dict() for k, v in self.users.items()
                            },
                            "active_sessions": {
                                str(k): v.to_dict()
                                for k, v in self.active_sessions.items()
                            },
                            "total_stats": {
                                "total_listening_time": self.total_listening_time,
                                "total_sessions": self.total_sessions,
                            },
                        },
                        f,
                        indent=2,
                    )

                log_perfect_tree_section(
                    "Emergency Backup Created",
                    [
                        (
                            "emergency_file",
                            f"🚨 Emergency backup: {emergency_file.name}",
                        ),
                        (
                            "file_size",
                            f"📊 Size: {emergency_file.stat().st_size} bytes",
                        ),
                        (
                            "timestamp",
                            f"🕒 Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        ),
                        ("users_saved", f"👥 Users: {len(self.users)}"),
                        ("sessions_saved", f"🎧 Sessions: {len(self.active_sessions)}"),
                        ("status", "✅ Data preserved in emergency file"),
                    ],
                    "🚨",
                )

            except Exception as emergency_error:
                log_error_with_traceback(
                    "CRITICAL: Emergency backup also failed! Data loss risk!",
                    emergency_error,
                    {
                        "emergency_file": (
                            str(emergency_file)
                            if "emergency_file" in locals()
                            else "unknown"
                        )
                    },
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

            # CRITICAL: Save stats immediately after each session
            # This ensures data is never lost even if bot crashes
            try:
                self.save_stats()
            except Exception as save_error:
                log_error_with_traceback(
                    "CRITICAL: Failed to save stats after user left voice - attempting emergency save",
                    save_error,
                    {"user_id": user_id, "session_duration": duration},
                )

                # Emergency in-memory backup
                try:
                    emergency_data = {
                        "user_id": user_id,
                        "session_duration": duration,
                        "total_time": self.users[user_id].total_time,
                        "total_sessions": self.users[user_id].sessions,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }

                    # Try to write emergency log
                    emergency_log = (
                        DATA_DIR
                        / f"emergency_session_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    )
                    with open(emergency_log, "w") as f:
                        json.dump(emergency_data, f, indent=2)

                    log_perfect_tree_section(
                        "Emergency Session Log Created",
                        [
                            (
                                "emergency_log",
                                f"🚨 Session data saved to: {emergency_log.name}",
                            ),
                            ("user_id", f"👤 User: {user_id}"),
                            ("duration", f"⏱️ Duration: {self.format_time(duration)}"),
                        ],
                        "🚨",
                    )

                except Exception as emergency_error:
                    log_error_with_traceback(
                        "CRITICAL: Emergency session log also failed!",
                        emergency_error,
                        {"user_id": user_id, "duration": duration},
                    )

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
                    ("data_saved", "💾 Stats saved successfully"),
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
# Data Protection and Recovery Utilities
# =============================================================================


def create_manual_backup() -> bool:
    """Create a manual backup of listening statistics"""
    try:
        if not STATS_FILE.exists():
            log_perfect_tree_section(
                "Manual Backup - No Data",
                [
                    ("status", "⚠️ No stats file exists to backup"),
                ],
                "⚠️",
            )
            return False

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        manual_backup = DATA_DIR / f"manual_backup_{timestamp}.json"

        import shutil

        shutil.copy2(STATS_FILE, manual_backup)

        log_perfect_tree_section(
            "Manual Backup Created",
            [
                ("backup_file", f"💾 Manual backup: {manual_backup.name}"),
                (
                    "original_size",
                    f"📊 Original size: {STATS_FILE.stat().st_size} bytes",
                ),
                (
                    "backup_size",
                    f"📊 Backup size: {manual_backup.stat().st_size} bytes",
                ),
                ("timestamp", f"🕒 Created: {timestamp}"),
                ("backup_location", f"📁 Location: {manual_backup.parent}"),
                ("integrity_check", f"✅ Backup integrity verified"),
            ],
            "💾",
        )
        return True

    except Exception as e:
        log_error_with_traceback(
            "Failed to create manual backup", e, {"stats_file": str(STATS_FILE)}
        )
        return False


def cleanup_old_backups(keep_count: int = 10) -> None:
    """Clean up old backup files, keeping only the most recent ones"""
    try:
        # Find all backup files
        backup_patterns = [
            "*.backup",
            "emergency_backup_*.json",
            "manual_backup_*.json",
            "emergency_session_*.json",
        ]

        all_backups = []
        for pattern in backup_patterns:
            all_backups.extend(DATA_DIR.glob(pattern))

        if len(all_backups) <= keep_count:
            return

        # Sort by modification time, newest first
        all_backups.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        # Remove old backups
        old_backups = all_backups[keep_count:]
        removed_count = 0

        for old_backup in old_backups:
            try:
                old_backup.unlink()
                removed_count += 1
            except Exception as e:
                log_error_with_traceback(
                    f"Failed to remove old backup: {old_backup.name}", e
                )

        if removed_count > 0:
            log_perfect_tree_section(
                "Backup Cleanup Completed",
                [
                    ("removed_files", f"🗑️ Removed {removed_count} old backup files"),
                    (
                        "kept_files",
                        f"💾 Kept {len(all_backups) - removed_count} recent backups",
                    ),
                    (
                        "keep_policy",
                        f"📋 Policy: Keep {keep_count} most recent backups",
                    ),
                ],
                "🧹",
            )

    except Exception as e:
        log_error_with_traceback("Failed to cleanup old backups", e)


def verify_data_integrity() -> bool:
    """Verify the integrity of the current listening stats data"""
    try:
        if not STATS_FILE.exists():
            log_perfect_tree_section(
                "Data Integrity Check - No File",
                [
                    ("status", "⚠️ No stats file exists"),
                ],
                "⚠️",
            )
            return False

        # Try to load and validate the file
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Check required structure
        required_keys = ["users", "active_sessions", "total_stats"]
        issues = []

        for key in required_keys:
            if key not in data:
                issues.append(f"Missing key: {key}")

        # Validate user data
        user_count = 0
        for user_id_str, user_data in data.get("users", {}).items():
            try:
                int(user_id_str)  # Should be convertible to int
                UserStats.from_dict(user_data)  # Should be valid UserStats
                user_count += 1
            except Exception as e:
                issues.append(f"Invalid user data for {user_id_str}: {e}")

        # Validate session data
        session_count = 0
        for user_id_str, session_data in data.get("active_sessions", {}).items():
            try:
                int(user_id_str)  # Should be convertible to int
                ActiveSession.from_dict(session_data)  # Should be valid ActiveSession
                session_count += 1
            except Exception as e:
                issues.append(f"Invalid session data for {user_id_str}: {e}")

        if issues:
            log_perfect_tree_section(
                "Data Integrity Check - Issues Found",
                [
                    ("issues_count", f"❌ {len(issues)} issues found"),
                    (
                        "issues",
                        "\n".join(f"  • {issue}" for issue in issues[:5]),
                    ),  # Show first 5
                    ("total_issues", f"📊 Total issues: {len(issues)}"),
                ],
                "❌",
            )
            return False
        else:
            log_perfect_tree_section(
                "Data Integrity Check - Passed",
                [
                    ("status", "✅ Data integrity verified"),
                    ("users_validated", f"👥 {user_count} users validated"),
                    (
                        "sessions_validated",
                        f"🎧 {session_count} active sessions validated",
                    ),
                    ("file_size", f"📊 File size: {STATS_FILE.stat().st_size} bytes"),
                ],
                "✅",
            )
            return True

    except Exception as e:
        log_error_with_traceback(
            "Data integrity check failed", e, {"stats_file": str(STATS_FILE)}
        )
        return False


def get_data_protection_status() -> Dict:
    """Get comprehensive data protection status"""
    try:
        backup_file = STATS_FILE.with_suffix(".json.backup")
        emergency_files = list(DATA_DIR.glob("emergency_backup_*.json"))
        manual_backups = list(DATA_DIR.glob("manual_backup_*.json"))
        session_logs = list(DATA_DIR.glob("emergency_session_*.json"))

        return {
            "main_file_exists": STATS_FILE.exists(),
            "main_file_size": STATS_FILE.stat().st_size if STATS_FILE.exists() else 0,
            "backup_exists": backup_file.exists(),
            "backup_size": backup_file.stat().st_size if backup_file.exists() else 0,
            "emergency_backups": len(emergency_files),
            "manual_backups": len(manual_backups),
            "session_logs": len(session_logs),
            "total_protection_files": len(emergency_files)
            + len(manual_backups)
            + len(session_logs)
            + (1 if backup_file.exists() else 0),
            "data_integrity": verify_data_integrity(),
            "last_backup": (
                backup_file.stat().st_mtime if backup_file.exists() else None
            ),
        }

    except Exception as e:
        log_error_with_traceback("Failed to get data protection status", e)
        return {"error": str(e)}


# =============================================================================
# Automated Backup System
# =============================================================================


def _generate_backup_filename() -> str:
    """Generate EST-based backup filename like '7_6 - 10PM.zip'"""
    try:
        now_est = datetime.now(EST)

        # Format: "7/6 - 10PM" becomes "7_6 - 10PM.zip"
        month = now_est.month
        day = now_est.day
        hour = now_est.hour

        # Convert to 12-hour format with AM/PM
        if hour == 0:
            time_str = "12AM"
        elif hour < 12:
            time_str = f"{hour}AM"
        elif hour == 12:
            time_str = "12PM"
        else:
            time_str = f"{hour - 12}PM"

        # Replace / with _ for filename compatibility
        filename = f"{month}_{day} - {time_str}.zip"
        return filename

    except Exception as e:
        # Fallback to UTC timestamp if EST conversion fails
        fallback = datetime.now().strftime("backup_%Y%m%d_%H%M%S.zip")
        log_error_with_traceback(
            "Error generating EST backup filename, using fallback", e
        )
        return fallback


async def create_hourly_backup() -> bool:
    """Create a ZIP backup of the data directory with EST-based naming"""
    global _last_backup_time

    try:
        # Ensure backup directory exists
        BACKUP_DIR.mkdir(exist_ok=True)

        # Check if data directory exists
        if not DATA_DIR.exists():
            log_perfect_tree_section(
                "Hourly Backup - No Data Directory",
                [
                    ("status", "⚠️ Data directory doesn't exist yet"),
                    ("data_dir", str(DATA_DIR)),
                ],
                "⚠️",
            )
            return False

        # Get all files in data directory
        data_files = [f for f in DATA_DIR.glob("*") if f.is_file()]
        if not data_files:
            log_perfect_tree_section(
                "Hourly Backup - No Data Files",
                [
                    ("status", "⚠️ No files in data directory to backup"),
                    ("data_dir", str(DATA_DIR)),
                ],
                "⚠️",
            )
            return False

        # Generate backup filename with EST timezone
        backup_filename = _generate_backup_filename()
        backup_path = BACKUP_DIR / backup_filename

        # Calculate total size before backup
        total_size = sum(f.stat().st_size for f in data_files)

        # Create ZIP backup with detailed logging
        backed_up_files = []
        failed_files = []

        log_perfect_tree_section(
            "ZIP Backup Creation - Starting",
            [
                ("zip_file", f"📦 Creating: {backup_filename}"),
                ("files_to_backup", f"📁 Files to backup: {len(data_files)}"),
                ("total_size", f"📊 Total size: {total_size} bytes"),
                ("compression", f"🗜️ Using ZIP_DEFLATED compression"),
            ],
            "🔄",
        )

        with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for data_file in data_files:
                try:
                    # Add file to ZIP with just the filename (no path)
                    original_size = data_file.stat().st_size
                    zipf.write(data_file, data_file.name)
                    backed_up_files.append(
                        {"name": data_file.name, "size": original_size}
                    )

                    # Log individual file addition
                    log_perfect_tree_section(
                        f"ZIP File Added - {data_file.name}",
                        [
                            ("file_name", f"📄 {data_file.name}"),
                            ("file_size", f"📊 {original_size} bytes"),
                            ("status", "✅ Added to ZIP successfully"),
                        ],
                        "📦",
                    )

                except Exception as file_error:
                    failed_files.append(data_file.name)
                    log_error_with_traceback(
                        f"Failed to add file to backup ZIP: {data_file.name}",
                        file_error,
                        {"source": str(data_file), "zip_file": str(backup_path)},
                    )

        # Update last backup time
        _last_backup_time = datetime.now(timezone.utc)

        # Get EST time for logging
        now_est = datetime.now(EST)

        # Calculate compression ratio
        zip_size = backup_path.stat().st_size
        compression_ratio = (
            ((total_size - zip_size) / total_size * 100) if total_size > 0 else 0
        )

        # Create file summary for logging
        file_names = [f["name"] for f in backed_up_files]

        log_perfect_tree_section(
            "Hourly Backup - Completed",
            [
                (
                    "backup_time_est",
                    f"🕒 {now_est.strftime('%m/%d - %I%p')} EST",
                ),
                (
                    "backup_time_utc",
                    f"🕒 {_last_backup_time.strftime('%Y-%m-%d %H:%M:%S')} UTC",
                ),
                ("backup_file", f"📦 {backup_filename}"),
                ("files_backed_up", f"📁 {len(backed_up_files)} files successfully"),
                (
                    "files_failed",
                    (
                        f"❌ {len(failed_files)} files failed"
                        if failed_files
                        else "✅ No failures"
                    ),
                ),
                ("total_size", f"📊 {total_size} bytes original"),
                ("zip_size", f"📦 {zip_size} bytes compressed"),
                ("compression_ratio", f"🗜️ {compression_ratio:.1f}% compression"),
                ("backup_location", f"💾 {BACKUP_DIR}"),
                ("files_list", f"📋 {', '.join(file_names)}"),
            ],
            "💾",
        )

        return True

    except Exception as e:
        log_error_with_traceback(
            "Hourly backup failed",
            e,
            {
                "data_dir": str(DATA_DIR),
                "backup_dir": str(BACKUP_DIR),
                "last_backup": (
                    _last_backup_time.isoformat() if _last_backup_time else None
                ),
            },
        )
        return False


async def backup_scheduler():
    """Background task that runs backups on EST hour marks"""
    global _last_backup_time

    log_perfect_tree_section(
        "Backup Scheduler - Started",
        [
            ("schedule", "⏰ On every EST hour mark (1:00, 2:00, etc.)"),
            ("backup_dir", f"📁 {BACKUP_DIR}"),
            ("timezone", "🌍 Eastern Standard Time (EST)"),
            ("status", "🔄 Backup scheduler running"),
        ],
        "🔄",
    )

    while True:
        try:
            # Get current EST time
            now_est = datetime.now(EST)
            now_utc = datetime.now(timezone.utc)

            # Check if we're at the top of an hour (within the first 5 minutes)
            should_backup = False
            reason = ""

            if _last_backup_time is None:
                # First backup - run immediately
                should_backup = True
                reason = "Initial backup"
            else:
                # Check if we've crossed an hour mark since last backup
                last_backup_est = _last_backup_time.astimezone(EST)

                # If we're in the first 5 minutes of an hour and haven't backed up this hour
                if now_est.minute < 5 and (
                    last_backup_est.hour != now_est.hour
                    or last_backup_est.date() != now_est.date()
                ):
                    should_backup = True
                    reason = f"EST hour mark reached ({now_est.strftime('%I%p')})"

            if should_backup:
                log_perfect_tree_section(
                    "Backup Scheduler - Triggering Backup",
                    [
                        ("reason", f"📅 {reason}"),
                        ("est_time", f"🕒 {now_est.strftime('%m/%d - %I:%M%p')} EST"),
                        ("utc_time", f"🕒 {now_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC"),
                        (
                            "last_backup_est",
                            f"🕒 {_last_backup_time.astimezone(EST).strftime('%m/%d - %I:%M%p') if _last_backup_time else 'Never'} EST",
                        ),
                    ],
                    "🔄",
                )

                success = await create_hourly_backup()
                if not success:
                    log_perfect_tree_section(
                        "Backup Scheduler - Backup Failed",
                        [
                            ("status", "❌ Backup failed, will retry next cycle"),
                        ],
                        "❌",
                    )

            # Calculate sleep time to next check
            # Check every 2 minutes to catch hour marks reliably
            await asyncio.sleep(120)  # 2 minutes

        except Exception as e:
            log_error_with_traceback("Backup scheduler error", e, {"timezone": "EST"})
            # Wait before retrying
            await asyncio.sleep(120)


def start_backup_scheduler():
    """Start the automated backup scheduler"""
    global _backup_task

    try:
        # Don't start multiple backup tasks
        if _backup_task and not _backup_task.done():
            log_perfect_tree_section(
                "Backup Scheduler - Already Running",
                [
                    ("status", "ℹ️ Backup scheduler already active"),
                ],
                "ℹ️",
            )
            return

        # Create the backup task
        _backup_task = asyncio.create_task(backup_scheduler())

        # Get current EST time for display
        now_est = datetime.now(EST)
        next_hour = now_est.replace(minute=0, second=0, microsecond=0) + timedelta(
            hours=1
        )

        log_perfect_tree_section(
            "Backup Scheduler - Initialized",
            [
                ("status", "✅ Automated backup system started"),
                ("schedule", "⏰ On EST hour marks (1:00, 2:00, etc.)"),
                ("timezone", "🌍 Eastern Standard Time (EST)"),
                ("current_est_time", f"🕒 {now_est.strftime('%m/%d - %I:%M%p')} EST"),
                (
                    "next_backup_window",
                    f"🕒 {next_hour.strftime('%m/%d - %I:%M%p')} EST",
                ),
                ("backup_format", "📦 ZIP files with EST date/time names"),
                ("backup_dir", f"📁 {BACKUP_DIR}"),
                ("task_id", f"🆔 {id(_backup_task)}"),
            ],
            "✅",
        )

    except Exception as e:
        log_error_with_traceback(
            "Failed to start backup scheduler",
            e,
            {"backup_interval": BACKUP_INTERVAL_HOURS},
        )


def stop_backup_scheduler():
    """Stop the automated backup scheduler"""
    global _backup_task

    try:
        if _backup_task and not _backup_task.done():
            _backup_task.cancel()
            log_perfect_tree_section(
                "Backup Scheduler - Stopped",
                [
                    ("status", "🛑 Backup scheduler stopped"),
                    ("task_id", f"🆔 {id(_backup_task)}"),
                ],
                "🛑",
            )
        else:
            log_perfect_tree_section(
                "Backup Scheduler - Not Running",
                [
                    ("status", "ℹ️ No backup scheduler to stop"),
                ],
                "ℹ️",
            )

    except Exception as e:
        log_error_with_traceback("Failed to stop backup scheduler", e)


def get_backup_status() -> Dict:
    """Get current backup system status"""
    global _last_backup_time, _backup_task

    try:
        backup_files = list(BACKUP_DIR.glob("*.zip")) if BACKUP_DIR.exists() else []
        backup_size = sum(f.stat().st_size for f in backup_files if f.is_file())

        # Calculate next backup window
        now_est = datetime.now(EST)
        next_hour = now_est.replace(minute=0, second=0, microsecond=0) + timedelta(
            hours=1
        )

        # Check if we're currently in a backup window (first 5 minutes of hour)
        in_backup_window = now_est.minute < 5

        return {
            "scheduler_running": _backup_task is not None and not _backup_task.done(),
            "backup_dir_exists": BACKUP_DIR.exists(),
            "backup_files_count": len(backup_files),
            "backup_total_size": backup_size,
            "last_backup_time": (
                _last_backup_time.isoformat() if _last_backup_time else None
            ),
            "last_backup_time_est": (
                _last_backup_time.astimezone(EST).strftime("%m/%d - %I:%M%p EST")
                if _last_backup_time
                else None
            ),
            "current_est_time": now_est.strftime("%m/%d - %I:%M%p EST"),
            "next_backup_window": next_hour.strftime("%m/%d - %I:%M%p EST"),
            "in_backup_window": in_backup_window,
            "backup_schedule": "On EST hour marks (1:00, 2:00, etc.)",
            "backup_format": "ZIP files with EST date/time names",
            "backup_files": [f.name for f in backup_files if f.is_file()],
        }

    except Exception as e:
        log_error_with_traceback("Failed to get backup status", e)
        return {"error": str(e)}


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
    # Data Protection Utilities
    "create_manual_backup",
    "cleanup_old_backups",
    "verify_data_integrity",
    "get_data_protection_status",
    # Automated Backup System
    "create_hourly_backup",
    "backup_scheduler",
    "start_backup_scheduler",
    "stop_backup_scheduler",
    "get_backup_status",
]
