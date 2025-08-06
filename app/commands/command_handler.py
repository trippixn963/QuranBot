"""Command handler for registering slash commands."""

from typing import TYPE_CHECKING

import discord
from discord import app_commands

from ..core.logger import TreeLogger
from .question import question_command


if TYPE_CHECKING:
    from ..bot import QuranBot


class CommandHandler:
    """Handles slash command registration and execution."""

    def __init__(self, bot: "QuranBot"):
        """
        Initialize command handler.

        Args
        ----
            bot: QuranBot instance.

        """
        self.bot = bot
        self.tree = bot.tree

    async def setup_commands(self) -> None:
        """Register all slash commands."""
        try:
            TreeLogger.info("Setting up slash commands", service="CommandHandler")

            # Register question command
            @self.tree.command(
                name="question",
                description="Send an Islamic knowledge quiz manually (Admin only)",
            )
            async def question(interaction: discord.Interaction) -> None:
                """Send a quiz question manually."""
                TreeLogger.debug(
                    "Question slash command invoked",
                    {"user_id": interaction.user.id, "guild_id": interaction.guild_id},
                    service="CommandHandler"
                )
                try:
                    await question_command(interaction, self.bot)
                except Exception as e:
                    TreeLogger.error(
                        "Error in question command wrapper",
                        {"error": str(e), "traceback": True},
                        service="CommandHandler"
                    )
                    try:
                        # Create error embed
                        error_embed = discord.Embed(
                            title="❌ Command Error",
                            description="An error occurred while processing the command. Please try again.",
                            color=0xFF6B6B
                        )
                        
                        # Add bot thumbnail
                        if interaction.client.user and interaction.client.user.avatar:
                            try:
                                error_embed.set_thumbnail(url=interaction.client.user.avatar.url)
                            except:
                                pass
                        
                        # Add developer footer
                        from ..ui.base.components import create_developer_footer
                        footer_text, developer_icon_url = create_developer_footer(
                            interaction.client, interaction.guild
                        )
                        error_embed.set_footer(text=footer_text, icon_url=developer_icon_url)
                        
                        if not interaction.response.is_done():
                            await interaction.response.send_message(
                                embed=error_embed,
                                ephemeral=True
                            )
                        else:
                            await interaction.followup.send(
                                embed=error_embed,
                                ephemeral=True
                            )
                    except:
                        # Fallback to text message if embed fails
                        try:
                            if not interaction.response.is_done():
                                await interaction.response.send_message(
                                    "An error occurred while processing the command.",
                                    ephemeral=True
                                )
                        except:
                            pass

            # Add more commands here as they are created
            # Example:
            # @self.tree.command(name="stats", description="Show quiz statistics")
            # async def stats(interaction: discord.Interaction) -> None:
            #     await stats_command(interaction, self.bot)

            # @self.tree.command(name="leaderboard", description="Show quiz leaderboard")
            # async def leaderboard(interaction: discord.Interaction) -> None:
            #     await leaderboard_command(interaction, self.bot)

            # Sync commands
            synced = await self.tree.sync()
            TreeLogger.info(
                "Slash commands synced successfully",
                {"command_count": len(synced), "commands": [cmd.name for cmd in synced]},
                service="CommandHandler"
            )

        except Exception as e:
            TreeLogger.error(
                "Failed to setup slash commands",
                {"error": str(e), "traceback": True},
                service="CommandHandler",
            )
