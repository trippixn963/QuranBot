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

RELEASE_NAME = "Open Source Release"
RELEASE_DATE = "2025-07-30"

RELEASE_NOTES = """
QuranBot 4.1.0 - Open Source Release

🌟 MAJOR MILESTONE - OPEN SOURCE TRANSFORMATION:
• Full open source release with comprehensive documentation
• Complete codebase cleanup and professional polish
• MIT License with inclusive interfaith collaboration message
• Community-ready with contribution guidelines and issue templates

📱 ENHANCED DOCUMENTATION & USER EXPERIENCE:
• Professional README with working badges and clear setup instructions
• Fixed screenshot display issues with proper filename encoding
• Added comprehensive troubleshooting section and system requirements
• Enhanced Quick Start guide with Docker and Python setup options
• Complete API documentation and development guides

🛡️ SECURITY & QUALITY IMPROVEMENTS:
• Pre-commit hooks with comprehensive code quality checks
• Security auditing with Bandit and vulnerability scanning
• Enhanced error handling and logging throughout the application
• Configuration validation scripts for deployment safety
• Comprehensive testing infrastructure

🏗️ INFRASTRUCTURE & DEPLOYMENT:
• GitHub Actions CI/CD pipeline with automated testing
• Docker containerization with multi-environment support
• Professional project structure with examples and templates
• Enhanced webhook logging and monitoring capabilities
• Performance profiling and bottleneck analysis tools

🤝 COMMUNITY & COLLABORATION FEATURES:
• GitHub Discussions, Issues, and PR templates
• Code of Conduct and Security Policy
• Comprehensive contributing guidelines
• Community Discord integration
• Interfaith collaboration showcase

📋 CONFIGURATION & SETUP IMPROVEMENTS:
• Unified configuration system with environment variable support
• Migration scripts for existing deployments
• Example configurations for different deployment scenarios
• Validation tools for configuration correctness
• Hot-reload configuration updates without restart

This release transforms QuranBot from a private project into a full-featured,
community-ready open source Islamic Discord bot with enterprise-grade quality
and comprehensive documentation for users and contributors.
"""

# =============================================================================
# Version Formatting Functions
# =============================================================================


def get_version_string() -> str:
    """Get the complete version string with optional pre-release and build info.

    Returns:
        str: Complete version string (e.g., "4.0.0", "4.1.0-beta", "4.0.1+build123")
    """
    version = __version__

    if VERSION_PRERELEASE:
        version += f"-{VERSION_PRERELEASE}"

    if VERSION_BUILD:
        version += f"+{VERSION_BUILD}"

    return version


def get_version_tuple() -> tuple[int, int, int]:
    """Get version as a tuple for version comparison.

    Returns:
        tuple: Version tuple (major, minor, patch)
    """
    return (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH)


def get_version_info() -> dict[str, str | int | tuple[int, int, int]]:
    """Get comprehensive version information.

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
