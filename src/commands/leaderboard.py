# =============================================================================
# QuranBot - Leaderboard Command (Cog)
# =============================================================================
# Displays quiz points leaderboard with pagination using Discord.py Cogs
# =============================================================================

import json
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from src.utils.stats import format_listening_time, get_user_listening_stats
from src.utils.tree_log import log_error_with_traceback, log_perfect_tree_section

# Path to quiz stats file
QUIZ_STATS_FILE = Path("data/quiz_stats.json")

# =============================================================================
# Pagination View Class
# =============================================================================


class LeaderboardView(discord.ui.View):
    """View for paginated leaderboard with navigation buttons"""

    def __init__(self, sorted_users, interaction_user, bot_client):
        super().__init__(timeout=300)  # 5 minute timeout
        self.sorted_users = sorted_users
        self.interaction_user = interaction_user
        self.bot_client = bot_client
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

    async def create_embed(self):
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
                f"Listening Time: **{listening_time}** 🎧\n\n"
            )

        if leaderboard_text:
            embed.description = (
                f"*Top users ranked by quiz points*\n\n{leaderboard_text}"
            )
        else:
            embed.description = "*No quiz data available yet. Answer some questions to appear on the leaderboard!*"

        # Set bot profile picture as thumbnail (preserve across all pages)
        try:
            if self.bot_client.user and self.bot_client.user.avatar:
                embed.set_thumbnail(url=self.bot_client.user.avatar.url)
            elif self.bot_client.user:
                embed.set_thumbnail(url=self.bot_client.user.default_avatar.url)
        except Exception:
            pass

        # Set footer with admin profile picture and page info (preserve across all pages)
        try:
            from src.config import get_config

            config = get_config()
            developer_id = config.developer_id or 0
            if developer_id:
                admin_user = await self.bot_client.fetch_user(developer_id)
                if admin_user and admin_user.avatar:
                    # Include page indicator with admin footer
                    if self.max_pages > 1:
                        footer_text = f"Page {self.current_page + 1} of {self.max_pages} • created by حَـــــنَّـــــا"
                    else:
                        footer_text = "created by حَـــــنَّـــــا"

                    embed.set_footer(
                        text=footer_text,
                        icon_url=admin_user.avatar.url,
                    )
                elif self.max_pages > 1:
                    embed.set_footer(
                        text=f"Page {self.current_page + 1} of {self.max_pages} • created by حَـــــنَّـــــا"
                    )
                else:
                    embed.set_footer(text="created by حَـــــنَّـــــا")
            elif self.max_pages > 1:
                embed.set_footer(
                    text=f"Page {self.current_page + 1} of {self.max_pages} • created by حَـــــنَّـــــا"
                )
            else:
                embed.set_footer(text="created by حَـــــنَّـــــا")
        except Exception:
            # Fallback to text-only footer
            if self.max_pages > 1:
                embed.set_footer(
                    text=f"Page {self.current_page + 1} of {self.max_pages} • created by حَـــــنَّـــــا"
                )
            else:
                embed.set_footer(text="created by حَـــــنَّـــــا")

        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if user can use the buttons"""
        if interaction.user.id != self.interaction_user.id:
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You can only use buttons on your own leaderboard command.",
                color=0xFF6B6B,
            )
            embed.set_footer(text="Created by حَـــــنَّـــــا")
            await interaction.response.send_message(embed=embed, ephemeral=True)
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
            embed = await self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(emoji="➡️", style=discord.ButtonStyle.primary)
    async def next_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Go to next page"""
        if self.current_page < self.max_pages - 1:
            self.current_page += 1
            self.update_buttons()
            embed = await self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        """Disable buttons when view times out"""
        for item in self.children:
            item.disabled = True


# =============================================================================
# Leaderboard Cog
# =============================================================================


class LeaderboardCog(commands.Cog):
    """Leaderboard command cog for displaying quiz points leaderboard"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="leaderboard",
        description="Display the quiz points leaderboard",
    )
    async def leaderboard(self, interaction: discord.Interaction):
        """Display the quiz points leaderboard with pagination"""
        try:
            # Load fresh quiz stats from file each time
            try:
                if QUIZ_STATS_FILE.exists():
                    with open(QUIZ_STATS_FILE, encoding="utf-8") as f:
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
            )[:30]

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
                    from src.config import get_config

                    config = get_config()
                    developer_id = config.developer_id or 0
                    if developer_id:
                        admin_user = await interaction.client.fetch_user(developer_id)
                        if admin_user and admin_user.avatar:
                            embed.set_footer(
                                text="created by حَـــــنَّـــــا",
                                icon_url=admin_user.avatar.url,
                            )
                        else:
                            embed.set_footer(text="created by حَـــــنَّـــــا")
                    else:
                        embed.set_footer(text="created by حَـــــنَّـــــا")
                except Exception:
                    embed.set_footer(text="created by حَـــــنَّـــــا")

                await interaction.response.send_message(embed=embed)
                return

            # Create paginated view
            view = LeaderboardView(sorted_users, interaction.user, interaction.client)
            embed = await view.create_embed()

            await interaction.response.send_message(embed=embed, view=view)

            # Log successful leaderboard display
            log_perfect_tree_section(
                "Leaderboard Command - Success",
                [
                    (
                        "user",
                        f"{interaction.user.display_name} ({interaction.user.id})",
                    ),
                    ("total_users", len(sorted_users)),
                    ("pages", view.max_pages),
                    ("status", "✅ Leaderboard displayed successfully"),
                ],
                "🏆",
            )

            # Log to enhanced webhook router
            try:
                from src.core.di_container import get_container

                container = get_container()
                if container:
                    enhanced_webhook = container.get("webhook_router")
                    if enhanced_webhook and hasattr(
                        enhanced_webhook, "log_quran_command_usage"
                    ):
                        await enhanced_webhook.log_quran_command_usage(
                            admin_name=interaction.user.display_name,
                            admin_id=interaction.user.id,
                            command_name="/leaderboard",
                            command_details={
                                "total_users_on_board": str(len(sorted_users)),
                                "total_pages": str(view.max_pages),
                                "top_scorer": (
                                    sorted_users[0][1].get("username", "Unknown")
                                    if sorted_users
                                    else "None"
                                ),
                                "top_score": (
                                    str(sorted_users[0][1].get("points", 0))
                                    if sorted_users
                                    else "0"
                                ),
                                "command_type": "Leaderboard View",
                            },
                            admin_avatar_url=(
                                interaction.user.avatar.url
                                if interaction.user.avatar
                                else None
                            ),
                        )
            except Exception as e:
                log_error_with_traceback("Failed to log to enhanced webhook router", e)

        except Exception as e:
            log_error_with_traceback("Error in leaderboard command", e)
            error_embed = discord.Embed(
                title="❌ Error",
                description="An error occurred while loading the leaderboard. Please try again later.",
                color=0xFF6B6B,
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)


# =============================================================================
# Cog Setup
# =============================================================================


async def setup(bot, container=None):
    """Set up the Leaderboard cog"""
    try:
        log_perfect_tree_section(
            "Leaderboard Cog Setup - Starting",
            [
                ("cog_name", "LeaderboardCog"),
                ("command_name", "/leaderboard"),
                ("status", "🔄 Initializing leaderboard cog setup"),
            ],
            "🚀",
        )

        await bot.add_cog(LeaderboardCog(bot))

        log_perfect_tree_section(
            "Leaderboard Cog Setup - Complete",
            [
                ("status", "✅ Leaderboard cog loaded successfully"),
                ("cog_name", "LeaderboardCog"),
                ("command_name", "/leaderboard"),
                ("description", "Display quiz points leaderboard"),
                ("permission_level", "🌐 Public command"),
                ("features", "📄 30 users, 5 per page, navigation buttons"),
            ],
            "🏆",
        )

    except Exception as setup_error:
        log_error_with_traceback("Failed to set up leaderboard cog", setup_error)

        log_perfect_tree_section(
            "Leaderboard Cog Setup - Failed",
            [
                ("error_type", type(setup_error).__name__),
                ("status", "❌ Failed to load leaderboard cog"),
                ("impact", "🚨 /leaderboard command will not be available"),
            ],
            "💥",
        )

        # Re-raise the exception to ensure the bot startup process is aware of the failure
        raise


# =============================================================================
# Export Functions (for backward compatibility)
# =============================================================================

__all__ = [
    "LeaderboardCog",
    "LeaderboardView",
    "setup",
]
