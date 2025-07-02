import discord
from discord import app_commands
from datetime import datetime
from typing import Optional, Dict, Any
import os

# Import the main project logger
from utils.logger import logger
from utils.log_helpers import log_async_function_call, log_function_call, log_operation

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

async def credits_command(interaction: discord.Interaction):
    """Admin command to show bot credits and information."""
    # Intensive logging for admin credits command
    channel_name = getattr(interaction.channel, 'name', 'DM') if interaction.channel else None
    
    log_operation("credits", "INFO", {
        "user_id": interaction.user.id,
        "user_name": interaction.user.name,
        "user_display_name": interaction.user.display_name,
        "guild_id": interaction.guild.id if interaction.guild else None,
        "guild_name": interaction.guild.name if interaction.guild else None,
        "channel_id": interaction.channel.id if interaction.channel else None,
        "channel_name": channel_name,
        "action": "admin_credits_command_executed",
        "timestamp": datetime.now().isoformat()
    })
    
    # Get available reciters
    bot = interaction.client
    reciters = getattr(bot, 'get_available_reciters', lambda: [])()
    reciters_text = "\n".join([f"• {reciter}" for reciter in reciters])
    
    # Create credits embed
    embed = discord.Embed(
        title="🕌 QuranBot Credits & Information",
        description="A 24/7 Quran streaming bot with multiple reciters and interactive controls.",
        color=discord.Color.blue()
    )
    
    # Bot Information
    embed.add_field(
        name="🤖 Bot Information",
        value=f"**Name:** Syrian Quran\n"
              f"**Version:** 2.0.0\n"
              f"**Status:** 24/7 Streaming\n"
              f"**Current Reciter:** {getattr(interaction.client, 'current_reciter', 'Unknown')}\n"
              f"**Total Surahs:** 114",
        inline=False
    )
    
    # Creator Information
    embed.add_field(
        name="👨‍💻 Creator",
        value="**Developer:** <@259725211664908288>\n"
              "**Role:** Full-Stack Developer & Bot Creator",
        inline=False
    )
    
    # Available Reciters
    embed.add_field(
        name=f"🎤 Available Reciters ({len(reciters)})",
        value=reciters_text if reciters else "No reciters available",
        inline=False
    )
    
    # Technologies Used
    embed.add_field(
        name="🛠️ Technologies Used",
        value="**Core Framework:** Discord.py\n"
              "**Audio Processing:** FFmpeg\n"
              "**Language:** Python 3.13\n"
              "**Database:** SQLite (State Management)\n"
              "**Logging:** Enhanced Structured Logging\n"
              "**Architecture:** Service-Oriented Design",
        inline=False
    )
    
    # Features
    embed.add_field(
        name="✨ Features",
        value="• 24/7 Continuous Quran Streaming\n"
              "• Multiple Reciter Support\n"
              "• Interactive Control Panel\n"
              "• Dynamic Rich Presence",
        inline=False
    )
    
    # Beta Testing Warning
    embed.add_field(
        name="⚠️ Beta Testing Notice",
        value="**This bot is currently in beta testing.**\n\n"
              "If you encounter any bugs or issues, please DM <@259725211664908288> to report them.\n\n"
              "Your feedback helps improve the bot!",
        inline=False
    )
    
    embed.set_footer(text="Made with ❤️ for the Muslim Ummah • QuranBot v2.0.0")
    embed.timestamp = discord.utils.utcnow()
    
    # Set creator's Discord profile picture
    try:
        creator_user = await interaction.client.fetch_user(259725211664908288)
        if creator_user and creator_user.avatar:
            embed.set_thumbnail(url=creator_user.avatar.url)
    except Exception as e:
        log_operation("credits", "WARNING", {
            "user_id": interaction.user.id,
            "user_name": interaction.user.name,
            "action": "creator_avatar_fetch_failed",
            "error": str(e)
        })
        # Fallback to guild icon if creator avatar fails
        try:
            if interaction.guild and interaction.guild.icon:
                embed.set_thumbnail(url=interaction.guild.icon.url)
        except:
            pass
    
    await interaction.response.send_message(embed=embed, ephemeral=False)
    
    log_operation("credits", "INFO", {
        "user_id": interaction.user.id,
        "user_name": interaction.user.name,
        "action": "admin_credits_displayed",
        "reciters_count": len(reciters),
        "current_reciter": getattr(interaction.client, 'current_reciter', 'Unknown')
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