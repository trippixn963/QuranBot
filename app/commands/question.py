"""Question command for QuranBot quiz system."""

from typing import TYPE_CHECKING

import discord

from ..config import get_config
from ..core.logger import TreeLogger
from ..ui.quiz import QuizView, create_quiz_embed


if TYPE_CHECKING:
    from ..bot import QuranBot


async def question_command(interaction: discord.Interaction, bot: "QuranBot") -> None:
    """
    Send an Islamic knowledge quiz manually (Admin only).

    Args
    ----
        interaction: Discord interaction.
        bot: QuranBot instance.

    """
    # Log command usage
    TreeLogger.info(
        "Question command initiated",
        {
            "user": f"{interaction.user.display_name} ({interaction.user.id})",
            "guild": interaction.guild.name if interaction.guild else "DM",
            "channel": getattr(interaction.channel, "name", "DM"),
        },
        service="QuestionCommand"
    )
    
    TreeLogger.debug(
        "Question command started",
        {"interaction_id": interaction.id, "user_id": interaction.user.id},
        service="QuestionCommand"
    )

    try:
        # Defer response immediately to avoid timeout
        await interaction.response.defer(ephemeral=True)
        
        TreeLogger.debug(
            "Response deferred early",
            {"interaction_id": interaction.id},
            service="QuestionCommand"
        )
        
        # Check admin permission
        config = get_config()
        if interaction.user.id != config.developer_id:
            TreeLogger.warning(
                "Unauthorized question command attempt",
                {
                    "user_id": interaction.user.id,
                    "required_id": config.developer_id,
                },
                service="QuestionCommand",
            )

            embed = discord.Embed(
                title="❌ Permission Denied",
                description="This command is only available to the bot administrator.",
                color=0xFF6B6B,
            )

            # Add developer footer
            from ..ui.base.components import create_developer_footer
            footer_text, developer_icon_url = create_developer_footer(
                interaction.client, interaction.guild
            )
            embed.set_footer(text=footer_text, icon_url=developer_icon_url)

            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Get quiz service
        TreeLogger.debug(
            "Getting quiz service",
            {"services_available": list(bot.services.keys())},
            service="QuestionCommand"
        )
        quiz_service = bot.services.get("quiz")
        if not quiz_service:
            TreeLogger.error("Quiz service not available", service="QuestionCommand")

            error_embed = discord.Embed(
                title="❌ System Error",
                description="Quiz service is not available. Please try again later.",
                color=0xFF6B6B,
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            return

        # Get quiz channel
        channel_id = 1350540215797940245  # Quiz channel ID
        if not channel_id:
            TreeLogger.error("Quiz channel not configured", service="QuestionCommand")

            error_embed = discord.Embed(
                title="❌ Configuration Error",
                description="Quiz channel is not configured.",
                color=0xFF6B6B,
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            return

        channel = interaction.client.get_channel(channel_id)
        if not channel:
            try:
                channel = await interaction.client.fetch_channel(channel_id)
            except Exception as fetch_error:
                TreeLogger.error(
                    f"Failed to fetch quiz channel: {channel_id}",
                    {
                        "error": str(fetch_error),
                        "channel_id": channel_id,
                        "traceback": True,
                    },
                    service="QuestionCommand",
                )

                error_embed = discord.Embed(
                    title="❌ Channel Error",
                    description="Could not find the quiz channel.",
                    color=0xFF6B6B,
                )
                await interaction.followup.send(embed=error_embed, ephemeral=True)
                return

        # Get random question
        question = await quiz_service.get_random_question()
        if not question:
            TreeLogger.warning("No quiz questions available", service="QuestionCommand")

            error_embed = discord.Embed(
                title="❌ No Questions Available",
                description="No quiz questions are currently available.",
                color=0xFF6B6B,
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            return

        # Create quiz embed and view
        embed = create_quiz_embed(question, bot=interaction.client, guild=interaction.guild)
        view = QuizView(question, quiz_service)
        view.original_embed = embed

        # Send quiz to channel
        try:
            message = await channel.send(embed=embed, view=view)
            view.message = message

            # Start timer
            await view.start_timer()

            # Send DM to admin with answer
            try:
                TreeLogger.debug(
                    "Attempting to fetch admin user for DM",
                    {"developer_id": config.developer_id},
                    service="QuestionCommand",
                )
                
                admin_user = await interaction.client.fetch_user(
                    config.developer_id
                )
                
                TreeLogger.debug(
                    "Admin user fetched successfully",
                    {"admin_user": str(admin_user), "admin_id": admin_user.id},
                    service="QuestionCommand",
                )
                
                if admin_user:
                    # Create answer embed
                    correct_choice = question.get_choice_text(
                        question.correct_answer, "english"
                    )

                    dm_embed = discord.Embed(
                        title="🔑 Quiz Answer",
                        description=(
                            f"The correct answer for the quiz you just sent:\n\n"
                            f"**{question.correct_answer}: {correct_choice}**"
                        ),
                        color=0x00D4AA,
                    )

                    # Add question details
                    dm_embed.add_field(
                        name="📝 Question Details",
                        value=(
                            f"• **Category:** {question.category}\n"
                            f"• **Difficulty:** {'⭐' * question.difficulty}\n"
                            f"• **ID:** {question.id}"
                        ),
                        inline=False,
                    )

                    # Add message link
                    message_link = (
                        f"https://discord.com/channels/"
                        f"{message.guild.id}/{message.channel.id}/{message.id}"
                    )
                    dm_embed.add_field(
                        name="🔗 Go to Question",
                        value=f"[Click here to jump to the quiz]({message_link})",
                        inline=False,
                    )

                    # Add explanation if available
                    explanation = question.get_explanation_text("english")
                    if explanation:
                        dm_embed.add_field(
                            name="📚 Explanation", value=explanation, inline=False
                        )

                    dm_embed.set_footer(text="Created by حَنَّا")

                    await admin_user.send(embed=dm_embed)

                    TreeLogger.info(
                        "Answer DM sent to admin",
                        {"question_id": question.id, "admin_id": admin_user.id},
                        service="QuestionCommand",
                    )

            except discord.Forbidden:
                TreeLogger.error(
                    "Could not send DM to admin (DMs may be disabled)",
                    {"admin_id": config.developer_id, "error": "Forbidden"},
                    service="QuestionCommand",
                )
            except Exception as e:
                TreeLogger.error(
                    "Failed to send answer DM",
                    {"error": str(e), "admin_id": config.developer_id, "traceback": True},
                    service="QuestionCommand",
                )

            # Send success confirmation
            success_embed = discord.Embed(
                title="✅ Quiz Sent Successfully",
                description=(
                    f"Quiz has been sent to {channel.mention}.\n\n"
                    f"**Question Details:**\n"
                    f"• Category: {question.category}\n"
                    f"• **Difficulty:** {'⭐' * question.difficulty}\n"
                    f"• Timer: 60 seconds\n"
                    f"• Answer DM: Sent to your DMs"
                ),
                color=0x00D4AA,
            )
            await interaction.followup.send(embed=success_embed, ephemeral=True)

            TreeLogger.info(
                "Quiz delivered successfully",
                {
                    "channel": channel.name,
                    "question_id": question.id,
                    "category": question.category,
                    "difficulty": question.difficulty,
                    "user_id": interaction.user.id,
                },
                service="QuestionCommand",
            )

        except discord.Forbidden:
            TreeLogger.error(
                "No permission to send in quiz channel",
                {"channel_id": channel.id},
                service="QuestionCommand",
            )

            error_embed = discord.Embed(
                title="❌ Permission Error",
                description="Bot doesn't have permission to send messages in the quiz channel.",
                color=0xFF6B6B,
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)

        except Exception as e:
            TreeLogger.error(
                "Failed to send quiz",
                {"error": str(e), "traceback": True},
                service="QuestionCommand",
            )

            error_embed = discord.Embed(
                title="❌ Delivery Error",
                description="Failed to send the quiz. Please try again.",
                color=0xFF6B6B,
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)

    except Exception as e:
        TreeLogger.error(
            "Unexpected error in question command",
            {"error": str(e), "user_id": interaction.user.id, "traceback": True},
            service="QuestionCommand",
        )

        try:
            error_embed = discord.Embed(
                title="❌ Unexpected Error",
                description="An unexpected error occurred. Please try again later.",
                color=0xFF6B6B,
            )

            # Since we always defer early, use followup
            await interaction.followup.send(embed=error_embed, ephemeral=True)
        except Exception:
            pass
