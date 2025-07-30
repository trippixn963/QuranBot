# =============================================================================
# QuranBot - Utilities Package
# =============================================================================
# Contains utility functions and classes for QuranBot functionality
#
# This package provides essential utilities including:
# - Tree-structured logging system with file and console output
# - Discord Rich Presence management with real-time progress tracking
# - Surah mapping and metadata management with Arabic/English names
# - Discord control panel with interactive buttons and dropdowns
# - Audio playback management with state persistence
# - State management for cross-restart persistence
# - Bulletproof data protection for all persistent files
#
# Key Features:
# - Consistent tree-style logging across all components
# - Comprehensive error handling with traceback logging
# - Real-time audio progress tracking and display
# - Interactive Discord UI components for user control
# - Robust state persistence and recovery mechanisms
# - Multi-reciter audio support with dynamic switching
# - Atomic writes and backup protection for all data files
# =============================================================================

# Import all utility components
from .control_panel import (
    ReciterSelect,
    SimpleControlPanelView,
    SurahSelect,
    cleanup_all_control_panels,
    create_control_panel,
    setup_control_panel,
)

# Discord logging for VPS monitoring
from .discord_logger import (
    discord_log_critical,
    discord_log_error,
    discord_log_success,
    discord_log_system,
    discord_log_user,
    discord_log_vps_status,
    discord_log_warning,
    get_discord_logger,
    setup_discord_logger,
)
from .rich_presence import RichPresenceManager, validate_rich_presence_dependencies
from .surah_mapper import (
    format_now_playing,
    get_surah_display,
    get_surah_info,
    get_surah_name,
    validate_surah_number,
)
from .tree_log import (
    log_async_error,
    log_critical_error,
    log_discord_error,
    log_error_with_traceback,
    log_perfect_tree_section,
    log_progress,
    log_spacing,
    log_status,
    log_user_interaction,
    log_voice_activity_tree,
    log_warning_with_context,
    write_to_log_files,
)

# Import listening stats utilities
try:
    from .listening_stats import (
        ListeningStatsManager,
        UserStats,
        format_listening_time,
        get_leaderboard_data,
        get_user_listening_stats,
        listening_stats_manager,
        track_voice_join,
        track_voice_leave,
    )
except ImportError:
    # Fallback if listening stats module is not available
    def track_voice_join(user_id):
        pass

    def track_voice_leave(user_id):
        return 0.0

    def get_user_listening_stats(user_id):
        return None

    def get_leaderboard_data():
        return {
            "top_users": [],
            "total_listening_time": 0,
            "total_sessions": 0,
            "active_users": 0,
            "total_users": 0,
        }

    def format_listening_time(seconds):
        return "0s"

    class ListeningStatsManager:
        pass

    class UserStats:
        pass

    listening_stats_manager = None

# Import version utilities with absolute import
try:
    from src.version import (
        BOT_NAME,
        BOT_VERSION,
        __author__,
        get_version_info,
        get_version_string,
        get_version_tuple,
    )
except ImportError:
    # Fallback for different import contexts
    BOT_NAME = "QuranBot"
    BOT_VERSION = "2.4.0"  # Keep in sync with src/version.py
    __author__ = "John (Discord: Trippixn)"  # Keep in sync with src/version.py

    def get_version_info():
        return {"version": BOT_VERSION, "name": BOT_NAME, "author": __author__}

    def get_version_string():
        return BOT_VERSION

    def get_version_tuple():
        return (2, 4, 0)  # Keep in sync with src/version.py


# Export main utility classes and functions
__all__ = [
    # Control Panel Components
    "SimpleControlPanelView",
    "SurahSelect",
    "ReciterSelect",
    "create_control_panel",
    "setup_control_panel",
    "cleanup_all_control_panels",
    # Rich Presence Management
    "RichPresenceManager",
    "validate_rich_presence_dependencies",
    # Surah Mapping and Metadata
    "get_surah_info",
    "get_surah_display",
    "get_surah_name",
    "validate_surah_number",
    "format_now_playing",
    # Tree Logging System
    "log_perfect_tree_section",
    "log_async_error",
    "log_critical_error",
    "log_discord_error",
    "log_error_with_traceback",
    "log_progress",
    "log_spacing",
    "log_status",
    "log_user_interaction",
    "log_warning_with_context",
    "log_voice_activity_tree",
    "write_to_log_files",
    # Listening Statistics
    "ListeningStatsManager",
    "UserStats",
    "track_voice_join",
    "track_voice_leave",
    "get_user_listening_stats",
    "get_leaderboard_data",
    "format_listening_time",
    "listening_stats_manager",
    # Automated Backup System
    "start_backup_scheduler",
    "stop_backup_scheduler",
    "get_backup_status",
    # Version Information
    "BOT_NAME",
    "BOT_VERSION",
    "__author__",
    "get_version_info",
    "get_version_string",
    "get_version_tuple",
]
