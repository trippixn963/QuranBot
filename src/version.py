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
__version__ = "4.0.1"

# Bot name and branding
BOT_NAME = "QuranBot"

# Author information - single source of truth
__author__ = "John (Discord: Trippixn)"
BOT_AUTHOR = __author__  # For backward compatibility

# Version components for programmatic access
VERSION_MAJOR = 4
VERSION_MINOR = 0
VERSION_PATCH = 1

# Pre-release identifiers (empty for stable releases)
VERSION_PRERELEASE = ""  # e.g., "alpha", "beta", "rc1"

# Build metadata (empty for standard releases)
VERSION_BUILD = ""  # e.g., "20231201", "commit-abc123"

# =============================================================================
# Release Information
# =============================================================================

RELEASE_NAME = "Stability & Enhancement Update"
RELEASE_DATE = "2025-01-27"

RELEASE_NOTES = """
QuranBot 4.0.1 - Stability & Enhancement Update

🔧 BUG FIXES & IMPROVEMENTS:
• Fixed /question command functionality with complete restoration from stable version
• Resolved QuizView constructor parameter naming issues
• Fixed signal handling for proper Ctrl+C graceful shutdown
• Corrected configuration service integration across all commands
• Resolved dependency resolution conflicts

📩 NEW FEATURES:
• Admin DM integration - automatic quiz answer delivery with rich embeds
• Enhanced quiz results with admin profile picture in footers
• Direct message links for easy navigation back to quiz messages
• Improved error handling with comprehensive fallback behavior

⚡ SYSTEM STABILITY:
• All legacy compatibility issues resolved
• Command loading system fully stabilized
• Audio system optimized for seamless operation
• Configuration unified under single source of truth
• Comprehensive testing completed across all components

🏗️ ARCHITECTURE ENHANCEMENTS:
• Dependency injection container fully operational
• Service lifecycle management improved
• Resource management optimized
• Error reporting enhanced with detailed logging
• Performance monitoring refined

📚 DOCUMENTATION:
• README updated with latest changes and improvements
• Version management centralized and automated
• Deployment guides verified and updated

This release focuses on stability, bug fixes, and user experience improvements
while maintaining the robust modernized architecture introduced in 4.0.0.
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
