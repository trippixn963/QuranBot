# =============================================================================
# QuranBot - Security Tests
# =============================================================================
# Comprehensive tests for security features including rate limiting,
# input validation, permission checking, and security service functionality.
# =============================================================================

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import discord
import pytest

from src.core.exceptions import RateLimitError, SecurityError, ValidationError
from src.core.security import (
    InputValidator,
    RateLimiter,
    SecurityService,
    rate_limit,
    require_admin,
    validate_input,
)
from src.core.structured_logger import StructuredLogger

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
async def mock_logger():
    """Create a mock structured logger"""
    logger = Mock(spec=StructuredLogger)
    logger.info = AsyncMock()
    logger.warning = AsyncMock()
    logger.error = AsyncMock()
    logger.debug = AsyncMock()
    return logger


@pytest.fixture
async def rate_limiter(mock_logger):
    """Create a RateLimiter instance for testing"""
    limiter = RateLimiter(logger=mock_logger)
    yield limiter
    # Cleanup
    if limiter._cleanup_task and not limiter._cleanup_task.done():
        limiter._cleanup_task.cancel()
        try:
            await limiter._cleanup_task
        except asyncio.CancelledError:
            pass


@pytest.fixture
def security_service(rate_limiter, mock_logger):
    """Create a SecurityService instance for testing"""
    return SecurityService(rate_limiter=rate_limiter, logger=mock_logger)


@pytest.fixture
def mock_interaction():
    """Create a mock Discord interaction"""
    interaction = Mock(spec=discord.Interaction)
    interaction.user = Mock()
    interaction.user.id = 12345
    interaction.guild = Mock()
    interaction.guild.id = 67890
    interaction.response = Mock()
    interaction.response.is_done.return_value = False
    interaction.response.send_message = AsyncMock()
    interaction.followup = Mock()
    interaction.followup.send = AsyncMock()
    return interaction


# =============================================================================
# Rate Limiter Tests
# =============================================================================


class TestRateLimiter:
    """Test rate limiting functionality"""

    @pytest.mark.asyncio
    async def test_user_rate_limit_within_bounds(self, rate_limiter):
        """Test that requests within user rate limit are allowed"""
        user_id = 12345
        guild_id = 67890
        command = "test_command"

        # Should allow up to the limit
        for i in range(5):  # Default user_limit is 5
            result = await rate_limiter.check_rate_limit(
                user_id=user_id, guild_id=guild_id, command_name=command
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_user_rate_limit_exceeded(self, rate_limiter):
        """Test that user rate limit is enforced"""
        user_id = 12345
        guild_id = 67890
        command = "test_command"

        # Fill up the rate limit
        for i in range(5):
            await rate_limiter.check_rate_limit(
                user_id=user_id, guild_id=guild_id, command_name=command
            )

        # Next request should be rate limited
        with pytest.raises(RateLimitError) as exc_info:
            await rate_limiter.check_rate_limit(
                user_id=user_id, guild_id=guild_id, command_name=command
            )

        assert exc_info.value.limit_type == "user"
        assert exc_info.value.limit == 5
        assert exc_info.value.current_count == 5

    @pytest.mark.asyncio
    async def test_guild_rate_limit_exceeded(self, rate_limiter):
        """Test that guild rate limit is enforced"""
        guild_id = 67890
        command = "test_command"

        # Fill up the guild rate limit with different users
        for user_id in range(1, 22):  # Default guild_limit is 20
            if user_id <= 20:
                result = await rate_limiter.check_rate_limit(
                    user_id=user_id, guild_id=guild_id, command_name=command
                )
                assert result is True
            else:
                # 21st user should be rate limited
                with pytest.raises(RateLimitError) as exc_info:
                    await rate_limiter.check_rate_limit(
                        user_id=user_id, guild_id=guild_id, command_name=command
                    )
                assert exc_info.value.limit_type == "guild"

    @pytest.mark.asyncio
    async def test_rate_limit_window_expiry(self, rate_limiter):
        """Test that rate limits reset after window expires"""
        user_id = 12345
        guild_id = 67890
        command = "test_command"

        # Fill up the rate limit
        for i in range(5):
            await rate_limiter.check_rate_limit(
                user_id=user_id,
                guild_id=guild_id,
                command_name=command,
                user_window=1,  # 1 second window for testing
            )

        # Should be rate limited immediately
        with pytest.raises(RateLimitError):
            await rate_limiter.check_rate_limit(
                user_id=user_id, guild_id=guild_id, command_name=command, user_window=1
            )

        # Wait for window to expire
        await asyncio.sleep(1.1)

        # Should be allowed again
        result = await rate_limiter.check_rate_limit(
            user_id=user_id, guild_id=guild_id, command_name=command, user_window=1
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_token_bucket_rate_limit(self, rate_limiter):
        """Test token bucket rate limiting"""
        user_id = 12345
        command = "test_command"

        # Should allow initial requests up to bucket size
        for i in range(10):  # Default bucket_size is 10
            result = await rate_limiter.check_token_bucket(
                user_id=user_id, command_name=command
            )
            if i < 10:
                assert result is True
            else:
                assert result is False

    @pytest.mark.asyncio
    async def test_rate_limit_status(self, rate_limiter):
        """Test getting rate limit status"""
        user_id = 12345
        command = "test_command"

        # Make some requests
        for i in range(3):
            await rate_limiter.check_rate_limit(
                user_id=user_id, guild_id=None, command_name=command
            )

        status = await rate_limiter.get_rate_limit_status(user_id, command)
        assert status["user_requests_last_minute"] == 3
        assert isinstance(status["available_tokens"], (int, float))


# =============================================================================
# Input Validator Tests
# =============================================================================


class TestInputValidator:
    """Test input validation and sanitization"""

    def test_sanitize_string_valid(self):
        """Test sanitizing valid strings"""
        text = "This is a valid string"
        result = InputValidator.sanitize_string(text)
        assert result == text

    def test_sanitize_string_too_long(self):
        """Test string length validation"""
        text = "a" * 2001  # Too long
        with pytest.raises(ValidationError) as exc_info:
            InputValidator.sanitize_string(text, max_length=2000)
        assert "too long" in str(exc_info.value)

    def test_sanitize_string_dangerous_content(self):
        """Test detection of dangerous content"""
        dangerous_texts = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "@everyone ping",
            "discord.gg/malicious",
        ]

        for text in dangerous_texts:
            with pytest.raises(ValidationError):
                InputValidator.sanitize_string(text)

    def test_sanitize_string_remove_mentions(self):
        """Test mention removal"""
        text = "Hello <@123456> and <@!789012>"
        result = InputValidator.sanitize_string(text, allow_mentions=False)
        assert "<@" not in result
        assert "[mention removed]" in result

    def test_sanitize_string_remove_links(self):
        """Test link removal"""
        text = "Check out https://example.com and http://test.org"
        result = InputValidator.sanitize_string(text, allow_links=False)
        assert "https://" not in result
        assert "[link removed]" in result

    def test_validate_surah_number_valid(self):
        """Test valid surah number validation"""
        for surah in [1, 50, 114, "1", "114"]:
            result = InputValidator.validate_surah_number(surah)
            assert isinstance(result, int)
            assert 1 <= result <= 114

    def test_validate_surah_number_invalid(self):
        """Test invalid surah number validation"""
        invalid_surahs = [0, 115, -1, "abc", None, 999]

        for surah in invalid_surahs:
            with pytest.raises(ValidationError):
                InputValidator.validate_surah_number(surah)

    def test_validate_ayah_number_valid(self):
        """Test valid ayah number validation"""
        result = InputValidator.validate_ayah_number(5, 1)
        assert result == 5

        result = InputValidator.validate_ayah_number("10", 2)
        assert result == 10

    def test_validate_ayah_number_invalid(self):
        """Test invalid ayah number validation"""
        invalid_ayahs = [0, -1, "abc", None]

        for ayah in invalid_ayahs:
            with pytest.raises(ValidationError):
                InputValidator.validate_ayah_number(ayah, 1)

    def test_validate_time_interval_valid(self):
        """Test valid time interval validation"""
        test_cases = [
            ("30m", 0.5),
            ("2h", 2.0),
            ("1h30m", 1.5),
            ("90m", 1.5),
            ("2.5h", 2.5),
            ("120", 2.0),  # Interpreted as minutes
        ]

        for interval_str, expected_hours in test_cases:
            result = InputValidator.validate_time_interval(interval_str)
            assert abs(result - expected_hours) < 0.01

    def test_validate_time_interval_invalid(self):
        """Test invalid time interval validation"""
        invalid_intervals = [
            "abc",
            "30s",  # Seconds not supported
            "25h",  # Too long
            "0m",  # Too short
            "",
            None,
        ]

        for interval in invalid_intervals:
            with pytest.raises(ValidationError):
                InputValidator.validate_time_interval(interval)

    def test_validate_user_id_valid(self):
        """Test valid Discord user ID validation"""
        valid_ids = [123456789012345678, "123456789012345678", 987654321098765432]

        for user_id in valid_ids:
            result = InputValidator.validate_user_id(user_id)
            assert isinstance(result, int)

    def test_validate_user_id_invalid(self):
        """Test invalid Discord user ID validation"""
        invalid_ids = [
            "abc",
            123,  # Too short
            12345678901234567890123,  # Too long
            None,
            "",
        ]

        for user_id in invalid_ids:
            with pytest.raises(ValidationError):
                InputValidator.validate_user_id(user_id)


# =============================================================================
# Security Service Tests
# =============================================================================


class TestSecurityService:
    """Test security service functionality"""

    @pytest.mark.asyncio
    async def test_admin_check(self, security_service):
        """Test admin user checking"""
        # Add a test admin
        security_service.admin_users.add(12345)

        assert await security_service.is_admin(12345) is True
        assert await security_service.is_admin(67890) is False

    @pytest.mark.asyncio
    async def test_blocked_user_check(self, security_service):
        """Test blocked user checking"""
        # Add a blocked user
        security_service.blocked_users.add(12345)

        assert await security_service.is_blocked(12345) is True
        assert await security_service.is_blocked(67890) is False

    @pytest.mark.asyncio
    async def test_trusted_guild_check(self, security_service):
        """Test trusted guild checking"""
        # Add a trusted guild
        security_service.trusted_guilds.add(12345)

        assert await security_service.is_trusted_guild(12345) is True
        assert await security_service.is_trusted_guild(67890) is False

    @pytest.mark.asyncio
    async def test_command_permission_blocked_user(self, security_service):
        """Test command permission check for blocked user"""
        # Block a user
        security_service.blocked_users.add(12345)

        with pytest.raises(SecurityError) as exc_info:
            await security_service.check_command_permission(
                user_id=12345, guild_id=None, command_name="test_command"
            )

        assert exc_info.value.reason == "blocked"
        assert exc_info.value.user_id == 12345

    @pytest.mark.asyncio
    async def test_command_permission_admin_required(self, security_service):
        """Test command permission check for admin-only commands"""
        # Non-admin user
        result = await security_service.check_command_permission(
            user_id=12345,
            guild_id=None,
            command_name="admin_command",
            require_admin=True,
        )
        assert result is False

        # Admin user
        security_service.admin_users.add(12345)
        result = await security_service.check_command_permission(
            user_id=12345,
            guild_id=None,
            command_name="admin_command",
            require_admin=True,
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_discord_token(self, security_service):
        """Test Discord token validation"""
        valid_tokens = [
            "FAKE_TOKEN_FOR_TESTING.12345.67890-abcdefghijklmnopqr",
            "Bot FAKE_TOKEN_FOR_TESTING.12345.67890-abcdefghijklmnopqr",
        ]

        invalid_tokens = ["short", "", None, "invalid!@#$%", 123]

        for token in valid_tokens:
            result = await security_service.validate_discord_token(token)
            assert result is True

        for token in invalid_tokens:
            result = await security_service.validate_discord_token(token)
            assert result is False

    @pytest.mark.asyncio
    async def test_sanitize_for_logging(self, security_service):
        """Test data sanitization for logging"""
        sensitive_data = {
            "user_id": 12345,
            "discord_token": "secret_token_here",
            "api_key": "secret_key",
            "password": "secret_password",
            "normal_field": "normal_value",
            "nested": {"secret": "another_secret", "public": "public_value"},
        }

        sanitized = await security_service.sanitize_for_logging(sensitive_data)

        assert sanitized["user_id"] == 12345
        assert sanitized["discord_token"] == "[REDACTED]"
        assert sanitized["api_key"] == "[REDACTED]"
        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["normal_field"] == "normal_value"
        assert sanitized["nested"]["secret"] == "[REDACTED]"
        assert sanitized["nested"]["public"] == "public_value"


# =============================================================================
# Decorator Tests
# =============================================================================


class TestSecurityDecorators:
    """Test security decorators"""

    @pytest.mark.asyncio
    async def test_rate_limit_decorator(self, mock_interaction):
        """Test rate limit decorator functionality"""
        # Mock the DI container to return a rate limiter
        with patch("src.core.security.DIContainer") as mock_container_class:
            mock_container = Mock()
            mock_rate_limiter = Mock()
            mock_rate_limiter.check_rate_limit = AsyncMock(return_value=True)

            mock_container.get.return_value = mock_rate_limiter
            mock_container_class.get_instance.return_value = mock_container

            @rate_limit(user_limit=5, user_window=60)
            async def test_command(interaction):
                return "success"

            result = await test_command(mock_interaction)
            assert result == "success"

            # Verify rate limiter was called
            mock_rate_limiter.check_rate_limit.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limit_decorator_exceeded(self, mock_interaction):
        """Test rate limit decorator when limit is exceeded"""
        with patch("src.core.security.DIContainer") as mock_container_class:
            mock_container = Mock()
            mock_rate_limiter = Mock()
            mock_rate_limiter.check_rate_limit = AsyncMock(
                side_effect=RateLimitError(
                    "Rate limit exceeded", limit_type="user", window=60
                )
            )

            mock_container.get.return_value = mock_rate_limiter
            mock_container_class.get_instance.return_value = mock_container

            @rate_limit(user_limit=1, user_window=60)
            async def test_command(interaction):
                return "success"

            result = await test_command(mock_interaction)
            assert result is None  # Should return None when rate limited

            # Verify error message was sent
            mock_interaction.response.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_require_admin_decorator_success(self, mock_interaction):
        """Test require_admin decorator for admin user"""
        with patch("src.core.security.DIContainer") as mock_container_class:
            mock_container = Mock()
            mock_security_service = Mock()
            mock_security_service.check_command_permission = AsyncMock(
                return_value=True
            )

            mock_container.get.return_value = mock_security_service
            mock_container_class.get_instance.return_value = mock_container

            @require_admin
            async def admin_command(interaction):
                return "admin_success"

            result = await admin_command(mock_interaction)
            assert result == "admin_success"

    @pytest.mark.asyncio
    async def test_require_admin_decorator_denied(self, mock_interaction):
        """Test require_admin decorator for non-admin user"""
        with patch("src.core.security.DIContainer") as mock_container_class:
            mock_container = Mock()
            mock_security_service = Mock()
            mock_security_service.check_command_permission = AsyncMock(
                return_value=False
            )

            mock_container.get.return_value = mock_security_service
            mock_container_class.get_instance.return_value = mock_container

            @require_admin
            async def admin_command(interaction):
                return "admin_success"

            result = await admin_command(mock_interaction)
            assert result is None

            # Verify access denied message was sent
            mock_interaction.response.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_input_decorator(self, mock_interaction):
        """Test validate_input decorator"""

        @validate_input(surah={"type": "surah"})
        async def test_command(interaction, surah=None):
            return f"surah_{surah}"

        # Test with valid input
        result = await test_command(mock_interaction, surah=1)
        assert result == "surah_1"

        # Test with invalid input (should handle validation error)
        result = await test_command(mock_interaction, surah=999)
        assert result is None

        # Verify validation error message was sent
        mock_interaction.response.send_message.assert_called_once()


# =============================================================================
# Integration Tests
# =============================================================================


class TestSecurityIntegration:
    """Test security system integration"""

    @pytest.mark.asyncio
    async def test_complete_security_flow(self, security_service, mock_interaction):
        """Test complete security validation flow"""
        # Setup admin user
        security_service.admin_users.add(mock_interaction.user.id)

        # Test admin command permission
        result = await security_service.check_command_permission(
            user_id=mock_interaction.user.id,
            guild_id=mock_interaction.guild.id,
            command_name="admin_command",
            require_admin=True,
        )
        assert result is True

        # Test rate limiting
        for i in range(5):  # Default user limit
            result = await security_service.rate_limiter.check_rate_limit(
                user_id=mock_interaction.user.id,
                guild_id=mock_interaction.guild.id,
                command_name="admin_command",
            )
            assert result is True

        # Next request should be rate limited
        with pytest.raises(RateLimitError):
            await security_service.rate_limiter.check_rate_limit(
                user_id=mock_interaction.user.id,
                guild_id=mock_interaction.guild.id,
                command_name="admin_command",
            )

    @pytest.mark.asyncio
    async def test_security_logging(self, security_service, mock_interaction):
        """Test security event logging"""
        await security_service.log_security_event(
            event_type="command_executed",
            user_id=mock_interaction.user.id,
            guild_id=mock_interaction.guild.id,
            details={"command": "test_command", "success": True},
        )

        # Verify logging was called
        security_service.logger.info.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
