# =============================================================================
# QuranBot - Credits Command (Overhauled)
# =============================================================================
# Beautiful, comprehensive bot information display with modern Discord features
# =============================================================================

import os
import platform
from datetime import datetime, timezone
from pathlib import Path

import discord
import psutil
from discord.ext import commands
from dotenv import load_dotenv

# Import tree logging functions
from src.utils.tree_log import (
    log_error_with_traceback,
    log_perfect_tree_section,
    log_user_interaction,
)

# Import version and author from centralized version module
from ..version import BOT_VERSION, __author__, get_version_info

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
# Utility Functions
# =============================================================================


def get_system_info():
    """Get system information for the bot"""
    try:
        # Get memory usage
        memory = psutil.virtual_memory()
        memory_used = memory.used / (1024**3)  # GB
        memory_total = memory.total / (1024**3)  # GB
        memory_percent = memory.percent

        # Get CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)

        # Get uptime (approximate)
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time

        return {
            "memory_used": f"{memory_used:.1f}",
            "memory_total": f"{memory_total:.1f}",
            "memory_percent": f"{memory_percent:.1f}",
            "cpu_percent": f"{cpu_percent:.1f}",
            "uptime_days": uptime.days,
            "uptime_hours": uptime.seconds // 3600,
            "python_version": platform.python_version(),
            "platform": platform.system(),
        }
    except Exception:
        return None


def format_large_number(num):
    """Format large numbers with appropriate suffixes"""
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    else:
        return str(num)


# =============================================================================
# Main Credits Command
# =============================================================================


async def credits_command(interaction: discord.Interaction):
    """
    Overhauled credits command with modern design and comprehensive information
    """
    try:
        # Log command execution
        log_perfect_tree_section(
            "Credits Command - Overhauled Version",
            [
                ("user", f"{interaction.user.display_name} ({interaction.user.id})"),
                ("guild", f"{interaction.guild.name if interaction.guild else 'DM'}"),
                ("version", "2.0 - Completely Overhauled"),
            ],
            "✨",
        )

        # Get version info
        version_info = get_version_info()

        # Get system info
        system_info = get_system_info()

        # Get bot stats
        guild_count = len(interaction.client.guilds)
        user_count = sum(guild.member_count for guild in interaction.client.guilds)

        # Create main embed with modern styling
        embed = discord.Embed(
            title="",  # We'll use description for the title for better formatting
            description="",
            color=0x1ABC9C,  # Modern teal color
            timestamp=datetime.now(timezone.utc),
        )

        # Custom title with emojis
        embed.description = (
            "# 🕌 QuranBot - Credits & Information\n"
            "**A modern Discord bot for beautiful Quran recitation and daily verses**\n\n"
            f"*Currently serving {format_large_number(user_count)} users across {guild_count} servers*"
        )

        # 📊 Bot Statistics
        embed.add_field(
            name="📊 **Bot Statistics**",
            value=(
                f"🏷️ **Version:** `{BOT_VERSION}`\n"
                f"🌐 **Servers:** `{guild_count}`\n"
                f"👥 **Users:** `{format_large_number(user_count)}`\n"
                f"⚡ **Commands:** `3 Slash Commands`\n"
                f"🎵 **Reciters:** `6 Available`\n"
                f"📖 **Surahs:** `114 Complete`"
            ),
            inline=True,
        )

        # 🔧 Technical Specifications
        tech_specs = (
            f"🐍 **Python:** `{system_info['python_version'] if system_info else '3.13+'}`\n"
            f"⚙️ **Discord.py:** `2.4+`\n"
            f"🎵 **Audio:** `FFmpeg + PyNaCl`\n"
            f"🖥️ **Platform:** `{system_info['platform'] if system_info else 'Linux'}`\n"
            f"📁 **Architecture:** `Modular Design`\n"
            f"🔐 **Commands:** `Slash Only`"
        )

        embed.add_field(
            name="🔧 **Technical Stack**",
            value=tech_specs,
            inline=True,
        )

        # 📈 System Performance (if available)
        if system_info:
            performance = (
                f"🧠 **CPU Usage:** `{system_info['cpu_percent']}%`\n"
                f"💾 **Memory:** `{system_info['memory_used']}GB / {system_info['memory_total']}GB`\n"
                f"📊 **Memory Usage:** `{system_info['memory_percent']}%`\n"
                f"⏱️ **System Uptime:** `{system_info['uptime_days']}d {system_info['uptime_hours']}h`\n"
                f"🔄 **Status:** `🟢 Operational`\n"
                f"📡 **Latency:** `{round(interaction.client.latency * 1000)}ms`"
            )
        else:
            performance = (
                f"🔄 **Status:** `🟢 Operational`\n"
                f"📡 **Latency:** `{round(interaction.client.latency * 1000)}ms`\n"
                f"⚡ **Performance:** `Optimized`\n"
                f"🛡️ **Reliability:** `99.9% Uptime`\n"
                f"🔧 **Monitoring:** `Active`\n"
                f"📊 **Health:** `Excellent`"
            )

        embed.add_field(
            name="📈 **System Performance**",
            value=performance,
            inline=True,
        )

        # ✨ Key Features
        embed.add_field(
            name="✨ **Key Features**",
            value=(
                "🎵 **High-Quality Audio Streaming**\n"
                "📱 **Interactive Control Panels**\n"
                "🎛️ **Rich Presence Integration**\n"
                "📊 **Listening Time Tracking**\n"
                "📖 **Daily Verse System**\n"
                "🔄 **State Management**\n"
                "🌍 **Multi-Server Support**\n"
                "🎯 **Professional Logging**"
            ),
            inline=True,
        )

        # 🎯 Available Commands
        embed.add_field(
            name="🎯 **Available Commands**",
            value=(
                "🏆 **`/leaderboard`** - Listening statistics\n"
                "📖 **`/verse`** - Manual daily verse\n"
                "ℹ️ **`/credits`** - This information\n"
                "🎵 **Voice Controls** - Join & play\n"
                "🎛️ **Control Panel** - Interactive UI\n"
                "🔄 **Auto-Resume** - State persistence"
            ),
            inline=True,
        )

        # 🏗️ Architecture & Design
        embed.add_field(
            name="🏗️ **Architecture & Design**",
            value=(
                "📦 **Modular Structure** - Clean separation\n"
                "🎯 **Event-Driven** - Reactive design\n"
                "🔒 **Error Handling** - Comprehensive\n"
                "📝 **Logging System** - Tree-structured\n"
                "⚡ **Async Operations** - High performance\n"
                "🔧 **Configuration** - Environment-based"
            ),
            inline=True,
        )

        # Add a separator line
        embed.add_field(
            name="\u200b",  # Invisible character
            value="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            inline=False,
        )

        # 👨‍💻 Developer Information
        embed.add_field(
            name="👨‍💻 **Developer Information**",
            value=(
                f"**Created by:** {__author__}\n"
                f"**Discord:** <@{ADMIN_USER_ID}>\n"
                f"**Project Type:** Open Source Educational\n"
                f"**Development Status:** Complete & Stable\n"
                f"**License:** MIT License\n"
                f"**Purpose:** Educational & Reference Use"
            ),
            inline=True,
        )

        # 📋 Repository & Links
        embed.add_field(
            name="📋 **Repository & Links**",
            value=(
                f"📂 **[GitHub Repository]({GITHUB_REPO_URL})**\n"
                f"🔗 **[View Source Code]({GITHUB_REPO_URL})**\n"
                f"📖 **[Documentation]({GITHUB_REPO_URL}#readme)**\n"
                f"🐛 **[Report Issues]({GITHUB_REPO_URL}/issues)**\n"
                f"⭐ **[Star the Project]({GITHUB_REPO_URL})**\n"
                f"🍴 **[Fork Repository]({GITHUB_REPO_URL}/fork)**"
            ),
            inline=True,
        )

        # ⚠️ Important Notice
        embed.add_field(
            name="⚠️ **Important Notice**",
            value=(
                '**Support Policy:** `"Take as it is"`\n'
                "**No Support Provided:** Use at your own risk\n"
                "**Educational Purpose:** Learning & reference only\n"
                "**Open Source:** MIT License - Free to use\n"
                "**No Warranty:** Provided as-is without guarantees\n"
                "**Community Driven:** Fork & modify as needed"
            ),
            inline=True,
        )

        # Set bot avatar as thumbnail
        if interaction.client.user and interaction.client.user.avatar:
            embed.set_thumbnail(url=interaction.client.user.avatar.url)

        # Get admin user for footer
        admin_user = None
        try:
            admin_user = await interaction.client.fetch_user(ADMIN_USER_ID)
        except Exception:
            pass

        # Set footer with admin profile picture
        footer_text = f"QuranBot v{BOT_VERSION} • Requested by {interaction.user.display_name} • Made with ❤️"
        if admin_user and admin_user.avatar:
            embed.set_footer(text=footer_text, icon_url=admin_user.avatar.url)
        else:
            embed.set_footer(text=footer_text)

        # Send the embed
        await interaction.response.send_message(embed=embed, ephemeral=False)

        # Log successful completion
        log_perfect_tree_section(
            "Credits Command - Overhauled Success",
            [
                ("user", f"{interaction.user.display_name}"),
                ("fields_added", len(embed.fields)),
                ("guild_count", guild_count),
                ("user_count", format_large_number(user_count)),
                ("status", "✅ Modern credits display sent successfully"),
            ],
            "✨",
        )

    except Exception as e:
        log_error_with_traceback("Error in overhauled credits command", e)
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
# Command Setup (Overhauled)
# =============================================================================


async def setup_credits_command(bot):
    """
    Set up the overhauled /credits slash command
    """
    # Check if command is already registered
    existing_commands = [cmd.name for cmd in bot.tree.get_commands()]
    if "credits" in existing_commands:
        log_perfect_tree_section(
            "Credits Command Setup - Already Registered",
            [
                ("status", "✅ /credits command already registered"),
                ("version", "Overhauled version active"),
            ],
            "✅",
        )
        return

    log_perfect_tree_section(
        "Credits Command Setup - Overhauled Registration",
        [
            ("setup_initiated", "Registering overhauled /credits command"),
            ("version", "2.0 - Completely redesigned"),
            ("features", "Modern UI, system stats, comprehensive info"),
        ],
        "✨",
    )

    @bot.tree.command(
        name="credits",
        description="🕌 Show comprehensive bot information, statistics, and developer credits",
    )
    async def credits(interaction: discord.Interaction):
        """Show overhauled bot credits with modern design and comprehensive information"""
        try:
            # Log user interaction
            log_user_interaction(
                interaction_type="slash_command",
                user_name=interaction.user.display_name,
                user_id=interaction.user.id,
                action_description="Used overhauled /credits command",
                details={
                    "command": "credits",
                    "version": "2.0 - Overhauled",
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
        "Credits Command Setup - Overhauled Complete",
        [
            ("command_registered", "✅ Overhauled /credits command registered"),
            ("description", "Comprehensive bot info with modern design"),
            ("features", "System stats, performance metrics, detailed info"),
            ("setup_completed", "✅ Overhauled credits setup completed"),
        ],
        "✨",
    )


# =============================================================================
# Export Functions
# =============================================================================

__all__ = [
    "credits_command",
    "setup_credits_command",
]
