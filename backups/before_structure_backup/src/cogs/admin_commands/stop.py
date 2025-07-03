"""
Stop command for the Quran Bot.
Allows admins to stop the bot gracefully.
"""

import discord
from discord import app_commands
import os
import asyncio
import logging
from datetime import datetime
import traceback
from utils.log_helpers import log_async_function_call, log_function_call, log_operation

# Enhanced logger for admin commands
logger = logging.getLogger(__name__)

def log_operation(operation: str, level: str = "INFO", extra: dict = None, error: Exception = None):
    """Enhanced logging with operation tracking and structured data. No emojis for clean logs."""
    # Format timestamp with new format: MM-DD | HH:MM:SS AM/PM
    timestamp = datetime.now().strftime('%m-%d | %I:%M:%S %p')
    
    log_data = {
        "operation": operation,
        "timestamp": timestamp,
        "component": "admin_stop"
    }
    
    if extra:
        log_data.update(extra)
    
    if error:
        log_data["error"] = str(error)
        log_data["error_type"] = type(error).__name__
        log_data["traceback"] = traceback.format_exc()
        level = "ERROR"
    
    # Include user information in the main log message if available
    user_info = ""
    if extra and "user_name" in extra and "user_id" in extra:
        user_info = f" | User: {extra['user_name']} ({extra['user_id']})"
    
    # Add latency monitoring if response time is available
    latency_info = ""
    if extra and "response_time_ms" in extra:
        latency_info = f" | Response: {extra['response_time_ms']:.2f}ms"
    
    log_message = f"Admin Stop - {operation.upper()}{user_info}{latency_info}"
    
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

def is_admin(interaction: discord.Interaction) -> bool:
    """Check if the user is an admin with enhanced logging."""
    try:
        # Get admin user IDs from environment
        admin_ids = []
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

class StopCommand(app_commands.Group):
    """Stop command for the Quran Bot."""
    
    def __init__(self):
        super().__init__(name="stop", description="Stop the Quran Bot")
        log_operation("init", "INFO", {"component": "StopCommand"})
    
    @app_commands.command(name="stop", description="Stop the Quran Bot")
    @log_async_function_call
    async def stop(self, interaction: discord.Interaction):
        """Stop the bot with enhanced logging and error handling."""
        try:
            log_operation("command", "INFO", {
                "user_id": interaction.user.id,
                "user_name": interaction.user.name,
                "command": "stop",
                "guild_id": interaction.guild.id if interaction.guild else None,
                "channel_id": interaction.channel.id if interaction.channel else None
            })
            
            # Check admin permissions
            if not is_admin(interaction):
                log_operation("auth", "WARNING", {
                    "user_id": interaction.user.id,
                    "user_name": interaction.user.name,
                    "command": "stop",
                    "reason": "not_admin"
                })
                embed = discord.Embed(
                    title="❌ Access Denied",
                    description="You don't have permission to use this command!",
                    color=discord.Color.red()
                )
                embed.add_field(name="Required", value="Admin permissions", inline=True)
                embed.add_field(name="User", value=f"<@{interaction.user.id}>", inline=True)
                embed.set_footer(text="Admin Commands")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Create stop embed
            embed = discord.Embed(
                title="🛑 Bot Stop",
                description="Stopping the Quran Bot...",
                color=discord.Color.red()
            )
            embed.add_field(
                name="⏱️ Status",
                value="The bot will stop in 3 seconds.",
                inline=False
            )
            embed.add_field(
                name="⚠️ Warning",
                value="The bot will completely stop and need to be manually restarted.",
                inline=False
            )
            embed.set_footer(text=f"Requested by {interaction.user.name} • {datetime.now().strftime('%m-%d | %I:%M:%S %p')}")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            log_operation("stop", "INFO", {
                "user_id": interaction.user.id,
                "user_name": interaction.user.name,
                "command": "stop",
                "status": "stop_initiated"
            })
            
            # Wait 3 seconds then stop
            await asyncio.sleep(3)
            
            # Stop the bot
            await interaction.client.close()
            
        except Exception as e:
            log_operation("command", "ERROR", {
                "user_id": interaction.user.id if interaction.user else None,
                "command": "stop",
                "error_details": "stop_command_failed"
            }, e)
            
            try:
                embed = discord.Embed(
                    title="❌ Error",
                    description="An error occurred while stopping the bot. Please try again.",
                    color=discord.Color.red()
                )
                embed.add_field(name="Status", value="Failed", inline=True)
                embed.add_field(name="User", value=f"<@{interaction.user.id}>", inline=True)
                embed.set_footer(text="Admin Commands")
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                pass

async def setup(bot):
    """Setup the stop command with enhanced logging."""
    try:
        log_operation("init", "INFO", {
            "component": "setup",
            "bot_name": bot.user.name if bot.user else "Unknown"
        })
        
        stop_command = StopCommand()
        bot.tree.add_command(stop_command)
        
        log_operation("success", "INFO", {
            "component": "setup",
            "action": "stop_command_loaded",
            "commands": ["stop"]
        })
        
    except Exception as e:
        log_operation("init", "ERROR", {
            "component": "setup",
            "action": "stop_command_failed"
        }, e)
        raise 