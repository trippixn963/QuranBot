# =============================================================================
# QuranBot - Credits Command (Simplified)
# =============================================================================
# Clean, simple bot information display
# =============================================================================

import os
from datetime import datetime, timezone
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

# Import tree logging functions
from src.utils.tree_log import (
    log_error_with_traceback,
    log_perfect_tree_section,
    log_user_interaction,
)

# Import version and author from centralized version module
from ..version import BOT_VERSION

# =============================================================================
# Environment Configuration
# =============================================================================

# Load environment variables
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
env_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", ".env")
load_dotenv(env_path)

# Configuration
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))
GITHUB_REPO_URL = "https://github.com/trippixn963/QuranBot"

# =============================================================================
# Main Credits Command
# =============================================================================


async def credits_command(interaction: discord.Interaction):
    """
    Simple and clean credits command
    """
    try:
        # Log command execution
        log_perfect_tree_section(
            "Credits Command - Simplified",
            [
                ("user", f"{interaction.user.display_name} ({interaction.user.id})"),
                ("guild", f"{interaction.guild.name if interaction.guild else 'DM'}"),
            ],
            "ℹ️",
        )

        # Get bot stats
        guild_count = len(interaction.client.guilds)
        user_count = sum(guild.member_count for guild in interaction.client.guilds)

        # Create simple embed
        embed = discord.Embed(
            title="🕌 QuranBot - Credits",
            description=f"**A Discord bot for Quran recitation and daily verses**\n\n*Serving {user_count} users across {guild_count} servers*",
            color=0x1ABC9C,
            timestamp=datetime.now(timezone.utc),
        )

        # Bot Information
        embed.add_field(
            name="🤖 Bot Information",
            value=(
                f"**Version:** `{BOT_VERSION}`\n"
                f"**Commands:** `/credits` `/leaderboard` `/verse`\n"
                f"**Features:** Audio streaming, Daily verses, Leaderboard"
            ),
            inline=False,
        )

        # Developer & Links
        embed.add_field(
            name="👨‍💻 Developer Information",
            value=(
                f"**Created by:** <@{ADMIN_USER_ID}>\n"
                f"**GitHub:** [QuranBot Repository]({GITHUB_REPO_URL})\n"
                f"**License:** MIT License - Open Source"
            ),
            inline=False,
        )

        # Support Policy
        embed.add_field(
            name="⚠️ Support Policy",
            value='**"Take as it is"** - No support provided • Educational use only',
            inline=False,
        )

        # Set bot avatar as thumbnail
        if interaction.client.user and interaction.client.user.avatar:
            embed.set_thumbnail(url=interaction.client.user.avatar.url)

        # Simple footer
        embed.set_footer(
            text=f"QuranBot v{BOT_VERSION} • Requested by {interaction.user.display_name}"
        )

        # Send the embed
        await interaction.response.send_message(embed=embed, ephemeral=False)

        # Log successful completion
        log_perfect_tree_section(
            "Credits Command - Success",
            [
                ("user", f"{interaction.user.display_name}"),
                ("guild_count", guild_count),
                ("user_count", user_count),
                ("status", "✅ Simple credits display sent"),
            ],
            "✅",
        )

    except Exception as e:
        log_error_with_traceback("Error in credits command", e)
        try:
            error_embed = discord.Embed(
                title="❌ Error",
                description="An error occurred while displaying credits. Please try again.",
                color=0xFF6B6B,
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
        except:
            pass


# =============================================================================
# Command Setup
# =============================================================================


async def setup_credits_command(bot):
    """
    Set up the simplified /credits slash command
    """
    # Check if command is already registered
    existing_commands = [cmd.name for cmd in bot.tree.get_commands()]
    if "credits" in existing_commands:
        log_perfect_tree_section(
            "Credits Command Setup - Already Registered",
            [
                ("status", "✅ /credits command already registered"),
                ("version", "Simplified version active"),
            ],
            "✅",
        )
        return

    log_perfect_tree_section(
        "Credits Command Setup - Simplified Registration",
        [
            ("setup_initiated", "Registering simplified /credits command"),
            ("version", "Clean and simple design"),
        ],
        "ℹ️",
    )

    @bot.tree.command(
        name="credits",
        description="🕌 Show bot information and credits",
    )
    async def credits(interaction: discord.Interaction):
        """Show simple bot credits and information"""
        try:
            # Log user interaction
            log_user_interaction(
                interaction_type="slash_command",
                user_name=interaction.user.display_name,
                user_id=interaction.user.id,
                action_description="Used simplified /credits command",
                details={
                    "command": "credits",
                    "version": "simplified",
                    "guild_id": interaction.guild_id if interaction.guild else None,
                    "channel_id": interaction.channel_id,
                },
            )

            # Call the main credits function
            await credits_command(interaction)

        except Exception as e:
            log_error_with_traceback("Error in credits slash command", e)
            try:
                error_embed = discord.Embed(
                    title="❌ Command Error",
                    description="An error occurred while processing the credits command.",
                    color=0xFF6B6B,
                )
                await interaction.response.send_message(
                    embed=error_embed, ephemeral=True
                )
            except:
                pass

    log_perfect_tree_section(
        "Credits Command Setup - Complete",
        [
            ("command_registered", "✅ Simplified /credits command registered"),
            ("description", "Clean and simple bot information"),
            ("setup_completed", "✅ Simplified credits setup completed"),
        ],
        "✅",
    )


# =============================================================================
# Export Functions
# =============================================================================

__all__ = [
    "credits_command",
    "setup_credits_command",
]
