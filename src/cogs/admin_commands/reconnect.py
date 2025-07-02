import discord
from discord import app_commands
import os
import time
import asyncio

# Get admin IDs from environment variable (comma-separated)
def get_admin_ids():
    admin_env = os.getenv('ADMIN_USER_IDS', '')
    if admin_env:
        return [int(uid.strip()) for uid in admin_env.split(',') if uid.strip().isdigit()]
    return []

def is_admin(interaction: discord.Interaction) -> bool:
    """Check if the user is an admin."""
    admin_ids = get_admin_ids()
    return interaction.user.id in admin_ids

@app_commands.command(name="reconnect", description="Reconnect to voice channel (Admin only)")
@app_commands.check(is_admin)
async def reconnect(interaction: discord.Interaction):
    """Reconnect to the voice channel."""
    embed = discord.Embed(
        title="🔗 Reconnecting",
        description="Attempting to reconnect to voice channel...",
        color=discord.Color.blue()
    )
    
    # Add creator as author and bot as thumbnail
    try:
        creator = await interaction.client.fetch_user(259725211664908288)
        if creator and creator.avatar:
            embed.set_author(name=creator.display_name, icon_url=creator.avatar.url)
    except Exception as e:
        pass
    
    if interaction.client.user and interaction.client.user.avatar:
        embed.set_thumbnail(url=interaction.client.user.avatar.url)
    
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
        
        # Add creator as author and bot as thumbnail
        try:
            creator = await interaction.client.fetch_user(259725211664908288)
            if creator and creator.avatar:
                embed.set_author(name=creator.display_name, icon_url=creator.avatar.url)
        except Exception as e:
            pass
        
        if interaction.client.user and interaction.client.user.avatar:
            embed.set_thumbnail(url=interaction.client.user.avatar.url)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        embed = discord.Embed(
            title="❌ Error",
            description=f"An error occurred: {str(error)}",
            color=discord.Color.red()
        )
        
        # Add creator as author and bot as thumbnail
        try:
            creator = await interaction.client.fetch_user(259725211664908288)
            if creator and creator.avatar:
                embed.set_author(name=creator.display_name, icon_url=creator.avatar.url)
        except Exception as e:
            pass
        
        if interaction.client.user and interaction.client.user.avatar:
            embed.set_thumbnail(url=interaction.client.user.avatar.url)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    """Setup the reconnect command."""
    bot.tree.add_command(reconnect)
