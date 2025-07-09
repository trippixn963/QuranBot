# =============================================================================
# QuranBot - Leaderboard Command
# =============================================================================
# Displays quiz points leaderboard
# =============================================================================

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import discord

from src.utils.listening_stats import format_listening_time, get_user_listening_stats
from src.utils.tree_log import log_error_with_traceback, log_perfect_tree_section

# Path to quiz stats file
QUIZ_STATS_FILE = Path("data/quiz_stats.json")

# =============================================================================
# Slash Command Implementation
# =============================================================================


@discord.app_commands.command(
    name="leaderboard",
    description="Display the quiz points leaderboard",
)
async def leaderboard_command(interaction: discord.Interaction):
    """Display the quiz points leaderboard"""
    try:
        # Load fresh quiz stats from file each time
        try:
            if QUIZ_STATS_FILE.exists():
                with open(QUIZ_STATS_FILE, "r", encoding="utf-8") as f:
                    quiz_stats = json.load(f)
            else:
                quiz_stats = {"user_scores": {}}
        except Exception as e:
            log_error_with_traceback("Error loading quiz stats for leaderboard", e)
            quiz_stats = {"user_scores": {}}

        user_scores = quiz_stats.get("user_scores", {})

        # Sort users by points (primary) and correct answers (secondary)
        sorted_users = sorted(
            user_scores.items(),
            key=lambda x: (x[1]["points"], x[1].get("correct", 0)),
            reverse=True,
        )[
            :10
        ]  # Top 10 users

        # Create embed
        embed = discord.Embed(
            title="🏆 QuranBot Leaderboard",
            description="*Top users ranked by quiz points*",
            color=0x00D4AA,
        )

        # Medal emojis for top 3
        medal_emojis = {1: "🥇", 2: "🥈", 3: "🥉"}

        leaderboard_text = ""
        for position, (user_id, stats) in enumerate(sorted_users, 1):
            # Get position display
            position_display = medal_emojis.get(position, f"{position}.")

            # Format quiz stats
            points = stats["points"]
            streak = stats.get(
                "current_streak", 0
            )  # Show current streak, not best streak

            # Get listening time stats
            listening_stats = get_user_listening_stats(int(user_id))
            if listening_stats:
                listening_time = format_listening_time(listening_stats.total_time)
            else:
                listening_time = "0s"

            # Create leaderboard entry
            leaderboard_text += (
                f"{position_display} <@{user_id}>\n"
                f"Points: **{points}** • Streak: **{streak}** 🔥\n"
                f"Listening Time: **{listening_time}**\n\n"
            )

        if leaderboard_text:
            embed.description = (
                f"*Top users ranked by quiz points*\n\n{leaderboard_text}"
            )
        else:
            embed.description = "*No quiz data available yet. Answer some questions to appear on the leaderboard!*"

        # Set bot profile picture as thumbnail
        try:
            if interaction.client.user and interaction.client.user.avatar:
                embed.set_thumbnail(url=interaction.client.user.avatar.url)
        except Exception:
            pass

        # Set footer with admin profile picture
        try:
            developer_id = int(os.getenv("DEVELOPER_ID", 0))
            if developer_id:
                admin_user = await interaction.client.fetch_user(developer_id)
                if admin_user and admin_user.avatar:
                    embed.set_footer(
                        text="created by حَـــــنَـــــا",
                        icon_url=admin_user.avatar.url,
                    )
                else:
                    embed.set_footer(text="created by حَـــــنَـــــا")
            else:
                embed.set_footer(text="created by حَـــــنَـــــا")
        except Exception:
            embed.set_footer(text="created by حَـــــنَـــــا")

        await interaction.response.send_message(embed=embed)

        # Log command usage
        log_perfect_tree_section(
            "Leaderboard Command - Success",
            [
                ("user", interaction.user.display_name),
                ("user_id", interaction.user.id),
                ("channel", interaction.channel.name if interaction.channel else "DM"),
                ("users_shown", len(sorted_users)),
            ],
            "🏆",
        )

    except Exception as e:
        log_error_with_traceback("Error in leaderboard command", e)
        try:
            await interaction.response.send_message(
                "❌ Error generating leaderboard. Please try again.", ephemeral=True
            )
        except:
            await interaction.followup.send(
                "❌ Error generating leaderboard. Please try again.", ephemeral=True
            )


async def setup_leaderboard_command(bot):
    """Set up the leaderboard command"""
    # Add the slash command to the bot's command tree
    bot.tree.add_command(leaderboard_command)

    log_perfect_tree_section(
        "Leaderboard Command Setup",
        [
            ("status", "✅ Leaderboard command loaded successfully"),
            ("command_name", "/leaderboard"),
            ("command_type", "Slash command only"),
            ("description", "Display quiz points leaderboard"),
            ("permission_level", "🌐 Public command"),
        ],
        "🏆",
    )
