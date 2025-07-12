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
__version__ = "3.5.1"

# Bot name and branding
BOT_NAME = "QuranBot"

# Author information - single source of truth
__author__ = "John (Discord: Trippixn)"
BOT_AUTHOR = __author__  # For backward compatibility

# Version components for programmatic access
VERSION_MAJOR = 3
VERSION_MINOR = 5
VERSION_PATCH = 1

# Pre-release identifiers (empty for stable releases)
VERSION_PRERELEASE = ""  # e.g., "alpha", "beta", "rc1"

# Build metadata (empty for standard releases)
VERSION_BUILD = ""  # e.g., "20231201", "commit-abc123"

# =============================================================================
# Version Formatting Functions
# =============================================================================


def get_version_string():
    """
    Get the complete version string with optional pre-release and build info.

    Returns:
        str: Complete version string (e.g., "2.0.0", "2.1.0-beta", "2.0.1+build123")
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
    }


# =============================================================================
# Export Version Information
# =============================================================================

# Make version easily accessible
BOT_VERSION = __version__  # For backward compatibility
VERSION = __version__  # Alternative access

# Export all version-related items
__all__ = [
    "__version__",
    "__author__",
    "BOT_NAME",
    "BOT_AUTHOR",
    "BOT_VERSION",
    "VERSION",
    "VERSION_MAJOR",
    "VERSION_MINOR",
    "VERSION_PATCH",
    "VERSION_PRERELEASE",
    "VERSION_BUILD",
    "get_version_string",
    "get_version_tuple",
    "get_version_info",
]
