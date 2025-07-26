# =============================================================================
# QuranBot - Test Prayer Notification Command
# =============================================================================
# Temporary command for testing Mecca prayer notifications
# =============================================================================

import discord
from discord import app_commands
from discord.ext import commands

from src.config import get_config_service
from src.utils.mecca_prayer_times import get_mecca_prayer_notifier


class TestPrayerCog(commands.Cog):
    """Test prayer notification command"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="test-prayer",
        description="Test Mecca prayer notification (Admin only)"
    )
    @app_commands.describe(
        prayer="Prayer to test (fajr, dhuhr, asr, maghrib, isha)"
    )
    async def test_prayer(
        self,
        interaction: discord.Interaction,
        prayer: str = "maghrib"
    ):
        """Test prayer notification command"""
        
        # Admin check
        config = get_config_service().config
        if interaction.user.id != config.DEVELOPER_ID:
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="This command is only available to the bot administrator.",
                color=0xFF6B6B,
            )
            embed.set_footer(text="Created by حَـــــنَـــــا")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Validate prayer name
        valid_prayers = ['fajr', 'dhuhr', 'asr', 'maghrib', 'isha']
        if prayer.lower() not in valid_prayers:
            embed = discord.Embed(
                title="❌ Invalid Prayer",
                description=f"Please choose from: {', '.join(valid_prayers)}",
                color=0xFF6B6B,
            )
            embed.set_footer(text="Created by حَـــــنَـــــا")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Get prayer notifier
        notifier = get_mecca_prayer_notifier()
        if not notifier:
            embed = discord.Embed(
                title="❌ System Error",
                description="Prayer notification system not available.",
                color=0xFF6B6B,
            )
            embed.set_footer(text="Created by حَـــــنَـــــا")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            # Send test notification
            await notifier.send_prayer_notification(prayer.lower(), "18:15")  # Example time
            
            embed = discord.Embed(
                title="✅ Test Successful",
                description=f"Test {prayer.capitalize()} prayer notification sent to daily verse channel!\n"
                           f"🤲 Dua emoji reaction added automatically\n"
                           f"🧹 Other reactions will be automatically removed",
                color=0x1ABC9C,
            )
            embed.set_footer(text="Created by حَـــــنَـــــا")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Test Failed",
                description=f"Error sending notification: {str(e)}",
                color=0xFF6B6B,
            )
            embed.set_footer(text="Created by حَـــــنَـــــا")
            await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    """Set up the test prayer cog"""
    await bot.add_cog(TestPrayerCog(bot)) 