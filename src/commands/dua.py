# =============================================================================
# QuranBot - Dua Commands
# =============================================================================
# Comprehensive dua system with time-based and occasion-based duas
# =============================================================================

from datetime import datetime
import json
from pathlib import Path
import random

import discord
from discord import app_commands
from discord.ext import commands

from src.config import get_config
from src.utils.tree_log import log_error_with_traceback, log_perfect_tree_section


class DuaManager:
    """Manages time-based and occasion-based duas"""

    def __init__(self):
        self.duas_file = Path("data/time_based_duas.json")
        self.duas_data: dict = {}
        self._load_duas()

    def _load_duas(self):
        """Load duas from JSON file"""
        try:
            if self.duas_file.exists():
                with open(self.duas_file, encoding="utf-8") as f:
                    self.duas_data = json.load(f)

                log_perfect_tree_section(
                    "Time-Based Duas - Loaded",
                    [
                        ("file", str(self.duas_file)),
                        ("categories", str(len(self.duas_data))),
                        (
                            "total_duas",
                            str(
                                sum(
                                    len(category)
                                    for category in self.duas_data.values()
                                )
                            ),
                        ),
                        ("status", "✅ Duas loaded successfully"),
                    ],
                    "🤲",
                )
            else:
                log_perfect_tree_section(
                    "Time-Based Duas - File Not Found",
                    [
                        ("file", str(self.duas_file)),
                        ("status", "⚠️ No duas available"),
                        ("action", "Create time_based_duas.json"),
                    ],
                    "⚠️",
                )
        except Exception as e:
            log_error_with_traceback("Error loading time-based duas", e)

    def get_random_dua(self, category: str) -> dict | None:
        """Get a random dua from specified category"""
        if category not in self.duas_data:
            return None

        duas = self.duas_data[category]
        if not duas:
            return None

        return random.choice(duas)

    def get_all_categories(self) -> list[str]:
        """Get all available dua categories"""
        return list(self.duas_data.keys())

    def get_current_time_category(self) -> str:
        """Determine appropriate dua category based on current time"""
        now = datetime.now()
        hour = now.hour

        # Morning duas (5 AM - 11 AM)
        if 5 <= hour < 11:
            return "morning_duas"
        # Evening duas (5 PM - 9 PM)
        elif 17 <= hour < 21:
            return "evening_duas"
        # Friday duas (if it's Friday)
        elif now.weekday() == 4:  # Friday
            return "friday_duas"
        else:
            # Default to general prayer duas
            categories = self.get_all_categories()
            if categories:
                return random.choice(categories)
            return "morning_duas"


class DuaCog(commands.Cog):
    """Dua commands for Islamic supplications"""

    def __init__(self, bot):
        self.bot = bot
        self.dua_manager = DuaManager()

    @app_commands.command(
        name="dua", description="Get a beautiful Islamic dua for different occasions"
    )
    @app_commands.describe(
        category="Type of dua (morning, evening, meal, travel, friday, ramadan, hajj, or random)"
    )
    @app_commands.choices(
        category=[
            app_commands.Choice(name="🌅 Morning Duas", value="morning_duas"),
            app_commands.Choice(name="🌆 Evening Duas", value="evening_duas"),
            app_commands.Choice(name="🍽️ Meal Duas", value="meal_duas"),
            app_commands.Choice(name="✈️ Travel Duas", value="travel_duas"),
            app_commands.Choice(name="🕌 Friday Duas", value="friday_duas"),
            app_commands.Choice(name="🌙 Ramadan Duas", value="ramadan_duas"),
            app_commands.Choice(name="🕋 Hajj Duas", value="hajj_duas"),
            app_commands.Choice(name="🎲 Random Dua", value="random"),
            app_commands.Choice(name="⏰ Time-Appropriate", value="auto"),
        ]
    )
    async def dua(self, interaction: discord.Interaction, category: str = "auto"):
        """Display a beautiful Islamic dua"""

        log_perfect_tree_section(
            "Dua Command - Initiated",
            [
                ("user", f"{interaction.user.display_name} ({interaction.user.id})"),
                ("requested_category", category),
                ("channel", f"#{interaction.channel.name}"),
                ("guild", interaction.guild.name if interaction.guild else "DM"),
            ],
            "🤲",
        )

        try:
            # Determine category
            if category == "auto":
                category = self.dua_manager.get_current_time_category()
            elif category == "random":
                categories = self.dua_manager.get_all_categories()
                if categories:
                    category = random.choice(categories)
                else:
                    category = "morning_duas"

            # Get dua
            dua = self.dua_manager.get_random_dua(category)

            if not dua:
                embed = discord.Embed(
                    title="❌ No Duas Available",
                    description=f"No duas found for category: {category}",
                    color=0xFF6B6B,
                )
                embed.set_footer(text="Created by حَـــــنَـــــا")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Create beautiful embed
            category_emojis = {
                "morning_duas": "🌅",
                "evening_duas": "🌆",
                "meal_duas": "🍽️",
                "travel_duas": "✈️",
                "friday_duas": "🕌",
                "ramadan_duas": "🌙",
                "hajj_duas": "🕋",
            }

            category_emoji = category_emojis.get(category, "🤲")
            category_name = category.replace("_", " ").title().replace("Duas", "Dua")

            embed = discord.Embed(
                title=f"{category_emoji} {dua.get('name', 'Islamic Dua')}",
                description=f"**{category_name}**\n\n"
                f"📿 **From {dua.get('source', 'Islamic Tradition')}:**\n\n"
                f"```{dua['arabic']}```\n\n"
                f"```{dua['english']}```",
                color=0x1ABC9C,
                timestamp=datetime.now(),
            )

            # Add timing information if available
            if dua.get("time"):
                embed.add_field(
                    name="⏰ When to Recite", value=f"```{dua['time']}```", inline=False
                )

            # Set bot thumbnail
            if self.bot.user and self.bot.user.avatar:
                embed.set_thumbnail(url=self.bot.user.avatar.url)

            # Set footer with admin profile picture
            try:
                config = get_config()
                admin_user = await self.bot.fetch_user(config.DEVELOPER_ID)
                if admin_user and admin_user.avatar:
                    embed.set_footer(
                        text="Created by حَـــــنَـــــا", icon_url=admin_user.avatar.url
                    )
                else:
                    embed.set_footer(text="Created by حَـــــنَـــــا")
            except:
                embed.set_footer(text="Created by حَـــــنَـــــا")

            # Send the dua
            await interaction.response.send_message(embed=embed)

            # Add dua emoji reaction
            try:
                message = await interaction.original_response()
                await message.add_reaction("🤲")
            except:
                pass

            # Send notification to enhanced webhook router
            try:
                from src.core.di_container import get_container

                container = get_container()
                if container:
                    enhanced_webhook = container.get("webhook_router")
                    if enhanced_webhook and hasattr(
                        enhanced_webhook, "log_control_panel_interaction"
                    ):
                        await enhanced_webhook.log_control_panel_interaction(
                            interaction_type="dua_command",
                            user_name=interaction.user.display_name,
                            user_id=interaction.user.id,
                            action_performed="/dua command used",
                            user_avatar_url=(
                                interaction.user.avatar.url
                                if interaction.user.avatar
                                else None
                            ),
                            panel_details={
                                "category": category,
                                "dua_name": dua.get("name", "Unknown"),
                                "source": dua.get("source", "Unknown"),
                                "channel": (
                                    f"#{interaction.channel.name}"
                                    if hasattr(interaction.channel, "name")
                                    else "DM"
                                ),
                                "action_type": "Islamic dua requested",
                            },
                        )
            except Exception as e:
                log_error_with_traceback(
                    "Failed to log dua command to enhanced webhook router", e
                )

            log_perfect_tree_section(
                "Dua Command - Success",
                [
                    ("user", interaction.user.display_name),
                    ("category", category),
                    ("dua_name", dua.get("name", "Unknown")),
                    ("source", dua.get("source", "Unknown")),
                    ("status", "✅ Dua displayed successfully"),
                ],
                "🤲",
            )

        except Exception as e:
            log_error_with_traceback("Error in dua command", e)

            embed = discord.Embed(
                title="❌ Error",
                description="An error occurred while retrieving the dua. Please try again.",
                color=0xFF6B6B,
            )
            embed.set_footer(text="Created by حَـــــنَـــــا")

            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    """Set up the dua cog"""
    await bot.add_cog(DuaCog(bot))
