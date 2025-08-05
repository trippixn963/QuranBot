# =============================================================================
# QuranBot - UI Formatters
# =============================================================================
# Formatting utilities for time, text, progress bars, and display elements
# used across Discord UI components.
# =============================================================================

import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from ...config.timezone import APP_TIMEZONE


def format_time_elapsed(start_time: datetime, current_time: Optional[datetime] = None) -> str:
    """
    Format elapsed time in human-readable format.
    
    Args:
        start_time: Starting datetime
        current_time: Current datetime (defaults to now)
        
    Returns:
        Formatted time string (e.g., "2m 30s", "1h 15m", "45s")
    """
    if current_time is None:
        current_time = datetime.now(APP_TIMEZONE)
    
    elapsed = current_time - start_time
    total_seconds = int(elapsed.total_seconds())
    
    if total_seconds < 0:
        return "0s"
    
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


def format_progress_bar(position: float, duration: float, length: int = 20) -> str:
    """
    Create a visual progress bar for audio playback.
    
    Args:
        position: Current position in seconds
        duration: Total duration in seconds
        length: Length of progress bar in characters
        
    Returns:
        Progress bar string with filled and empty segments
    """
    if duration <= 0:
        return "▱" * length
    
    # Safety check: ensure position never exceeds duration
    safe_position = max(0.0, min(position, duration))
    
    progress = min(safe_position / duration, 1.0)
    filled_length = int(progress * length)
    
    filled_chars = "▰" * filled_length
    empty_chars = "▱" * (length - filled_length)
    
    return filled_chars + empty_chars


def format_time_duration(seconds: float) -> str:
    """
    Format duration in MM:SS or HH:MM:SS format.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted time string
    """
    if seconds < 0 or seconds != seconds:  # Check for negative or NaN
        return "00:00"
    
    # Cap extremely large values to prevent overflow
    if seconds > 86400:  # More than 24 hours
        seconds = 86400
    
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to specified length with suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add when truncating
        
    Returns:
        Truncated text with suffix if needed
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def format_activity_display(user: Dict[str, Any], action: str, timestamp: datetime) -> str:
    """
    Format user activity for display in control panel.
    
    Args:
        user: User information dictionary
        action: Action performed
        timestamp: When action occurred
        
    Returns:
        Formatted activity string
    """
    username = truncate_text(user.get("username", "Unknown"), 15)
    time_ago = format_time_elapsed(timestamp)
    action_display = truncate_text(action, 20)
    
    return f"**{username}** {action_display} *{time_ago} ago*"


def format_surah_display(surah_info: Dict[str, Any], include_verses: bool = True) -> str:
    """
    Format Surah information for display.
    
    Args:
        surah_info: Surah information dictionary
        include_verses: Whether to include verse count
        
    Returns:
        Formatted Surah display string
    """
    number = surah_info.get("number", "?")
    name_english = surah_info.get("name_english", "Unknown")
    name_arabic = surah_info.get("name_arabic", "")
    verses = surah_info.get("verses", 0)
    
    display = f"**{number}. {name_english}**"
    
    if name_arabic:
        display += f" • *{name_arabic}*"
    
    if include_verses and verses > 0:
        display += f" • {verses} verses"
    
    return display


def format_reciter_display(reciter_info: Dict[str, Any]) -> str:
    """
    Format reciter information for display.
    
    Args:
        reciter_info: Reciter information dictionary
        
    Returns:
        Formatted reciter display string
    """
    name = reciter_info.get("name", "Unknown")
    name_arabic = reciter_info.get("name_arabic", "")
    
    display = f"**{name}**"
    
    if name_arabic and name_arabic != name:
        display += f" • *{name_arabic}*"
    
    return display


def format_percentage(value: float, decimal_places: int = 1) -> str:
    """
    Format a decimal as a percentage.
    
    Args:
        value: Decimal value (0.0 to 1.0)
        decimal_places: Number of decimal places
        
    Returns:
        Formatted percentage string
    """
    percentage = value * 100
    return f"{percentage:.{decimal_places}f}%"


def format_file_size(bytes_size: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        bytes_size: Size in bytes
        
    Returns:
        Formatted size string (e.g., "1.5 MB", "512 KB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"


def clean_text_for_discord(text: str) -> str:
    """
    Clean text for Discord display by removing/escaping special characters.
    
    Args:
        text: Text to clean
        
    Returns:
        Cleaned text safe for Discord
    """
    # Escape Discord markdown characters
    discord_chars = ['*', '_', '`', '~', '\\', '|']
    for char in discord_chars:
        text = text.replace(char, f'\\{char}')
    
    # Remove control characters except newlines and tabs
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    return text


def format_emoji_number(number: int) -> str:
    """
    Convert number to emoji representation.
    
    Args:
        number: Number to convert (0-9)
        
    Returns:
        Emoji representation of number
    """
    emoji_map = {
        0: "0️⃣", 1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣",
        5: "5️⃣", 6: "6️⃣", 7: "7️⃣", 8: "8️⃣", 9: "9️⃣"
    }
    return emoji_map.get(number, str(number))


def format_list_display(items: List[str], max_items: int = 5, separator: str = " • ") -> str:
    """
    Format a list for display with optional truncation.
    
    Args:
        items: List of items to format
        max_items: Maximum items to show
        separator: Separator between items
        
    Returns:
        Formatted list string
    """
    if not items:
        return "None"
    
    display_items = items[:max_items]
    result = separator.join(display_items)
    
    if len(items) > max_items:
        remaining = len(items) - max_items
        result += f" and {remaining} more..."
    
    return result


def format_status_indicator(is_active: bool, active_text: str = "🟢 Active", 
                          inactive_text: str = "🔴 Inactive") -> str:
    """
    Format status indicator with emoji.
    
    Args:
        is_active: Whether status is active
        active_text: Text for active status
        inactive_text: Text for inactive status
        
    Returns:
        Formatted status string
    """
    return active_text if is_active else inactive_text