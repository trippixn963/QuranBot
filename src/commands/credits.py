# =============================================================================
# QuranBot - Credits Command (Cog)
# =============================================================================
# Clean, simple bot information display using Discord.py Cogs
# =============================================================================

import discord
from discord import app_commands
from discord.ext import commands

from src.config import get_config
from src.core.exceptions import DiscordAPIError, ServiceError, handle_errors
from src.core.logger import StructuredLogger
from src.core.security import rate_limit

# Import tree logging functions
from src.utils.tree_log import log_error_with_traceback, log_perfect_tree_section
from src.version import __version__

# =============================================================================
# Configuration
# =============================================================================

GITHUB_REPO_URL = "https://github.com/trippixn963/QuranBot"

# =============================================================================
# Credits Cog
# =============================================================================


class CreditsCog(commands.Cog):
    """Credits command cog for displaying bot information"""

    def __init__(self, bot, container=None):
        self.bot = bot
        self.container = container
        self.config = get_config()
        self.logger = StructuredLogger("credits", "INFO")

    @app_commands.command(
        name="credits",
        description="🕌 Show bot information and credits",
    )
    @rate_limit(user_limit=3, user_window=30)  # 3 requests per 30 seconds per user
    @handle_errors(logger=None, reraise=False)
    async def credits(self, interaction: discord.Interaction):
        """
        Simple and clean credits command
        """
        try:
            # Log command execution
            await self.logger.info(
                "Credits command executed",
                {
                    "user_id": interaction.user.id,
                    "user_name": interaction.user.display_name,
                    "guild_id": interaction.guild.id if interaction.guild else None,
                    "guild_name": interaction.guild.name if interaction.guild else "DM",
                },
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
                    f"**Version:** `{__version__}`\n"
                    "**Commands:** `/credits` `/leaderboard`\n"
                    "**Features:** Audio streaming, Daily verses, Leaderboard"
                ),
                inline=False,
            )

            # Spacer
            embed.add_field(name="\u200b", value="\u200b", inline=False)

            # Developer & Links
            embed.add_field(
                name="👨‍💻 Developer Information",
                value=(
                    f"**Created by:** <@{self.config.ADMIN_USER_ID}>\n"
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
                value=f"This bot is currently in **beta testing phase**. Please DM <@{self.config.ADMIN_USER_ID}> if you encounter any issues or bugs.",
                inline=False,
            )

            # Set bot avatar as thumbnail
            if interaction.client.user and interaction.client.user.avatar:
                embed.set_thumbnail(url=interaction.client.user.avatar.url)

            # Send the embed
            await interaction.response.send_message(embed=embed, ephemeral=False)

            # Log credits command usage via enhanced webhook router first
            try:
                if self.container:
                    enhanced_webhook = self.container.get("webhook_router")
                    if enhanced_webhook and hasattr(
                        enhanced_webhook, "log_quran_command_usage"
                    ):
                        await enhanced_webhook.log_quran_command_usage(
                            admin_name=interaction.user.display_name,
                            admin_id=interaction.user.id,
                            command_name="/credits",
                            command_details={
                                "bot_version": __version__,
                                "channel": (
                                    f"#{interaction.channel.name}"
                                    if hasattr(interaction.channel, "name")
                                    else "Direct Message"
                                ),
                                "command_type": "Bot Information",
                                "github_repo": GITHUB_REPO_URL,
                            },
                            admin_avatar_url=(
                                interaction.user.avatar.url
                                if interaction.user.avatar
                                else None
                            ),
                        )
            except Exception as webhook_error:
                await self.logger.warning(
                    "Failed to send webhook for credits command",
                    {"user_id": interaction.user.id, "error": str(webhook_error)},
                )

            # Log successful completion
            await self.logger.info(
                "Credits command completed successfully",
                {
                    "user_id": interaction.user.id,
                    "guild_count": guild_count,
                    "user_count": user_count,
                },
            )

        except discord.HTTPException as e:
            # Discord API specific errors
            await self.logger.error(
                "Discord API error in credits command",
                {
                    "error_code": getattr(e, "code", None),
                    "error_text": getattr(e, "text", str(e)),
                    "user_id": interaction.user.id,
                },
            )
            raise DiscordAPIError(
                "Failed to send credits message due to Discord API error",
                status_code=getattr(e, "status", None),
                discord_error=str(e),
                context={"command": "credits", "user_id": interaction.user.id},
                original_error=e,
            )

        except discord.Forbidden as e:
            # Permission errors
            await self.logger.error(
                "Permission denied in credits command",
                {
                    "error": str(e),
                    "user_id": interaction.user.id,
                    "guild_id": interaction.guild.id if interaction.guild else None,
                },
            )
            raise DiscordAPIError(
                "Insufficient permissions to send credits message",
                status_code=403,
                discord_error=str(e),
                context={"command": "credits", "user_id": interaction.user.id},
                original_error=e,
            )

        except Exception as e:
            # Unexpected errors - wrap in ServiceError
            await self.logger.error(
                "Unexpected error in credits command",
                {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "user_id": interaction.user.id,
                },
                exc_info=True,
            )

            # Try to send error message to user
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
                # If we can't send the error message, just log it
                await self.logger.error(
                    "Failed to send error message to user",
                    {"user_id": interaction.user.id},
                )

            raise ServiceError(
                "Unexpected error in credits command",
                service_name="credits_cog",
                operation="display_credits",
                context={"user_id": interaction.user.id},
                original_error=e,
            )


# =============================================================================
# Cog Setup
# =============================================================================


async def setup(bot, container=None):
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

        await bot.add_cog(CreditsCog(bot, container))

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

        # Re-raise as ServiceError for proper handling
        raise ServiceError(
            "Failed to setup credits cog",
            service_name="credits_cog",
            operation="setup",
            context={"error_type": type(setup_error).__name__},
            original_error=setup_error,
        )


# =============================================================================
# Export Functions (for backward compatibility)
# =============================================================================

__all__ = [
    "CreditsCog",
    "setup",
]
