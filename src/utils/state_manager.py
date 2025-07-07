# =============================================================================
# QuranBot - State Manager
# =============================================================================
# Handles saving and loading bot state to persist playback position
# across restarts and shutdowns
# =============================================================================

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

from .tree_log import log_error_with_traceback, log_perfect_tree_section

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", ".env")
load_dotenv(env_path)


class StateManager:
    """
    Manages bot state persistence across restarts and shutdowns.

    The StateManager handles saving and loading of playback state and bot statistics
    to ensure continuity across bot restarts. It provides robust error handling
    and automatic fallback to default values when state files are corrupted.

    Features:
    - Playback state persistence (current surah, position, reciter settings)
    - Bot statistics tracking (sessions, runtime, completed surahs)
    - Automatic backup creation and state recovery
    - Environment-based default configuration
    - Silent operation to prevent log spam during frequent saves

    State Files:
    - playback_state.json: Current playback position and settings
    - bot_stats.json: Long-term bot usage statistics
    - backups/: Timestamped backup copies of state files

    Args:
        data_dir: Directory to store state files (default: "data")
        default_reciter: Default reciter name for new sessions
        default_shuffle: Default shuffle setting for new sessions
        default_loop: Default loop setting for new sessions
    """

    def __init__(
        self,
        data_dir: str = "data",
        default_reciter: str = "Saad Al Ghamdi",
        default_shuffle: bool = False,
        default_loop: bool = False,
    ):
        """
        Initialize the StateManager with default settings.

        Creates the data directory if it doesn't exist and sets up default
        state structures with environment-based configuration values.

        Args:
            data_dir: Directory path for storing state files
            default_reciter: Default reciter for new sessions
            default_shuffle: Default shuffle mode setting
            default_loop: Default loop mode setting
        """
        try:
            self.data_dir = Path(data_dir)
            self.data_dir.mkdir(exist_ok=True)

            # State file paths
            self.playback_state_file = self.data_dir / "playback_state.json"
            self.bot_stats_file = self.data_dir / "bot_stats.json"

            # Default state structure with environment values
            self.default_playback_state = {
                "current_surah": 1,
                "current_position": 0.0,
                "current_reciter": default_reciter,
                "total_duration": 0.0,
                "last_updated": None,
                "is_playing": False,
                "loop_enabled": default_loop,
                "shuffle_enabled": default_shuffle,
            }

            self.default_bot_stats = {
                "total_runtime": 0.0,
                "total_sessions": 0,
                "last_startup": None,
                "last_shutdown": None,
                "surahs_completed": 0,
                "favorite_reciter": default_reciter,
            }

        except Exception as e:
            log_error_with_traceback("Error initializing StateManager", e)
            raise

    def save_playback_state(
        self,
        current_surah: int,
        current_position: float,
        current_reciter: str,
        total_duration: float = 0.0,
        is_playing: bool = True,
        loop_enabled: bool = False,
        shuffle_enabled: bool = False,
    ) -> bool:
        """
        Save current playback state to persistent storage.

        Saves the current playback position and settings to JSON file for
        recovery after bot restarts. Operation is silent to prevent log spam
        during frequent automatic saves.

        Args:
            current_surah: Current surah number (1-114)
            current_position: Current playback position in seconds
            current_reciter: Name of current reciter
            total_duration: Total duration of current track in seconds
            is_playing: Whether audio is currently playing
            loop_enabled: Whether loop mode is enabled
            shuffle_enabled: Whether shuffle mode is enabled

        Returns:
            bool: True if save was successful, False otherwise
        """
        try:
            # Validate input parameters
            if not (1 <= current_surah <= 114):
                log_error_with_traceback(
                    "Invalid surah number in save_playback_state",
                    ValueError(f"Surah number must be 1-114, got {current_surah}"),
                )
                return False

            if current_position < 0:
                current_position = 0.0  # Clamp negative positions

            if total_duration < 0:
                total_duration = 0.0  # Clamp negative durations

            state = {
                "current_surah": current_surah,
                "current_position": current_position,
                "current_reciter": current_reciter,
                "total_duration": total_duration,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "is_playing": is_playing,
                "loop_enabled": loop_enabled,
                "shuffle_enabled": shuffle_enabled,
            }

            # Atomic write to prevent corruption
            temp_file = self.playback_state_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)

            # Move temp file to final location (atomic on most filesystems)
            temp_file.replace(self.playback_state_file)

            # State saved silently - no logging to avoid spam during frequent saves
            return True

        except (IOError, OSError) as e:
            log_error_with_traceback("File system error saving playback state", e)
            return False
        except (TypeError, ValueError) as e:
            log_error_with_traceback("Data validation error saving playback state", e)
            return False
        except Exception as e:
            log_error_with_traceback("Unexpected error saving playback state", e)
            return False

    def load_playback_state(self) -> Dict[str, Any]:
        """
        Load playback state from persistent storage.

        Loads the saved playback state from JSON file, with automatic fallback
        to default values if the file doesn't exist or is corrupted. Validates
        loaded data and merges with defaults to ensure all required fields exist.

        Returns:
            Dict[str, Any]: Playback state dictionary with all required fields
        """
        try:
            if not self.playback_state_file.exists():
                log_perfect_tree_section(
                    "Playback State - Default",
                    [
                        ("state_default", "No previous state found, using defaults"),
                    ],
                    "📁",
                )
                return self.default_playback_state.copy()

            with open(self.playback_state_file, "r", encoding="utf-8") as f:
                state = json.load(f)

            # Validate critical fields
            if not isinstance(state, dict):
                raise ValueError("State file contains invalid data structure")

            validation_items = []

            # Validate surah number if present
            if "current_surah" in state:
                surah = state["current_surah"]
                if not isinstance(surah, int) or not (1 <= surah <= 114):
                    validation_items.append(
                        ("state_validation", f"Invalid surah {surah}, using default")
                    )
                    state["current_surah"] = 1

            # Validate position if present
            if "current_position" in state:
                position = state["current_position"]
                if not isinstance(position, (int, float)) or position < 0:
                    validation_items.append(
                        ("state_validation", f"Invalid position {position}, using 0")
                    )
                    state["current_position"] = 0.0

            # Merge with defaults to ensure all required fields exist
            merged_state = self.default_playback_state.copy()
            merged_state.update(state)

            state_items = [
                (
                    "state_loaded",
                    f"Surah {merged_state['current_surah']} at {merged_state['current_position']:.1f}s",
                ),
            ]

            if validation_items:
                state_items.extend(validation_items)

            log_perfect_tree_section(
                "Playback State - Loaded",
                state_items,
                "✅",
            )
            return merged_state

        except (FileNotFoundError, PermissionError) as e:
            log_error_with_traceback("File access error loading playback state", e)
            return self.default_playback_state.copy()
        except (json.JSONDecodeError, ValueError) as e:
            log_error_with_traceback("Data corruption error loading playback state", e)
            return self.default_playback_state.copy()
        except Exception as e:
            log_error_with_traceback("Unexpected error loading playback state", e)
            return self.default_playback_state.copy()

    def save_bot_stats(
        self,
        total_runtime: float = None,
        increment_sessions: bool = False,
        last_startup: str = None,
        last_shutdown: str = None,
        increment_completed: bool = False,
        favorite_reciter: str = None,
    ) -> bool:
        """
        Save bot statistics and usage metrics to persistent storage.

        Updates and saves bot statistics including session counts, runtime,
        and usage patterns. Uses atomic writes to prevent corruption and
        provides detailed error reporting.

        Args:
            total_runtime: Total bot runtime in seconds (optional)
            increment_sessions: Whether to increment the session counter
            last_startup: ISO timestamp of last startup (optional)
            last_shutdown: ISO timestamp of last shutdown (optional)
            increment_completed: Whether to increment completed surah counter
            favorite_reciter: Name of most-used reciter (optional)

        Returns:
            bool: True if save was successful, False otherwise
        """
        try:
            # Load existing stats or use defaults
            current_stats = self.load_bot_stats()

            validation_items = []

            # Update provided values with validation
            if total_runtime is not None:
                if isinstance(total_runtime, (int, float)) and total_runtime >= 0:
                    current_stats["total_runtime"] = float(total_runtime)
                else:
                    validation_items.append(
                        ("stats_validation", "Invalid runtime value, skipping")
                    )

            if increment_sessions:
                current_stats["total_sessions"] += 1

            if last_startup:
                if isinstance(last_startup, str):
                    current_stats["last_startup"] = last_startup
                else:
                    validation_items.append(
                        ("stats_validation", "Invalid startup timestamp, skipping")
                    )

            if last_shutdown:
                if isinstance(last_shutdown, str):
                    current_stats["last_shutdown"] = last_shutdown
                else:
                    validation_items.append(
                        ("stats_validation", "Invalid shutdown timestamp, skipping")
                    )

            if increment_completed:
                current_stats["surahs_completed"] += 1

            if favorite_reciter:
                if isinstance(favorite_reciter, str) and favorite_reciter.strip():
                    current_stats["favorite_reciter"] = favorite_reciter.strip()
                else:
                    validation_items.append(
                        ("stats_validation", "Invalid reciter name, skipping")
                    )

            # Atomic write to prevent corruption
            temp_file = self.bot_stats_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(current_stats, f, indent=2, ensure_ascii=False)

            # Move temp file to final location
            temp_file.replace(self.bot_stats_file)

            stats_items = [
                ("stats_saved", f"Session #{current_stats['total_sessions']}"),
            ]

            if validation_items:
                stats_items.extend(validation_items)

            log_perfect_tree_section(
                "Bot Stats - Saved",
                stats_items,
                "✅",
            )
            return True

        except (IOError, OSError) as e:
            log_error_with_traceback("File system error saving bot stats", e)
            return False
        except (TypeError, ValueError) as e:
            log_error_with_traceback("Data validation error saving bot stats", e)
            return False
        except Exception as e:
            log_error_with_traceback("Unexpected error saving bot stats", e)
            return False

    def load_bot_stats(self) -> Dict[str, Any]:
        """
        Load bot statistics from persistent storage.

        Loads saved bot statistics with automatic fallback to defaults
        if the file doesn't exist or contains invalid data. Validates
        loaded data to ensure data integrity.

        Returns:
            Dict[str, Any]: Bot statistics dictionary with all required fields
        """
        try:
            if not self.bot_stats_file.exists():
                return self.default_bot_stats.copy()

            with open(self.bot_stats_file, "r", encoding="utf-8") as f:
                stats = json.load(f)

            # Validate data structure
            if not isinstance(stats, dict):
                raise ValueError("Stats file contains invalid data structure")

            # Validate numeric fields
            if "total_sessions" in stats:
                if (
                    not isinstance(stats["total_sessions"], int)
                    or stats["total_sessions"] < 0
                ):
                    stats["total_sessions"] = 0

            if "surahs_completed" in stats:
                if (
                    not isinstance(stats["surahs_completed"], int)
                    or stats["surahs_completed"] < 0
                ):
                    stats["surahs_completed"] = 0

            if "total_runtime" in stats:
                if (
                    not isinstance(stats["total_runtime"], (int, float))
                    or stats["total_runtime"] < 0
                ):
                    stats["total_runtime"] = 0.0

            # Merge with defaults to ensure all required fields exist
            merged_stats = self.default_bot_stats.copy()
            merged_stats.update(stats)

            return merged_stats

        except (FileNotFoundError, PermissionError) as e:
            log_error_with_traceback("File access error loading bot stats", e)
            return self.default_bot_stats.copy()
        except (json.JSONDecodeError, ValueError) as e:
            log_error_with_traceback("Data corruption error loading bot stats", e)
            return self.default_bot_stats.copy()
        except Exception as e:
            log_error_with_traceback("Unexpected error loading bot stats", e)
            return self.default_bot_stats.copy()

    def mark_startup(self) -> bool:
        """
        Record bot startup time and increment session counter.

        Marks the current time as bot startup and increments the total
        session counter for usage tracking.

        Returns:
            bool: True if startup was recorded successfully, False otherwise
        """
        try:
            startup_time = datetime.now(timezone.utc).isoformat()
            return self.save_bot_stats(
                increment_sessions=True, last_startup=startup_time
            )
        except Exception as e:
            log_error_with_traceback("Error marking startup time", e)
            return False

    def mark_shutdown(self) -> bool:
        """
        Record bot shutdown time for usage tracking.

        Marks the current time as bot shutdown for calculating
        session duration and uptime statistics.

        Returns:
            bool: True if shutdown was recorded successfully, False otherwise
        """
        try:
            shutdown_time = datetime.now(timezone.utc).isoformat()
            return self.save_bot_stats(last_shutdown=shutdown_time)
        except Exception as e:
            log_error_with_traceback("Error marking shutdown time", e)
            return False

    def mark_surah_completed(self) -> bool:
        """
        Increment the completed surah counter for usage statistics.

        Tracks the number of surahs that have been played to completion
        for usage analytics and user engagement metrics.

        Returns:
            bool: True if counter was incremented successfully, False otherwise
        """
        try:
            return self.save_bot_stats(increment_completed=True)
        except Exception as e:
            log_error_with_traceback("Error marking surah completion", e)
            return False

    def get_resume_info(self) -> Dict[str, Any]:
        """
        Get formatted resume information for bot startup logging.

        Provides a structured summary of the saved state for display
        during bot initialization, including whether resume is needed.

        Returns:
            Dict[str, Any]: Resume information with playback details
        """
        try:
            state = self.load_playback_state()

            return {
                "surah": state["current_surah"],
                "position": state["current_position"],
                "reciter": state["current_reciter"],
                "duration": state["total_duration"],
                "last_updated": state["last_updated"],
                "should_resume": state["current_position"] > 0,
            }
        except Exception as e:
            log_error_with_traceback("Error getting resume info", e)
            # Return safe defaults
            return {
                "surah": 1,
                "position": 0.0,
                "reciter": "Saad Al Ghamdi",
                "duration": 0.0,
                "last_updated": None,
                "should_resume": False,
            }

    def clear_state(self) -> bool:
        """
        Clear all saved state files for a fresh start.

        Removes all persistent state files including playback state
        and bot statistics. Useful for debugging or clean installations.

        Returns:
            bool: True if state was cleared successfully, False otherwise
        """
        try:
            files_removed = 0

            if self.playback_state_file.exists():
                self.playback_state_file.unlink()
                files_removed += 1

            if self.bot_stats_file.exists():
                self.bot_stats_file.unlink()
                files_removed += 1

            log_perfect_tree_section(
                "State Cleared",
                [
                    ("state_cleared", f"Cleared {files_removed} state files"),
                ],
                "🗑️",
            )
            return True

        except (FileNotFoundError, PermissionError) as e:
            log_error_with_traceback("File access error clearing state", e)
            return False
        except Exception as e:
            log_error_with_traceback("Unexpected error clearing state", e)
            return False

    def backup_state(self, backup_name: str = None) -> bool:
        """
        Create a timestamped backup of current state files.

        Creates backup copies of all state files in a backups subdirectory
        with optional custom naming. Useful for state preservation before
        major updates or troubleshooting.

        Args:
            backup_name: Custom backup name (optional, auto-generated if None)

        Returns:
            bool: True if backup was created successfully, False otherwise
        """
        try:
            if not backup_name:
                backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Validate backup name
            if not isinstance(backup_name, str) or not backup_name.strip():
                raise ValueError("Invalid backup name provided")

            backup_name = backup_name.strip()

            backup_dir = self.data_dir / "backups"
            backup_dir.mkdir(exist_ok=True)

            files_backed_up = 0

            # Copy state files to backup with error handling for each
            if self.playback_state_file.exists():
                try:
                    backup_playback = backup_dir / f"{backup_name}_playback_state.json"
                    backup_playback.write_text(
                        self.playback_state_file.read_text(encoding="utf-8")
                    )
                    files_backed_up += 1
                except Exception as e:
                    log_error_with_traceback("Error backing up playback state", e)

            if self.bot_stats_file.exists():
                try:
                    backup_stats = backup_dir / f"{backup_name}_bot_stats.json"
                    backup_stats.write_text(
                        self.bot_stats_file.read_text(encoding="utf-8")
                    )
                    files_backed_up += 1
                except Exception as e:
                    log_error_with_traceback("Error backing up bot stats", e)

            if files_backed_up > 0:
                log_perfect_tree_section(
                    "State Backup - Success",
                    [
                        (
                            "state_backed_up",
                            f"Backup '{backup_name}': {files_backed_up} files",
                        ),
                    ],
                    "💾",
                )
                return True
            else:
                log_perfect_tree_section(
                    "State Backup - Warning",
                    [
                        ("backup_warning", "No state files found to backup"),
                    ],
                    "⚠️",
                )
                return False

        except (IOError, OSError) as e:
            log_error_with_traceback("File system error creating backup", e)
            return False
        except ValueError as e:
            log_error_with_traceback("Validation error creating backup", e)
            return False
        except Exception as e:
            log_error_with_traceback("Unexpected error creating backup", e)
            return False


# =============================================================================
# Global State Manager Instance
# =============================================================================

# Create global instance with environment defaults
DEFAULT_RECITER = os.getenv("DEFAULT_RECITER", "Saad Al Ghamdi")
DEFAULT_SHUFFLE = os.getenv("DEFAULT_SHUFFLE", "false").lower() == "true"
DEFAULT_LOOP = os.getenv("DEFAULT_LOOP", "false").lower() == "true"

state_manager = StateManager(
    default_reciter=DEFAULT_RECITER,
    default_shuffle=DEFAULT_SHUFFLE,
    default_loop=DEFAULT_LOOP,
)
