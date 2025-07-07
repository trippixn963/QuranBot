# =============================================================================
# QuranBot - Verse Command
# =============================================================================
# Manual verse command that sends a daily verse and resets the timer
# =============================================================================

from datetime import datetime, timezone

import discord
from discord.ext import commands

from src.utils.daily_verses import daily_verses_manager
from src.utils.tree_log import log_error_with_traceback, log_perfect_tree_section


class VerseCommand(commands.Cog):
    """Manual verse command for sending daily verses on demand"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="verse", aliases=["v", "daily"])
    async def verse(self, ctx):
        """Send a daily verse manually and reset the 3-hour timer"""
        try:
            # Check if daily verses system is set up
            if (
                not daily_verses_manager.bot
                or not daily_verses_manager.daily_verse_channel_id
            ):
                embed = discord.Embed(
                    title="❌ Daily Verses Not Configured",
                    description="The daily verses system is not set up. Please check the bot configuration.",
                    color=0xFF6B6B,
                )
                await ctx.send(embed=embed)
                return

            # Get the daily verse channel
            channel = self.bot.get_channel(daily_verses_manager.daily_verse_channel_id)
            if not channel:
                embed = discord.Embed(
                    title="❌ Channel Not Found",
                    description="The daily verse channel could not be found.",
                    color=0xFF6B6B,
                )
                await ctx.send(embed=embed)
                return

            # Get next verse
            verse = daily_verses_manager.get_next_verse()
            if not verse:
                embed = discord.Embed(
                    title="❌ No Verses Available",
                    description="No verses are available in the queue or pool.",
                    color=0xFF6B6B,
                )
                await ctx.send(embed=embed)
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
            confirmation_embed.add_field(
                name="📊 Queue Status",
                value=f"**{len(daily_verses_manager.verses_queue)}** verses remaining in queue",
                inline=True,
            )

            await ctx.send(embed=confirmation_embed)

            # Log the manual verse sending
            log_perfect_tree_section(
                "Daily Verses - Manual Verse Sent",
                [
                    ("triggered_by", f"{ctx.author.display_name} ({ctx.author.id})"),
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
            await ctx.send(embed=error_embed)


async def setup_verse_command(bot):
    """Set up the verse command"""
    await bot.add_cog(VerseCommand(bot))

    log_perfect_tree_section(
        "Verse Command Setup",
        [
            ("status", "✅ Verse command loaded successfully"),
            ("command_name", "/verse"),
            ("aliases", "/v, /daily"),
            ("description", "Send daily verse manually and reset timer"),
        ],
        "📖",
    )


# Export the command and setup function
verse_command = VerseCommand
__all__ = ["setup_verse_command", "verse_command"]
