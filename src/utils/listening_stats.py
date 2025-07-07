# =============================================================================
# QuranBot - Listening Statistics Manager
# =============================================================================
# Tracks user voice channel listening time and generates leaderboards
# =============================================================================

import asyncio
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import discord

from .tree_log import log_error_with_traceback, log_perfect_tree_section

# =============================================================================
# Configuration
# =============================================================================

# Path to the listening stats data file
DATA_DIR = Path(__file__).parent.parent.parent / "data"
STATS_FILE = DATA_DIR / "listening_stats.json"

# Temp backup directory for .backup files (keeps data/ clean)
TEMP_BACKUP_DIR = Path(__file__).parent.parent.parent / "backup" / "temp"

# Leaderboard auto-update configuration
LEADERBOARD_UPDATE_INTERVAL = 60  # Update every 60 seconds
LEADERBOARD_CHANNEL_ID = None  # Will be set by bot
LEADERBOARD_UPDATE_TASK = None  # Global task for auto-updates

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
        self.bot = None
        self.leaderboard_channel_id = None
        self.leaderboard_update_task = None
        self.last_leaderboard_message = None
        self.update_counter = 0  # Add counter to reduce log spam
        self.last_logged_active_count = 0  # Track changes in active users

        # Ensure data directory exists
        DATA_DIR.mkdir(exist_ok=True)

        # Ensure temp backup directory exists (keeps data/ clean)
        TEMP_BACKUP_DIR.mkdir(parents=True, exist_ok=True)

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

                    # Try to load from backup (now in temp directory)
                    backup_file = TEMP_BACKUP_DIR / f"{STATS_FILE.stem}.backup"
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
            # Create backup before saving (in temp directory to keep data/ clean)
            backup_file = TEMP_BACKUP_DIR / f"{STATS_FILE.stem}.backup"
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
                                f"🕒 Created: {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}",
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
                    STATS_FILE.parent
                    / f"emergency_session_{user_id}_{datetime.now().strftime('%Y%m%d_%I%M%S_%p')}.json"
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
                            f"🕒 Created: {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}",
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
                        f"⏰ Session started at {datetime.now(timezone.utc).strftime('%I:%M:%S %p')}",
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
                    emergency_file = (
                        STATS_FILE.parent
                        / f"emergency_session_{user_id}_{datetime.now().strftime('%Y%m%d_%I%M%S_%p')}.json"
                    )
                    with open(emergency_file, "w") as f:
                        json.dump(emergency_data, f, indent=2)

                    log_perfect_tree_section(
                        "Emergency Session Log Created",
                        [
                            (
                                "emergency_log",
                                f"🚨 Session data saved to: {emergency_file.name}",
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

    def set_leaderboard_channel(self, bot, channel_id: int):
        """Set up the leaderboard auto-update system"""
        try:
            self.bot = bot
            self.leaderboard_channel_id = channel_id

            # Start the auto-update task
            self.start_leaderboard_updates()

            log_perfect_tree_section(
                "Leaderboard Auto-Update - Setup",
                [
                    ("channel_id", str(channel_id)),
                    ("update_interval", f"{LEADERBOARD_UPDATE_INTERVAL}s"),
                    ("status", "✅ Auto-update system initialized"),
                ],
                "🏆",
            )

        except Exception as e:
            log_error_with_traceback("Failed to set up leaderboard auto-update", e)

    def start_leaderboard_updates(self):
        """Start the automatic leaderboard update task"""
        try:
            # Cancel existing task if running
            if self.leaderboard_update_task and not self.leaderboard_update_task.done():
                self.leaderboard_update_task.cancel()

            # Start new update task
            self.leaderboard_update_task = asyncio.create_task(
                self._leaderboard_update_loop()
            )

            log_perfect_tree_section(
                "Leaderboard Auto-Update - Started",
                [
                    ("status", "✅ Auto-update task started"),
                    ("interval", f"{LEADERBOARD_UPDATE_INTERVAL}s"),
                    ("active_users", len(self.active_sessions)),
                ],
                "🏆",
            )

        except Exception as e:
            log_error_with_traceback("Failed to start leaderboard updates", e)

    async def _leaderboard_update_loop(self):
        """Background task that updates the leaderboard periodically"""
        while True:
            try:
                await asyncio.sleep(LEADERBOARD_UPDATE_INTERVAL)

                # Only update if there are active users
                if (
                    len(self.active_sessions) > 0
                    and self.bot
                    and self.leaderboard_channel_id
                ):
                    await self._update_leaderboard()

            except asyncio.CancelledError:
                break
            except Exception as e:
                log_error_with_traceback("Error in leaderboard update loop", e)

    async def _update_leaderboard(self):
        """Update the leaderboard message"""
        try:
            if not self.bot or not self.leaderboard_channel_id:
                return

            channel = self.bot.get_channel(self.leaderboard_channel_id)
            if not channel:
                return

            # Get current leaderboard data
            leaderboard_data = self.get_leaderboard_data()
            top_users = leaderboard_data["top_users"]

            if not top_users:
                return

            # Create embed
            embed = discord.Embed(
                title="🏆 Quran Listening Leaderboard",
                description="*Top listeners in the Quran voice channel*",
                color=0x00D4AA,
                timestamp=datetime.now(timezone.utc),
            )

            # Medal emojis for top 3
            medal_emojis = {1: "🥇", 2: "🥈", 3: "🥉"}

            leaderboard_text = ""
            for position, (user_id, total_time, sessions) in enumerate(top_users, 1):
                # Get medal emoji or position number
                position_display = medal_emojis.get(position, f"{position}.")

                # Format time
                time_formatted = self.format_time(total_time)

                # Add active indicator if user is currently listening
                active_indicator = " 🎧" if user_id in self.active_sessions else ""

                # Create leaderboard entry with time under the name
                # This solves Arabic text formatting issues by separating directional content
                leaderboard_text += f"{position_display} <@{user_id}>{active_indicator}\n`{time_formatted}`\n\n"

                # Add space after each entry except the last one
                if position < len(top_users):
                    leaderboard_text += "\n"

            embed.description = (
                f"*Top listeners in the Quran voice channel*\n\n{leaderboard_text}"
            )

            # Add stats footer
            embed.add_field(
                name="📊 Server Statistics",
                value=f"**Active Listeners:** {leaderboard_data['active_users']} 🎧\n"
                f"**Total Users:** {leaderboard_data['total_users']} 👥\n"
                f"**Total Sessions:** {leaderboard_data['total_sessions']} 🔢",
                inline=False,
            )

            # Set bot avatar as thumbnail
            if self.bot.user and self.bot.user.avatar:
                embed.set_thumbnail(url=self.bot.user.avatar.url)

            # Set footer
            embed.set_footer(
                text=f"Auto-updated every {LEADERBOARD_UPDATE_INTERVAL}s • {len(self.active_sessions)} active",
                icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None,
            )

            # Delete old message if exists
            if self.last_leaderboard_message:
                try:
                    await self.last_leaderboard_message.delete()
                except:
                    pass  # Message might already be deleted

            # Send new message
            self.last_leaderboard_message = await channel.send(embed=embed)

            # Only log every 10th update or when active user count changes
            self.update_counter += 1
            current_active_count = len(self.active_sessions)

            should_log = (
                self.update_counter % 10 == 0  # Every 10th update
                or current_active_count
                != self.last_logged_active_count  # Active users changed
            )

            if should_log:
                log_perfect_tree_section(
                    "Leaderboard Auto-Update - Updated",
                    [
                        ("users_shown", len(top_users)),
                        ("active_users", current_active_count),
                        ("message_id", str(self.last_leaderboard_message.id)),
                        ("channel", channel.name),
                        ("update_count", f"#{self.update_counter}"),
                    ],
                    "🏆",
                )
                self.last_logged_active_count = current_active_count

        except Exception as e:
            log_error_with_traceback("Failed to update leaderboard", e)

    def stop_leaderboard_updates(self):
        """Stop the automatic leaderboard updates"""
        try:
            if self.leaderboard_update_task and not self.leaderboard_update_task.done():
                self.leaderboard_update_task.cancel()

            log_perfect_tree_section(
                "Leaderboard Auto-Update - Stopped",
                [
                    ("status", "✅ Auto-update task stopped"),
                ],
                "🏆",
            )

        except Exception as e:
            log_error_with_traceback("Failed to stop leaderboard updates", e)


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


def cleanup_old_backups(keep_count: int = 10) -> None:
    """Clean up old backup files, keeping only the most recent ones"""
    try:
        # Find all backup files (excluding manual backups since they're disabled)
        backup_patterns = [
            "*.backup",
            "emergency_backup_*.json",
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
        # Use temp backup directory for .backup files (keeps data/ clean)
        backup_file = TEMP_BACKUP_DIR / f"{STATS_FILE.stem}.backup"
        emergency_files = list(DATA_DIR.glob("emergency_backup_*.json"))
        session_logs = list(DATA_DIR.glob("emergency_session_*.json"))

        return {
            "main_file_exists": STATS_FILE.exists(),
            "main_file_size": STATS_FILE.stat().st_size if STATS_FILE.exists() else 0,
            "backup_exists": backup_file.exists(),
            "backup_size": backup_file.stat().st_size if backup_file.exists() else 0,
            "emergency_backups": len(emergency_files),
            "session_logs": len(session_logs),
            "total_protection_files": len(emergency_files)
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


def set_leaderboard_channel(bot, channel_id: int):
    """Set up the leaderboard auto-update system"""
    listening_stats_manager.set_leaderboard_channel(bot, channel_id)


def start_leaderboard_updates():
    """Start the automatic leaderboard updates"""
    listening_stats_manager.start_leaderboard_updates()


def stop_leaderboard_updates():
    """Stop the automatic leaderboard updates"""
    listening_stats_manager.stop_leaderboard_updates()


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
    # Data Protection Utilities (Listening Stats Only)
    "cleanup_old_backups",
    "verify_data_integrity",
    "get_data_protection_status",
    # Leaderboard Auto-Update Functions
    "set_leaderboard_channel",
    "start_leaderboard_updates",
    "stop_leaderboard_updates",
]
