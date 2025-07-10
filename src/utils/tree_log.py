# =============================================================================
# QuranBot - Tree Style Logging Module (Open Source Edition)
# =============================================================================
# This is an open source project provided AS-IS without official support.
# Feel free to use, modify, and learn from this code under the license terms.
#
# Purpose:
# Professional-grade logging system that creates beautiful, hierarchical logs
# with perfect tree structure, timestamps, and multi-destination output.
# Originally designed for QuranBot but usable in any Python project.
#
# Key Features:
# - Beautiful tree-style log formatting
# - Multi-destination logging (console, files, JSON)
# - Perfect tree structure with proper indentation
# - Timezone-aware timestamps (EST/UTC)
# - Structured JSON log output
# - Emoji support for visual categorization
# - Run ID tracking for session management
#
# Technical Implementation:
# - Stack-based tree structure tracking
# - Atomic file writes for log persistence
# - Timezone handling with pytz
# - JSON serialization for structured logs
# - Unicode symbol management
#
# Log Structure:
# /logs/
#   /YYYY-MM-DD/
#     general.log    - Main log file
#     errors.log     - Error-specific logs
#     activity.log   - User activity tracking
#     discord.log    - Discord-specific events
#
# Required Dependencies:
# - pytz: Timezone handling
# =============================================================================

import json
import os
import secrets
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytz

# Global state tracking for tree structure
_is_first_section = True  # Controls top-level spacing
_tree_stack: List[bool] = []  # Tracks which levels have siblings
_current_depth = 0  # Current nesting level

# Unicode symbols for perfect tree structure
# Modify these to change the visual appearance of the tree
TREE_SYMBOLS = {
    "branch": "├─",  # Node with siblings below
    "last": "└─",  # Last node in current branch
    "pipe": "│ ",  # Vertical continuation line
    "space": "  ",  # Alignment spacing
    "nested_branch": "├─",  # Used in nested structures
    "nested_last": "└─",  # Last node in nested structure
}


class TreeLogger:
    """
    Professional-grade tree-style logging system for Python applications.

    This is an open source component that can be used as a reference for
    implementing beautiful, hierarchical logging in any Python project.

    Key Features:
    - Beautiful tree-style log formatting
    - Perfect hierarchical structure
    - Multi-destination output
    - Timezone-aware timestamps
    - Session tracking with run IDs
    - Structured JSON logging
    - Unicode symbol support

    Log Categories:
    1. General Logs:
       - Application events
       - State changes
       - User interactions

    2. Error Logs:
       - Exceptions with tracebacks
       - Warning messages
       - Critical errors

    3. Activity Logs:
       - User actions
       - System events
       - Performance metrics

    Implementation Notes:
    - Uses stack-based tree tracking
    - Supports nested structures
    - Handles Unicode properly
    - Atomic file writes
    - JSON serialization

    Usage Example:
    ```python
    # Log a simple message
    log_status("Application started", status="INFO", emoji="🚀")

    # Log a tree structure
    log_perfect_tree_section(
        "Initialization",
        [
            ("status", "Starting up"),
            ("version", "1.0.0"),
            ("mode", "production")
        ],
        emoji="🎯"
    )
    ```
    """

    def __init__(self):
        """Initialize the TreeLogger instance."""
        self.log_dir = self._setup_log_directories()
        self.run_id = self._generate_run_id()
        self.current_datetime_iso = self._get_current_datetime_iso()

    def _setup_log_directories(self):
        """Create log directory structure for today."""
        try:
            log_date = self._get_log_date()
            log_dir = Path(f"logs/{log_date}")
            log_dir.mkdir(parents=True, exist_ok=True)
            return log_dir
        except Exception as e:
            print(f"Warning: Could not create log directory: {e}")
            return None

    def _generate_run_id(self):
        """Generate a unique run ID for each bot instance."""
        return secrets.token_hex(4).upper()

    def _get_log_date(self):
        """Get current date for log file naming (YYYY-MM-DD format)."""
        try:
            est = pytz.timezone("US/Eastern")
            now_est = datetime.now(est)
            return now_est.strftime("%Y-%m-%d")
        except:
            return datetime.now().strftime("%Y-%m-%d")

    def _get_current_datetime_iso(self):
        """Get current datetime in ISO format for JSON logs."""
        try:
            est = pytz.timezone("US/Eastern")
            now_est = datetime.now(est)
            return now_est.isoformat()
        except:
            return datetime.now().isoformat()

    def _get_timestamp(self):
        """Get current timestamp in EST timezone with custom format."""
        try:
            # Create EST timezone
            est = pytz.timezone("US/Eastern")
            # Get current time in EST
            now_est = datetime.now(est)
            # Format as MM/DD HH:MM AM/PM EST
            formatted_time = now_est.strftime("%m/%d %I:%M %p EST")
            return f"[{formatted_time}]"
        except ImportError:
            # Fallback if pytz is not available
            now = datetime.now()
            formatted_time = now.strftime("%m/%d %I:%M %p")
            return f"[{formatted_time}]"
        except Exception:
            # Fallback if timezone handling fails
            now = datetime.now()
            formatted_time = now.strftime("%m/%d %I:%M %p")
            return f"[{formatted_time}]"

    def reset_tree_structure(self):
        """Reset the tree structure tracking."""
        global _tree_stack, _current_depth
        _tree_stack = []
        _current_depth = 0

    def get_tree_prefix(self, is_last_item=False, depth_override=None):
        """Generate the proper tree prefix based on current depth and structure."""
        global _tree_stack, _current_depth

        depth = depth_override if depth_override is not None else _current_depth

        if depth == 0:
            return TREE_SYMBOLS["branch"] if not is_last_item else TREE_SYMBOLS["last"]

        prefix = ""
        for i in range(depth):
            if i < len(_tree_stack):
                if _tree_stack[i]:  # This level has more siblings
                    prefix += TREE_SYMBOLS["pipe"]
                else:  # This level is the last item
                    prefix += TREE_SYMBOLS["space"]
            else:
                prefix += TREE_SYMBOLS["space"]

        # Add the current level symbol
        prefix += TREE_SYMBOLS["branch"] if not is_last_item else TREE_SYMBOLS["last"]

        return prefix

    def start_tree_section(self, has_more_siblings=True):
        """Start a new tree section with proper nesting."""
        global _tree_stack, _current_depth

        if _current_depth < len(_tree_stack):
            _tree_stack[_current_depth] = has_more_siblings
        else:
            _tree_stack.append(has_more_siblings)

        _current_depth += 1

    def end_tree_section(self):
        """End the current tree section."""
        global _current_depth
        if _current_depth > 0:
            _current_depth -= 1

    def log_tree_item(self, key, value, is_last=False, depth_override=None):
        """Log a single tree item with proper tree structure."""
        prefix = self.get_tree_prefix(is_last, depth_override)
        message = f"{prefix} {key}: {value}"

        timestamp = self._get_timestamp()
        print(f"{timestamp} {message}")
        self._write_to_log_files(message, "INFO", "tree_item")

    def log_tree_group(self, title, items, emoji="🎯"):
        """Log a group of related items with perfect tree structure."""
        timestamp = self._get_timestamp()

        # Log the group header
        group_header = f"{emoji} {title}"
        print(f"{timestamp} {group_header}")
        self._write_to_log_files(group_header, "INFO", "tree_group")

        # Log each item in the group
        for i, (key, value) in enumerate(items):
            is_last = i == len(items) - 1
            self.log_tree_item(key, value, is_last, depth_override=0)

    def log_nested_tree_group(self, title, items, emoji="🎯", parent_depth=0):
        """Log a nested group with proper indentation."""
        # Calculate prefix for the group title
        prefix = self.get_tree_prefix(is_last_item=False, depth_override=parent_depth)

        timestamp = self._get_timestamp()
        group_header = f"{prefix} {emoji} {title}"
        print(f"{timestamp} {group_header}")
        self._write_to_log_files(group_header, "INFO", "nested_tree_group")

        # Log items with increased depth
        for i, (key, value) in enumerate(items):
            is_last = i == len(items) - 1
            self.log_tree_item(key, value, is_last, depth_override=parent_depth + 1)

    def log_perfect_tree_section(self, title, items, emoji="🎯", nested_groups=None):
        """
        Create a perfect tree structure with proper nesting and visual hierarchy.
        Automatically adds spacing before each section for better readability.

        Args:
            title: Section title
            items: List of (key, value) tuples for main items
            emoji: Emoji for the section header
            nested_groups: Dict of nested groups {group_name: [(key, value), ...]}
        """
        global _is_first_section

        timestamp = self._get_timestamp()

        # Add spacing before section (except for the very first section)
        if not _is_first_section:
            print("")
            self._write_to_log_files("", "INFO", "section_spacing")
        else:
            _is_first_section = False

        # Reset tree structure for this section
        self.reset_tree_structure()

        # Log section header
        section_header = f"{emoji} {title}"
        print(f"{timestamp} {section_header}")
        self._write_to_log_files(section_header, "INFO", "perfect_tree_section")

        # Calculate total items to determine which is last
        total_main_items = len(items) if items else 0
        total_nested_groups = len(nested_groups) if nested_groups else 0
        has_nested = total_nested_groups > 0

        # Log main items
        if items:
            for i, (key, value) in enumerate(items):
                is_last_main = (i == total_main_items - 1) and not has_nested
                self.log_tree_item(key, value, is_last_main, depth_override=0)

        # Log nested groups
        if nested_groups:
            nested_group_keys = list(nested_groups.keys())
            for i, (group_name, group_items) in enumerate(nested_groups.items()):
                is_last_group = i == len(nested_group_keys) - 1

                # Log group header
                group_prefix = self.get_tree_prefix(is_last_group, depth_override=0)
                group_header = f"{group_prefix} 📁 {group_name}"
                print(f"{timestamp} {group_header}")
                self._write_to_log_files(
                    group_header, "INFO", "perfect_tree_nested_group"
                )

                # Log group items with proper nesting
                if group_items:
                    for j, (key, value) in enumerate(group_items):
                        is_last_item = j == len(group_items) - 1

                        # Create nested prefix
                        nested_prefix = ""
                        if not is_last_group:
                            nested_prefix += TREE_SYMBOLS["pipe"]
                        else:
                            nested_prefix += TREE_SYMBOLS["space"]

                        nested_prefix += (
                            TREE_SYMBOLS["last"]
                            if is_last_item
                            else TREE_SYMBOLS["branch"]
                        )

                        nested_message = f"{nested_prefix} {key}: {value}"
                        print(f"{timestamp} {nested_message}")
                        self._write_to_log_files(
                            nested_message, "INFO", "perfect_tree_nested_item"
                        )

    def log_voice_activity_tree(self, user_name, activity_type, details):
        """
        Log voice activity with perfect tree structure for voice channel events.

        Args:
            user_name: Name of the user
            activity_type: Type of voice activity (join, leave, move, etc.)
            details: Dictionary of activity details
        """
        timestamp = self._get_timestamp()

        # Add line breaker for visual separation
        print("")
        self._write_to_log_files("", "INFO", "voice_activity")

        # Create activity header with proper emoji
        activity_emojis = {
            "join": "🎤",
            "leave": "🚪",
            "move": "🔄",
            "mute": "🔇",
            "unmute": "🔊",
            "deafen": "🔇",
            "undeafen": "🔊",
        }

        emoji = activity_emojis.get(activity_type, "🎵")
        activity_header = f"{emoji} Voice Activity - {activity_type.title()}"
        print(f"{timestamp} {activity_header}")
        self._write_to_log_files(activity_header, "INFO", "voice_activity")

        # Log user information
        user_info = f"├─ user: {user_name}"
        print(f"{timestamp} {user_info}")
        self._write_to_log_files(user_info, "INFO", "voice_activity")

        # Log activity details with perfect tree structure
        if details:
            detail_keys = list(details.keys())
            for i, (key, value) in enumerate(details.items()):
                is_last = i == len(detail_keys) - 1
                prefix = "└─" if is_last else "├─"
                detail_line = f"{prefix} {key}: {value}"
                print(f"{timestamp} {detail_line}")
                self._write_to_log_files(detail_line, "INFO", "voice_activity")

        # Add line breaker after activity
        print("")
        self._write_to_log_files("", "INFO", "voice_activity")

    def log_initialization_tree(self, component_name, steps, emoji="🚀"):
        """
        Log initialization process with perfect tree structure.

        Args:
            component_name: Name of the component being initialized
            steps: List of (step_name, status, details) tuples
            emoji: Emoji for the section header
        """
        timestamp = self._get_timestamp()

        # Log initialization header
        init_header = f"{emoji} {component_name} Initialization"
        print(f"{timestamp} {init_header}")
        self._write_to_log_files(init_header, "INFO", "initialization_tree")

        # Log each step with perfect tree structure
        for i, (step_name, status, details) in enumerate(steps):
            is_last = i == len(steps) - 1

            # Determine status emoji
            status_emoji = (
                "✅" if status == "success" else "❌" if status == "error" else "🔄"
            )

            # Log step with status
            prefix = "└─" if is_last else "├─"
            step_line = f"{prefix} {step_name}: {status_emoji} {details}"
            print(f"{timestamp} {step_line}")
            self._write_to_log_files(step_line, "INFO", "initialization_tree")

    def log_run_separator(self):
        """Create a visual separator for new runs."""
        # Reset section tracking for new run
        self.reset_section_tracking()

        separator_line = "=" * 80
        timestamp = self._get_timestamp()

        # Print separator to console
        print(f"\n{separator_line}")
        print(f"{timestamp} 🚀 NEW BOT RUN STARTED")
        print(f"{separator_line}")

        # Write separator to log files
        self._write_to_log_files("", "INFO", "run_separator")
        self._write_to_log_files(separator_line, "INFO", "run_separator")
        self._write_to_log_files("🚀 NEW BOT RUN STARTED", "INFO", "run_separator")
        self._write_to_log_files(separator_line, "INFO", "run_separator")

    def log_run_header(self, bot_name, version, run_id=None):
        """Log run header with bot info and unique run ID."""
        if run_id is None:
            run_id = self.run_id

        timestamp = self._get_timestamp()

        # Create run header
        header_info = [
            f"🎯 {bot_name} v{version} - Run ID: {run_id}",
            f"├─ started_at: {timestamp}",
            f"├─ version: {version}",
            f"├─ run_id: {run_id}",
            f"└─ log_session: {self._get_log_date()}",
        ]

        # Print to console
        for line in header_info:
            print(f"{timestamp} {line}")

        # Write to log files
        for line in header_info:
            self._write_to_log_files(line, "INFO", "run_header")

        return run_id

    def log_run_end(self, run_id, reason="Normal shutdown"):
        """Log run end with run ID and reason."""
        timestamp = self._get_timestamp()

        end_info = [
            f"🏁 Bot Run Ended - Run ID: {run_id}",
            f"├─ ended_at: {timestamp}",
            f"├─ run_id: {run_id}",
            f"└─ reason: {reason}",
        ]

        # Print to console
        for line in end_info:
            print(f"{timestamp} {line}")

        # Write to log files
        for line in end_info:
            self._write_to_log_files(line, "INFO", "run_end")

        # Add spacing after run end
        self.log_spacing()

    def log_user_interaction(
        self,
        interaction_type: str,
        user_name: str,
        user_id: int,
        action_description: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Log user interactions in a dedicated tree section for easy identification.

        Args:
            interaction_type: Type of interaction (e.g., "dropdown_surah", "button_navigation")
            user_name: Display name of the user
            user_id: Discord user ID
            action_description: Description of what the user did
            details: Additional details about the interaction
        """
        try:
            timestamp = self._get_timestamp()

            # Add line breaker for visual separation
            print("")
            self._write_to_log_files("", "INFO", "user_interaction")

            # Create interaction header
            interaction_header = (
                f"👤 User Interaction - {interaction_type.title().replace('_', ' ')}"
            )
            print(f"{timestamp} {interaction_header}")
            self._write_to_log_files(interaction_header, "INFO", "user_interaction")

            # Log user information
            user_info = f"├─ user: {user_name} ({user_id})"
            print(f"{timestamp} {user_info}")
            self._write_to_log_files(user_info, "INFO", "user_interaction")

            action_info = f"├─ action: {action_description}"
            print(f"{timestamp} {action_info}")
            self._write_to_log_files(action_info, "INFO", "user_interaction")

            # Log additional details if provided
            if details:
                detail_keys = list(details.keys())
                for i, (key, value) in enumerate(details.items()):
                    detail_line = f"├─ {key}: {value}"
                    print(f"{timestamp} {detail_line}")
                    self._write_to_log_files(detail_line, "INFO", "user_interaction")

            # End interaction log
            completion_line = (
                f"└─ interaction_completed: ✅ {interaction_type} processed"
            )
            print(f"{timestamp} {completion_line}")
            self._write_to_log_files(completion_line, "INFO", "user_interaction")

            # Add line breaker after interaction
            print("")
            self._write_to_log_files("", "INFO", "user_interaction")

        except Exception as e:
            timestamp = self._get_timestamp()
            error_line = (
                f"├─ user_interaction_log_error: Failed to log interaction: {str(e)}"
            )
            print(f"{timestamp} {error_line}")
            self._write_to_log_files(error_line, "ERROR", "user_interaction")

            type_line = f"├─ interaction_type: {interaction_type}"
            print(f"{timestamp} {type_line}")
            self._write_to_log_files(type_line, "ERROR", "user_interaction")

            user_line = f"├─ user: {user_name} ({user_id})"
            print(f"{timestamp} {user_line}")
            self._write_to_log_files(user_line, "ERROR", "user_interaction")

            action_line = f"└─ action: {action_description}"
            print(f"{timestamp} {action_line}")
            self._write_to_log_files(action_line, "ERROR", "user_interaction")

    def log_progress(self, current, total, emoji="🎶"):
        """Log progress with current/total format."""
        timestamp = self._get_timestamp()
        formatted_message = f"{emoji} Progress ({current}/{total})"
        print(f"{timestamp} {formatted_message}")
        self._write_to_log_files(formatted_message, "INFO", "progress")

    def log_status(self, message, status="INFO", emoji="📍"):
        """Log status with emoji and message."""
        if status != "INFO":
            self.log_perfect_tree_section(
                f"Status Update", [("message", message), ("level", status)], emoji
            )
        else:
            timestamp = self._get_timestamp()
            formatted_message = f"{emoji} {message}"
            print(f"{timestamp} {formatted_message}")
            self._write_to_log_files(formatted_message, status, "status")

    def log_version_info(self, bot_name, version, additional_info=None):
        """Log version information in a structured format."""
        items = [
            ("name", bot_name),
            ("version", version),
            ("changelog", "See CHANGELOG.md for details"),
        ]

        if additional_info:
            for key, value in additional_info.items():
                items.append((key, value))

        self.log_perfect_tree_section(f"{bot_name} Version Information", items, "📋")

    def log_error_with_traceback(self, message, exception=None, level="ERROR"):
        """Enhanced error logging with full traceback support."""
        timestamp = self._get_timestamp()

        if exception:
            # Get the full traceback
            tb_lines = traceback.format_exception(
                type(exception), exception, exception.__traceback__
            )
            tb_string = "".join(tb_lines)

            # Log the main error message
            formatted_message = f"├─ {level}: {message}"
            print(f"{timestamp} {formatted_message}")
            self._write_to_log_files(formatted_message, level, "error")

            # Log exception details
            exception_details = f"├─ exception_type: {type(exception).__name__}"
            print(f"{timestamp} {exception_details}")
            self._write_to_log_files(exception_details, level, "error")

            exception_message = f"├─ exception_message: {str(exception)}"
            print(f"{timestamp} {exception_message}")
            self._write_to_log_files(exception_message, level, "error")

            # Log full traceback with tree formatting
            traceback_header = f"└─ full_traceback:"
            print(f"{timestamp} {traceback_header}")
            self._write_to_log_files(traceback_header, level, "error")

            # Format traceback lines with proper indentation
            for line in tb_string.strip().split("\n"):
                if line.strip():
                    formatted_tb_line = f"   {line}"
                    print(f"{timestamp} {formatted_tb_line}")
                    self._write_to_log_files(formatted_tb_line, level, "error")
        else:
            # Simple error without exception
            formatted_message = f"├─ {level}: {message}"
            print(f"{timestamp} {formatted_message}")
            self._write_to_log_files(formatted_message, level, "error")

    def log_critical_error(self, message, exception=None):
        """Log critical errors that might crash the application."""
        self.log_error_with_traceback(f"CRITICAL: {message}", exception, "CRITICAL")

    def log_warning_with_context(self, message, context=None):
        """Log warnings with additional context information."""
        timestamp = self._get_timestamp()
        formatted_message = f"├─ WARNING: {message}"
        print(f"{timestamp} {formatted_message}")
        self._write_to_log_files(formatted_message, "WARNING", "warning")

        if context:
            context_message = f"└─ context: {context}"
            print(f"{timestamp} {context_message}")
            self._write_to_log_files(context_message, "WARNING", "warning")

    def log_async_error(self, function_name, exception, additional_context=None):
        """Specialized logging for async function errors."""
        timestamp = self._get_timestamp()

        # Log async error header
        header = f"├─ ASYNC_ERROR in {function_name}"
        print(f"{timestamp} {header}")
        self._write_to_log_files(header, "ERROR", "async_error")

        # Add context if provided
        if additional_context:
            context_msg = f"├─ context: {additional_context}"
            print(f"{timestamp} {context_msg}")
            self._write_to_log_files(context_msg, "ERROR", "async_error")

        # Log the full traceback
        self.log_error_with_traceback(
            f"Exception in async function {function_name}", exception, "ERROR"
        )

    def log_discord_error(self, event_name, exception, guild_id=None, channel_id=None):
        """Specialized logging for Discord-related errors."""
        timestamp = self._get_timestamp()

        # Log Discord error header
        header = f"├─ DISCORD_ERROR in {event_name}"
        print(f"{timestamp} {header}")
        self._write_to_log_files(header, "ERROR", "discord_error")

        # Add Discord context
        if guild_id:
            guild_msg = f"├─ guild_id: {guild_id}"
            print(f"{timestamp} {guild_msg}")
            self._write_to_log_files(guild_msg, "ERROR", "discord_error")

        if channel_id:
            channel_msg = f"├─ channel_id: {channel_id}"
            print(f"{timestamp} {channel_msg}")
            self._write_to_log_files(channel_msg, "ERROR", "discord_error")

        # Log the full traceback
        self.log_error_with_traceback(
            f"Discord event error in {event_name}", exception, "ERROR"
        )

    def log_spacing(self):
        """Add a blank line for visual separation."""
        print()
        self._write_to_log_files("", "INFO", "spacing")

    def reset_section_tracking(self):
        """Reset the section tracking for a new run or major section group."""
        global _is_first_section
        _is_first_section = True

    def log_section_group_separator(self, title=None):
        """Add extra spacing and optional title for major section groups."""
        print()
        if title:
            timestamp = self._get_timestamp()
            separator_line = f"{'='*60}"
            title_line = f"📋 {title}"
            print(f"{timestamp} {separator_line}")
            print(f"{timestamp} {title_line}")
            print(f"{timestamp} {separator_line}")
            self._write_to_log_files(separator_line, "INFO", "section_group_separator")
            self._write_to_log_files(title_line, "INFO", "section_group_separator")
            self._write_to_log_files(separator_line, "INFO", "section_group_separator")
        print()
        self._write_to_log_files("", "INFO", "section_group_spacing")

    def log_run_end(self, run_id, reason="Normal shutdown"):
        """Log run end with run ID and reason."""
        timestamp = self._get_timestamp()

        end_info = [
            f"🏁 Bot Run Ended - Run ID: {run_id}",
            f"├─ ended_at: {timestamp}",
            f"├─ run_id: {run_id}",
            f"└─ reason: {reason}",
        ]

        # Print to console
        for line in end_info:
            print(f"{timestamp} {line}")

        # Write to log files
        for line in end_info:
            self._write_to_log_files(line, "INFO", "run_end")

        # Add spacing after run end
        self.log_spacing()

    def log_user_interaction(
        self,
        interaction_type: str,
        user_name: str,
        user_id: int,
        action_description: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Log user interactions in a dedicated tree section for easy identification.

        Args:
            interaction_type: Type of interaction (e.g., "dropdown_surah", "button_navigation")
            user_name: Display name of the user
            user_id: Discord user ID
            action_description: Description of what the user did
            details: Additional details about the interaction
        """
        try:
            timestamp = self._get_timestamp()

            # Add line breaker for visual separation
            print("")
            self._write_to_log_files("", "INFO", "user_interaction")

            # Create interaction header
            interaction_header = (
                f"👤 User Interaction - {interaction_type.title().replace('_', ' ')}"
            )
            print(f"{timestamp} {interaction_header}")
            self._write_to_log_files(interaction_header, "INFO", "user_interaction")

            # Log user information
            user_info = f"├─ user: {user_name} ({user_id})"
            print(f"{timestamp} {user_info}")
            self._write_to_log_files(user_info, "INFO", "user_interaction")

            action_info = f"├─ action: {action_description}"
            print(f"{timestamp} {action_info}")
            self._write_to_log_files(action_info, "INFO", "user_interaction")

            # Log additional details if provided
            if details:
                detail_keys = list(details.keys())
                for i, (key, value) in enumerate(details.items()):
                    detail_line = f"├─ {key}: {value}"
                    print(f"{timestamp} {detail_line}")
                    self._write_to_log_files(detail_line, "INFO", "user_interaction")

            # End interaction log
            completion_line = (
                f"└─ interaction_completed: ✅ {interaction_type} processed"
            )
            print(f"{timestamp} {completion_line}")
            self._write_to_log_files(completion_line, "INFO", "user_interaction")

            # Add line breaker after interaction
            print("")
            self._write_to_log_files("", "INFO", "user_interaction")

        except Exception as e:
            timestamp = self._get_timestamp()
            error_line = (
                f"├─ user_interaction_log_error: Failed to log interaction: {str(e)}"
            )
            print(f"{timestamp} {error_line}")
            self._write_to_log_files(error_line, "ERROR", "user_interaction")

            type_line = f"├─ interaction_type: {interaction_type}"
            print(f"{timestamp} {type_line}")
            self._write_to_log_files(type_line, "ERROR", "user_interaction")

            user_line = f"├─ user: {user_name} ({user_id})"
            print(f"{timestamp} {user_line}")
            self._write_to_log_files(user_line, "ERROR", "user_interaction")

            action_line = f"└─ action: {action_description}"
            print(f"{timestamp} {action_line}")
            self._write_to_log_files(action_line, "ERROR", "user_interaction")
