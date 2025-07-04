import discord
from discord import app_commands
import os
import time
import asyncio
import traceback
from src.monitoring.logging.tree_log import tree_log

# Get admin ID from environment variable
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '0'))

def is_admin(interaction: discord.Interaction) -> bool:
    """Check if the user is the admin."""
    tree_log('debug', 'Checking admin status', {'user_id': interaction.user.id, 'admin_id': ADMIN_USER_ID})
    return interaction.user.id == ADMIN_USER_ID

@app_commands.command(name="reconnect", description="Reconnect to voice channel (Admin only)")
@app_commands.check(is_admin)
async def reconnect(interaction: discord.Interaction):
    """Reconnect to the voice channel."""
    tree_log('info', 'Reconnect command invoked', {'user_id': interaction.user.id, 'guild_id': interaction.guild.id if interaction.guild else None})
    embed = discord.Embed(
        title="🔗 Reconnecting",
        description="Attempting to reconnect to voice channel...",
        color=discord.Color.blue()
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)
    
    # Disconnect from all voice channels
    if hasattr(interaction.client, '_voice_clients'):
        for voice_client in interaction.client._voice_clients.values():
            try:
                tree_log('debug', 'Disconnecting voice client', {'guild_id': getattr(voice_client.guild, 'id', None)})
                await voice_client.disconnect()
            except Exception as e:
                tree_log('error', f'Error disconnecting voice client: {e}', {'traceback': traceback.format_exc()})
                pass
        interaction.client._voice_clients.clear()
    
    # Wait a moment and reconnect
    tree_log('debug', 'Waiting before reconnecting', {'delay': 2})
    await asyncio.sleep(2)
    try:
        tree_log('info', 'Attempting to rejoin voice channel', {})
        await interaction.client.find_and_join_channel()
        tree_log('info', 'Rejoin voice channel complete', {})
    except Exception as e:
        tree_log('error', f'Error during rejoin: {e}', {'traceback': traceback.format_exc()})
    
    # Update the message
    embed.description = "✅ Reconnected to voice channel!"
    embed.color = discord.Color.green()
    await interaction.edit_original_response(embed=embed)

@reconnect.error
async def reconnect_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Handle errors for reconnect command."""
    tree_log('error', f'Reconnect command error: {error}', {'user_id': interaction.user.id, 'traceback': traceback.format_exc()})
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
    """Setup the reconnect command."""
    tree_log('info', 'Adding reconnect command to bot', {})
    bot.tree.add_command(reconnect) 