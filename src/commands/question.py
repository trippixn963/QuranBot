#!/usr/bin/env python3
# =============================================================================
# QuranBot - Question Command (Cog)
# =============================================================================
# Allows admins to manually trigger Islamic knowledge quizzes using Discord.py Cogs
# Mirrors the functionality of /verse command
# =============================================================================

import asyncio
import os
from datetime import datetime, timedelta, timezone

import discord
import pytz
from discord import app_commands
from discord.ext import commands

from src.utils.tree_log import (
    log_error_with_traceback,
    log_perfect_tree_section,
    log_user_interaction,
)

# Environment variables with validation
DEVELOPER_ID = int(os.getenv("DEVELOPER_ID", "0"))
DAILY_VERSE_CHANNEL_ID = int(os.getenv("DAILY_VERSE_CHANNEL_ID", "0"))

# Validate required environment variables
if DEVELOPER_ID == 0:
    raise ValueError("DEVELOPER_ID environment variable must be set")
if DAILY_VERSE_CHANNEL_ID == 0:
    raise ValueError("DAILY_VERSE_CHANNEL_ID environment variable must be set")


class QuizView(discord.ui.View):
    """Discord UI View for quiz buttons"""

    def __init__(self, correct_answer: str, question_data: dict):
        super().__init__(timeout=None)  # Disable default timeout, use custom timer
        self.correct_answer = correct_answer
        self.question_data = question_data
        self.responses = {}  # Store user responses {user_id: answer}
        self.message = None
        self.original_embed = None  # Store original embed for updates
        self.remaining_time = 60  # Track remaining time separately
        self.timer_task = None  # Track the timer task
        self.start_time = None  # Track when quiz started

        # Add buttons for each choice with different colors
        choice_letters = ["A", "B", "C", "D", "E", "F"]
        button_styles = {
            "A": discord.ButtonStyle.success,  # Green
            "B": discord.ButtonStyle.primary,  # Blue
            "C": discord.ButtonStyle.danger,  # Red
            "D": discord.ButtonStyle.secondary,  # Gray
            "E": discord.ButtonStyle.success,  # Green (fallback)
            "F": discord.ButtonStyle.primary,  # Blue (fallback)
        }

        # Get choices from question data (complex structure with A, B, C, D keys)
        choices = question_data.get("choices", {})

        # Create buttons for each choice
        for letter in choice_letters:
            if letter in choices:
                style = button_styles.get(letter, discord.ButtonStyle.secondary)
                button = QuizButton(letter, letter == correct_answer, style)
                self.add_item(button)

    async def start_timer(self):
        """Start the custom timer that counts down and handles timeout"""
        import asyncio
        from datetime import datetime, timezone

        from src.utils.tree_log import log_perfect_tree_section

        self.start_time = datetime.now(timezone.utc)

        log_perfect_tree_section(
            "Quiz Timer - Started",
            [
                ("duration", "60 seconds"),
                ("start_time", self.start_time.strftime("%H:%M:%S UTC")),
                ("timer_type", "Custom asyncio timer"),
            ],
            "⏰",
        )

        self.timer_task = asyncio.create_task(self._timer_countdown())

    async def _timer_countdown(self):
        """Internal timer countdown that updates every second"""
        import asyncio
        from datetime import datetime, timezone

        from src.utils.tree_log import log_perfect_tree_section

        try:
            while self.remaining_time > 0:
                await asyncio.sleep(1)
                self.remaining_time -= 1

                # Update every 5 seconds for smoother progress bar
                if self.remaining_time % 5 == 0:
                    elapsed = (
                        datetime.now(timezone.utc) - self.start_time
                    ).total_seconds()
                    log_perfect_tree_section(
                        "Quiz Timer - Update",
                        [
                            ("remaining_time", f"{self.remaining_time} seconds"),
                            ("elapsed_real_time", f"{elapsed:.1f} seconds"),
                            ("responses_count", len(self.responses)),
                        ],
                        "⏱️",
                    )
                    await self.update_question_embed(update_timer=True)

                # Time warnings at specific intervals
                elif self.remaining_time in [30, 20, 10, 5]:
                    await self.update_question_embed(update_timer=True)

            # Time's up - trigger timeout
            elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds()
            log_perfect_tree_section(
                "Quiz Timer - Timeout",
                [
                    ("timer_reached_zero", "✅ Timer completed"),
                    ("total_elapsed_time", f"{elapsed:.1f} seconds"),
                    ("expected_duration", "60 seconds"),
                    ("responses_received", len(self.responses)),
                ],
                "🏁",
            )

            await self.on_timeout()
        except asyncio.CancelledError:
            # Timer was cancelled (quiz ended early)
            elapsed = (
                (datetime.now(timezone.utc) - self.start_time).total_seconds()
                if self.start_time
                else 0
            )
            log_perfect_tree_section(
                "Quiz Timer - Cancelled",
                [
                    ("reason", "Timer task cancelled"),
                    ("elapsed_time", f"{elapsed:.1f} seconds"),
                ],
                "⚠️",
            )
        except Exception as e:
            from src.utils.tree_log import log_error_with_traceback

            log_error_with_traceback("Error in quiz timer countdown", e)

    async def reduce_timer(self, seconds: int = 10):
        """This method is no longer used - timer always runs for 60 seconds"""
        # Just update the embed to show current responses, don't reduce timer
        await self.update_question_embed()

    async def update_question_embed(self, update_timer=False):
        """Update the original question embed to show who has answered"""
        if not self.message or not self.original_embed:
            return

        # Create updated embed based on original
        embed = self.original_embed.copy()

        # Update or add "Answered by" field
        if self.responses:
            answered_users = []
            for user_id in self.responses.keys():
                answered_users.append(f"<@{user_id}>")
            answered_text = " | ".join(answered_users)

            # Find if "Answered by" field exists and update it
            answered_field_found = False
            for i, field in enumerate(embed.fields):
                if field.name == "👤 Answered by:":
                    embed.set_field_at(
                        i,
                        name="👤 Answered by:",
                        value=answered_text,
                        inline=False,
                    )
                    answered_field_found = True
                    break

            # If "Answered by" field doesn't exist, add it
            if not answered_field_found:
                embed.add_field(
                    name="👤 Answered by:",
                    value=answered_text,
                    inline=False,
                )

        # Only update timer display if explicitly requested (from timer countdown)
        if update_timer:
            remaining_time = self.remaining_time

            # Update timer field
            for i, field in enumerate(embed.fields):
                if field.name == "⏰ Time Remaining:":
                    # Create progress bar with blocks
                    total_blocks = 20
                    filled_blocks = int((remaining_time / 60) * total_blocks)
                    empty_blocks = total_blocks - filled_blocks

                    # Color-coded progress bar
                    if remaining_time > 40:
                        bar_color = "🟢"  # Green
                    elif remaining_time > 20:
                        bar_color = "🟡"  # Yellow
                    else:
                        bar_color = "🔴"  # Red

                    progress_bar = bar_color * filled_blocks + "⬜" * empty_blocks
                    timer_text = f"⏰ {remaining_time}s\n{progress_bar}"

                    embed.set_field_at(
                        i,
                        name="⏰ Time Remaining:",
                        value=timer_text,
                        inline=False,
                    )
                    break

        # Update the message
        try:
            await self.message.edit(embed=embed, view=self)
        except Exception as e:
            from src.utils.tree_log import log_error_with_traceback

            log_error_with_traceback("Failed to update question embed", e)

    async def on_timeout(self):
        """Handle quiz timeout"""
        import asyncio

        from src.utils.tree_log import log_perfect_tree_section

        # Cancel the timer task if it's still running
        if self.timer_task and not self.timer_task.done():
            self.timer_task.cancel()

        # Disable all buttons
        for item in self.children:
            item.disabled = True

        # Calculate elapsed time
        elapsed = (
            (datetime.now(timezone.utc) - self.start_time).total_seconds()
            if self.start_time
            else 60
        )

        log_perfect_tree_section(
            "Quiz Timeout - Processing",
            [
                ("timeout_reason", "⏰ 60-second timer expired"),
                ("total_responses", len(self.responses)),
                ("elapsed_time", f"{elapsed:.1f} seconds"),
                ("status", "🔄 Processing quiz results"),
            ],
            "⏰",
        )

        # Send results
        await self.send_results()

        # Update the message to show timeout
        try:
            if self.message:
                timeout_embed = discord.Embed(
                    title="⏰ Quiz Timeout",
                    description="Time's up! The quiz has ended.",
                    color=0xFF6B6B,
                )
                await self.message.edit(embed=timeout_embed, view=self)
        except Exception as e:
            from src.utils.tree_log import log_error_with_traceback

            log_error_with_traceback("Failed to update message on timeout", e)

        # Stop the view
        self.stop()

    async def send_results(self):
        """Send quiz results to the channel"""
        if not self.message:
            return

        from src.utils.tree_log import log_perfect_tree_section

        # Get quiz manager to record stats
        quiz_manager = get_quiz_manager()

        # Calculate results
        correct_count = 0
        incorrect_count = 0
        user_results = {}

        for user_id, answer in self.responses.items():
            is_correct = answer == self.correct_answer
            user_results[user_id] = {
                "answer": answer,
                "is_correct": is_correct,
            }

            if is_correct:
                correct_count += 1
                # Record correct answer in quiz manager
                if quiz_manager:
                    try:
                        quiz_manager.record_answer(user_id, True)
                    except Exception as e:
                        from src.utils.tree_log import log_error_with_traceback

                        log_error_with_traceback(
                            f"Failed to record correct answer for user {user_id}", e
                        )
            else:
                incorrect_count += 1
                # Record incorrect answer in quiz manager
                if quiz_manager:
                    try:
                        quiz_manager.record_answer(user_id, False)
                    except Exception as e:
                        from src.utils.tree_log import log_error_with_traceback

                        log_error_with_traceback(
                            f"Failed to record incorrect answer for user {user_id}", e
                        )

        # Log quiz completion
        log_perfect_tree_section(
            "Quiz Results - Calculated",
            [
                ("total_responses", len(self.responses)),
                ("correct_answers", correct_count),
                ("incorrect_answers", incorrect_count),
                ("correct_answer", self.correct_answer),
                ("question_id", self.question_data.get("id", "Unknown")),
            ],
            "📊",
        )

        # Create results embed
        results_embed = discord.Embed(
            title="📊 Quiz Results",
            color=0x00D4AA,
        )

        # Add question info
        results_embed.add_field(
            name="❓ Question",
            value=self.question_data.get("question", "Unknown question"),
            inline=False,
        )

        # Add correct answer
        choices = self.question_data.get("choices", {})
        correct_choice_text = choices.get(self.correct_answer, "Unknown")
        results_embed.add_field(
            name="✅ Correct Answer",
            value=f"**{self.correct_answer}**) {correct_choice_text}",
            inline=False,
        )

        # Add statistics
        total_responses = len(self.responses)
        if total_responses > 0:
            accuracy = (correct_count / total_responses) * 100
            results_embed.add_field(
                name="📈 Statistics",
                value=f"**{total_responses}** responses | **{correct_count}** correct | **{accuracy:.1f}%** accuracy",
                inline=False,
            )

            # Add user results
            if user_results:
                correct_users = []
                incorrect_users = []

                for user_id, result in user_results.items():
                    if result["is_correct"]:
                        correct_users.append(f"<@{user_id}> ({result['answer']})")
                    else:
                        incorrect_users.append(f"<@{user_id}> ({result['answer']})")

                if correct_users:
                    results_embed.add_field(
                        name="🎉 Correct Answers",
                        value="\n".join(correct_users),
                        inline=False,
                    )

                if incorrect_users:
                    results_embed.add_field(
                        name="❌ Incorrect Answers",
                        value="\n".join(incorrect_users),
                        inline=False,
                    )
        else:
            results_embed.add_field(
                name="📈 Statistics",
                value="No responses received",
                inline=False,
            )

        # Add explanation if available
        if self.question_data.get("explanation"):
            results_embed.add_field(
                name="💡 Explanation",
                value=self.question_data["explanation"],
                inline=False,
            )

        # Set footer
        results_embed.set_footer(text="Created by حَـــــنَـــــا")

        # Send results
        try:
            await self.message.channel.send(embed=results_embed)

            log_perfect_tree_section(
                "Quiz Results - Sent",
                [
                    ("channel", self.message.channel.name),
                    ("total_responses", total_responses),
                    ("correct_answers", correct_count),
                    ("incorrect_answers", incorrect_count),
                    ("status", "✅ Results sent successfully"),
                ],
                "📤",
            )

        except Exception as e:
            from src.utils.tree_log import log_error_with_traceback

            log_error_with_traceback("Failed to send quiz results", e)


class QuizButton(discord.ui.Button):
    """Individual quiz choice button"""

    def __init__(self, letter: str, is_correct: bool, style: discord.ButtonStyle):
        super().__init__(
            label=letter,
            style=style,
            custom_id=f"quiz_choice_{letter}",
        )
        self.letter = letter
        self.is_correct = is_correct

    async def callback(self, interaction: discord.Interaction):
        """Handle button click"""
        # Check if user already answered
        if interaction.user.id in self.view.responses:
            await interaction.response.send_message(
                "❌ You have already answered this question!", ephemeral=True
            )
            return

        # Record the response
        self.view.responses[interaction.user.id] = self.letter

        # Log user interaction
        log_user_interaction(
            interaction_type="quiz_answer",
            user_name=interaction.user.display_name,
            user_id=interaction.user.id,
            action_description=f"Answered quiz question with choice {self.letter}",
            details={
                "choice": self.letter,
                "is_correct": self.is_correct,
                "question_id": self.view.question_data.get("id", "Unknown"),
                "response_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
        )

        # Send confirmation
        if self.is_correct:
            await interaction.response.send_message(
                f"✅ You selected **{self.letter}**! Your answer has been recorded.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"📝 You selected **{self.letter}**! Your answer has been recorded.",
                ephemeral=True,
            )

        # Update the original embed to show who has answered
        await self.view.update_question_embed()


def get_daily_verses_manager():
    """Get daily verses manager instance"""
    try:
        from src.utils.daily_verses import daily_verse_manager

        return daily_verse_manager
    except Exception as e:
        log_error_with_traceback("Failed to import daily_verse_manager", e)
        return None


def get_quiz_manager():
    """Get quiz manager instance"""
    try:
        from src.utils.quiz_manager import quiz_manager

        return quiz_manager
    except Exception as e:
        log_error_with_traceback("Failed to import quiz_manager", e)
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

        This command allows administrators to send Islamic knowledge quizzes
        manually, bypassing the automatic timer system.

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

                # Set footer with admin profile picture
                try:
                    admin_user = await interaction.client.fetch_user(DEVELOPER_ID)
                    if admin_user and admin_user.avatar:
                        embed.set_footer(
                            text="Created by حَـــــنَـــــا",
                            icon_url=admin_user.avatar.url,
                        )
                    else:
                        embed.set_footer(text="Created by حَـــــنَـــــا")
                except Exception:
                    embed.set_footer(text="Created by حَـــــنَـــــا")

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
            await interaction.response.send_message(
                "❓ Processing your question command...", ephemeral=True
            )

            # Get the channel
            try:
                channel = interaction.client.get_channel(DAILY_VERSE_CHANNEL_ID)
                if not channel:
                    channel = await interaction.client.fetch_channel(
                        DAILY_VERSE_CHANNEL_ID
                    )

                if not channel:
                    raise ValueError(f"Channel {DAILY_VERSE_CHANNEL_ID} not found")

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
                description=question_data.get("question", "Question not available"),
                color=0x00D4AA,
            )

            # Add choices
            choices = question_data.get("choices", {})
            choice_text = ""
            for letter in ["A", "B", "C", "D", "E", "F"]:
                if letter in choices:
                    choice_text += f"**{letter}**) {choices[letter]}\n"

            if choice_text:
                embed.add_field(
                    name="📝 Choices",
                    value=choice_text,
                    inline=False,
                )

            # Add timer field with progress bar
            total_blocks = 20
            progress_bar = "🟢" * total_blocks
            timer_text = f"⏰ 60s\n{progress_bar}"

            embed.add_field(
                name="⏰ Time Remaining:",
                value=timer_text,
                inline=False,
            )

            # Add category and difficulty
            embed.add_field(
                name="📚 Category",
                value=question_data.get("category", "General"),
                inline=True,
            )

            embed.add_field(
                name="⭐ Difficulty",
                value=question_data.get("difficulty", "Medium"),
                inline=True,
            )

            # Set bot profile picture as thumbnail
            try:
                if interaction.client.user and interaction.client.user.avatar:
                    embed.set_thumbnail(url=interaction.client.user.avatar.url)
            except Exception:
                pass

            # Set footer
            embed.set_footer(text="Created by حَـــــنَـــــا")

            # Create quiz view
            correct_answer = question_data.get("correct_answer", "A")
            view = QuizView(correct_answer, question_data)
            view.original_embed = embed

            # Send the quiz
            try:
                message = await channel.send(embed=embed, view=view)
                view.message = message

                # Start the timer
                await view.start_timer()

                # Send confirmation to admin
                try:
                    success_embed = discord.Embed(
                        title="✅ Quiz Sent Successfully",
                        description=f"Quiz has been sent to {channel.mention}.\n\n**Question Details:**\n• Category: {question_data.get('category', 'Unknown')}\n• Difficulty: {question_data.get('difficulty', 'Unknown')}\n• Timer: 60 seconds\n• Quiz Timer: Reset",
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


async def setup(bot):
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
    "QuizView",
    "QuizButton",
    "get_daily_verses_manager",
    "get_quiz_manager",
    "setup",
]
