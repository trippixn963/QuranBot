# =============================================================================
# QuranBot - Leaderboard Command
# =============================================================================
# Displays quiz points leaderboard with pagination
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
# Pagination View Class
# =============================================================================


class LeaderboardView(discord.ui.View):
    """View for paginated leaderboard with navigation buttons"""

    def __init__(self, sorted_users, interaction_user):
        super().__init__(timeout=300)  # 5 minute timeout
        self.sorted_users = sorted_users
        self.interaction_user = interaction_user
        self.current_page = 0
        self.max_pages = (len(sorted_users) - 1) // 5 + 1  # 5 users per page

        # Update button states
        self.update_buttons()

    def update_buttons(self):
        """Update button states based on current page"""
        # Left arrow button
        self.children[0].disabled = self.current_page == 0

        # Right arrow button
        self.children[1].disabled = self.current_page >= self.max_pages - 1

    def create_embed(self):
        """Create embed for current page"""
        # Calculate start and end indices for current page
        start_idx = self.current_page * 5
        end_idx = min(start_idx + 5, len(self.sorted_users))
        page_users = self.sorted_users[start_idx:end_idx]

        # Create embed
        embed = discord.Embed(
            title="🏆 QuranBot Leaderboard",
            description="*Top users ranked by quiz points*",
            color=0x00D4AA,
        )

        # Medal emojis for top 3
        medal_emojis = {1: "🥇", 2: "🥈", 3: "🥉"}

        leaderboard_text = ""
        for i, (user_id, stats) in enumerate(page_users):
            # Calculate actual position (1-based)
            position = start_idx + i + 1

            # Get position display
            position_display = medal_emojis.get(position, f"{position}.")

            # Format quiz stats
            points = stats["points"]
            streak = stats.get("current_streak", 0)

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

        # Add page indicator
        if self.max_pages > 1:
            embed.set_footer(
                text=f"Page {self.current_page + 1} of {self.max_pages} • created by حَـــــنَـــــا"
            )
        else:
            embed.set_footer(text="created by حَـــــنَـــــا")

        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if user can use the buttons"""
        if interaction.user.id != self.interaction_user.id:
            await interaction.response.send_message(
                "❌ You can only use buttons on your own leaderboard command.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(emoji="⬅️", style=discord.ButtonStyle.primary)
    async def previous_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Go to previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(emoji="➡️", style=discord.ButtonStyle.primary)
    async def next_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Go to next page"""
        if self.current_page < self.max_pages - 1:
            self.current_page += 1
            self.update_buttons()
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        """Disable buttons when view times out"""
        for item in self.children:
            item.disabled = True


# =============================================================================
# Slash Command Implementation
# =============================================================================


@discord.app_commands.command(
    name="leaderboard",
    description="Display the quiz points leaderboard",
)
async def leaderboard_command(interaction: discord.Interaction):
    """Display the quiz points leaderboard with pagination"""
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
            :30
        ]  # Top 30 users

        if not sorted_users:
            # No users to display
            embed = discord.Embed(
                title="🏆 QuranBot Leaderboard",
                description="*No quiz data available yet. Answer some questions to appear on the leaderboard!*",
                color=0x00D4AA,
            )

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
            return

        # Create paginated view
        view = LeaderboardView(sorted_users, interaction.user)
        embed = view.create_embed()

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
                    # Update footer to include admin icon while preserving page info
                    current_footer = (
                        embed.footer.text
                        if embed.footer
                        else "created by حَـــــنَـــــا"
                    )
                    embed.set_footer(
                        text=current_footer,
                        icon_url=admin_user.avatar.url,
                    )
                else:
                    # Keep existing footer text if no admin avatar
                    pass
            else:
                # Keep existing footer text if no developer ID
                pass
        except Exception:
            # Keep existing footer text if error occurs
            pass

        await interaction.response.send_message(embed=embed, view=view)

        # Log command usage
        log_perfect_tree_section(
            "Leaderboard Command - Success",
            [
                ("user", interaction.user.display_name),
                ("user_id", interaction.user.id),
                ("channel", interaction.channel.name if interaction.channel else "DM"),
                ("total_users", len(sorted_users)),
                ("pages", view.max_pages),
                ("users_per_page", 5),
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
            ("command_type", "Slash command with pagination"),
            ("description", "Display quiz points leaderboard"),
            ("permission_level", "🌐 Public command"),
            ("features", "📄 30 users, 5 per page, navigation buttons"),
        ],
        "🏆",
    )
