#!/usr/bin/env python3
# =============================================================================
# QuranBot - Quiz Manager
# =============================================================================
# Manages the Islamic quiz system that follows daily verses
# =============================================================================

import asyncio
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

import discord
import pytz
from discord.ui import Button, View

from .tree_log import log_error_with_traceback, log_perfect_tree_section

# Global scheduler task
_quiz_scheduler_task = None

# =============================================================================
# Configuration
# =============================================================================

# Path to quiz data files
DATA_DIR = Path("data")
QUIZ_DATA_FILE = DATA_DIR / "quiz_data.json"
QUIZ_STATS_FILE = DATA_DIR / "quiz_stats.json"
RECENT_QUESTIONS_FILE = DATA_DIR / "recent_questions.json"
QUIZ_STATE_FILE = DATA_DIR / "quiz_state.json"

# Quiz configuration
QUIZ_DELAY_MINUTES = 1  # Delay after verse before quiz
QUIZ_INTERVAL_HOURS = 3  # Hours between quizzes
MAX_RECENT_QUESTIONS = 50  # Maximum number of questions to track as "recent"
MIN_DIFFICULTY = 3  # Minimum difficulty for questions (1-5 scale)

# Constants for validation
MIN_QUESTION_LENGTH = 10
MAX_QUESTION_LENGTH = 500
MIN_OPTIONS = 2
MAX_OPTIONS = 6
MIN_OPTION_LENGTH = 1
MAX_OPTION_LENGTH = 200
VALID_DIFFICULTIES = {"easy", "medium", "hard"}
VALID_CATEGORIES = {
    "general",
    "surah_names",
    "verse_meanings",
    "prophets",
    "history",
    "rules",
    "vocabulary",
}


class QuizManager:
    """Manages Quran-related quiz functionality with comprehensive validation"""

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

    def update_user_score(self, user_id: str, is_correct: bool) -> bool:
        """Update a user's quiz score"""
        try:
            if user_id not in self.user_scores:
                self.user_scores[user_id] = {"correct": 0, "total": 0}

            if is_correct:
                self.user_scores[user_id]["correct"] += 1
            self.user_scores[user_id]["total"] += 1

            self.save_state()
            return True
        except Exception as e:
            log_error_with_traceback("Error updating user score", e)
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
            state = {
                "questions": self.questions,
                "user_scores": self.user_scores,
                "recent_questions": self.recent_questions,  # Add recent questions tracking
            }

            # Add last_sent_time if it exists
            if self.last_sent_time:
                state["last_sent_time"] = self.last_sent_time.isoformat()

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
                # Get channel
                channel = bot.get_channel(channel_id)
                if channel:
                    # Create embed
                    embed = discord.Embed(
                        title="📚 Scheduled Islamic Quiz",
                        description=question["question"],
                        color=0x3498DB,
                    )

                    # Add options as fields
                    options_text = ""
                    for i, option in enumerate(question["options"]):
                        options_text += f"{chr(65 + i)}. {option}\n"

                    embed.add_field(
                        name="Options",
                        value=options_text,
                        inline=False,
                    )

                    embed.add_field(
                        name="Difficulty",
                        value=question["difficulty"].title(),
                        inline=True,
                    )

                    embed.add_field(
                        name="Category",
                        value=question["category"].replace("_", " ").title(),
                        inline=True,
                    )

                    # Add footer with next question time
                    interval_hours = quiz_manager.get_interval_hours()
                    if interval_hours < 1:
                        interval_text = f"{int(interval_hours * 60)}m"
                    else:
                        interval_text = f"{interval_hours:.1f}h"

                    embed.set_footer(
                        text=f"Next question in: {interval_text} (Custom interval)"
                    )

                    # Send message
                    message = await channel.send(embed=embed)

                    # Add reaction options
                    try:
                        reactions = ["🇦", "🇧", "🇨", "🇩", "🇪", "🇫"]
                        for i in range(len(question["options"])):
                            await message.add_reaction(reactions[i])
                    except Exception:
                        pass  # Non-critical if reactions fail

                    # Update last sent time
                    quiz_manager.update_last_sent_time()

                    log_perfect_tree_section(
                        "Scheduled Question Posted",
                        [
                            ("difficulty", question["difficulty"]),
                            ("category", question["category"]),
                            ("channel", str(channel_id)),
                            ("interval", f"{interval_hours}h"),
                            ("next_in", interval_text),
                        ],
                        "📬",
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
