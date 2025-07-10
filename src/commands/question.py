#!/usr/bin/env python3
# =============================================================================
# QuranBot - Question Command
# =============================================================================
# Allows admins to manually trigger Islamic knowledge quizzes
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

            # Create visual progress bar
            total_time = 60
            progress_percentage = remaining_time / total_time
            bar_length = 20
            filled_length = int(bar_length * progress_percentage)
            empty_length = bar_length - filled_length

            # Different progress bar styles based on remaining time
            if remaining_time > 30:
                # Green progress bar (more than 30 seconds)
                progress_bar = "🟩" * filled_length + "⬜" * empty_length
                timer_emoji = "⏰"
            elif remaining_time > 10:
                # Yellow progress bar (10-30 seconds)
                progress_bar = "🟨" * filled_length + "⬜" * empty_length
                timer_emoji = "⏰"
            else:
                # Red progress bar (less than 10 seconds)
                progress_bar = "🟥" * filled_length + "⬜" * empty_length
                timer_emoji = "⚠️"

            # Time warning messages
            if remaining_time == 30:
                warning_text = f"\n⏰ **30 seconds remaining**"
            elif remaining_time == 20:
                warning_text = f"\n⏰ **20 seconds remaining**"
            elif remaining_time == 10:
                warning_text = f"\n⚠️ **10 seconds left!**"
            elif remaining_time == 5:
                warning_text = f"\n🚨 **5 seconds left!**"
            else:
                warning_text = ""

            # Update timer field - search for the timer field and update it
            timer_field_found = False
            for i, field in enumerate(embed.fields):
                # Look for timer field by checking if it contains timer-related text
                if ("seconds to answer" in field.name) or (
                    "⏰" in field.name and "answer" in field.name
                ):
                    embed.set_field_at(
                        i,
                        name=f"{timer_emoji} You have {remaining_time} seconds to answer",
                        value=f"{progress_bar}{warning_text}",
                        inline=False,
                    )
                    timer_field_found = True
                    break

            # If timer field wasn't found, log the issue for debugging
            if not timer_field_found:
                from src.utils.tree_log import log_error_with_traceback

                log_error_with_traceback(
                    "Timer field not found in embed",
                    None,
                    {
                        "field_names": [field.name for field in embed.fields],
                        "remaining_time": remaining_time,
                    },
                )

        # Update the message
        try:
            await self.message.edit(embed=embed, view=self)
        except Exception as e:
            from src.utils.tree_log import log_error_with_traceback

            log_error_with_traceback("Failed to edit question message", e)

    async def on_timeout(self):
        """Called when the timer reaches zero"""
        from datetime import datetime, timezone

        from src.utils.tree_log import log_perfect_tree_section

        timeout_start = datetime.now(timezone.utc)

        log_perfect_tree_section(
            "Quiz Timeout - Starting",
            [
                ("action", "Processing quiz timeout"),
                ("responses_received", len(self.responses)),
                ("timeout_start", timeout_start.strftime("%H:%M:%S UTC")),
            ],
            "🔄",
        )

        # Cancel the timer task if it's still running
        if self.timer_task and not self.timer_task.done():
            self.timer_task.cancel()

        # Disable all buttons
        for item in self.children:
            item.disabled = True

        # Update the original message to show disabled buttons
        if self.message:
            try:
                await self.message.edit(view=self)
            except:
                pass

        # Log quiz timeout for each user who participated
        for user_id in self.responses.keys():
            log_user_interaction(
                interaction_type="quiz_timeout",
                user_name="Unknown",  # Will be resolved when results are processed
                user_id=user_id,
                action_description="Quiz timer expired while user had submitted answer",
                details={
                    "user_answer": self.responses[user_id],
                    "correct_answer": self.correct_answer,
                    "quiz_duration": "60 seconds",
                    "total_participants": len(self.responses),
                },
            )

        # Send results embed
        await self.send_results()

        # Delete the original question embed after results are sent
        try:
            await self.message.delete()
            log_perfect_tree_section(
                "Quiz Cleanup",
                [
                    ("original_message", "✅ Question embed deleted"),
                    ("cleanup_reason", "Timer expired, results sent"),
                ],
                "🧹",
            )
        except Exception as e:
            log_error_with_traceback("Failed to delete original question embed", e)

        timeout_end = datetime.now(timezone.utc)
        timeout_duration = (timeout_end - timeout_start).total_seconds()

        log_perfect_tree_section(
            "Quiz Timeout - Complete",
            [
                ("timeout_processing_time", f"{timeout_duration:.2f} seconds"),
                ("results_sent", "✅ Results embed sent"),
                ("question_deleted", "✅ Original question cleaned up"),
            ],
            "✅",
        )

    async def send_results(self):
        """Send the results embed showing who answered correctly"""
        from datetime import datetime, timezone

        from src.utils.tree_log import log_perfect_tree_section

        if not self.message:
            return

        results_start = datetime.now(timezone.utc)

        # Debug: Log the responses
        log_perfect_tree_section(
            "Quiz Results - Starting",
            [
                ("total_responses", len(self.responses)),
                ("responses_dict", str(self.responses)),
                ("correct_answer", self.correct_answer),
                ("results_start", results_start.strftime("%H:%M:%S UTC")),
            ],
            "📊",
        )

        # Create results embed
        embed = discord.Embed(
            title="⏰ Quiz Results",
            description=f"Time's up! Here are the results for the quiz.",
            color=0x3498DB,
        )

        # Add bot's profile picture as thumbnail
        try:
            if self.message.guild and self.message.guild.me:
                bot_member = self.message.guild.me
                if bot_member.avatar:
                    embed.set_thumbnail(url=bot_member.avatar.url)
                else:
                    embed.set_thumbnail(url=bot_member.default_avatar.url)
        except:
            pass

        # Show correct answer
        correct_choice = self.question_data.get("choices", {}).get(
            self.correct_answer, {}
        )
        if isinstance(correct_choice, dict):
            correct_text = correct_choice.get(
                "english", f"Option {self.correct_answer}"
            )
            correct_arabic = correct_choice.get("arabic", "")
            if correct_arabic:
                answer_text = (
                    f"**{self.correct_answer}:** {correct_text}\n    {correct_arabic}"
                )
            else:
                answer_text = f"**{self.correct_answer}:** {correct_text}"
        else:
            answer_text = f"**{self.correct_answer}:** {correct_choice}"

        embed.add_field(
            name="✅ Correct Answer",
            value=answer_text,
            inline=False,
        )

        # Update quiz statistics for each user
        import json
        import os
        from pathlib import Path

        stats_file = Path("data/quiz_stats.json")

        # Load existing stats
        if stats_file.exists():
            with open(stats_file, "r", encoding="utf-8") as f:
                quiz_stats = json.load(f)
        else:
            quiz_stats = {"user_scores": {}}

        # Ensure user_scores key exists
        if "user_scores" not in quiz_stats:
            quiz_stats["user_scores"] = {}

        user_scores = quiz_stats["user_scores"]

        # Update stats for each user
        for user_id, answer in self.responses.items():
            user_id_str = str(user_id)

            # Initialize user stats if not exists
            if user_id_str not in user_scores:
                user_scores[user_id_str] = {
                    "total_questions": 0,
                    "correct_answers": 0,
                    "points": 0,
                    "current_streak": 0,
                    "best_streak": 0,
                }

            user_stats = user_scores[user_id_str]

            # Ensure all required fields exist (for backwards compatibility)
            required_fields = {
                "total_questions": 0,
                "correct_answers": 0,
                "points": 0,
                "current_streak": 0,
                "best_streak": 0,
            }

            for field, default_value in required_fields.items():
                if field not in user_stats:
                    user_stats[field] = default_value

            user_stats["total_questions"] += 1

            is_correct = answer == self.correct_answer

            # Update stats based on correctness
            if is_correct:
                user_stats["correct_answers"] += 1
                user_stats["points"] += 1  # +1 point for correct answer
                user_stats["current_streak"] += 1

                # Update best streak if current is better
                if user_stats["current_streak"] > user_stats["best_streak"]:
                    user_stats["best_streak"] = user_stats["current_streak"]

                points_change = "+1 pt"

                # Log user quiz result - correct answer
                log_user_interaction(
                    interaction_type="quiz_result_correct",
                    user_name="Unknown",  # Will be updated below when we fetch user
                    user_id=user_id,
                    action_description=f"Answered quiz correctly with '{answer}'",
                    details={
                        "selected_answer": answer,
                        "correct_answer": self.correct_answer,
                        "is_correct": True,
                        "points_earned": 1,
                        "new_total_points": user_stats["points"],
                        "current_streak": user_stats["current_streak"],
                        "best_streak": user_stats["best_streak"],
                        "total_questions_answered": user_stats["total_questions"],
                        "total_correct_answers": user_stats["correct_answers"],
                    },
                )

                log_perfect_tree_section(
                    "📊 Quiz Stats - User Update",
                    [
                        ("user_id", user_id_str),
                        ("answer", answer),
                        ("is_correct", "✅ Correct"),
                        ("points_earned", "+1 points"),
                        ("current_streak", user_stats["current_streak"]),
                        ("total_points", user_stats["points"]),
                    ],
                    "📊",
                )
            else:
                # Wrong answer: subtract 1 point but don't go below 0
                user_stats["points"] = max(
                    0, user_stats["points"] - 1
                )  # -1 point for wrong answer, minimum 0
                user_stats["current_streak"] = 0  # Reset streak

                points_change = "-1 pt"

                # Log user quiz result - incorrect answer
                log_user_interaction(
                    interaction_type="quiz_result_incorrect",
                    user_name="Unknown",  # Will be updated below when we fetch user
                    user_id=user_id,
                    action_description=f"Answered quiz incorrectly with '{answer}'",
                    details={
                        "selected_answer": answer,
                        "correct_answer": self.correct_answer,
                        "is_correct": False,
                        "points_lost": 1,
                        "new_total_points": user_stats["points"],
                        "streak_reset": True,
                        "previous_streak": user_stats["current_streak"],
                        "total_questions_answered": user_stats["total_questions"],
                        "total_correct_answers": user_stats["correct_answers"],
                    },
                )

                log_perfect_tree_section(
                    "📊 Quiz Stats - User Update",
                    [
                        ("user_id", user_id_str),
                        ("answer", answer),
                        ("is_correct", "❌ Incorrect"),
                        ("points_lost", "-1 points"),
                        ("streak_reset", "✅ Streak reset to 0"),
                        ("total_points", user_stats["points"]),
                    ],
                    "📊",
                )

        # Save updated stats
        os.makedirs("data", exist_ok=True)
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(quiz_stats, f, indent=2, ensure_ascii=False)

        log_perfect_tree_section(
            "Quiz Stats - File Updated",
            [
                ("stats_file", str(stats_file)),
                ("users_updated", len(self.responses)),
                ("status", "✅ Quiz stats saved successfully"),
            ],
            "💾",
        )

        # Show who answered correctly and incorrectly
        all_users = []

        log_perfect_tree_section(
            "Quiz Results - Processing Answers",
            [
                ("correct_answer", self.correct_answer),
                ("total_responses", len(self.responses)),
                ("processing_each_response", "Starting individual checks"),
            ],
            "🔍",
        )

        for user_id, answer in self.responses.items():
            try:
                user = self.message.guild.get_member(user_id)

                # If user not found in cache, try fetching from API
                if not user:
                    try:
                        user = await self.message.guild.fetch_member(user_id)
                    except:
                        user = None

                # Log each user's answer processing
                is_correct = answer == self.correct_answer
                user_name = user.display_name if user else "Unknown"

                # Log user quiz results display
                log_user_interaction(
                    interaction_type="quiz_results_displayed",
                    user_name=user_name,
                    user_id=user_id,
                    action_description="Quiz results displayed to user",
                    details={
                        "user_answer": answer,
                        "correct_answer": self.correct_answer,
                        "is_correct": is_correct,
                        "user_found_in_guild": user is not None,
                        "display_name": user_name,
                        "total_participants": len(self.responses),
                    },
                )

                log_perfect_tree_section(
                    "Quiz Results - User Answer Check",
                    [
                        ("user_id", user_id),
                        ("user_name", user_name),
                        ("user_answer", answer),
                        ("correct_answer", self.correct_answer),
                        ("is_correct", is_correct),
                        ("user_found", user is not None),
                    ],
                    "👤",
                )

                if is_correct:
                    all_users.append(f"<@{user_id}> - ✅ (+1 pt)")
                else:
                    all_users.append(f"<@{user_id}> - ❌ (-1 pt)")

            except Exception as e:
                log_perfect_tree_section(
                    "Quiz Results - User Processing Error",
                    [
                        ("user_id", user_id),
                        ("error", str(e)),
                        ("status", "❌ Error processing user"),
                    ],
                    "⚠️",
                )
                all_users.append(f"<@{user_id}> - ❌")

        # Create readable user list for logging (with usernames)
        log_items = [("total_users_processed", len(all_users))]

        # Add embed format for reference
        log_items.append(("users_for_embed", all_users))

        # Add each user as a separate log item for clean vertical display
        for i, (user_id, answer) in enumerate(self.responses.items(), 1):
            try:
                user = self.message.guild.get_member(user_id)
                if not user:
                    try:
                        user = await self.message.guild.fetch_member(user_id)
                    except:
                        user = None

                user_name = user.display_name if user else "Unknown User"
                is_correct = answer == self.correct_answer

                if is_correct:
                    log_items.append(
                        (f"user_{i}", f"{user_name} ({user_id}) - ✅ (+1 pt)")
                    )
                else:
                    log_items.append(
                        (f"user_{i}", f"{user_name} ({user_id}) - ❌ (-1 pt)")
                    )
            except:
                log_items.append((f"user_{i}", f"Unknown User ({user_id}) - ❌"))

        log_perfect_tree_section(
            "Quiz Results - Final User List",
            log_items,
            "📋",
        )

        # Add answers field showing all users
        if all_users:
            embed.add_field(
                name="👥 Answers",
                value="\n".join(all_users),
                inline=False,
            )
        else:
            embed.add_field(
                name="👥 Answers",
                value="No one answered",
                inline=False,
            )

        # Add explanation if available
        explanation = self.question_data.get("explanation", {})
        if isinstance(explanation, dict):
            explanation_text = explanation.get("english", "")
            if explanation_text:
                embed.add_field(
                    name="📖 Explanation",
                    value=f"```\n{explanation_text}\n```",
                    inline=False,
                )

        # Set footer with admin profile picture (same as question embed)
        try:
            from src.commands.question import DEVELOPER_ID

            if self.message.guild and self.message.guild.get_member(DEVELOPER_ID):
                admin_member = self.message.guild.get_member(DEVELOPER_ID)
                if admin_member and admin_member.avatar:
                    embed.set_footer(
                        text="Created by حَـــــنَـــــا",
                        icon_url=admin_member.avatar.url,
                    )
                else:
                    embed.set_footer(text="Created by حَـــــنَـــــا")
            else:
                # Fallback: try to fetch user from client
                try:
                    admin_user = await self.message.guild.fetch_member(DEVELOPER_ID)
                    if admin_user and admin_user.avatar:
                        embed.set_footer(
                            text="Created by حَـــــنَـــــا",
                            icon_url=admin_user.avatar.url,
                        )
                    else:
                        embed.set_footer(text="Created by حَـــــنَـــــا")
                except:
                    embed.set_footer(text="Created by حَـــــنَـــــا")
        except Exception:
            embed.set_footer(text="Created by حَـــــنَـــــا")

        # Send results
        try:
            await self.message.channel.send(embed=embed)

            results_end = datetime.now(timezone.utc)
            results_duration = (results_end - results_start).total_seconds()
            total_quiz_duration = (
                (results_end - self.start_time).total_seconds()
                if self.start_time
                else 0
            )

            log_perfect_tree_section(
                "Quiz Results - Complete",
                [
                    ("results_processing_time", f"{results_duration:.2f} seconds"),
                    ("total_quiz_duration", f"{total_quiz_duration:.2f} seconds"),
                    ("expected_duration", "60 seconds"),
                    ("results_embed_sent", "✅ Successfully sent"),
                ],
                "🏆",
            )

        except Exception as e:
            from src.utils.tree_log import log_error_with_traceback

            log_error_with_traceback("Failed to send quiz results", e)


class QuizButton(discord.ui.Button):
    """Individual quiz answer button"""

    def __init__(self, letter: str, is_correct: bool, style: discord.ButtonStyle):
        super().__init__(
            style=style,
            label=letter,
            custom_id=f"quiz_{letter}",
        )
        self.letter = letter
        self.is_correct = is_correct

    async def callback(self, interaction: discord.Interaction):
        """Handle button click"""
        # Log the button click interaction
        log_user_interaction(
            interaction_type="quiz_button_click",
            user_name=interaction.user.display_name,
            user_id=interaction.user.id,
            action_description=f"Clicked quiz button '{self.letter}'",
            details={
                "button_letter": self.letter,
                "is_correct_answer": self.is_correct,
                "quiz_message_id": self.view.message.id if self.view.message else None,
                "guild_id": interaction.guild_id if interaction.guild else None,
                "channel_id": interaction.channel_id,
                "response_time": datetime.now(pytz.timezone("US/Eastern")).strftime(
                    "%m/%d %I:%M %p EST"
                ),
            },
        )

        # Check if user already answered
        if interaction.user.id in self.view.responses:
            # Log duplicate answer attempt
            log_user_interaction(
                interaction_type="quiz_duplicate_answer",
                user_name=interaction.user.display_name,
                user_id=interaction.user.id,
                action_description="Attempted to answer quiz question again",
                details={
                    "original_answer": self.view.responses[interaction.user.id],
                    "attempted_answer": self.letter,
                    "total_responses": len(self.view.responses),
                },
            )

            # Create embed for already answered
            embed = discord.Embed(
                title="⚠️ Already Answered",
                description="You have already answered this quiz!",
                color=0xFFA500,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Store the user's response
        self.view.responses[interaction.user.id] = self.letter

        # Log successful answer submission
        log_user_interaction(
            interaction_type="quiz_answer_submitted",
            user_name=interaction.user.display_name,
            user_id=interaction.user.id,
            action_description=f"Successfully submitted answer '{self.letter}'",
            details={
                "selected_answer": self.letter,
                "is_correct": self.is_correct,
                "total_responses_now": len(self.view.responses),
                "all_responses": str(self.view.responses),
                "submission_time": datetime.now(pytz.timezone("US/Eastern")).strftime(
                    "%m/%d %I:%M %p EST"
                ),
            },
        )

        # Debug: Log the response storage
        from src.utils.tree_log import log_perfect_tree_section

        log_perfect_tree_section(
            "Button Click Debug",
            [
                ("user_id", interaction.user.id),
                ("user_name", interaction.user.display_name),
                ("selected_answer", self.letter),
                ("total_responses", len(self.view.responses)),
                ("all_responses", str(self.view.responses)),
            ],
            "🐛",
        )

        # Create response embed
        embed = discord.Embed(
            title="✅ Answer Recorded",
            description=f"Your answer **{self.letter}** has been recorded!\n\nWait for the timer to finish to see the results.",
            color=0x00D4AA,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

        # Update the original message to show who has answered
        await self.view.update_question_embed()


# Get the daily verses manager through a function instead of global import
def get_daily_verses_manager():
    """Get the daily verses manager instance"""
    try:
        from src.utils.daily_verses import daily_verse_manager

        return daily_verse_manager
    except Exception as e:
        log_error_with_traceback("Failed to import daily_verse_manager", e)
        return None


# Get the quiz manager through a function instead of global import
def get_quiz_manager():
    """Get the quiz manager instance"""
    try:
        from src.utils.quiz_manager import quiz_manager

        return quiz_manager
    except Exception as e:
        log_error_with_traceback("Failed to import quiz_manager", e)
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
        # Log the command usage attempt
        log_user_interaction(
            interaction_type="slash_command",
            user_name=interaction.user.display_name,
            user_id=interaction.user.id,
            action_description="Attempted to use /question command",
            details={
                "command": "question",
                "guild_id": interaction.guild_id if interaction.guild else None,
                "channel_id": interaction.channel_id,
                "is_admin": interaction.user.id == DEVELOPER_ID,
                "attempt_time": datetime.now(pytz.timezone("US/Eastern")).strftime(
                    "%m/%d %I:%M %p EST"
                ),
            },
        )

        # Get the daily verses manager with error handling
        daily_verses_manager = get_daily_verses_manager()
        if not daily_verses_manager:
            log_perfect_tree_section(
                "Question Command - Critical Error",
                [
                    ("error", "❌ daily_verses_manager not available"),
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

        # Check if user is the developer/admin
        if interaction.user.id != DEVELOPER_ID:
            # Log unauthorized access attempt
            log_user_interaction(
                interaction_type="unauthorized_command_attempt",
                user_name=interaction.user.display_name,
                user_id=interaction.user.id,
                action_description="Attempted to use admin-only /question command",
                details={
                    "command": "question",
                    "required_permission": "admin",
                    "required_user_id": DEVELOPER_ID,
                    "access_denied": True,
                },
            )

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
                        text="Created by حَـــــنَـــــا",
                        icon_url=admin_user.avatar.url,
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

        # Log successful admin authentication
        log_user_interaction(
            interaction_type="admin_command_authenticated",
            user_name=interaction.user.display_name,
            user_id=interaction.user.id,
            action_description="Successfully authenticated for /question command",
            details={
                "command": "question",
                "permission_level": "admin",
                "authentication_success": True,
            },
        )

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
        quiz_manager = get_quiz_manager()
        if not quiz_manager:
            log_perfect_tree_section(
                "Question Command - System Not Configured",
                [
                    ("quiz_manager", "❌ Not initialized"),
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

        # Get the target channel
        try:
            channel = interaction.client.get_channel(DAILY_VERSE_CHANNEL_ID)
            if not channel:
                channel = await interaction.client.fetch_channel(DAILY_VERSE_CHANNEL_ID)

            if not channel:
                raise ValueError(f"Channel {DAILY_VERSE_CHANNEL_ID} not found")

        except Exception as e:
            log_error_with_traceback("Failed to get quiz channel", e)

            embed = discord.Embed(
                title="❌ Channel Error",
                description="Could not find the quiz channel. Please check the bot configuration.",
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

        # Create quiz embed (matching the old format)
        embed = discord.Embed(
            title=f"📚 Islamic Knowledge Quiz - {question.get('category', 'General').replace('_', ' ').title()}",
            description=question.get("context", {}).get("english", "Islamic Knowledge"),
            color=0x3498DB,
        )

        # Get the question text (handle both simple and complex formats)
        if isinstance(question.get("question"), dict):
            # Complex format with Arabic/English
            arabic_question = question["question"].get("arabic", "سؤال إسلامي")
            english_question = question["question"].get("english", "Islamic Question")
        else:
            # Simple format (fallback)
            english_question = question.get("question", "Question not available")
            arabic_question = "سؤال إسلامي"  # Default Arabic placeholder

        # Add Arabic section with moon emoji and code block formatting
        embed.add_field(
            name="🌙 Arabic Question",
            value=f"```{arabic_question}```",
            inline=False,
        )

        # Add English section with book emoji and code block formatting
        embed.add_field(
            name="📖 English Question",
            value=f"```{english_question}```",
            inline=False,
        )

        # Add timer with clock emoji and initial progress bar
        initial_progress_bar = "🟩" * 20  # Full green bar at start
        embed.add_field(
            name="⏰ You have 60 seconds to answer",
            value=initial_progress_bar,
            inline=False,
        )

        # Don't add "Answered by" field initially - it will be added dynamically when users answer

        # Add difficulty with stars
        difficulty = question.get("difficulty", 3)
        # Handle both number and string difficulties
        if isinstance(difficulty, int):
            # Number format (1-5)
            difficulty_stars = "⭐" * min(difficulty, 5)
        else:
            # String format
            difficulty_stars = {"easy": "⭐", "medium": "⭐⭐", "hard": "⭐⭐⭐"}.get(
                str(difficulty).lower(), "⭐⭐"
            )

        embed.add_field(
            name="Difficulty",
            value=difficulty_stars,
            inline=True,
        )

        # Add topics (avoid duplicates between category and themes)
        themes = question.get("themes", ["General"])
        category = question.get("category", "general").replace("_", " ").title()

        # Create a list of all topics and remove duplicates while preserving order
        all_topics = [category] + themes
        unique_topics = []
        for topic in all_topics:
            if topic not in unique_topics:
                unique_topics.append(topic)

        topics_text = " • ".join(unique_topics)
        embed.add_field(
            name="Topics",
            value=topics_text,
            inline=True,
        )

        # Add choices section
        choices_text = ""
        choice_letters = ["A", "B", "C", "D", "E", "F"]

        # Get choices from question (complex structure with A, B, C, D keys)
        choices = question.get("choices", {})

        # Build choices text from the complex structure
        for letter in choice_letters:
            if letter in choices:
                choice_data = choices[letter]
                if isinstance(choice_data, dict):
                    # Complex format with Arabic/English
                    arabic_choice = choice_data.get("arabic", "")
                    english_choice = choice_data.get("english", "")
                    choices_text += f"**{letter}:** {english_choice}\n"
                    if arabic_choice:
                        choices_text += f"     `{arabic_choice}`\n\n"
                    else:
                        choices_text += "\n"
                else:
                    # Simple format fallback
                    choices_text += f"**{letter}:** {choice_data}\n\n"

        embed.add_field(
            name="Choices",
            value=choices_text,
            inline=False,
        )

        # Add bot's profile picture as thumbnail
        try:
            if interaction.client.user and interaction.client.user.avatar:
                embed.set_thumbnail(url=interaction.client.user.avatar.url)
            elif interaction.client.user:
                embed.set_thumbnail(url=interaction.client.user.default_avatar.url)
        except Exception:
            pass  # Continue without thumbnail if it fails

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
        except Exception as avatar_error:
            log_error_with_traceback(
                "Failed to fetch admin avatar for quiz message",
                avatar_error,
            )
            embed.set_footer(text="Created by حَـــــنَـــــا")

        # Get correct answer (already a letter in complex format)
        correct_answer_letter = question.get("correct_answer", "A")

        # Send the quiz with buttons
        view = QuizView(correct_answer_letter, question)
        view.original_embed = embed  # Store original embed
        message = await channel.send(embed=embed, view=view)
        view.message = message  # Store message reference for results

        # Start the custom timer
        await view.start_timer()

        # Send admin DM with the correct answer
        try:
            admin_user = await interaction.client.fetch_user(DEVELOPER_ID)
            if admin_user:
                # Create admin answer embed
                admin_embed = discord.Embed(
                    title="🔐 Admin Answer Key",
                    description=f"**Quiz just posted in {channel.mention}**",
                    color=0xFF6B35,
                )

                # Add question info
                admin_embed.add_field(
                    name="📖 Question",
                    value=f"```{english_question}```",
                    inline=False,
                )

                # Add correct answer with highlighting
                correct_choice = question.get("choices", {}).get(
                    correct_answer_letter, {}
                )
                if isinstance(correct_choice, dict):
                    correct_text = correct_choice.get(
                        "english", f"Option {correct_answer_letter}"
                    )
                    correct_arabic = correct_choice.get("arabic", "")

                    answer_text = f"**{correct_answer_letter}:** {correct_text}"
                    if correct_arabic:
                        answer_text += f"\n`{correct_arabic}`"
                else:
                    answer_text = f"**{correct_answer_letter}:** {correct_choice}"

                admin_embed.add_field(
                    name="✅ Correct Answer",
                    value=answer_text,
                    inline=False,
                )

                # Add quiz details
                admin_embed.add_field(
                    name="📊 Quiz Info",
                    value=f"**Category:** {question['category'].replace('_', ' ').title()}\n**Difficulty:** {difficulty_stars}\n**Message ID:** {message.id}",
                    inline=False,
                )

                # Set footer
                admin_embed.set_footer(text="🔒 Admin Only - Keep this private!")

                # Send DM to admin
                await admin_user.send(embed=admin_embed)

                log_perfect_tree_section(
                    "Admin Answer DM - Sent",
                    [
                        ("admin_id", str(DEVELOPER_ID)),
                        ("correct_answer", correct_answer_letter),
                        ("quiz_message_id", str(message.id)),
                        ("status", "✅ Admin DM sent successfully"),
                    ],
                    "🔐",
                )

        except Exception as admin_dm_error:
            log_error_with_traceback(
                "Failed to send admin answer DM",
                admin_dm_error,
            )

        # Log button setup
        try:
            log_perfect_tree_section(
                "Quiz Buttons - Setup Complete",
                [
                    ("buttons_added", f"✅ {len(view.children)} answer buttons"),
                    ("timeout", "⏰ 60 second timer started"),
                    ("message_id", str(message.id)),
                ],
                "🎮",
            )
        except Exception as button_error:
            log_error_with_traceback(
                "Failed to log button setup",
                button_error,
            )

        # Update quiz manager stats and timing
        quiz_manager.update_last_sent_time()

        # Calculate next quiz time (simplified)
        interval_hours = quiz_manager.get_interval_hours()
        next_quiz_time = datetime.now(timezone.utc) + timedelta(hours=interval_hours)

        # Create confirmation embed
        confirmation_embed = discord.Embed(
            title="✅ Quiz Question Sent Successfully",
            description=f"**{question['category'].replace('_', ' ').title()} Quiz** has been sent to {channel.mention}",
            color=0x00D4AA,
        )

        confirmation_embed.add_field(
            name="🔄 Timer Reset",
            value=f"Next automatic quiz will be sent in **{interval_hours} hours**\n*Around {next_quiz_time.strftime('%I:%M %p')} EST*",
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
        log_user_interaction(
            interaction_type="manual_quiz_sent",
            user_name=interaction.user.display_name,
            user_id=interaction.user.id,
            action_description="Successfully sent manual quiz question",
            details={
                "command": "question",
                "quiz_message_id": str(message.id),
                "channel_id": channel.id,
                "channel_name": channel.name,
                "question_category": question["category"],
                "question_difficulty": question["difficulty"],
                "correct_answer": correct_answer_letter,
                "timer_reset_hours": interval_hours,
                "next_auto_quiz": next_quiz_time.astimezone(
                    pytz.timezone("US/Eastern")
                ).strftime("%m/%d %I:%M %p EST"),
            },
        )

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
                ("difficulty", question["difficulty"]),
                ("message_id", str(message.id)),
                ("timer_reset", f"✅ {interval_hours}-hour timer reset"),
                (
                    "next_auto_quiz",
                    f"In {interval_hours} hours ({next_quiz_time.strftime('%I:%M %p')} EST)",
                ),
                ("status", "🎉 Command executed successfully"),
            ],
            "🏆",
        )

    except Exception as e:
        # Log command error
        log_user_interaction(
            interaction_type="command_error",
            user_name=interaction.user.display_name,
            user_id=interaction.user.id,
            action_description="Error occurred while processing /question command",
            details={
                "command": "question",
                "error_type": type(e).__name__,
                "error_message": str(e),
                "guild_id": interaction.guild_id if interaction.guild else None,
                "channel_id": interaction.channel_id,
            },
        )

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
