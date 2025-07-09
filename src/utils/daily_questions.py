#!/usr/bin/env python3
# =============================================================================
# QuranBot - Daily Questions Manager
# =============================================================================
# Manages daily Quran-related questions and user interactions
# =============================================================================

import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union

import pytz

from .tree_log import log_error_with_traceback, log_perfect_tree_section


class DailyQuestionManager:
    """Manages daily Quran-related questions and user interactions"""

    def __init__(self, data_dir: Union[str, Path]):
        """Initialize the daily question manager"""
        self.data_dir = Path(data_dir)
        self.questions_pool: List[Dict] = []
        self.current_question: Optional[Dict] = None
        self.question_history: List[Dict] = []
        self.state_file = self.data_dir / "daily_questions.json"
        self.history_file = self.data_dir / "question_history.json"

        # Create data directory if it doesn't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Load existing state
        self.load_state()

    def add_question_to_pool(
        self,
        question: str,
        options: List[str],
        correct_answer: int,
        explanation: str,
    ) -> bool:
        """Add a new question to the pool"""
        try:
            new_question = {
                "question": question,
                "options": options,
                "correct_answer": correct_answer,
                "explanation": explanation,
            }
            self.questions_pool.append(new_question)
            return True
        except Exception as e:
            log_error_with_traceback("Error adding question to pool", e)
            return False

    def should_update_question(self) -> bool:
        """Check if it's time to update the daily question"""
        try:
            if not self.current_question:
                return True

            current_time = datetime.now(pytz.UTC)
            question_time = datetime.fromtimestamp(
                self.current_question["timestamp"], pytz.UTC
            )
            time_diff = current_time - question_time

            return time_diff.total_seconds() >= 24 * 3600  # 24 hours
        except Exception as e:
            log_error_with_traceback("Error checking question update time", e)
            return True

    def select_new_question(self) -> Optional[Dict]:
        """Select and set a new daily question"""
        try:
            if not self.questions_pool:
                return None

            # Filter out recently used questions
            available_questions = [
                q
                for q in self.questions_pool
                if q not in self.question_history[-10:]  # Avoid recent questions
            ]

            if not available_questions:
                available_questions = self.questions_pool  # Reset if all used

            # Select random question
            new_question = random.choice(available_questions)
            self.current_question = {
                **new_question,
                "timestamp": datetime.now(pytz.UTC).timestamp(),
            }

            # Update history
            self.question_history.append(self.current_question)
            if len(self.question_history) > 50:  # Keep last 50 questions
                self.question_history = self.question_history[-50:]

            self.save_state()
            return self.current_question
        except Exception as e:
            log_error_with_traceback("Error selecting new question", e)
            return None

    def check_answer(self, answer_index: int) -> bool:
        """Check if the provided answer is correct"""
        try:
            if not self.current_question:
                return False
            return answer_index == self.current_question["correct_answer"]
        except Exception as e:
            log_error_with_traceback("Error checking answer", e)
            return False

    def get_current_question(self) -> Optional[Dict]:
        """Get the current daily question"""
        try:
            if self.should_update_question():
                return self.select_new_question()
            return self.current_question
        except Exception as e:
            log_error_with_traceback("Error getting current question", e)
            return None

    def get_question_history(self) -> List[Dict]:
        """Get the history of past questions"""
        try:
            return self.question_history.copy()
        except Exception as e:
            log_error_with_traceback("Error getting question history", e)
            return []

    def get_time_until_next_question(self) -> timedelta:
        """Get time remaining until next question"""
        try:
            if not self.current_question:
                return timedelta()

            current_time = datetime.now(pytz.UTC)
            question_time = datetime.fromtimestamp(
                self.current_question["timestamp"], pytz.UTC
            )
            next_question_time = question_time + timedelta(days=1)

            return max(next_question_time - current_time, timedelta())
        except Exception as e:
            log_error_with_traceback("Error calculating next question time", e)
            return timedelta()

    def save_state(self) -> bool:
        """Save current state to file"""
        try:
            state = {
                "current_question": self.current_question,
                "questions_pool": self.questions_pool,
            }
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)

            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.question_history, f, indent=2)

            log_perfect_tree_section(
                "Daily Questions State Saved",
                [
                    ("questions_pool", f"{len(self.questions_pool)} questions"),
                    ("history", f"{len(self.question_history)} entries"),
                    ("status", "✅ State saved successfully"),
                ],
                "💾",
            )
            return True
        except Exception as e:
            log_error_with_traceback("Error saving state", e)
            return False

    def load_state(self) -> bool:
        """Load state from file"""
        try:
            if self.state_file.exists():
                with open(self.state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                    self.current_question = state.get("current_question")
                    self.questions_pool = state.get("questions_pool", [])

            if self.history_file.exists():
                with open(self.history_file, "r", encoding="utf-8") as f:
                    self.question_history = json.load(f)

            log_perfect_tree_section(
                "Daily Questions State Loaded",
                [
                    ("questions_pool", f"{len(self.questions_pool)} questions"),
                    ("history", f"{len(self.question_history)} entries"),
                    ("status", "✅ State loaded successfully"),
                ],
                "📥",
            )
            return True
        except Exception as e:
            log_error_with_traceback("Error loading state", e)
            return False
