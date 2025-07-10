# =============================================================================
# QuranBot - Verse Command (Open Source Edition)
# =============================================================================
# This is an open source project provided AS-IS without official support.
# Feel free to use, modify, and learn from this code under the license terms.
#
# Purpose:
# Administrative Discord slash command for manual control of the daily verse
# system. Demonstrates proper command structure, permission handling, and
# error management in Discord.py applications.
#
# Key Features:
# - Slash command implementation
# - Admin-only access control
# - Rich embed responses
# - Comprehensive error handling
# - Detailed logging
# - State management integration
#
# Technical Implementation:
# - Uses discord.py's app_commands
# - Environment-based configuration
# - Asynchronous execution
# - Modular component design
#
# Required Permissions:
# - Bot must have permission to send messages and embeds
# - User must be configured as admin in environment
#
# Environment Variables:
# - DEVELOPER_ID: Discord ID of bot administrator
# =============================================================================

import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import discord
from discord.ext import commands

from src.utils.tree_log import log_error_with_traceback, log_perfect_tree_section


def get_daily_verses_manager():
    """
    Safely retrieve the daily verses manager instance.

    This function demonstrates proper error handling and dependency
    management in a Discord bot context. It uses lazy loading to
    prevent circular imports and provides graceful fallback.

    Returns:
        Optional[DailyVersesManager]: The manager instance or None if error

    Implementation Notes:
    - Uses lazy imports to prevent circular dependencies
    - Provides comprehensive error logging
    - Returns None instead of raising exceptions
    """
    try:
        from src.utils.daily_verses import daily_verse_manager

        return daily_verse_manager
    except Exception as e:
        log_error_with_traceback("Failed to import daily_verse_manager", e)
        return None


@discord.app_commands.command(
    name="verse",
    description="Send a daily verse manually and reset the 3-hour timer (Admin only)",
)
async def verse_slash_command(interaction: discord.Interaction):
    """
    Administrative command to manually trigger daily verse delivery.

    This is an open source implementation demonstrating proper Discord
    slash command structure with permission handling, error management,
    and user feedback.

    Features:
    - Admin-only access control
    - Rich embed responses
    - Comprehensive error handling
    - Detailed logging
    - State validation

    Flow:
    1. Validate system configuration
    2. Check user permissions
    3. Verify verse system state
    4. Execute verse delivery
    5. Update timers and state

    Error Handling:
    - Configuration errors
    - Permission issues
    - System state problems
    - Runtime exceptions

    Usage:
    /verse - Manually trigger verse delivery (admin only)
    """

    # Log command initiation
    log_perfect_tree_section(
        "Verse Command - Initiated",
        [
            ("user", f"{interaction.user.display_name} ({interaction.user.id})"),
            ("guild", f"{interaction.guild.name}" if interaction.guild else "DM"),
            (
                "channel",
                (
                    f"#{interaction.channel.name}"
                    if hasattr(interaction.channel, "name")
                    else "DM"
                ),
            ),
            ("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ("status", "🔄 Starting verse command execution"),
        ],
        "📖",
    )

    try:
        # Get the daily verses manager with error handling
        daily_verses_manager = get_daily_verses_manager()
        if not daily_verses_manager:
            log_perfect_tree_section(
                "Verse Command - Critical Error",
                [
                    ("error", "❌ Failed to get daily_verses_manager"),
                    (
                        "user",
                        f"{interaction.user.display_name} ({interaction.user.id})",
                    ),
                    ("status", "🚨 Command execution aborted"),
                ],
                "⚠️",
            )

            error_embed = discord.Embed(
                title="❌ System Error",
                description="Critical system error: Daily verses manager unavailable. Please contact the administrator.",
                color=0xFF6B6B,
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return

        # Get developer ID from environment with error handling
        try:
            DEVELOPER_ID = int(os.getenv("DEVELOPER_ID") or "0")
            if DEVELOPER_ID == 0:
                raise ValueError("DEVELOPER_ID not set in environment")
        except (ValueError, TypeError) as e:
            log_error_with_traceback("Failed to get DEVELOPER_ID from environment", e)

            log_perfect_tree_section(
                "Verse Command - Configuration Error",
                [
                    ("error", "❌ DEVELOPER_ID not configured"),
                    (
                        "user",
                        f"{interaction.user.display_name} ({interaction.user.id})",
                    ),
                    ("status", "🚨 Command execution aborted"),
                ],
                "⚠️",
            )

            error_embed = discord.Embed(
                title="❌ Configuration Error",
                description="Bot configuration error: Developer ID not set. Please contact the administrator.",
                color=0xFF6B6B,
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return

        # Check if user is the developer/admin
        if interaction.user.id != DEVELOPER_ID:
            log_perfect_tree_section(
                "Verse Command - Permission Denied",
                [
                    (
                        "user",
                        f"{interaction.user.display_name} ({interaction.user.id})",
                    ),
                    ("required_id", str(DEVELOPER_ID)),
                    ("status", "❌ Unauthorized access attempt"),
                    ("action", "🚫 Command execution denied"),
                ],
                "🔒",
            )

            embed = discord.Embed(
                title="❌ Permission Denied",
                description="This command is only available to the bot administrator.",
                color=0xFF6B6B,
            )

            # Set footer with admin profile picture with error handling
            try:
                admin_user = await interaction.client.fetch_user(DEVELOPER_ID)
                if admin_user and admin_user.avatar:
                    embed.set_footer(
                        text="Created by حَـــــنَـــــا", icon_url=admin_user.avatar.url
                    )
                else:
                    embed.set_footer(text="Created by حَـــــنَـــــا")
            except Exception as avatar_error:
                log_error_with_traceback(
                    "Failed to fetch admin avatar for permission denied message",
                    avatar_error,
                )
                embed.set_footer(text="Created by حَـــــنَـــــا")

            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Log successful authentication
        log_perfect_tree_section(
            "Verse Command - Authentication Success",
            [
                ("user", f"{interaction.user.display_name} ({interaction.user.id})"),
                ("permission_level", "🔓 Admin verified"),
                ("status", "✅ Authentication passed"),
            ],
            "🔐",
        )

        # Check if daily verses system is configured
        if not daily_verses_manager.verse_pool:
            log_perfect_tree_section(
                "Verse Command - System Not Configured",
                [
                    (
                        "verse_pool",
                        f"❌ Empty ({len(daily_verses_manager.verse_pool)} verses)",
                    ),
                    ("status", "🚨 Daily verses system not properly configured"),
                ],
                "⚠️",
            )

            embed = discord.Embed(
                title="❌ Daily Verses Not Configured",
                description="The daily verses system is not properly configured. No verses are available in the pool.",
                color=0xFF6B6B,
            )

            # Set footer with admin profile picture with error handling
            try:
                admin_user = await interaction.client.fetch_user(DEVELOPER_ID)
                if admin_user and admin_user.avatar:
                    embed.set_footer(
                        text="Created by حَـــــنَـــــا", icon_url=admin_user.avatar.url
                    )
                else:
                    embed.set_footer(text="Created by حَـــــنَـــــا")
            except Exception as avatar_error:
                log_error_with_traceback(
                    "Failed to fetch admin avatar for configuration error message",
                    avatar_error,
                )
                embed.set_footer(text="Created by حَـــــنَـــــا")

            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Get a random verse from the daily verses manager
        try:
            verse = daily_verses_manager.get_random_verse()
        except Exception as e:
            log_error_with_traceback(
                "Failed to get random verse from daily verses manager", e
            )
            verse = None

        # Check if we got a verse
        if not verse:
            log_perfect_tree_section(
                "Verse Command - No Verses Available",
                [
                    (
                        "pool_size",
                        f"📊 Pool size: {len(daily_verses_manager.verse_pool)}",
                    ),
                    ("status", "❌ No verses available"),
                ],
                "📚",
            )

            embed = discord.Embed(
                title="❌ No Verses Available",
                description="The daily verses system is not properly configured or has no verses available.",
                color=0xFF0000,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Get channel for sending verse
        try:
            DAILY_VERSE_CHANNEL_ID = int(os.getenv("DAILY_VERSE_CHANNEL_ID") or "0")
            if DAILY_VERSE_CHANNEL_ID == 0:
                await interaction.response.send_message(
                    "❌ Daily verse channel not configured. Please set DAILY_VERSE_CHANNEL_ID in environment.",
                    ephemeral=True,
                )
                return

            channel = interaction.client.get_channel(DAILY_VERSE_CHANNEL_ID)
            if not channel:
                await interaction.response.send_message(
                    f"❌ Could not find daily verse channel with ID {DAILY_VERSE_CHANNEL_ID}.",
                    ephemeral=True,
                )
                return
        except Exception as e:
            log_error_with_traceback("Failed to get daily verse channel", e)
            await interaction.response.send_message(
                "❌ Failed to access daily verse channel.", ephemeral=True
            )
            return

        # Extract verse information with proper field names
        surah_number = verse.get("surah", "Unknown")
        ayah_number = verse.get("ayah", verse.get("verse", "Unknown"))

        # Get surah name from surah mapper
        try:
            from src.utils.surah_mapper import get_surah_name

            surah_name = get_surah_name(surah_number)
        except Exception:
            surah_name = f"Surah {surah_number}"

        # Update last sent verse
        try:
            daily_verses_manager.save_state()
        except Exception as e:
            log_error_with_traceback("Failed to update last sent verse", e)

        # Calculate next automatic verse time
        current_time = datetime.now(timezone.utc).astimezone(
            timezone(timedelta(hours=-5))
        )  # EST
        next_auto_time = current_time + timedelta(hours=3)  # Default 3 hour interval
        hours_until_next = 3

        log_perfect_tree_section(
            "Verse Command - Next Timer Calculated",
            [
                (
                    "current_time",
                    f"{current_time.strftime('%Y-%m-%d %I:%M:%S %p')} EST",
                ),
                (
                    "next_auto_time",
                    f"{next_auto_time.strftime('%Y-%m-%d %I:%M:%S %p')} EST",
                ),
                ("hours_until_next", f"{hours_until_next}"),
                ("status", "✅ Next automatic verse time calculated"),
            ],
            "🕐",
        )

        # Send confirmation message to user
        try:
            confirmation_embed = discord.Embed(
                title="📖 Verse Sent Successfully",
                description=f"**{surah_name} ({surah_number}:{ayah_number})** has been sent to {channel.mention}",
                color=0x2ECC71,
            )
            confirmation_embed.add_field(
                name="⏰ Next Automatic Verse",
                value=f"In approximately **{hours_until_next} hours** at {next_auto_time.strftime('%I:%M %p')} EST",
                inline=False,
            )
            await interaction.response.send_message(
                embed=confirmation_embed, ephemeral=True
            )
        except Exception as e:
            log_error_with_traceback("Failed to send confirmation message to user", e)
            await interaction.response.send_message(
                "✅ Verse sent successfully!", ephemeral=True
            )

        # Create and send verse embed
        try:
            embed = discord.Embed(
                title=f"📖 Daily Verse - {surah_name}",
                description=f"Ayah {ayah_number}",
                color=0x2ECC71,
            )

            # Add bot's profile picture as thumbnail
            if interaction.client.user and interaction.client.user.avatar:
                embed.set_thumbnail(url=interaction.client.user.avatar.url)
            elif interaction.client.user:
                # Fallback to default avatar if no custom avatar
                embed.set_thumbnail(url=interaction.client.user.default_avatar.url)

            # Add Arabic section with code block formatting
            embed.add_field(
                name="🌙 Arabic",
                value=f"```\n{verse.get('arabic', verse['text'])}\n```",
                inline=False,
            )

            # Add Translation section with code block formatting
            embed.add_field(
                name="📝 Translation",
                value=f"```\n{verse['translation']}\n```",
                inline=False,
            )

            # Set footer with creator information
            try:
                DEVELOPER_ID = int(os.getenv("DEVELOPER_ID") or "0")
                if DEVELOPER_ID != 0:
                    admin_user = await interaction.client.fetch_user(DEVELOPER_ID)
                    if admin_user and admin_user.avatar:
                        embed.set_footer(
                            text="created by حَـــــنَّـــــا",
                            icon_url=admin_user.avatar.url,
                        )
                    else:
                        embed.set_footer(text="created by حَـــــنَّـــــا")
                else:
                    embed.set_footer(text="created by حَـــــنَّـــــا")
            except Exception as e:
                log_error_with_traceback("Failed to set footer with admin avatar", e)
                embed.set_footer(text="created by حَـــــنَّـــــا")

            # Send message
            message = await channel.send(embed=embed)

            # Add dua reaction
            try:
                await message.add_reaction("🤲")

                # Monitor reactions to remove unwanted ones
                def check_reaction(reaction, user):
                    return (
                        reaction.message.id == message.id
                        and str(reaction.emoji) != "🤲"
                        and not user.bot
                    )

                # Set up reaction monitoring in background
                async def monitor_reactions():
                    try:
                        while True:
                            reaction, user = await interaction.client.wait_for(
                                "reaction_add",
                                timeout=3600,  # Monitor for 1 hour
                                check=check_reaction,
                            )
                            # Remove the unwanted reaction
                            await reaction.remove(user)
                    except asyncio.TimeoutError:
                        pass  # Stop monitoring after timeout
                    except Exception:
                        pass  # Ignore any other errors

                # Start monitoring task in background
                asyncio.create_task(monitor_reactions())

            except Exception as e:
                log_error_with_traceback(
                    "Failed to add dua reaction or set up monitoring", e
                )

        except Exception as e:
            log_error_with_traceback("Failed to create or send verse embed", e)
            await interaction.followup.send(
                "❌ Failed to send verse embed.", ephemeral=True
            )
            return

        # Log success
        log_perfect_tree_section(
            "Verse Command - Success",
            [
                ("user", f"{interaction.user.display_name} ({interaction.user.id})"),
                ("surah", f"{surah_name} ({surah_number}:{ayah_number})"),
                ("channel", f"{channel.name} ({channel.id})"),
                ("status", "✅ Verse sent successfully"),
            ],
            "📖",
        )

    except discord.errors.NotFound as not_found_error:
        log_error_with_traceback(
            "Discord entity not found during verse command execution", not_found_error
        )

        log_perfect_tree_section(
            "Verse Command - Discord Not Found Error",
            [
                ("error_type", "discord.errors.NotFound"),
                ("user", f"{interaction.user.display_name} ({interaction.user.id})"),
                ("status", "❌ Discord entity not found"),
            ],
            "🔍",
        )

        error_embed = discord.Embed(
            title="❌ Discord Error",
            description="A Discord entity (user, channel, message, etc.) could not be found. Please check the configuration.",
            color=0xFF6B6B,
        )
        error_embed.set_footer(text="Created by حَـــــنَـــــا")

        # Handle both responded and unresponded interactions
        try:
            if interaction.response.is_done():
                await interaction.followup.send(embed=error_embed, ephemeral=True)
            else:
                await interaction.response.send_message(
                    embed=error_embed, ephemeral=True
                )
        except Exception as response_error:
            log_error_with_traceback(
                "Failed to send Discord not found error message", response_error
            )

    except discord.errors.Forbidden as forbidden_error:
        log_error_with_traceback(
            "Discord permission denied during verse command execution", forbidden_error
        )

        log_perfect_tree_section(
            "Verse Command - Discord Permission Error",
            [
                ("error_type", "discord.errors.Forbidden"),
                ("user", f"{interaction.user.display_name} ({interaction.user.id})"),
                ("status", "❌ Bot lacks required permissions"),
            ],
            "🚫",
        )

        error_embed = discord.Embed(
            title="❌ Permission Error",
            description="The bot lacks the required permissions to complete this action. Please check bot permissions.",
            color=0xFF6B6B,
        )
        error_embed.set_footer(text="Created by حَـــــنَـــــا")

        # Handle both responded and unresponded interactions
        try:
            if interaction.response.is_done():
                await interaction.followup.send(embed=error_embed, ephemeral=True)
            else:
                await interaction.response.send_message(
                    embed=error_embed, ephemeral=True
                )
        except Exception as response_error:
            log_error_with_traceback(
                "Failed to send Discord permission error message", response_error
            )

    except discord.errors.HTTPException as http_error:
        log_error_with_traceback(
            "Discord HTTP error during verse command execution", http_error
        )

        log_perfect_tree_section(
            "Verse Command - Discord HTTP Error",
            [
                ("error_type", "discord.errors.HTTPException"),
                ("user", f"{interaction.user.display_name} ({interaction.user.id})"),
                ("status", "❌ Discord API error"),
            ],
            "🌐",
        )

        error_embed = discord.Embed(
            title="❌ Discord API Error",
            description="A Discord API error occurred. Please try again later.",
            color=0xFF6B6B,
        )
        error_embed.set_footer(text="Created by حَـــــنَـــــا")

        # Handle both responded and unresponded interactions
        try:
            if interaction.response.is_done():
                await interaction.followup.send(embed=error_embed, ephemeral=True)
            else:
                await interaction.response.send_message(
                    embed=error_embed, ephemeral=True
                )
        except Exception as response_error:
            log_error_with_traceback(
                "Failed to send Discord HTTP error message", response_error
            )

    except Exception as e:
        log_error_with_traceback("Unexpected error in manual verse command", e)

        log_perfect_tree_section(
            "Verse Command - Unexpected Error",
            [
                ("error_type", type(e).__name__),
                ("user", f"{interaction.user.display_name} ({interaction.user.id})"),
                ("status", "❌ Unexpected error occurred"),
                ("impact", "🚨 Command execution failed"),
            ],
            "💥",
        )

        error_embed = discord.Embed(
            title="❌ Unexpected Error",
            description="An unexpected error occurred while processing the verse command. Please check the logs for details.",
            color=0xFF6B6B,
        )

        # Set footer with admin profile picture with error handling
        try:
            DEVELOPER_ID = int(os.getenv("DEVELOPER_ID") or "0")
            admin_user = await interaction.client.fetch_user(DEVELOPER_ID)
            if admin_user and admin_user.avatar:
                error_embed.set_footer(
                    text="Created by حَـــــنَـــــا", icon_url=admin_user.avatar.url
                )
            else:
                error_embed.set_footer(text="Created by حَـــــنَـــــا")
        except Exception as avatar_error:
            log_error_with_traceback(
                "Failed to fetch admin avatar for unexpected error message",
                avatar_error,
            )
            error_embed.set_footer(text="Created by حَـــــنَـــــا")

        # Handle both responded and unresponded interactions
        try:
            if interaction.response.is_done():
                await interaction.followup.send(embed=error_embed, ephemeral=True)
            else:
                await interaction.response.send_message(
                    embed=error_embed, ephemeral=True
                )
        except Exception as response_error:
            log_error_with_traceback(
                "Failed to send unexpected error message", response_error
            )


async def setup_verse_command(bot):
    """Set up the verse command with comprehensive error handling and logging"""
    try:
        log_perfect_tree_section(
            "Verse Command Setup - Starting",
            [
                ("command_name", "/verse"),
                ("command_type", "Discord Application Command"),
                ("status", "🔄 Initializing verse command setup"),
            ],
            "🚀",
        )

        # Add the slash command to the bot's command tree
        bot.tree.add_command(verse_slash_command)

        log_perfect_tree_section(
            "Verse Command Setup - Complete",
            [
                ("status", "✅ Verse command loaded successfully"),
                ("command_name", "/verse"),
                ("command_type", "Slash command only"),
                ("description", "Send daily verse manually and reset timer"),
                ("permission_level", "🔒 Admin only"),
                ("error_handling", "✅ Comprehensive traceback and logging"),
                ("tree_logging", "✅ Perfect tree logging implemented"),
            ],
            "📖",
        )

    except Exception as setup_error:
        log_error_with_traceback("Failed to set up verse command", setup_error)

        log_perfect_tree_section(
            "Verse Command Setup - Failed",
            [
                ("error_type", type(setup_error).__name__),
                ("status", "❌ Failed to load verse command"),
                ("impact", "🚨 /verse command will not be available"),
            ],
            "💥",
        )

        # Re-raise the exception to ensure the bot startup process is aware of the failure
        raise
