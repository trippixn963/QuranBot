# =============================================================================
# QuranBot - Credits Command
# =============================================================================
# Slash command to display bot information, developer credits, and repository
# =============================================================================

import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from src.utils.tree_log import log_tree_branch, log_tree_final, log_user_interaction

from ..utils.tree_log import (
    log_error_with_traceback,
    log_section_start,
    log_spacing,
    log_tree_branch,
    log_tree_final,
)

# =============================================================================
# Configuration
# =============================================================================


# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", ".env")
load_dotenv(env_path)

# Admin/Developer Information (loaded from environment)
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))
GITHUB_REPO_URL = "https://github.com/JohnHamwi/QuranBot"
BOT_VERSION = "1.6.1"


# =============================================================================
# Credits Command
# =============================================================================


async def credits_command(interaction: discord.Interaction):
    """
    Show bot credits, information, and developer details

    Features:
    - Bot information and version
    - Developer credits with mention
    - GitHub repository link
    - Technologies used
    - Admin profile picture as thumbnail
    - Request to favorite the bot
    """
    try:
        # Comprehensive logging for credits command execution
        log_section_start("Credits Command Execution", "🎯")
        log_tree_branch(
            "command_user", f"{interaction.user.display_name} ({interaction.user.id})"
        )
        log_tree_branch(
            "command_guild", f"{interaction.guild.name if interaction.guild else 'DM'}"
        )
        log_tree_branch(
            "command_channel",
            f"#{interaction.channel.name if hasattr(interaction.channel, 'name') else 'DM'}",
        )

        # Environment configuration validation with detailed logging
        log_spacing()
        log_tree_branch("config_validation", "Validating environment configuration")

        if ADMIN_USER_ID == 0:
            log_tree_branch(
                "config_error", "❌ ADMIN_USER_ID not found in environment variables"
            )
            log_tree_final("command_result", "❌ Configuration error - command aborted")
            await interaction.response.send_message(
                "❌ Bot configuration error. Please contact the administrator.",
                ephemeral=True,
            )
            return

        log_tree_branch("config_admin_id", f"✅ Admin ID loaded: {ADMIN_USER_ID}")
        log_tree_branch("config_github_url", f"✅ GitHub URL: {GITHUB_REPO_URL}")
        log_tree_branch("config_bot_version", f"✅ Bot Version: {BOT_VERSION}")

        # Admin user fetching with comprehensive logging
        log_spacing()
        log_tree_branch(
            "admin_fetch_start", f"Fetching admin user data for ID: {ADMIN_USER_ID}"
        )

        admin_user = None
        try:
            admin_user = await interaction.client.fetch_user(ADMIN_USER_ID)
            log_tree_branch(
                "admin_fetch_success", f"✅ Admin user: {admin_user.display_name}"
            )
            log_tree_branch(
                "admin_avatar_status",
                f"Avatar available: {admin_user.avatar is not None}",
            )
        except Exception as e:
            log_tree_branch("admin_fetch_error", f"❌ Could not fetch admin user: {e}")
            log_tree_branch("admin_fallback", "Will proceed without admin thumbnail")

        # Create credits embed with logging
        log_spacing()
        log_tree_branch("embed_creation", "Building credits embed")

        embed = discord.Embed(
            title="🎵 QuranBot Credits & Information",
            description="**A professional Discord bot for playing Quran audio with beautiful recitations**",
            color=0x00D4AA,
        )

        log_tree_branch("embed_title", "✅ Title and description set")
        log_tree_branch("embed_color", "✅ Brand color applied (0x00D4AA)")

        # Bot Information
        embed.add_field(
            name="🤖 Bot Information",
            value=f"**Version:** {BOT_VERSION}\n"
            f"**Purpose:** High-quality Quran audio playback\n"
            f"**Features:** Multiple reciters, search functionality, control panel",
            inline=False,
        )

        # Developer Credits
        embed.add_field(
            name="👨‍💻 Developer",
            value=f"**Created by:** <@{ADMIN_USER_ID}>\n"
            f"**GitHub:** [QuranBot Repository]({GITHUB_REPO_URL})\n"
            f"**Status:** Actively maintained and updated",
            inline=False,
        )

        # Technologies Used
        embed.add_field(
            name="🔧 Technologies Used",
            value="**Language:** Python 3.13\n"
            "**Library:** discord.py 2.4+\n"
            "**Audio:** FFmpeg, PyNaCl\n"
            "**Features:** Rich Presence, Interactive UI, State Management",
            inline=False,
        )

        # Support & Links
        embed.add_field(
            name="🌟 Support the Project",
            value=f"⭐ **[Star the repository on GitHub]({GITHUB_REPO_URL})**\n"
            f"🔗 **[View source code]({GITHUB_REPO_URL})**\n"
            f"💖 **Please favorite this bot if you enjoy it!**",
            inline=False,
        )

        # Add admin profile picture as thumbnail with detailed logging
        log_spacing()
        log_tree_branch(
            "thumbnail_processing", "Setting admin profile picture as thumbnail"
        )

        if admin_user and admin_user.avatar:
            embed.set_thumbnail(url=admin_user.avatar.url)
            log_tree_branch("thumbnail_set", "✅ Admin custom avatar set as thumbnail")
            log_tree_branch("thumbnail_url", f"Avatar URL: {admin_user.avatar.url}")
        elif admin_user:
            embed.set_thumbnail(url=admin_user.default_avatar.url)
            log_tree_branch(
                "thumbnail_default", "✅ Admin default avatar set as thumbnail"
            )
            log_tree_branch(
                "thumbnail_url", f"Default avatar URL: {admin_user.default_avatar.url}"
            )
        else:
            log_tree_branch(
                "thumbnail_none", "❌ No admin user available for thumbnail"
            )

        # Log embed completion
        log_tree_branch("embed_fields", f"✅ {len(embed.fields)} fields added to embed")
        log_tree_branch("embed_ready", "✅ Credits embed fully constructed")

        # Send the embed with response logging
        log_spacing()
        log_tree_branch("response_sending", "Sending credits embed to user")

        await interaction.response.send_message(embed=embed, ephemeral=False)

        log_tree_branch("response_sent", "✅ Credits embed delivered successfully")
        log_tree_branch("response_visibility", "Public response (ephemeral=False)")
        log_tree_final(
            "command_completed", "🎯 Credits command execution completed successfully"
        )

    except Exception as e:
        log_error_with_traceback("Error in credits command", e)
        try:
            await interaction.response.send_message(
                "❌ An error occurred while displaying credits. Please try again.",
                ephemeral=True,
            )
        except:
            pass  # Interaction might have already been responded to


# =============================================================================
# Command Setup
# =============================================================================


async def setup_credits_command(bot):
    """
    Set up the /credits slash command with comprehensive logging

    Args:
        bot: The Discord bot instance
    """
    tree_log(
        "⚙️ Credits Command Setup",
        "setup_initiated",
        "Registering /credits slash command",
    )
    tree_log("⚙️ Credits Command Setup", "bot_instance", f"Bot user: {bot.user.name}")

    @bot.tree.command(
        name="credits",
        description="Show bot information, credits, and GitHub repository",
    )
    async def credits(interaction: discord.Interaction):
        """Shows bot credits, information, and GitHub repository"""
        try:
            # Log user interaction in dedicated section
            log_user_interaction(
                interaction_type="slash_command",
                user_name=interaction.user.display_name,
                user_id=interaction.user.id,
                action_description="Used /credits command",
                details={
                    "command": "credits",
                    "guild_id": interaction.guild_id if interaction.guild else None,
                    "channel_id": interaction.channel_id,
                },
            )

            # API calls that Discord tracks for Active Developer Badge
            try:
                # Fetch user information (Discord API call)
                user_info = await bot.fetch_user(interaction.user.id)

                # Fetch guild information if in a guild (Discord API call)
                guild_info = None
                if interaction.guild:
                    guild_info = await bot.fetch_guild(interaction.guild.id)

                # Fetch channel information (Discord API call)
                channel_info = await bot.fetch_channel(interaction.channel_id)

                log_tree_branch(
                    "api_calls_completed",
                    f"✅ API calls successful for user {user_info.name}",
                )

            except Exception as e:
                log_tree_branch(
                    "api_calls_warning",
                    f"⚠️ Some API calls failed: {str(e)}",
                )

            embed = discord.Embed(
                title="🕋 QuranBot Credits",
                description="*A Discord bot for streaming Quran audio with interactive controls*",
                color=0x00D4AA,
                timestamp=interaction.created_at,
            )

            # Bot Information
            embed.add_field(
                name="📊 Bot Information",
                value=f"• **Version:** 1.6.2\n• **Language:** Python 3.11+\n• **Framework:** Discord.py 2.3+\n• **Audio Engine:** FFmpeg",
                inline=False,
            )

            # Features
            embed.add_field(
                name="✨ Features",
                value="• 🎵 **Audio Streaming** - High-quality Quran recitation\n• 🎛️ **Interactive Controls** - Dropdown menus and buttons\n• 📱 **Rich Presence** - Real-time Discord activity\n• 🔄 **State Management** - Resume playback across sessions\n• 📊 **Comprehensive Logging** - Professional tree-structured logs",
                inline=False,
            )

            # Technical Details
            embed.add_field(
                name="🔧 Technical Stack",
                value="• **6 Reciters** available with 114+ Surahs each\n• **Slash Commands** - Modern Discord interaction system\n• **Voice Integration** - Seamless audio streaming\n• **Professional Architecture** - Modular, scalable design",
                inline=False,
            )

            # Repository & Support
            embed.add_field(
                name="📋 Repository & Policy",
                value='• **GitHub:** [QuranBot Repository](https://github.com/johnhamwi/QuranBot)\n• **License:** MIT License\n• **Support Policy:** ⚠️ **"Take as it is" - No support provided**\n• **Purpose:** Educational and reference use only',
                inline=False,
            )

            # Developer Information
            embed.add_field(
                name="👨‍💻 Developer",
                value="• **Created by:** John Hamwi\n• **Project Type:** Open Source Educational Resource\n• **Development Status:** Complete - No ongoing development",
                inline=False,
            )

            # Set bot avatar as thumbnail
            if bot.user.avatar:
                embed.set_thumbnail(url=bot.user.avatar.url)

            # Footer with additional info
            embed.set_footer(
                text=f"QuranBot v1.6.2 • Requested by {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.response.send_message(embed=embed, ephemeral=False)

            log_tree_branch(
                "command_completed",
                f"✅ Credits displayed for {interaction.user.display_name}",
            )

        except Exception as e:
            log_tree_branch("command_error", f"❌ Error: {str(e)}")
            await interaction.response.send_message(
                "❌ An error occurred while displaying credits. Please try again.",
                ephemeral=True,
            )

    @bot.tree.command(
        name="devping", description="Developer ping command for API tracking"
    )
    async def devping(interaction: discord.Interaction):
        """Hidden developer command that makes multiple API calls for Discord tracking"""
        try:
            # Log user interaction
            log_user_interaction(
                interaction_type="slash_command",
                user_name=interaction.user.display_name,
                user_id=interaction.user.id,
                action_description="Used /devping command",
                details={
                    "command": "devping",
                    "purpose": "API tracking for Active Developer Badge",
                },
            )

            # Multiple API calls that Discord tracks
            api_calls_made = 0

            try:
                # 1. Fetch bot user info
                bot_user = await bot.fetch_user(bot.user.id)
                api_calls_made += 1

                # 2. Fetch command user info
                user_info = await bot.fetch_user(interaction.user.id)
                api_calls_made += 1

                # 3. Fetch guild info if available
                if interaction.guild:
                    guild_info = await bot.fetch_guild(interaction.guild.id)
                    api_calls_made += 1

                    # 4. Fetch guild members (limited)
                    members = []
                    async for member in interaction.guild.fetch_members(limit=5):
                        members.append(member)
                    api_calls_made += len(members)

                # 5. Fetch channel info
                channel_info = await bot.fetch_channel(interaction.channel_id)
                api_calls_made += 1

                # 6. Get bot application info
                app_info = await bot.application_info()
                api_calls_made += 1

                log_tree_branch(
                    "api_tracking",
                    f"✅ Made {api_calls_made} API calls for Discord tracking",
                )

            except Exception as e:
                log_tree_branch(
                    "api_error",
                    f"⚠️ Some API calls failed: {str(e)}",
                )

            embed = discord.Embed(
                title="🔧 Developer Ping",
                description=f"API tracking ping completed!\n\n**API Calls Made:** {api_calls_made}\n**Bot Status:** ✅ Active\n**Purpose:** Discord Active Developer Badge tracking",
                color=0x00FF00,
                timestamp=interaction.created_at,
            )

            embed.set_footer(
                text=f"DevPing • {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            log_tree_branch("command_error", f"❌ Error: {str(e)}")
            await interaction.response.send_message(
                "❌ DevPing failed. Please try again.", ephemeral=True
            )

    log_tree_branch(
        "command_registered",
        "✅ /credits command registered with bot tree",
    )
    log_tree_branch(
        "devping_registered",
        "✅ /devping command registered with bot tree",
    )
    log_tree_branch("command_name", "credits")
    log_tree_branch(
        "command_description",
        "Show bot information, credits, and GitHub repository",
    )
    log_tree_final(
        "setup_completed",
        "✅ Credits command setup completed successfully",
    )


# =============================================================================
# Export Functions
# =============================================================================

__all__ = [
    "credits_command",
    "setup_credits_command",
]
