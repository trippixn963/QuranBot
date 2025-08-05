# =============================================================================
# QuranBot - Control Panel Embeds
# =============================================================================
# Embed creation and formatting for control panel displays including status,
# surah information, error messages, and progress tracking.
#
# Embed Types:
# - Status Embed: Real-time playback status with progress bars
# - Surah Info Embed: Detailed surah information and metadata
# - Error Embed: Standardized error messages with recovery guidance
# - Success Embed: Operation confirmation and feedback
# - Loading Embed: Progress indicators for long operations
# - Search Results Embed: Formatted search results with pagination
#
# Design Features:
# - Dark theme colors (#2f3136) for Discord integration
# - Progress bars with visual indicators (▰▱▰▱)
# - Arabic/English bilingual display support
# - Rich formatting with emojis and structured data
# - Responsive layout with proper field organization
#
# Formatting Utilities:
# - Time duration formatting (MM:SS)
# - Progress percentage calculations
# - Text truncation for Discord limits
# - Safe value extraction with defaults
# - Thumbnail and author integration
#
# Error Handling:
# - Graceful degradation for missing data
# - Safe default values for all fields
# - Consistent error message formatting
# - User-friendly error descriptions
# =============================================================================

# Standard library imports
from datetime import datetime
from typing import Any

# Third-party imports
import discord

# Local imports - config
from ...config.timezone import APP_TIMEZONE

# Local imports - core modules
from ...core.errors import ErrorHandler
from ...core.logger import TreeLogger

# Local imports - base components
from ..base.formatters import (
    format_progress_bar,
    format_surah_display,
    format_time_duration,
    truncate_text,
)

# Initialize error handler for embeds
error_handler = ErrorHandler()


def create_status_embed(
    audio_state: dict[str, Any], activity_info: dict[str, Any] | None = None
) -> discord.Embed:
    """
    Create the main status embed matching the exact design from the screenshot.

    Generates the primary control panel display with real-time audio information,
    progress tracking, and user activity. Uses consistent formatting and colors
    to match the Discord dark theme and provide clear visual hierarchy.

    Args:
        audio_state: Current audio playback state from audio manager
        activity_info: Recent user activity information for display

    Returns:
        Formatted Discord embed ready for display in control panel
    """
    try:
        # STEP 1: Log Embed Creation Context
        # Record detailed context for debugging and monitoring
        TreeLogger.debug(
            "Creating status embed",
            {
                "has_audio_state": bool(audio_state),
                "has_activity_info": bool(activity_info),
                "is_playing": (
                    audio_state.get("is_playing", False) if audio_state else False
                ),
                "surah_number": (
                    audio_state.get("current_surah", {}).get("number")
                    if audio_state and audio_state.get("current_surah")
                    else None
                ),
                "reciter": (
                    audio_state.get("current_reciter", {}).get("name")
                    if audio_state and audio_state.get("current_reciter")
                    else None
                ),
                "position": audio_state.get("position", 0) if audio_state else 0,
                "duration": audio_state.get("duration", 0) if audio_state else 0,
                "current_surah": (
                    audio_state.get("current_surah", {}).get("number")
                    if audio_state
                    else None
                ),
                "is_playing": (
                    audio_state.get("is_playing", False) if audio_state else False
                ),
            },
            service="ControlPanelEmbeds",
        )

        # STEP 2: Extract Audio Information with Safe Defaults
        # Ensure we have valid data even if audio state is incomplete
        if not audio_state:
            audio_state = {}

        current_surah = audio_state.get("current_surah", {})
        current_reciter = audio_state.get("current_reciter", {})
        position = audio_state.get("position", 0)
        duration = audio_state.get("duration", 0)
        is_playing = audio_state.get("is_playing", False)

        # STEP 3: Extract Surah Information with Compatibility Handling
        # Get surah details with fallback values for missing data
        surah_number = current_surah.get("number", 1)
        surah_name = current_surah.get("name_english", "Al-Fatiha")
        surah_arabic = current_surah.get("name_arabic", "الفاتحة")

        # STEP 4: Handle Reciter Name Format Variations
        # Support different reciter name formats (enum, string, etc.)
        reciter_raw = current_reciter.get("name", "Saad Al Ghamdi")
        if hasattr(reciter_raw, "value"):
            # Handle enum values
            reciter_name = reciter_raw.value
        elif (
            isinstance(reciter_raw, str)
            and "." in reciter_raw
            and reciter_raw.startswith("ReciterName")
        ):
            # Handle "ReciterName.SAAD_AL_GHAMDI" format
            reciter_name = reciter_raw.split(".")[-1].replace("_", " ").title()
        else:
            # Handle plain string format
            reciter_name = str(reciter_raw)

        reciter_arabic = current_reciter.get("name_arabic", "سعد الغامدي")

        # STEP 5: Calculate Progress with Safety Checks
        # Ensure progress calculations are safe and accurate
        if duration > 0:
            # Clamp position to valid range to prevent display errors
            safe_position = max(0.0, min(position, duration))
            progress_percent = int((safe_position / duration) * 100)
            position_str = format_time_duration(safe_position)
            duration_str = format_time_duration(duration)
        else:
            # Provide default values when duration is unknown
            progress_percent = 0
            position_str = "0:00"
            duration_str = "0:00"

            # STEP 6: Create Embed with Dark Theme Styling
        # Initialize embed with consistent Discord dark theme colors
        embed = discord.Embed(
            color=0x2F3136  # Dark theme color matching Discord's design
        )

        # STEP 7: Format Main Status Section
        # Create formatted status display with code blocks for visibility
        status_text = f"**Surah:** ```{surah_name} - {surah_arabic}```\n\n"
        status_text += f"**Reciter:** ```{reciter_name} - {reciter_arabic}```\n\n"
        status_text += f"**Progress:** ```{position_str} / {duration_str}```\n"

        # STEP 8: Add Progress Bar Visualization
        # Create visual progress bar with percentage display
        progress_bar = format_progress_bar(position, duration, length=20)
        status_text += f"```{progress_bar} {progress_percent}%```"

        # Set the formatted status as embed description
        embed.description = status_text

        # STEP 9: Add Last Activity Tracking
        # Display recent user activity if available
        if activity_info and activity_info.get("last_activity"):
            last_activity = activity_info["last_activity"]
            if (
                last_activity.get("user")
                and last_activity.get("action")
                and last_activity.get("time_elapsed")
            ):
                # Extract activity details for display
                user_id = last_activity["user"].get("id")
                action = last_activity["action"]
                time_elapsed = last_activity["time_elapsed"]

                # Add activity field to embed
                embed.add_field(
                    name="",
                    value=f"**Last Activity:** <@{user_id}> {action} • `{time_elapsed}`",
                    inline=False,
                )

        # STEP 10: Log Successful Embed Creation
        # Record successful embed creation for monitoring
        TreeLogger.success(
            "Status embed created successfully",
            {
                "embed_length": len(embed.description or ""),
                "embed_color": embed.color,
                "has_surah_info": bool(current_surah),
                "has_reciter_info": bool(current_reciter),
            },
            service="ControlPanelEmbeds",
        )

        return embed

    except Exception as e:
        # STEP 11: Error Recovery and Logging
        # Handle any errors during embed creation gracefully
        TreeLogger.error(
            f"Error creating status embed: {e}",
            {
                "has_audio_state": bool(audio_state),
                "has_activity_info": bool(activity_info),
                "error_type": type(e).__name__,
            },
            service="ControlPanelEmbeds",
        )

        # STEP 12: Provide Fallback Error Embed
        # Return a basic error embed to prevent complete failure
        embed = discord.Embed(
            title="🕌 QuranBot Status",
            description="Unable to display status. Please try again later.",
            color=discord.Color.red(),
        )
        return embed


def create_surah_info_embed(surah_info: dict[str, Any]) -> discord.Embed:
    """
    Create information embed for a specific surah.

    Generates a detailed information display for a selected surah,
    including Arabic name, verse count, revelation context, meaning,
    and description. Used in search results and surah selection.

    Args:
        surah_info: Dictionary containing surah metadata and details

    Returns:
        Formatted Discord embed with comprehensive surah information
    """
    try:
        # STEP 1: Create Base Embed with Title
        # Initialize embed with surah name and consistent styling
        embed = discord.Embed(
            title=f"📖 {surah_info.get('name_english', 'Unknown Surah')}",
            color=0x3498DB,
        )

        # STEP 2: Add Arabic Name Field
        # Display original Arabic name with formatting
        if surah_info.get("name_arabic"):
            embed.add_field(
                name="🕌 Arabic Name",
                value=f"*{surah_info['name_arabic']}*",
                inline=True,
            )

        # STEP 3: Add Surah Details
        # Show surah number and verse count
        number = surah_info.get("number", "?")
        verses = surah_info.get("verses", 0)
        embed.add_field(
            name="📊 Details", value=f"Surah {number} • {verses} verses", inline=True
        )

        # STEP 4: Add Revelation Context
        # Show whether surah was revealed in Mecca or Medina
        revelation_type = surah_info.get("revelation_type", "")
        if revelation_type:
            location = (
                "🕋 Meccan" if revelation_type.lower() == "meccan" else "🕌 Medinan"
            )
            embed.add_field(name="📍 Revelation", value=location, inline=True)

        # STEP 5: Add Surah Meaning
        # Display the meaning/translation of the surah name
        if surah_info.get("meaning"):
            embed.add_field(
                name="💫 Meaning", value=surah_info["meaning"], inline=False
            )

        # STEP 6: Add Surah Description
        # Include detailed description with length limits
        if surah_info.get("description"):
            description = truncate_text(surah_info["description"], 500)
            embed.add_field(name="📝 Description", value=description, inline=False)

        # STEP 7: Add Footer with Usage Hint
        # Provide guidance on how to use the information
        embed.set_footer(text="Select this surah to begin playback")

        return embed

    except Exception as e:
        TreeLogger.error(
            f"Error creating surah info embed: {e}",
            {"surah_number": surah_info.get("number"), "error_type": type(e).__name__},
            service="ControlPanelEmbeds",
        )

        # Return a basic error embed
        return discord.Embed(
            title="Surah Information",
            description="Unable to display surah information.",
            color=discord.Color.red(),
        )


def create_error_embed(error_message: str, error_type: str = "Error") -> discord.Embed:
    """
    Create standardized error embed with consistent styling.

    Provides user-friendly error messages with consistent formatting,
    appropriate colors, and helpful guidance for error recovery.
    Used throughout the control panel for error communication.

    Args:
        error_message: User-friendly error message to display
        error_type: Category of error for the embed title

    Returns:
        Formatted error embed ready for display
    """
    # Create error embed with red color and timestamp
    embed = discord.Embed(
        title=f"❌ {error_type}",
        description=error_message,
        color=0xFF6B6B,  # Red color for errors
        timestamp=datetime.now(APP_TIMEZONE),
    )

    # Add helpful footer with recovery guidance
    embed.set_footer(text="Please try again or contact support if the issue persists")

    return embed


def create_success_embed(message: str, title: str = "Success") -> discord.Embed:
    """
    Create standardized success embed.

    Args:
        message: Success message to display
        title: Title for the embed

    Returns:
        Formatted success embed
    """
    embed = discord.Embed(
        title=f"✅ {title}",
        description=message,
        color=0x2ECC71,
        timestamp=datetime.now(APP_TIMEZONE),
    )

    return embed


def create_loading_embed(message: str = "Loading...") -> discord.Embed:
    """
    Create loading embed for operations in progress.

    Args:
        message: Loading message to display

    Returns:
        Formatted loading embed
    """
    embed = discord.Embed(title="⏳ Loading", description=message, color=0xF39C12)

    return embed


def create_search_results_embed(
    results: list[dict[str, Any]], query: str
) -> discord.Embed:
    """
    Create embed for displaying search results.

    Args:
        results: List of search result dictionaries
        query: Original search query

    Returns:
        Formatted search results embed
    """
    embed = discord.Embed(title=f"🔍 Search Results for '{query}'", color=0x3498DB)

    if not results:
        embed.description = "No results found. Try a different search term."
        embed.color = 0x95A5A6
        return embed

    # Show first few results in embed
    result_text = []
    for i, result in enumerate(results[:5], 1):
        surah_display = format_surah_display(result, include_verses=False)
        result_text.append(f"{i}. {surah_display}")

    embed.description = "\n".join(result_text)

    if len(results) > 5:
        embed.add_field(
            name="📊 Total Results",
            value=f"Showing 5 of {len(results)} results",
            inline=False,
        )

    embed.set_footer(text="Select a result from the dropdown below")

    return embed


def add_thumbnail_to_embed(embed: discord.Embed, thumbnail_url: str | None = None):
    """
    Add thumbnail to embed if URL is provided.

    Args:
        embed: Discord embed to modify
        thumbnail_url: URL of thumbnail image
    """
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)


def add_author_to_embed(
    embed: discord.Embed, author_name: str, author_icon_url: str | None = None
):
    """
    Add author information to embed.

    Args:
        embed: Discord embed to modify
        author_name: Name of the author
        author_icon_url: URL of author's icon
    """
    embed.set_author(name=author_name, icon_url=author_icon_url)
