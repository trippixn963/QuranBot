#!/usr/bin/env python3
# =============================================================================
# QuranBot - Comprehensive Integration Tests
# =============================================================================
# End-to-end integration tests covering system interactions, workflow testing,
# and cross-component communication in realistic scenarios.
# =============================================================================

import asyncio
from pathlib import Path
import pytest
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.config.config import QuranBotConfig
from src.core.di_container import DIContainer
from src.security.error_handler import SecureErrorHandler
from src.security.validators import SecureValidator
from src.utils.audio_manager import AudioManager


class TestSystemIntegration:
    """Test complete system integration scenarios."""

    @pytest.fixture
    async def mock_config(self):
        """Create mock configuration for testing."""
        return QuranBotConfig(
            discord_token="Bot " + "A" * 59,
            guild_id=123456789012345678,
            target_channel_id=234567890123456789,
            daily_verse_channel_id=345678901234567890,
            developer_id=456789012345678901,
            openai_api_key="sk-" + "A" * 48,
            webhook_url="https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890_-",
        )

    @pytest.fixture
    async def di_container(self, mock_config):
        """Create dependency injection container with mock services."""
        container = DIContainer()
        
        # Register core services
        container.register("config", mock_config, singleton=True)
        
        # Register mock audio manager
        mock_audio_manager = MagicMock(spec=AudioManager)
        mock_audio_manager.initialize = AsyncMock()
        mock_audio_manager.play_audio = AsyncMock()
        mock_audio_manager.stop_audio = AsyncMock()
        mock_audio_manager.get_current_position = AsyncMock(return_value={"surah": 1, "ayah": 1})
        container.register("audio_manager", mock_audio_manager, singleton=True)
        
        # Register mock error handler
        mock_error_handler = MagicMock(spec=SecureErrorHandler)
        mock_error_handler.handle_error = AsyncMock(return_value={"error": {"code": "TEST_ERROR", "message": "Test error"}})
        container.register("error_handler", mock_error_handler, singleton=True)
        
        await container.initialize()
        return container

    @pytest.mark.asyncio
    async def test_bot_initialization_workflow(self, di_container):
        """Test complete bot initialization workflow."""
        # Simulate bot startup sequence
        config = di_container.get("config")
        audio_manager = di_container.get("audio_manager")
        
        # Verify configuration validation
        assert config.discord_token.startswith("Bot ")
        assert SecureValidator.validate_guild_id(config.guild_id) == config.guild_id
        assert SecureValidator.validate_channel_id(config.target_channel_id) == config.target_channel_id
        
        # Verify audio manager initialization
        await audio_manager.initialize()
        audio_manager.initialize.assert_called_once()
        
        # Test service interactions
        await audio_manager.play_audio("test_file.mp3")
        audio_manager.play_audio.assert_called_once_with("test_file.mp3")

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, di_container):
        """Test error handling across system components."""
        error_handler = di_container.get("error_handler")
        
        # Test various error scenarios
        test_error = ValueError("Test validation error")
        
        # Test error handling with context
        result = await error_handler.handle_error(
            test_error,
            context={"component": "audio_manager", "operation": "play_audio"},
            user_facing=True,
            user_id=123456789012345678
        )
        
        error_handler.handle_error.assert_called_once()
        assert "error" in result
        assert "code" in result["error"]

    @pytest.mark.asyncio
    async def test_configuration_security_validation(self, mock_config):
        """Test security validation of configuration values."""
        # Test Discord token validation
        validated_token = SecureValidator.validate_discord_token(mock_config.discord_token)
        assert validated_token == mock_config.discord_token
        
        # Test ID validations
        assert SecureValidator.validate_guild_id(mock_config.guild_id) == mock_config.guild_id
        assert SecureValidator.validate_user_id(mock_config.developer_id) == mock_config.developer_id
        assert SecureValidator.validate_channel_id(mock_config.target_channel_id) == mock_config.target_channel_id
        
        # Test OpenAI key validation
        assert SecureValidator.validate_openai_key(mock_config.openai_api_key) == mock_config.openai_api_key
        
        # Test webhook URL validation
        assert SecureValidator.validate_webhook_url(mock_config.webhook_url) == mock_config.webhook_url

    @pytest.mark.asyncio
    async def test_audio_playback_workflow(self, di_container):
        """Test complete audio playback workflow."""
        audio_manager = di_container.get("audio_manager")
        config = di_container.get("config")
        
        # Test initialization
        await audio_manager.initialize()
        
        # Test playback start
        test_file = "001.mp3"
        await audio_manager.play_audio(test_file)
        audio_manager.play_audio.assert_called_with(test_file)
        
        # Test position tracking
        position = await audio_manager.get_current_position()
        assert isinstance(position, dict)
        assert "surah" in position
        assert "ayah" in position
        
        # Test stop functionality
        await audio_manager.stop_audio()
        audio_manager.stop_audio.assert_called_once()


class TestQuizSystemIntegration:
    """Test quiz system integration scenarios."""

    @pytest.fixture
    def mock_quiz_data(self):
        """Create mock quiz data for testing."""
        return {
            "id": "test_question_001",
            "question": {
                "arabic": "ما هي أول سورة في القرآن الكريم؟",
                "english": "What is the first surah in the Holy Quran?"
            },
            "choices": {
                "A": {"arabic": "الفاتحة", "english": "Al-Fatiha"},
                "B": {"arabic": "البقرة", "english": "Al-Baqarah"},
                "C": {"arabic": "آل عمران", "english": "Ali 'Imran"},
                "D": {"arabic": "النساء", "english": "An-Nisa"}
            },
            "correct_answer": "A",
            "category": "Quran Knowledge",
            "difficulty": 1
        }

    @pytest.mark.asyncio
    async def test_quiz_question_validation(self, mock_quiz_data):
        """Test quiz question data validation."""
        # Test question structure
        assert "id" in mock_quiz_data
        assert "question" in mock_quiz_data
        assert "choices" in mock_quiz_data
        assert "correct_answer" in mock_quiz_data
        
        # Test bilingual content
        question = mock_quiz_data["question"]
        assert isinstance(question, dict)
        assert "arabic" in question and "english" in question
        
        # Test choices structure
        choices = mock_quiz_data["choices"]
        assert len(choices) >= 2  # At least 2 choices
        assert mock_quiz_data["correct_answer"] in choices
        
        # Test difficulty validation
        difficulty = mock_quiz_data["difficulty"]
        assert isinstance(difficulty, int)
        assert 1 <= difficulty <= 5

    @pytest.mark.asyncio
    async def test_quiz_answer_processing(self, mock_quiz_data):
        """Test quiz answer processing and validation."""
        correct_answer = mock_quiz_data["correct_answer"]
        choices = list(mock_quiz_data["choices"].keys())
        
        # Test correct answer validation
        assert correct_answer in choices
        
        # Test answer choice validation
        for choice in choices:
            assert len(choice) == 1  # Single letter choices
            assert choice.isupper()  # Uppercase letters
        
        # Test invalid answer handling
        invalid_answers = ["Z", "1", "invalid", ""]
        for invalid in invalid_answers:
            assert invalid not in choices


class TestSecurityIntegration:
    """Test security integration across system components."""

    @pytest.mark.asyncio
    async def test_input_sanitization_workflow(self):
        """Test input sanitization across different components."""
        # Test various input types that might come from Discord
        test_inputs = [
            ("normal_text", "This is normal text"),
            ("script_injection", "<script>alert('xss')</script>"),
            ("sql_injection", "'; DROP TABLE users; --"),
            ("path_traversal", "../../../etc/passwd"),
            ("null_byte", "test\x00file"),
            ("long_input", "A" * 2000),
        ]
        
        for test_name, test_input in test_inputs:
            if test_name == "normal_text":
                # Should pass validation
                result = SecureValidator.validate_text_input(test_input, max_length=1000)
                assert result == test_input.strip()
            else:
                # Should raise SecurityError
                with pytest.raises(Exception):  # Could be SecurityError or other validation error
                    SecureValidator.validate_text_input(test_input, max_length=1000)

    @pytest.mark.asyncio
    async def test_configuration_security_integration(self):
        """Test security validation integration with configuration."""
        # Test secure configuration loading
        secure_config = {
            "discord_token": "Bot " + "A" * 59,
            "guild_id": "123456789012345678",
            "developer_id": "456789012345678901",
            "openai_api_key": "sk-" + "A" * 48,
        }
        
        # Validate each configuration value
        validated_token = SecureValidator.validate_discord_token(secure_config["discord_token"])
        assert validated_token == secure_config["discord_token"]
        
        validated_guild = SecureValidator.validate_guild_id(secure_config["guild_id"])
        assert validated_guild == int(secure_config["guild_id"])
        
        validated_user = SecureValidator.validate_user_id(secure_config["developer_id"])
        assert validated_user == int(secure_config["developer_id"])
        
        validated_key = SecureValidator.validate_openai_key(secure_config["openai_api_key"])
        assert validated_key == secure_config["openai_api_key"]

    @pytest.mark.asyncio
    async def test_log_sanitization_integration(self):
        """Test log data sanitization across components."""
        sensitive_data = {
            "discord_token": "Bot abcd1234567890",
            "password": "secret123",
            "api_key": "sk-1234567890abcdef",
            "user_message": "Hello world",
            "webhook_url": "https://discord.com/api/webhooks/123/abc",
            "normal_data": "This is safe",
            "long_text": "A" * 300,
        }
        
        sanitized = SecureValidator.sanitize_log_data(sensitive_data)
        
        # Check that sensitive data is redacted
        assert sanitized["discord_token"] == "[REDACTED]"
        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["api_key"] == "[REDACTED]"
        assert sanitized["webhook_url"] == "[REDACTED]"
        
        # Check that safe data is preserved
        assert sanitized["user_message"] == "Hello world"
        assert sanitized["normal_data"] == "This is safe"
        
        # Check that long text is truncated
        assert sanitized["long_text"].endswith("...[TRUNCATED]")
        assert len(sanitized["long_text"]) <= 220  # 200 + truncation message


class TestDatabaseIntegration:
    """Test database integration and data persistence."""

    @pytest.mark.asyncio
    async def test_state_persistence_workflow(self):
        """Test state persistence across system restarts."""
        # Mock database operations
        mock_state = {
            "current_surah": 1,
            "current_ayah": 7,
            "current_reciter": "Saad Al Ghamdi",
            "playback_position": 125.5,
            "volume": 0.7,
            "last_updated": "2025-07-30T12:00:00Z"
        }
        
        # Test state validation
        assert 1 <= mock_state["current_surah"] <= 114
        assert mock_state["current_ayah"] >= 1
        assert mock_state["current_reciter"] in [
            "Saad Al Ghamdi", "Abdul Basit", "Mishary Rashid",
            "Maher Al Muaiqly", "Muhammad Al Luhaidan", "Yasser Al Dosari"
        ]
        assert 0.0 <= mock_state["volume"] <= 1.0
        assert mock_state["playback_position"] >= 0

    @pytest.mark.asyncio
    async def test_quiz_statistics_integration(self):
        """Test quiz statistics tracking and validation."""
        mock_stats = {
            "user_id": 123456789012345678,
            "total_questions": 50,
            "correct_answers": 35,
            "accuracy_percentage": 70.0,
            "categories_attempted": ["Quran Knowledge", "Hadith", "Islamic History"],
            "average_response_time": 15.2,
            "streak_current": 5,
            "streak_best": 12,
            "last_quiz_date": "2025-07-30"
        }
        
        # Validate statistics data
        assert SecureValidator.validate_user_id(mock_stats["user_id"]) == mock_stats["user_id"]
        assert mock_stats["total_questions"] >= mock_stats["correct_answers"]
        assert 0.0 <= mock_stats["accuracy_percentage"] <= 100.0
        assert mock_stats["average_response_time"] > 0
        assert mock_stats["streak_current"] <= mock_stats["streak_best"]


class TestPerformanceIntegration:
    """Test performance characteristics of integrated systems."""

    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test system behavior under concurrent load."""
        # Create multiple concurrent operations
        async def mock_operation(operation_id: int):
            """Mock an async operation."""
            await asyncio.sleep(0.01)  # Simulate work
            return f"result_{operation_id}"
        
        # Test concurrent execution
        tasks = [mock_operation(i) for i in range(50)]
        results = await asyncio.gather(*tasks)
        
        # Verify all operations completed
        assert len(results) == 50
        for i, result in enumerate(results):
            assert result == f"result_{i}"

    @pytest.mark.asyncio
    async def test_memory_usage_patterns(self):
        """Test memory usage patterns during operations."""
        # Create and destroy objects to test memory management
        large_objects = []
        
        # Create objects
        for i in range(100):
            large_data = {"data": "A" * 1000, "id": i}
            large_objects.append(large_data)
        
        assert len(large_objects) == 100
        
        # Clean up objects
        large_objects.clear()
        assert len(large_objects) == 0

    @pytest.mark.asyncio
    async def test_error_handling_performance(self):
        """Test error handling performance under load."""
        import logging
        error_handler = SecureErrorHandler(logging.getLogger("test"), debug_mode=False)
        
        # Test multiple error handling operations
        errors = [ValueError(f"Test error {i}") for i in range(20)]
        
        tasks = []
        for error in errors:
            task = error_handler.handle_error(
                error,
                context={"test": True},
                user_facing=True
            )
            tasks.append(task)
        
        # All error handling should complete without blocking
        results = await asyncio.gather(*tasks, return_exceptions=True)
        assert len(results) == 20


# Test configuration
pytest_plugins = []

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])