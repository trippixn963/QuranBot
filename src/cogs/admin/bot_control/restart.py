import discord
from discord import app_commands
import os
import time
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import traceback
from src.monitoring.logging.tree_log import tree_log

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

class AdminCommands(app_commands.Group):
    """Admin commands for the Quran Bot."""
    
    def __init__(self):
        super().__init__(name="admin", description="Admin commands for Quran Bot")
        tree_log('info', 'AdminCommands initialized', {"component": "AdminCommands"})
    
    @app_commands.command(name="restart", description="Restart the Quran Bot")
    async def restart(self, interaction: discord.Interaction):
        """Restart the bot with enhanced logging and error handling."""
        try:
            tree_log('info', 'Restart command invoked', {
                "user_id": interaction.user.id,
                "user_name": interaction.user.name,
                "command": "restart",
                "guild_id": interaction.guild.id if interaction.guild else None,
                "channel_id": interaction.channel.id if interaction.channel else None
            })
            
            # Check admin permissions
            if not is_admin(interaction):
                tree_log('warning', 'Restart denied: not admin', {
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
                    tree_log('warning', 'Error fetching creator for embed', {"error": str(e), "traceback": traceback.format_exc()})
                
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
            
            tree_log('info', 'Restart initiated', {
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
            tree_log('error', 'Error during restart command', {
                "user_id": interaction.user.id if interaction.user else None,
                "command": "restart",
                "error_details": "restart_command_failed",
                "traceback": traceback.format_exc()
            })
            
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
        tree_log('info', 'Setting up admin commands', {
            "component": "setup",
            "bot_name": bot.user.name if bot.user else "Unknown"
        })
        
        admin_commands = AdminCommands()
        bot.tree.add_command(admin_commands)
        
        tree_log('info', 'Admin commands loaded', {
            "component": "setup",
            "action": "admin_commands_loaded",
            "commands": ["restart"]
        })
        
    except Exception as e:
        tree_log('critical', 'Error during admin command setup', {
            "component": "setup",
            "error_details": "setup_failed",
            "traceback": traceback.format_exc()
        }) 
