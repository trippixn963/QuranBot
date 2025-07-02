import discord
from discord import app_commands
import os
import sys
import logging

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

@app_commands.command(name="restart", description="Restart the bot (Admin only)")
@app_commands.check(is_admin)
async def restart(interaction: discord.Interaction):
    """Restart the bot."""
    embed = discord.Embed(
        title="�� Restarting Bot",
        description="The bot is restarting... It will be back online shortly.",
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
    
    embed.set_footer(text=f"Restart requested by {interaction.user.name}")
    embed.timestamp = discord.utils.utcnow()
    
    await interaction.response.send_message(embed=embed)
    
    logging.info(f"Bot restart initiated by {interaction.user.name} ({interaction.user.id})")
    
    # Close bot gracefully
    await interaction.client.close()
    
    # Restart the script
    os.execv(sys.executable, ['python'] + sys.argv)

@restart.error
async def restart_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Handle errors for restart command."""
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
    """Setup the restart command."""
    bot.tree.add_command(restart)
