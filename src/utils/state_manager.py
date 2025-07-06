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

from .tree_log import log_error_with_traceback, log_tree_branch, log_tree_final

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", ".env")
load_dotenv(env_path)


class StateManager:
    """Manages bot state persistence across restarts"""

    def __init__(
        self,
        data_dir: str = "data",
        default_reciter: str = "Saad Al Ghamdi",
        default_shuffle: bool = False,
        default_loop: bool = False,
    ):
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
        """Save current playback state to JSON file"""
        try:
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

            with open(self.playback_state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)

            log_tree_branch(
                "state_saved", f"Surah {current_surah} at {current_position:.1f}s"
            )
            return True

        except Exception as e:
            log_error_with_traceback("Error saving playback state", e)
            return False

    def load_playback_state(self) -> Dict[str, Any]:
        """Load playback state from JSON file"""
        try:
            if not self.playback_state_file.exists():
                log_tree_branch(
                    "state_default", "No previous state found, using defaults"
                )
                return self.default_playback_state.copy()

            with open(self.playback_state_file, "r", encoding="utf-8") as f:
                state = json.load(f)

            # Validate and merge with defaults
            merged_state = self.default_playback_state.copy()
            merged_state.update(state)

            log_tree_branch(
                "state_loaded",
                f"Surah {merged_state['current_surah']} at {merged_state['current_position']:.1f}s",
            )
            return merged_state

        except Exception as e:
            log_error_with_traceback("Error loading playback state", e)
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
        """Save bot statistics to JSON file"""
        try:
            # Load existing stats or use defaults
            current_stats = self.load_bot_stats()

            # Update provided values
            if total_runtime is not None:
                current_stats["total_runtime"] = total_runtime
            if increment_sessions:
                current_stats["total_sessions"] += 1
            if last_startup:
                current_stats["last_startup"] = last_startup
            if last_shutdown:
                current_stats["last_shutdown"] = last_shutdown
            if increment_completed:
                current_stats["surahs_completed"] += 1
            if favorite_reciter:
                current_stats["favorite_reciter"] = favorite_reciter

            with open(self.bot_stats_file, "w", encoding="utf-8") as f:
                json.dump(current_stats, f, indent=2, ensure_ascii=False)

            log_tree_branch(
                "stats_saved", f"Session #{current_stats['total_sessions']}"
            )
            return True

        except Exception as e:
            log_error_with_traceback("Error saving bot stats", e)
            return False

    def load_bot_stats(self) -> Dict[str, Any]:
        """Load bot statistics from JSON file"""
        try:
            if not self.bot_stats_file.exists():
                return self.default_bot_stats.copy()

            with open(self.bot_stats_file, "r", encoding="utf-8") as f:
                stats = json.load(f)

            # Validate and merge with defaults
            merged_stats = self.default_bot_stats.copy()
            merged_stats.update(stats)

            return merged_stats

        except Exception as e:
            log_error_with_traceback("Error loading bot stats", e)
            return self.default_bot_stats.copy()

    def mark_startup(self) -> bool:
        """Mark bot startup time and increment session count"""
        startup_time = datetime.now(timezone.utc).isoformat()
        return self.save_bot_stats(increment_sessions=True, last_startup=startup_time)

    def mark_shutdown(self) -> bool:
        """Mark bot shutdown time"""
        shutdown_time = datetime.now(timezone.utc).isoformat()
        return self.save_bot_stats(last_shutdown=shutdown_time)

    def mark_surah_completed(self) -> bool:
        """Increment completed surah counter"""
        return self.save_bot_stats(increment_completed=True)

    def get_resume_info(self) -> Dict[str, Any]:
        """Get formatted resume information for logging"""
        state = self.load_playback_state()

        return {
            "surah": state["current_surah"],
            "position": state["current_position"],
            "reciter": state["current_reciter"],
            "duration": state["total_duration"],
            "last_updated": state["last_updated"],
            "should_resume": state["current_position"] > 0,
        }

    def clear_state(self) -> bool:
        """Clear all saved state (useful for fresh start)"""
        try:
            if self.playback_state_file.exists():
                self.playback_state_file.unlink()
            if self.bot_stats_file.exists():
                self.bot_stats_file.unlink()

            log_tree_final("state_cleared", "All saved state cleared")
            return True

        except Exception as e:
            log_error_with_traceback("Error clearing state", e)
            return False

    def backup_state(self, backup_name: str = None) -> bool:
        """Create a backup of current state"""
        try:
            if not backup_name:
                backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            backup_dir = self.data_dir / "backups"
            backup_dir.mkdir(exist_ok=True)

            # Copy state files to backup
            if self.playback_state_file.exists():
                backup_playback = backup_dir / f"{backup_name}_playback_state.json"
                backup_playback.write_text(self.playback_state_file.read_text())

            if self.bot_stats_file.exists():
                backup_stats = backup_dir / f"{backup_name}_bot_stats.json"
                backup_stats.write_text(self.bot_stats_file.read_text())

            log_tree_final("state_backed_up", f"Backup created: {backup_name}")
            return True

        except Exception as e:
            log_error_with_traceback("Error creating state backup", e)
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
