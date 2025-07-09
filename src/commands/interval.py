import json
from datetime import datetime, timezone
from pathlib import Path

import discord
from discord.ext import commands

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
            question_hours = data.get("question_interval_hours", 3)
    return verse_hours, question_hours


# Helper to save verse interval
def save_verse_interval(hours):
    if VERSE_STATE_FILE.exists():
        with open(VERSE_STATE_FILE, "r") as f:
            data = json.load(f)
    else:
        data = {}
    if "schedule_config" not in data:
        data["schedule_config"] = {}
    data["schedule_config"]["send_interval_hours"] = hours
    with open(VERSE_STATE_FILE, "w") as f:
        json.dump(data, f, indent=2)


# Helper to save question interval
def save_question_interval(hours):
    if QUIZ_STATE_FILE.exists():
        with open(QUIZ_STATE_FILE, "r") as f:
            data = json.load(f)
    else:
        data = {}
    data["question_interval_hours"] = hours
    data["last_update"] = datetime.now(timezone.utc).isoformat()
    with open(QUIZ_STATE_FILE, "w") as f:
        json.dump(data, f, indent=2)


# Main interval command setup
def setup_interval_command(bot):
    @bot.tree.command(
        name="interval",
        description="View or set verse/question post intervals (admin only)",
    )
    @commands.is_owner()
    async def interval(interaction: discord.Interaction):
        # Admin only
        if interaction.user.id != ADMIN_USER_ID:
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You do not have permission to use this command.",
                color=0xFF6B6B,
            )
            if bot.user and bot.user.avatar:
                embed.set_thumbnail(url=bot.user.avatar.url)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        verse_hours, question_hours = load_intervals()
        embed = discord.Embed(
            title="⏰ Interval Settings",
            description="Change how often verses and questions are posted.",
            color=0x00D4AA,
        )
        embed.add_field(
            name="📖 Verse Interval", value=f"`{verse_hours}` hours", inline=False
        )
        embed.add_field(
            name="❓ Question Interval", value=f"`{question_hours}` hours", inline=False
        )
        embed.set_footer(text="Admin only | Use /interval set to change")
        if bot.user and bot.user.avatar:
            embed.set_thumbnail(url=bot.user.avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(
        name="interval_set", description="Set verse or question interval (admin only)"
    )
    @commands.is_owner()
    async def interval_set(interaction: discord.Interaction, type: str, hours: int):
        # Admin only
        if interaction.user.id != ADMIN_USER_ID:
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You do not have permission to use this command.",
                color=0xFF6B6B,
            )
            if bot.user and bot.user.avatar:
                embed.set_thumbnail(url=bot.user.avatar.url)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if type.lower() == "verse":
            save_verse_interval(hours)
            what = "Verse"
        elif type.lower() == "question":
            save_question_interval(hours)
            what = "Question"
        else:
            embed = discord.Embed(
                title="❌ Invalid Type",
                description="Type must be 'verse' or 'question'",
                color=0xFF6B6B,
            )
            if bot.user and bot.user.avatar:
                embed.set_thumbnail(url=bot.user.avatar.url)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        embed = discord.Embed(
            title="✅ Interval Updated",
            description=f"{what} interval set to `{hours}` hours.",
            color=0x00D4AA,
        )
        if bot.user and bot.user.avatar:
            embed.set_thumbnail(url=bot.user.avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)


# For dynamic loading
async def setup(bot):
    setup_interval_command(bot)
