# =============================================================================
# QuranBot - Bot Package
# =============================================================================
# Contains the main Discord bot implementation and event handling
#
# This package provides the core Discord bot functionality including:
# - Discord client initialization and configuration
# - Event handlers for voice state changes and errors
# - Audio playback coordination with voice channels
# - Integration with Rich Presence and control panel systems
# - Comprehensive error handling and logging
# - State management and persistence across restarts
#
# The bot is designed as a 24/7 audio streaming service that:
# - Automatically connects to configured voice channels
# - Plays Quran audio with multiple reciter support
# - Provides interactive control panels for user interaction
# - Maintains playback state across bot restarts
# - Implements robust error recovery and reconnection logic
# =============================================================================

from .main import *

# Export main bot components for external access
__all__ = [
    "bot",  # Main Discord bot instance
    "BOT_NAME",  # Bot display name
    "BOT_VERSION",  # Current bot version
    "DISCORD_TOKEN",  # Discord authentication token
]
