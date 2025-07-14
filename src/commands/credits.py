# =============================================================================
# QuranBot - Credits Command (Cog)
# =============================================================================
# Clean, simple bot information display using Discord.py Cogs
# =============================================================================

import os
from datetime import datetime, timezone
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

# Import tree logging functions
from utils.tree_log import (
    log_error_with_traceback,
    log_perfect_tree_section,
    log_user_interaction,
)

# Import version and author from centralized version module
from version import BOT_VERSION

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
# Credits Cog
# =============================================================================


class CreditsCog(commands.Cog):
    """Credits command cog for displaying bot information"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="credits",
        description="🕌 Show bot information and credits",
    )
    async def credits(self, interaction: discord.Interaction):
        """
        Simple and clean credits command
        """
        try:
            # Log command execution
            log_perfect_tree_section(
                "Credits Command - Simplified",
                [
                    (
                        "user",
                        f"{interaction.user.display_name} ({interaction.user.id})",
                    ),
                    (
                        "guild",
                        f"{interaction.guild.name if interaction.guild else 'DM'}",
                    ),
                ],
                "ℹ️",
            )

            # Get bot stats
            guild_count = len(interaction.client.guilds)
            user_count = sum(guild.member_count for guild in interaction.client.guilds)

            # Create simple embed
            embed = discord.Embed(
                title="🕌 QuranBot - Credits",
                description="**A Discord bot for Quran recitation and daily verses**",
                color=0x1ABC9C,
            )

            # Bot Information
            embed.add_field(
                name="🤖 Bot Information",
                value=(
                    f"**Version:** `3.0.0`\n"
                    f"**Commands:** `/credits` `/leaderboard`\n"
                    f"**Features:** Audio streaming, Daily verses, Leaderboard"
                ),
                inline=False,
            )

            # Spacer
            embed.add_field(name="\u200b", value="\u200b", inline=False)

            # Developer & Links
            embed.add_field(
                name="👨‍💻 Developer Information",
                value=(
                    f"**Created by:** <@{ADMIN_USER_ID}>\n"
                    f"**GitHub:** [QuranBot Repository]({GITHUB_REPO_URL})\n"
                    f"**⭐ Please star the repository if you like it!**"
                ),
                inline=False,
            )

            # Spacer
            embed.add_field(name="\u200b", value="\u200b", inline=False)

            # Beta Testing Notice
            embed.add_field(
                name="⚠️ Beta Testing",
                value=f"This bot is currently in **beta testing phase**. Please DM <@{ADMIN_USER_ID}> if you encounter any issues or bugs.",
                inline=False,
            )

            # Set bot avatar as thumbnail
            if interaction.client.user and interaction.client.user.avatar:
                embed.set_thumbnail(url=interaction.client.user.avatar.url)

            # No footer as requested

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
                await interaction.response.send_message(
                    embed=error_embed, ephemeral=True
                )
            except:
                pass


# =============================================================================
# Cog Setup
# =============================================================================


async def setup(bot):
    """
    Set up the Credits cog
    """
    try:
        log_perfect_tree_section(
            "Credits Cog Setup - Starting",
            [
                ("cog_name", "CreditsCog"),
                ("command_name", "/credits"),
                ("status", "🔄 Initializing credits cog setup"),
            ],
            "🚀",
        )

        await bot.add_cog(CreditsCog(bot))

        log_perfect_tree_section(
            "Credits Cog Setup - Complete",
            [
                ("status", "✅ Credits cog loaded successfully"),
                ("cog_name", "CreditsCog"),
                ("command_name", "/credits"),
                ("description", "Clean and simple bot information"),
                ("setup_completed", "✅ Credits cog setup completed"),
            ],
            "✅",
        )

    except Exception as setup_error:
        log_error_with_traceback("Failed to set up credits cog", setup_error)

        log_perfect_tree_section(
            "Credits Cog Setup - Failed",
            [
                ("error_type", type(setup_error).__name__),
                ("status", "❌ Failed to load credits cog"),
                ("impact", "🚨 /credits command will not be available"),
            ],
            "💥",
        )

        # Re-raise the exception to ensure the bot startup process is aware of the failure
        raise


# =============================================================================
# Export Functions (for backward compatibility)
# =============================================================================

__all__ = [
    "CreditsCog",
    "setup",
]
