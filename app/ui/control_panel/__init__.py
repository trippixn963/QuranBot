# =============================================================================
# QuranBot - Control Panel Package
# =============================================================================
# Discord control panel system for Quran audio playback management.
# Provides UI components for surah selection, reciter switching, and
# real-time playback control.
#
# Core Components:
# - Manager: Panel lifecycle and multi-guild coordination
# - View: Interactive UI components and state management
# - Embeds: Message formatting and status displays
# - Monitor: Health monitoring and maintenance
# - Utils: Common utilities and error handling
#
# Features:
# - Real-time audio state monitoring
# - Interactive playback controls
# - Surah/reciter selection with pagination
# - Activity tracking and logging
# - Automatic panel updates
# - Error handling and recovery
# =============================================================================

# Local imports - current module
from .embeds import create_error_embed, create_status_embed, create_surah_info_embed
from .manager import ControlPanelManager
from .view import ControlPanelView


__all__ = [
    "ControlPanelManager",
    "ControlPanelView",
    "create_status_embed",
    "create_surah_info_embed",
    "create_error_embed",
]
