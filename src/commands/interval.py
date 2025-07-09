import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import discord
from discord import app_commands

from src.utils.tree_log import log_error_with_traceback, log_perfect_tree_section

# Paths to state files
VERSE_STATE_FILE = Path("data/daily_verses_state.json")
QUIZ_STATE_FILE = Path("data/quiz_state.json")

# Admin user ID (replace with your actual admin ID or import from config)
ADMIN_USER_ID = 259725211664908288


# Helper to load current intervals
def load_intervals():
    verse_hours = 3
    question_hours = 3
    # Load verse interval
    if VERSE_STATE_FILE.exists():
        with open(VERSE_STATE_FILE, "r") as f:
            data = json.load(f)
            verse_hours = data.get("schedule_config", {}).get("send_interval_hours", 3)
    # Load question interval
    if QUIZ_STATE_FILE.exists():
        with open(QUIZ_STATE_FILE, "r") as f:
            data = json.load(f)
            question_hours = data.get("schedule_config", {}).get(
                "send_interval_hours", 3
            )
    return verse_hours, question_hours


# Helper to save intervals
def save_interval(type_: str, hours: float):
    if type_ == "verse":
        if VERSE_STATE_FILE.exists():
            with open(VERSE_STATE_FILE, "r") as f:
                data = json.load(f)
        else:
            data = {"schedule_config": {}}
        data.setdefault("schedule_config", {})["send_interval_hours"] = hours
        with open(VERSE_STATE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    elif type_ == "question":
        if QUIZ_STATE_FILE.exists():
            with open(QUIZ_STATE_FILE, "r") as f:
                data = json.load(f)
        else:
            data = {"schedule_config": {}}
        data.setdefault("schedule_config", {})["send_interval_hours"] = hours
        with open(QUIZ_STATE_FILE, "w") as f:
            json.dump(data, f, indent=2)


# Helper to parse time string like '10m', '2h', '1h30m' to hours (float)
def parse_time_string(time_str: str):
    time_str = time_str.strip().lower()
    match = re.fullmatch(r"(?:(\d{1,2})h)?(?:(\d{1,2})m)?", time_str)
    if not match:
        return None
    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    total_minutes = hours * 60 + minutes
    if total_minutes < 1 or total_minutes > 24 * 60:
        return None
    return total_minutes / 60


# Autocomplete function for type parameter
async def type_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """Provide autocomplete options for the type parameter"""
    choices = [
        app_commands.Choice(name="📖 Verse Interval", value="verse"),
        app_commands.Choice(name="❓ Question Interval", value="question"),
    ]

    # Filter choices based on current input
    if current:
        current_lower = current.lower()
        choices = [
            choice
            for choice in choices
            if current_lower in choice.name.lower()
            or current_lower in choice.value.lower()
        ]

    return choices


@app_commands.command(
    name="interval",
    description="Set the posting interval for verses or questions (admin only)",
)
@app_commands.describe(
    type="Which interval to set (verse or question)",
    interval="Interval (e.g. 10m, 2h, 1h30m, 24h, min 1m, max 24h)",
)
@app_commands.autocomplete(type=type_autocomplete)
async def interval_slash_command(
    interaction: discord.Interaction, type: str, interval: str
):
    """Set the posting interval for verses or questions (admin only)"""
    try:
        # Admin only
        if interaction.user.id != ADMIN_USER_ID:
            embed = discord.Embed(
                title="Permission Denied",
                description="You do not have permission to use this command.",
                color=0xFF0000,
            )
            embed.set_thumbnail(url=interaction.client.user.display_avatar.url)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Validate type
        type = type.lower()
        if type not in ("verse", "question"):
            embed = discord.Embed(
                title="Invalid Type",
                description="Type must be 'verse' or 'question'",
                color=0xFF0000,
            )
            embed.set_thumbnail(url=interaction.client.user.display_avatar.url)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Parse interval
        hours = parse_time_string(interval)
        if hours is None:
            embed = discord.Embed(
                title="Invalid Interval",
                description="Interval must be between 1m and 24h (e.g. 10m, 2h, 1h30m)",
                color=0xFF0000,
            )
            embed.set_thumbnail(url=interaction.client.user.display_avatar.url)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        save_interval(type, hours)

        embed = discord.Embed(
            title="Interval Updated",
            description=f"The {type.title()} interval is now set to **{interval}**.",
            color=0x00D4AA,
        )
        embed.set_thumbnail(url=interaction.client.user.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

        # Log successful interval change
        log_perfect_tree_section(
            "Interval Command - Success",
            [
                ("user", f"{interaction.user.display_name} ({interaction.user.id})"),
                ("type", type.title()),
                ("interval", interval),
                ("hours", f"{hours:.2f}"),
                ("status", "✅ Interval updated successfully"),
            ],
            "⏰",
        )

    except Exception as e:
        log_error_with_traceback("Error in interval command", e)
        error_embed = discord.Embed(
            title="❌ Error",
            description="An error occurred while processing the interval command. Please try again later.",
            color=0xFF6B6B,
        )
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
        else:
            await interaction.followup.send(embed=error_embed, ephemeral=True)


async def setup_interval_command(bot):
    """Set up the interval command with comprehensive error handling and logging"""
    try:
        log_perfect_tree_section(
            "Interval Command Setup - Starting",
            [
                ("command_name", "/interval"),
                ("command_type", "Discord Application Command"),
                ("status", "🔄 Initializing interval command setup"),
            ],
            "🚀",
        )

        # Add the slash command to the bot's command tree (like other commands)
        bot.tree.add_command(interval_slash_command)

        log_perfect_tree_section(
            "Interval Command Setup - Complete",
            [
                ("status", "✅ Interval command loaded successfully"),
                ("command_name", "/interval"),
                ("command_type", "Slash command only"),
                ("description", "Set posting intervals for verses and questions"),
                ("permission_level", "🔒 Admin only"),
                ("error_handling", "✅ Comprehensive traceback and logging"),
                ("tree_logging", "✅ Perfect tree logging implemented"),
            ],
            "📖",
        )

    except Exception as setup_error:
        log_error_with_traceback("Failed to set up interval command", setup_error)

        log_perfect_tree_section(
            "Interval Command Setup - Failed",
            [
                ("error_type", type(setup_error).__name__),
                ("status", "❌ Failed to load interval command"),
                ("impact", "🚨 /interval command will not be available"),
            ],
            "💥",
        )

        # Re-raise the exception to ensure the bot startup process is aware of the failure
        raise
