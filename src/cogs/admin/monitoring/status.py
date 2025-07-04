import discord
from discord import app_commands
import os
import time
import psutil
from src.monitoring.logging.tree_log import tree_log

# Get admin ID from environment variable
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '0'))

def is_admin(interaction: discord.Interaction) -> bool:
    """Check if the user is the admin."""
    tree_log('debug', 'Checking admin status', {
        'user_id': interaction.user.id,
        'admin_id': ADMIN_USER_ID
    })
    return interaction.user.id == ADMIN_USER_ID

@app_commands.command(name="status", description="Get comprehensive bot and system status (Admin only)")
@app_commands.check(is_admin)
async def status(interaction: discord.Interaction):
    """Get comprehensive bot and system status."""
    try:
        tree_log('info', 'Status command invoked', {
            'user_id': interaction.user.id,
            'user_name': interaction.user.name
        })
        embed = discord.Embed(
            title="📊 Bot & System Status",
            color=discord.Color.green()
        )
        # Bot info
        embed.add_field(
            name="🤖 Bot Info",
            value=f"**Name:** {interaction.client.user.name}\n**ID:** {interaction.client.user.id}\n**Uptime:** {get_uptime(interaction.client)}\n**Latency:** {round(interaction.client.latency * 1000)}ms",
            inline=False
        )
        # Voice status
        voice_status = "❌ Not connected"
        if hasattr(interaction.client, '_voice_clients') and interaction.client._voice_clients:
            for guild_id, voice_client in interaction.client._voice_clients.items():
                if voice_client.is_connected():
                    voice_status = f"✅ Connected to {voice_client.channel.name}"
                    break
        embed.add_field(
            name="🔊 Voice Status",
            value=voice_status,
            inline=True
        )
        # Streaming status
        streaming_status = "✅ Streaming" if getattr(interaction.client, 'is_streaming', False) else "❌ Not streaming"
        embed.add_field(
            name="🎵 Streaming",
            value=streaming_status,
            inline=True
        )
        # Current song
        current_song = getattr(interaction.client, 'current_audio_file', 'None')
        embed.add_field(
            name="🎵 Current Song",
            value=current_song,
            inline=True
        )
        # Health info
        if hasattr(interaction.client, 'health_monitor'):
            health = interaction.client.health_monitor
            embed.add_field(
                name="💚 Health",
                value=f"**Songs Played:** {getattr(health, 'songs_played', 0)}\n**Errors:** {getattr(health, 'error_count', 0)}",
                inline=True
            )
        # System info
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used = memory.used / (1024**3)  # GB
            memory_total = memory.total / (1024**3)  # GB
            process = psutil.Process()
            process_memory = process.memory_info().rss / (1024**2)  # MB
            embed.add_field(
                name="🖥️ System",
                value=f"**CPU:** {cpu_percent}% ({cpu_count} cores)\n**RAM:** {memory_percent}% ({memory_used:.1f}GB/{memory_total:.1f}GB)\n**Bot Memory:** {process_memory:.1f}MB",
                inline=False
            )
        except Exception as e:
            import traceback
            tree_log('error', 'Error getting system info in status command', {
                'user_id': interaction.user.id,
                'error': str(e),
                'traceback': traceback.format_exc()
            })
            embed.add_field(
                name="🖥️ System",
                value=f"Error getting system info: {str(e)}",
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        tree_log('info', 'Status command completed', {
            'user_id': interaction.user.id,
            'user_name': interaction.user.name
        })
    except Exception as e:
        import traceback
        tree_log('error', 'Error in status command', {
            'user_id': interaction.user.id if interaction.user else None,
            'error': str(e),
            'traceback': traceback.format_exc()
        })
        try:
            embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred while getting status: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except:
            pass

def get_uptime(bot) -> str:
    """Get bot uptime as a formatted string."""
    if hasattr(bot, 'start_time'):
        uptime = time.time() - bot.start_time
        days = int(uptime // 86400)
        hours = int((uptime % 86400) // 3600)
        minutes = int((uptime % 3600) // 60)
        seconds = int(uptime % 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m {seconds}s"
        elif hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    return "Unknown"

@status.error
async def status_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Handle errors for status command."""
    import traceback
    if isinstance(error, app_commands.CheckFailure):
        tree_log('warning', 'Status command access denied', {
            'user_id': interaction.user.id if interaction.user else None,
            'error': str(error),
            'traceback': traceback.format_exc()
        })
        embed = discord.Embed(
            title="❌ Access Denied",
            description="This command is only available to the bot administrator.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        tree_log('error', 'Error in status command error handler', {
            'user_id': interaction.user.id if interaction.user else None,
            'error': str(error),
            'traceback': traceback.format_exc()
        })
        embed = discord.Embed(
            title="❌ Error",
            description=f"An error occurred: {str(error)}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    """Setup the status command."""
    bot.tree.add_command(status) 