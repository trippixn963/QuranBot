# =============================================================================
# QuranBot - Verse Command
# =============================================================================
# Manual verse command that sends a daily verse and resets the timer
# Admin-only command for controlling daily verse system
# =============================================================================

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import discord
from discord.ext import commands

from src.utils.tree_log import log_error_with_traceback, log_perfect_tree_section


# Get the daily verses manager through a function instead of global import
def get_daily_verses_manager():
    """Get the daily verses manager instance"""
    try:
        from src.utils.daily_verses import daily_verses_manager

        return daily_verses_manager
    except Exception as e:
        log_error_with_traceback("Failed to import daily_verses_manager", e)
        return None


@discord.app_commands.command(
    name="verse",
    description="Send a daily verse manually and reset the 3-hour timer (Admin only)",
)
async def verse_slash_command(interaction: discord.Interaction):
    """Send a daily verse manually and reset the 3-hour timer"""

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
        if (
            not daily_verses_manager.bot
            or not daily_verses_manager.daily_verse_channel_id
        ):
            log_perfect_tree_section(
                "Verse Command - System Not Configured",
                [
                    (
                        "bot_instance",
                        "❌ Not set" if not daily_verses_manager.bot else "✅ Set",
                    ),
                    (
                        "channel_id",
                        (
                            "❌ Not set"
                            if not daily_verses_manager.daily_verse_channel_id
                            else f"✅ {daily_verses_manager.daily_verse_channel_id}"
                        ),
                    ),
                    ("status", "🚨 Daily verses system not properly configured"),
                ],
                "⚠️",
            )

            embed = discord.Embed(
                title="❌ Daily Verses Not Configured",
                description="The daily verses system is not properly configured. Please check the bot configuration.",
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

        # Get the daily verse channel with error handling
        try:
            channel = interaction.client.get_channel(
                daily_verses_manager.daily_verse_channel_id
            )
            if not channel:
                # Try fetching the channel if get_channel fails
                channel = await interaction.client.fetch_channel(
                    daily_verses_manager.daily_verse_channel_id
                )
        except Exception as channel_error:
            log_error_with_traceback(
                f"Failed to get/fetch channel {daily_verses_manager.daily_verse_channel_id}",
                channel_error,
            )
            channel = None

        if not channel:
            log_perfect_tree_section(
                "Verse Command - Channel Not Found",
                [
                    ("channel_id", str(daily_verses_manager.daily_verse_channel_id)),
                    ("status", "❌ Channel not accessible"),
                    (
                        "possible_causes",
                        "Channel deleted, bot lacks permissions, or invalid ID",
                    ),
                ],
                "🔍",
            )

            embed = discord.Embed(
                title="❌ Channel Not Found",
                description=f"The daily verse channel (ID: {daily_verses_manager.daily_verse_channel_id}) could not be found or accessed.",
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
                    "Failed to fetch admin avatar for channel error message",
                    avatar_error,
                )
                embed.set_footer(text="Created by حَـــــنَـــــا")

            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Log successful channel access
        log_perfect_tree_section(
            "Verse Command - Channel Access Success",
            [
                ("channel_name", f"#{channel.name}"),
                ("channel_id", str(channel.id)),
                ("guild", f"{channel.guild.name}" if channel.guild else "DM"),
                ("status", "✅ Channel accessible"),
            ],
            "📺",
        )

        # Get next verse with error handling
        try:
            verse = daily_verses_manager.get_next_verse()
        except Exception as verse_error:
            log_error_with_traceback(
                "Failed to get next verse from daily verses manager", verse_error
            )
            verse = None

        if not verse:
            log_perfect_tree_section(
                "Verse Command - No Verses Available",
                [
                    (
                        "queue_size",
                        (
                            len(daily_verses_manager.verses_queue)
                            if hasattr(daily_verses_manager, "verses_queue")
                            else "Unknown"
                        ),
                    ),
                    (
                        "pool_size",
                        (
                            len(daily_verses_manager.verses_pool)
                            if hasattr(daily_verses_manager, "verses_pool")
                            else "Unknown"
                        ),
                    ),
                    ("status", "❌ No verses available"),
                ],
                "📚",
            )

            embed = discord.Embed(
                title="❌ No Verses Available",
                description="No verses are available in the queue or pool. The system may need to be reloaded.",
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
                    "Failed to fetch admin avatar for no verses message", avatar_error
                )
                embed.set_footer(text="Created by حَـــــنَـــــا")

            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Log successful verse retrieval
        log_perfect_tree_section(
            "Verse Command - Verse Retrieved",
            [
                ("surah", f"{verse['surah_name']} ({verse['surah']}:{verse['ayah']})"),
                ("arabic_name", verse.get("arabic_name", "N/A")),
                (
                    "queue_remaining",
                    (
                        len(daily_verses_manager.verses_queue)
                        if hasattr(daily_verses_manager, "verses_queue")
                        else "Unknown"
                    ),
                ),
                (
                    "pool_remaining",
                    (
                        len(daily_verses_manager.verses_pool)
                        if hasattr(daily_verses_manager, "verses_pool")
                        else "Unknown"
                    ),
                ),
                ("status", "✅ Verse selected for sending"),
            ],
            "📖",
        )

        # Create verse embed with error handling
        try:
            verse_embed = await daily_verses_manager.create_verse_embed(verse)
        except Exception as embed_error:
            log_error_with_traceback("Failed to create verse embed", embed_error)

            # Create a fallback embed
            verse_embed = discord.Embed(
                title=f"📖 Daily Verse - {verse['surah_name']}",
                description=f"Ayah {verse['ayah']}",
                color=0x00D4AA,
            )
            verse_embed.add_field(
                name="🌙 Arabic",
                value=f"```\n{verse.get('arabic', 'Arabic text unavailable')}\n```",
                inline=False,
            )
            verse_embed.add_field(
                name="📝 English",
                value=f"```\n{verse.get('english', 'English translation unavailable')}\n```",
                inline=False,
            )

        # Send the verse to the daily verse channel with error handling
        try:
            message = await channel.send(embed=verse_embed)

            log_perfect_tree_section(
                "Verse Command - Message Sent",
                [
                    ("message_id", str(message.id)),
                    ("channel", f"#{channel.name}"),
                    (
                        "surah",
                        f"{verse['surah_name']} ({verse['surah']}:{verse['ayah']})",
                    ),
                    ("status", "✅ Verse message sent successfully"),
                ],
                "📤",
            )
        except Exception as send_error:
            log_error_with_traceback(
                "Failed to send verse message to channel", send_error
            )

            error_embed = discord.Embed(
                title="❌ Failed to Send Verse",
                description=f"Could not send the verse to {channel.mention}. Please check bot permissions.",
                color=0xFF6B6B,
            )

            # Set footer with admin profile picture with error handling
            try:
                admin_user = await interaction.client.fetch_user(DEVELOPER_ID)
                if admin_user and admin_user.avatar:
                    error_embed.set_footer(
                        text="Created by حَـــــنَـــــا", icon_url=admin_user.avatar.url
                    )
                else:
                    error_embed.set_footer(text="Created by حَـــــنَـــــا")
            except Exception as avatar_error:
                log_error_with_traceback(
                    "Failed to fetch admin avatar for send error message", avatar_error
                )
                error_embed.set_footer(text="Created by حَـــــنَـــــا")

            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return

        # Add dua reaction automatically with error handling
        try:
            await message.add_reaction("🤲")

            log_perfect_tree_section(
                "Verse Command - Reaction Added",
                [
                    ("reaction", "🤲 (Dua)"),
                    ("message_id", str(message.id)),
                    ("status", "✅ Dua reaction added successfully"),
                ],
                "🤲",
            )
        except Exception as reaction_error:
            log_error_with_traceback(
                "Failed to add dua reaction to manual verse", reaction_error
            )

            log_perfect_tree_section(
                "Verse Command - Reaction Failed",
                [
                    ("reaction", "🤲 (Dua)"),
                    ("message_id", str(message.id)),
                    ("status", "❌ Failed to add reaction (non-critical)"),
                    ("impact", "Message sent successfully, reaction failed"),
                ],
                "⚠️",
            )

        # Update last sent verse and reset timer with error handling
        try:
            daily_verses_manager.last_sent_verse = verse
            daily_verses_manager.reset_timer()

            log_perfect_tree_section(
                "Verse Command - Timer Reset",
                [
                    (
                        "last_sent_verse",
                        f"{verse['surah_name']} ({verse['surah']}:{verse['ayah']})",
                    ),
                    ("timer_status", "✅ 3-hour timer reset"),
                    ("status", "✅ System state updated"),
                ],
                "⏰",
            )
        except Exception as timer_error:
            log_error_with_traceback(
                "Failed to update last sent verse or reset timer", timer_error
            )

        # Calculate next automatic verse time (3 hours from now) with error handling
        try:
            # Get current time in EST
            est_tz = timezone(timedelta(hours=-5))  # EST is UTC-5
            current_time = datetime.now(est_tz)
            next_auto_time = current_time + timedelta(hours=3)
            next_auto_time = next_auto_time.replace(microsecond=0)

            log_perfect_tree_section(
                "Verse Command - Next Timer Calculated",
                [
                    ("current_time", current_time.strftime("%Y-%m-%d %I:%M:%S %p EST")),
                    (
                        "next_auto_time",
                        next_auto_time.strftime("%Y-%m-%d %I:%M:%S %p EST"),
                    ),
                    ("hours_until_next", "3"),
                    ("status", "✅ Next automatic verse time calculated"),
                ],
                "🕐",
            )
        except Exception as time_error:
            log_error_with_traceback(
                "Failed to calculate next automatic verse time", time_error
            )
            next_auto_time = None

        # Send confirmation to the user with comprehensive error handling
        try:
            confirmation_embed = discord.Embed(
                title="✅ Verse Sent Successfully",
                description=f"**{verse['surah_name']} ({verse['surah']}:{verse['ayah']})** has been sent to {channel.mention}",
                color=0x00D4AA,
            )

            if next_auto_time:
                confirmation_embed.add_field(
                    name="🔄 Timer Reset",
                    value=f"Next automatic verse will be sent in **3 hours**\n*Around {next_auto_time.strftime('%I:%M %p')} EST*",
                    inline=False,
                )
            else:
                confirmation_embed.add_field(
                    name="🔄 Timer Reset",
                    value="Next automatic verse will be sent in **3 hours**\n*Time calculation failed - check logs*",
                    inline=False,
                )

            # Show message ID and coordination info
            confirmation_embed.add_field(
                name="📨 Message ID",
                value=f"**[{message.id}](https://discord.com/channels/{channel.guild.id}/{channel.id}/{message.id})**\nVerse message in {channel.mention}",
                inline=True,
            )
            confirmation_embed.add_field(
                name="🤝 Coordination",
                value="✅ Verse removed from queue to prevent duplicates",
                inline=True,
            )

            # Set footer with admin profile picture with error handling
            try:
                admin_user = await interaction.client.fetch_user(DEVELOPER_ID)
                if admin_user and admin_user.avatar:
                    confirmation_embed.set_footer(
                        text="Created by حَـــــنَـــــا", icon_url=admin_user.avatar.url
                    )
                else:
                    confirmation_embed.set_footer(text="Created by حَـــــنَـــــا")
            except Exception as avatar_error:
                log_error_with_traceback(
                    "Failed to fetch admin avatar for confirmation message",
                    avatar_error,
                )
                confirmation_embed.set_footer(text="Created by حَـــــنَـــــا")

            await interaction.response.send_message(
                embed=confirmation_embed, ephemeral=True
            )

            log_perfect_tree_section(
                "Verse Command - Confirmation Sent",
                [
                    (
                        "user",
                        f"{interaction.user.display_name} ({interaction.user.id})",
                    ),
                    ("message_type", "Ephemeral confirmation"),
                    ("status", "✅ User confirmation sent successfully"),
                ],
                "📋",
            )
        except Exception as confirmation_error:
            log_error_with_traceback(
                "Failed to send confirmation message to user", confirmation_error
            )

        # Log the successful manual verse sending with comprehensive details
        log_perfect_tree_section(
            "Verse Command - Execution Complete",
            [
                (
                    "triggered_by",
                    f"{interaction.user.display_name} ({interaction.user.id})",
                ),
                ("admin_verified", "✅ Admin permission confirmed"),
                ("channel", f"#{channel.name} ({channel.id})"),
                ("surah", f"{verse['surah_name']} ({verse['surah']}:{verse['ayah']})"),
                ("message_id", str(message.id)),
                ("timer_reset", "✅ 3-hour timer reset"),
                (
                    "next_auto_verse",
                    (
                        f"In 3 hours ({next_auto_time.strftime('%I:%M %p')} EST)"
                        if next_auto_time
                        else "Time calculation failed"
                    ),
                ),
                (
                    "queue_remaining",
                    (
                        len(daily_verses_manager.verses_queue)
                        if hasattr(daily_verses_manager, "verses_queue")
                        else "Unknown"
                    ),
                ),
                (
                    "pool_remaining",
                    (
                        len(daily_verses_manager.verses_pool)
                        if hasattr(daily_verses_manager, "verses_pool")
                        else "Unknown"
                    ),
                ),
                ("coordination", "✅ Verse removed to prevent automatic duplicate"),
                ("reaction_added", "✅ Dua reaction added"),
                ("status", "🎉 Command executed successfully"),
            ],
            "🏆",
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
