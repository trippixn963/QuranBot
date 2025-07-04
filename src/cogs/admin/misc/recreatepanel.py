import discord
from discord import app_commands
import os
import time
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from src.monitoring.logging.tree_log import tree_log

# Enhanced logger for admin commands
logger = logging.getLogger(__name__)

def log_operation(operation: str, level: str = "INFO", extra: Optional[Dict[str, Any]] = None, error: Optional[Exception] = None):
    """Enhanced logging with operation tracking and structured data."""
    # Format timestamp with new format: MM-DD | HH:MM:SS AM/PM
    timestamp = datetime.now().strftime('%m-%d | %I:%M:%S %p')
    
    log_data = {
        "operation": operation,
        "timestamp": timestamp,
        "component": "admin_recreatepanel"
    }
    
    if extra:
        log_data.update(extra)
    
    if error:
        log_data["error"] = str(error)
        log_data["error_type"] = type(error).__name__
        import traceback
        log_data["traceback"] = traceback.format_exc()
        level = "ERROR"
    
    # Use tree_log for all admin recreatepanel command logging
    tree_log(level.lower(), f"AdminRecreatePanel - {operation}", log_data)

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
        import traceback
        tree_log('error', 'Error during admin permission check', {
            "user_id": interaction.user.id if interaction.user else None,
            "check_type": "admin_permission",
            "error_details": "admin_check_failed",
            "traceback": traceback.format_exc()
        })
        return False

@app_commands.command(name="recreatepanel", description="Recreate the control panel (Admin only)")
async def recreatepanel(interaction: discord.Interaction):
    """Recreate the control panel with enhanced logging and error handling."""
    try:
        tree_log('info', 'Recreatepanel command invoked', {
            "user_id": interaction.user.id,
            "user_name": interaction.user.name,
            "command": "recreatepanel",
            "guild_id": interaction.guild.id if interaction.guild else None,
            "channel_id": interaction.channel.id if interaction.channel else None
        })
        
        # Check admin permissions
        if not is_admin(interaction):
            tree_log('warning', 'Recreatepanel denied: not admin', {
                "user_id": interaction.user.id,
                "user_name": interaction.user.name,
                "command": "recreatepanel",
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
        
        # Create initial response embed
        embed = discord.Embed(
            title="🔄 Recreating Control Panel",
            description="Deleting old panel and creating a new one...",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="⏱️ Status",
            value="Processing...",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        tree_log('info', 'Recreate initiated', {
            "user_id": interaction.user.id,
            "user_name": interaction.user.name,
            "command": "recreatepanel",
            "status": "recreate_initiated"
        })
        
        # Import required modules
        try:
            from core.config.config import Config
            tree_log('debug', 'Config import success', {"component": "config_import", "status": "success"})
        except Exception as e:
            import traceback
            tree_log('error', 'Config import failed', {"component": "config_import", "error_details": "import_failed", "traceback": traceback.format_exc()})
            raise
        
        # Get the target channel
        panel_channel_id = Config.PANEL_CHANNEL_ID
        
        # Find the channel
        channel = None
        for guild in interaction.client.guilds:
            channel = guild.get_channel(panel_channel_id)
            if channel:
                break
        
        if not channel:
            tree_log('error', 'Panel channel not found', {
                "error": "Panel channel not found",
                "panel_channel_id": panel_channel_id
            })
            raise Exception("Panel channel not found")
        
        # Delete all messages in the channel (clear the whole chat)
        try:
            tree_log('info', 'Clearing channel', {
                "action": "clearing_channel",
                "channel_id": channel.id,
                "channel_name": channel.name
            })
            
            # Delete all messages in the channel
            deleted_count = 0
            async for message in channel.history(limit=None):  # No limit to delete all messages
                try:
                    await message.delete()
                    deleted_count += 1
                except Exception as delete_error:
                    # Skip messages we can't delete (e.g., too old)
                    continue
            
            tree_log('info', 'Channel cleared', {
                "action": "channel_cleared",
                "deleted_count": deleted_count,
                "channel_id": channel.id
            })
            
        except Exception as e:
            tree_log('warning', 'Failed to clear channel', {
                "error": f"Failed to clear channel: {str(e)}",
                "channel_id": channel.id
            })
        
        # Wait a moment
        await asyncio.sleep(1)
        
        # Trigger panel recreation by calling the setup function
        try:
            tree_log('info', 'Triggering panel recreation', {"phase": "trigger_panel_recreation"})
            
            # Import and call the control panel setup
            from cogs.user_commands.control_panel import setup as control_panel_setup
            await control_panel_setup(interaction.client)
            
            tree_log('info', 'Panel recreation triggered', {"phase": "panel_recreation_triggered", "status": "success"})
        except Exception as e:
            import traceback
            tree_log('error', 'Panel recreation failed', {"phase": "panel_recreation", "error_details": "recreation_failed", "traceback": traceback.format_exc()})
            raise
        
        # Success embed
        success_embed = discord.Embed(
            title="✅ Control Panel Recreated",
            description="The control panel has been successfully recreated!",
            color=discord.Color.green()
        )
        success_embed.add_field(
            name="🎯 Status",
            value="Panel recreated successfully",
            inline=False
        )
        success_embed.add_field(
            name="👤 Admin",
            value=f"<@{interaction.user.id}>",
            inline=True
        )
        success_embed.add_field(
            name="⏰ Time",
            value=f"<t:{int(time.time())}:F>",
            inline=True
        )
        
        tree_log('info', 'Recreate completed', {
            "user_id": interaction.user.id,
            "user_name": interaction.user.name,
            "command": "recreatepanel",
            "status": "recreate_completed"
        })
        
        await interaction.edit_original_response(embed=success_embed)
        
    except Exception as e:
        import traceback
        tree_log('error', 'Error during recreatepanel command', {
            "user_id": interaction.user.id if interaction.user else None,
            "command": "recreatepanel",
            "error_details": "recreatepanel_command_failed",
            "traceback": traceback.format_exc()
        })
        
        try:
            error_embed = discord.Embed(
                title="❌ Error",
                description="An error occurred while recreating the control panel. Please try again.",
                color=discord.Color.red()
            )
            error_embed.add_field(name="Status", value="Failed", inline=True)
            error_embed.add_field(name="User", value=f"<@{interaction.user.id}>", inline=True)
            
            await interaction.edit_original_response(embed=error_embed)
        except:
            pass

@recreatepanel.error
async def recreatepanel_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Handle errors for recreatepanel command."""
    if isinstance(error, app_commands.CheckFailure):
        embed = discord.Embed(
            title="❌ Access Denied",
            description="This command is only available to the bot administrator.",
            color=discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        embed = discord.Embed(
            title="❌ Error",
            description=f"An error occurred: {str(error)}",
            color=discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    """Setup the recreatepanel command with enhanced logging."""
    try:
        tree_log('info', 'Setting up recreatepanel command', {
            "component": "setup",
            "bot_name": bot.user.name if bot.user else "Unknown"
        })
        
        bot.tree.add_command(recreatepanel)
        
        tree_log('info', 'Recreatepanel command added', {
            "component": "setup",
            "status": "recreatepanel_command_added"
        })
        
    except Exception as e:
        import traceback
        tree_log('error', 'Error during recreatepanel command setup', {
            "component": "setup",
            "error_details": "setup_failed",
            "traceback": traceback.format_exc()
        })
        raise 