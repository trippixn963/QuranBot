"""
Ask Islam Command - Islamic AI Assistant

Provides AI-powered Islamic knowledge assistance with proper disclaimers.
"""

from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from src.config import get_config_service
from src.core.di_container import DIContainer
from src.core.structured_logger import (
    log_error_with_traceback,
    log_perfect_tree_section,
)
from src.services.islamic_ai_service import get_islamic_ai_service


class AskIslamCog(commands.Cog):
    """Discord command cog for Islamic AI assistance"""

    def __init__(self, bot: commands.Bot, container: DIContainer):
        self.bot = bot
        self.container = container
        self.config = get_config_service().config

    @app_commands.command(
        name="ask-islam",
        description="Ask questions about Islam - Get AI-powered Islamic knowledge with proper disclaimers"
    )
    @app_commands.describe(
        question="Your Islamic question (be specific for better answers)"
    )
    async def ask_islam(self, interaction: discord.Interaction, question: str):
        """
        Islamic AI Assistant Command

        Provides AI-powered Islamic knowledge with proper religious disclaimers.
        Rate limited to 5 questions per 10 minutes per user.

        Examples:
        /ask-islam question:What are the 5 pillars of Islam?
        /ask-islam question:How do I perform Wudu correctly?
        /ask-islam question:What is the significance of Ramadan?
        """

        # Log command initiation
        log_perfect_tree_section(
            "Ask Islam Command - Initiated",
            [
                ("user", f"{interaction.user.display_name} ({interaction.user.id})"),
                ("question_length", str(len(question))),
                ("question_preview", question[:50] + "..." if len(question) > 50 else question),
                ("timestamp", interaction.created_at.strftime("%Y-%m-%d %H:%M:%S")),
            ],
            "🤖",
        )

        try:
            # Defer response (AI processing may take time)
            await interaction.response.defer(thinking=True)

            # Get AI service
            ai_service = await get_islamic_ai_service()

            if ai_service.client is None:
                embed = discord.Embed(
                    title="🚫 Service Unavailable",
                    description="The Islamic AI assistant is currently unavailable. Please try again later.",
                    color=0xFF6B6B,
                )
                embed.set_footer(text="Created by حَـــــنَـــــا")
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Check rate limit
            rate_status = ai_service.get_rate_limit_status(interaction.user.id)
            if rate_status["requests_remaining"] <= 0:
                reset_time = rate_status.get("reset_time", 0)
                embed = discord.Embed(
                    title="⏰ Rate Limit Reached",
                    description=f"You've reached the limit of 5 questions per 10 minutes.\n"
                               f"Please wait **{reset_time // 60}m {reset_time % 60}s** before asking again.",
                    color=0xFFA500,
                )
                embed.add_field(
                    name="🔄 Rate Limit Info",
                    value="```• 5 questions per 10 minutes\n"
                          "• Helps ensure quality responses\n"
                          "• Resets automatically```",
                    inline=False
                )
                embed.set_footer(text="Created by حَـــــنَـــــا")
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Process question through AI
            success, ai_response, error_message = await ai_service.ask_question(
                interaction.user.id, question
            )

            if not success:
                embed = discord.Embed(
                    title="❌ Error Processing Question",
                    description=error_message or "An unexpected error occurred. Please try again.",
                    color=0xFF6B6B,
                )
                embed.set_footer(text="Created by حَـــــنَـــــا")
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Create beautiful response embed
            embed = discord.Embed(
                title="🤖 Islamic AI Assistant",
                description=ai_response,
                color=0x1ABC9C,
                timestamp=interaction.created_at
            )

            # Add question field
            question_display = question if len(question) <= 100 else question[:97] + "..."
            embed.add_field(
                name="❓ Your Question",
                value=f"```{question_display}```",
                inline=False
            )

            # Add important disclaimer
            embed.add_field(
                name="⚠️ Important Disclaimer",
                value="```This is AI-generated Islamic guidance. For important religious matters, "
                      "always consult qualified Islamic scholars, your local imam, or trusted religious authorities.```",
                inline=False
            )

            # Add rate limit status
            updated_rate_status = ai_service.get_rate_limit_status(interaction.user.id)
            embed.add_field(
                name="📊 Usage Status",
                value=f"```Questions remaining: {updated_rate_status['requests_remaining']}/5```",
                inline=True
            )

            # Set bot thumbnail
            if self.bot.user and self.bot.user.avatar:
                embed.set_thumbnail(url=self.bot.user.avatar.url)

            # Set footer with admin profile picture
            try:
                admin_user = await self.bot.fetch_user(self.config.DEVELOPER_ID)
                if admin_user and admin_user.avatar:
                    embed.set_footer(
                        text="Created by حَـــــنَـــــا • AI-Powered Islamic Guidance",
                        icon_url=admin_user.avatar.url,
                    )
                else:
                    embed.set_footer(text="Created by حَـــــنَـــــا • AI-Powered Islamic Guidance")
            except (discord.HTTPException, discord.NotFound, AttributeError):
                embed.set_footer(text="Created by حَـــــنَـــــا • AI-Powered Islamic Guidance")

            # Send response
            await interaction.followup.send(embed=embed)

            # Log successful response
            log_perfect_tree_section(
                "Ask Islam Command - Success",
                [
                    ("user", f"{interaction.user.display_name} ({interaction.user.id})"),
                    ("response_length", str(len(ai_response))),
                    ("questions_remaining", str(updated_rate_status['requests_remaining'])),
                    ("status", "✅ AI response delivered"),
                ],
                "✅",
            )

        except Exception as e:
            log_error_with_traceback("Ask Islam command error", e)

            try:
                embed = discord.Embed(
                    title="❌ Unexpected Error",
                    description="An unexpected error occurred while processing your question. Please try again later.",
                    color=0xFF6B6B,
                )
                embed.set_footer(text="Created by حَـــــنَـــــا")

                if interaction.response.is_done():
                    await interaction.followup.send(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                # If even error handling fails, log it
                log_error_with_traceback("Failed to send error message in ask_islam command", e)


async def setup(bot: commands.Bot, container: DIContainer):
    """Set up the Ask Islam command cog"""
    try:
        cog = AskIslamCog(bot, container)
        await bot.add_cog(cog)

        log_perfect_tree_section(
            "Ask Islam Command - Loaded",
            [
                ("command", "/ask-islam"),
                ("ai_model", "GPT-3.5 Turbo"),
                ("rate_limit", "5 questions/10min"),
                ("disclaimers", "✅ Implemented"),
                ("status", "🤖 Ready for Islamic guidance"),
            ],
            "📚",
        )

    except Exception as e:
        log_error_with_traceback("Failed to load Ask Islam command", e)
