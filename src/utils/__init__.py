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
#
# Key Features:
# - Consistent tree-style logging across all components
# - Comprehensive error handling with traceback logging
# - Real-time audio progress tracking and display
# - Interactive Discord UI components for user control
# - Robust state persistence and recovery mechanisms
# - Multi-reciter audio support with dynamic switching
# =============================================================================

# Import all utility components for easy access
from .audio_manager import AudioManager
from .control_panel import *
from .rich_presence import *
from .surah_mapper import *
from .tree_log import *

# Export main utility classes and functions
__all__ = [
    # Audio Management
    "AudioManager",
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
    "log_tree",
    "log_tree_branch",
    "log_tree_final",
    "log_section_start",
    "log_spacing",
    "log_error_with_traceback",
    "log_async_error",
    "log_critical_error",
]
