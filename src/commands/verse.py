# =============================================================================
# QuranBot - Verse Command (Cog)
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
# - Uses discord.py's app_commands with Cogs
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
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from src.core.exceptions import ConfigurationError
from src.core.security import rate_limit, require_admin
from src.utils import daily_verses
from src.utils.discord_logger import get_discord_logger
from src.utils.tree_log import (
    log_error_with_traceback,
    log_perfect_tree_section,
    log_user_interaction,
)


def get_daily_verses_manager():
    """
    Safely retrieve the daily verses manager instance.

    This function demonstrates proper error handling and dependency
    management in a Discord bot context. It uses lazy loading to
    prevent circular imports and provides graceful fallback.

    Returns:
        Optional[DailyVerseManager]: The manager instance or None if error

    Implementation Notes:
    - Uses lazy imports to prevent circular dependencies
    - Provides comprehensive error logging
    - Returns None instead of raising exceptions
    """
    try:
        # Access the global manager from the daily_verses module
        return daily_verses.daily_verse_manager
    except Exception as e:
        log_error_with_traceback("Failed to access daily_verse_manager", e)
        return None


# =============================================================================
# Verse Cog
# =============================================================================


class VerseCog(commands.Cog):
    """Verse command cog for manual daily verse delivery"""

    def __init__(self, bot, container=None):
        self.bot = bot
        self.container = container

    @app_commands.command(
        name="verse",
        description="Send a daily verse manually and reset the 3-hour timer (Admin only)",
    )
    @require_admin
    @rate_limit(
        user_limit=2, user_window=60
    )  # 2 requests per minute for admin commands
    async def verse(self, interaction: discord.Interaction):
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
                await interaction.response.send_message(
                    embed=error_embed, ephemeral=True
                )
                return

            # Permission checking is now handled by @require_admin decorator
            # Log authorized access
            log_perfect_tree_section(
                "Verse Command - Authorized Access",
                [
                    (
                        "user",
                        f"{interaction.user.display_name} ({interaction.user.id})",
                    ),
                    ("permission_level", "✅ Administrator"),
                    ("status", "🔓 Access granted"),
                    ("action", "🚀 Proceeding with verse delivery"),
                ],
                "🔓",
            )

            # Send a quick acknowledgment to the user
            ack_embed = discord.Embed(
                title="📖 Processing Verse Command",
                description="Processing your verse request...",
                color=0x3498DB,
            )
            ack_embed.set_footer(text="Created by حَـــــنَـــــا")
            await interaction.response.send_message(embed=ack_embed, ephemeral=True)

            # Get the daily verse channel
            try:
                from src.config import get_config_service

                config = get_config_service().config

                channel = interaction.client.get_channel(config.DAILY_VERSE_CHANNEL_ID)
                if not channel:
                    channel = await interaction.client.fetch_channel(
                        config.DAILY_VERSE_CHANNEL_ID
                    )

                if not channel:
                    raise ConfigurationError(
                        f"Channel {config.DAILY_VERSE_CHANNEL_ID} not found",
                        config_field="DAILY_VERSE_CHANNEL_ID",
                        config_value=config.DAILY_VERSE_CHANNEL_ID,
                    )

            except Exception as e:
                log_error_with_traceback("Failed to get daily verse channel", e)

                error_embed = discord.Embed(
                    title="❌ Channel Error",
                    description="Could not find the daily verse channel. Please check the bot configuration.",
                    color=0xFF6B6B,
                )
                await interaction.followup.send(embed=error_embed, ephemeral=True)
                return

            # Get a random verse from the manager
            verse_data = daily_verses_manager.get_random_verse()

            if not verse_data:
                log_perfect_tree_section(
                    "Verse Command - No Verses Available",
                    [
                        ("error", "❌ No verses available"),
                        ("status", "🚨 Command execution failed"),
                    ],
                    "⚠️",
                )

                error_embed = discord.Embed(
                    title="❌ No Verses Available",
                    description="No verses are currently available in the system.",
                    color=0xFF6B6B,
                )
                await interaction.followup.send(embed=error_embed, ephemeral=True)
                return

            # Update the last sent time to reset the timer
            try:
                daily_verses_manager.update_last_sent_time()
            except Exception as e:
                log_error_with_traceback("Failed to update last sent verse", e)

            # Log verse selection
            log_perfect_tree_section(
                "Verse Command - Verse Selected",
                [
                    ("verse_id", verse_data.get("id", "Unknown")),
                    ("surah", verse_data.get("surah", "Unknown")),
                    ("verse_number", verse_data.get("verse_number", "Unknown")),
                    ("status", "✅ Verse selected successfully"),
                ],
                "📖",
            )

            # Create the verse embed (matching the proper format)
            surah_name = verse_data.get(
                "surah_name", f"Surah {verse_data.get('surah', 'Unknown')}"
            )
            arabic_name = verse_data.get("arabic_name", "")

            # Format the title like in the screenshot
            if arabic_name:
                title = f"📖 Daily Verse - {surah_name} ({arabic_name})"
            else:
                title = f"📖 Daily Verse - {surah_name}"

            embed = discord.Embed(
                title=title,
                color=0x2ECC71,  # Green color matching screenshot
            )

            # Add Ayah number as description
            embed.description = (
                f"Ayah {verse_data.get('ayah', verse_data.get('verse', 'Unknown'))}"
            )

            # Add Arabic text with moon emoji and code block formatting
            arabic_text = verse_data.get("arabic", "Arabic text not available")
            embed.add_field(
                name="🌙 Arabic",
                value=f"```{arabic_text}```",
                inline=False,
            )

            # Add English translation with scroll emoji and code block formatting
            english_text = verse_data.get(
                "translation", "English translation not available"
            )
            embed.add_field(
                name="📝 Translation",
                value=f"```{english_text}```",
                inline=False,
            )

            # Add context or additional information if available
            if verse_data.get("context"):
                embed.add_field(
                    name="📝 Context",
                    value=verse_data["context"],
                    inline=False,
                )

            # Set bot profile picture as thumbnail
            try:
                if interaction.client.user and interaction.client.user.avatar:
                    embed.set_thumbnail(url=interaction.client.user.avatar.url)
            except (AttributeError, discord.HTTPException):
                # Continue without thumbnail if it fails
                pass

            # Set footer with admin profile picture
            try:
                admin_user = await interaction.client.fetch_user(DEVELOPER_ID)
                if admin_user and admin_user.avatar:
                    embed.set_footer(
                        text="Created by حَـــــنَـــــا",
                        icon_url=admin_user.avatar.url,
                    )
                else:
                    embed.set_footer(text="Created by حَـــــنَـــــا")
            except Exception as avatar_error:
                log_error_with_traceback(
                    "Failed to set footer with admin avatar", avatar_error
                )
                embed.set_footer(text="Created by حَـــــنَـــــا")

            # Send the verse to the channel
            try:
                message = await channel.send(embed=embed)

                # Record verse sent in statistics
                if daily_verses.daily_verse_manager:
                    daily_verses.daily_verse_manager.record_verse_sent(
                        verse_data.get("surah", 1)
                    )

                # Add only the dua emoji for user interaction
                await message.add_reaction("🤲")  # Dua emoji only

                # Monitor reactions for user interaction tracking and removal of unauthorized reactions
                def check_dua_reaction(reaction, user):
                    return (
                        reaction.message.id == message.id
                        and not user.bot
                        and str(reaction.emoji) == "🤲"
                    )

                def check_unauthorized_reaction(reaction, user):
                    return (
                        reaction.message.id == message.id
                        and not user.bot
                        and str(reaction.emoji) != "🤲"
                    )

                async def monitor_unauthorized_reactions():
                    """Monitor and remove unauthorized reactions"""
                    try:
                        while True:
                            reaction, user = await interaction.client.wait_for(
                                "reaction_add",
                                check=check_unauthorized_reaction,
                                timeout=3600,
                            )  # 1 hour timeout

                            # Log unauthorized reaction removal
                            log_user_interaction(
                                interaction_type="verse_reaction_removed",
                                user_name=user.display_name,
                                user_id=user.id,
                                action_description=f"Added unauthorized reaction '{reaction.emoji}' to daily verse, removed automatically",
                                details={
                                    "reaction_removed": str(reaction.emoji),
                                    "allowed_reaction": "🤲",
                                    "verse_id": verse_data.get("id", "Unknown"),
                                    "surah": verse_data.get("surah", "Unknown"),
                                    "verse_number": verse_data.get(
                                        "ayah", verse_data.get("verse", "Unknown")
                                    ),
                                    "message_id": message.id,
                                    "channel_id": channel.id,
                                },
                            )

                            # Remove the unauthorized reaction
                            try:
                                await reaction.remove(user)
                            except discord.Forbidden:
                                # Bot doesn't have permission to remove reactions
                                pass
                            except (discord.HTTPException, discord.NotFound):
                                # Ignore other reaction removal errors (message deleted, etc.)
                                pass

                    except TimeoutError:
                        # Timeout reached, stop monitoring
                        pass
                    except Exception as e:
                        log_error_with_traceback(
                            "Error monitoring unauthorized reactions", e
                        )

                async def monitor_dua_reactions():
                    """Monitor dua reactions specifically"""
                    try:
                        while True:
                            reaction, user = await interaction.client.wait_for(
                                "reaction_add",
                                check=check_dua_reaction,
                                timeout=3600,
                            )  # 1 hour timeout

                            # Log dua interaction
                            log_user_interaction(
                                interaction_type="dua_reaction",
                                user_name=user.display_name,
                                user_id=user.id,
                                action_description="Made dua (🤲) on daily verse",
                                details={
                                    "reaction": "🤲",
                                    "verse_id": verse_data.get("id", "Unknown"),
                                    "surah": verse_data.get("surah", "Unknown"),
                                    "verse_number": verse_data.get(
                                        "ayah", verse_data.get("verse", "Unknown")
                                    ),
                                    "message_id": message.id,
                                    "channel_id": channel.id,
                                    "spiritual_activity": "dua_made",
                                },
                            )

                            # Record dua reaction in statistics
                            if daily_verses.daily_verse_manager:
                                daily_verses.daily_verse_manager.record_dua_reaction(
                                    user.id,
                                    verse_data.get("surah", 1),
                                    verse_data.get("ayah", verse_data.get("verse", 1)),
                                )

                            # Log to Discord with user profile picture
                            discord_logger = get_discord_logger()
                            if discord_logger:
                                try:
                                    user_avatar_url = (
                                        user.avatar.url
                                        if user.avatar
                                        else user.default_avatar.url
                                    )
                                    await discord_logger.log_user_interaction(
                                        "dua_reaction",
                                        user.display_name,
                                        user.id,
                                        "made dua (🤲) on daily verse",
                                        {
                                            "Reaction": "🤲",
                                            "Verse ID": str(
                                                verse_data.get("id", "Unknown")
                                            ),
                                            "Surah": str(
                                                verse_data.get("surah", "Unknown")
                                            ),
                                            "Verse Number": str(
                                                verse_data.get(
                                                    "ayah",
                                                    verse_data.get("verse", "Unknown"),
                                                )
                                            ),
                                            "Message ID": str(message.id),
                                            "Channel ID": str(channel.id),
                                            "Spiritual Activity": "Dua Made",
                                        },
                                        user_avatar_url,
                                    )
                                except:
                                    pass

                    except TimeoutError:
                        # Timeout reached, stop monitoring
                        pass
                    except Exception as e:
                        log_error_with_traceback("Error monitoring dua reactions", e)

                # Start monitoring tasks
                asyncio.create_task(monitor_unauthorized_reactions())
                asyncio.create_task(monitor_dua_reactions())

                # Send confirmation to the user
                try:
                    # Create clickable link to the verse message
                    guild_id = (
                        interaction.guild.id if interaction.guild else channel.guild.id
                    )
                    verse_link = f"https://discord.com/channels/{guild_id}/{channel.id}/{message.id}"

                    success_embed = discord.Embed(
                        title="✅ Verse Sent Successfully",
                        description=f"Daily verse has been sent to {channel.mention}.\n\n**Verse Details:**\n• Surah: {verse_data.get('surah', 'Unknown')}\n• Verse: {verse_data.get('ayah', verse_data.get('verse', 'Unknown'))}\n• Timer: Reset to 3 hours\n\n📖 **[Click here to view the verse →]({verse_link})**",
                        color=0x00D4AA,
                    )
                    await interaction.followup.send(embed=success_embed, ephemeral=True)
                except Exception as e:
                    log_error_with_traceback(
                        "Failed to send confirmation message to user", e
                    )

                # Log successful verse delivery
                log_perfect_tree_section(
                    "Verse Command - Success",
                    [
                        (
                            "user",
                            f"{interaction.user.display_name} ({interaction.user.id})",
                        ),
                        ("channel", f"#{channel.name}"),
                        ("verse_id", verse_data.get("id", "Unknown")),
                        ("surah", verse_data.get("surah", "Unknown")),
                        (
                            "verse_number",
                            verse_data.get("ayah", verse_data.get("verse", "Unknown")),
                        ),
                        ("message_id", message.id),
                        ("reactions_added", "🤲"),
                        ("timer_reset", "✅ 3 hours"),
                        ("status", "✅ Verse delivered successfully"),
                    ],
                    "🏆",
                )

                # Send success notification to Discord logger
                discord_logger = get_discord_logger()
                if discord_logger:
                    try:
                        await discord_logger.log_user_activity(
                            f"Manual Verse Sent by {interaction.user.display_name}",
                            f"📖 **Daily verse delivered manually**\n\n"
                            f"**Verse Details:**\n"
                            f"• Surah: {verse_data.get('surah', 'Unknown')}\n"
                            f"• Verse: {verse_data.get('ayah', verse_data.get('verse', 'Unknown'))}\n"
                            f"• Channel: {channel.mention}\n"
                            f"• Reaction: 🤲 (dua emoji)\n\n"
                            f"Daily verse timer has been reset to 3 hours.",
                            {
                                "Admin": interaction.user.display_name,
                                "User ID": str(interaction.user.id),
                                "Verse ID": str(verse_data.get("id", "Unknown")),
                                "Message ID": str(message.id),
                            },
                        )
                    except:
                        pass

            except discord.Forbidden:
                log_error_with_traceback(
                    "Permission denied when sending verse to channel",
                    Exception("Bot lacks permission to send messages in the channel"),
                )
                error_embed = discord.Embed(
                    title="❌ Permission Error",
                    description="Bot doesn't have permission to send messages in the daily verse channel.",
                    color=0xFF6B6B,
                )
                await interaction.followup.send(embed=error_embed, ephemeral=True)

            except Exception as e:
                log_error_with_traceback("Failed to create or send verse embed", e)

                log_perfect_tree_section(
                    "Verse Command - Delivery Failed",
                    [
                        (
                            "user",
                            f"{interaction.user.display_name} ({interaction.user.id})",
                        ),
                        ("error", str(e)),
                        ("status", "❌ Failed to deliver verse"),
                    ],
                    "💥",
                )

                error_embed = discord.Embed(
                    title="❌ Delivery Error",
                    description="Failed to send the verse. Please try again or contact the administrator.",
                    color=0xFF6B6B,
                )
                await interaction.followup.send(embed=error_embed, ephemeral=True)

        except discord.InteractionResponded:
            # Interaction was already responded to, which is fine
            log_error_with_traceback(
                "Interaction already responded to in verse command",
                Exception("Double response attempt"),
            )

        except Exception as e:
            log_error_with_traceback("Error in verse command", e)

            log_perfect_tree_section(
                "Verse Command - Unexpected Error",
                [
                    (
                        "user",
                        f"{interaction.user.display_name} ({interaction.user.id})",
                    ),
                    ("error_type", type(e).__name__),
                    ("error_message", str(e)),
                    ("status", "❌ Command execution failed"),
                ],
                "💥",
            )

            try:
                error_embed = discord.Embed(
                    title="❌ Unexpected Error",
                    description="An unexpected error occurred while processing the verse command. Please try again later.",
                    color=0xFF6B6B,
                )
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        embed=error_embed, ephemeral=True
                    )
                else:
                    await interaction.followup.send(embed=error_embed, ephemeral=True)
            except Exception as response_error:
                log_error_with_traceback(
                    "Failed to send unexpected error message", response_error
                )


# =============================================================================
# Cog Setup
# =============================================================================


async def setup(bot, container=None):
    """Set up the Verse cog"""
    try:
        log_perfect_tree_section(
            "Verse Cog Setup - Starting",
            [
                ("cog_name", "VerseCog"),
                ("command_name", "/verse"),
                ("status", "🔄 Initializing verse cog setup"),
            ],
            "🚀",
        )

        await bot.add_cog(VerseCog(bot, container))

        log_perfect_tree_section(
            "Verse Cog Setup - Complete",
            [
                ("status", "✅ Verse cog loaded successfully"),
                ("cog_name", "VerseCog"),
                ("command_name", "/verse"),
                ("description", "Send daily verse manually and reset timer"),
                ("permission_level", "🔒 Admin only"),
                ("error_handling", "✅ Comprehensive traceback and logging"),
                ("tree_logging", "✅ Perfect tree logging implemented"),
            ],
            "📖",
        )

    except Exception as setup_error:
        log_error_with_traceback("Failed to set up verse cog", setup_error)

        log_perfect_tree_section(
            "Verse Cog Setup - Failed",
            [
                ("error_type", type(setup_error).__name__),
                ("status", "❌ Failed to load verse cog"),
                ("impact", "🚨 /verse command will not be available"),
            ],
            "💥",
        )

        # Re-raise the exception to ensure the bot startup process is aware of the failure
        raise


# =============================================================================
# Export Functions (for backward compatibility)
# =============================================================================

__all__ = [
    "VerseCog",
    "get_daily_verses_manager",
    "setup",
]
