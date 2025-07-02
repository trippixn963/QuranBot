import discord
from discord import app_commands
import os

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

@app_commands.command(name="logs", description="Get recent bot logs (Admin only)")
@app_commands.describe(lines="Number of log lines to retrieve (1-100, default: 20)")
@app_commands.check(is_admin)
async def logs(interaction: discord.Interaction, lines: int = 20):
    """Retrieve recent bot logs."""
    await interaction.response.defer(ephemeral=True)
    
    # Validate lines parameter
    if lines < 1 or lines > 100:
        embed = discord.Embed(
            title="❌ Invalid Parameter",
            description="Number of lines must be between 1 and 100.",
            color=discord.Color.red()
        )
        
        # Add creator as author and user's avatar as thumbnail
        try:
            creator = await interaction.client.fetch_user(259725211664908288)
            if creator and creator.avatar:
                embed.set_author(name=creator.display_name, icon_url=creator.avatar.url)
        except Exception as e:
            pass
        
        if interaction.user.avatar:
            embed.set_thumbnail(url=interaction.user.avatar.url)
        
        await interaction.followup.send(embed=embed)
        return
    
    try:
        log_file_path = os.path.join(os.getcwd(), 'logs', 'quran_bot.log')
        
        if not os.path.exists(log_file_path):
            embed = discord.Embed(
                title="❌ Log File Not Found",
                description="The log file could not be found.",
                color=discord.Color.red()
            )
            
            # Add creator as author and user's avatar as thumbnail
            try:
                creator = await interaction.client.fetch_user(259725211664908288)
                if creator and creator.avatar:
                    embed.set_author(name=creator.display_name, icon_url=creator.avatar.url)
            except Exception as e:
                pass
            
            if interaction.user.avatar:
                embed.set_thumbnail(url=interaction.user.avatar.url)
            
            await interaction.followup.send(embed=embed)
            return
        
        # Read the last N lines from the log file
        with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            log_lines = f.readlines()
        
        if not log_lines:
            embed = discord.Embed(
                title="📋 Bot Logs",
                description="No logs available.",
                color=discord.Color.blue()
            )
            
            # Add creator as author and user's avatar as thumbnail
            try:
                creator = await interaction.client.fetch_user(259725211664908288)
                if creator and creator.avatar:
                    embed.set_author(name=creator.display_name, icon_url=creator.avatar.url)
            except Exception as e:
                pass
            
            if interaction.user.avatar:
                embed.set_thumbnail(url=interaction.user.avatar.url)
            
            await interaction.followup.send(embed=embed)
            return
        
        # Get the last N lines
        recent_logs = log_lines[-lines:] if len(log_lines) >= lines else log_lines
        log_content = ''.join(recent_logs)
        
        # Truncate if too long for Discord
        if len(log_content) > 1950:  # Leave room for markdown formatting
            log_content = log_content[-1950:]
            log_content = "... " + log_content[log_content.find('\n') + 1:]
        
        embed = discord.Embed(
            title="📋 Bot Logs",
            description=f"```\n{log_content}\n```",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📊 Info",
            value=f"**Lines Requested:** {lines}\n**Lines Shown:** {len(recent_logs)}\n**Total Lines:** {len(log_lines)}",
            inline=False
        )
        
        # Add creator as author and user's avatar as thumbnail
        try:
            creator = await interaction.client.fetch_user(259725211664908288)
            if creator and creator.avatar:
                embed.set_author(name=creator.display_name, icon_url=creator.avatar.url)
        except Exception as e:
            pass
        
        if interaction.user.avatar:
            embed.set_thumbnail(url=interaction.user.avatar.url)
        
        embed.set_footer(text=f"Requested by {interaction.user.name}")
        embed.timestamp = discord.utils.utcnow()
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        embed = discord.Embed(
            title="❌ Error",
            description=f"An error occurred while reading logs: {str(e)}",
            color=discord.Color.red()
        )
        
        # Add creator as author and user's avatar as thumbnail
        try:
            creator = await interaction.client.fetch_user(259725211664908288)
            if creator and creator.avatar:
                embed.set_author(name=creator.display_name, icon_url=creator.avatar.url)
        except Exception as e:
            pass
        
        if interaction.user.avatar:
            embed.set_thumbnail(url=interaction.user.avatar.url)
        
        await interaction.followup.send(embed=embed)

@logs.error
async def logs_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Handle errors for logs command."""
    if isinstance(error, app_commands.CheckFailure):
        embed = discord.Embed(
            title="❌ Access Denied",
            description="This command is only available to the bot administrator.",
            color=discord.Color.red()
        )
        
        # Add creator as author and user's avatar as thumbnail
        try:
            creator = await interaction.client.fetch_user(259725211664908288)
            if creator and creator.avatar:
                embed.set_author(name=creator.display_name, icon_url=creator.avatar.url)
        except Exception as e:
            pass
        
        if interaction.user.avatar:
            embed.set_thumbnail(url=interaction.user.avatar.url)
        
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        embed = discord.Embed(
            title="❌ Error",
            description=f"An error occurred: {str(error)}",
            color=discord.Color.red()
        )
        
        # Add creator as author and user's avatar as thumbnail
        try:
            creator = await interaction.client.fetch_user(259725211664908288)
            if creator and creator.avatar:
                embed.set_author(name=creator.display_name, icon_url=creator.avatar.url)
        except Exception as e:
            pass
        
        if interaction.user.avatar:
            embed.set_thumbnail(url=interaction.user.avatar.url)
        
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    """Setup the logs command."""
    bot.tree.add_command(logs)
