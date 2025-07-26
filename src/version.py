# =============================================================================
# QuranBot - Version Management
# =============================================================================
# Single source of truth for version information across the entire project
# Update only this file when bumping versions
# =============================================================================

# =============================================================================
# Version Configuration
# =============================================================================

# Main version number - update this single line for new releases
__version__ = "4.1.0"

# Bot name and branding
BOT_NAME = "QuranBot"

# Author information - single source of truth
__author__ = "John (Discord: Trippixn)"
BOT_AUTHOR = __author__  # For backward compatibility

# Version components for programmatic access
VERSION_MAJOR = 4
VERSION_MINOR = 1
VERSION_PATCH = 0

# Pre-release identifiers (empty for stable releases)
VERSION_PRERELEASE = ""  # e.g., "alpha", "beta", "rc1"

# Build metadata (empty for standard releases)
VERSION_BUILD = ""  # e.g., "20231201", "commit-abc123"

# =============================================================================
# Release Information
# =============================================================================

RELEASE_NAME = "Advanced AI Integration"
RELEASE_DATE = "2025-01-27"

RELEASE_NOTES = """
QuranBot 4.1.0 - Advanced AI Integration

🤖 NEW: ADVANCED AI ASSISTANT:
• OpenAI GPT-3.5 Turbo integration for natural Islamic Q&A
• Mention-based interaction - simply @QuranBot for intelligent responses
• Bilingual support: understands Arabic/English, responds in English
• Smart rate limiting: 1 question per hour (admin exempt) with exact reset times
• Enhanced knowledge base: Hadith search, verse lookup, practical Islamic tools
• Conversation memory: personalized responses based on user history
• Cultural sensitivity: Syrian context awareness with current affairs
• Palestinian solidarity: principled stance supporting Palestinian rights

🕌 PRAYER TIME INTEGRATION:
• Real-time Mecca prayer notifications with beautiful embeds
• Time-based duas: contextual selections for different prayer times
• Interactive UI: dua emoji reactions with automatic moderation
• Islamic calendar integration: full Hijri date awareness

🌍 MULTILINGUAL FEATURES:
• GPT-powered translation to Arabic, German, Spanish
• Instant translation buttons with distinct colors
• English "back to original" button for easy language switching
• High-quality, context-aware Islamic term preservation

🎵 ENHANCED AUDIO SYSTEM:
• State persistence: audio position survives bot restarts
• Automatic role management for voice channel participants
• Improved playback reliability and resume functionality

🏗️ SYSTEM IMPROVEMENTS:
• Enhanced conversation memory service with user profiling
• Advanced cultural context detection and adaptation
• Improved error handling and graceful fallbacks
• Comprehensive logging for all AI interactions

📚 KNOWLEDGE BASE EXPANSION:
• 12+ authentic hadith sources with smart search
• Contextual Quran verse lookup and explanations
• Practical Islamic tools: prayer times, Qibla, Zakat calculations
• Bot feature awareness for comprehensive help responses

This major release transforms QuranBot into an intelligent Islamic assistant
while maintaining all existing functionality and reliability.
"""

# =============================================================================
# Version Formatting Functions
# =============================================================================


def get_version_string():
    """
    Get the complete version string with optional pre-release and build info.

    Returns:
        str: Complete version string (e.g., "4.0.0", "4.1.0-beta", "4.0.1+build123")
    """
    version = __version__

    if VERSION_PRERELEASE:
        version += f"-{VERSION_PRERELEASE}"

    if VERSION_BUILD:
        version += f"+{VERSION_BUILD}"

    return version


def get_version_tuple():
    """
    Get version as a tuple for version comparison.

    Returns:
        tuple: Version tuple (major, minor, patch)
    """
    return (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH)


def get_version_info():
    """
    Get comprehensive version information.

    Returns:
        dict: Complete version information
    """
    return {
        "version": __version__,
        "version_string": get_version_string(),
        "major": VERSION_MAJOR,
        "minor": VERSION_MINOR,
        "patch": VERSION_PATCH,
        "prerelease": VERSION_PRERELEASE,
        "build": VERSION_BUILD,
        "tuple": get_version_tuple(),
        "author": __author__,
        "bot_name": BOT_NAME,
        "release_name": RELEASE_NAME,
        "release_date": RELEASE_DATE,
        "release_notes": RELEASE_NOTES,
    }


# =============================================================================
# Export Version Information
# =============================================================================

# Make version easily accessible
BOT_VERSION = __version__  # For backward compatibility
VERSION = __version__  # Alternative access

# Export all version-related items
__all__ = [
    "BOT_AUTHOR",
    "BOT_NAME",
    "BOT_VERSION",
    "RELEASE_DATE",
    "RELEASE_NAME",
    "RELEASE_NOTES",
    "VERSION",
    "VERSION_BUILD",
    "VERSION_MAJOR",
    "VERSION_MINOR",
    "VERSION_PATCH",
    "VERSION_PRERELEASE",
    "__author__",
    "__version__",
    "get_version_info",
    "get_version_string",
    "get_version_tuple",
]
