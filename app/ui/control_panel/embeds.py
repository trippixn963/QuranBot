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
from typing import Dict, Any, Optional, List

# Third-party imports
import discord

# Local imports - base components
from ..base.formatters import (
    format_time_duration,
    format_progress_bar,
    format_surah_display,
    format_reciter_display,
    format_activity_display,
    format_percentage,
    truncate_text
)

# Local imports - config
from ...config.timezone import APP_TIMEZONE

# Local imports - core modules
from ...core.errors import ErrorHandler
from ...core.logger import TreeLogger

# Initialize error handler for embeds
error_handler = ErrorHandler()


def create_status_embed(audio_state: Dict[str, Any], activity_info: Optional[Dict[str, Any]] = None) -> discord.Embed:
    """
    Create the main status embed matching the exact design from the screenshot.
    
    Args:
        audio_state: Current audio playbook state
        activity_info: Recent user activity information
        
    Returns:
        Formatted Discord embed matching the original design
    """
    try:
        TreeLogger.debug("Creating status embed", {
            "has_audio_state": bool(audio_state),
            "has_activity_info": bool(activity_info),
            "is_playing": audio_state.get("is_playing", False) if audio_state else False,
            "surah_number": audio_state.get("current_surah", {}).get("number") if audio_state and audio_state.get("current_surah") else None,
            "reciter": audio_state.get("current_reciter", {}).get("name") if audio_state and audio_state.get("current_reciter") else None,
            "position": audio_state.get("position", 0) if audio_state else 0,
            "duration": audio_state.get("duration", 0) if audio_state else 0,
            "current_surah": audio_state.get("current_surah", {}).get("number") if audio_state else None,
            "is_playing": audio_state.get("is_playing", False) if audio_state else False
        }, service="ControlPanelEmbeds")
        
        # Extract audio information with safe defaults
        if not audio_state:
            audio_state = {}
        
        current_surah = audio_state.get("current_surah", {})
        current_reciter = audio_state.get("current_reciter", {})
        position = audio_state.get("position", 0)
        duration = audio_state.get("duration", 0)
        is_playing = audio_state.get("is_playing", False)
    
        # Get surah information from audio state
        surah_number = current_surah.get("number", 1)
        # Try both name formats for compatibility
        surah_name = current_surah.get("name_english", "Al-Fatiha")
        surah_arabic = current_surah.get("name_arabic", "الفاتحة")
        # Handle reciter name - could be enum value or string
        reciter_raw = current_reciter.get("name", "Saad Al Ghamdi")
        if hasattr(reciter_raw, 'value'):
            reciter_name = reciter_raw.value
        elif isinstance(reciter_raw, str) and '.' in reciter_raw and reciter_raw.startswith('ReciterName'):
            # Handle "ReciterName.SAAD_AL_GHAMDI" format
            reciter_name = reciter_raw.split('.')[-1].replace('_', ' ').title()
        else:
            reciter_name = str(reciter_raw)
        
        reciter_arabic = current_reciter.get("name_arabic", "سعد الغامدي")
    
        # Calculate progress
        if duration > 0:
            # Safety check: ensure position never exceeds duration
            safe_position = max(0.0, min(position, duration))
            progress_percent = int((safe_position / duration) * 100)
            position_str = format_time_duration(safe_position)
            duration_str = format_time_duration(duration)
        else:
            # When duration is unknown, show 0:00 / 0:00
            progress_percent = 0
            position_str = "0:00"
            duration_str = "0:00"
    
        # Create embed with exact styling from screenshot
        embed = discord.Embed(
            color=0x2f3136  # Dark theme color
        )
        
        # Main status section with black boxes for better visibility
        status_text = f"**Surah:** ```{surah_name} - {surah_arabic}```\n\n"
        status_text += f"**Reciter:** ```{reciter_name} - {reciter_arabic}```\n\n"
        status_text += f"**Progress:** ```{position_str} / {duration_str}```\n"
        
        # Progress bar with black box
        progress_bar = format_progress_bar(position, duration, length=20)
        status_text += f"```{progress_bar} {progress_percent}%```"
        
        embed.description = status_text
    
        # Add last activity tracking at the bottom
        if activity_info and activity_info.get("last_activity"):
            last_activity = activity_info["last_activity"]
            if (last_activity.get("user") and 
                last_activity.get("action") and 
                last_activity.get("time_elapsed")):
                
                user_id = last_activity["user"].get("id")
                action = last_activity["action"]
                time_elapsed = last_activity["time_elapsed"]
                
                embed.add_field(
                    name="",
                    value=f"**Last Activity:** <@{user_id}> {action} • `{time_elapsed}`",
                    inline=False
                )
        
        TreeLogger.success("Status embed created successfully", {
            "embed_length": len(embed.description or ""),
            "embed_color": embed.color,
            "has_surah_info": bool(current_surah),
            "has_reciter_info": bool(current_reciter)
        }, service="ControlPanelEmbeds")
        
        return embed
    
    except Exception as e:
        TreeLogger.error(f"Error creating status embed: {e}", {
            "has_audio_state": bool(audio_state),
            "has_activity_info": bool(activity_info),
            "error_type": type(e).__name__
        }, service="ControlPanelEmbeds")
        
        # Return a basic error embed
        embed = discord.Embed(
            title="🕌 QuranBot Status",
            description="Unable to display status. Please try again later.",
            color=discord.Color.red()
        )
        return embed


def create_surah_info_embed(surah_info: Dict[str, Any]) -> discord.Embed:
    """
    Create information embed for a specific surah.
    
    Args:
        surah_info: Surah information dictionary
        
    Returns:
        Formatted Discord embed with surah details
    """
    try:
        embed = discord.Embed(
            title=f"📖 {surah_info.get('name_english', 'Unknown Surah')}",
            color=0x3498DB
        )
        
        # Arabic name
        if surah_info.get("name_arabic"):
            embed.add_field(
                name="🕌 Arabic Name",
                value=f"*{surah_info['name_arabic']}*",
                inline=True
            )
        
        # Number and verses
        number = surah_info.get("number", "?")
        verses = surah_info.get("verses", 0)
        embed.add_field(
            name="📊 Details",
            value=f"Surah {number} • {verses} verses",
            inline=True
        )
        
        # Revelation type
        revelation_type = surah_info.get("revelation_type", "")
        if revelation_type:
            location = "🕋 Meccan" if revelation_type.lower() == "meccan" else "🕌 Medinan"
            embed.add_field(
                name="📍 Revelation",
                value=location,
                inline=True
            )
        
        # Meaning
        if surah_info.get("meaning"):
            embed.add_field(
                name="💫 Meaning",
                value=surah_info["meaning"],
                inline=False
            )
    
        # Description
        if surah_info.get("description"):
            description = truncate_text(surah_info["description"], 500)
            embed.add_field(
                name="📝 Description",
                value=description,
                inline=False
            )
        
        embed.set_footer(text="Select this surah to begin playback")
        
        return embed
    
    except Exception as e:
        TreeLogger.error(f"Error creating surah info embed: {e}", {
            "surah_number": surah_info.get("number"),
            "error_type": type(e).__name__
        }, service="ControlPanelEmbeds")
        
        # Return a basic error embed
        return discord.Embed(
            title="Surah Information",
            description="Unable to display surah information.",
            color=discord.Color.red()
        )


def create_error_embed(error_message: str, error_type: str = "Error") -> discord.Embed:
    """
    Create standardized error embed.
    
    Args:
        error_message: Error message to display
        error_type: Type of error (for title)
        
    Returns:
        Formatted error embed
    """
    embed = discord.Embed(
        title=f"❌ {error_type}",
        description=error_message,
        color=0xFF6B6B,
        timestamp=datetime.now(APP_TIMEZONE)
    )
    
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
        timestamp=datetime.now(APP_TIMEZONE)
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
    embed = discord.Embed(
        title="⏳ Loading",
        description=message,
        color=0xF39C12
    )
    
    return embed


def create_search_results_embed(results: List[Dict[str, Any]], query: str) -> discord.Embed:
    """
    Create embed for displaying search results.
    
    Args:
        results: List of search result dictionaries
        query: Original search query
        
    Returns:
        Formatted search results embed
    """
    embed = discord.Embed(
        title=f"🔍 Search Results for '{query}'",
        color=0x3498DB
    )
    
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
            inline=False
        )
    
    embed.set_footer(text="Select a result from the dropdown below")
    
    return embed


def add_thumbnail_to_embed(embed: discord.Embed, thumbnail_url: Optional[str] = None):
    """
    Add thumbnail to embed if URL is provided.
    
    Args:
        embed: Discord embed to modify
        thumbnail_url: URL of thumbnail image
    """
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)


def add_author_to_embed(embed: discord.Embed, author_name: str, 
                       author_icon_url: Optional[str] = None):
    """
    Add author information to embed.
    
    Args:
        embed: Discord embed to modify
        author_name: Name of the author
        author_icon_url: URL of author's icon
    """
    embed.set_author(name=author_name, icon_url=author_icon_url)