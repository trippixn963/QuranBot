# =============================================================================
# QuranBot - Interval Command (Cog)
# =============================================================================
# Administrative command to adjust quiz and verse intervals using Discord.py Cogs
# =============================================================================

from datetime import UTC, datetime, timedelta
import re

import discord
from discord import app_commands
from discord.ext import commands

# Import configuration service
from src.config import get_config_service
from src.core.exceptions import (
    ValidationError,
)
from src.core.security import rate_limit, require_admin, validate_input
from src.utils import daily_verses
from src.utils import quiz_manager as quiz_mgr
from src.utils.tree_log import log_error_with_traceback, log_perfect_tree_section


def parse_time_string(time_str: str) -> float:
    """
    Parse a time string into hours.

    Supported formats:
    - "30m" -> 0.5 hours
    - "2h" -> 2.0 hours
    - "1h30m" -> 1.5 hours
    - "90m" -> 1.5 hours
    - "2.5h" -> 2.5 hours
    - "120" -> 2.0 hours (assumes minutes if no unit)

    Returns:
        float: Time in hours

    Raises:
        ValueError: If format is invalid
    """
    if not time_str:
        log_perfect_tree_section(
            "Time Parsing - Empty Input",
            [
                ("input", "Empty string"),
                ("status", "❌ Invalid input"),
            ],
            "⏰",
        )
        raise ValidationError(
            "Time string cannot be empty",
            field_name="time_string",
            field_value=time_str,
            validation_rule="cannot be empty",
        )

    original_input = time_str
    time_str = time_str.lower().strip()

    log_perfect_tree_section(
        "Time Parsing - Started",
        [
            ("original_input", f"'{original_input}'"),
            ("normalized_input", f"'{time_str}'"),
            ("parsing_method", "Regex pattern matching"),
        ],
        "⏰",
    )

    # Pattern to match combinations like "1h30m", "2h", "30m", "2.5h", etc.
    pattern = r"^(?:(\d+(?:\.\d+)?)h)?(?:(\d+(?:\.\d+)?)m)?$"
    match = re.match(pattern, time_str)

    if match:
        hours_str, minutes_str = match.groups()
        total_hours = 0.0

        parsing_details = [
            ("pattern_match", "✅ Regex pattern matched"),
            ("hours_component", hours_str if hours_str else "None"),
            ("minutes_component", minutes_str if minutes_str else "None"),
        ]

        if hours_str:
            hours_value = float(hours_str)
            total_hours += hours_value
            parsing_details.append(("hours_parsed", f"{hours_value}h"))

        if minutes_str:
            minutes_value = float(minutes_str)
            total_hours += minutes_value / 60.0
            parsing_details.append(
                ("minutes_parsed", f"{minutes_value}m ({minutes_value/60.0:.3f}h)")
            )

        if total_hours > 0:
            parsing_details.extend(
                [
                    ("total_hours", f"{total_hours:.3f}"),
                    ("formatted_display", format_time_display(total_hours)),
                    ("status", "✅ Successfully parsed"),
                ]
            )

            log_perfect_tree_section(
                "Time Parsing - Success (Pattern Match)",
                parsing_details,
                "✅",
            )
            return total_hours

    # Try parsing as just a number (assume minutes)
    try:
        number = float(time_str)
        if number > 0:
            # If it's a reasonable number for hours (<=24), treat as hours
            # Otherwise treat as minutes
            if number <= 24:
                result_hours = number
                interpretation = "hours (number ≤ 24)"
            else:
                result_hours = number / 60.0
                interpretation = "minutes (number > 24)"

            log_perfect_tree_section(
                "Time Parsing - Success (Number)",
                [
                    ("input_number", str(number)),
                    ("interpretation", interpretation),
                    ("result_hours", f"{result_hours:.3f}"),
                    ("formatted_display", format_time_display(result_hours)),
                    ("status", "✅ Successfully parsed as number"),
                ],
                "✅",
            )
            return result_hours
    except ValueError:
        log_perfect_tree_section(
            "Time Parsing - Number Parse Failed",
            [
                ("input", f"'{time_str}'"),
                ("error", "Not a valid number"),
                ("status", "❌ Number parsing failed"),
            ],
            "❌",
        )

    # All parsing methods failed
    log_perfect_tree_section(
        "Time Parsing - Failed",
        [
            ("original_input", f"'{original_input}'"),
            ("normalized_input", f"'{time_str}'"),
            ("pattern_match", "❌ No regex match"),
            ("number_parse", "❌ Not a valid number"),
            ("status", "❌ All parsing methods failed"),
        ],
        "❌",
    )

    raise ValidationError(
        f"Invalid time format: '{original_input}'. Use formats like '30m', '2h', '1h30m', or '90'",
        field_name="time_format",
        field_value=original_input,
        validation_rule="must match formats like '30m', '2h', '1h30m', or '90'",
    )


def format_time_display(hours: float) -> str:
    """
    Format hours into a readable string.

    Args:
        hours: Time in hours

    Returns:
        str: Formatted time string like "1h 30m" or "30m"
    """
    if hours < 0:
        log_perfect_tree_section(
            "Time Formatting - Invalid Input",
            [
                ("input_hours", str(hours)),
                ("status", "❌ Negative time value"),
                ("result", "Invalid"),
            ],
            "⏰",
        )
        return "Invalid"

    total_minutes = int(hours * 60)
    display_hours = total_minutes // 60
    display_minutes = total_minutes % 60

    if display_hours > 0 and display_minutes > 0:
        result = f"{display_hours}h {display_minutes}m"
    elif display_hours > 0:
        result = f"{display_hours}h"
    else:
        result = f"{display_minutes}m"

    log_perfect_tree_section(
        "Time Formatting - Success",
        [
            ("input_hours", f"{hours:.3f}"),
            ("total_minutes", str(total_minutes)),
            ("display_hours", str(display_hours)),
            ("display_minutes", str(display_minutes)),
            ("formatted_result", f"'{result}'"),
            ("status", "✅ Successfully formatted"),
        ],
        "✅",
    )

    return result


def get_quiz_manager():
    """Get quiz manager instance"""
    try:
        return quiz_mgr.quiz_manager
    except Exception as e:
        log_error_with_traceback("Failed to access quiz_manager", e)
        return None


def get_daily_verses_manager():
    """Get daily verses manager instance"""
    try:
        return daily_verses.daily_verse_manager
    except Exception as e:
        log_error_with_traceback("Failed to access daily_verse_manager", e)
        return None


# =============================================================================
# Interval Cog
# =============================================================================


class IntervalCog(commands.Cog):
    """Interval command cog for adjusting quiz and verse intervals"""

    def __init__(self, bot, container=None):
        self.bot = bot
        self.container = container

    @app_commands.command(
        name="interval",
        description="Adjust quiz and verse intervals with flexible time formats (Admin only)",
    )
    @app_commands.describe(
        quiz_time="Quiz interval (e.g., '30m', '2h', '1h30m', '90m')",
        verse_time="Verse interval (e.g., '3h', '2h30m', '180m')",
    )
    async def interval(
        self,
        interaction: discord.Interaction,
        quiz_time: str = None,
        verse_time: str = None,
    ):
        """
        Administrative command to adjust quiz and verse intervals.

        This command allows administrators to modify the automatic posting
        intervals for both quiz questions and daily verses using flexible
        time formats.

        Parameters:
        - quiz_time: Time between quiz questions (e.g., '30m', '2h', '1h30m')
        - verse_time: Time between daily verses (e.g., '3h', '2h30m', '180m')

        Supported time formats:
        - Minutes: '30m', '90m'
        - Hours: '2h', '3h'
        - Combined: '1h30m', '2h15m'
        - Decimal hours: '2.5h', '1.25h'
        - Numbers: '120' (interpreted as minutes if >24, hours if ≤24)

        Features:
        - Admin-only access control
        - Flexible time format parsing
        - Input validation (1 minute to 24 hours)
        - Real-time configuration updates
        - Comprehensive error handling
        - Detailed logging

        Usage:
        /interval quiz_time:30m verse_time:3h
        /interval quiz_time:1h30m (only change quiz interval)
        /interval verse_time:2h30m (only change verse interval)
        """

        # Log command initiation
        log_perfect_tree_section(
            "Interval Command - Initiated",
            [
                ("user", f"{interaction.user.display_name} ({interaction.user.id})"),
                ("guild", f"{interaction.guild.name}" if interaction.guild else "DM"),
                ("quiz_time", quiz_time if quiz_time else "None"),
                ("verse_time", verse_time if verse_time else "None"),
                ("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                ("status", "🔄 Starting interval command execution"),
            ],
            "⏰",
        )

        try:
            # Simple admin check
            config = get_config_service().config
            if interaction.user.id != config.DEVELOPER_ID:
                embed = discord.Embed(
                    title="❌ Permission Denied",
                    description="This command is only available to the bot administrator.",
                    color=0xFF6B6B,
                )
                embed.set_footer(text="Created by حَـــــنَّـــــا")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Validate parameters
            if quiz_time is None and verse_time is None:
                # No parameters provided - show current settings
                await self._show_current_intervals(interaction)
                return

            # Parse and validate time formats
            quiz_hours = None
            verse_hours = None

            if quiz_time is not None:
                log_perfect_tree_section(
                    "Quiz Time Validation - Started",
                    [
                        ("input", f"'{quiz_time}'"),
                        ("validation_range", "1 minute to 24 hours"),
                        ("status", "🔄 Starting quiz time parsing"),
                    ],
                    "📝",
                )

                try:
                    quiz_hours = parse_time_string(quiz_time)

                    log_perfect_tree_section(
                        "Quiz Time Validation - Parsed",
                        [
                            ("input", f"'{quiz_time}'"),
                            ("parsed_hours", f"{quiz_hours:.3f}"),
                            ("formatted_display", format_time_display(quiz_hours)),
                            ("status", "✅ Successfully parsed"),
                        ],
                        "📝",
                    )

                    if quiz_hours < (1 / 60) or quiz_hours > 24:  # 1 minute to 24 hours
                        log_perfect_tree_section(
                            "Quiz Time Validation - Out of Range",
                            [
                                ("input", f"'{quiz_time}'"),
                                ("parsed_hours", f"{quiz_hours:.3f}"),
                                ("formatted_display", format_time_display(quiz_hours)),
                                ("valid_range", "1 minute (0.017h) to 24 hours"),
                                ("status", "❌ Value out of range"),
                            ],
                            "❌",
                        )

                        error_embed = discord.Embed(
                            title="❌ Invalid Quiz Time",
                            description=f"Quiz time must be between 1 minute and 24 hours.\nYou entered: `{quiz_time}` = {format_time_display(quiz_hours)}",
                            color=0xFF6B6B,
                        )
                        error_embed.add_field(
                            name="💡 Valid Examples",
                            value="• ⏰ `30m` (30 minutes)\n• 🕐 `2h` (2 hours)\n• ⏳ `1h30m` (1 hour 30 minutes)\n• 📅 `90m` (90 minutes)",
                            inline=False,
                        )
                        await interaction.response.send_message(
                            embed=error_embed, ephemeral=True
                        )
                        return
                    else:
                        log_perfect_tree_section(
                            "Quiz Time Validation - Success",
                            [
                                ("input", f"'{quiz_time}'"),
                                ("parsed_hours", f"{quiz_hours:.3f}"),
                                ("formatted_display", format_time_display(quiz_hours)),
                                ("validation_range", "✅ Within valid range"),
                                ("status", "✅ Quiz time validation passed"),
                            ],
                            "✅",
                        )

                except ValueError as e:
                    log_perfect_tree_section(
                        "Quiz Time Validation - Parse Error",
                        [
                            ("input", f"'{quiz_time}'"),
                            ("error_message", str(e)),
                            ("status", "❌ Failed to parse quiz time"),
                        ],
                        "❌",
                    )

                    error_embed = discord.Embed(
                        title="❌ Invalid Quiz Time Format",
                        description=str(e),
                        color=0xFF6B6B,
                    )
                    error_embed.add_field(
                        name="💡 Valid Examples",
                        value="• ⏰ `30m` (30 minutes)\n• 🕐 `2h` (2 hours)\n• ⏳ `1h30m` (1 hour 30 minutes)\n• 📅 `90m` (90 minutes)\n• 🕑 `2.5h` (2.5 hours)",
                        inline=False,
                    )
                    await interaction.response.send_message(
                        embed=error_embed, ephemeral=True
                    )
                    return

            if verse_time is not None:
                log_perfect_tree_section(
                    "Verse Time Validation - Started",
                    [
                        ("input", f"'{verse_time}'"),
                        ("validation_range", "1 minute to 24 hours"),
                        ("status", "🔄 Starting verse time parsing"),
                    ],
                    "📖",
                )

                try:
                    verse_hours = parse_time_string(verse_time)

                    log_perfect_tree_section(
                        "Verse Time Validation - Parsed",
                        [
                            ("input", f"'{verse_time}'"),
                            ("parsed_hours", f"{verse_hours:.3f}"),
                            ("formatted_display", format_time_display(verse_hours)),
                            ("status", "✅ Successfully parsed"),
                        ],
                        "📖",
                    )

                    if (
                        verse_hours < (1 / 60) or verse_hours > 24
                    ):  # 1 minute to 24 hours
                        log_perfect_tree_section(
                            "Verse Time Validation - Out of Range",
                            [
                                ("input", f"'{verse_time}'"),
                                ("parsed_hours", f"{verse_hours:.3f}"),
                                ("formatted_display", format_time_display(verse_hours)),
                                ("valid_range", "1 minute (0.017h) to 24 hours"),
                                ("status", "❌ Value out of range"),
                            ],
                            "❌",
                        )

                        error_embed = discord.Embed(
                            title="❌ Invalid Verse Time",
                            description=f"Verse time must be between 1 minute and 24 hours.\nYou entered: `{verse_time}` = {format_time_display(verse_hours)}",
                            color=0xFF6B6B,
                        )
                        error_embed.add_field(
                            name="💡 Valid Examples",
                            value="• 🕒 `3h` (3 hours)\n• ⏰ `2h30m` (2 hours 30 minutes)\n• 📅 `180m` (180 minutes)\n• 🕓 `4h` (4 hours)",
                            inline=False,
                        )
                        await interaction.response.send_message(
                            embed=error_embed, ephemeral=True
                        )
                        return
                    else:
                        log_perfect_tree_section(
                            "Verse Time Validation - Success",
                            [
                                ("input", f"'{verse_time}'"),
                                ("parsed_hours", f"{verse_hours:.3f}"),
                                ("formatted_display", format_time_display(verse_hours)),
                                ("validation_range", "✅ Within valid range"),
                                ("status", "✅ Verse time validation passed"),
                            ],
                            "✅",
                        )

                except ValueError as e:
                    log_perfect_tree_section(
                        "Verse Time Validation - Parse Error",
                        [
                            ("input", f"'{verse_time}'"),
                            ("error_message", str(e)),
                            ("status", "❌ Failed to parse verse time"),
                        ],
                        "❌",
                    )

                    error_embed = discord.Embed(
                        title="❌ Invalid Verse Time Format",
                        description=str(e),
                        color=0xFF6B6B,
                    )
                    error_embed.add_field(
                        name="💡 Valid Examples",
                        value="• 🕒 `3h` (3 hours)\n• ⏰ `2h30m` (2 hours 30 minutes)\n• 📅 `180m` (180 minutes)\n• 🕓 `4.5h` (4.5 hours)",
                        inline=False,
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
                    (
                        "quiz_hours",
                        f"{quiz_hours} hours" if quiz_hours else "unchanged",
                    ),
                    (
                        "verse_hours",
                        f"{verse_hours} hours" if verse_hours else "unchanged",
                    ),
                    ("status", "🔓 Access granted"),
                    ("action", "🚀 Proceeding with interval updates"),
                ],
                "🔓",
            )

            # Send acknowledgment
            ack_embed = discord.Embed(
                title="⏰ Processing Interval Updates",
                description="Processing your interval changes...",
                color=0x3498DB,
            )
            ack_embed.set_footer(text="Created by حَـــــنَّـــــا")
            await interaction.response.send_message(embed=ack_embed, ephemeral=True)

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
                            f"Quiz interval: {format_time_display(old_interval)} → {format_time_display(quiz_hours)}"
                        )

                        log_perfect_tree_section(
                            "Quiz Interval - Updated",
                            [
                                ("old_interval", format_time_display(old_interval)),
                                ("new_interval", format_time_display(quiz_hours)),
                                ("input_format", quiz_time),
                                ("status", "✅ Quiz interval updated successfully"),
                            ],
                            "📝",
                        )
                    else:
                        errors.append("Failed to get quiz manager")
                except Exception as e:
                    log_error_with_traceback("Failed to update quiz interval", e)
                    errors.append(f"Quiz interval update failed: {e!s}")

            # Update verse interval
            if verse_hours is not None:
                try:
                    daily_verses_manager = get_daily_verses_manager()
                    if daily_verses_manager:
                        old_interval = daily_verses_manager.get_interval_hours()
                        daily_verses_manager.set_interval_hours(verse_hours)
                        changes_made.append(
                            f"Verse interval: {format_time_display(old_interval)} → {format_time_display(verse_hours)}"
                        )

                        log_perfect_tree_section(
                            "Verse Interval - Updated",
                            [
                                ("old_interval", format_time_display(old_interval)),
                                ("new_interval", format_time_display(verse_hours)),
                                ("input_format", verse_time),
                                ("status", "✅ Verse interval updated successfully"),
                            ],
                            "📖",
                        )
                    else:
                        errors.append("Failed to get daily verses manager")
                except Exception as e:
                    log_error_with_traceback("Failed to update verse interval", e)
                    errors.append(f"Verse interval update failed: {e!s}")

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
                    now = datetime.now(UTC)
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
                except (AttributeError, TypeError, ValueError, OverflowError):
                    # Skip timing calculations if data is invalid
                    pass

                # Add format examples
                embed.add_field(
                    name="💡 Time Format Examples",
                    value="• ⏰ `30m` (30 minutes)\n• 🕐 `2h` (2 hours)\n• ⏳ `1h30m` (1 hour 30 minutes)\n• 📅 `90m` (90 minutes)",
                    inline=False,
                )

                log_perfect_tree_section(
                    "Interval Command - Success",
                    [
                        (
                            "user",
                            f"{interaction.user.display_name} ({interaction.user.id})",
                        ),
                        ("changes_made", len(changes_made)),
                        (
                            "quiz_time",
                            (
                                f"{quiz_time} ({format_time_display(quiz_hours)})"
                                if quiz_hours
                                else "unchanged"
                            ),
                        ),
                        (
                            "verse_time",
                            (
                                f"{verse_time} ({format_time_display(verse_hours)})"
                                if verse_hours
                                else "unchanged"
                            ),
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

            # Send success notification to enhanced webhook router first
            try:
                from src.core.di_container import get_container
                container = get_container()
                if container:
                    enhanced_webhook = container.get("enhanced_webhook_router")
                    if enhanced_webhook and hasattr(enhanced_webhook, "log_control_panel_interaction"):
                        changes_text = "\n".join([f"• {change}" for change in changes_made])
                        await enhanced_webhook.log_control_panel_interaction(
                            interaction_type="interval_command",
                            user_name=interaction.user.display_name,
                            user_id=interaction.user.id,
                            action_performed="Interval settings updated",
                            user_avatar_url=interaction.user.avatar.url if interaction.user.avatar else None,
                            panel_details={
                                "changes_made": changes_text,
                                "quiz_time": f"{quiz_time} ({format_time_display(quiz_hours)})" if quiz_hours else "unchanged",
                                "verse_time": f"{verse_time} ({format_time_display(verse_hours)})" if verse_hours else "unchanged",
                                "changes_count": len(changes_made),
                                "timers_reset": "All timers reset to new intervals"
                            }
                        )
            except Exception as e:
                log_error_with_traceback("Failed to log to enhanced webhook router", e)

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
                    value=f"**{format_time_display(quiz_interval)}**",
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
                    value=f"**{format_time_display(verse_interval)}**",
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
                value="Use `/interval quiz_time:30m verse_time:3h` to update intervals",
                inline=False,
            )

            embed.add_field(
                name="🕒 Time Format Examples",
                value="• ⏰ `30m` (30 minutes)\n• 🕐 `2h` (2 hours)\n• ⏳ `1h30m` (1 hour 30 minutes)\n• 📅 `90m` (90 minutes)\n• 🕑 `2.5h` (2.5 hours)",
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
                        (
                            format_time_display(quiz_interval)
                            if quiz_interval
                            else "Unknown"
                        ),
                    ),
                    (
                        "verse_interval",
                        (
                            format_time_display(verse_interval)
                            if verse_interval
                            else "Unknown"
                        ),
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


async def setup(bot, container=None):
    """Set up the Interval cog"""
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

        await bot.add_cog(IntervalCog(bot, container))

        log_perfect_tree_section(
            "Interval Cog Setup - Complete",
            [
                ("status", "✅ Interval cog loaded successfully"),
                ("cog_name", "IntervalCog"),
                ("command_name", "/interval"),
                (
                    "description",
                    "Adjust quiz and verse intervals with flexible time formats",
                ),
                ("permission_level", "🔒 Admin only"),
                (
                    "parameters",
                    "quiz_time (e.g., '30m', '2h', '1h30m'), verse_time (e.g., '3h', '2h30m')",
                ),
                ("time_formats", "Minutes, hours, combined formats, decimal hours"),
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
    "format_time_display",
    "get_daily_verses_manager",
    "get_quiz_manager",
    "parse_time_string",
    "setup",
]
