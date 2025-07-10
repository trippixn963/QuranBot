# =============================================================================
# QuranBot - Interval Command (Cog)
# =============================================================================
# Administrative command to adjust quiz and verse intervals using Discord.py Cogs
# =============================================================================

import os
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands

from src.utils.tree_log import (
    log_error_with_traceback,
    log_perfect_tree_section,
    log_user_interaction,
)

# Environment variables
DEVELOPER_ID = int(os.getenv("DEVELOPER_ID", "0"))

# Validate required environment variables
if DEVELOPER_ID == 0:
    raise ValueError("DEVELOPER_ID environment variable must be set")


def get_quiz_manager():
    """Get quiz manager instance"""
    try:
        from src.utils.quiz_manager import quiz_manager

        return quiz_manager
    except Exception as e:
        log_error_with_traceback("Failed to import quiz_manager", e)
        return None


def get_daily_verses_manager():
    """Get daily verses manager instance"""
    try:
        from src.utils.daily_verses import daily_verse_manager

        return daily_verse_manager
    except Exception as e:
        log_error_with_traceback("Failed to import daily_verse_manager", e)
        return None


# =============================================================================
# Interval Cog
# =============================================================================


class IntervalCog(commands.Cog):
    """Interval command cog for adjusting quiz and verse intervals"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="interval",
        description="Adjust quiz and verse intervals (Admin only)",
    )
    @app_commands.describe(
        quiz_hours="Hours between quiz questions (1-24)",
        verse_hours="Hours between daily verses (1-24)",
    )
    async def interval(
        self,
        interaction: discord.Interaction,
        quiz_hours: int = None,
        verse_hours: int = None,
    ):
        """
        Administrative command to adjust quiz and verse intervals.

        This command allows administrators to modify the automatic posting
        intervals for both quiz questions and daily verses.

        Parameters:
        - quiz_hours: Hours between quiz questions (1-24)
        - verse_hours: Hours between daily verses (1-24)

        Features:
        - Admin-only access control
        - Input validation (1-24 hours)
        - Real-time configuration updates
        - Comprehensive error handling
        - Detailed logging

        Usage:
        /interval quiz_hours:3 verse_hours:4
        /interval quiz_hours:6 (only change quiz interval)
        /interval verse_hours:2 (only change verse interval)
        """

        # Log command initiation
        log_perfect_tree_section(
            "Interval Command - Initiated",
            [
                ("user", f"{interaction.user.display_name} ({interaction.user.id})"),
                ("guild", f"{interaction.guild.name}" if interaction.guild else "DM"),
                ("quiz_hours", str(quiz_hours) if quiz_hours else "None"),
                ("verse_hours", str(verse_hours) if verse_hours else "None"),
                ("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                ("status", "🔄 Starting interval command execution"),
            ],
            "⏰",
        )

        try:
            # Check if user is the developer/admin
            if interaction.user.id != DEVELOPER_ID:
                log_perfect_tree_section(
                    "Interval Command - Permission Denied",
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
                except Exception:
                    embed.set_footer(text="Created by حَـــــنَـــــا")

                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Validate parameters
            if quiz_hours is None and verse_hours is None:
                # No parameters provided - show current settings
                await self._show_current_intervals(interaction)
                return

            # Validate ranges
            if quiz_hours is not None and (quiz_hours < 1 or quiz_hours > 24):
                error_embed = discord.Embed(
                    title="❌ Invalid Quiz Hours",
                    description="Quiz hours must be between 1 and 24.",
                    color=0xFF6B6B,
                )
                await interaction.response.send_message(
                    embed=error_embed, ephemeral=True
                )
                return

            if verse_hours is not None and (verse_hours < 1 or verse_hours > 24):
                error_embed = discord.Embed(
                    title="❌ Invalid Verse Hours",
                    description="Verse hours must be between 1 and 24.",
                    color=0xFF6B6B,
                )
                await interaction.response.send_message(
                    embed=error_embed, ephemeral=True
                )
                return

            # Log authorized access
            log_perfect_tree_section(
                "Interval Command - Authorized Access",
                [
                    (
                        "user",
                        f"{interaction.user.display_name} ({interaction.user.id})",
                    ),
                    ("permission_level", "✅ Administrator"),
                    ("status", "🔓 Access granted"),
                    ("action", "🚀 Proceeding with interval updates"),
                ],
                "🔓",
            )

            # Send acknowledgment
            await interaction.response.send_message(
                "⏰ Processing interval updates...", ephemeral=True
            )

            # Update intervals
            changes_made = []
            errors = []

            # Update quiz interval
            if quiz_hours is not None:
                try:
                    quiz_manager = get_quiz_manager()
                    if quiz_manager:
                        old_interval = quiz_manager.get_interval_hours()
                        quiz_manager.set_interval_hours(quiz_hours)
                        changes_made.append(
                            f"Quiz interval: {old_interval}h → {quiz_hours}h"
                        )

                        log_perfect_tree_section(
                            "Quiz Interval - Updated",
                            [
                                ("old_interval", f"{old_interval} hours"),
                                ("new_interval", f"{quiz_hours} hours"),
                                ("status", "✅ Quiz interval updated successfully"),
                            ],
                            "📝",
                        )
                    else:
                        errors.append("Failed to get quiz manager")
                except Exception as e:
                    log_error_with_traceback("Failed to update quiz interval", e)
                    errors.append(f"Quiz interval update failed: {str(e)}")

            # Update verse interval
            if verse_hours is not None:
                try:
                    daily_verses_manager = get_daily_verses_manager()
                    if daily_verses_manager:
                        old_interval = daily_verses_manager.get_interval_hours()
                        daily_verses_manager.set_interval_hours(verse_hours)
                        changes_made.append(
                            f"Verse interval: {old_interval}h → {verse_hours}h"
                        )

                        log_perfect_tree_section(
                            "Verse Interval - Updated",
                            [
                                ("old_interval", f"{old_interval} hours"),
                                ("new_interval", f"{verse_hours} hours"),
                                ("status", "✅ Verse interval updated successfully"),
                            ],
                            "📖",
                        )
                    else:
                        errors.append("Failed to get daily verses manager")
                except Exception as e:
                    log_error_with_traceback("Failed to update verse interval", e)
                    errors.append(f"Verse interval update failed: {str(e)}")

            # Create response embed
            if changes_made and not errors:
                # Success
                embed = discord.Embed(
                    title="✅ Intervals Updated Successfully",
                    description="The following intervals have been updated:",
                    color=0x00D4AA,
                )

                for change in changes_made:
                    embed.add_field(
                        name="📊 Change Made",
                        value=change,
                        inline=False,
                    )

                # Add next scheduled times
                try:
                    now = datetime.now(timezone.utc)
                    if quiz_hours is not None:
                        next_quiz = now + timedelta(hours=quiz_hours)
                        embed.add_field(
                            name="📝 Next Quiz",
                            value=f"<t:{int(next_quiz.timestamp())}:R>",
                            inline=True,
                        )

                    if verse_hours is not None:
                        next_verse = now + timedelta(hours=verse_hours)
                        embed.add_field(
                            name="📖 Next Verse",
                            value=f"<t:{int(next_verse.timestamp())}:R>",
                            inline=True,
                        )
                except Exception:
                    pass

                log_perfect_tree_section(
                    "Interval Command - Success",
                    [
                        (
                            "user",
                            f"{interaction.user.display_name} ({interaction.user.id})",
                        ),
                        ("changes_made", len(changes_made)),
                        ("quiz_hours", str(quiz_hours) if quiz_hours else "unchanged"),
                        (
                            "verse_hours",
                            str(verse_hours) if verse_hours else "unchanged",
                        ),
                        ("status", "✅ All intervals updated successfully"),
                    ],
                    "🏆",
                )

            elif changes_made and errors:
                # Partial success
                embed = discord.Embed(
                    title="⚠️ Intervals Partially Updated",
                    description="Some intervals were updated, but errors occurred:",
                    color=0xFFA500,
                )

                for change in changes_made:
                    embed.add_field(
                        name="✅ Success",
                        value=change,
                        inline=False,
                    )

                for error in errors:
                    embed.add_field(
                        name="❌ Error",
                        value=error,
                        inline=False,
                    )

            else:
                # All failed
                embed = discord.Embed(
                    title="❌ Interval Update Failed",
                    description="Failed to update intervals:",
                    color=0xFF6B6B,
                )

                for error in errors:
                    embed.add_field(
                        name="❌ Error",
                        value=error,
                        inline=False,
                    )

            # Set footer
            embed.set_footer(text="Created by حَـــــنَـــــا")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            log_error_with_traceback("Error in interval command", e)

            log_perfect_tree_section(
                "Interval Command - Unexpected Error",
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
                    description="An unexpected error occurred while processing the interval command. Please try again later.",
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

    async def _show_current_intervals(self, interaction: discord.Interaction):
        """Show current interval settings"""
        try:
            # Get current intervals
            quiz_interval = None
            verse_interval = None

            try:
                quiz_manager = get_quiz_manager()
                if quiz_manager:
                    quiz_interval = quiz_manager.get_interval_hours()
            except Exception as e:
                log_error_with_traceback("Failed to get quiz interval", e)

            try:
                daily_verses_manager = get_daily_verses_manager()
                if daily_verses_manager:
                    verse_interval = daily_verses_manager.get_interval_hours()
            except Exception as e:
                log_error_with_traceback("Failed to get verse interval", e)

            # Create embed
            embed = discord.Embed(
                title="⏰ Current Interval Settings",
                description="Current automatic posting intervals:",
                color=0x00D4AA,
            )

            if quiz_interval is not None:
                embed.add_field(
                    name="📝 Quiz Interval",
                    value=f"**{quiz_interval} hours**",
                    inline=True,
                )
            else:
                embed.add_field(
                    name="📝 Quiz Interval",
                    value="❌ Unable to retrieve",
                    inline=True,
                )

            if verse_interval is not None:
                embed.add_field(
                    name="📖 Verse Interval",
                    value=f"**{verse_interval} hours**",
                    inline=True,
                )
            else:
                embed.add_field(
                    name="📖 Verse Interval",
                    value="❌ Unable to retrieve",
                    inline=True,
                )

            embed.add_field(
                name="💡 Usage",
                value="Use `/interval quiz_hours:X verse_hours:Y` to update intervals",
                inline=False,
            )

            # Set footer
            embed.set_footer(text="Created by حَـــــنَـــــا")

            await interaction.response.send_message(embed=embed, ephemeral=True)

            log_perfect_tree_section(
                "Interval Command - Current Settings Shown",
                [
                    (
                        "user",
                        f"{interaction.user.display_name} ({interaction.user.id})",
                    ),
                    (
                        "quiz_interval",
                        f"{quiz_interval} hours" if quiz_interval else "Unknown",
                    ),
                    (
                        "verse_interval",
                        f"{verse_interval} hours" if verse_interval else "Unknown",
                    ),
                    ("status", "✅ Current settings displayed"),
                ],
                "📋",
            )

        except Exception as e:
            log_error_with_traceback("Error showing current intervals", e)

            error_embed = discord.Embed(
                title="❌ Error",
                description="Failed to retrieve current interval settings.",
                color=0xFF6B6B,
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)


# =============================================================================
# Cog Setup
# =============================================================================


async def setup(bot):
    """Set up the Interval cog with comprehensive error handling and logging"""
    try:
        log_perfect_tree_section(
            "Interval Cog Setup - Starting",
            [
                ("cog_name", "IntervalCog"),
                ("command_name", "/interval"),
                ("status", "🔄 Initializing interval cog setup"),
            ],
            "🚀",
        )

        await bot.add_cog(IntervalCog(bot))

        log_perfect_tree_section(
            "Interval Cog Setup - Complete",
            [
                ("status", "✅ Interval cog loaded successfully"),
                ("cog_name", "IntervalCog"),
                ("command_name", "/interval"),
                ("description", "Adjust quiz and verse intervals"),
                ("permission_level", "🔒 Admin only"),
                ("parameters", "quiz_hours (1-24), verse_hours (1-24)"),
                ("error_handling", "✅ Comprehensive traceback and logging"),
                ("tree_logging", "✅ Perfect tree logging implemented"),
            ],
            "⏰",
        )

    except Exception as setup_error:
        log_error_with_traceback("Failed to set up interval cog", setup_error)

        log_perfect_tree_section(
            "Interval Cog Setup - Failed",
            [
                ("error_type", type(setup_error).__name__),
                ("status", "❌ Failed to load interval cog"),
                ("impact", "🚨 /interval command will not be available"),
            ],
            "💥",
        )

        # Re-raise the exception to ensure the bot startup process is aware of the failure
        raise


# =============================================================================
# Export Functions (for backward compatibility)
# =============================================================================

__all__ = [
    "IntervalCog",
    "get_quiz_manager",
    "get_daily_verses_manager",
    "setup",
]
