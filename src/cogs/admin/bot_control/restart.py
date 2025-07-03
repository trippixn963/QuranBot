import discord
from discord import app_commands
import os
import time
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any

# Enhanced logger for admin commands
logger = logging.getLogger(__name__)

def log_operation(operation: str, level: str = "INFO", extra: Optional[Dict[str, Any]] = None, error: Optional[Exception] = None):
    """Enhanced logging with operation tracking and structured data."""
    emoji_map = {
        "init": "🚀", "auth": "🔐", "command": "⚡", "restart": "🔄", 
        "reciter": "🎤", "error": "❌", "success": "✅", "check": "🔍"
    }
    
    emoji = emoji_map.get(operation, "ℹ️")
    level_emoji = {"DEBUG": "🔍", "INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌", "CRITICAL": "🔥"}
    
    # Format timestamp with new format: MM-DD | HH:MM:SS AM/PM
    timestamp = datetime.now().strftime('%m-%d | %I:%M:%S %p')
    
    log_data = {
        "operation": operation,
        "timestamp": timestamp,
        "component": "admin_commands"
    }
    
    if extra:
        log_data.update(extra)
    
    if error:
        log_data["error"] = str(error)
        log_data["error_type"] = type(error).__name__
        level = "ERROR"
    
    log_message = f"{emoji} {level_emoji.get(level, 'ℹ️')} Admin Commands - {operation.upper()}"
    
    if level == "DEBUG":
        logger.debug(log_message, extra={"extra": log_data})
    elif level == "INFO":
        logger.info(log_message, extra={"extra": log_data})
    elif level == "WARNING":
        logger.warning(log_message, extra={"extra": log_data})
    elif level == "ERROR":
        logger.error(log_message, extra={"extra": log_data})
    elif level == "CRITICAL":
        logger.critical(log_message, extra={"extra": log_data})

# Get admin ID from environment variable
ADMIN_USER_IDS = os.getenv('ADMIN_USER_IDS', '').split(',') if os.getenv('ADMIN_USER_IDS') else []

def is_admin(interaction: discord.Interaction) -> bool:
    """Check if the user is an admin with enhanced logging."""
    try:
        from core.config.config import Config
        
        # Get admin user IDs from environment
        admin_ids = []
        import os
        admin_env = os.getenv('ADMIN_USER_IDS', '')
        if admin_env:
            admin_ids = [int(uid.strip()) for uid in admin_env.split(',') if uid.strip().isdigit()]
        
        user_id = interaction.user.id
        
        log_operation("check", "DEBUG", {
            "user_id": user_id,
            "user_name": interaction.user.name,
            "admin_ids": admin_ids,
            "check_type": "admin_permission"
        })
        
        if user_id in admin_ids:
            log_operation("auth", "INFO", {
                "user_id": user_id,
                "user_name": interaction.user.name,
                "check_type": "admin_permission",
                "result": "success"
            })
            return True
        
        log_operation("auth", "WARNING", {
            "user_id": user_id,
            "user_name": interaction.user.name,
            "check_type": "admin_permission",
            "result": "denied"
        })
        return False
        
    except Exception as e:
        log_operation("check", "ERROR", {
            "user_id": interaction.user.id if interaction.user else None,
            "check_type": "admin_permission",
            "error_details": "admin_check_failed"
        }, e)
        return False

class AdminCommands(app_commands.Group):
    """Admin commands for the Quran Bot."""
    
    def __init__(self):
        super().__init__(name="admin", description="Admin commands for Quran Bot")
        log_operation("init", "INFO", {"component": "AdminCommands"})
    
    @app_commands.command(name="restart", description="Restart the Quran Bot")
    async def restart(self, interaction: discord.Interaction):
        """Restart the bot with enhanced logging and error handling."""
        try:
            log_operation("command", "INFO", {
                "user_id": interaction.user.id,
                "user_name": interaction.user.name,
                "command": "restart",
                "guild_id": interaction.guild.id if interaction.guild else None,
                "channel_id": interaction.channel.id if interaction.channel else None
            })
            
            # Check admin permissions
            if not is_admin(interaction):
                log_operation("auth", "WARNING", {
                    "user_id": interaction.user.id,
                    "user_name": interaction.user.name,
                    "command": "restart",
                    "reason": "not_admin"
                })
                embed = discord.Embed(
                    title="❌ Access Denied",
                    description="You don't have permission to use this command!",
                    color=discord.Color.red()
                )
                embed.add_field(name="Required", value="Admin permissions", inline=True)
                embed.add_field(name="User", value=f"<@{interaction.user.id}>", inline=True)
                
                # Add creator as author and bot as thumbnail
                try:
                    creator = await interaction.client.fetch_user(259725211664908288)
                    if creator and creator.avatar:
                        embed.set_author(name=creator.name, icon_url=creator.avatar.url)
                except Exception as e:
                    log_operation("auth", "WARNING", {"error": str(e)})
                
                if interaction.client.user and interaction.client.user.avatar:
                    embed.set_thumbnail(url=interaction.client.user.avatar.url)
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Create restart embed
            embed = discord.Embed(
                title="🔄 Bot Restart",
                description="Restarting the Quran Bot...",
                color=discord.Color.orange()
            )
            embed.add_field(
                name="⏱️ Status",
                value="The bot will restart in 3 seconds.",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            log_operation("restart", "INFO", {
                "user_id": interaction.user.id,
                "user_name": interaction.user.name,
                "command": "restart",
                "status": "restart_initiated"
            })
            
            # Wait 3 seconds then restart
            await asyncio.sleep(3)
            
            # Trigger restart
            await interaction.client.close()
            
        except Exception as e:
            log_operation("command", "ERROR", {
                "user_id": interaction.user.id if interaction.user else None,
                "command": "restart",
                "error_details": "restart_command_failed"
            }, e)
            
            try:
                await interaction.response.send_message(
                    "❌ An error occurred while restarting the bot. Please try again.",
                    ephemeral=True
                )
            except:
                pass

async def setup(bot):
    """Setup the admin commands with enhanced logging."""
    try:
        log_operation("init", "INFO", {
            "component": "setup",
            "bot_name": bot.user.name if bot.user else "Unknown"
        })
        
        admin_commands = AdminCommands()
        bot.tree.add_command(admin_commands)
        
        log_operation("success", "INFO", {
            "component": "setup",
            "action": "admin_commands_loaded",
            "commands": ["restart"]
        })
        
    except Exception as e:
        log_operation("error", "CRITICAL", {
            "component": "setup",
            "error_details": "setup_failed"
        }, e) 
