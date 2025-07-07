# =============================================================================
# QuranBot - Leaderboard Command
# =============================================================================
# Displays listening time leaderboard for Quran voice channel users
# =============================================================================

from datetime import datetime, timezone

import discord
from discord.ext import commands

from src.utils.listening_stats import get_leaderboard_data
from src.utils.tree_log import log_error_with_traceback, log_perfect_tree_section


class LeaderboardCommand(commands.Cog):
    """Leaderboard command for displaying listening statistics"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="leaderboard", aliases=["lb", "top"])
    async def leaderboard(self, ctx):
        """Display the Quran listening leaderboard"""
        try:
            # Get leaderboard data
            leaderboard_data = get_leaderboard_data()
            top_users = leaderboard_data["top_users"]

            if not top_users:
                embed = discord.Embed(
                    title="🏆 Quran Listening Leaderboard",
                    description="No listening data available yet. Join the voice channel to start tracking!",
                    color=0x00D4AA,
                )
                await ctx.send(embed=embed)
                return

            # Create embed
            embed = discord.Embed(
                title="🏆 Quran Listening Leaderboard",
                description="*Top listeners in the Quran voice channel*",
                color=0x00D4AA,
                timestamp=datetime.now(timezone.utc),
            )

            # Medal emojis for top 3
            medal_emojis = {1: "🥇", 2: "🥈", 3: "🥉"}

            leaderboard_text = ""
            for position, (user_id, total_time, sessions) in enumerate(top_users, 1):
                # Get position display
                position_display = medal_emojis.get(position, f"{position}.")

                # Format time
                time_formatted = self._format_time(total_time)

                # Get user object to access username
                try:
                    user = self.bot.get_user(user_id)
                    if user:
                        username = user.name  # Discord username (can't contain Arabic)
                        user_display = f"{username} - <@{user_id}>"
                    else:
                        user_display = f"<@{user_id}>"
                except:
                    user_display = f"<@{user_id}>"

                # Create leaderboard entry with username first, then mention
                leaderboard_text += (
                    f"{position_display} {user_display}\n"
                    f"**Time spent**: `{time_formatted}`\n\n"
                )

            embed.description = (
                f"*Top listeners in the Quran voice channel*\n\n{leaderboard_text}"
            )

            # Add stats footer
            embed.add_field(
                name="📊 Server Statistics",
                value=f"**Active Listeners:** {leaderboard_data['active_users']} 🎧\n"
                f"**Total Users:** {leaderboard_data['total_users']} 👥\n"
                f"**Total Sessions:** {leaderboard_data['total_sessions']} 🔢",
                inline=False,
            )

            # Set bot avatar as thumbnail
            if self.bot.user and self.bot.user.avatar:
                embed.set_thumbnail(url=self.bot.user.avatar.url)

            # Set footer
            embed.set_footer(
                text=f"QuranBot v2.2.1 • Requested by {ctx.author.display_name}",
                icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None,
            )

            await ctx.send(embed=embed)

            # Log command usage
            log_perfect_tree_section(
                "Leaderboard Command - Success",
                [
                    ("user", ctx.author.display_name),
                    ("user_id", ctx.author.id),
                    ("channel", ctx.channel.name),
                    ("top_users_shown", len(top_users)),
                ],
                "🏆",
            )

        except Exception as e:
            log_error_with_traceback("Error in leaderboard command", e)
            await ctx.send("❌ Error generating leaderboard. Please try again.")

    def _format_time(self, seconds: float) -> str:
        """Format time in seconds to human-readable format"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            if hours < 24:
                return f"{hours}h {minutes}m"
            else:
                days = int(hours // 24)
                remaining_hours = int(hours % 24)
                return f"{days}d {remaining_hours}h"


async def setup(bot):
    """Set up the leaderboard command"""
    await bot.add_cog(LeaderboardCommand(bot))
