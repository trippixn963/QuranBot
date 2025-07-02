import discord
from discord import app_commands
import os
from monitoring.logging.log_helpers import log_async_function_call, log_function_call, log_operation

# Get admin ID from environment variable
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '0'))

def is_admin(interaction: discord.Interaction) -> bool:
    """Check if the user is the admin."""
    return interaction.user.id == ADMIN_USER_ID

@app_commands.command(name="info", description="Get bot logs and configuration (Admin only)")
@app_commands.check(is_admin)
@log_async_function_call
async def info(interaction: discord.Interaction, lines: int = 10):
    """Get bot logs and configuration."""
    if lines > 30:
        lines = 30  # Limit to 30 lines max
    
    embed = discord.Embed(
        title="📋 Bot Information",
        color=discord.Color.blue()
    )
    
    # Configuration section
    try:
        from core.config.config import Config
        
        config_info = {
            "Target Channel ID": str(Config.TARGET_CHANNEL_ID),
            "Target Guild ID": str(Config.TARGET_GUILD_ID) if Config.TARGET_GUILD_ID else "Not set",
            "Logs Channel ID": str(Config.LOGS_CHANNEL_ID),
            "Audio Folder": Config.AUDIO_FOLDER,
            "Log Level": Config.LOG_LEVEL,
            "Auto Reconnect": str(Config.AUTO_RECONNECT)
        }
        
        config_text = "\n".join([f"**{key}:** {value}" for key, value in config_info.items()])
        embed.add_field(
            name="⚙️ Configuration",
            value=config_text,
            inline=False
        )
    except Exception as e:
        embed.add_field(
            name="⚙️ Configuration",
            value=f"Error loading config: {str(e)}",
            inline=False
        )
    
    # Logs section
    log_file = "logs/2025-07-01.log"
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                log_lines = f.readlines()
            
            # Get the last N lines
            recent_logs = log_lines[-lines:] if len(log_lines) > lines else log_lines
            
            # Format logs (limit to 1000 characters)
            log_text = ''.join(recent_logs)
            if len(log_text) > 1000:
                log_text = log_text[-1000:] + "\n... (truncated)"
            
            embed.add_field(
                name=f"📋 Recent Logs ({len(recent_logs)} lines)",
                value=f"```\n{log_text}\n```",
                inline=False
            )
            
        except Exception as e:
            embed.add_field(
                name="📋 Logs",
                value=f"Error reading logs: {str(e)}",
                inline=False
            )
    else:
        embed.add_field(
            name="📋 Logs",
            value="No log file found.",
            inline=False
        )
    
    embed.set_footer(text=f"Requested by {interaction.user.name}")
    embed.timestamp = discord.utils.utcnow()
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@info.error
async def info_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Handle errors for info command."""
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
    """Setup the info command."""
    bot.tree.add_command(info) 