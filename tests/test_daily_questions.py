#!/usr/bin/env python3
# =============================================================================
# QuranBot - Daily Questions Tests
# =============================================================================
# Comprehensive tests for daily questions functionality
# =============================================================================

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytz

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from utils.daily_questions import DailyQuestionManager


class TestDailyQuestionManager:
    """Test suite for DailyQuestionManager class"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = DailyQuestionManager(data_dir=self.temp_dir)

        # Sample question data
        self.sample_question = {
            "question": "What is the meaning of 'Bismillah'?",
            "options": [
                "In the name of Allah",
                "Praise be to Allah",
                "Allah is Great",
                "Glory be to Allah",
            ],
            "correct_answer": 0,
            "explanation": "Bismillah means 'In the name of Allah'",
        }

    def test_initialization(self):
        """Test DailyQuestionManager initialization"""
        assert self.manager.data_dir == Path(self.temp_dir)
        assert isinstance(self.manager.questions_pool, list)
        assert (
            isinstance(self.manager.current_question, dict)
            or self.manager.current_question is None
        )

    def test_add_question_to_pool(self):
        """Test adding a new question to the pool"""
        result = self.manager.add_question_to_pool(
            question=self.sample_question["question"],
            options=self.sample_question["options"],
            correct_answer=self.sample_question["correct_answer"],
            explanation=self.sample_question["explanation"],
        )

        assert result is True
        assert len(self.manager.questions_pool) == 1
        assert (
            self.manager.questions_pool[0]["question"]
            == self.sample_question["question"]
        )

    @patch("utils.daily_questions.datetime")
    def test_should_update_question(self, mock_datetime):
        """Test question update timing logic"""
        # Mock current time to a known value
        mock_now = datetime(2023, 1, 1, 12, 0, tzinfo=pytz.UTC)
        mock_datetime.now.return_value = mock_now
        mock_datetime.fromtimestamp.side_effect = lambda ts, tz: datetime.fromtimestamp(
            ts, tz
        )

        # Test when no current question exists
        assert self.manager.should_update_question() is True

        # Set current question with recent timestamp
        self.manager.current_question = {
            **self.sample_question,
            "timestamp": mock_now.timestamp(),
        }
        assert self.manager.should_update_question() is False

        # Test with old question
        old_time = mock_now - timedelta(days=2)
        self.manager.current_question["timestamp"] = old_time.timestamp()
        assert self.manager.should_update_question() is True

    def test_select_new_question(self):
        """Test new question selection"""
        # Add multiple questions to pool
        questions = [
            {
                "question": f"Test Question {i}",
                "options": ["A", "B", "C", "D"],
                "correct_answer": 0,
                "explanation": f"Explanation {i}",
            }
            for i in range(3)
        ]

        for q in questions:
            self.manager.add_question_to_pool(
                question=q["question"],
                options=q["options"],
                correct_answer=q["correct_answer"],
                explanation=q["explanation"],
            )

        # Test question selection
        new_question = self.manager.select_new_question()
        assert new_question is not None
        assert "question" in new_question
        assert "options" in new_question
        assert "correct_answer" in new_question
        assert "explanation" in new_question
        assert "timestamp" in new_question

    def test_check_answer(self):
        """Test answer checking functionality"""
        # Set current question
        self.manager.current_question = {
            **self.sample_question,
            "timestamp": datetime.now(pytz.UTC).timestamp(),
        }

        # Test correct answer
        result = self.manager.check_answer(0)
        assert result is True

        # Test incorrect answer
        result = self.manager.check_answer(1)
        assert result is False

    def test_get_current_question(self):
        """Test current question retrieval"""
        # Test with no current question
        assert self.manager.get_current_question() is None

        # Set and test current question
        self.manager.current_question = {
            **self.sample_question,
            "timestamp": datetime.now(pytz.UTC).timestamp(),
        }
        current = self.manager.get_current_question()
        assert current is not None
        assert current["question"] == self.sample_question["question"]

    def test_save_and_load_state(self):
        """Test state persistence"""
        # Add question to pool and set current question
        self.manager.add_question_to_pool(
            question=self.sample_question["question"],
            options=self.sample_question["options"],
            correct_answer=self.sample_question["correct_answer"],
            explanation=self.sample_question["explanation"],
        )
        self.manager.current_question = {
            **self.sample_question,
            "timestamp": datetime.now(pytz.UTC).timestamp(),
        }

        # Save state
        save_result = self.manager.save_state()
        assert save_result is True

        # Create new instance and load state
        new_manager = DailyQuestionManager(data_dir=self.temp_dir)
        load_result = new_manager.load_state()
        assert load_result is True

        # Verify state was loaded correctly
        assert len(new_manager.questions_pool) == len(self.manager.questions_pool)
        assert new_manager.current_question == self.manager.current_question

    def test_get_question_history(self):
        """Test question history tracking"""
        # Add and cycle through several questions
        for i in range(3):
            question = {
                "question": f"Test Question {i}",
                "options": ["A", "B", "C", "D"],
                "correct_answer": 0,
                "explanation": f"Explanation {i}",
            }
            self.manager.add_question_to_pool(**question)
            self.manager.select_new_question()

        history = self.manager.get_question_history()
        assert isinstance(history, list)
        assert len(history) > 0
        for entry in history:
            assert "question" in entry
            assert "timestamp" in entry

    @patch("utils.daily_questions.datetime")
    def test_get_time_until_next_question(self, mock_datetime):
        """Test next question timing calculation"""
        # Mock current time
        mock_now = datetime(2023, 1, 1, 12, 0, tzinfo=pytz.UTC)
        mock_datetime.now.return_value = mock_now
        mock_datetime.fromtimestamp.side_effect = lambda ts, tz: datetime.fromtimestamp(
            ts, tz
        )

        # Set current question time
        self.manager.current_question = {
            **self.sample_question,
            "timestamp": mock_now.timestamp(),
        }

        # Calculate time until next question
        time_left = self.manager.get_time_until_next_question()
        assert isinstance(time_left, timedelta)
        assert time_left.total_seconds() > 0

    def test_question_pool_management(self):
        """Test question pool loading and management"""
        # Create test question pool
        questions = [
            {
                "question": "What is the meaning of 'Bismillah'?",
                "options": [
                    "In the name of Allah",
                    "Praise be to Allah",
                    "Allah is Great",
                    "Glory be to Allah",
                ],
                "correct_answer": 0,
                "explanation": "Bismillah means 'In the name of Allah'",
            },
            {
                "question": "Which surah is known as 'The Opening'?",
                "options": [
                    "Al-Fatiha",
                    "Al-Baqarah",
                    "Al-Ikhlas",
                    "An-Nas",
                ],
                "correct_answer": 0,
                "explanation": "Al-Fatiha is the first surah and means 'The Opening'",
            },
        ]

        # Save questions to file
        questions_file = Path(self.temp_dir) / "questions_pool.json"
        with open(questions_file, "w") as f:
            json.dump(questions, f)

        # Test loading
        self.manager.load_questions_pool()
        assert len(self.manager.questions_pool) == 2
        assert all(isinstance(q, dict) for q in self.manager.questions_pool)

        # Test question selection
        question = self.manager.get_next_question()
        assert question is not None
        assert "question" in question
        assert "options" in question
        assert "correct_answer" in question
        assert "explanation" in question

        # Test question rotation
        used_questions = set()
        for _ in range(4):  # Test multiple rotations
            question = self.manager.get_next_question()
            question_text = question["question"]
            used_questions.add(question_text)
        assert len(used_questions) == 2  # Should cycle through all questions

    @pytest.mark.asyncio
    async def test_scheduling(self):
        """Test question scheduling and timing"""
        # Mock current time to test scheduling
        mock_now = datetime.now(pytz.timezone("US/Eastern"))
        next_post_time = mock_now.replace(
            hour=9, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)

        with patch("datetime.datetime") as mock_dt:
            mock_dt.now.return_value = mock_now

            # Test schedule calculation
            schedule_time = self.manager.calculate_next_post_time()
            assert schedule_time == next_post_time

            # Test early morning schedule
            mock_dt.now.return_value = mock_now.replace(hour=3)
            schedule_time = self.manager.calculate_next_post_time()
            assert schedule_time.hour == 9
            assert schedule_time.date() == mock_now.date()

            # Test late night schedule
            mock_dt.now.return_value = mock_now.replace(hour=23)
            schedule_time = self.manager.calculate_next_post_time()
            assert schedule_time.hour == 9
            assert schedule_time.date() == (mock_now + timedelta(days=1)).date()

    @pytest.mark.asyncio
    async def test_user_responses(self):
        """Test user response handling"""
        # Setup test question
        self.manager.current_question = self.sample_question
        self.manager.current_responses = {}

        # Test correct answer
        user_id = 123456789
        response = 0  # Correct answer
        result = await self.manager.process_response(user_id, response)
        assert result["correct"] is True
        assert result["explanation"] == self.sample_question["explanation"]
        assert user_id in self.manager.current_responses
        assert self.manager.current_responses[user_id]["correct"] is True

        # Test incorrect answer
        user_id = 987654321
        response = 1  # Incorrect answer
        result = await self.manager.process_response(user_id, response)
        assert result["correct"] is False
        assert result["explanation"] == self.sample_question["explanation"]
        assert user_id in self.manager.current_responses
        assert self.manager.current_responses[user_id]["correct"] is False

        # Test duplicate response
        result = await self.manager.process_response(user_id, 0)
        assert result is None  # Should not allow duplicate responses

        # Test invalid answer index
        result = await self.manager.process_response(111111111, 5)
        assert result is None  # Should reject invalid answer index

    @pytest.mark.asyncio
    async def test_score_tracking(self):
        """Test user score tracking"""
        # Setup test data
        user_id = 123456789
        username = "TestUser"

        # Test score initialization
        self.manager.initialize_user_score(user_id, username)
        assert user_id in self.manager.user_scores
        assert self.manager.user_scores[user_id]["username"] == username
        assert self.manager.user_scores[user_id]["correct"] == 0
        assert self.manager.user_scores[user_id]["total"] == 0
        assert self.manager.user_scores[user_id]["streak"] == 0

        # Test correct answer tracking
        await self.manager.update_user_score(user_id, True)
        assert self.manager.user_scores[user_id]["correct"] == 1
        assert self.manager.user_scores[user_id]["total"] == 1
        assert self.manager.user_scores[user_id]["streak"] == 1

        # Test streak building
        await self.manager.update_user_score(user_id, True)
        assert self.manager.user_scores[user_id]["streak"] == 2

        # Test streak breaking
        await self.manager.update_user_score(user_id, False)
        assert self.manager.user_scores[user_id]["streak"] == 0
        assert self.manager.user_scores[user_id]["correct"] == 2
        assert self.manager.user_scores[user_id]["total"] == 3

    def test_data_persistence(self):
        """Test score and question state persistence"""
        # Setup test data
        user_id = 123456789
        username = "TestUser"
        self.manager.initialize_user_score(user_id, username)
        self.manager.user_scores[user_id]["correct"] = 5
        self.manager.user_scores[user_id]["total"] = 10
        self.manager.user_scores[user_id]["streak"] = 3

        # Test save operation
        self.manager.save_scores()
        scores_file = Path(self.temp_dir) / "user_scores.json"
        assert scores_file.exists()

        # Test load operation
        new_manager = DailyQuestionManager(data_dir=self.temp_dir)
        new_manager.load_scores()
        assert user_id in new_manager.user_scores
        assert new_manager.user_scores[user_id]["correct"] == 5
        assert new_manager.user_scores[user_id]["total"] == 10
        assert new_manager.user_scores[user_id]["streak"] == 3

    def test_error_handling(self):
        """Test error handling scenarios"""
        # Test missing questions file
        questions_file = Path(self.temp_dir) / "questions_pool.json"
        if questions_file.exists():
            questions_file.unlink()

        self.manager.load_questions_pool()
        assert len(self.manager.questions_pool) == 0  # Should handle gracefully

        # Test corrupted questions file
        with open(questions_file, "w") as f:
            f.write("invalid json")

        self.manager.load_questions_pool()
        assert len(self.manager.questions_pool) == 0  # Should handle gracefully

        # Test missing scores file
        scores_file = Path(self.temp_dir) / "user_scores.json"
        if scores_file.exists():
            scores_file.unlink()

        self.manager.load_scores()
        assert isinstance(self.manager.user_scores, dict)  # Should initialize empty

        # Test corrupted scores file
        with open(scores_file, "w") as f:
            f.write("invalid json")

        self.manager.load_scores()
        assert isinstance(self.manager.user_scores, dict)  # Should handle gracefully

    def test_leaderboard_generation(self):
        """Test leaderboard generation"""
        # Setup test data
        test_users = [
            (123, "User1", 10, 15, 2),  # 66.7% accuracy
            (456, "User2", 15, 20, 5),  # 75% accuracy
            (789, "User3", 5, 10, 1),  # 50% accuracy
        ]

        for user_id, username, correct, total, streak in test_users:
            self.manager.initialize_user_score(user_id, username)
            self.manager.user_scores[user_id]["correct"] = correct
            self.manager.user_scores[user_id]["total"] = total
            self.manager.user_scores[user_id]["streak"] = streak

        # Test top scores
        leaderboard = self.manager.generate_leaderboard()
        assert len(leaderboard) == 3

        # Verify sorting by accuracy
        assert leaderboard[0]["user_id"] == 456  # User2 (75%)
        assert leaderboard[1]["user_id"] == 123  # User1 (66.7%)
        assert leaderboard[2]["user_id"] == 789  # User3 (50%)

        # Test score formatting
        for entry in leaderboard:
            assert "username" in entry
            assert "correct" in entry
            assert "total" in entry
            assert "accuracy" in entry
            assert "streak" in entry
            assert isinstance(entry["accuracy"], float)

    def test_question_validation(self):
        """Test question validation"""
        # Test valid question
        valid_question = {
            "question": "Test Question?",
            "options": ["A", "B", "C", "D"],
            "correct_answer": 0,
            "explanation": "Test explanation",
        }
        assert self.manager.validate_question(valid_question) is True

        # Test missing fields
        invalid_questions = [
            {"question": "Test?"},  # Missing options
            {"options": ["A", "B"]},  # Missing question
            {"question": "Test?", "options": ["A"]},  # Too few options
            {
                "question": "Test?",
                "options": ["A", "B"],
                "correct_answer": 2,
            },  # Invalid answer index
        ]

        for question in invalid_questions:
            assert self.manager.validate_question(question) is False

    def test_question_rotation(self):
        """Test question rotation and history"""
        # Setup multiple questions
        questions = [
            {
                "question": f"Question {i}?",
                "options": ["A", "B", "C", "D"],
                "correct_answer": 0,
                "explanation": f"Explanation {i}",
            }
            for i in range(5)
        ]

        self.manager.questions_pool = questions.copy()
        used_questions = set()

        # Test complete rotation
        for _ in range(len(questions)):
            question = self.manager.get_next_question()
            question_text = question["question"]
            assert (
                question_text not in used_questions
            )  # Should not repeat until all used
            used_questions.add(question_text)

        assert len(used_questions) == len(questions)  # Should use all questions

        # Test rotation reset
        question = self.manager.get_next_question()
        assert question["question"] in used_questions  # Should start over

    def teardown_method(self):
        """Clean up test environment"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
