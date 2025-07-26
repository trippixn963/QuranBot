# =============================================================================
# QuranBot - Exception Hierarchy Tests
# =============================================================================
# Comprehensive tests for the custom exception hierarchy including context
# support, error handling decorators, and specific exception types.
# =============================================================================

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest

from src.core.exceptions import (
    AudioError,
    BackupError,
    ConfigurationError,
    DiscordAPIError,
    FFmpegError,
    QuizError,
    QuranBotError,
    RateLimitError,
    ServiceError,
    StateError,
    ValidationError,
    VoiceConnectionError,
    WebhookError,
    create_error_context,
    handle_errors,
)
from src.core.structured_logger import StructuredLogger


class TestQuranBotError:
    """Test the base QuranBotError class"""

    def test_basic_error_creation(self):
        """Test creating a basic QuranBotError"""
        error = QuranBotError("Test error message")

        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.context == {}
        assert error.original_error is None
        assert error.timestamp is not None

    def test_error_with_context(self):
        """Test creating error with context"""
        context = {"user_id": 12345, "operation": "test_operation"}
        error = QuranBotError("Test error", context=context)

        assert error.context == context
        assert error.context["user_id"] == 12345
        assert error.context["operation"] == "test_operation"

    def test_error_with_original_error(self):
        """Test creating error with original exception"""
        original = ValueError("Original error")
        error = QuranBotError("Wrapped error", original_error=original)

        assert error.original_error == original
        assert str(error.original_error) == "Original error"

    def test_error_timestamp(self):
        """Test that error timestamp is properly set"""
        error = QuranBotError("Test error")

        # Timestamp should be recent (within last minute)
        time_diff = datetime.now(UTC) - error.timestamp
        assert time_diff.total_seconds() < 60


class TestAudioError:
    """Test audio-related exceptions"""

    def test_basic_audio_error(self):
        """Test creating a basic AudioError"""
        error = AudioError("Audio playback failed")

        assert isinstance(error, QuranBotError)
        assert str(error) == "Audio playback failed"

    def test_voice_connection_error(self):
        """Test VoiceConnectionError with specific context"""
        error = VoiceConnectionError(
            "Failed to connect to voice channel",
            voice_channel_id=123456789,
            guild_id=987654321,
        )

        assert isinstance(error, AudioError)
        assert error.context["voice_channel_id"] == 123456789
        assert error.context["guild_id"] == 987654321

    def test_ffmpeg_error(self):
        """Test FFmpegError with command context"""
        error = FFmpegError(
            "FFmpeg processing failed",
            ffmpeg_command="ffmpeg -i input.mp3 output.wav",
            ffmpeg_output="Error: Invalid codec",
        )

        assert isinstance(error, AudioError)
        assert error.context["ffmpeg_command"] == "ffmpeg -i input.mp3 output.wav"
        assert error.context["ffmpeg_output"] == "Error: Invalid codec"


class TestConfigurationError:
    """Test configuration-related exceptions"""

    def test_basic_configuration_error(self):
        """Test creating a basic ConfigurationError"""
        error = ConfigurationError("Missing required configuration")

        assert isinstance(error, QuranBotError)
        assert str(error) == "Missing required configuration"

    def test_configuration_error_with_details(self):
        """Test ConfigurationError with configuration details"""
        context = {
            "config_key": "DISCORD_TOKEN",
            "expected_type": "string",
            "actual_value": None,
        }
        error = ConfigurationError("Invalid configuration value", context=context)

        assert error.context["config_key"] == "DISCORD_TOKEN"
        assert error.context["expected_type"] == "string"
        assert error.context["actual_value"] is None


class TestStateError:
    """Test state management exceptions"""

    def test_basic_state_error(self):
        """Test creating a basic StateError"""
        error = StateError("State file corruption detected")

        assert isinstance(error, QuranBotError)
        assert str(error) == "State file corruption detected"

    def test_backup_error(self):
        """Test BackupError with backup-specific context"""
        error = BackupError(
            "Backup creation failed",
            backup_path="/path/to/backup.zip",
            backup_type="daily",
        )

        assert isinstance(error, StateError)
        assert error.context["backup_path"] == "/path/to/backup.zip"
        assert error.context["backup_type"] == "daily"


class TestValidationError:
    """Test validation exceptions"""

    def test_basic_validation_error(self):
        """Test creating a basic ValidationError"""
        error = ValidationError("Input validation failed")

        assert isinstance(error, QuranBotError)
        assert str(error) == "Input validation failed"

    def test_validation_error_with_field_context(self):
        """Test ValidationError with field details"""
        context = {
            "field_name": "surah_number",
            "field_value": "invalid",
            "expected_range": "1-114",
        }
        error = ValidationError("Invalid surah number", context=context)

        assert error.context["field_name"] == "surah_number"
        assert error.context["field_value"] == "invalid"
        assert error.context["expected_range"] == "1-114"


class TestRateLimitError:
    """Test rate limiting exceptions"""

    def test_basic_rate_limit_error(self):
        """Test creating a basic RateLimitError"""
        error = RateLimitError("Rate limit exceeded")

        assert isinstance(error, QuranBotError)
        assert str(error) == "Rate limit exceeded"

    def test_rate_limit_error_with_details(self):
        """Test RateLimitError with rate limit details"""
        context = {
            "limit_type": "discord_api",
            "requests_made": 100,
            "requests_allowed": 50,
            "reset_time": "2024-01-01T12:00:00Z",
        }
        error = RateLimitError("Discord API rate limit exceeded", context=context)

        assert error.context["limit_type"] == "discord_api"
        assert error.context["requests_made"] == 100
        assert error.context["requests_allowed"] == 50


class TestServiceError:
    """Test service-related exceptions"""

    def test_basic_service_error(self):
        """Test creating a basic ServiceError"""
        error = ServiceError("Service initialization failed")

        assert isinstance(error, QuranBotError)
        assert str(error) == "Service initialization failed"

    def test_service_error_with_service_context(self):
        """Test ServiceError with service details"""
        error = ServiceError(
            "Audio service failed to start",
            service_name="AudioService",
            operation="initialize",
        )

        assert error.context["service_name"] == "AudioService"
        assert error.context["operation"] == "initialize"


class TestDiscordAPIError:
    """Test Discord API exceptions"""

    def test_basic_discord_api_error(self):
        """Test creating a basic DiscordAPIError"""
        error = DiscordAPIError("Discord API request failed")

        assert isinstance(error, QuranBotError)
        assert str(error) == "Discord API request failed"

    def test_discord_api_error_with_details(self):
        """Test DiscordAPIError with API details"""
        error = DiscordAPIError(
            "API request failed",
            status_code=429,
            discord_error="Rate limit exceeded",
            endpoint="/api/v10/channels/123/messages",
        )

        assert error.context["status_code"] == 429
        assert error.context["discord_error"] == "Rate limit exceeded"
        assert error.context["endpoint"] == "/api/v10/channels/123/messages"

    def test_webhook_error(self):
        """Test WebhookError with webhook details"""
        error = WebhookError(
            "Webhook delivery failed",
            webhook_url="https://discord.com/api/webhooks/123/abc",
            status_code=404,
        )

        assert isinstance(error, DiscordAPIError)
        assert (
            error.context["webhook_url"] == "https://discord.com/api/webhooks/123/abc"
        )
        assert error.context["status_code"] == 404


class TestQuizError:
    """Test quiz system exceptions"""

    def test_basic_quiz_error(self):
        """Test creating a basic QuizError"""
        error = QuizError("Quiz loading failed")

        assert isinstance(error, QuranBotError)
        assert str(error) == "Quiz loading failed"

    def test_quiz_error_with_details(self):
        """Test QuizError with quiz details"""
        error = QuizError(
            "Invalid quiz question",
            quiz_id="islamic_knowledge_1",
            question_id="q_001",
            user_id=123456789,
        )

        assert error.context["quiz_id"] == "islamic_knowledge_1"
        assert error.context["question_id"] == "q_001"
        assert error.context["user_id"] == 123456789


class TestErrorHandlerDecorator:
    """Test the error handling decorator"""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock structured logger"""
        logger = Mock(spec=StructuredLogger)
        logger._logger = Mock()
        # Mock async methods
        logger.error = AsyncMock()
        logger.warning = AsyncMock()
        logger.info = AsyncMock()
        return logger

    def test_sync_function_success(self, mock_logger):
        """Test decorator with successful sync function"""

        @handle_errors(mock_logger, reraise=False)
        def test_function(x, y):
            return x + y

        result = test_function(2, 3)
        assert result == 5

        # Logger should not be called for successful execution
        mock_logger._logger.error.assert_not_called()

    def test_sync_function_quranbot_error(self, mock_logger):
        """Test decorator with QuranBot error in sync function"""

        @handle_errors(mock_logger, reraise=False)
        def test_function():
            raise AudioError("Test audio error", context={"test": "value"})

        result = test_function()
        assert result is None

        # Logger should be called with QuranBot error details
        mock_logger._logger.error.assert_called_once()
        call_args = mock_logger._logger.error.call_args
        assert "QuranBot error in test_function" in call_args[0][0]
        assert "AudioError" in str(call_args)

    def test_sync_function_generic_error(self, mock_logger):
        """Test decorator with generic error in sync function"""

        @handle_errors(mock_logger, reraise=False)
        def test_function():
            raise ValueError("Generic error")

        result = test_function()
        assert result is None

        # Logger should be called with generic error details
        mock_logger._logger.error.assert_called_once()
        call_args = mock_logger._logger.error.call_args
        assert "Unexpected error in test_function" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_async_function_success(self, mock_logger):
        """Test decorator with successful async function"""

        @handle_errors(mock_logger, reraise=False)
        async def test_async_function(x, y):
            await asyncio.sleep(0.01)  # Simulate async work
            return x * y

        result = await test_async_function(3, 4)
        assert result == 12

        # Logger should not be called for successful execution
        mock_logger._logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_async_function_error(self, mock_logger):
        """Test decorator with error in async function"""

        @handle_errors(mock_logger, reraise=False)
        async def test_async_function():
            await asyncio.sleep(0.01)
            raise ConfigurationError("Test config error")

        result = await test_async_function()
        assert result is None

        # Logger should be called with error details
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "QuranBot error in test_async_function" in call_args[0][0]

    def test_reraise_behavior(self, mock_logger):
        """Test decorator with reraise=True"""

        @handle_errors(mock_logger, reraise=True)
        def test_function():
            raise AudioError("Test error")

        with pytest.raises(AudioError):
            test_function()

        # Logger should still be called even with reraise
        mock_logger._logger.error.assert_called_once()


class TestErrorContextUtilities:
    """Test error context utility functions"""

    def test_create_error_context(self):
        """Test create_error_context utility function"""
        context = create_error_context(
            operation="test_operation", user_id=123456, component="audio_manager"
        )

        assert context["operation"] == "test_operation"
        assert context["user_id"] == 123456
        assert context["component"] == "audio_manager"
        assert "timestamp" in context

        # Verify timestamp format
        timestamp = datetime.fromisoformat(context["timestamp"].replace("Z", "+00:00"))
        assert isinstance(timestamp, datetime)


class TestExceptionInheritance:
    """Test exception inheritance hierarchy"""

    def test_inheritance_structure(self):
        """Test that all exceptions inherit correctly"""
        # Test direct inheritance from QuranBotError
        assert issubclass(AudioError, QuranBotError)
        assert issubclass(ConfigurationError, QuranBotError)
        assert issubclass(StateError, QuranBotError)
        assert issubclass(ValidationError, QuranBotError)
        assert issubclass(RateLimitError, QuranBotError)
        assert issubclass(ServiceError, QuranBotError)
        assert issubclass(DiscordAPIError, QuranBotError)
        assert issubclass(QuizError, QuranBotError)

        # Test specific exception inheritance
        assert issubclass(VoiceConnectionError, AudioError)
        assert issubclass(FFmpegError, AudioError)
        assert issubclass(WebhookError, DiscordAPIError)
        assert issubclass(BackupError, StateError)

    def test_isinstance_behavior(self):
        """Test isinstance behavior with exception hierarchy"""
        voice_error = VoiceConnectionError("Test voice error")

        # Should be instance of parent classes
        assert isinstance(voice_error, VoiceConnectionError)
        assert isinstance(voice_error, AudioError)
        assert isinstance(voice_error, QuranBotError)
        assert isinstance(voice_error, Exception)

        # Should not be instance of sibling classes
        assert not isinstance(voice_error, ConfigurationError)
        assert not isinstance(voice_error, FFmpegError)


class TestRealWorldScenarios:
    """Test real-world error scenarios"""

    def test_audio_playback_failure_scenario(self):
        """Test a realistic audio playback failure scenario"""
        # Simulate FFmpeg failure during audio processing
        original_error = RuntimeError("FFmpeg process exited with code 1")

        error = FFmpegError(
            "Audio encoding failed during playback",
            ffmpeg_command="ffmpeg -i /path/to/audio.mp3 -f s16le pipe:1",
            ffmpeg_output="Error: Unsupported audio format",
            context={
                "audio_file": "/path/to/audio.mp3",
                "user_id": 123456789,
                "guild_id": 987654321,
            },
            original_error=original_error,
        )

        assert isinstance(error, FFmpegError)
        assert isinstance(error, AudioError)
        assert isinstance(error, QuranBotError)

        assert error.context["ffmpeg_command"] is not None
        assert error.context["ffmpeg_output"] == "Error: Unsupported audio format"
        assert error.context["audio_file"] == "/path/to/audio.mp3"
        assert error.original_error == original_error

    def test_configuration_validation_scenario(self):
        """Test a realistic configuration validation scenario"""
        error = ConfigurationError(
            "Invalid Discord token format",
            context={
                "config_key": "DISCORD_TOKEN",
                "validation_rule": "Must start with 'Bot ' or be a valid token format",
                "provided_value_length": 5,  # Don't log actual token
                "config_source": "environment_variable",
            },
        )

        assert isinstance(error, ConfigurationError)
        assert error.context["config_key"] == "DISCORD_TOKEN"
        assert error.context["validation_rule"] is not None
        assert error.context["provided_value_length"] == 5

    def test_quiz_system_failure_scenario(self):
        """Test a realistic quiz system failure scenario"""
        error = QuizError(
            "Quiz question validation failed",
            quiz_id="daily_islamic_quiz",
            question_id="quran_verse_001",
            user_id=123456789,
            context={
                "validation_errors": [
                    "Missing correct answer",
                    "Invalid choice format",
                ],
                "question_content": "What is the first surah of the Quran?",
                "attempted_operation": "load_question",
            },
        )

        assert isinstance(error, QuizError)
        assert error.context["quiz_id"] == "daily_islamic_quiz"
        assert error.context["question_id"] == "quran_verse_001"
        assert error.context["user_id"] == 123456789
        assert "validation_errors" in error.context
        assert len(error.context["validation_errors"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
