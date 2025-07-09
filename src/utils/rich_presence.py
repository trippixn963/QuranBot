#!/usr/bin/env python3
# =============================================================================
# QuranBot - Rich Presence Manager
# =============================================================================
# Manages Discord rich presence functionality
# =============================================================================

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Union

import discord
import pytz

from .tree_log import log_error_with_traceback, log_perfect_tree_section


def validate_rich_presence_dependencies() -> bool:
    """Validate that all required dependencies for rich presence are available"""
    try:
        import discord

        return True
    except ImportError:
        log_error_with_traceback(
            "Missing discord.py dependency",
            ImportError("discord.py is required for rich presence functionality"),
        )
        return False


class RichPresenceManager:
    """Manages Discord rich presence functionality"""

    ACTIVITY_TYPES = {
        "playing": discord.ActivityType.playing,
        "streaming": discord.ActivityType.streaming,
        "listening": discord.ActivityType.listening,
        "watching": discord.ActivityType.watching,
        "competing": discord.ActivityType.competing,
    }

    PRESENCE_TEMPLATES = {
        "listening": {
            "status": "{emoji} {surah} ・ {playback_time}",  # Added playback time with ・ separator
            "details": "Verse {verse} of {total}",
            "state": "Recited by {reciter}",
        },
        "reading": {
            "status": "Reading Quran",
            "details": "{surah} - Verse {verse}",
            "state": "Translation by {translator}",
        },
        "quiz": {
            "status": "Taking a Quiz",
            "details": "Score: {score}",
            "state": "Rank: {rank}",
        },
    }

    def __init__(self, client: discord.Client, data_dir: Union[str, Path]):
        """Initialize the rich presence manager"""
        self.client = client
        self.data_dir = Path(data_dir)
        self.state_file = self.data_dir / "rich_presence_state.json"
        self.is_enabled = True
        self.current_status = ""
        self.current_details = ""
        self.current_state = ""
        self.start_time = None

        # Create data directory if it doesn't exist
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            log_error_with_traceback("Error creating data directory", e)
            # Continue even if directory creation fails
            pass

        # Load existing state
        self.load_state()

    def update_presence(
        self,
        status: str,
        details: str,
        state: str,
        activity_type: str = "playing",
        start_time: Optional[datetime] = None,
        silent: bool = False,
    ) -> bool:
        """Update Discord rich presence"""
        try:
            if not self.is_enabled:
                return True

            if activity_type not in self.ACTIVITY_TYPES:
                log_error_with_traceback(
                    "Invalid activity type",
                    ValueError(
                        f"Activity type must be one of {list(self.ACTIVITY_TYPES.keys())}"
                    ),
                )
                return False

            # Create activity with start time if provided
            activity_kwargs = {
                "type": self.ACTIVITY_TYPES[activity_type],
                "name": status,
                "details": details,
                "state": state,
            }
            if start_time:
                activity_kwargs["start"] = int(start_time.timestamp())
                self.start_time = start_time

            activity = discord.Activity(**activity_kwargs)
            # Schedule the coroutine to be run in the event loop
            if (
                hasattr(self.client, "loop")
                and self.client.loop
                and self.client.loop.is_running()
            ):
                import asyncio

                asyncio.create_task(self.client.change_presence(activity=activity))
            else:
                # Fallback for when loop is not available
                import asyncio

                try:
                    asyncio.get_event_loop().create_task(
                        self.client.change_presence(activity=activity)
                    )
                except RuntimeError:
                    # If no event loop is running, we can't update presence
                    pass
            self.current_status = status
            self.current_details = details
            self.current_state = state
            self.save_state(silent=silent)

            # Only log if not silent
            if not silent:
                log_perfect_tree_section(
                    "Rich Presence Updated",
                    [
                        ("status", status),
                        ("details", details),
                        ("state", state),
                        ("activity", activity_type),
                        ("status", "✅ Updated successfully"),
                    ],
                    "🎮",
                )
            return True
        except Exception as e:
            log_error_with_traceback("Error updating rich presence", e)
            return False

    def update_presence_with_template(
        self,
        template_name: str,
        data: Dict[str, str],
        start_time: Optional[datetime] = None,
        silent: bool = False,
    ) -> bool:
        """Update presence using a predefined template"""
        try:
            if template_name not in self.PRESENCE_TEMPLATES:
                log_error_with_traceback(
                    "Invalid template",
                    ValueError(f"Template {template_name} not found"),
                )
                return False

            template = self.PRESENCE_TEMPLATES[template_name]
            status = self.format_presence_text(template["status"], **data)
            details = self.format_presence_text(template["details"], **data)
            state = self.format_presence_text(template["state"], **data)

            return self.update_presence(
                status=status,
                details=details,
                state=state,
                activity_type=(
                    "listening" if template_name == "listening" else "playing"
                ),
                start_time=start_time,
                silent=silent,
            )
        except Exception as e:
            log_error_with_traceback("Error updating presence with template", e)
            return False

    def format_presence_text(self, template: str, **kwargs) -> str:
        """Format presence text with placeholders"""
        try:
            return template.format(**kwargs)
        except KeyError as e:
            log_error_with_traceback(
                "Missing placeholder in template",
                ValueError(f"Missing required placeholder: {e}"),
            )
            return f"ERROR: Missing {e}"
        except Exception as e:
            log_error_with_traceback("Error formatting presence text", e)
            return "ERROR: Invalid format"

    def toggle_presence(self) -> bool:
        """Toggle rich presence on/off"""
        try:
            self.is_enabled = not self.is_enabled
            if not self.is_enabled:
                self.clear_presence()

            self.save_state()

            log_perfect_tree_section(
                "Rich Presence Toggled",
                [
                    ("enabled", "ON" if self.is_enabled else "OFF"),
                    ("status", "✅ Toggled successfully"),
                ],
                "🔄",
            )
            return True
        except Exception as e:
            log_error_with_traceback("Error toggling rich presence", e)
            return False

    def clear_presence(self) -> bool:
        """Clear rich presence"""
        try:
            # Schedule the coroutine to be run in the event loop
            if (
                hasattr(self.client, "loop")
                and self.client.loop
                and self.client.loop.is_running()
            ):
                import asyncio

                asyncio.create_task(self.client.change_presence(activity=None))
            else:
                # Fallback for when loop is not available
                import asyncio

                try:
                    asyncio.get_event_loop().create_task(
                        self.client.change_presence(activity=None)
                    )
                except RuntimeError:
                    # If no event loop is running, we can't update presence
                    pass
            self.current_status = ""
            self.current_details = ""
            self.current_state = ""
            self.start_time = None
            self.save_state()

            log_perfect_tree_section(
                "Rich Presence Cleared",
                [("status", "✅ Cleared successfully")],
                "🧹",
            )
            return True
        except Exception as e:
            log_error_with_traceback("Error clearing rich presence", e)
            return False

    def get_elapsed_time(self) -> Optional[timedelta]:
        """Get elapsed time since presence start"""
        try:
            if not self.start_time:
                return None

            current_time = datetime.now(pytz.UTC)
            return current_time - self.start_time
        except Exception as e:
            log_error_with_traceback("Error getting elapsed time", e)
            return None

    def save_state(self, silent: bool = False) -> bool:
        """Save current state to file"""
        try:
            state = {
                "is_enabled": self.is_enabled,
                "current_status": self.current_status,
                "current_details": self.current_details,
                "current_state": self.current_state,
                "start_time": self.start_time.timestamp() if self.start_time else None,
            }

            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)

            # Only log if not silent
            if not silent:
                log_perfect_tree_section(
                    "Rich Presence State Saved",
                    [
                        ("enabled", "ON" if self.is_enabled else "OFF"),
                        ("status", "✅ State saved successfully"),
                    ],
                    "💾",
                )
            return True
        except Exception as e:
            log_error_with_traceback("Error saving rich presence state", e)
            return False

    def load_state(self) -> bool:
        """Load state from file"""
        try:
            if self.state_file.exists():
                with open(self.state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)

                self.is_enabled = state.get("is_enabled", True)
                self.current_status = state.get("current_status", "")
                self.current_details = state.get("current_details", "")
                self.current_state = state.get("current_state", "")
                start_time = state.get("start_time")
                self.start_time = (
                    datetime.fromtimestamp(start_time, tz=pytz.UTC)
                    if start_time
                    else None
                )

                log_perfect_tree_section(
                    "Rich Presence State Loaded",
                    [
                        ("enabled", "ON" if self.is_enabled else "OFF"),
                        ("status", "✅ State loaded successfully"),
                    ],
                    "📥",
                )
            return True
        except Exception as e:
            log_error_with_traceback("Error loading rich presence state", e)
            return False
