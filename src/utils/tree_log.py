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
#   YYYY-MM-DD.log    - Single daily log file (all events)
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
        """Create log directory structure with date-based subdirectories and 3 log files."""
        try:
            # Create main logs directory (always relative to project root)
            project_root = Path(__file__).parent.parent.parent
            main_log_dir = project_root / "logs"
            main_log_dir.mkdir(parents=True, exist_ok=True)
            
            # Create today's date subdirectory
            date_str = self._get_log_date()
            date_log_dir = main_log_dir / date_str
            date_log_dir.mkdir(parents=True, exist_ok=True)
            
            return date_log_dir
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

    def _write_to_log_files(self, message: str, level: str, category: str) -> None:
        """
        Write log message to 3 separate log files in date-based subdirectory.

        Creates logs/YYYY-MM-DD/ directory with:
        - logs.log: All log messages
        - errors.log: Only ERROR and CRITICAL level messages
        - logs.json: Structured JSON log entries

        Args:
            message: The log message to write
            level: Log level (INFO, ERROR, WARNING, etc.)
            category: Category of the log (for context)
        """
        try:
            # Check if the date has changed and update log directory if needed
            current_date = self._get_log_date()
            if not self.log_dir or self.log_dir.name != current_date:
                # Date has changed, create new log directory
                project_root = Path(__file__).parent.parent.parent
                main_log_dir = project_root / "logs"
                main_log_dir.mkdir(parents=True, exist_ok=True)
                
                new_date_log_dir = main_log_dir / current_date
                new_date_log_dir.mkdir(parents=True, exist_ok=True)
                
                # Update the log directory
                old_date = self.log_dir.name if self.log_dir else "None"
                self.log_dir = new_date_log_dir
                
                # Log the date change (but avoid infinite recursion)
                if old_date != "None" and old_date != current_date:
                    timestamp = self._get_timestamp()
                    print(f"{timestamp} [INFO] 📅 Log date changed: {old_date} → {current_date}")

            if not self.log_dir:
                return

            # Create timestamp for the log entry
            timestamp = self._get_timestamp()

            # Format the log entry with level and category for context
            if message.strip():  # Only add level/category info for non-empty messages
                log_entry = f"{timestamp} [{level}] {message}\n"
            else:
                log_entry = "\n"  # Just a blank line for spacing

            # 1. Write to main logs.log file (all messages)
            main_log_file = self.log_dir / "logs.log"
            with open(main_log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
                f.flush()

            # 2. Write to errors.log file (only ERROR and CRITICAL levels)
            if level in ["ERROR", "CRITICAL", "WARNING"]:
                error_log_file = self.log_dir / "errors.log"
                with open(error_log_file, "a", encoding="utf-8") as f:
                    f.write(log_entry)
                    f.flush()

            # 3. Write to logs.json file (structured JSON format)
            if message.strip():  # Only write non-empty messages to JSON
                json_log_file = self.log_dir / "logs.json"
                json_entry = {
                    "timestamp": timestamp,
                    "level": level,
                    "category": category,
                    "message": message.strip(),
                    "run_id": self.run_id,
                    "iso_datetime": self.current_datetime_iso
                }
                
                # Append JSON entry as a single line
                with open(json_log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(json_entry) + "\n")
                    f.flush()

        except Exception as e:
            # Fallback to console if file writing fails
            print(f"LOG_ERROR: Failed to write to log file: {e}")


# =============================================================================
# Global Logger Instance and Standalone Functions
# =============================================================================
# Create a global logger instance for use throughout the application.
# This provides both class-based and function-based interfaces.
#
# The standalone functions are provided for backward compatibility and
# convenience, allowing direct imports without instantiating the logger.
# =============================================================================

# Global logger instance
_global_logger = TreeLogger()


# Standalone functions for backward compatibility and convenience
def log_perfect_tree_section(title, items, emoji="🎯", nested_groups=None):
    """Standalone function for logging perfect tree sections."""
    _global_logger.log_perfect_tree_section(title, items, emoji, nested_groups)


def log_error_with_traceback(message, exception=None, level="ERROR"):
    """Standalone function for logging errors with tracebacks."""
    _global_logger.log_error_with_traceback(message, exception, level)


def log_critical_error(message, exception=None):
    """Standalone function for logging critical errors."""
    _global_logger.log_critical_error(message, exception)


def log_warning_with_context(message, context=None):
    """Standalone function for logging warnings with context."""
    _global_logger.log_warning_with_context(message, context)


def log_async_error(function_name, exception, additional_context=None):
    """Standalone function for logging async errors."""
    _global_logger.log_async_error(function_name, exception, additional_context)


def log_discord_error(event_name, exception, guild_id=None, channel_id=None):
    """Standalone function for logging Discord errors."""
    _global_logger.log_discord_error(event_name, exception, guild_id, channel_id)


def log_spacing():
    """Standalone function for adding spacing."""
    _global_logger.log_spacing()


def log_status(message, status="INFO", emoji="📍"):
    """Standalone function for logging status messages."""
    _global_logger.log_status(message, status, emoji)


def log_progress(current, total, emoji="🎶"):
    """Standalone function for logging progress."""
    _global_logger.log_progress(current, total, emoji)


def log_user_interaction(
    interaction_type, user_name, user_id, action_description, details=None
):
    """Standalone function for logging user interactions."""
    _global_logger.log_user_interaction(
        interaction_type, user_name, user_id, action_description, details
    )


def log_voice_activity_tree(user_name, activity_type, details):
    """Standalone function for logging voice activity."""
    _global_logger.log_voice_activity_tree(user_name, activity_type, details)


def log_run_separator():
    """Standalone function for logging run separators."""
    _global_logger.log_run_separator()


def log_run_header(bot_name, version, run_id=None):
    """Standalone function for logging run headers."""
    return _global_logger.log_run_header(bot_name, version, run_id)


def log_run_end(run_id, reason="Normal shutdown"):
    """Standalone function for logging run ends."""
    _global_logger.log_run_end(run_id, reason)


def get_timestamp():
    """Standalone function for getting formatted timestamps."""
    return _global_logger._get_timestamp()


def write_to_log_files(message: str, level: str, category: str) -> None:
    """
    Standalone function for writing to log files.

    This is the main function used throughout the codebase for logging.
    Now consolidates all logs into a single file per day.
    """
    _global_logger._write_to_log_files(message, level, category)
