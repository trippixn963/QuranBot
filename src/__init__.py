# =============================================================================
# QuranBot - Source Package
# =============================================================================
# Main source package for QuranBot Discord application
#
# This package contains all core functionality for the QuranBot including:
# - Discord bot implementation with voice channel integration
# - Audio playback management with state persistence
# - Rich presence integration with real-time progress tracking
# - Control panel with interactive Discord UI components
# - Tree-structured logging system for comprehensive monitoring
# - Surah mapping and metadata management
# =============================================================================

# Import version and author from centralized version module
from .version import __author__, __version__

__description__ = "Discord bot for playing Quran audio with tree-style logging"
__license__ = "MIT"
__url__ = "https://github.com/trippixn963/QuranBot"

# Package metadata for external tools
__all__ = ["__version__", "__author__", "__description__", "__license__", "__url__"]
