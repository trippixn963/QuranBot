# =============================================================================
# QuranBot - Modern Webhook Logger Tests
# =============================================================================
# Comprehensive test suite for the modernized webhook logger implementation.
# Tests cover configuration, rate limiting, message formatting, error handling,
# and integration with the dependency injection container.
# =============================================================================

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest

from src.core.structured_logger import StructuredLogger
from src.core.webhook_logger import (
    EmbedField,
    LogLevel,
    ModernWebhookLogger,
    RateLimitTracker,
    WebhookConfig,
    WebhookFormatter,
    WebhookMessage,
    WebhookSender,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def webhook_config():
    """Create a test webhook configuration."""
    return WebhookConfig(
        webhook_url="https://discord.com/api/webhooks/123456789/test_webhook_token",
        owner_user_id=155149108183695360,
        max_logs_per_minute=5,
        request_timeout=10,
        retry_attempts=2,
        timezone="US/Eastern",
    )


@pytest.fixture
def mock_logger():
    """Create a mock structured logger."""
    logger = AsyncMock(spec=StructuredLogger)
    return logger


@pytest.fixture
def webhook_formatter(webhook_config):
    """Create a webhook formatter instance."""
    return WebhookFormatter(webhook_config)


@pytest.fixture
def webhook_sender(webhook_config, mock_logger):
    """Create a webhook sender instance."""
    return WebhookSender(webhook_config, mock_logger)


@pytest.fixture
def modern_webhook_logger(webhook_config, mock_logger):
    """Create a modern webhook logger instance."""
    return ModernWebhookLogger(webhook_config, mock_logger)


# =============================================================================
# Configuration Tests
# =============================================================================


class TestWebhookConfig:
    """Test webhook configuration validation and behavior."""

    def test_valid_config_creation(self):
        """Test creating a valid webhook configuration."""
        config = WebhookConfig(
            webhook_url="https://discord.com/api/webhooks/123/token",
            owner_user_id=12345,
            max_logs_per_minute=10,
        )

        assert config.webhook_url == "https://discord.com/api/webhooks/123/token"
        assert config.owner_user_id == 12345
        assert config.max_logs_per_minute == 10
        assert config.timezone == "US/Eastern"  # Default value

    def test_empty_webhook_url_raises_error(self):
        """Test that empty webhook URL raises ValueError."""
        with pytest.raises(ValueError, match="webhook_url is required"):
            WebhookConfig(webhook_url="")

    def test_invalid_rate_limit_raises_error(self):
        """Test that invalid rate limit raises ValueError."""
        with pytest.raises(ValueError, match="max_logs_per_minute must be positive"):
            WebhookConfig(
                webhook_url="https://discord.com/api/webhooks/123/token",
                max_logs_per_minute=0,
            )

    def test_invalid_timeout_raises_error(self):
        """Test that invalid timeout raises ValueError."""
        with pytest.raises(ValueError, match="request_timeout must be positive"):
            WebhookConfig(
                webhook_url="https://discord.com/api/webhooks/123/token",
                request_timeout=0,
            )


class TestEmbedField:
    """Test embed field validation and truncation."""

    def test_valid_field_creation(self):
        """Test creating a valid embed field."""
        field = EmbedField(name="Test Field", value="Test Value", inline=True)

        assert field.name == "Test Field"
        assert field.value == "Test Value"
        assert field.inline is True

    def test_long_name_truncation(self):
        """Test that long field names are truncated."""
        long_name = "x" * 300
        field = EmbedField(name=long_name, value="Test Value")

        assert len(field.name) == 256
        assert field.name.endswith("...")

    def test_long_value_truncation(self):
        """Test that long field values are truncated."""
        long_value = "x" * 2000
        field = EmbedField(name="Test", value=long_value)

        assert len(field.value) == 1024
        assert field.value.endswith("...")


class TestWebhookMessage:
    """Test webhook message creation and validation."""

    def test_message_with_default_timestamp(self):
        """Test that message gets default timestamp if not provided."""
        message = WebhookMessage(title="Test", description="Description")

        assert message.timestamp is not None
        assert abs(message.timestamp.timestamp() - time.time()) < 1

    def test_message_with_custom_timestamp(self):
        """Test message with custom timestamp."""
        from datetime import datetime

        custom_time = datetime(2024, 1, 1, 12, 0, 0)
        message = WebhookMessage(
            title="Test", description="Description", timestamp=custom_time
        )

        assert message.timestamp == custom_time

    def test_message_with_fields(self):
        """Test message with embed fields."""
        fields = [
            EmbedField("Field 1", "Value 1", True),
            EmbedField("Field 2", "Value 2", False),
        ]
        message = WebhookMessage(title="Test", description="Description", fields=fields)

        assert len(message.fields) == 2
        assert message.fields[0].name == "Field 1"
        assert message.fields[1].inline is False

    def test_message_with_avatar_info(self):
        """Test message with user avatar and author info."""
        message = WebhookMessage(
            title="User Activity",
            description="User did something",
            author_name="TestUser",
            author_icon_url="https://cdn.discordapp.com/avatars/123/avatar.png",
            author_url="https://discord.com/users/123456789",
            thumbnail_url="https://example.com/thumb.png",
        )

        assert message.author_name == "TestUser"
        assert (
            message.author_icon_url
            == "https://cdn.discordapp.com/avatars/123/avatar.png"
        )
        assert message.author_url == "https://discord.com/users/123456789"
        assert message.thumbnail_url == "https://example.com/thumb.png"


# =============================================================================
# Rate Limiting Tests
# =============================================================================


class TestRateLimitTracker:
    """Test rate limiting functionality."""

    @pytest.mark.asyncio
    async def test_initial_requests_allowed(self):
        """Test that initial requests within limit are allowed."""
        tracker = RateLimitTracker(max_requests=3, window_seconds=60)

        assert await tracker.can_proceed() is True
        assert await tracker.can_proceed() is True
        assert await tracker.can_proceed() is True

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self):
        """Test that requests are blocked when rate limit is exceeded."""
        tracker = RateLimitTracker(max_requests=2, window_seconds=60)

        assert await tracker.can_proceed() is True
        assert await tracker.can_proceed() is True
        assert await tracker.can_proceed() is False  # Should be blocked

    @pytest.mark.asyncio
    async def test_rate_limit_window_expiry(self):
        """Test that rate limit resets after window expires."""
        tracker = RateLimitTracker(max_requests=1, window_seconds=1)

        assert await tracker.can_proceed() is True
        assert await tracker.can_proceed() is False  # Blocked

        # Wait for window to expire
        await asyncio.sleep(1.1)

        assert await tracker.can_proceed() is True  # Should be allowed again

    @pytest.mark.asyncio
    async def test_retry_after_calculation(self):
        """Test retry after time calculation."""
        tracker = RateLimitTracker(max_requests=1, window_seconds=60)

        await tracker.can_proceed()  # Use up the limit

        retry_after = await tracker.get_retry_after()
        assert 55 <= retry_after <= 60  # Should be close to window size


# =============================================================================
# Message Formatting Tests
# =============================================================================


class TestWebhookFormatter:
    """Test webhook message formatting."""

    def test_basic_message_formatting(self, webhook_formatter):
        """Test basic message formatting."""
        message = WebhookMessage(
            title="Test Title", description="Test Description", level=LogLevel.INFO
        )

        payload = webhook_formatter.format_message(message)

        assert "embeds" in payload
        assert len(payload["embeds"]) == 1

        embed = payload["embeds"][0]
        assert "ℹ️ Test Title" in embed["title"]
        assert embed["description"] == "Test Description"
        assert embed["color"] == 0x3498DB  # Blue for INFO

    def test_message_with_fields(self, webhook_formatter):
        """Test message formatting with fields."""
        fields = [
            EmbedField("Field 1", "Value 1", True),
            EmbedField("Field 2", "Value 2", False),
        ]
        message = WebhookMessage(title="Test", description="Description", fields=fields)

        payload = webhook_formatter.format_message(message)
        embed = payload["embeds"][0]

        assert "fields" in embed
        assert len(embed["fields"]) == 2
        assert embed["fields"][0]["name"] == "Field 1"
        assert embed["fields"][0]["inline"] is True
        assert embed["fields"][1]["inline"] is False

    def test_message_with_content(self, webhook_formatter):
        """Test message formatting with content (pings)."""
        message = WebhookMessage(
            title="Test", description="Description", content="<@123456789> Alert!"
        )

        payload = webhook_formatter.format_message(message)

        assert payload["content"] == "<@123456789> Alert!"

    def test_message_with_avatar_formatting(self, webhook_formatter):
        """Test message formatting with user avatar and author info."""
        message = WebhookMessage(
            title="User Activity",
            description="User performed an action",
            author_name="TestUser",
            author_icon_url="https://cdn.discordapp.com/avatars/123/avatar.png",
            author_url="https://discord.com/users/123456789",
            thumbnail_url="https://example.com/thumb.png",
            image_url="https://example.com/image.png",
        )

        payload = webhook_formatter.format_message(message)
        embed = payload["embeds"][0]

        # Check author section
        assert "author" in embed
        assert embed["author"]["name"] == "TestUser"
        assert (
            embed["author"]["icon_url"]
            == "https://cdn.discordapp.com/avatars/123/avatar.png"
        )
        assert embed["author"]["url"] == "https://discord.com/users/123456789"

        # Check thumbnail and image
        assert embed["thumbnail"]["url"] == "https://example.com/thumb.png"
        assert embed["image"]["url"] == "https://example.com/image.png"

    def test_different_log_levels(self, webhook_formatter):
        """Test formatting for different log levels."""
        test_cases = [
            (LogLevel.ERROR, "❌", 0xE74C3C),
            (LogLevel.WARNING, "⚠️", 0xF39C12),
            (LogLevel.SUCCESS, "✅", 0x27AE60),
            (LogLevel.CRITICAL, "🚨", 0x8B0000),
        ]

        for level, emoji, color in test_cases:
            message = WebhookMessage(
                title="Test", description="Description", level=level
            )

            payload = webhook_formatter.format_message(message)
            embed = payload["embeds"][0]

            assert emoji in embed["title"]
            assert embed["color"] == color

    def test_description_truncation(self, webhook_formatter):
        """Test that long descriptions are truncated."""
        long_description = "x" * 5000
        message = WebhookMessage(title="Test", description=long_description)

        payload = webhook_formatter.format_message(message)
        embed = payload["embeds"][0]

        assert len(embed["description"]) <= 4096
        assert embed["description"].endswith("...")

    def test_too_many_fields_limited(self, webhook_formatter):
        """Test that too many fields are limited to Discord's max."""
        fields = [EmbedField(f"Field {i}", f"Value {i}") for i in range(30)]
        message = WebhookMessage(title="Test", description="Description", fields=fields)

        payload = webhook_formatter.format_message(message)
        embed = payload["embeds"][0]

        assert len(embed["fields"]) == 25  # Discord's limit


# =============================================================================
# Webhook Sender Tests
# =============================================================================


class TestWebhookSender:
    """Test webhook sending functionality."""

    @pytest.mark.asyncio
    async def test_successful_webhook_send(self, webhook_sender, mock_logger):
        """Test successful webhook sending."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            # Mock successful response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_session.post.return_value.__aenter__.return_value = mock_response

            webhook_sender.session = mock_session

            payload = {"test": "payload"}
            result = await webhook_sender.send_webhook(payload)

            assert result is True
            mock_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_webhook_rate_limited_by_discord(self, webhook_sender, mock_logger):
        """Test handling of Discord rate limiting."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            # Mock rate limited response
            mock_response = AsyncMock()
            mock_response.status = 429
            mock_response.headers = {"Retry-After": "5"}
            mock_session.post.return_value.__aenter__.return_value = mock_response

            webhook_sender.session = mock_session

            with patch("asyncio.sleep") as mock_sleep:
                payload = {"test": "payload"}
                result = await webhook_sender.send_webhook(payload)

                assert result is False
                mock_logger.warning.assert_called()
                # Should have attempted retry with sleep
                mock_sleep.assert_called()

    @pytest.mark.asyncio
    async def test_webhook_timeout_handling(self, webhook_sender, mock_logger):
        """Test handling of request timeouts."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            # Mock timeout
            mock_session.post.side_effect = asyncio.TimeoutError()
            webhook_sender.session = mock_session

            payload = {"test": "payload"}
            result = await webhook_sender.send_webhook(payload)

            assert result is False
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_webhook_sender_closed(self, webhook_sender, mock_logger):
        """Test that closed sender doesn't send requests."""
        await webhook_sender.close()

        payload = {"test": "payload"}
        result = await webhook_sender.send_webhook(payload)

        assert result is False
        mock_logger.warning.assert_called_with(
            "Webhook sender not initialized or closed"
        )


# =============================================================================
# Modern Webhook Logger Tests
# =============================================================================


class TestModernWebhookLogger:
    """Test the main webhook logger functionality."""

    @pytest.mark.asyncio
    async def test_initialization_success(self, modern_webhook_logger, mock_logger):
        """Test successful webhook logger initialization."""
        with patch.object(modern_webhook_logger.sender, "initialize") as mock_init:
            with patch.object(
                modern_webhook_logger, "_send_heartbeat"
            ) as mock_heartbeat:
                mock_init.return_value = None
                mock_heartbeat.return_value = None

                result = await modern_webhook_logger.initialize()

                assert result is True
                assert modern_webhook_logger.initialized is True
                mock_init.assert_called_once()
                mock_heartbeat.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialization_failure(self, modern_webhook_logger, mock_logger):
        """Test webhook logger initialization failure."""
        with patch.object(modern_webhook_logger.sender, "initialize") as mock_init:
            mock_init.side_effect = Exception("Test error")

            result = await modern_webhook_logger.initialize()

            assert result is False
            assert modern_webhook_logger.initialized is False
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_log_error_with_ping(self, modern_webhook_logger, mock_logger):
        """Test error logging with owner ping."""
        modern_webhook_logger.initialized = True

        with patch.object(modern_webhook_logger, "_send_message") as mock_send:
            mock_send.return_value = True

            result = await modern_webhook_logger.log_error(
                "Test Error",
                "This is a test error",
                exception=ValueError("Test exception"),
                context={"key": "value"},
                ping_owner=True,
            )

            assert result is True
            mock_send.assert_called_once()

            # Check that the message was formatted correctly
            call_args = mock_send.call_args[0][0]  # First positional argument
            assert call_args.title == "Test Error"
            assert call_args.level == LogLevel.ERROR
            assert call_args.content is not None  # Should have ping content
            assert len(call_args.fields) >= 2  # Exception type and message

    @pytest.mark.asyncio
    async def test_log_critical_with_ping(self, modern_webhook_logger, mock_logger):
        """Test critical error logging with owner ping."""
        modern_webhook_logger.initialized = True

        with patch.object(modern_webhook_logger, "_send_message") as mock_send:
            mock_send.return_value = True

            result = await modern_webhook_logger.log_critical(
                "Critical Error", "This is critical", ping_owner=True
            )

            assert result is True
            mock_send.assert_called_once()

            call_args = mock_send.call_args[0][0]
            assert call_args.level == LogLevel.CRITICAL
            assert "🚨 **CRITICAL ERROR** 🚨" in call_args.description
            assert call_args.content is not None  # Should have ping content

    @pytest.mark.asyncio
    async def test_rate_limiting_prevents_send(
        self, modern_webhook_logger, mock_logger
    ):
        """Test that rate limiting prevents message sending."""
        modern_webhook_logger.initialized = True

        with patch.object(
            modern_webhook_logger.rate_limiter, "can_proceed"
        ) as mock_can_proceed:
            mock_can_proceed.return_value = False

            with patch.object(
                modern_webhook_logger.rate_limiter, "get_retry_after"
            ) as mock_retry:
                mock_retry.return_value = 30.0

                result = await modern_webhook_logger.log_info("Test", "Description")

                assert result is False
                mock_logger.debug.assert_called()

    @pytest.mark.asyncio
    async def test_shutdown_sequence(self, modern_webhook_logger, mock_logger):
        """Test proper shutdown sequence."""
        modern_webhook_logger.initialized = True

        with patch.object(modern_webhook_logger, "log_system") as mock_log_system:
            with patch.object(modern_webhook_logger.sender, "close") as mock_close:
                await modern_webhook_logger.shutdown()

                assert modern_webhook_logger._closed is True
                mock_log_system.assert_called_with(
                    "Webhook Logger Shutdown", "Webhook logger is shutting down"
                )
                mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_logger_methods_coverage(self, modern_webhook_logger, mock_logger):
        """Test that all logging methods work correctly."""
        modern_webhook_logger.initialized = True

        with patch.object(modern_webhook_logger, "_send_message") as mock_send:
            mock_send.return_value = True

            # Test all logging methods
            await modern_webhook_logger.log_info("Info", "Info message")
            await modern_webhook_logger.log_warning("Warning", "Warning message")
            await modern_webhook_logger.log_success("Success", "Success message")
            await modern_webhook_logger.log_system("System", "System message")
            await modern_webhook_logger.log_user_activity("User", "User activity")

            # Should have called _send_message for each method
            assert mock_send.call_count == 5

            # Check that different log levels were used
            call_levels = [call[0][0].level for call in mock_send.call_args_list]
            assert LogLevel.INFO in call_levels
            assert LogLevel.WARNING in call_levels
            assert LogLevel.SUCCESS in call_levels
            assert LogLevel.SYSTEM in call_levels
            assert LogLevel.USER in call_levels

    @pytest.mark.asyncio
    async def test_user_interaction_with_avatar(
        self, modern_webhook_logger, mock_logger
    ):
        """Test user interaction logging with avatar."""
        modern_webhook_logger.initialized = True

        with patch.object(modern_webhook_logger, "_send_message") as mock_send:
            mock_send.return_value = True

            result = await modern_webhook_logger.log_user_interaction(
                interaction_type="command_use",
                user_name="TestUser",
                user_id=123456789,
                action_description="used the !quiz command",
                details={"command": "!quiz", "channel": "general"},
                user_avatar_url="https://cdn.discordapp.com/avatars/123/avatar.png",
            )

            assert result is True
            mock_send.assert_called_once()

            # Check the message content
            call_args = mock_send.call_args[0][0]
            assert call_args.title == "💬 User Interaction"
            assert "TestUser" in call_args.description
            assert call_args.author_name == "TestUser"
            assert (
                call_args.author_icon_url
                == "https://cdn.discordapp.com/avatars/123/avatar.png"
            )
            assert call_args.author_url == "https://discord.com/users/123456789"

    @pytest.mark.asyncio
    async def test_quiz_activity_with_avatar(self, modern_webhook_logger, mock_logger):
        """Test quiz activity logging with avatar."""
        modern_webhook_logger.initialized = True

        with patch.object(modern_webhook_logger, "_send_message") as mock_send:
            mock_send.return_value = True

            result = await modern_webhook_logger.log_quiz_activity(
                user_name="QuizMaster",
                user_id=987654321,
                question_text="What is the first surah?",
                user_answer="Al-Fatiha",
                correct_answer="Al-Fatiha",
                is_correct=True,
                user_avatar_url="https://cdn.discordapp.com/avatars/987/quiz_avatar.png",
                additional_context={"difficulty": "easy", "streak": 5},
            )

            assert result is True
            mock_send.assert_called_once()

            # Check the message content
            call_args = mock_send.call_args[0][0]
            assert "Quiz Answer - Correct!" in call_args.title
            assert "QuizMaster" in call_args.description
            assert call_args.author_name == "QuizMaster"
            assert (
                call_args.author_icon_url
                == "https://cdn.discordapp.com/avatars/987/quiz_avatar.png"
            )

            # Check that fields include quiz info
            field_names = [field.name for field in call_args.fields]
            assert "Result" in field_names
            assert "Question" in field_names
            assert "User Answer" in field_names
            assert "Correct Answer" in field_names
            assert "Difficulty" in field_names
            assert "Streak" in field_names


# =============================================================================
# Integration Tests
# =============================================================================


class TestWebhookLoggerIntegration:
    """Test webhook logger integration scenarios."""

    @pytest.mark.asyncio
    async def test_end_to_end_error_logging(self, webhook_config, mock_logger):
        """Test complete error logging flow."""
        # Create logger with real components (except HTTP)
        webhook_logger = ModernWebhookLogger(webhook_config, mock_logger)

        # Mock the HTTP session to avoid real network calls
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            # Mock successful response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_session.post.return_value.__aenter__.return_value = mock_response

            # Initialize and test
            await webhook_logger.initialize()

            # Mock the session after initialization
            webhook_logger.sender.session = mock_session

            # Test error logging
            exception = ValueError("Test error")
            result = await webhook_logger.log_error(
                "Integration Test Error",
                "This is an integration test",
                exception=exception,
                context={"test": "value"},
            )

            assert result is True

            # Verify HTTP call was made
            mock_session.post.assert_called()
            call_args = mock_session.post.call_args

            # Check the payload structure
            payload = call_args[1]["json"]  # keyword arguments, json parameter
            assert "embeds" in payload
            assert len(payload["embeds"]) == 1

            embed = payload["embeds"][0]
            assert "❌ Integration Test Error" in embed["title"]
            assert "This is an integration test" in embed["description"]
            assert "fields" in embed

            # Should have fields for exception type, message, and context
            field_names = [field["name"] for field in embed["fields"]]
            assert "Exception Type" in field_names
            assert "Exception Message" in field_names
            assert "Test" in field_names  # Context field

    @pytest.mark.asyncio
    async def test_multiple_rapid_logs_rate_limited(self, webhook_config, mock_logger):
        """Test that multiple rapid logs are properly rate limited."""
        # Use a very restrictive rate limit for testing
        webhook_config.max_logs_per_minute = 2
        webhook_logger = ModernWebhookLogger(webhook_config, mock_logger)

        with patch("aiohttp.ClientSession"):
            await webhook_logger.initialize()

            with patch.object(webhook_logger.sender, "send_webhook") as mock_send:
                mock_send.return_value = True

                # Send multiple messages rapidly
                results = []
                for i in range(5):
                    result = await webhook_logger.log_info(
                        f"Message {i}", "Description"
                    )
                    results.append(result)

                # First 2 should succeed, rest should be rate limited
                assert results[0] is True
                assert results[1] is True
                assert results[2] is False  # Rate limited
                assert results[3] is False  # Rate limited
                assert results[4] is False  # Rate limited

                # Only 2 HTTP calls should have been made
                assert mock_send.call_count == 2


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestWebhookLoggerErrorHandling:
    """Test error handling in various scenarios."""

    @pytest.mark.asyncio
    async def test_logger_not_initialized(self, modern_webhook_logger):
        """Test that methods handle uninitialized logger gracefully."""
        # Don't initialize the logger
        result = await modern_webhook_logger.log_error("Test", "Description")

        assert result is False

    @pytest.mark.asyncio
    async def test_logger_already_closed(self, modern_webhook_logger):
        """Test that methods handle closed logger gracefully."""
        modern_webhook_logger.initialized = True
        modern_webhook_logger._closed = True

        result = await modern_webhook_logger.log_error("Test", "Description")

        assert result is False

    @pytest.mark.asyncio
    async def test_send_message_exception_handling(
        self, modern_webhook_logger, mock_logger
    ):
        """Test that exceptions in _send_message are handled properly."""
        modern_webhook_logger.initialized = True

        with patch.object(
            modern_webhook_logger.formatter, "format_message"
        ) as mock_format:
            mock_format.side_effect = Exception("Formatting error")

            result = await modern_webhook_logger.log_error("Test", "Description")

            assert result is False
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_heartbeat_failure_during_init(
        self, modern_webhook_logger, mock_logger
    ):
        """Test that heartbeat failure doesn't prevent initialization."""
        with patch.object(modern_webhook_logger.sender, "initialize"):
            with patch.object(
                modern_webhook_logger, "_send_heartbeat"
            ) as mock_heartbeat:
                mock_heartbeat.side_effect = Exception("Heartbeat failed")

                result = await modern_webhook_logger.initialize()

                # Should still succeed even if heartbeat fails
                assert result is True
                assert modern_webhook_logger.initialized is True
                mock_logger.warning.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
