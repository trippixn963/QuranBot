#!/usr/bin/env python3
# =============================================================================
# QuranBot - Question Command (Cog)
# =============================================================================
# Allows admins to manually trigger Islamic knowledge quizzes using Discord.py Cogs
# Mirrors the functionality of /verse command
# =============================================================================

from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from src.config import get_config
from src.utils.quiz_manager import QuizView
from src.utils.tree_log import log_error_with_traceback, log_perfect_tree_section

# =============================================================================
# Utility Functions
# =============================================================================


def get_daily_verses_manager():
    """Get daily verses manager instance"""
    try:
        from src.utils.daily_verses import DailyVersesManager

        return DailyVersesManager()
    except ImportError:
        # Fallback if daily verses module is not available
        return None
    except Exception as e:
        log_error_with_traceback("Failed to create daily verses manager", e)
        return None


def get_quiz_manager():
    """Get quiz manager instance"""
    try:
        from pathlib import Path

        from src.utils.quiz_manager import QuizManager

        # Use the data directory from the project root
        data_dir = Path(__file__).parent.parent.parent / "data"
        return QuizManager(data_dir)
    except ImportError:
        # Fallback if quiz manager module is not available
        return None
    except Exception as e:
        log_error_with_traceback("Failed to create quiz manager", e)
        return None


# =============================================================================
# Question Cog
# =============================================================================


class QuestionCog(commands.Cog):
    """Question command cog for manual quiz delivery"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="question",
        description="Send an Islamic knowledge quiz manually and reset the timer (Admin only)",
    )
    async def question(self, interaction: discord.Interaction):
        """
        Administrative command to manually trigger quiz delivery.

        This is an open source implementation demonstrating proper Discord
        slash command structure with permission handling, error management,
        and user feedback.

        Features:
        - Admin-only access control
        - Interactive quiz with multiple choice buttons
        - Automatic timer (60 seconds)
        - Results tracking and statistics
        - Comprehensive error handling

        Usage:
        /question - Manually trigger quiz delivery (admin only)
        """

        # Log command initiation
        log_perfect_tree_section(
            "Question Command - Initiated",
            [
                ("user", f"{interaction.user.display_name} ({interaction.user.id})"),
                ("guild", f"{interaction.guild.name}" if interaction.guild else "DM"),
                (
                    "channel",
                    (
                        f"#{interaction.channel.name}"
                        if hasattr(interaction.channel, "name")
                        else "DM"
                    ),
                ),
                ("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                ("status", "🔄 Starting question command execution"),
            ],
            "❓",
        )

        try:
            # Get configuration
            config = get_config()

            # Check if user is the developer/admin
            if interaction.user.id != config.DEVELOPER_ID:
                log_perfect_tree_section(
                    "Question Command - Permission Denied",
                    [
                        (
                            "user",
                            f"{interaction.user.display_name} ({interaction.user.id})",
                        ),
                        ("required_id", str(config.DEVELOPER_ID)),
                        ("status", "❌ Unauthorized access attempt"),
                        ("action", "🚫 Command execution denied"),
                    ],
                    "🔒",
                )

                embed = discord.Embed(
                    title="❌ Permission Denied",
                    description="This command is only available to the bot administrator.",
                    color=0xFF6B6B,
                )

                try:
                    admin_user = await interaction.client.fetch_user(
                        config.DEVELOPER_ID
                    )
                    if admin_user and admin_user.avatar:
                        embed.set_footer(
                            text="Created by حَـــــنَّـــــا",
                            icon_url=admin_user.avatar.url,
                        )
                    else:
                        embed.set_footer(text="Created by حَـــــنَّـــــا")
                except Exception:
                    embed.set_footer(text="Created by حَـــــنَّـــــا")

                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Log authorized access
            log_perfect_tree_section(
                "Question Command - Authorized Access",
                [
                    (
                        "user",
                        f"{interaction.user.display_name} ({interaction.user.id})",
                    ),
                    ("permission_level", "✅ Administrator"),
                    ("status", "🔓 Access granted"),
                    ("action", "🚀 Proceeding with quiz delivery"),
                ],
                "🔓",
            )

            # Get quiz manager
            quiz_manager = get_quiz_manager()
            if not quiz_manager:
                log_perfect_tree_section(
                    "Question Command - Critical Error",
                    [
                        ("error", "❌ Failed to get quiz_manager"),
                        (
                            "user",
                            f"{interaction.user.display_name} ({interaction.user.id})",
                        ),
                        ("status", "🚨 Command execution aborted"),
                    ],
                    "⚠️",
                )

                error_embed = discord.Embed(
                    title="❌ System Error",
                    description="Critical system error: Quiz manager unavailable. Please contact the administrator.",
                    color=0xFF6B6B,
                )
                await interaction.response.send_message(
                    embed=error_embed, ephemeral=True
                )
                return

            # Send acknowledgment
            ack_embed = discord.Embed(
                title="❓ Processing Question Command",
                description="Processing your question request...",
                color=0x3498DB,
            )
            ack_embed.set_footer(text="Created by حَـــــنَّـــــا")
            await interaction.response.send_message(embed=ack_embed, ephemeral=True)

            # Get the channel
            try:
                channel_id = config.DAILY_VERSE_CHANNEL_ID
                if not channel_id:
                    raise ValueError("DAILY_VERSE_CHANNEL_ID not configured")

                channel = interaction.client.get_channel(channel_id)
                if not channel:
                    channel = await interaction.client.fetch_channel(channel_id)

                if not channel:
                    raise ValueError(f"Channel {channel_id} not found")

            except Exception as e:
                log_error_with_traceback("Failed to get quiz channel", e)

                error_embed = discord.Embed(
                    title="❌ Channel Error",
                    description="Could not find the quiz channel. Please check the bot configuration.",
                    color=0xFF6B6B,
                )
                await interaction.followup.send(embed=error_embed, ephemeral=True)
                return

            # Get a random question
            question_data = quiz_manager.get_random_question()

            if not question_data:
                log_perfect_tree_section(
                    "Question Command - No Questions Available",
                    [
                        ("error", "❌ No questions available"),
                        ("status", "🚨 Command execution failed"),
                    ],
                    "⚠️",
                )

                error_embed = discord.Embed(
                    title="❌ No Questions Available",
                    description="No questions are currently available in the system.",
                    color=0xFF6B6B,
                )
                await interaction.followup.send(embed=error_embed, ephemeral=True)
                return

            # Update the last sent time to reset the timer
            try:
                quiz_manager.update_last_sent_time()
            except Exception as e:
                log_error_with_traceback("Failed to update last sent question", e)

            # Log question selection
            log_perfect_tree_section(
                "Question Command - Question Selected",
                [
                    ("question_id", question_data.get("id", "Unknown")),
                    ("category", question_data.get("category", "Unknown")),
                    ("difficulty", question_data.get("difficulty", "Unknown")),
                    ("status", "✅ Question selected successfully"),
                ],
                "❓",
            )

            # Create question embed
            embed = discord.Embed(
                title="❓ Islamic Knowledge Quiz",
                color=0x00D4AA,
            )

            # Add spacing before question
            embed.add_field(
                name="\u200b",  # Invisible character for spacing
                value="",
                inline=False,
            )

            # Add the Arabic question first at the very top
            question_text = question_data.get("question", "Unknown question")
            if isinstance(question_text, dict):
                arabic_text = question_text.get("arabic", "")
                english_text = question_text.get("english", "")

                if arabic_text:
                    embed.add_field(
                        name="🕌 **Question**",
                        value=f"```\n{arabic_text}\n```",
                        inline=False,
                    )

                # Add English translation right after Arabic (if both exist)
                if english_text:
                    embed.add_field(
                        name="📖 **Translation**",
                        value=f"```\n{english_text}\n```",
                        inline=False,
                    )
            else:
                # If it's just a string, display it as the question
                embed.add_field(
                    name="❓ **Question**",
                    value=f"```\n{question_text!s}\n```",
                    inline=False,
                )

            # Add spacing after English question
            embed.add_field(
                name="\u200b",  # Invisible character for spacing
                value="",
                inline=False,
            )

            # Add category and difficulty after the questions
            embed.add_field(
                name="📚 Category",
                value=question_data.get("category", "General"),
                inline=True,
            )

            # Handle difficulty - convert numbers to stars
            difficulty_value = question_data.get("difficulty", "Medium")
            if str(difficulty_value).isdigit():
                difficulty_num = int(difficulty_value)
                if 1 <= difficulty_num <= 5:
                    difficulty_display = "⭐" * difficulty_num
                else:
                    difficulty_display = str(difficulty_value)
            else:
                difficulty_display = str(difficulty_value)

            embed.add_field(
                name="⭐ Difficulty",
                value=difficulty_display,
                inline=True,
            )

            # Add timer placeholder (will be updated by QuizView)
            embed.add_field(
                name="⏰ Timer",
                value="Starting...",
                inline=True,
            )

            # Add spacing after category/difficulty/timer section
            embed.add_field(
                name="\u200b",  # Invisible character for spacing
                value="",
                inline=False,
            )

            # Add choices with English first, then Arabic in code blocks
            choices = question_data.get("choices", {})
            choice_text = ""
            for letter in ["A", "B", "C", "D", "E", "F"]:
                if letter in choices:
                    choice_data = choices[letter]
                    if isinstance(choice_data, dict):
                        english_choice = choice_data.get("english", "")
                        arabic_choice = choice_data.get("arabic", "")

                        if english_choice and arabic_choice:
                            choice_text += f"**{letter}.** {english_choice}\n```\n{arabic_choice}\n```\n\n"
                        elif english_choice:
                            choice_text += f"**{letter}.** {english_choice}\n\n"
                        elif arabic_choice:
                            choice_text += (
                                f"**{letter}.** ```\n{arabic_choice}\n```\n\n"
                            )
                    else:
                        choice_text += f"**{letter}.** {choice_data}\n\n"

            if choice_text:
                embed.add_field(
                    name="**Answers:**",
                    value=choice_text.strip(),
                    inline=False,
                )

            # Add spacing after answers section
            embed.add_field(
                name="\u200b",  # Invisible character for spacing
                value="",
                inline=False,
            )

            # Set bot profile picture as thumbnail
            try:
                if interaction.client.user and interaction.client.user.avatar:
                    embed.set_thumbnail(url=interaction.client.user.avatar.url)
            except Exception:
                pass

            # Set footer with admin profile picture
            try:
                admin_user = await interaction.client.fetch_user(config.DEVELOPER_ID)
                if admin_user and admin_user.avatar:
                    embed.set_footer(
                        text="Created by حَـــــنَّـــــا",
                        icon_url=admin_user.avatar.url,
                    )
                else:
                    embed.set_footer(text="Created by حَـــــنَّـــــا")
            except Exception:
                embed.set_footer(text="Created by حَـــــنَّـــــا")

            # Create quiz view with quiz manager instance for score tracking
            correct_answer = question_data.get("correct_answer", "A")
            view = QuizView(correct_answer, question_data, quiz_manager)
            view.original_embed = embed

            # Send the quiz
            try:
                message = await channel.send(embed=embed, view=view)
                view.message = message

                # Start the timer
                await view.start_timer()

                # Send answer DM to admin
                try:
                    admin_user = await interaction.client.fetch_user(
                        config.DEVELOPER_ID
                    )
                    if admin_user:
                        # Create answer embed for DM
                        choices = question_data.get("choices", {})
                        correct_choice = choices.get(correct_answer, "Unknown")

                        # Format the correct answer
                        if isinstance(correct_choice, dict):
                            english_text = correct_choice.get("english", "")
                            arabic_text = correct_choice.get("arabic", "")

                            if english_text and arabic_text:
                                answer_display = f"**{correct_answer}: {english_text}**\n{arabic_text}"
                            elif english_text:
                                answer_display = f"**{correct_answer}: {english_text}**"
                            elif arabic_text:
                                answer_display = f"**{correct_answer}:** {arabic_text}"
                            else:
                                answer_display = (
                                    f"**{correct_answer}:** Answer not available"
                                )
                        else:
                            answer_display = f"**{correct_answer}: {correct_choice!s}**"

                        dm_embed = discord.Embed(
                            title="🔑 Quiz Answer",
                            description=f"The correct answer for the quiz you just sent:\n\n{answer_display}",
                            color=0x00D4AA,
                        )

                        # Add question details
                        dm_embed.add_field(
                            name="📝 Question Details",
                            value=f"• **Category:** {question_data.get('category', 'Unknown')}\n• **Difficulty:** {question_data.get('difficulty', 'Unknown')}\n• **ID:** {question_data.get('id', 'Unknown')}",
                            inline=False,
                        )

                        # Add message link for easy navigation
                        message_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
                        dm_embed.add_field(
                            name="🔗 Go to Question",
                            value=f"[Click here to jump to the quiz]({message_link})",
                            inline=False,
                        )

                        dm_embed.set_footer(text="Created by حَـــــنَّـــــا")

                        await admin_user.send(embed=dm_embed)

                        log_perfect_tree_section(
                            "Question Command - Answer DM Sent",
                            [
                                (
                                    "recipient",
                                    f"{admin_user.display_name} ({admin_user.id})",
                                ),
                                ("question_id", question_data.get("id", "Unknown")),
                                ("correct_answer", correct_answer),
                                ("status", "✅ Answer DM sent successfully"),
                            ],
                            "📩",
                        )
                except Exception as e:
                    log_error_with_traceback("Failed to send answer DM to admin", e)

                # Send confirmation to admin
                try:
                    success_embed = discord.Embed(
                        title="✅ Quiz Sent Successfully",
                        description=f"Quiz has been sent to {channel.mention}.\n\n**Question Details:**\n• Category: {question_data.get('category', 'Unknown')}\n• Difficulty: {question_data.get('difficulty', 'Unknown')}\n• Timer: 60 seconds\n• Quiz Timer: Reset\n• Answer DM: Sent to your DMs",
                        color=0x00D4AA,
                    )
                    await interaction.followup.send(embed=success_embed, ephemeral=True)
                except Exception as e:
                    log_error_with_traceback(
                        "Failed to send confirmation message to admin", e
                    )

                # Log successful quiz delivery
                log_perfect_tree_section(
                    "Question Command - Success",
                    [
                        (
                            "user",
                            f"{interaction.user.display_name} ({interaction.user.id})",
                        ),
                        ("channel", f"#{channel.name}"),
                        ("question_id", question_data.get("id", "Unknown")),
                        ("category", question_data.get("category", "Unknown")),
                        ("difficulty", question_data.get("difficulty", "Unknown")),
                        ("message_id", message.id),
                        ("timer_duration", "60 seconds"),
                        ("status", "✅ Quiz delivered successfully"),
                    ],
                    "🏆",
                )

                # Send success notification to enhanced webhook router first
                try:
                    from src.core.di_container import get_container

                    container = get_container()
                    if container:
                        enhanced_webhook = container.get("enhanced_webhook_router")
                        if enhanced_webhook and hasattr(
                            enhanced_webhook, "log_quiz_event"
                        ):
                            await enhanced_webhook.log_quiz_event(
                                event_type="sent",
                                user_name=interaction.user.display_name,
                                user_id=interaction.user.id,
                                question_text=question_data.get("question", "Unknown question"),
                                user_avatar_url=(
                                    interaction.user.avatar.url
                                    if interaction.user.avatar
                                    else None
                                ),
                                quiz_details={
                                    "question_category": question_data.get(
                                        "category", "Unknown"
                                    ),
                                    "question_difficulty": question_data.get(
                                        "difficulty", "Unknown"
                                    ),
                                    "question_id": str(
                                        question_data.get("id", "Unknown")
                                    ),
                                    "channel": f"#{channel.name}",
                                    "message_id": str(message.id),
                                    "timer_duration": "60 seconds",
                                    "quiz_type": "Manual Quiz",
                                    "triggered_by": "admin_command",
                                },
                            )
                except Exception as e:
                    log_error_with_traceback(
                        "Failed to log to enhanced webhook router", e
                    )
                    # No fallback - enhanced webhook router is the primary logging method

            except discord.Forbidden:
                log_error_with_traceback(
                    "Permission denied when sending quiz to channel",
                    Exception("Bot lacks permission to send messages in the channel"),
                )
                error_embed = discord.Embed(
                    title="❌ Permission Error",
                    description="Bot doesn't have permission to send messages in the quiz channel.",
                    color=0xFF6B6B,
                )
                await interaction.followup.send(embed=error_embed, ephemeral=True)

            except Exception as e:
                log_error_with_traceback("Failed to create or send quiz embed", e)

                log_perfect_tree_section(
                    "Question Command - Delivery Failed",
                    [
                        (
                            "user",
                            f"{interaction.user.display_name} ({interaction.user.id})",
                        ),
                        ("error", str(e)),
                        ("status", "❌ Failed to deliver quiz"),
                    ],
                    "💥",
                )

                error_embed = discord.Embed(
                    title="❌ Delivery Error",
                    description="Failed to send the quiz. Please try again or contact the administrator.",
                    color=0xFF6B6B,
                )
                await interaction.followup.send(embed=error_embed, ephemeral=True)

        except Exception as e:
            log_error_with_traceback("Error in question command", e)

            log_perfect_tree_section(
                "Question Command - Unexpected Error",
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
                    description="An unexpected error occurred while processing the question command. Please try again later.",
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


# =============================================================================
# Cog Setup
# =============================================================================


async def setup(bot, container=None):
    """Set up the Question cog with comprehensive error handling and logging"""
    try:
        log_perfect_tree_section(
            "Question Cog Setup - Starting",
            [
                ("cog_name", "QuestionCog"),
                ("command_name", "/question"),
                ("status", "🔄 Initializing question cog setup"),
            ],
            "🚀",
        )

        await bot.add_cog(QuestionCog(bot))

        log_perfect_tree_section(
            "Question Cog Setup - Complete",
            [
                ("status", "✅ Question cog loaded successfully"),
                ("cog_name", "QuestionCog"),
                ("command_name", "/question"),
                ("description", "Send Islamic knowledge quiz manually"),
                ("permission_level", "🔒 Admin only"),
                ("features", "📝 Interactive quiz with 60s timer"),
                ("error_handling", "✅ Comprehensive traceback and logging"),
                ("tree_logging", "✅ Perfect tree logging implemented"),
            ],
            "❓",
        )

    except Exception as setup_error:
        log_error_with_traceback("Failed to set up question cog", setup_error)

        log_perfect_tree_section(
            "Question Cog Setup - Failed",
            [
                ("error_type", type(setup_error).__name__),
                ("status", "❌ Failed to load question cog"),
                ("impact", "🚨 /question command will not be available"),
            ],
            "💥",
        )

        # Re-raise the exception to ensure the bot startup process is aware of the failure
        raise


# =============================================================================
# Export Functions (for backward compatibility)
# =============================================================================

__all__ = [
    "QuestionCog",
    "get_daily_verses_manager",
    "get_quiz_manager",
    "setup",
]
