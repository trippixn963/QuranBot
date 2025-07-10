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
from discord import app_commands
from discord.ext import commands

from src.utils.tree_log import log_error_with_traceback, log_perfect_tree_section

# Environment variables
DEVELOPER_ID = int(os.getenv("DEVELOPER_ID", "259725211664908288"))
DAILY_VERSE_CHANNEL_ID = int(os.getenv("DAILY_VERSE_CHANNEL_ID", "1389675580253016144"))


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

                # Log every 10 seconds for debugging
                if self.remaining_time % 10 == 0:
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

            # Find if "Answered by" field exists and update it, or add it
            answered_field_index = None
            for i, field in enumerate(embed.fields):
                if field.name == "👤 Answered by:":
                    answered_field_index = i
                    break

            if answered_field_index is not None:
                # Update existing field
                embed.set_field_at(
                    answered_field_index,
                    name="👤 Answered by:",
                    value=answered_text,
                    inline=False,
                )
            else:
                # Add new field after timer field
                embed.add_field(
                    name="👤 Answered by:",
                    value=answered_text,
                    inline=False,
                )

        # Only update timer display if explicitly requested (from timer countdown)
        if update_timer:
            remaining_time = self.remaining_time
            for i, field in enumerate(embed.fields):
                if "You have" in field.name and "seconds" in field.name:
                    embed.set_field_at(
                        i,
                        name=f"⏰ You have {remaining_time} seconds to answer",
                        value="",
                        inline=False,
                    )
                    break

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

        # Send results embed
        await self.send_results()

        timeout_end = datetime.now(timezone.utc)
        timeout_duration = (timeout_end - timeout_start).total_seconds()

        log_perfect_tree_section(
            "Quiz Timeout - Complete",
            [
                ("timeout_processing_time", f"{timeout_duration:.2f} seconds"),
                ("results_sent", "✅ Results embed sent"),
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

        log_perfect_tree_section(
            "Quiz Results - Final User List",
            [
                ("total_users_processed", len(all_users)),
                ("users_list", all_users),
            ],
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
        # Check if user already answered
        if interaction.user.id in self.view.responses:
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

        # Create embed confirmation
        embed = discord.Embed(
            title="✅ Answer Recorded",
            description=f"You selected **{self.letter}**. Results will be shown when the timer expires!",
            color=0x00D4AA,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        # Update the original message to show who answered (no timer reduction)
        try:
            await self.view.update_question_embed()
        except Exception as e:
            from src.utils.tree_log import log_error_with_traceback

            log_error_with_traceback("Failed to update question embed", e)


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

        # Add timer with clock emoji
        embed.add_field(
            name="⏰ You have 60 seconds to answer",
            value="",
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

        # Add topics
        themes = question.get("themes", ["General"])
        category = question.get("category", "general").replace("_", " ").title()
        topics_text = f"{category} • {' • '.join(themes)}"
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
