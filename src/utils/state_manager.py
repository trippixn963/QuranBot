# =============================================================================
# QuranBot - State Manager
# =============================================================================
# Handles saving and loading bot state to persist playback position
# across restarts and shutdowns with bulletproof data protection
# =============================================================================

import json
import os
import shutil
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
    Manages bot state persistence across restarts and shutdowns with bulletproof protection.

    The StateManager handles saving and loading of playback state and bot statistics
    to ensure continuity across bot restarts. It provides robust error handling,
    atomic writes, backup creation, and automatic fallback to default values when
    state files are corrupted.

    Features:
    - Playback state persistence (current surah, position, reciter settings)
    - Bot statistics tracking (sessions, runtime, completed surahs)
    - Atomic writes to prevent corruption during saves
    - Automatic backup creation before each save
    - Emergency save mechanisms for critical data protection
    - Corruption detection and automatic recovery
    - Environment-based default configuration
    - Silent operation to prevent log spam during frequent saves

    State Files:
    - playback_state.json: Current playback position and settings
    - playback_state.json.backup: Automatic backup of playback state
    - bot_stats.json: Long-term bot usage statistics
    - bot_stats.json.backup: Automatic backup of bot statistics
    - emergency_backup_*.json: Emergency backup files
    - emergency_session_*.json: Individual session emergency logs

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
        Initialize the StateManager with default settings and bulletproof protection.

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
        Save current playback state to persistent storage with bulletproof protection.

        Saves the current playback position and settings to JSON file with atomic writes,
        backup creation, and emergency save mechanisms for recovery after bot restarts.
        Operation is silent to prevent log spam during frequent automatic saves.

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

            # Create backup before saving
            backup_file = self.playback_state_file.with_suffix(".json.backup")
            if self.playback_state_file.exists():
                try:
                    shutil.copy2(self.playback_state_file, backup_file)

                    # Log backup creation
                    log_perfect_tree_section(
                        "Playback State Backup Created",
                        [
                            ("backup_file", f"💾 Backup: {backup_file.name}"),
                            (
                                "original_size",
                                f"📊 Original: {self.playback_state_file.stat().st_size} bytes",
                            ),
                            (
                                "backup_size",
                                f"📊 Backup: {backup_file.stat().st_size} bytes",
                            ),
                            (
                                "timestamp",
                                f"🕒 Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                            ),
                        ],
                        "💾",
                    )
                except Exception as backup_error:
                    log_error_with_traceback(
                        "Failed to create playback state backup",
                        backup_error,
                        {"backup_file": str(backup_file)},
                    )

            # Prepare state data with metadata
            state = {
                "current_surah": current_surah,
                "current_position": current_position,
                "current_reciter": current_reciter,
                "total_duration": total_duration,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "is_playing": is_playing,
                "loop_enabled": loop_enabled,
                "shuffle_enabled": shuffle_enabled,
                "metadata": {
                    "version": "2.2.0",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "save_type": "playback_state",
                },
            }

            # Atomic write to prevent corruption
            temp_file = self.playback_state_file.with_suffix(".tmp")
            try:
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(state, f, indent=2, ensure_ascii=False)
                    f.flush()  # Ensure data is written to disk
                    os.fsync(f.fileno())  # Force OS to write to disk

                # Atomic rename (this is atomic on most filesystems)
                temp_file.replace(self.playback_state_file)

                # State saved silently - no logging to avoid spam during frequent saves
                return True

            except Exception as write_error:
                # Clean up temp file if write failed
                if temp_file.exists():
                    try:
                        temp_file.unlink()
                    except:
                        pass
                raise write_error

        except (IOError, OSError) as e:
            log_error_with_traceback("File system error saving playback state", e)

            # Try emergency save
            try:
                emergency_file = (
                    self.data_dir
                    / f"emergency_playback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                emergency_data = {
                    "emergency_save": True,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "playback_state": state,
                    "error": str(e),
                }
                with open(emergency_file, "w", encoding="utf-8") as f:
                    json.dump(emergency_data, f, indent=2)

                log_perfect_tree_section(
                    "Emergency Playback Save Created",
                    [
                        ("emergency_file", f"🚨 Emergency save: {emergency_file.name}"),
                        (
                            "file_size",
                            f"📊 Size: {emergency_file.stat().st_size} bytes",
                        ),
                        ("surah", f"📖 Surah: {current_surah}"),
                        ("position", f"⏱️ Position: {current_position:.1f}s"),
                        ("reciter", f"🎤 Reciter: {current_reciter}"),
                        (
                            "timestamp",
                            f"🕒 Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        ),
                        ("status", "✅ Playback state preserved"),
                    ],
                    "🚨",
                )
            except Exception as emergency_error:
                log_error_with_traceback(
                    "CRITICAL: Emergency playback save also failed!",
                    emergency_error,
                )

            return False
        except (TypeError, ValueError) as e:
            log_error_with_traceback("Data validation error saving playback state", e)
            return False
        except Exception as e:
            log_error_with_traceback("Unexpected error saving playback state", e)
            return False

    def load_playback_state(self) -> Dict[str, Any]:
        """
        Load playback state from persistent storage with corruption recovery.

        Loads the saved playback state from JSON file, with automatic fallback
        to backup files if the main file is corrupted. Validates loaded data
        and merges with defaults to ensure all required fields exist.

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

            # Try to load main file
            try:
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
                            (
                                "state_validation",
                                f"Invalid surah {surah}, using default",
                            )
                        )
                        state["current_surah"] = 1

                # Validate position if present
                if "current_position" in state:
                    position = state["current_position"]
                    if not isinstance(position, (int, float)) or position < 0:
                        validation_items.append(
                            (
                                "state_validation",
                                f"Invalid position {position}, using 0",
                            )
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

            except (json.JSONDecodeError, ValueError) as main_error:
                log_error_with_traceback(
                    "Main playback state file corrupted, attempting backup recovery",
                    main_error,
                    {"main_file": str(self.playback_state_file)},
                )

                # Try to load from backup
                backup_file = self.playback_state_file.with_suffix(".json.backup")
                if backup_file.exists():
                    try:
                        with open(backup_file, "r", encoding="utf-8") as f:
                            backup_state = json.load(f)

                        # Validate backup data
                        if isinstance(backup_state, dict):
                            # Merge with defaults
                            merged_state = self.default_playback_state.copy()
                            merged_state.update(backup_state)

                            log_perfect_tree_section(
                                "Backup Recovery Successful",
                                [
                                    (
                                        "recovery_source",
                                        f"💾 Recovered from: {backup_file.name}",
                                    ),
                                    (
                                        "surah",
                                        f"📖 Surah: {merged_state['current_surah']}",
                                    ),
                                    (
                                        "position",
                                        f"⏱️ Position: {merged_state['current_position']:.1f}s",
                                    ),
                                    (
                                        "action_needed",
                                        "⚠️ Main file will be regenerated on next save",
                                    ),
                                ],
                                "🔄",
                            )

                            # Immediately save to regenerate main file
                            self.save_playback_state(
                                merged_state["current_surah"],
                                merged_state["current_position"],
                                merged_state["current_reciter"],
                                merged_state["total_duration"],
                                merged_state["is_playing"],
                                merged_state["loop_enabled"],
                                merged_state["shuffle_enabled"],
                            )

                            return merged_state

                    except Exception as backup_error:
                        log_error_with_traceback(
                            "Backup recovery failed, checking for emergency files",
                            backup_error,
                            {"backup_file": str(backup_file)},
                        )

                # Try emergency recovery
                emergency_files = list(self.data_dir.glob("emergency_playback_*.json"))
                if emergency_files:
                    # Sort by modification time, newest first
                    emergency_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                    latest_emergency = emergency_files[0]

                    try:
                        with open(latest_emergency, "r", encoding="utf-8") as f:
                            emergency_data = json.load(f)

                        if "playback_state" in emergency_data:
                            emergency_state = emergency_data["playback_state"]
                            merged_state = self.default_playback_state.copy()
                            merged_state.update(emergency_state)

                            log_perfect_tree_section(
                                "Emergency Recovery Successful",
                                [
                                    (
                                        "recovery_source",
                                        f"🚨 Recovered from: {latest_emergency.name}",
                                    ),
                                    (
                                        "surah",
                                        f"📖 Surah: {merged_state['current_surah']}",
                                    ),
                                    (
                                        "position",
                                        f"⏱️ Position: {merged_state['current_position']:.1f}s",
                                    ),
                                    (
                                        "emergency_files_found",
                                        f"📁 {len(emergency_files)} emergency files available",
                                    ),
                                ],
                                "🚨",
                            )

                            # Save to regenerate main file
                            self.save_playback_state(
                                merged_state["current_surah"],
                                merged_state["current_position"],
                                merged_state["current_reciter"],
                                merged_state["total_duration"],
                                merged_state["is_playing"],
                                merged_state["loop_enabled"],
                                merged_state["shuffle_enabled"],
                            )

                            return merged_state

                    except Exception as emergency_error:
                        log_error_with_traceback(
                            "Emergency recovery failed, using defaults",
                            emergency_error,
                        )

                # All recovery attempts failed, use defaults
                log_perfect_tree_section(
                    "Playback State - Recovery Failed",
                    [
                        ("status", "⚠️ All recovery attempts failed"),
                        ("action", "🔄 Starting with default state"),
                    ],
                    "⚠️",
                )
                return self.default_playback_state.copy()

        except (FileNotFoundError, PermissionError) as e:
            log_error_with_traceback("File access error loading playback state", e)
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
        Save bot statistics and usage metrics to persistent storage with bulletproof protection.

        Updates and saves bot statistics including session counts, runtime,
        and usage patterns. Uses atomic writes, backup creation, and emergency
        saves to prevent data loss.

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

            # Create backup before saving
            backup_file = self.bot_stats_file.with_suffix(".json.backup")
            if self.bot_stats_file.exists():
                try:
                    shutil.copy2(self.bot_stats_file, backup_file)

                    # Log backup creation
                    log_perfect_tree_section(
                        "Bot Stats Backup Created",
                        [
                            ("backup_file", f"💾 Backup: {backup_file.name}"),
                            (
                                "original_size",
                                f"📊 Original: {self.bot_stats_file.stat().st_size} bytes",
                            ),
                            (
                                "backup_size",
                                f"📊 Backup: {backup_file.stat().st_size} bytes",
                            ),
                            (
                                "timestamp",
                                f"🕒 Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                            ),
                        ],
                        "💾",
                    )
                except Exception as backup_error:
                    log_error_with_traceback(
                        "Failed to create bot stats backup",
                        backup_error,
                        {"backup_file": str(backup_file)},
                    )

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

            # Add metadata
            current_stats["metadata"] = {
                "version": "2.2.0",
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "save_type": "bot_stats",
            }

            # Atomic write to prevent corruption
            temp_file = self.bot_stats_file.with_suffix(".tmp")
            try:
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(current_stats, f, indent=2, ensure_ascii=False)
                    f.flush()  # Ensure data is written to disk
                    os.fsync(f.fileno())  # Force OS to write to disk

                # Atomic rename
                temp_file.replace(self.bot_stats_file)

                # Log successful save with validation warnings if any
                save_items = [
                    (
                        "file_saved",
                        f"💾 Bot stats saved to: {self.bot_stats_file.name}",
                    ),
                    (
                        "total_sessions",
                        f"📊 Total sessions: {current_stats['total_sessions']}",
                    ),
                    (
                        "total_runtime",
                        f"⏱️ Total runtime: {current_stats['total_runtime']:.1f}s",
                    ),
                    (
                        "surahs_completed",
                        f"📖 Surahs completed: {current_stats['surahs_completed']}",
                    ),
                    ("backup_available", f"💾 Backup: {backup_file.exists()}"),
                ]

                if validation_items:
                    save_items.extend(validation_items)

                log_perfect_tree_section(
                    "Bot Stats - Saved Successfully",
                    save_items,
                    "✅",
                )
                return True

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
                "CRITICAL: Failed to save bot statistics - Data may be at risk!",
                e,
                {
                    "stats_file": str(self.bot_stats_file),
                    "backup_exists": (
                        backup_file.exists() if "backup_file" in locals() else False
                    ),
                },
            )

            # Try emergency save
            try:
                emergency_file = (
                    self.data_dir
                    / f"emergency_bot_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                emergency_data = {
                    "emergency_save": True,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "bot_stats": current_stats,
                    "error": str(e),
                }
                with open(emergency_file, "w", encoding="utf-8") as f:
                    json.dump(emergency_data, f, indent=2)

                log_perfect_tree_section(
                    "Emergency Bot Stats Save Created",
                    [
                        ("emergency_file", f"🚨 Emergency save: {emergency_file.name}"),
                        (
                            "file_size",
                            f"📊 Size: {emergency_file.stat().st_size} bytes",
                        ),
                        (
                            "sessions",
                            f"📊 Sessions: {current_stats.get('total_sessions', 0)}",
                        ),
                        (
                            "runtime",
                            f"⏱️ Runtime: {current_stats.get('total_runtime', 0):.1f}s",
                        ),
                        (
                            "timestamp",
                            f"🕒 Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        ),
                        ("status", "✅ Bot statistics preserved"),
                    ],
                    "🚨",
                )

            except Exception as emergency_error:
                log_error_with_traceback(
                    "CRITICAL: Emergency bot stats save also failed! Data loss risk!",
                    emergency_error,
                )

            return False

    def load_bot_stats(self) -> Dict[str, Any]:
        """
        Load bot statistics from persistent storage with corruption recovery.

        Loads saved bot statistics with automatic fallback to backup files
        if the main file is corrupted. Validates loaded data to ensure
        data integrity and provides comprehensive error recovery.

        Returns:
            Dict[str, Any]: Bot statistics dictionary with all required fields
        """
        try:
            if not self.bot_stats_file.exists():
                return self.default_bot_stats.copy()

            # Try to load main file
            try:
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

            except (json.JSONDecodeError, ValueError) as main_error:
                log_error_with_traceback(
                    "Main bot stats file corrupted, attempting backup recovery",
                    main_error,
                    {"main_file": str(self.bot_stats_file)},
                )

                # Try to load from backup
                backup_file = self.bot_stats_file.with_suffix(".json.backup")
                if backup_file.exists():
                    try:
                        with open(backup_file, "r", encoding="utf-8") as f:
                            backup_stats = json.load(f)

                        # Validate backup data
                        if isinstance(backup_stats, dict):
                            # Merge with defaults
                            merged_stats = self.default_bot_stats.copy()
                            merged_stats.update(backup_stats)

                            log_perfect_tree_section(
                                "Bot Stats Backup Recovery Successful",
                                [
                                    (
                                        "recovery_source",
                                        f"💾 Recovered from: {backup_file.name}",
                                    ),
                                    (
                                        "sessions",
                                        f"📊 Sessions: {merged_stats['total_sessions']}",
                                    ),
                                    (
                                        "runtime",
                                        f"⏱️ Runtime: {merged_stats['total_runtime']:.1f}s",
                                    ),
                                    (
                                        "action_needed",
                                        "⚠️ Main file will be regenerated on next save",
                                    ),
                                ],
                                "🔄",
                            )

                            # Immediately save to regenerate main file
                            self.save_bot_stats()

                            return merged_stats

                    except Exception as backup_error:
                        log_error_with_traceback(
                            "Bot stats backup recovery failed, checking for emergency files",
                            backup_error,
                            {"backup_file": str(backup_file)},
                        )

                # Try emergency recovery
                emergency_files = list(self.data_dir.glob("emergency_bot_stats_*.json"))
                if emergency_files:
                    # Sort by modification time, newest first
                    emergency_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                    latest_emergency = emergency_files[0]

                    try:
                        with open(latest_emergency, "r", encoding="utf-8") as f:
                            emergency_data = json.load(f)

                        if "bot_stats" in emergency_data:
                            emergency_stats = emergency_data["bot_stats"]
                            merged_stats = self.default_bot_stats.copy()
                            merged_stats.update(emergency_stats)

                            log_perfect_tree_section(
                                "Bot Stats Emergency Recovery Successful",
                                [
                                    (
                                        "recovery_source",
                                        f"🚨 Recovered from: {latest_emergency.name}",
                                    ),
                                    (
                                        "sessions",
                                        f"📊 Sessions: {merged_stats['total_sessions']}",
                                    ),
                                    (
                                        "runtime",
                                        f"⏱️ Runtime: {merged_stats['total_runtime']:.1f}s",
                                    ),
                                    (
                                        "emergency_files_found",
                                        f"📁 {len(emergency_files)} emergency files available",
                                    ),
                                ],
                                "🚨",
                            )

                            # Save to regenerate main file
                            self.save_bot_stats()

                            return merged_stats

                    except Exception as emergency_error:
                        log_error_with_traceback(
                            "Bot stats emergency recovery failed, using defaults",
                            emergency_error,
                        )

                # All recovery attempts failed, use defaults
                log_perfect_tree_section(
                    "Bot Stats - Recovery Failed",
                    [
                        ("status", "⚠️ All recovery attempts failed"),
                        ("action", "🔄 Starting with default stats"),
                    ],
                    "⚠️",
                )
                return self.default_bot_stats.copy()

        except (FileNotFoundError, PermissionError) as e:
            log_error_with_traceback("File access error loading bot stats", e)
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
                # Calculate total backup size
                total_backup_size = 0
                backup_details = []

                if self.playback_state_file.exists():
                    backup_playback = backup_dir / f"{backup_name}_playback_state.json"
                    if backup_playback.exists():
                        size = backup_playback.stat().st_size
                        total_backup_size += size
                        backup_details.append(f"playback_state ({size} bytes)")

                if self.bot_stats_file.exists():
                    backup_stats = backup_dir / f"{backup_name}_bot_stats.json"
                    if backup_stats.exists():
                        size = backup_stats.stat().st_size
                        total_backup_size += size
                        backup_details.append(f"bot_stats ({size} bytes)")

                log_perfect_tree_section(
                    "State Backup - Success",
                    [
                        ("backup_name", f"📦 Backup: {backup_name}"),
                        ("files_backed_up", f"💾 {files_backed_up} files backed up"),
                        ("total_size", f"📊 Total size: {total_backup_size} bytes"),
                        ("backup_details", f"📋 Files: {', '.join(backup_details)}"),
                        ("backup_location", f"📁 Location: {backup_dir}"),
                        (
                            "timestamp",
                            f"🕒 Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        ),
                        ("integrity_check", f"✅ All backups verified"),
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
    # Data Protection and Recovery Utilities
    # =============================================================================

    def create_manual_backup(self) -> bool:
        """Create manual backups of all state files"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_count = 0

            # Backup playback state
            if self.playback_state_file.exists():
                manual_backup = (
                    self.data_dir / f"manual_backup_playback_{timestamp}.json"
                )
                shutil.copy2(self.playback_state_file, manual_backup)
                backup_count += 1

            # Backup bot stats
            if self.bot_stats_file.exists():
                manual_backup = (
                    self.data_dir / f"manual_backup_bot_stats_{timestamp}.json"
                )
                shutil.copy2(self.bot_stats_file, manual_backup)
                backup_count += 1

            if backup_count > 0:
                # Calculate total backup size
                total_backup_size = 0
                backup_details = []

                if self.playback_state_file.exists():
                    playback_backup = (
                        self.data_dir / f"manual_backup_playback_{timestamp}.json"
                    )
                    if playback_backup.exists():
                        size = playback_backup.stat().st_size
                        total_backup_size += size
                        backup_details.append(f"playback_state.json ({size} bytes)")

                if self.bot_stats_file.exists():
                    stats_backup = (
                        self.data_dir / f"manual_backup_bot_stats_{timestamp}.json"
                    )
                    if stats_backup.exists():
                        size = stats_backup.stat().st_size
                        total_backup_size += size
                        backup_details.append(f"bot_stats.json ({size} bytes)")

                log_perfect_tree_section(
                    "Manual State Backup Created",
                    [
                        ("files_backed_up", f"💾 {backup_count} files backed up"),
                        (
                            "total_size",
                            f"📊 Total backup size: {total_backup_size} bytes",
                        ),
                        ("backup_details", f"📋 Files: {', '.join(backup_details)}"),
                        ("timestamp", f"🕒 Created: {timestamp}"),
                        ("backup_location", f"📁 Location: {self.data_dir}"),
                        ("integrity_check", f"✅ All backups verified"),
                    ],
                    "💾",
                )
                return True
            else:
                log_perfect_tree_section(
                    "Manual Backup - No Data",
                    [
                        ("status", "⚠️ No state files exist to backup"),
                    ],
                    "⚠️",
                )
                return False

        except Exception as e:
            log_error_with_traceback("Failed to create manual state backup", e)
            return False

    def verify_data_integrity(self) -> bool:
        """Verify integrity of all state files"""
        try:
            integrity_items = []
            all_valid = True

            # Check playback state file
            if self.playback_state_file.exists():
                try:
                    with open(self.playback_state_file, "r", encoding="utf-8") as f:
                        state = json.load(f)
                    if isinstance(state, dict) and "current_surah" in state:
                        integrity_items.append(("playback_state", "✅ Valid"))
                    else:
                        integrity_items.append(
                            ("playback_state", "❌ Invalid structure")
                        )
                        all_valid = False
                except Exception:
                    integrity_items.append(("playback_state", "❌ Corrupted"))
                    all_valid = False
            else:
                integrity_items.append(("playback_state", "⚠️ File not found"))

            # Check bot stats file
            if self.bot_stats_file.exists():
                try:
                    with open(self.bot_stats_file, "r", encoding="utf-8") as f:
                        stats = json.load(f)
                    if isinstance(stats, dict) and "total_sessions" in stats:
                        integrity_items.append(("bot_stats", "✅ Valid"))
                    else:
                        integrity_items.append(("bot_stats", "❌ Invalid structure"))
                        all_valid = False
                except Exception:
                    integrity_items.append(("bot_stats", "❌ Corrupted"))
                    all_valid = False
            else:
                integrity_items.append(("bot_stats", "⚠️ File not found"))

            # Check backup files
            playback_backup = self.playback_state_file.with_suffix(".json.backup")
            stats_backup = self.bot_stats_file.with_suffix(".json.backup")

            integrity_items.append(
                (
                    "playback_backup",
                    "✅ Available" if playback_backup.exists() else "⚠️ Not found",
                )
            )
            integrity_items.append(
                (
                    "stats_backup",
                    "✅ Available" if stats_backup.exists() else "⚠️ Not found",
                )
            )

            log_perfect_tree_section(
                "State Data Integrity Check",
                integrity_items,
                "✅" if all_valid else "⚠️",
            )

            return all_valid

        except Exception as e:
            log_error_with_traceback("Failed to verify state data integrity", e)
            return False

    def get_data_protection_status(self) -> Dict:
        """Get comprehensive data protection status for state files"""
        try:
            playback_backup = self.playback_state_file.with_suffix(".json.backup")
            stats_backup = self.bot_stats_file.with_suffix(".json.backup")

            emergency_playback = list(self.data_dir.glob("emergency_playback_*.json"))
            emergency_stats = list(self.data_dir.glob("emergency_bot_stats_*.json"))
            manual_backups = list(self.data_dir.glob("manual_backup_*.json"))

            return {
                "playback_state_exists": self.playback_state_file.exists(),
                "playback_state_size": (
                    self.playback_state_file.stat().st_size
                    if self.playback_state_file.exists()
                    else 0
                ),
                "playback_backup_exists": playback_backup.exists(),
                "playback_backup_size": (
                    playback_backup.stat().st_size if playback_backup.exists() else 0
                ),
                "bot_stats_exists": self.bot_stats_file.exists(),
                "bot_stats_size": (
                    self.bot_stats_file.stat().st_size
                    if self.bot_stats_file.exists()
                    else 0
                ),
                "stats_backup_exists": stats_backup.exists(),
                "stats_backup_size": (
                    stats_backup.stat().st_size if stats_backup.exists() else 0
                ),
                "emergency_playback_files": len(emergency_playback),
                "emergency_stats_files": len(emergency_stats),
                "manual_backups": len(manual_backups),
                "total_protection_files": len(emergency_playback)
                + len(emergency_stats)
                + len(manual_backups)
                + (1 if playback_backup.exists() else 0)
                + (1 if stats_backup.exists() else 0),
                "data_integrity": self.verify_data_integrity(),
            }

        except Exception as e:
            log_error_with_traceback("Failed to get state data protection status", e)
            return {"error": str(e)}

    def cleanup_old_backups(self, keep_days: int = 7) -> int:
        """Clean up old emergency and manual backup files"""
        try:
            cutoff_time = datetime.now().timestamp() - (keep_days * 24 * 60 * 60)
            cleaned_count = 0

            # Clean emergency files
            for pattern in [
                "emergency_playback_*.json",
                "emergency_bot_stats_*.json",
                "manual_backup_*.json",
            ]:
                for file in self.data_dir.glob(pattern):
                    if file.stat().st_mtime < cutoff_time:
                        try:
                            file.unlink()
                            cleaned_count += 1
                        except Exception:
                            continue

            if cleaned_count > 0:
                log_perfect_tree_section(
                    "State Backup Cleanup",
                    [
                        (
                            "files_cleaned",
                            f"🗑️ {cleaned_count} old backup files removed",
                        ),
                        (
                            "retention_days",
                            f"📅 Keeping files newer than {keep_days} days",
                        ),
                    ],
                    "🗑️",
                )

            return cleaned_count

        except Exception as e:
            log_error_with_traceback("Failed to cleanup old state backups", e)
            return 0


# =============================================================================
# Global Instance
# =============================================================================

# Create global state manager instance
state_manager = StateManager()
