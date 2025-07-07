# =============================================================================
# QuranBot - Verse Command
# =============================================================================
# Manual verse command that sends a daily verse and resets the timer
# Admin-only command for controlling daily verse system
# =============================================================================

import os
from datetime import datetime, timezone

import discord

from src.utils.daily_verses import daily_verses_manager
from src.utils.tree_log import log_error_with_traceback, log_perfect_tree_section

# =============================================================================
# Slash Command Implementation
# =============================================================================


@discord.app_commands.command(
    name="verse",
    description="Send a daily verse manually and reset the 3-hour timer (Admin only)",
)
async def verse_slash_command(interaction: discord.Interaction):
    """Send a daily verse manually and reset the 3-hour timer (Admin only)"""
    try:
        # Get DEVELOPER_ID from environment
        DEVELOPER_ID = int(os.getenv("DEVELOPER_ID") or "0")

        # Check if user is the admin/developer
        if interaction.user.id != DEVELOPER_ID:
            embed = discord.Embed(
                title="🔒 Admin Only Command",
                description="This command is restricted to the bot administrator only.",
                color=0xFF6B6B,
            )
            embed.add_field(
                name="📋 Available Commands",
                value="Use `/credits` or `/leaderboard` for general bot information.",
                inline=False,
            )

            # Set footer with admin profile picture
            try:
                admin_user = interaction.client.get_user(DEVELOPER_ID)
                if admin_user and admin_user.avatar:
                    embed.set_footer(
                        text="Created by حَـــــنَـــــا", icon_url=admin_user.avatar.url
                    )
                else:
                    embed.set_footer(text="Created by حَـــــنَـــــا")
            except Exception:
                embed.set_footer(text="Created by حَـــــنَـــــا")

            await interaction.response.send_message(embed=embed, ephemeral=True)

            # Log unauthorized access attempt
            log_perfect_tree_section(
                "Daily Verses - Unauthorized Access Attempt",
                [
                    (
                        "attempted_by",
                        f"{interaction.user.display_name} ({interaction.user.id})",
                    ),
                    ("command", "/verse"),
                    ("status", "🔒 Access denied - Admin only"),
                    ("admin_id", str(DEVELOPER_ID)),
                ],
                "🔒",
            )
            return

        # Check if daily verses system is configured
        if (
            not daily_verses_manager.bot
            or not daily_verses_manager.daily_verse_channel_id
        ):
            # Debug logging to see the actual values
            print(f"DEBUG: daily_verses_manager.bot = {daily_verses_manager.bot}")
            print(
                f"DEBUG: daily_verses_manager.daily_verse_channel_id = {daily_verses_manager.daily_verse_channel_id}"
            )
            print(
                f"DEBUG: daily_verses_manager.developer_user_id = {daily_verses_manager.developer_user_id}"
            )

            embed = discord.Embed(
                title="❌ Daily Verses Not Configured",
                description="The daily verses system is not properly configured. Please check the bot configuration.",
                color=0xFF6B6B,
            )

            # Set footer with admin profile picture
            try:
                admin_user = interaction.client.get_user(DEVELOPER_ID)
                if admin_user and admin_user.avatar:
                    embed.set_footer(
                        text="Created by حَـــــنَـــــا", icon_url=admin_user.avatar.url
                    )
                else:
                    embed.set_footer(text="Created by حَـــــنَـــــا")
            except Exception:
                embed.set_footer(text="Created by حَـــــنَـــــا")

            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Get the daily verse channel
        channel = interaction.client.get_channel(
            daily_verses_manager.daily_verse_channel_id
        )
        if not channel:
            embed = discord.Embed(
                title="❌ Channel Not Found",
                description="The daily verse channel could not be found.",
                color=0xFF6B6B,
            )

            # Set footer with admin profile picture
            try:
                admin_user = interaction.client.get_user(DEVELOPER_ID)
                if admin_user and admin_user.avatar:
                    embed.set_footer(
                        text="Created by حَـــــنَـــــا", icon_url=admin_user.avatar.url
                    )
                else:
                    embed.set_footer(text="Created by حَـــــنَـــــا")
            except Exception:
                embed.set_footer(text="Created by حَـــــنَـــــا")

            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Get next verse
        verse = daily_verses_manager.get_next_verse()
        if not verse:
            embed = discord.Embed(
                title="❌ No Verses Available",
                description="No verses are available in the queue or pool.",
                color=0xFF6B6B,
            )

            # Set footer with admin profile picture
            try:
                admin_user = interaction.client.get_user(DEVELOPER_ID)
                if admin_user and admin_user.avatar:
                    embed.set_footer(
                        text="Created by حَـــــنَـــــا", icon_url=admin_user.avatar.url
                    )
                else:
                    embed.set_footer(text="Created by حَـــــنَـــــا")
            except Exception:
                embed.set_footer(text="Created by حَـــــنَـــــا")

            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Send the verse to the daily verse channel
        verse_embed = daily_verses_manager.create_verse_embed(verse)
        message = await channel.send(embed=verse_embed)

        # Add dua reaction automatically
        try:
            await message.add_reaction("🤲")
        except Exception as reaction_error:
            log_error_with_traceback(
                "Error adding dua reaction to manual verse", reaction_error
            )

        # Update last sent verse and reset timer
        daily_verses_manager.last_sent_verse = verse
        daily_verses_manager.reset_timer()

        # Calculate next automatic verse time (3 hours from now)
        next_auto_time = datetime.now(timezone.utc).replace(microsecond=0)
        next_auto_time = next_auto_time.replace(hour=(next_auto_time.hour + 3) % 24)
        if next_auto_time.hour < 3:  # Handle day rollover
            next_auto_time = next_auto_time.replace(day=next_auto_time.day + 1)

        # Send confirmation to the user
        confirmation_embed = discord.Embed(
            title="✅ Verse Sent Successfully",
            description=f"**{verse['surah_name']} ({verse['surah']}:{verse['ayah']})** has been sent to {channel.mention}",
            color=0x00D4AA,
        )
        confirmation_embed.add_field(
            name="🔄 Timer Reset",
            value=f"Next automatic verse will be sent in **3 hours**\n*Around {next_auto_time.strftime('%I:%M %p')} UTC*",
            inline=False,
        )

        # Show queue/pool status with coordination info
        if daily_verses_manager.verses_queue:
            queue_info = f"**{len(daily_verses_manager.verses_queue)}** verses remaining in queue"
            coordination_info = "✅ Verse removed from queue to prevent duplicates"
        elif daily_verses_manager.verses_pool:
            queue_info = f"Queue empty, **{len(daily_verses_manager.verses_pool)}** verses remaining in pool"
            coordination_info = "✅ Verse removed from pool to prevent duplicates"
        else:
            queue_info = "Both queue and pool are now empty"
            coordination_info = "✅ All verses have been sent"

        confirmation_embed.add_field(
            name="📊 Queue Status", value=queue_info, inline=True
        )
        confirmation_embed.add_field(
            name="🤝 Coordination", value=coordination_info, inline=True
        )

        # Set footer with admin profile picture
        try:
            admin_user = interaction.client.get_user(DEVELOPER_ID)
            if admin_user and admin_user.avatar:
                confirmation_embed.set_footer(
                    text="Created by حَـــــنَـــــا", icon_url=admin_user.avatar.url
                )
            else:
                confirmation_embed.set_footer(text="Created by حَـــــنَـــــا")
        except Exception:
            confirmation_embed.set_footer(text="Created by حَـــــنَـــــا")

        await interaction.response.send_message(
            embed=confirmation_embed, ephemeral=True
        )

        # Log the manual verse sending
        log_perfect_tree_section(
            "Daily Verses - Manual Verse Sent",
            [
                (
                    "triggered_by",
                    f"{interaction.user.display_name} ({interaction.user.id})",
                ),
                ("admin_verified", "✅ Admin permission confirmed"),
                ("channel", channel.name),
                (
                    "surah",
                    f"{verse['surah_name']} ({verse['surah']}:{verse['ayah']})",
                ),
                ("message_id", str(message.id)),
                ("timer_reset", "✅ 3-hour timer reset"),
                (
                    "next_auto_verse",
                    f"In 3 hours ({next_auto_time.strftime('%I:%M %p')} UTC)",
                ),
                ("queue_remaining", len(daily_verses_manager.verses_queue)),
                ("pool_remaining", len(daily_verses_manager.verses_pool)),
                ("coordination", "✅ Verse removed to prevent automatic duplicate"),
            ],
            "📖",
        )

    except Exception as e:
        log_error_with_traceback("Error in manual verse command", e)

        error_embed = discord.Embed(
            title="❌ Error Sending Verse",
            description="An error occurred while trying to send the verse. Please check the logs.",
            color=0xFF6B6B,
        )

        # Set footer with admin profile picture
        try:
            DEVELOPER_ID = int(os.getenv("DEVELOPER_ID") or "0")
            admin_user = interaction.client.get_user(DEVELOPER_ID)
            if admin_user and admin_user.avatar:
                error_embed.set_footer(
                    text="Created by حَـــــنَـــــا", icon_url=admin_user.avatar.url
                )
            else:
                error_embed.set_footer(text="Created by حَـــــنَـــــا")
        except Exception:
            error_embed.set_footer(text="Created by حَـــــنَـــــا")

        # Handle both responded and unresponded interactions
        if interaction.response.is_done():
            await interaction.followup.send(embed=error_embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=error_embed, ephemeral=True)


async def setup_verse_command(bot):
    """Set up the verse command"""
    # Add the slash command to the bot's command tree
    bot.tree.add_command(verse_slash_command)

    log_perfect_tree_section(
        "Verse Command Setup",
        [
            ("status", "✅ Verse command loaded successfully"),
            ("command_name", "/verse"),
            ("command_type", "Slash command only"),
            ("description", "Send daily verse manually and reset timer"),
            ("permission_level", "🔒 Admin only"),
        ],
        "📖",
    )
