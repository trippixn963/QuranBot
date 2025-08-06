"""
QuranBot - Quiz Service.

Manages Islamic knowledge quiz functionality including questions, scoring,
and user statistics with comprehensive error handling and performance tracking.
"""

import asyncio
from datetime import datetime, timedelta
import json
from pathlib import Path
import random
from typing import Any, Dict, List, Optional, Tuple

from ...config import get_config
from ...core.errors import ErrorHandler, ServiceError
from ...core.logger import TreeLogger
from ..core.base_service import BaseService


class QuizQuestion:
    """Represents a quiz question with bilingual support."""

    def __init__(self, data: dict[str, Any]):
        """
        Initialize quiz question from data.

        Args
        ----
            data: Question data dictionary.

        """
        self.id = data.get("id", "unknown")
        self.category = data.get("category", "General")
        self.difficulty = data.get("difficulty", 3)
        self.themes = data.get("themes", [])
        self.context = data.get("context", {})
        self.question = data.get("question", {})
        self.choices = data.get("choices", {})
        self.correct_answer = data.get("correct_answer", "A")
        self.explanation = data.get("explanation", {})
        self.reference = data.get("reference", "")

    def get_question_text(self, language: str = "english") -> str:
        """
        Get question text in specified language.

        Args
        ----
            language: Language to retrieve (english/arabic).

        Returns
        -------
            Question text in specified language.

        """
        if isinstance(self.question, dict):
            return self.question.get(
                language, self.question.get("english", "Question not available")
            )
        return str(self.question)

    def get_choice_text(self, choice: str, language: str = "english") -> str:
        """
        Get choice text in specified language.

        Args
        ----
            choice: Choice letter (A, B, C, D).
            language: Language to retrieve (english/arabic).

        Returns
        -------
            Choice text in specified language.

        """
        choice_data = self.choices.get(choice.upper(), {})
        if isinstance(choice_data, dict):
            return choice_data.get(
                language, choice_data.get("english", "Choice not available")
            )
        return str(choice_data)

    def get_explanation_text(self, language: str = "english") -> str:
        """
        Get explanation text in specified language.

        Args
        ----
            language: Language to retrieve (english/arabic).

        Returns
        -------
            Explanation text in specified language.

        """
        if isinstance(self.explanation, dict):
            return self.explanation.get(language, self.explanation.get("english", ""))
        return str(self.explanation)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert question to dictionary format.

        Returns
        -------
            Dictionary representation of the question.

        """
        return {
            "id": self.id,
            "category": self.category,
            "difficulty": self.difficulty,
            "question": self.question,
            "choices": self.choices,
            "correct_answer": self.correct_answer,
            "explanation": self.explanation,
            "reference": self.reference,
        }


class QuizService(BaseService):
    """
    Service for managing Islamic knowledge quizzes.

    Features:
    - Bilingual question support (Arabic/English)
    - Multiple difficulty levels
    - Category-based questions
    - User statistics tracking
    - Leaderboard functionality
    - Anti-duplicate question tracking
    - Configurable quiz intervals
    """

    def __init__(self, bot=None):
        """Initialize quiz service."""
        super().__init__("QuizService")
        self.bot = bot
        self.questions: list[QuizQuestion] = []
        self.recent_questions: list[str] = []
        self.user_stats: dict[str, dict[str, Any]] = {}
        self.last_quiz_time: datetime | None = None
        self.quiz_interval_hours = 3.0
        self.max_recent_questions = 20
        self._questions_loaded = False
        self.error_handler = ErrorHandler()
        
        # Track active quizzes and first correct answers
        self.active_quizzes: dict[str, dict[str, Any]] = {}  # question_id -> quiz info
        self.first_correct_answers: dict[str, str] = {}  # question_id -> user_id

    async def _initialize(self) -> bool:
        """
        Initialize the quiz service.

        Returns
        -------
            True if initialization successful.

        """
        try:
            TreeLogger.info("Initializing quiz service", service="QuizService")

            # Load quiz questions
            await self._load_questions()

            # Load user statistics
            await self._load_user_stats()

            # Load recent questions
            await self._load_recent_questions()

            TreeLogger.info(
                f"Quiz service initialized with {len(self.questions)} questions",
                {
                    "total_questions": len(self.questions),
                    "categories": self._get_category_counts(),
                    "recent_questions": len(self.recent_questions),
                },
            )

            return True

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "initialize_quiz_service",
                    "service_name": "QuizService",
                },
            )
            TreeLogger.error(
                "Failed to initialize quiz service",
                {"error": str(e), "traceback": True},
                service="QuizService",
            )
            return False

    async def _load_questions(self) -> None:
        """Load quiz questions from JSON file."""
        try:
            config = get_config()
            quiz_file = config.data_folder / "quiz_questions.json"

            if not quiz_file.exists():
                TreeLogger.warning(
                    "Quiz questions file not found",
                    {"path": str(quiz_file)},
                    service="QuizService",
                )
                return

            with open(quiz_file, encoding="utf-8") as f:
                data = json.load(f)

            # Parse questions
            self.questions = []
            questions_data = data.get("questions", [])

            for q_data in questions_data:
                try:
                    question = QuizQuestion(q_data)
                    self.questions.append(question)
                except Exception as e:
                    TreeLogger.warning(
                        f"Failed to parse question: {q_data.get('id', 'unknown')}",
                        {"error": str(e)},
                        service="QuizService",
                    )

            self._questions_loaded = True

            TreeLogger.info(
                f"Loaded {len(self.questions)} quiz questions",
                {
                    "total": len(self.questions),
                    "categories": self._get_category_counts(),
                },
                service="QuizService",
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "load_quiz_questions",
                    "file_path": str(quiz_file) if "quiz_file" in locals() else None,
                },
            )
            TreeLogger.error(
                "Failed to load quiz questions",
                {"error": str(e), "traceback": True},
                service="QuizService",
            )
            raise ServiceError(f"Failed to load quiz questions: {e}")

    async def _load_user_stats(self) -> None:
        """Load user statistics from file."""
        try:
            config = get_config()
            stats_file = config.data_folder / "quiz_stats.json"

            if stats_file.exists():
                with open(stats_file, encoding="utf-8") as f:
                    self.user_stats = json.load(f)
            else:
                self.user_stats = {}

        except Exception as e:
            TreeLogger.warning(
                "Failed to load user stats, starting fresh",
                {"error": str(e)},
                service="QuizService",
            )
            self.user_stats = {}

    async def _load_recent_questions(self) -> None:
        """Load recently asked questions."""
        try:
            config = get_config()
            recent_file = config.data_folder / "quiz_recent.json"

            if recent_file.exists():
                with open(recent_file, encoding="utf-8") as f:
                    data = json.load(f)
                    self.recent_questions = data.get("recent", [])
                    last_time = data.get("last_quiz_time")
                    if last_time:
                        self.last_quiz_time = datetime.fromisoformat(last_time)
            else:
                self.recent_questions = []

        except Exception as e:
            TreeLogger.warning(
                "Failed to load recent questions, starting fresh",
                {"error": str(e)},
                service="QuizService",
            )
            self.recent_questions = []

    async def _save_user_stats(self) -> None:
        """Save user statistics to file."""
        try:
            config = get_config()
            stats_file = config.data_folder / "quiz_stats.json"

            with open(stats_file, "w", encoding="utf-8") as f:
                json.dump(self.user_stats, f, indent=2)

        except Exception as e:
            TreeLogger.error(
                "Failed to save user stats", {"error": str(e)}, service="QuizService"
            )

    async def _save_recent_questions(self) -> None:
        """Save recently asked questions."""
        try:
            config = get_config()
            recent_file = config.data_folder / "quiz_recent.json"

            data = {
                "recent": self.recent_questions,
                "last_quiz_time": (
                    self.last_quiz_time.isoformat() if self.last_quiz_time else None
                ),
            }

            with open(recent_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            TreeLogger.error(
                "Failed to save recent questions",
                {"error": str(e)},
                service="QuizService",
            )

    def _get_category_counts(self) -> dict[str, int]:
        """
        Get count of questions per category.

        Returns
        -------
            Dictionary of category counts.

        """
        counts = {}
        for question in self.questions:
            category = question.category
            counts[category] = counts.get(category, 0) + 1
        return counts

    async def get_random_question(
        self,
        category: str | None = None,
        difficulty: int | None = None,
        exclude_recent: bool = True,
    ) -> QuizQuestion | None:
        """
        Get a random quiz question.

        Args
        ----
            category: Optional category filter.
            difficulty: Optional difficulty filter (1-5).
            exclude_recent: Whether to exclude recently asked questions.

        Returns
        -------
            Random quiz question or None if no questions available.

        """
        try:
            if not self._questions_loaded:
                await self._load_questions()

            # Filter questions
            available_questions = self.questions.copy()

            # Filter by category
            if category:
                available_questions = [
                    q
                    for q in available_questions
                    if q.category.lower() == category.lower()
                ]

            # Filter by difficulty
            if difficulty:
                available_questions = [
                    q for q in available_questions if q.difficulty == difficulty
                ]

            # Exclude recent questions
            if exclude_recent and self.recent_questions:
                available_questions = [
                    q for q in available_questions if q.id not in self.recent_questions
                ]

            if not available_questions:
                # If no questions available with filters, try without recent exclusion
                if exclude_recent and self.recent_questions:
                    return await self.get_random_question(
                        category=category, difficulty=difficulty, exclude_recent=False
                    )
                return None

            # Select random question
            question = random.choice(available_questions)

            # Update recent questions
            self.recent_questions.insert(0, question.id)
            if len(self.recent_questions) > self.max_recent_questions:
                self.recent_questions = self.recent_questions[
                    : self.max_recent_questions
                ]

            # Update last quiz time
            self.last_quiz_time = datetime.utcnow()

            # Save state
            await self._save_recent_questions()

            TreeLogger.info(
                "Selected quiz question",
                {
                    "question_id": question.id,
                    "category": question.category,
                    "difficulty": question.difficulty,
                },
                service="QuizService",
            )

            # Track active quiz
            self.active_quizzes[question.id] = {
                "start_time": datetime.utcnow(),
                "question": question,
                "answered_users": set(),
            }

            return question

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "get_random_question",
                    "category": category,
                    "difficulty": difficulty,
                    "exclude_recent": exclude_recent,
                    "available_questions": len(self.questions),
                },
            )
            TreeLogger.error(
                "Failed to get random question",
                {
                    "error": str(e),
                    "traceback": True,
                    "category": category,
                    "difficulty": difficulty,
                },
                service="QuizService",
            )
            return None

    async def record_answer(
        self,
        user_id: str,
        question_id: str,
        answer: str,
        is_correct: bool,
        response_time: float | None = None,
    ) -> tuple[bool, int]:
        """
        Record a user's answer to a quiz question.

        Args
        ----
            user_id: Discord user ID.
            question_id: Question ID.
            answer: User's answer (A, B, C, D).
            is_correct: Whether the answer was correct.
            response_time: Time taken to answer in seconds.

        Returns
        -------
            Tuple of (reward_given, reward_amount)

        """
        reward_given = False
        reward_amount = 0
        
        try:
            TreeLogger.debug(
                "Recording quiz answer",
                {
                    "user_id": user_id,
                    "question_id": question_id,
                    "answer": answer,
                    "is_correct": is_correct,
                    "response_time": response_time,
                },
                service="QuizService",
            )
            
            # Initialize user stats if needed
            if user_id not in self.user_stats:
                TreeLogger.debug(
                    "Initializing user stats",
                    {"user_id": user_id},
                    service="QuizService",
                )
                self.user_stats[user_id] = {
                    "total_questions": 0,
                    "correct_answers": 0,
                    "total_points": 0,
                    "best_streak": 0,
                    "current_streak": 0,
                    "last_answered": None,
                    "category_stats": {},
                }

            stats = self.user_stats[user_id]

            # Update basic stats
            stats["total_questions"] += 1
            stats["last_answered"] = datetime.utcnow().isoformat()
            
            # Get the question object
            question = next(
                (q for q in self.questions if q.id == question_id), None
            )

            if is_correct:
                stats["correct_answers"] += 1
                stats["current_streak"] += 1
                stats["best_streak"] = max(
                    stats["best_streak"], stats["current_streak"]
                )
                if question:
                    points = question.difficulty * 10
                    if response_time and response_time < 10:  # Bonus for quick answers
                        points += 5
                    stats["total_points"] += points

                    # Update category stats
                    category = question.category
                    if category not in stats["category_stats"]:
                        stats["category_stats"][category] = {"total": 0, "correct": 0}
                    stats["category_stats"][category]["total"] += 1
                    stats["category_stats"][category]["correct"] += 1
                    
                    # Check if this is the first correct answer
                    is_first = question_id not in self.first_correct_answers
                    if is_first:
                        self.first_correct_answers[question_id] = user_id
                    
                    # Give UnbelievaBoat reward for correct answer
                    if self.bot and self.bot.services.get("unbelievaboat"):
                        try:
                            TreeLogger.debug(
                                "Attempting to give quiz reward",
                                {
                                    "user_id": user_id,
                                    "difficulty": question.difficulty,
                                    "is_first": is_first,
                                },
                                service="QuizService",
                            )
                            
                            unbelievaboat_service = self.bot.services.get("unbelievaboat")
                            success, amount = await unbelievaboat_service.reward_quiz_answer(
                                int(user_id), 
                                question.difficulty, 
                                question.question,
                                response_time if response_time else 30.0,
                                is_first=is_first
                            )
                            
                            if success:
                                reward_given = True
                                reward_amount = amount
                                TreeLogger.info(
                                    "Quiz reward distributed successfully",
                                    {
                                        "user_id": user_id,
                                        "amount": amount,
                                        "difficulty": question.difficulty,
                                        "is_first": is_first,
                                        "response_time": response_time,
                                    },
                                    service="QuizService",
                                )
                            else:
                                TreeLogger.warning(
                                    "Failed to distribute quiz reward",
                                    {
                                        "user_id": user_id,
                                        "difficulty": question.difficulty,
                                    },
                                    service="QuizService",
                                )
                                
                        except Exception as e:
                            TreeLogger.error(
                                "Error distributing quiz reward",
                                e,
                                {
                                    "user_id": user_id,
                                    "question_id": question_id,
                                    "difficulty": question.difficulty,
                                    "error_type": type(e).__name__,
                                    "traceback": True,
                                },
                                service="QuizService",
                            )
                            # Don't fail the whole operation just because reward failed
            else:
                stats["current_streak"] = 0
                
                # Update category stats for wrong answer
                if question:
                    category = question.category
                    if category not in stats["category_stats"]:
                        stats["category_stats"][category] = {"total": 0, "correct": 0}
                    stats["category_stats"][category]["total"] += 1
                
                # Apply penalty for wrong answer
                if self.bot and self.bot.services.get("unbelievaboat") and question:
                    try:
                        TreeLogger.debug(
                            "Attempting to apply quiz penalty",
                            {
                                "user_id": user_id,
                                "difficulty": question.difficulty,
                            },
                            service="QuizService",
                        )
                        
                        unbelievaboat_service = self.bot.services.get("unbelievaboat")
                        penalty_success, penalty_amount = await unbelievaboat_service.penalize_wrong_answer(
                            int(user_id),
                            question.difficulty,
                            response_time if response_time else 30.0
                        )
                        
                        if penalty_success:
                            reward_given = True  # We'll use negative to indicate penalty
                            reward_amount = -penalty_amount
                            TreeLogger.info(
                                "Quiz penalty applied successfully",
                                {
                                    "user_id": user_id,
                                    "penalty": penalty_amount,
                                    "difficulty": question.difficulty,
                                    "response_time": response_time,
                                },
                                service="QuizService",
                            )
                        else:
                            TreeLogger.warning(
                                "Failed to apply quiz penalty",
                                {
                                    "user_id": user_id,
                                    "difficulty": question.difficulty,
                                },
                                service="QuizService",
                            )
                            
                    except Exception as e:
                        TreeLogger.error(
                            "Error applying quiz penalty",
                            e,
                            {
                                "user_id": user_id,
                                "question_id": question_id,
                                "difficulty": question.difficulty,
                                "error_type": type(e).__name__,
                                "traceback": True,
                            },
                            service="QuizService",
                        )
                        # Don't fail the whole operation just because penalty failed

            # Save stats
            await self._save_user_stats()

            TreeLogger.info(
                "Recorded quiz answer",
                {
                    "user_id": user_id,
                    "question_id": question_id,
                    "correct": is_correct,
                    "response_time": response_time,
                    "reward_given": reward_given,
                    "reward_amount": reward_amount,
                },
                service="QuizService",
            )
            
            return reward_given, reward_amount

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "record_quiz_answer",
                    "user_id": user_id,
                    "question_id": question_id,
                    "answer": answer,
                    "is_correct": is_correct,
                },
            )
            TreeLogger.error(
                "Failed to record answer",
                {
                    "user_id": user_id,
                    "question_id": question_id,
                    "error": str(e),
                    "traceback": True,
                },
                service="QuizService",
            )
            # Mark user as having answered this quiz
            if question_id in self.active_quizzes:
                self.active_quizzes[question_id]["answered_users"].add(user_id)
            
            return reward_given, reward_amount

    async def cleanup_finished_quiz(self, question_id: str) -> None:
        """
        Clean up finished quiz data.
        
        Args:
            question_id: Question ID to clean up
        """
        if question_id in self.active_quizzes:
            del self.active_quizzes[question_id]
        if question_id in self.first_correct_answers:
            del self.first_correct_answers[question_id]
        
        TreeLogger.debug(
            "Cleaned up finished quiz",
            {"question_id": question_id},
            service="QuizService",
        )

    async def get_user_stats(self, user_id: str) -> dict[str, Any]:
        """
        Get comprehensive user quiz statistics.

        Args
        ----
            user_id: Discord user ID.

        Returns
        -------
            User statistics dictionary.

        """
        if user_id not in self.user_stats:
            return {
                "total_questions": 0,
                "correct_answers": 0,
                "accuracy_percentage": 0.0,
                "total_points": 0,
                "best_streak": 0,
                "current_streak": 0,
                "rank": None,
                "category_performance": {},
            }

        stats = self.user_stats[user_id].copy()

        # Calculate accuracy
        if stats["total_questions"] > 0:
            stats["accuracy_percentage"] = round(
                (stats["correct_answers"] / stats["total_questions"]) * 100, 1
            )
        else:
            stats["accuracy_percentage"] = 0.0

        # Calculate rank
        all_scores = sorted(
            [s["total_points"] for s in self.user_stats.values()], reverse=True
        )
        user_score = stats["total_points"]
        stats["rank"] = (
            all_scores.index(user_score) + 1 if user_score in all_scores else None
        )

        # Calculate category performance
        category_performance = {}
        for category, cat_stats in stats.get("category_stats", {}).items():
            if cat_stats["total"] > 0:
                accuracy = (cat_stats["correct"] / cat_stats["total"]) * 100
                category_performance[category] = {
                    "total": cat_stats["total"],
                    "correct": cat_stats["correct"],
                    "accuracy": round(accuracy, 1),
                }
        stats["category_performance"] = category_performance

        return stats

    async def get_leaderboard(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get the quiz leaderboard.

        Args
        ----
            limit: Maximum number of entries to return.

        Returns
        -------
            List of leaderboard entries.

        """
        try:
            leaderboard = []

            # Sort users by total points
            sorted_users = sorted(
                self.user_stats.items(),
                key=lambda x: x[1]["total_points"],
                reverse=True,
            )

            for rank, (user_id, stats) in enumerate(sorted_users[:limit], 1):
                accuracy = 0.0
                if stats["total_questions"] > 0:
                    accuracy = (
                        stats["correct_answers"] / stats["total_questions"]
                    ) * 100

                leaderboard.append(
                    {
                        "rank": rank,
                        "user_id": user_id,
                        "total_points": stats["total_points"],
                        "total_questions": stats["total_questions"],
                        "correct_answers": stats["correct_answers"],
                        "accuracy_percentage": round(accuracy, 1),
                        "best_streak": stats["best_streak"],
                    }
                )

            return leaderboard

        except Exception as e:
            TreeLogger.error(
                "Failed to get leaderboard", {"error": str(e)}, service="QuizService"
            )
            return []

    async def should_send_quiz(self) -> bool:
        """
        Check if it's time to send a quiz based on interval.

        Returns
        -------
            True if quiz should be sent.

        """
        if not self.last_quiz_time:
            return True

        time_since = datetime.utcnow() - self.last_quiz_time
        hours_since = time_since.total_seconds() / 3600

        return hours_since >= self.quiz_interval_hours

    async def get_quiz_statistics(self) -> dict[str, Any]:
        """
        Get comprehensive quiz system statistics.

        Returns
        -------
            Dictionary of quiz statistics.

        """
        try:
            total_users = len(self.user_stats)
            total_answers = sum(s["total_questions"] for s in self.user_stats.values())
            total_correct = sum(s["correct_answers"] for s in self.user_stats.values())

            overall_accuracy = 0.0
            if total_answers > 0:
                overall_accuracy = (total_correct / total_answers) * 100

            # Category statistics
            category_stats = {}
            for stats in self.user_stats.values():
                for category, cat_data in stats.get("category_stats", {}).items():
                    if category not in category_stats:
                        category_stats[category] = {"total": 0, "correct": 0}
                    category_stats[category]["total"] += cat_data["total"]
                    category_stats[category]["correct"] += cat_data["correct"]

            # Calculate category accuracies
            for category, data in category_stats.items():
                if data["total"] > 0:
                    data["accuracy"] = round((data["correct"] / data["total"]) * 100, 1)
                else:
                    data["accuracy"] = 0.0

            return {
                "total_questions": len(self.questions),
                "total_categories": len(self._get_category_counts()),
                "active_users": total_users,
                "total_answers_given": total_answers,
                "total_correct_answers": total_correct,
                "overall_accuracy": round(overall_accuracy, 1),
                "recent_questions_tracked": len(self.recent_questions),
                "category_statistics": category_stats,
                "last_quiz_time": (
                    self.last_quiz_time.isoformat() if self.last_quiz_time else None
                ),
            }

        except Exception as e:
            TreeLogger.error(
                "Failed to get quiz statistics",
                {"error": str(e)},
                service="QuizService",
            )
            return {}

    async def update_quiz_interval(self, hours: float) -> bool:
        """
        Update the quiz interval.

        Args
        ----
            hours: New interval in hours.

        Returns
        -------
            True if update successful.

        """
        try:
            self.quiz_interval_hours = max(0.1, hours)  # Minimum 6 minutes

            TreeLogger.info(
                f"Updated quiz interval to {self.quiz_interval_hours} hours",
                {"interval_hours": self.quiz_interval_hours},
                service="QuizService",
            )

            return True

        except Exception as e:
            TreeLogger.error(
                "Failed to update quiz interval",
                {"error": str(e)},
                service="QuizService",
            )
            return False

    async def _start(self) -> bool:
        """
        Start the quiz service.

        Returns
        -------
            True if service started successfully.

        """
        TreeLogger.info("Quiz service started", service="QuizService")
        return True

    async def _stop(self) -> bool:
        """
        Stop the quiz service.

        Returns
        -------
            True if service stopped successfully.

        """
        try:
            # Save any pending data
            await self._save_user_stats()
            await self._save_recent_questions()

            TreeLogger.info("Quiz service stopped", service="QuizService")
            return True

        except Exception as e:
            TreeLogger.error(
                "Error stopping quiz service", {"error": str(e)}, service="QuizService"
            )
            return False

    async def _cleanup(self) -> bool:
        """
        Cleanup quiz service resources.

        Returns
        -------
            True if cleanup successful.

        """
        self.questions.clear()
        self.recent_questions.clear()
        self.user_stats.clear()

        TreeLogger.info("Quiz service cleaned up", service="QuizService")
        return True

    async def _health_check(self) -> dict[str, Any]:
        """
        Perform health check on quiz service.

        Returns
        -------
            Health check results.

        """
        return {
            "healthy": self._questions_loaded and len(self.questions) > 0,
            "total_questions": len(self.questions),
            "categories": len(self._get_category_counts()),
            "active_users": len(self.user_stats),
            "recent_questions": len(self.recent_questions),
            "last_quiz_time": (
                self.last_quiz_time.isoformat() if self.last_quiz_time else None
            ),
        }
