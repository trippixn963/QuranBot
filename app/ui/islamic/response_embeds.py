# =============================================================================
# QuranBot - Islamic Response Embeds
# =============================================================================
# Beautiful embed formatting for AI responses
# =============================================================================

import discord
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from ...config import get_config


def create_ai_response_embed(
    question: str,
    response: str,
    user: discord.User,
    context: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    bot: Optional[discord.Client] = None,
    remaining_questions: int = 1
) -> discord.Embed:
    """
    Create a beautiful embed for AI response matching old QuranBot format.
    
    Args:
        question: User's message
        response: AI response
        user: Discord user who asked
        context: Context information (current surah, etc.)
        metadata: Response metadata (tokens, cost, etc.)
        bot: Bot client for fetching developer info
        
    Returns:
        Formatted Discord embed
    """
    # Create main embed with response in code block (no title)
    embed = discord.Embed(
        description=f"```\n{response}\n```",  # Response in code block
        color=0x00D4AA,  # Signature QuranBot green
    )
    
    # Add the user's question as a field
    embed.add_field(
        name="❓ Your Question",
        value=f"```\n{question}\n```",
        inline=False
    )
    
    # Add bot thumbnail
    if bot and bot.user:
        try:
            embed.set_thumbnail(url=bot.user.avatar.url)
        except:
            pass
    
    # Add developer attribution
    config = get_config()
    developer_icon_url = None
    
    # Try to get developer avatar if bot is provided
    if bot and config.developer_id:
        try:
            developer = bot.get_user(config.developer_id)
            if developer and developer.avatar:
                developer_icon_url = developer.avatar.url
        except:
            pass
    
    embed.set_footer(
        text="Developed by حَـــــنَّـــــا",
        icon_url=developer_icon_url
    )
    
    return embed


def create_rate_limit_embed(
    message: str,
    time_remaining: timedelta,
    user: discord.User,
    bot: Optional[discord.Client] = None
) -> discord.Embed:
    """
    Create embed for rate limit message.
    
    Args:
        message: Friendly cooldown message
        time_remaining: Time until next allowed mention
        user: User who hit rate limit
        bot: Bot client for fetching developer info
        
    Returns:
        Formatted Discord embed
    """
    # Calculate exact time when they can ask again
    next_time = datetime.now() + time_remaining
    next_time_str = next_time.strftime("%I:%M %p")
    
    # Combine the messages in a single description with black box formatting
    combined_message = f"JazakAllah Khair for your interest! {message}\n\nYou can send another message at **{next_time_str}**"
    
    embed = discord.Embed(
        title="⏰ Please Wait",
        description=f"```{combined_message}```",
        color=0xFF0000  # Red color as requested
    )
    
    # Add bot thumbnail
    if bot and bot.user and bot.user.avatar:
        try:
            embed.set_thumbnail(url=bot.user.avatar.url)
        except:
            pass
    
    # Add developer attribution only
    config = get_config()
    developer_icon_url = None
    
    # Try to get developer avatar if bot is provided
    if bot and config.developer_id:
        try:
            developer = bot.get_user(config.developer_id)
            if developer and developer.avatar:
                developer_icon_url = developer.avatar.url
        except:
            pass
    
    embed.set_footer(
        text="Developed by حَـــــنَّـــــا",
        icon_url=developer_icon_url
    )
    
    return embed


def create_error_embed_with_pfp(
    title: str,
    description: str,
    bot: Optional[discord.Client] = None,
    color: int = 0xFF0000  # Red by default
) -> discord.Embed:
    """
    Create a standardized error embed with bot profile picture.
    
    Args:
        title: Embed title
        description: Error description
        bot: Bot client for profile picture
        color: Embed color (red by default)
        
    Returns:
        Formatted Discord embed with bot pfp
    """
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    
    # Add bot thumbnail
    if bot and bot.user and bot.user.avatar:
        try:
            embed.set_thumbnail(url=bot.user.avatar.url)
        except:
            pass
    
    # Add developer attribution
    config = get_config()
    developer_icon_url = None
    
    if bot and config.developer_id:
        try:
            developer = bot.get_user(config.developer_id)
            if developer and developer.avatar:
                developer_icon_url = developer.avatar.url
        except:
            pass
    
    embed.set_footer(
        text="Developed by حَـــــنَّـــــا",
        icon_url=developer_icon_url
    )
    
    return embed


def create_ai_error_embed(error_type: str = "generic", bot: Optional[discord.Client] = None) -> discord.Embed:
    """
    Create embed for AI service errors.
    
    Args:
        error_type: Type of error (generic, api, budget, etc.)
        bot: Bot client for profile picture
        
    Returns:
        Formatted Discord embed with bot pfp
    """
    if error_type == "budget":
        return create_error_embed_with_pfp(
            title="💰 Monthly Budget Exceeded",
            description="The AI service has reached its monthly budget limit. "
                       "It will be available again next month, InshaAllah.\n\n"
                       "📅 **Budget Reset**: The budget resets on the 1st of each month",
            bot=bot,
            color=0xFF0000  # Red
        )
    
    elif error_type == "api":
        return create_error_embed_with_pfp(
            title="🔌 Connection Error",
            description="I'm having trouble connecting to my knowledge base. "
                       "Please try again in a few moments.",
            bot=bot,
            color=0xFF0000  # Red
        )
    
    else:  # generic
        return create_error_embed_with_pfp(
            title="❌ Unable to Process",
            description="I encountered an error while processing your message. "
                       "Please try again later.",
            bot=bot,
            color=0xFF0000  # Red
        )