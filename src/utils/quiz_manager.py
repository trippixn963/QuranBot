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
from discord.ui import Button, View

from .tree_log import log_error_with_traceback, log_perfect_tree_section

# =============================================================================
# Configuration
# =============================================================================

# Path to quiz data files
DATA_DIR = Path("data")
QUIZ_DATA_FILE = DATA_DIR / "quiz_data.json"
QUIZ_STATS_FILE = DATA_DIR / "quiz_stats.json"
RECENT_QUESTIONS_FILE = DATA_DIR / "recent_questions.json"

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
        """Get a random quiz question"""
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

            return random.choice(filtered_questions)
        except Exception as e:
            log_error_with_traceback("Error getting random question", e)
            return None

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
            }
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)

            log_perfect_tree_section(
                "Quiz State Saved",
                [
                    ("total_questions", len(self.questions)),
                    ("total_users", len(self.user_scores)),
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
            if self.state_file.exists():
                with open(self.state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                    self.questions = state.get("questions", [])
                    self.user_scores = state.get("user_scores", {})

            log_perfect_tree_section(
                "Quiz State Loaded",
                [
                    ("total_questions", len(self.questions)),
                    ("total_users", len(self.user_scores)),
                    ("status", "✅ State loaded successfully"),
                ],
                "📥",
            )
            return True
        except Exception as e:
            log_error_with_traceback("Error loading quiz state", e)
            return False
