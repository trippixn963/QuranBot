#!/usr/bin/env python3
# =============================================================================
# QuranBot - Quiz Manager (Open Source Edition)
# =============================================================================
# This is an open source project provided AS-IS without official support.
# Feel free to use, modify, and learn from this code under the license terms.
#
# Purpose:
# Enterprise-grade quiz system for Discord bots with comprehensive validation,
# scheduling, and state management. Originally designed for Islamic knowledge
# quizzes but adaptable for any educational content.
#
# Key Features:
# - Automated quiz scheduling
# - Question pool management
# - User score tracking
# - Leaderboard system
# - Anti-duplicate protection
# - Comprehensive validation
# - State persistence
#
# Technical Implementation:
# - Async/await for non-blocking operations
# - JSON-based state storage
# - Discord UI components integration
# - Timezone-aware scheduling
# - Error handling and logging
#
# File Structure:
# /data/
#   ├── quiz_data.json      # Question pool and metadata
#   ├── quiz_state.json     # Current quiz state and scheduling
#   ├── quiz_stats.json     # User statistics and leaderboard
#   └── recent_questions.json # Anti-duplicate tracking
#
# =============================================================================

import asyncio
import json
import os
import random
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import discord
import pytz
from discord.ui import Button, View

# Load environment variables
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", ".env")
load_dotenv(env_path)

from .tree_log import (
    log_error_with_traceback,
    log_perfect_tree_section,
    log_user_interaction,
    log_warning_with_context,
)

# Global scheduler task reference
_quiz_scheduler_task = None

# =============================================================================
# Interactive Quiz UI Components
# =============================================================================
# Import the interactive quiz components from the question command
# This ensures automated questions have the same beautiful UI as manual ones

class QuizView(discord.ui.View):
    """Discord UI View for quiz buttons - used by both manual and automated quizzes"""

    def __init__(self, correct_answer: str, question_data: dict, quiz_manager_instance=None):
        super().__init__(timeout=None)  # Disable default timeout, use custom timer
        self.correct_answer = correct_answer
        self.question_data = question_data
        self.quiz_manager = quiz_manager_instance  # Reference to quiz manager for score tracking
        self.responses = {}  # Store user responses {user_id: answer}
        self.message = None
        self.original_embed = None  # Store original embed for updates
        self.remaining_time = 60  # Track remaining time separately
        self.timer_task = None  # Track the timer task
        self.start_time = None  # Track when quiz started
        self.results_message = None  # Store results message for deletion
        self.deletion_task = None  # Track the deletion task

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
        from datetime import datetime, timezone

        self.start_time = datetime.now(timezone.utc)

        # Update the timer field to show "60s" at the start
        if self.message and self.original_embed:
            embed = self.original_embed.copy()
            
            # Update the timer field to show "60s" at the start
            timer_text = "60s"

            # Find and update the timer field
            timer_field_found = False
            for i, field in enumerate(embed.fields):
                if field.name == "⏰ Timer":
                    embed.set_field_at(
                        i,
                        name="⏰ Timer",
                        value=timer_text,
                        inline=True,
                    )
                    timer_field_found = True
                    break
            
            # Update the message with the initial timer field
            try:
                await self.message.edit(embed=embed, view=self)
                self.original_embed = embed  # Update the stored embed
            except Exception as e:
                log_error_with_traceback("Failed to update initial timer field in embed", e)

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
        from datetime import datetime, timezone

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
            # Don't log cancellation as an error - this is expected during shutdown
            pass
        except Exception as e:
            log_error_with_traceback("Error in quiz timer countdown", e)

    async def update_question_embed(self, update_timer=False):
        """Update the original question embed to show who has answered"""
        if not self.message or not self.original_embed:
            return

        # Create updated embed based on original
        embed = self.original_embed.copy()

        # Update or add "Answered by" field
        if self.responses:
            answered_users = []
            order_labels = ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th", "10th"]
            
            for i, user_id in enumerate(self.responses.keys()):
                if i < len(order_labels):
                    answered_users.append(f"{order_labels[i]} <@{user_id}>")
                else:
                    answered_users.append(f"{i+1}th <@{user_id}>")
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

            # Simple timer display: 60s, 55s, 50s, etc.
            timer_text = f"{remaining_time}s"

            # Look for existing timer field and update it
            timer_field_found = False
            for i, field in enumerate(embed.fields):
                if field.name == "⏰ Timer":
                    embed.set_field_at(
                        i,
                        name="⏰ Timer",
                        value=timer_text,
                        inline=True,
                    )
                    timer_field_found = True
                    break

        # Update the message
        try:
            await self.message.edit(embed=embed, view=self)
        except discord.NotFound:
            # Message was deleted - stop the timer and view
            if self.timer_task and not self.timer_task.done():
                self.timer_task.cancel()
            if self.deletion_task and not self.deletion_task.done():
                self.deletion_task.cancel()
            self.stop()
        except Exception as e:
            log_error_with_traceback("Failed to update question embed", e)

    async def on_timeout(self):
        """Handle quiz timeout"""
        # Timer task should have completed naturally, no need to cancel

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

        # Update the message to disable buttons but keep the quiz content
        try:
            if self.message and self.original_embed:
                # Keep the original quiz content, just disable the view
                final_embed = self.original_embed.copy()
                
                # Update timer field to show "Time's Up!" if it exists
                timer_field_found = False
                for i, field in enumerate(final_embed.fields):
                    if field.name == "⏰ Timer":
                        final_embed.set_field_at(
                            i,
                            name="⏰ Timer",
                            value="Time's Up!",
                            inline=True,
                        )
                        timer_field_found = True
                        break
                
                await self.message.edit(embed=final_embed, view=self)
        except Exception as e:
            log_error_with_traceback("Failed to update message on timeout", e)

        # Schedule deletion of both messages after 1 minute
        self.deletion_task = asyncio.create_task(self._schedule_message_deletion())

        # Stop the view
        self.stop()

    def stop(self):
        """Override stop method to ensure proper cleanup of tasks"""
        # Cancel any running tasks
        if self.timer_task and not self.timer_task.done():
            self.timer_task.cancel()
        if self.deletion_task and not self.deletion_task.done():
            self.deletion_task.cancel()
        
        # Call parent stop method
        super().stop()

    async def _schedule_message_deletion(self):
        """Schedule deletion of quiz question and results messages after 1 minute"""
        try:
            # Wait 1 minute (60 seconds)
            await asyncio.sleep(60)
            
            messages_deleted = []
            
            # Delete the original quiz question
            if self.message:
                try:
                    await self.message.delete()
                    messages_deleted.append("question")
                    log_perfect_tree_section(
                        "Quiz Cleanup - Question Deleted",
                        [
                            ("message_id", str(self.message.id)),
                            ("status", "✅ Quiz question deleted after timeout"),
                        ],
                        "🗑️",
                    )
                except discord.NotFound:
                    # Message was already deleted
                    messages_deleted.append("question (already deleted)")
                except Exception as e:
                    log_error_with_traceback("Failed to delete quiz question", e)
            
            # Delete the results message
            if self.results_message:
                try:
                    await self.results_message.delete()
                    messages_deleted.append("results")
                    log_perfect_tree_section(
                        "Quiz Cleanup - Results Deleted",
                        [
                            ("message_id", str(self.results_message.id)),
                            ("status", "✅ Quiz results deleted after timeout"),
                        ],
                        "🗑️",
                    )
                except discord.NotFound:
                    # Message was already deleted
                    messages_deleted.append("results (already deleted)")
                except Exception as e:
                    log_error_with_traceback("Failed to delete quiz results", e)
            
            # Log cleanup summary
            if messages_deleted:
                log_perfect_tree_section(
                    "Quiz Cleanup - Complete",
                    [
                        ("messages_deleted", ", ".join(messages_deleted)),
                        ("cleanup_delay", "60 seconds after timeout"),
                        ("status", "✅ Quiz cleanup completed"),
                    ],
                    "🧹",
                )
                
        except asyncio.CancelledError:
            # Task was cancelled, which is normal during shutdown
            log_perfect_tree_section(
                "Quiz Cleanup - Cancelled",
                [
                    ("status", "⚠️ Quiz cleanup task cancelled"),
                    ("reason", "Bot shutdown or quiz interrupted"),
                ],
                "⚠️",
            )
        except Exception as e:
            log_error_with_traceback("Error in quiz message deletion", e)

    async def send_results(self):
        """Send quiz results"""
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
                if self.quiz_manager:
                    try:
                        self.quiz_manager.record_answer(user_id, True)
                    except Exception as e:
                        log_error_with_traceback("Failed to record correct answer", e)
            else:
                incorrect_count += 1
                # Record incorrect answer in quiz manager
                if self.quiz_manager:
                    try:
                        self.quiz_manager.record_answer(user_id, False)
                    except Exception as e:
                        log_error_with_traceback("Failed to record incorrect answer", e)

        # Create results embed
        results_embed = discord.Embed(
            title="📊 Quiz Results",
            description="Time's up! Here are the results for the quiz.",
            color=0x00D4AA,
        )

        # Add spacing after the header
        results_embed.add_field(
            name="\u200b",  # Invisible character for spacing
            value="",
            inline=False,
        )

        # Add correct answer
        choices = self.question_data.get("choices", {})
        correct_choice = choices.get(self.correct_answer, "Unknown")
        if isinstance(correct_choice, dict):
            english_text = correct_choice.get("english", "")
            arabic_text = correct_choice.get("arabic", "")
            
            if english_text and arabic_text:
                correct_display = f"**{self.correct_answer}: {english_text}**\n```\n{arabic_text}\n```"
            elif english_text:
                correct_display = f"**{self.correct_answer}: {english_text}**"
            elif arabic_text:
                correct_display = f"**{self.correct_answer}:** ```\n{arabic_text}\n```"
            else:
                correct_display = f"**{self.correct_answer}:** Answer not available"
        else:
            correct_display = f"**{self.correct_answer}: {str(correct_choice)}**"

        results_embed.add_field(
            name="✅ Correct Answer",
            value=correct_display,
            inline=False,
        )

        # Add single spacing line
        results_embed.add_field(
            name="\u200b",  # Invisible character for spacing
            value="",
            inline=False,
        )

        # Add answers section with user responses
        if user_results:
            answers_text = ""
            for user_id, result in user_results.items():
                try:
                    # Always use mention format for consistency
                    if result["is_correct"]:
                        answers_text += f"👤 <@{user_id}> - {result['answer']} ✅ (+1 pt)\n"
                    else:
                        # Check if user would lose points (i.e., they have points to lose)
                        if self.quiz_manager:
                            try:
                                # Load current user stats to check if they have points
                                from pathlib import Path
                                import json
                                quiz_stats_file = Path("data") / "quiz_stats.json"
                                if quiz_stats_file.exists():
                                    with open(quiz_stats_file, "r", encoding="utf-8") as f:
                                        quiz_stats = json.load(f)
                                    user_points = quiz_stats.get("user_scores", {}).get(str(user_id), {}).get("points", 0)
                                    if user_points > 0:
                                        answers_text += f"👤 <@{user_id}> - {result['answer']} ❌ (-1 pt)\n"
                                    else:
                                        answers_text += f"👤 <@{user_id}> - {result['answer']} ❌ (0 pts)\n"
                                else:
                                    answers_text += f"👤 <@{user_id}> - {result['answer']} ❌ (-1 pt)\n"
                            except Exception:
                                answers_text += f"👤 <@{user_id}> - {result['answer']} ❌ (-1 pt)\n"
                        else:
                            answers_text += f"👤 <@{user_id}> - {result['answer']} ❌ (-1 pt)\n"
                except Exception as e:
                    # Log the error and continue with mention format
                    if result["is_correct"]:
                        answers_text += f"👤 <@{user_id}> - {result['answer']} ✅ (+1 pt)\n"
                    else:
                        answers_text += f"👤 <@{user_id}> - {result['answer']} ❌ (-1 pt)\n"
            
            if answers_text:
                results_embed.add_field(
                    name="👥 Answers",
                    value=answers_text.strip(),
                    inline=False,
                )
        else:
            # Debug: Add a field to show no responses were recorded
            results_embed.add_field(
                name="👥 Answers",
                value="No responses recorded",
                inline=False,
            )

        # Add single spacing line
        results_embed.add_field(
            name="\u200b",  # Invisible character for spacing
            value="",
            inline=False,
        )

        # Add message link for easy navigation
        if self.message:
            message_link = f"https://discord.com/channels/{self.message.guild.id}/{self.message.channel.id}/{self.message.id}"
            results_embed.add_field(
                name="🔗 Go to Question",
                value=f"[Click here to view the original question]({message_link})",
                inline=False,
            )

        # Add explanation if available
        explanation = self.question_data.get("explanation", {})
        
        # Debug: Log explanation data to help troubleshoot
        log_perfect_tree_section(
            "Quiz Results - Explanation Debug",
            [
                ("explanation_exists", "Yes" if explanation else "No"),
                ("explanation_type", type(explanation).__name__),
                ("explanation_content", str(explanation)[:200] if explanation else "None"),
                ("question_data_keys", list(self.question_data.keys())),
            ],
            "🔍",
        )
        
        if explanation:
            # Add single spacing line before explanation
            results_embed.add_field(
                name="\u200b",  # Invisible character for spacing
                value="",
                inline=False,
            )
            
            if isinstance(explanation, dict):
                english_explanation = explanation.get("english", "")
                arabic_explanation = explanation.get("arabic", "")
                
                if english_explanation and arabic_explanation:
                    explanation_text = f"```\n{english_explanation}\n```"
                elif english_explanation:
                    explanation_text = f"```\n{english_explanation}\n```"
                elif arabic_explanation:
                    explanation_text = f"```\n{arabic_explanation}\n```"
                else:
                    explanation_text = None
            else:
                explanation_text = f"```\n{str(explanation)}\n```"

            if explanation_text:
                results_embed.add_field(
                    name="📘 Explanation",
                    value=explanation_text,
                    inline=False,
                )

        # Set bot thumbnail
        if self.message.guild.me and self.message.guild.me.avatar:
            results_embed.set_thumbnail(url=self.message.guild.me.avatar.url)

        # Set footer with admin info
        try:
            import os
            DEVELOPER_ID = int(os.getenv("DEVELOPER_ID", "0"))
            if DEVELOPER_ID != 0:
                # Try to get admin user from guild first
                admin_user = self.message.guild.get_member(DEVELOPER_ID)
                if not admin_user:
                    # If not in guild, fetch user directly
                    admin_user = await self.message.channel.guild.client.fetch_user(DEVELOPER_ID)
                
                if admin_user and admin_user.avatar:
                    results_embed.set_footer(
                        text="Created by حَـــــنَّـــــا",
                        icon_url=admin_user.avatar.url
                    )
                else:
                    results_embed.set_footer(text="Created by حَـــــنَّـــــا")
            else:
                results_embed.set_footer(text="Created by حَـــــنَّـــــا")
        except Exception:
            results_embed.set_footer(text="Created by حَـــــنَّـــــا")

        # Send results
        try:
            self.results_message = await self.message.channel.send(embed=results_embed)
        except Exception as e:
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
        from src.utils.tree_log import log_user_interaction

        # Check if user already answered
        if interaction.user.id in self.view.responses:
            embed = discord.Embed(
                title="❌ Already Answered",
                description="You have already answered this question!",
                color=0xFF6B6B,
            )
            # Set footer with admin info and profile picture
            try:
                import os
                DEVELOPER_ID = int(os.getenv("DEVELOPER_ID", "0"))
                if DEVELOPER_ID != 0:
                    # Try to get admin user from guild first
                    admin_user = interaction.guild.get_member(DEVELOPER_ID)
                    if not admin_user:
                        # If not in guild, fetch user directly
                        admin_user = await interaction.client.fetch_user(DEVELOPER_ID)
                    
                    if admin_user and admin_user.avatar:
                        embed.set_footer(
                            text="Created by حَـــــنَّـــــا",
                            icon_url=admin_user.avatar.url
                        )
                    else:
                        embed.set_footer(text="Created by حَـــــنَّـــــا")
                else:
                    embed.set_footer(text="Created by حَـــــنَّـــــا")
            except Exception:
                embed.set_footer(text="Created by حَـــــنَّـــــا")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Record the response
        self.view.responses[interaction.user.id] = self.letter

        # Cache user info for dashboard display
        try:
            from src.utils.user_cache import cache_user_from_interaction
            cache_user_from_interaction(interaction)
        except Exception:
            pass  # Fail silently to not interfere with quiz operations

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

        # Log to Discord with user profile picture
        from src.utils.discord_logger import get_discord_logger
        discord_logger = get_discord_logger()
        if discord_logger:
            try:
                user_avatar_url = interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url
                await discord_logger.log_user_interaction(
                    "quiz_correct" if self.is_correct else "quiz_incorrect",
                    interaction.user.display_name,
                    interaction.user.id,
                    f"answered quiz question {'correctly' if self.is_correct else 'incorrectly'} with choice {self.letter}",
                    {
                        "Choice": self.letter,
                        "Result": "Correct ✅" if self.is_correct else "Incorrect ❌",
                        "Question ID": str(self.view.question_data.get("id", "Unknown")),
                        "Response Time": datetime.now().strftime("%I:%M %p EST"),
                        "Question": self.view.question_data.get("question", "Unknown")[:100] + "..." if len(self.view.question_data.get("question", "")) > 100 else self.view.question_data.get("question", "Unknown")
                    },
                    user_avatar_url
                )
            except:
                pass

        # Simply acknowledge the interaction without sending a confirmation embed
        await interaction.response.defer()

        # Update the original embed to show who has answered
        await self.view.update_question_embed()


# =============================================================================
# Configuration
# =============================================================================
# Core settings that control quiz behavior and validation rules.
# Modify these values to adjust the quiz system's behavior.
#
# File Paths:
# - All data files stored in /data directory
# - Separate files for different data types
# - JSON format for easy manual editing
#
# Timing Settings:
# - QUIZ_DELAY_MINUTES: Wait time after verse
# - QUIZ_INTERVAL_HOURS: Time between quizzes
# - Timezone-aware scheduling (UTC/EST)
#
# Question Pool Management:
# - MAX_RECENT_QUESTIONS: Anti-duplicate buffer size
# - MIN_DIFFICULTY: Minimum question complexity
# - Configurable categories and difficulties
# =============================================================================

# Data file paths with Path objects for cross-platform compatibility
DATA_DIR = Path("data")
QUIZ_DATA_FILE = DATA_DIR / "quiz_data.json"
QUIZ_STATS_FILE = DATA_DIR / "quiz_stats.json"
RECENT_QUESTIONS_FILE = DATA_DIR / "recent_questions.json"
QUIZ_STATE_FILE = DATA_DIR / "quiz_state.json"

# Quiz timing and frequency configuration
QUIZ_DELAY_MINUTES = 1  # Delay after verse before quiz
QUIZ_INTERVAL_HOURS = 3  # Hours between quizzes
MAX_RECENT_QUESTIONS = 50  # Anti-duplicate buffer size
MIN_DIFFICULTY = 3  # Minimum difficulty (1-5 scale)

# Validation constraints for question content
MIN_QUESTION_LENGTH = 10
MAX_QUESTION_LENGTH = 500
MIN_OPTIONS = 2
MAX_OPTIONS = 6
MIN_OPTION_LENGTH = 1
MAX_OPTION_LENGTH = 200

# Valid categories and difficulty levels
VALID_DIFFICULTIES = {"easy", "medium", "hard"}
VALID_CATEGORIES = {
    "general",  # General Islamic knowledge
    "surah_names",  # Names and attributes of surahs
    "verse_meanings",  # Understanding verse contexts
    "prophets",  # Stories of the prophets
    "history",  # Islamic history
    "rules",  # Islamic rules and guidelines
    "vocabulary",  # Arabic vocabulary
}


class QuizManager:
    """
    Enterprise-grade quiz system for Discord bots.

    This is an open source component that can be used as a reference for
    implementing educational quiz systems in Discord bots.

    Key Features:
    - Question pool management with validation
    - User score tracking and leaderboards
    - Scheduled quiz delivery
    - Anti-duplicate protection
    - State persistence
    - Comprehensive error handling

    Data Management:
    1. Questions:
       - Validated content and structure
       - Categorized by topic and difficulty
       - Anti-duplicate tracking

    2. User Data:
       - Score tracking
       - Performance statistics
       - Participation history

    3. System State:
       - Quiz schedule tracking
       - Runtime statistics
       - Configuration state

    Implementation Notes:
    - Uses JSON for data storage
    - Implements atomic saves
    - Provides data validation
    - Handles timezone conversion
    - Supports custom scheduling

    Usage Example:
    ```python
    quiz_manager = QuizManager(data_dir="data")

    # Add a question
    success, error = quiz_manager.add_question(
        question="What is the first surah?",
        options=["Al-Fatiha", "Al-Baqarah", "Al-Ikhlas"],
        correct_answer=0,
        difficulty="easy",
        category="general"
    )

    # Schedule quizzes
    start_quiz_scheduler(bot, channel_id)
    ```
    """

    def __init__(self, data_dir: Union[str, Path]):
        """Initialize the quiz manager"""
        self.data_dir = Path(data_dir)
        self.questions: List[Dict] = []
        self.user_scores: Dict[int, Dict] = {}
        self.state_file = self.data_dir / "quiz_state.json"
        self.scores_file = self.data_dir / "quiz_scores.json"
        self.last_sent_time = None

        # Recent questions tracking to avoid duplicates
        self.recent_questions: List[str] = []  # Store question IDs
        self.max_recent_questions = 15  # Track last 15 questions

        # Create data directory if it doesn't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Load existing state
        self.load_state()

    def validate_question(
        self,
        question: str,
        options: List[str],
        correct_answer: int,
        difficulty: str = "medium",
        category: str = "general",
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate question data before adding to the pool.

        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            # Validate question text
            if not isinstance(question, str):
                return False, "Question must be a string"

            question = question.strip()
            if len(question) < MIN_QUESTION_LENGTH:
                return (
                    False,
                    f"Question too short (minimum {MIN_QUESTION_LENGTH} characters)",
                )
            if len(question) > MAX_QUESTION_LENGTH:
                return (
                    False,
                    f"Question too long (maximum {MAX_QUESTION_LENGTH} characters)",
                )

            # Validate options
            if not isinstance(options, list):
                return False, "Options must be a list"

            if len(options) < MIN_OPTIONS:
                return False, f"Not enough options (minimum {MIN_OPTIONS})"
            if len(options) > MAX_OPTIONS:
                return False, f"Too many options (maximum {MAX_OPTIONS})"

            # Validate each option
            for i, option in enumerate(options):
                if not isinstance(option, str):
                    return False, f"Option {i+1} must be a string"

                option = option.strip()
                if len(option) < MIN_OPTION_LENGTH:
                    return (
                        False,
                        f"Option {i+1} too short (minimum {MIN_OPTION_LENGTH} character)",
                    )
                if len(option) > MAX_OPTION_LENGTH:
                    return (
                        False,
                        f"Option {i+1} too long (maximum {MAX_OPTION_LENGTH} characters)",
                    )

            # Check for duplicate options
            if len(set(options)) != len(options):
                return False, "Duplicate options are not allowed"

            # Validate correct answer
            if not isinstance(correct_answer, int):
                return False, "Correct answer must be an integer"

            if correct_answer < 0 or correct_answer >= len(options):
                return (
                    False,
                    f"Correct answer index must be between 0 and {len(options)-1}",
                )

            # Validate difficulty
            if difficulty not in VALID_DIFFICULTIES:
                return (
                    False,
                    f"Invalid difficulty. Must be one of: {', '.join(VALID_DIFFICULTIES)}",
                )

            # Validate category
            if category not in VALID_CATEGORIES:
                return (
                    False,
                    f"Invalid category. Must be one of: {', '.join(VALID_CATEGORIES)}",
                )

            return True, None

        except Exception as e:
            log_error_with_traceback("Error validating question", e)
            return False, f"Validation error: {str(e)}"

    def add_question(
        self,
        question: str,
        options: List[str],
        correct_answer: int,
        difficulty: str = "medium",
        category: str = "general",
    ) -> Tuple[bool, Optional[str]]:
        """
        Add a new quiz question with comprehensive validation.

        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        try:
            # Validate the question data
            is_valid, error_message = self.validate_question(
                question, options, correct_answer, difficulty, category
            )

            if not is_valid:
                log_perfect_tree_section(
                    "Question Validation Failed",
                    [
                        ("status", "❌ Invalid question data"),
                        ("error", error_message),
                    ],
                    "❌",
                )
                return False, error_message

            # Create the question object
            new_question = {
                "question": question.strip(),
                "options": [opt.strip() for opt in options],
                "correct_answer": correct_answer,
                "difficulty": difficulty,
                "category": category,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "times_asked": 0,
                "times_correct": 0,
                "last_asked": None,
            }

            self.questions.append(new_question)
            self.save_state()

            log_perfect_tree_section(
                "Question Added Successfully",
                [
                    ("status", "✅ New question added"),
                    ("difficulty", difficulty),
                    ("category", category),
                    ("options_count", len(options)),
                ],
                "✅",
            )

            return True, None

        except Exception as e:
            error_msg = f"Error adding quiz question: {str(e)}"
            log_error_with_traceback(error_msg, e)
            return False, error_msg

    def validate_answer(
        self, question_index: int, answer: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a user's answer to a question.

        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            # Validate question index
            if not isinstance(question_index, int):
                return False, "Question index must be an integer"

            if question_index < 0 or question_index >= len(self.questions):
                return False, f"Invalid question index: {question_index}"

            question = self.questions[question_index]

            # Validate answer
            if not isinstance(answer, int):
                return False, "Answer must be an integer"

            if answer < 0 or answer >= len(question["options"]):
                return False, f"Invalid answer index: {answer}"

            return True, None

        except Exception as e:
            log_error_with_traceback("Error validating answer", e)
            return False, f"Validation error: {str(e)}"

    def get_random_question(
        self, difficulty: Optional[str] = None, category: Optional[str] = None
    ) -> Optional[Dict]:
        """Get a random quiz question, avoiding recently asked questions"""
        try:
            filtered_questions = self.questions

            if difficulty:
                filtered_questions = [
                    q for q in filtered_questions if q["difficulty"] == difficulty
                ]

            if category:
                filtered_questions = [
                    q for q in filtered_questions if q["category"] == category
                ]

            if not filtered_questions:
                return None

            # Filter out recently asked questions
            available_questions = [
                q
                for q in filtered_questions
                if q.get("id", str(hash(str(q)))) not in self.recent_questions
            ]

            # If no questions available (all recent), reset recent list and use all
            if not available_questions:
                log_perfect_tree_section(
                    "Quiz Questions - Recent Reset",
                    [
                        ("reason", "All questions recently asked"),
                        ("recent_count", len(self.recent_questions)),
                        ("action", "🔄 Resetting recent questions list"),
                        ("available_after_reset", len(filtered_questions)),
                    ],
                    "🔄",
                )
                self.recent_questions = []
                available_questions = filtered_questions

            # Select random question
            selected_question = random.choice(available_questions)

            # Track this question as recently asked
            question_id = selected_question.get("id", str(hash(str(selected_question))))
            self.add_to_recent_questions(question_id)

            log_perfect_tree_section(
                "Quiz Question - Selected",
                [
                    ("question_id", question_id),
                    ("category", selected_question.get("category", "unknown")),
                    ("difficulty", selected_question.get("difficulty", "unknown")),
                    ("recent_count", len(self.recent_questions)),
                    ("available_count", len(available_questions)),
                ],
                "🎯",
            )

            return selected_question
        except Exception as e:
            log_error_with_traceback("Error getting random question", e)
            return None

    def add_to_recent_questions(self, question_id: str) -> None:
        """Add a question ID to the recent questions list"""
        try:
            # Add to beginning of list
            if question_id in self.recent_questions:
                self.recent_questions.remove(question_id)

            self.recent_questions.insert(0, question_id)

            # Keep only the most recent questions
            if len(self.recent_questions) > self.max_recent_questions:
                self.recent_questions = self.recent_questions[
                    : self.max_recent_questions
                ]

            # Save state to persist recent questions
            self.save_state()

        except Exception as e:
            log_error_with_traceback("Error adding to recent questions", e)

    def get_recent_questions_info(self) -> Dict:
        """Get information about recently asked questions"""
        try:
            return {
                "recent_count": len(self.recent_questions),
                "max_recent": self.max_recent_questions,
                "recent_ids": self.recent_questions.copy(),
                "total_questions": len(self.questions),
                "available_questions": len(
                    [
                        q
                        for q in self.questions
                        if q.get("id", str(hash(str(q)))) not in self.recent_questions
                    ]
                ),
            }
        except Exception as e:
            log_error_with_traceback("Error getting recent questions info", e)
            return {}

    def check_answer(self, answer_index: int, question: Dict) -> bool:
        """Check if the provided answer is correct"""
        try:
            return answer_index == question["correct_answer"]
        except Exception as e:
            log_error_with_traceback("Error checking answer", e)
            return False

    def record_answer(self, user_id: int, is_correct: bool) -> bool:
        """Record a user's answer for score tracking"""
        try:
            user_id_str = str(user_id)
            if user_id_str not in self.user_scores:
                self.user_scores[user_id_str] = {"correct": 0, "total": 0}

            if is_correct:
                self.user_scores[user_id_str]["correct"] += 1
            self.user_scores[user_id_str]["total"] += 1

            # Save to quiz state file
            self.save_state()
            
            # Also update the quiz stats file that the leaderboard reads from
            self.update_quiz_stats_file(user_id, is_correct)
            
            return True
        except Exception as e:
            log_error_with_traceback("Error recording user answer", e)
            return False

    def update_quiz_stats_file(self, user_id: int, is_correct: bool) -> bool:
        """Update the quiz_stats.json file that the leaderboard command reads from"""
        try:
            user_id_str = str(user_id)
            
            # Load existing quiz stats
            quiz_stats = {"user_scores": {}}
            if QUIZ_STATS_FILE.exists():
                try:
                    with open(QUIZ_STATS_FILE, "r", encoding="utf-8") as f:
                        quiz_stats = json.load(f)
                except Exception as e:
                    log_error_with_traceback("Error loading quiz stats file", e)
                    quiz_stats = {"user_scores": {}}
            
            # Ensure user_scores exists
            if "user_scores" not in quiz_stats:
                quiz_stats["user_scores"] = {}
            
            # Initialize user if not exists
            if user_id_str not in quiz_stats["user_scores"]:
                quiz_stats["user_scores"][user_id_str] = {
                    "points": 0,
                    "correct": 0,
                    "total": 0,
                    "current_streak": 0,
                    "best_streak": 0,
                    "last_answer_time": None,
                    "categories": {}
                }
            
            user_stats = quiz_stats["user_scores"][user_id_str]
            
            # Ensure all required fields exist (for backwards compatibility)
            if "correct" not in user_stats:
                user_stats["correct"] = 0
            if "total" not in user_stats:
                user_stats["total"] = 0
            if "points" not in user_stats:
                user_stats["points"] = 0
            if "current_streak" not in user_stats:
                user_stats["current_streak"] = 0
            if "best_streak" not in user_stats:
                user_stats["best_streak"] = 0
            
            # Update stats
            if is_correct:
                user_stats["points"] += 1
                user_stats["correct"] += 1
                user_stats["current_streak"] += 1
                user_stats["best_streak"] = max(user_stats["best_streak"], user_stats["current_streak"])
            else:
                # Subtract 1 point for wrong answers, but don't go below 0
                user_stats["points"] = max(0, user_stats["points"] - 1)
                user_stats["current_streak"] = 0
            
            user_stats["total"] += 1
            user_stats["last_answer_time"] = datetime.now(timezone.utc).isoformat()
            
            # Save updated quiz stats
            with open(QUIZ_STATS_FILE, "w", encoding="utf-8") as f:
                json.dump(quiz_stats, f, indent=2)
            
            log_perfect_tree_section(
                "Quiz Stats Updated",
                [
                    ("user_id", user_id_str),
                    ("is_correct", "✅ Correct" if is_correct else "❌ Incorrect"),
                    ("new_points", user_stats["points"]),
                    ("current_streak", user_stats["current_streak"]),
                    ("total_answered", user_stats["total"]),
                    ("status", "✅ Quiz stats file updated successfully"),
                ],
                "📊",
            )
            
            return True
            
        except Exception as e:
            log_error_with_traceback("Error updating quiz stats file", e)
            return False

    def get_user_stats(self, user_id: str) -> Dict:
        """Get statistics for a specific user"""
        try:
            if user_id not in self.user_scores:
                return {"correct": 0, "total": 0, "percentage": 0.0}

            stats = self.user_scores[user_id]
            percentage = (
                (stats["correct"] / stats["total"]) * 100 if stats["total"] > 0 else 0
            )

            return {
                "correct": stats["correct"],
                "total": stats["total"],
                "percentage": percentage,
            }
        except Exception as e:
            log_error_with_traceback("Error getting user stats", e)
            return {"correct": 0, "total": 0, "percentage": 0.0}

    def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Get the quiz leaderboard"""
        try:
            # Calculate scores and sort
            leaderboard = []
            for user_id, stats in self.user_scores.items():
                percentage = (
                    (stats["correct"] / stats["total"]) * 100
                    if stats["total"] > 0
                    else 0
                )
                leaderboard.append(
                    {
                        "user_id": user_id,
                        "correct": stats["correct"],
                        "total": stats["total"],
                        "percentage": percentage,
                    }
                )

            # Sort by percentage, then total correct, then total attempts
            leaderboard.sort(
                key=lambda x: (x["percentage"], x["correct"], -x["total"]),
                reverse=True,
            )

            return leaderboard[:limit]
        except Exception as e:
            log_error_with_traceback("Error getting leaderboard", e)
            return []

    def get_questions_by_difficulty(self, difficulty: str) -> List[Dict]:
        """Get questions filtered by difficulty"""
        try:
            return [q for q in self.questions if q["difficulty"] == difficulty]
        except Exception as e:
            log_error_with_traceback("Error filtering questions by difficulty", e)
            return []

    def get_questions_by_category(self, category: str) -> List[Dict]:
        """Get questions filtered by category"""
        try:
            return [q for q in self.questions if q["category"] == category]
        except Exception as e:
            log_error_with_traceback("Error filtering questions by category", e)
            return []

    def save_state(self) -> bool:
        """Save current state to file"""
        try:
            # Load existing state to preserve schedule_config
            existing_state = {}
            if self.state_file.exists():
                try:
                    with open(self.state_file, "r", encoding="utf-8") as f:
                        existing_state = json.load(f)
                except Exception:
                    existing_state = {}
            
            state = {
                "questions": self.questions,
                "user_scores": self.user_scores,
                "recent_questions": self.recent_questions,  # Add recent questions tracking
            }

            # Add last_sent_time if it exists
            if self.last_sent_time:
                state["last_sent_time"] = self.last_sent_time.isoformat()

            # Preserve existing schedule_config if it exists
            if "schedule_config" in existing_state:
                state["schedule_config"] = existing_state["schedule_config"]

            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)

            log_perfect_tree_section(
                "Quiz State Saved",
                [
                    ("total_questions", len(self.questions)),
                    ("total_users", len(self.user_scores)),
                    ("recent_questions", len(self.recent_questions)),
                    (
                        "last_sent",
                        (
                            self.last_sent_time.strftime("%H:%M:%S")
                            if self.last_sent_time
                            else "Never"
                        ),
                    ),
                    ("status", "✅ State saved successfully"),
                ],
                "💾",
            )
            return True
        except Exception as e:
            log_error_with_traceback("Error saving quiz state", e)
            return False

    def load_state(self) -> bool:
        """Load state from file"""
        try:
            # First try to load from quiz_data.json (the main quiz database)
            if QUIZ_DATA_FILE.exists():
                with open(QUIZ_DATA_FILE, "r", encoding="utf-8") as f:
                    quiz_data = json.load(f)
                    if "questions" in quiz_data:
                        self.questions = quiz_data["questions"]
                        # Clean up corrupted questions after loading
                        self._clean_corrupted_questions()

            # Then load user scores, timing, and recent questions from state file
            if self.state_file.exists():
                with open(self.state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                    # Only load user scores, timing, and recent questions, not questions
                    self.user_scores = state.get("user_scores", {})
                    self.recent_questions = state.get("recent_questions", [])

                    # Handle last_sent_time with timezone
                    if state.get("last_sent_time"):
                        try:
                            # Try to parse as ISO format first
                            self.last_sent_time = datetime.fromisoformat(
                                state["last_sent_time"]
                            )
                            # Ensure it's UTC timezone
                            if self.last_sent_time.tzinfo is None:
                                self.last_sent_time = self.last_sent_time.replace(
                                    tzinfo=pytz.UTC
                                )
                        except ValueError:
                            # Fallback for old format
                            self.last_sent_time = None
                    else:
                        self.last_sent_time = None

            log_perfect_tree_section(
                "Quiz State Loaded",
                [
                    ("total_questions", len(self.questions)),
                    ("total_users", len(self.user_scores)),
                    ("recent_questions", len(self.recent_questions)),
                    (
                        "last_sent",
                        (
                            self.last_sent_time.strftime("%H:%M:%S")
                            if self.last_sent_time
                            else "Never"
                        ),
                    ),
                    ("status", "✅ State loaded successfully"),
                ],
                "💾",
            )
            return True
        except Exception as e:
            log_error_with_traceback("Error loading quiz state", e)
            return False

    def _clean_corrupted_questions(self) -> None:
        """Remove corrupted questions that are missing required fields"""
        try:
            original_count = len(self.questions)
            valid_questions = []
            corrupted_count = 0

            # Required fields for complex format only
            required_fields = [
                "question",
                "choices",
                "correct_answer",
                "difficulty",
                "category",
            ]

            for i, question in enumerate(self.questions):
                try:
                    # Check if question is a dictionary
                    if not isinstance(question, dict):
                        corrupted_count += 1
                        log_error_with_traceback(
                            f"Question {i} is not a dictionary: {type(question).__name__}",
                            None,
                        )
                        continue

                    # Check for required fields
                    missing_fields = [
                        field for field in required_fields if field not in question
                    ]
                    if missing_fields:
                        corrupted_count += 1
                        log_error_with_traceback(
                            f"Question {i} missing required fields: {missing_fields}",
                            None,
                            {
                                "question_data": str(question)[:200],
                                "missing_fields": missing_fields,
                            },
                        )
                        continue

                    # Validate choices field (complex format only)
                    if (
                        not isinstance(question["choices"], dict)
                        or len(question["choices"]) == 0
                    ):
                        corrupted_count += 1
                        log_error_with_traceback(
                            f"Question {i} has invalid choices field",
                            None,
                            {
                                "question_data": str(question)[:200],
                                "choices_type": type(
                                    question.get("choices", None)
                                ).__name__,
                                "choices_value": str(question.get("choices", None))[
                                    :100
                                ],
                            },
                        )
                        continue

                    # Question is valid
                    valid_questions.append(question)

                except Exception as e:
                    corrupted_count += 1
                    log_error_with_traceback(f"Error validating question {i}", e)
                    continue

            # Update questions list
            self.questions = valid_questions

            # Log cleanup results
            if corrupted_count > 0:
                log_perfect_tree_section(
                    "Quiz Data Cleanup",
                    [
                        ("original_questions", original_count),
                        ("corrupted_removed", corrupted_count),
                        ("valid_questions", len(valid_questions)),
                        ("status", "🧹 Corrupted questions removed"),
                    ],
                    "🧹",
                )

                # Save cleaned data
                self.save_state()
            else:
                log_perfect_tree_section(
                    "Quiz Data Validation",
                    [
                        ("total_questions", len(self.questions)),
                        ("status", "✅ All questions valid"),
                    ],
                    "✅",
                )

        except Exception as e:
            log_error_with_traceback("Error cleaning corrupted questions", e)

    def get_interval_hours(self) -> float:
        """Get the current question interval in hours from config"""
        try:
            # Use the same file path as the interval command
            quiz_config_file = Path("data/quiz_state.json")
            if quiz_config_file.exists():
                with open(quiz_config_file, "r") as f:
                    data = json.load(f)
                    return data.get("schedule_config", {}).get(
                        "send_interval_hours", 3.0
                    )
            return 3.0  # Default 3 hours
        except Exception as e:
            log_error_with_traceback("Error loading question interval config", e)
            return 3.0

    def set_interval_hours(self, hours: float) -> bool:
        """Set the question interval in hours and save to config"""
        try:
            quiz_config_file = Path("data/quiz_state.json")
            
            # Load existing config or create new one
            config_data = {}
            if quiz_config_file.exists():
                with open(quiz_config_file, "r") as f:
                    config_data = json.load(f)
            
            # Update the schedule config
            if "schedule_config" not in config_data:
                config_data["schedule_config"] = {}
            
            config_data["schedule_config"]["send_interval_hours"] = hours
            config_data["schedule_config"]["last_updated"] = datetime.now(timezone.utc).isoformat()
            
            # Save the updated config
            with open(quiz_config_file, "w") as f:
                json.dump(config_data, f, indent=2)
            
            return True
        except Exception as e:
            log_error_with_traceback("Error saving question interval config", e)
            return False

    def should_send_question(self) -> bool:
        """Check if it's time to send a question based on custom interval"""
        try:
            interval_hours = self.get_interval_hours()

            if not self.last_sent_time:
                return True  # Send immediately if never sent

            current_time = datetime.now(pytz.UTC)
            time_diff = current_time - self.last_sent_time
            interval_seconds = interval_hours * 3600

            return time_diff.total_seconds() >= interval_seconds
        except Exception as e:
            log_error_with_traceback("Error checking question send time", e)
            return True

    def update_last_sent_time(self):
        """Update the last sent time to now"""
        try:
            self.last_sent_time = datetime.now(pytz.UTC)
            self.save_state()
        except Exception as e:
            log_error_with_traceback("Error updating last sent time", e)

    def load_default_questions(self) -> None:
        """Load default sample questions if no questions exist"""
        try:
            # Check if we already have questions loaded from quiz_data.json
            if len(self.questions) > 0:
                log_perfect_tree_section(
                    "Questions Already Loaded",
                    [
                        ("questions_count", str(len(self.questions))),
                        ("source", "quiz_data.json (complex format)"),
                        ("status", "✅ Using existing questions from quiz_data.json"),
                    ],
                    "📚",
                )
                return  # Already have questions from quiz_data.json

            # Only load simple default questions if quiz_data.json is empty/missing
            # Sample Islamic quiz questions
            default_questions = [
                {
                    "question": "How many chapters (surahs) are there in the Quran?",
                    "options": ["114", "116", "112", "118"],
                    "correct_answer": 0,
                    "difficulty": "easy",
                    "category": "general",
                },
                {
                    "question": "What is the first chapter of the Quran called?",
                    "options": ["Al-Baqarah", "Al-Fatihah", "An-Nas", "Al-Ikhlas"],
                    "correct_answer": 1,
                    "difficulty": "easy",
                    "category": "surah_names",
                },
                {
                    "question": "Which prophet is mentioned most frequently in the Quran?",
                    "options": [
                        "Prophet Muhammad (PBUH)",
                        "Prophet Ibrahim (PBUH)",
                        "Prophet Musa (PBUH)",
                        "Prophet Isa (PBUH)",
                    ],
                    "correct_answer": 2,
                    "difficulty": "medium",
                    "category": "prophets",
                },
                {
                    "question": "What does 'Bismillah' mean?",
                    "options": [
                        "In the name of Allah",
                        "Praise be to Allah",
                        "Allah is great",
                        "There is no god but Allah",
                    ],
                    "correct_answer": 0,
                    "difficulty": "easy",
                    "category": "vocabulary",
                },
                {
                    "question": "Which surah is known as the 'Heart of the Quran'?",
                    "options": ["Al-Fatihah", "Yaseen", "Al-Baqarah", "Al-Ikhlas"],
                    "correct_answer": 1,
                    "difficulty": "medium",
                    "category": "surah_names",
                },
            ]

            # Add each question
            for q in default_questions:
                success, error = self.add_question(
                    q["question"],
                    q["options"],
                    q["correct_answer"],
                    q["difficulty"],
                    q["category"],
                )
                if not success:
                    log_error_with_traceback(
                        f"Failed to add default question: {error}", None
                    )

            # Save the state with new questions
            self.save_state()

            log_perfect_tree_section(
                "Default Questions Loaded",
                [
                    ("questions_added", str(len(default_questions))),
                    ("status", "✅ Sample questions loaded successfully"),
                ],
                "📚",
            )

        except Exception as e:
            log_error_with_traceback("Error loading default questions", e)


# Global quiz manager instance
quiz_manager = None


async def check_and_send_scheduled_question(bot, channel_id: int) -> None:
    """
    Check if it's time for a scheduled question based on custom interval and send if needed.

    Args:
        bot: Discord bot instance
        channel_id: Channel ID for question posts
    """
    try:
        if not quiz_manager:
            return

        if quiz_manager.should_send_question():
            # Get new question
            question = quiz_manager.get_random_question()
            if question:
                # Validate question data before processing
                if not isinstance(question, dict):
                    log_error_with_traceback(
                        "Invalid question format: not a dictionary", None
                    )
                    return

                # Handle both simple and complex question formats
                question_text = ""
                options_list = []
                correct_answer_index = 0

                # Complex format (from quiz_data.json)
                if "choices" in question and isinstance(question["choices"], dict):
                    # Extract question text - show Arabic first, then English translation
                    if isinstance(question["question"], dict):
                        arabic_text = question["question"].get("arabic", "")
                        english_text = question["question"].get("english", "")
                        
                        # Format: Arabic Question first, then English Question
                        if arabic_text and english_text:
                            question_text = f"🕌 **Arabic Question**\n```\n{arabic_text}\n```\n\n🇺🇸 **English Question**\n```\n{english_text}\n```"
                        elif arabic_text:
                            question_text = f"🕌 **Arabic Question**\n```\n{arabic_text}\n```"
                        elif english_text:
                            question_text = f"🇺🇸 **English Question**\n```\n{english_text}\n```"
                        else:
                            question_text = "Question text not available"
                    else:
                        question_text = str(question["question"])

                    # Extract options from choices - show English first, then Arabic in code blocks
                    choices = question["choices"]
                    choice_letters = sorted(choices.keys())  # A, B, C, D, etc.
                    
                    for letter in choice_letters:
                        choice = choices[letter]
                        if isinstance(choice, dict):
                            arabic_option = choice.get("arabic", "")
                            english_option = choice.get("english", "")
                            
                            # Format: English first, then Arabic in code block
                            if english_option and arabic_option:
                                option_text = f"{english_option}\n```\n{arabic_option}\n```"
                            elif english_option:
                                option_text = english_option
                            elif arabic_option:
                                option_text = f"```\n{arabic_option}\n```"
                            else:
                                option_text = "Option not available"
                        else:
                            option_text = str(choice)
                        options_list.append(option_text)

                    # Convert letter answer to index
                    correct_letter = question.get("correct_answer", "A")
                    if correct_letter in choice_letters:
                        correct_answer_index = choice_letters.index(correct_letter)

                # Simple format (legacy)
                elif "options" in question and isinstance(question["options"], list):
                    question_text = str(question["question"])
                    options_list = question["options"]
                    correct_answer_index = question.get("correct_answer", 0)

                # Validation failed
                else:
                    log_error_with_traceback(
                        "Question missing valid choices or options field",
                        None,
                        {
                            "question_data": str(question)[:200],
                            "has_choices": "choices" in question,
                            "has_options": "options" in question,
                        },
                    )
                    return

                # Final validation
                if not question_text or not options_list:
                    log_error_with_traceback(
                        "Question or options are empty after processing",
                        None,
                        {
                            "question_text": question_text[:100],
                            "options_count": len(options_list),
                        },
                    )
                    return

                # Get channel
                channel = bot.get_channel(channel_id)
                if channel:
                    # Create embed with EXACT same format as manual /question command
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
                    question_text = question.get("question", "Unknown question")
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
                                name="🇺🇸 **Translation**",
                                value=f"```\n{english_text}\n```",
                                inline=False,
                            )
                    else:
                        # If it's just a string, display it as the question
                        embed.add_field(
                            name="❓ **Question**",
                            value=f"```\n{str(question_text)}\n```",
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
                        value=question.get("category", "General"),
                        inline=True,
                    )

                    # Handle difficulty - convert numbers to stars
                    difficulty_value = question.get("difficulty", "Medium")
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
                    choices = question.get("choices", {})
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
                                    choice_text += f"**{letter}.** ```\n{arabic_choice}\n```\n\n"
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
                        if bot.user and bot.user.avatar:
                            embed.set_thumbnail(url=bot.user.avatar.url)
                    except Exception:
                        pass

                    # Set footer with admin profile picture
                    try:
                        import os
                        DEVELOPER_ID = int(os.getenv("DEVELOPER_ID", "0"))
                        if DEVELOPER_ID != 0:
                            admin_user = await bot.fetch_user(DEVELOPER_ID)
                            if admin_user and admin_user.avatar:
                                embed.set_footer(
                                    text="Created by حَـــــنَـــــا",
                                    icon_url=admin_user.avatar.url,
                                )
                            else:
                                embed.set_footer(text="Created by حَـــــنَـــــا")
                        else:
                            embed.set_footer(text="Created by حَـــــنَـــــا")
                    except Exception:
                        embed.set_footer(text="Created by حَـــــنَـــــا")

                    # Create the interactive quiz view with buttons and timer
                    correct_answer = chr(65 + correct_answer_index)  # Convert index to letter
                    
                    # Prepare question data for the view (convert to format expected by QuizView)
                    # Pass the original question structure to maintain Arabic/English choice
                    quiz_question_data = {
                        "question": question.get("question", question_text),  # Pass original structure
                        "choices": question.get("choices", {}),  # Pass original choices structure
                        "correct_answer": correct_answer,
                        "category": question.get("category", "general"),
                        "difficulty": difficulty_display,
                        "id": question.get("id", "scheduled_quiz"),
                        "explanation": question.get("explanation", {})  # Include explanation for results
                    }
                    
                    # If it's a simple format, build choices dictionary for the view
                    if "choices" not in question:
                        quiz_question_data["choices"] = {}
                        for i, option in enumerate(options_list):
                            letter = chr(65 + i)
                            quiz_question_data["choices"][letter] = option

                    # Create quiz view with interactive buttons
                    view = QuizView(correct_answer, quiz_question_data, quiz_manager)
                    view.original_embed = embed

                    # Send the interactive quiz
                    message = await channel.send(embed=embed, view=view)
                    view.message = message

                    # Start the 60-second timer
                    await view.start_timer()

                    # Send admin DM with the correct answer (same format as manual /question)
                    try:
                        import os

                        DEVELOPER_ID = int(os.getenv("DEVELOPER_ID", "0"))
                        if DEVELOPER_ID != 0:
                            admin_user = await bot.fetch_user(DEVELOPER_ID)
                            if admin_user:
                                # Use EXACT same DM format as manual /question command
                                choices = question.get("choices", {})
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
                                        answer_display = f"**{correct_answer}:** Answer not available"
                                else:
                                    answer_display = f"**{correct_answer}: {str(correct_choice)}**"

                                dm_embed = discord.Embed(
                                    title="🔑 Quiz Answer",
                                    description=f"The correct answer for the quiz you just sent:\n\n{answer_display}",
                                    color=0x00D4AA,
                                )
                                
                                # Add question details
                                dm_embed.add_field(
                                    name="📝 Question Details",
                                    value=f"• **Category:** {question.get('category', 'Unknown')}\n• **Difficulty:** {question.get('difficulty', 'Unknown')}\n• **ID:** {question.get('id', 'Unknown')}",
                                    inline=False
                                )
                                
                                # Add message link for easy navigation
                                message_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
                                dm_embed.add_field(
                                    name="🔗 Go to Question",
                                    value=f"[Click here to jump to the quiz]({message_link})",
                                    inline=False
                                )
                                
                                dm_embed.set_footer(text="Created by حَـــــنَّـــــا")
                                
                                await admin_user.send(embed=dm_embed)

                    except Exception as e:
                        # Log error but don't fail the whole question sending
                        log_error_with_traceback("Failed to send admin DM", e)

                    # Update last sent time
                    quiz_manager.update_last_sent_time()

                    # Log successful question send
                    # Get correct answer text for logging
                    correct_answer_text = "Unknown"
                    if "choices" in question:
                        correct_choice = question["choices"].get(correct_answer, "Unknown")
                        if isinstance(correct_choice, dict):
                            correct_answer_text = correct_choice.get("english", correct_choice.get("arabic", "Unknown"))
                        else:
                            correct_answer_text = str(correct_choice)
                    elif "options" in question and correct_answer_index < len(options_list):
                        correct_answer_text = options_list[correct_answer_index]
                    
                    log_perfect_tree_section(
                        "Interactive Scheduled Quiz Sent",
                        [
                            ("channel", f"#{channel.name}"),
                            ("question_id", question.get("id", "N/A")),
                            ("difficulty", difficulty_display),
                            ("category", str(question.get("category", "general")).replace("_", " ").title()),
                            ("options_count", len(options_list)),
                            ("correct_answer", f"{chr(65 + correct_answer_index)}. {correct_answer_text}"),
                            ("interactive_features", "✅ Buttons, Timer, Progress Bar"),
                            ("timer_duration", "60 seconds"),
                            ("status", "✅ Interactive quiz posted successfully"),
                        ],
                        "📚",
                    )

    except Exception as e:
        log_error_with_traceback("Error checking and sending scheduled question", e)


async def quiz_scheduler_loop(bot, channel_id: int) -> None:
    """
    Background task that checks for scheduled questions every 30 seconds.

    Args:
        bot: Discord bot instance
        channel_id: Channel ID for question posts
    """
    log_perfect_tree_section(
        "Quiz Scheduler - Started",
        [
            ("status", "🔄 Quiz scheduler running"),
            ("check_interval", "30 seconds"),
            ("channel_id", str(channel_id)),
        ],
        "⏰",
    )

    while True:
        try:
            await asyncio.sleep(30)  # Check every 30 seconds
            await check_and_send_scheduled_question(bot, channel_id)
        except asyncio.CancelledError:
            log_perfect_tree_section(
                "Quiz Scheduler - Stopped",
                [
                    ("status", "🛑 Quiz scheduler stopped"),
                    ("reason", "Task cancelled"),
                ],
                "⏰",
            )
            break
        except Exception as e:
            log_error_with_traceback("Error in quiz scheduler loop", e)
            await asyncio.sleep(30)  # Wait before retrying


def start_quiz_scheduler(bot, channel_id: int) -> None:
    """
    Start the background quiz scheduler.

    Args:
        bot: Discord bot instance
        channel_id: Channel ID for question posts
    """
    global _quiz_scheduler_task

    try:
        # Cancel existing task if running
        if _quiz_scheduler_task and not _quiz_scheduler_task.done():
            _quiz_scheduler_task.cancel()

        # Start new scheduler task
        _quiz_scheduler_task = asyncio.create_task(quiz_scheduler_loop(bot, channel_id))

        log_perfect_tree_section(
            "Quiz Scheduler - Initialized",
            [
                ("status", "✅ Quiz scheduler started"),
                ("channel_id", str(channel_id)),
                ("check_frequency", "Every 30 seconds"),
                ("task_id", f"🆔 {id(_quiz_scheduler_task)}"),
            ],
            "⏰",
        )

    except Exception as e:
        log_error_with_traceback("Failed to start quiz scheduler", e)


async def setup_quiz_system(bot, channel_id: int) -> None:
    """
    Set up the quiz system with custom interval scheduling.

    Args:
        bot: Discord bot instance
        channel_id: Channel ID for question posts
    """
    global quiz_manager

    try:
        # Initialize manager if needed
        if quiz_manager is None:
            quiz_manager = QuizManager(Path("data"))

        # Load default questions if none exist
        quiz_manager.load_default_questions()

        # Start the custom interval scheduler
        start_quiz_scheduler(bot, channel_id)

        # Log successful setup
        interval_hours = quiz_manager.get_interval_hours()
        log_perfect_tree_section(
            "Quiz System Setup",
            [
                ("status", "✅ System initialized"),
                ("channel", str(channel_id)),
                ("questions_loaded", str(len(quiz_manager.questions))),
                ("custom_interval", f"{interval_hours}h"),
                ("scheduler", "✅ Custom interval scheduler started"),
            ],
            "📚",
        )

    except Exception as e:
        log_error_with_traceback("Error setting up quiz system", e)
