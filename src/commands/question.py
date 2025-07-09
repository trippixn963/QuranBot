#!/usr/bin/env python3
# =============================================================================
# QuranBot - Question Command
# =============================================================================
# Allows admins to manually trigger Islamic knowledge quizzes
# Mirrors the functionality of /verse command
# =============================================================================

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import discord
from discord import app_commands

from src.utils.tree_log import log_error_with_traceback, log_perfect_tree_section


# Get the daily verses manager through a function instead of global import
def get_daily_verses_manager():
    """Get the daily verses manager instance"""
    try:
        from src.utils.daily_verses import daily_verses_manager

        return daily_verses_manager
    except Exception as e:
        log_error_with_traceback("Failed to import daily_verses_manager", e)
        return None


@app_commands.command(
    name="question",
    description="Send an Islamic knowledge quiz manually and reset the timer (Admin only)",
)
async def question_slash_command(interaction: discord.Interaction):
    """
    Manually trigger an Islamic knowledge quiz
    Only usable by the bot administrator
    Mirrors /verse command functionality
    """
    try:
        # Get the daily verses manager with error handling
        daily_verses_manager = get_daily_verses_manager()
        if not daily_verses_manager:
            log_perfect_tree_section(
                "Question Command - Critical Error",
                [
                    ("error", "❌ Failed to get daily_verses_manager"),
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
                description="Critical system error: Quiz system unavailable. Please contact the administrator.",
                color=0xFF6B6B,
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return

        # Get developer ID from environment with error handling
        try:
            DEVELOPER_ID = int(os.getenv("DEVELOPER_ID") or "0")
            if DEVELOPER_ID == 0:
                raise ValueError("DEVELOPER_ID not set in environment")
        except (ValueError, TypeError) as e:
            log_error_with_traceback("Failed to get DEVELOPER_ID from environment", e)

            log_perfect_tree_section(
                "Question Command - Configuration Error",
                [
                    ("error", "❌ DEVELOPER_ID not configured"),
                    (
                        "user",
                        f"{interaction.user.display_name} ({interaction.user.id})",
                    ),
                    ("status", "🚨 Command execution aborted"),
                ],
                "⚠️",
            )

            error_embed = discord.Embed(
                title="❌ Configuration Error",
                description="Bot configuration error: Developer ID not set. Please contact the administrator.",
                color=0xFF6B6B,
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return

        # Check if user is the developer/admin
        if interaction.user.id != DEVELOPER_ID:
            log_perfect_tree_section(
                "Question Command - Permission Denied",
                [
                    (
                        "user",
                        f"{interaction.user.display_name} ({interaction.user.id})",
                    ),
                    ("required_id", str(DEVELOPER_ID)),
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

            # Set footer with admin profile picture with error handling
            try:
                admin_user = await interaction.client.fetch_user(DEVELOPER_ID)
                if admin_user and admin_user.avatar:
                    embed.set_footer(
                        text="Created by حَـــــنَـــــا", icon_url=admin_user.avatar.url
                    )
                else:
                    embed.set_footer(text="Created by حَـــــنَـــــا")
            except Exception as avatar_error:
                log_error_with_traceback(
                    "Failed to fetch admin avatar for permission denied message",
                    avatar_error,
                )
                embed.set_footer(text="Created by حَـــــنَـــــا")

            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Log successful authentication
        log_perfect_tree_section(
            "Question Command - Authentication Success",
            [
                ("user", f"{interaction.user.display_name} ({interaction.user.id})"),
                ("permission_level", "🔓 Admin verified"),
                ("status", "✅ Authentication passed"),
            ],
            "🔐",
        )

        # Check if quiz system is configured
        quiz_manager = daily_verses_manager.quiz_manager
        if not quiz_manager or not quiz_manager.quiz_channel_id:
            log_perfect_tree_section(
                "Question Command - System Not Configured",
                [
                    (
                        "quiz_manager",
                        "❌ Not initialized" if not quiz_manager else "✅ Initialized",
                    ),
                    (
                        "channel_id",
                        (
                            "❌ Not set"
                            if not quiz_manager.quiz_channel_id
                            else f"✅ {quiz_manager.quiz_channel_id}"
                        ),
                    ),
                    ("status", "🚨 Quiz system not properly configured"),
                ],
                "⚠️",
            )

            embed = discord.Embed(
                title="❌ Quiz System Not Configured",
                description="The quiz system is not properly configured. Please check the bot configuration.",
                color=0xFF6B6B,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Get the channel
        channel = interaction.guild.get_channel(quiz_manager.quiz_channel_id)
        if not channel:
            log_perfect_tree_section(
                "Question Command - Channel Not Found",
                [
                    ("channel_id", str(quiz_manager.quiz_channel_id)),
                    ("status", "❌ Channel not accessible"),
                ],
                "❌",
            )

            embed = discord.Embed(
                title="❌ Channel Not Found",
                description="Could not access the quiz channel. Please check the configuration.",
                color=0xFF6B6B,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Get a random challenging question
        question = quiz_manager.get_random_question()
        if not question:
            log_perfect_tree_section(
                "Question Command - No Questions Available",
                [
                    ("error", "❌ No questions available"),
                    ("status", "🚨 Command execution failed"),
                ],
                "⚠️",
            )

            embed = discord.Embed(
                title="❌ No Questions Available",
                description="No questions are currently available in the system.",
                color=0xFF6B6B,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Create and send the quiz
        embed = await quiz_manager.create_quiz_embed(question)
        view = quiz_manager.create_quiz_view(question["correct_answer"])

        # Send the quiz
        message = await channel.send(embed=embed, view=view)
        view.message = message
        quiz_manager.current_quiz_message_id = message.id  # Store the message ID

        # Store message for timer updates and start timer task
        quiz_manager.current_quiz_message = message
        from datetime import datetime, timezone

        quiz_manager.current_quiz_start_time = datetime.now(timezone.utc)

        # Start timer update task
        import asyncio

        if hasattr(quiz_manager, "timer_task") and quiz_manager.timer_task:
            quiz_manager.timer_task.cancel()
        quiz_manager.timer_task = asyncio.create_task(
            quiz_manager.update_quiz_timer(
                message, view, quiz_manager.current_quiz_start_time
            )
        )

        # Update stats
        quiz_manager.quiz_stats["total_questions"] += 1
        quiz_manager.save_stats()

        # Reset the quiz timer
        quiz_manager.reset_timer()

        # Calculate next quiz time
        next_quiz_time = quiz_manager.get_next_quiz_time()

        # Create confirmation embed
        confirmation_embed = discord.Embed(
            title="✅ Quiz Question Sent Successfully",
            description=f"**{question['category']} Quiz** has been sent to {channel.mention}",
            color=0x00D4AA,
        )

        if next_quiz_time:
            confirmation_embed.add_field(
                name="🔄 Timer Reset",
                value=f"Next automatic quiz will be sent in **3 hours**\n*Around {next_quiz_time.strftime('%I:%M %p')} EST*",
                inline=False,
            )
        else:
            confirmation_embed.add_field(
                name="🔄 Timer Reset",
                value="Next automatic quiz will be sent in **3 hours**\n*Time calculation failed - check logs*",
                inline=False,
            )

        # Show message ID and coordination info
        confirmation_embed.add_field(
            name="📨 Message ID",
            value=f"**[{message.id}](https://discord.com/channels/{channel.guild.id}/{channel.id}/{message.id})**\nQuiz message in {channel.mention}",
            inline=True,
        )

        # Set footer with admin profile picture
        try:
            admin_user = await interaction.client.fetch_user(DEVELOPER_ID)
            if admin_user and admin_user.avatar:
                confirmation_embed.set_footer(
                    text="Created by حَـــــنَـــــا",
                    icon_url=admin_user.avatar.url,
                )
            else:
                confirmation_embed.set_footer(text="Created by حَـــــنَـــــا")
        except Exception as avatar_error:
            log_error_with_traceback(
                "Failed to fetch admin avatar for confirmation message",
                avatar_error,
            )
            confirmation_embed.set_footer(text="Created by حَـــــنَـــــا")

        # Send confirmation
        await interaction.response.send_message(
            embed=confirmation_embed,
            ephemeral=True,
        )

        # Log the successful manual quiz sending
        log_perfect_tree_section(
            "Question Command - Execution Complete",
            [
                (
                    "triggered_by",
                    f"{interaction.user.display_name} ({interaction.user.id})",
                ),
                ("developer_verified", "✅ Developer permission confirmed"),
                ("channel", f"#{channel.name} ({channel.id})"),
                ("question_id", question.get("id", "unknown")),
                ("category", question["category"]),
                ("difficulty", "⭐" * question["difficulty"]),
                ("message_id", str(message.id)),
                ("timer_reset", "✅ 3-hour timer reset"),
                (
                    "next_auto_quiz",
                    (
                        f"In 3 hours ({next_quiz_time.strftime('%I:%M %p')} EST)"
                        if next_quiz_time
                        else "Time calculation failed"
                    ),
                ),
                ("status", "🎉 Command executed successfully"),
            ],
            "🏆",
        )

    except Exception as e:
        log_error_with_traceback("Error in question command", e)
        error_embed = discord.Embed(
            title="❌ Error",
            description="An error occurred while processing the question command. Please try again later.",
            color=0xFF6B6B,
        )
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
        else:
            await interaction.followup.send(embed=error_embed, ephemeral=True)


async def setup_question_command(bot):
    """Set up the question command with comprehensive error handling and logging"""
    try:
        log_perfect_tree_section(
            "Question Command Setup - Starting",
            [
                ("command_name", "/question"),
                ("command_type", "Discord Application Command"),
                ("status", "🔄 Initializing question command setup"),
            ],
            "🚀",
        )

        # Add the slash command to the bot's command tree
        bot.tree.add_command(question_slash_command)

        log_perfect_tree_section(
            "Question Command Setup - Complete",
            [
                ("status", "✅ Question command loaded successfully"),
                ("command_name", "/question"),
                ("command_type", "Slash command only"),
                ("description", "Send quiz manually and reset timer"),
                ("permission_level", "🔒 Admin only"),
                ("error_handling", "✅ Comprehensive traceback and logging"),
                ("tree_logging", "✅ Perfect tree logging implemented"),
            ],
            "📖",
        )

    except Exception as setup_error:
        log_error_with_traceback("Failed to set up question command", setup_error)

        log_perfect_tree_section(
            "Question Command Setup - Failed",
            [
                ("error_type", type(setup_error).__name__),
                ("status", "❌ Failed to load question command"),
                ("impact", "🚨 /question command will not be available"),
            ],
            "💥",
        )

        # Re-raise the exception to ensure the bot startup process is aware of the failure
        raise
