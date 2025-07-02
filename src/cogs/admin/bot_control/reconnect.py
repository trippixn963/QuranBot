import discord
from discord import app_commands
import os
import time
import asyncio

# Get admin ID from environment variable
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '0'))

def is_admin(interaction: discord.Interaction) -> bool:
    """Check if the user is the admin."""
    return interaction.user.id == ADMIN_USER_ID

@app_commands.command(name="reconnect", description="Reconnect to voice channel (Admin only)")
@app_commands.check(is_admin)
async def reconnect(interaction: discord.Interaction):
    """Reconnect to the voice channel."""
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
                await voice_client.disconnect()
            except:
                pass
        interaction.client._voice_clients.clear()
    
    # Wait a moment and reconnect
    await asyncio.sleep(2)
    await interaction.client.find_and_join_channel()
    
    # Update the message
    embed.description = "✅ Reconnected to voice channel!"
    embed.color = discord.Color.green()
    await interaction.edit_original_response(embed=embed)

@reconnect.error
async def reconnect_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Handle errors for reconnect command."""
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
    bot.tree.add_command(reconnect) 