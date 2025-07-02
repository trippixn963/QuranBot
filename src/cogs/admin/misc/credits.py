import discord
from discord import app_commands
from datetime import datetime
from typing import Optional, Dict, Any
import os

# Import the main project logger
from monitoring.logging.logger import logger
from monitoring.logging.log_helpers import log_async_function_call, log_function_call, log_operation

def log_operation(operation: str, level: str = "INFO", extra: Optional[Dict[str, Any]] = None, error: Optional[Exception] = None):
    """Enhanced logging for admin credits command with emoji-structured format."""
    operation_emojis = {
        "credits": "📋",
        "admin": "👑",
        "error": "❌"
    }
    
    level_emojis = {
        "DEBUG": "🔍",
        "INFO": "ℹ️",
        "WARNING": "⚠️",
        "ERROR": "❌",
        "CRITICAL": "🔥"
    }
    
    emoji = operation_emojis.get(operation, "📋")
    level_emoji = level_emojis.get(level, "ℹ️")
    
    log_data = {
        "operation": operation,
        "component": "admin_credits",
        "timestamp": datetime.now().isoformat()
    }
    
    if extra:
        log_data.update(extra)
    
    if error:
        log_data["error"] = str(error)
        log_data["error_type"] = type(error).__name__
    
    log_message = f"{emoji} {level_emoji} Admin Credits - {operation.upper()}"
    
    if level == "DEBUG":
        logger.debug(log_message, extra=log_data)
    elif level == "INFO":
        logger.info(log_message, extra=log_data)
    elif level == "WARNING":
        logger.warning(log_message, extra=log_data)
    elif level == "ERROR":
        logger.error(log_message, extra=log_data)
    elif level == "CRITICAL":
        logger.critical(log_message, extra=log_data)

async def create_credits_embed(bot, interaction: discord.Interaction) -> discord.Embed:
    """Create a clean, streamlined credits embed with repository link and bot avatar."""
    # Get current bot status
    current_reciter = getattr(bot, 'current_reciter', 'Unknown')
    reciters = getattr(bot, 'get_available_reciters', lambda: [])()
    
    embed = discord.Embed(
        title="🕌 QuranBot - Credits",
        description="**24/7 Quran streaming bot** with multiple reciters and interactive controls.\n"
                   "Built with ❤️ for the Muslim Ummah.",
        color=0x00D4AA,  # Islamic green
        timestamp=datetime.now()
    )
    
    # Current Status (compact)
    embed.add_field(
        name="📊 Status", 
        value=f"🎵 **{current_reciter}**\n"
              f"🔢 **{len(reciters)} Reciters**\n"
              f"📖 **114 Surahs**", 
        inline=True
    )
    
    # Repository & Version
    embed.add_field(
        name="🔗 Repository", 
        value="[**GitHub Repository**](https://github.com/JohnHamwi/QuranAudioBot)\n"
              f"**Version:** 2.0.0\n"
              f"**Language:** Python 3.13", 
        inline=True
    )
    
    # Developer
    embed.add_field(
        name="👨‍💻 Developer", 
        value="<@259725211664908288>\n"
              "**Full-Stack Developer**", 
        inline=True
    )
    
    # Features (streamlined)
    embed.add_field(
        name="✨ Key Features",
        value="• 24/7 Continuous Streaming\n"
              "• Multiple Professional Reciters\n"
              "• Interactive Control Panel\n"
              "• Real-time Activity Logging",
        inline=False
    )
    
    # Set bot profile picture as thumbnail
    if bot.user and bot.user.avatar:
        embed.set_thumbnail(url=bot.user.avatar.url)
    
    return embed

async def credits_command(interaction: discord.Interaction):
    """Show bot credits and information with clean design."""
    bot = interaction.client
    
    # Log the command usage
    log_operation("credits", "INFO", {
        "user_id": interaction.user.id,
        "user_name": interaction.user.name,
        "action": "credits_command_executed",
        "timestamp": datetime.now().isoformat()
    })
    
    # Create the new clean credits embed
    embed = await create_credits_embed(bot, interaction)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)
    
    log_operation("credits", "INFO", {
        "user_id": interaction.user.id,
        "user_name": interaction.user.name,
        "action": "credits_displayed"
    })

async def setup(bot):
    """Setup the admin credits command."""
    try:
        log_operation("init", "INFO", {
            "component": "setup",
            "bot_name": bot.user.name if bot.user else "Unknown"
        })
        
        # Create the command
        credits_command_obj = app_commands.Command(
            name="credits",
            description="Show bot credits and information (Admin only)",
            callback=credits_command,
            parent=None
        )
        
        # Add default permissions
        credits_command_obj.default_permissions = discord.Permissions(administrator=True)
        
        # Add to command tree
        bot.tree.add_command(credits_command_obj)
        
        log_operation("init", "INFO", {
            "component": "setup",
            "status": "success",
            "command": "credits"
        })
        
    except Exception as e:
        log_operation("error", "CRITICAL", {
            "component": "setup",
            "error_details": "setup_failed",
            "error": str(e)
        }, e)
        raise 