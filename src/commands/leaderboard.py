# =============================================================================
# QuranBot - Leaderboard Command
# =============================================================================
# Displays listening time leaderboard for Quran voice channel users
# =============================================================================

import discord
from discord.ext import commands

# Import listening stats functions
from src.utils.listening_stats import format_listening_time, get_leaderboard_data

# Import tree logging functions
from src.utils.tree_log import (
    log_error_with_traceback,
    log_perfect_tree_section,
    log_user_interaction,
)

# Import version information
from src.version import BOT_VERSION

# =============================================================================
# Medal Emojis for Top 3
# =============================================================================

MEDAL_EMOJIS = {
    1: "🥇",  # Gold medal
    2: "🥈",  # Silver medal
    3: "🥉",  # Bronze medal
}

# =============================================================================
# Leaderboard Command
# =============================================================================


async def leaderboard_command(interaction: discord.Interaction):
    """
    Display the listening time leaderboard for Quran voice channel users.

    Shows the top 10 users by total listening time with:
    - Medal emojis for top 3 positions
    - User mentions and listening time in black boxes
    - Bot profile picture as thumbnail
    - Total server statistics
    """
    try:
        # Log user interaction
        log_user_interaction(
            interaction_type="slash_command",
            user_name=interaction.user.display_name,
            user_id=interaction.user.id,
            action_description="Used /leaderboard command",
            details={
                "command": "leaderboard",
                "guild_id": interaction.guild_id if interaction.guild else None,
                "channel_id": interaction.channel_id,
            },
        )

        # Get leaderboard data
        leaderboard_data = get_leaderboard_data()
        top_users = leaderboard_data["top_users"]

        log_perfect_tree_section(
            "Leaderboard Data Retrieved",
            [
                ("top_users_count", f"📊 {len(top_users)} users in leaderboard"),
                (
                    "total_listening_time",
                    f"⏱️ Total server listening time: {format_listening_time(leaderboard_data['total_listening_time'])}",
                ),
                (
                    "active_users",
                    f"🎧 Currently active: {leaderboard_data['active_users']} users",
                ),
                (
                    "total_users",
                    f"👥 Total users tracked: {leaderboard_data['total_users']}",
                ),
            ],
            "🏆",
        )

        # Create embed
        embed = discord.Embed(
            title="🏆 Quran Listening Leaderboard",
            description="*Top listeners in the Quran voice channel*",
            color=0x00D4AA,
            timestamp=interaction.created_at,
        )

        # Add leaderboard entries
        if top_users:
            leaderboard_text = ""

            for position, (user_id, total_time, sessions) in enumerate(top_users, 1):
                # Get medal emoji or position number
                position_display = MEDAL_EMOJIS.get(position, f"{position}.")

                # Format time
                time_formatted = format_listening_time(total_time)

                # Create leaderboard entry
                leaderboard_text += (
                    f"{position_display} <@{user_id}> - `{time_formatted}`\n"
                )

                # Add space after each entry except the last one
                if position < len(top_users):
                    leaderboard_text += "\n"

            # Add leaderboard directly to embed description or as a single field
            if leaderboard_text.strip():
                embed.description = (
                    f"*Top listeners in the Quran voice channel*\n\n{leaderboard_text}"
                )
            else:
                embed.description = "*No listening data available yet.*\n*Start listening to Quran recitations to appear on the leaderboard!*"
        else:
            embed.description = "*No listening data available yet.*\n*Start listening to Quran recitations to appear on the leaderboard!*"

        # Set bot avatar as thumbnail
        if interaction.client.user.avatar:
            embed.set_thumbnail(url=interaction.client.user.avatar.url)

        # Set footer
        embed.set_footer(
            text=f"QuranBot v{BOT_VERSION} • Requested by {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url,
        )

        # Send the embed
        await interaction.response.send_message(embed=embed, ephemeral=False)

        log_perfect_tree_section(
            "Leaderboard Command - Success",
            [
                (
                    "command_completed",
                    f"✅ Leaderboard displayed for {interaction.user.display_name}",
                ),
                ("users_shown", f"📊 {len(top_users)} users displayed"),
            ],
            "✅",
        )

    except Exception as e:
        log_error_with_traceback(
            "Leaderboard command failed",
            e,
            {
                "user_id": interaction.user.id,
                "guild_id": interaction.guild_id if interaction.guild else None,
                "channel_id": interaction.channel_id,
            },
        )

        # Send error message
        await interaction.response.send_message(
            "❌ An error occurred while displaying the leaderboard. Please try again.",
            ephemeral=True,
        )


# =============================================================================
# Setup Function
# =============================================================================


async def setup_leaderboard_command(bot):
    """
    Set up the leaderboard slash command.

    Args:
        bot: The Discord bot instance
    """
    try:
        log_perfect_tree_section(
            "Leaderboard Command Setup - Starting",
            [
                ("setup_start", "🏆 Setting up leaderboard command"),
            ],
            "🔧",
        )

        @bot.tree.command(
            name="leaderboard",
            description="Display the top 10 Quran listeners by listening time",
        )
        async def leaderboard(interaction: discord.Interaction):
            """Display the listening time leaderboard for Quran voice channel users"""
            await leaderboard_command(interaction)

        log_perfect_tree_section(
            "Leaderboard Command Setup - Complete",
            [
                (
                    "command_registered",
                    "✅ /leaderboard command registered with bot tree",
                ),
                ("command_name", "leaderboard"),
                (
                    "command_description",
                    "Display the top 10 Quran listeners by listening time",
                ),
                (
                    "setup_completed",
                    "✅ Leaderboard command setup completed successfully",
                ),
            ],
            "✅",
        )

    except Exception as e:
        log_error_with_traceback("Failed to setup leaderboard command", e)


# =============================================================================
# Export Functions
# =============================================================================

__all__ = [
    "leaderboard_command",
    "setup_leaderboard_command",
]
