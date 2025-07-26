#!/usr/bin/env python3
# =============================================================================
# QuranBot - Quiz Manager Tests
# =============================================================================
# Comprehensive tests for quiz functionality
# =============================================================================

import os
from pathlib import Path
import sys
import tempfile

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from utils.quiz_manager import QuizManager


class TestQuizManager:
    """Test suite for QuizManager class"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.quiz_manager = QuizManager(data_dir=self.temp_dir)

        # Sample quiz data
        self.sample_question = {
            "question": "What is the first surah of the Quran?",
            "options": ["Al-Fatiha", "Al-Baqarah", "Al-Ikhlas", "An-Nas"],
            "correct_answer": 0,
            "difficulty": "easy",
            "category": "surah_names",
        }

    def test_initialization(self):
        """Test QuizManager initialization"""
        assert self.quiz_manager.data_dir == Path(self.temp_dir)
        assert isinstance(self.quiz_manager.questions, list)
        assert isinstance(self.quiz_manager.user_scores, dict)

    def test_add_question(self):
        """Test adding a new question"""
        result = self.quiz_manager.add_question(
            question=self.sample_question["question"],
            options=self.sample_question["options"],
            correct_answer=self.sample_question["correct_answer"],
            difficulty=self.sample_question["difficulty"],
            category=self.sample_question["category"],
        )

        assert result is True
        assert len(self.quiz_manager.questions) == 1
        assert (
            self.quiz_manager.questions[0]["question"]
            == self.sample_question["question"]
        )

    def test_get_random_question(self):
        """Test getting a random question"""
        # Add sample question
        self.quiz_manager.add_question(
            question=self.sample_question["question"],
            options=self.sample_question["options"],
            correct_answer=self.sample_question["correct_answer"],
            difficulty=self.sample_question["difficulty"],
            category=self.sample_question["category"],
        )

        question = self.quiz_manager.get_random_question()
        assert question is not None
        assert "question" in question
        assert "options" in question
        assert "correct_answer" in question

    def test_check_answer(self):
        """Test answer checking functionality"""
        # Add sample question
        self.quiz_manager.add_question(
            question=self.sample_question["question"],
            options=self.sample_question["options"],
            correct_answer=self.sample_question["correct_answer"],
            difficulty=self.sample_question["difficulty"],
            category=self.sample_question["category"],
        )

        # Test correct answer
        result = self.quiz_manager.check_answer(0, self.sample_question)
        assert result is True

        # Test incorrect answer
        result = self.quiz_manager.check_answer(1, self.sample_question)
        assert result is False

    def test_update_user_score(self):
        """Test user score updating"""
        user_id = "123456789"

        # Test initial score
        self.quiz_manager.update_user_score(user_id, True)
        assert user_id in self.quiz_manager.user_scores
        assert self.quiz_manager.user_scores[user_id]["correct"] == 1
        assert self.quiz_manager.user_scores[user_id]["total"] == 1

        # Test incorrect answer
        self.quiz_manager.update_user_score(user_id, False)
        assert self.quiz_manager.user_scores[user_id]["correct"] == 1
        assert self.quiz_manager.user_scores[user_id]["total"] == 2

    def test_get_user_stats(self):
        """Test retrieving user statistics"""
        user_id = "123456789"

        # Add some sample scores
        self.quiz_manager.update_user_score(user_id, True)
        self.quiz_manager.update_user_score(user_id, True)
        self.quiz_manager.update_user_score(user_id, False)

        stats = self.quiz_manager.get_user_stats(user_id)
        assert stats["correct"] == 2
        assert stats["total"] == 3
        assert stats["percentage"] == (2 / 3) * 100

    def test_get_leaderboard(self):
        """Test leaderboard functionality"""
        # Add scores for multiple users
        users = ["user1", "user2", "user3"]
        scores = [(3, 1), (2, 1), (1, 1)]  # (correct, incorrect) pairs

        for user, (correct, incorrect) in zip(users, scores, strict=False):
            for _ in range(correct):
                self.quiz_manager.update_user_score(user, True)
            for _ in range(incorrect):
                self.quiz_manager.update_user_score(user, False)

        leaderboard = self.quiz_manager.get_leaderboard()
        assert len(leaderboard) == 3
        assert leaderboard[0]["user_id"] == "user1"  # Highest score first
        assert leaderboard[-1]["user_id"] == "user3"  # Lowest score last

    def test_filter_questions(self):
        """Test question filtering by difficulty and category"""
        # Add questions with different difficulties and categories
        questions = [
            {
                "question": "Easy Surah Question",
                "options": ["A", "B", "C", "D"],
                "correct_answer": 0,
                "difficulty": "easy",
                "category": "surah_names",
            },
            {
                "question": "Hard Verse Question",
                "options": ["A", "B", "C", "D"],
                "correct_answer": 0,
                "difficulty": "hard",
                "category": "verses",
            },
        ]

        for q in questions:
            self.quiz_manager.add_question(
                question=q["question"],
                options=q["options"],
                correct_answer=q["correct_answer"],
                difficulty=q["difficulty"],
                category=q["category"],
            )

        # Test filtering by difficulty
        easy_questions = self.quiz_manager.get_questions_by_difficulty("easy")
        assert len(easy_questions) == 1
        assert easy_questions[0]["difficulty"] == "easy"

        # Test filtering by category
        verse_questions = self.quiz_manager.get_questions_by_category("verses")
        assert len(verse_questions) == 1
        assert verse_questions[0]["category"] == "verses"

    def test_save_and_load_state(self):
        """Test saving and loading quiz state"""
        # Add some questions and scores
        self.quiz_manager.add_question(
            question=self.sample_question["question"],
            options=self.sample_question["options"],
            correct_answer=self.sample_question["correct_answer"],
            difficulty=self.sample_question["difficulty"],
            category=self.sample_question["category"],
        )
        self.quiz_manager.update_user_score("test_user", True)

        # Save state
        save_result = self.quiz_manager.save_state()
        assert save_result is True

        # Create new instance and load state
        new_manager = QuizManager(data_dir=self.temp_dir)
        load_result = new_manager.load_state()
        assert load_result is True

        # Verify state was loaded correctly
        assert len(new_manager.questions) == len(self.quiz_manager.questions)
        assert new_manager.user_scores == self.quiz_manager.user_scores


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
