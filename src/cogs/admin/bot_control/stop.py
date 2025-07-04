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
from monitoring.logging.log_helpers import log_async_function_call, log_function_call
from src.monitoring.logging.tree_log import tree_log

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
    
    # Use tree_log for all admin stop command logging
    if error:
        if extra is None:
            extra = {}
        extra['error'] = str(error)
        extra['error_type'] = type(error).__name__
        extra['traceback'] = traceback.format_exc()
        level = "error"
    else:
        level = level.lower()
    tree_log(level, f"AdminStop - {operation}", extra)

def is_admin(interaction: discord.Interaction) -> bool:
    """Check if the user is an admin with enhanced logging."""
    try:
        # Get admin user IDs from environment
        admin_ids = []
        admin_env = os.getenv('ADMIN_USER_IDS', '')
        if admin_env:
            admin_ids = [int(uid.strip()) for uid in admin_env.split(',') if uid.strip().isdigit()]
        
        user_id = interaction.user.id
        
        tree_log('debug', 'Checking admin permission', {
            "user_id": user_id,
            "user_name": interaction.user.name,
            "admin_ids": admin_ids,
            "check_type": "admin_permission"
        })
        
        if user_id in admin_ids:
            tree_log('info', 'Admin permission granted', {
                "user_id": user_id,
                "user_name": interaction.user.name,
                "check_type": "admin_permission",
                "result": "success"
            })
            return True
        
        tree_log('warning', 'Admin permission denied', {
            "user_id": user_id,
            "user_name": interaction.user.name,
            "check_type": "admin_permission",
            "result": "denied"
        })
        return False
        
    except Exception as e:
        tree_log('error', 'Error during admin permission check', {
            "user_id": interaction.user.id if interaction.user else None,
            "check_type": "admin_permission",
            "error_details": "admin_check_failed",
            "traceback": traceback.format_exc()
        })
        return False

class StopCommand(app_commands.Group):
    """Stop command for the Quran Bot."""
    
    def __init__(self):
        super().__init__(name="stop", description="Stop the Quran Bot")
        tree_log('info', 'StopCommand initialized', {"component": "StopCommand"})
    
    @app_commands.command(name="stop", description="Stop the Quran Bot")
    @log_async_function_call
    async def stop(self, interaction: discord.Interaction):
        """Stop the bot with enhanced logging and error handling."""
        try:
            tree_log('info', 'Stop command invoked', {
                "user_id": interaction.user.id,
                "user_name": interaction.user.name,
                "command": "stop",
                "guild_id": interaction.guild.id if interaction.guild else None,
                "channel_id": interaction.channel.id if interaction.channel else None
            })
            
            # Check admin permissions
            if not is_admin(interaction):
                tree_log('warning', 'Stop denied: not admin', {
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

            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            tree_log('info', 'Stop initiated', {
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
            tree_log('error', 'Error during stop command', {
                "user_id": interaction.user.id if interaction.user else None,
                "command": "stop",
                "error_details": "stop_command_failed",
                "traceback": traceback.format_exc()
            })
            
            try:
                embed = discord.Embed(
                    title="❌ Error",
                    description="An error occurred while stopping the bot. Please try again.",
                    color=discord.Color.red()
                )
                embed.add_field(name="Status", value="Failed", inline=True)
                embed.add_field(name="User", value=f"<@{interaction.user.id}>", inline=True)

                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                pass

async def setup(bot):
    """Setup the stop command with enhanced logging."""
    try:
        tree_log('info', 'Setting up stop command', {
            "component": "setup",
            "bot_name": bot.user.name if bot.user else "Unknown"
        })
        
        stop_command = StopCommand()
        bot.tree.add_command(stop_command)
        
        tree_log('info', 'Stop command loaded', {
            "component": "setup",
            "action": "stop_command_loaded",
            "commands": ["stop"]
        })
        
    except Exception as e:
        tree_log('error', 'Error during stop command setup', {
            "component": "setup",
            "action": "stop_command_failed",
            "traceback": traceback.format_exc()
        })
        raise 
