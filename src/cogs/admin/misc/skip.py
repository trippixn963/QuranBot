import discord
from discord import app_commands
import os
import time

# Get admin ID from environment variable
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '0'))

def is_admin(interaction: discord.Interaction) -> bool:
    """Check if the user is the admin."""
    return interaction.user.id == ADMIN_USER_ID

@app_commands.command(name="skip", description="Skip to the next surah (Admin only)")
@app_commands.check(is_admin)
async def skip(interaction: discord.Interaction):
    """Skip to the next surah."""
    embed = discord.Embed(
        title="⏭️ Skip Surah",
        description="Skipping to the next surah...",
        color=discord.Color.orange()
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
    
    # Stop current playback
    if hasattr(interaction.client, '_voice_clients') and interaction.client._voice_clients:
        for voice_client in interaction.client._voice_clients.values():
            if voice_client.is_playing():
                voice_client.stop()
                embed.add_field(name="🎵 Stopped", value="Current surah playback stopped", inline=True)
                break
    
    embed.add_field(name="Admin", value=f"<@{interaction.user.id}>", inline=True)
    embed.add_field(name="Time", value=f"<t:{int(time.time())}:F>", inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@skip.error
async def skip_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Handle errors for skip command."""
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
    """Setup the skip command."""
    bot.tree.add_command(skip) 