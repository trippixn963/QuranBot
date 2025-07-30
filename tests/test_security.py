#!/usr/bin/env python3
# =============================================================================
# QuranBot - Security Tests
# =============================================================================
# Comprehensive security tests to validate security measures and identify
# potential vulnerabilities in the QuranBot codebase.
# =============================================================================

import pytest
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.security.validators import SecureValidator, SecurityError
from src.security.error_handler import SecureErrorHandler, ErrorSeverity
import logging


class TestSecureValidator:
    """Test secure input validation."""
    
    def test_discord_token_validation(self):
        """Test Discord token validation."""
        # Valid tokens
        valid_token = "A" * 59  # Minimum length
        assert SecureValidator.validate_discord_token(valid_token) == valid_token
        
        # Valid token with Bot prefix
        bot_token = "Bot " + "A" * 59
        assert SecureValidator.validate_discord_token(bot_token) == bot_token
        
        # Invalid tokens
        with pytest.raises(SecurityError):
            SecureValidator.validate_discord_token("")  # Empty
        
        with pytest.raises(SecurityError):
            SecureValidator.validate_discord_token("short")  # Too short
        
        with pytest.raises(SecurityError):
            SecureValidator.validate_discord_token("A" * 58 + "<script>")  # Dangerous chars
    
    def test_user_id_validation(self):
        """Test Discord user ID validation."""
        # Valid user IDs
        valid_id = "123456789012345678"  # 18 digits
        assert SecureValidator.validate_user_id(valid_id) == int(valid_id)
        assert SecureValidator.validate_user_id(int(valid_id)) == int(valid_id)
        
        # Invalid user IDs
        with pytest.raises(SecurityError):
            SecureValidator.validate_user_id("123")  # Too short
        
        with pytest.raises(SecurityError):
            SecureValidator.validate_user_id("12345678901234567890")  # Too long
        
        with pytest.raises(SecurityError):
            SecureValidator.validate_user_id("abc123456789012345")  # Non-numeric
        
        with pytest.raises(SecurityError):
            SecureValidator.validate_user_id("0")  # Below minimum snowflake
    
    def test_webhook_url_validation(self):
        """Test webhook URL validation."""
        # Valid webhook URL
        valid_url = "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890_-"
        assert SecureValidator.validate_webhook_url(valid_url) == valid_url
        
        # Invalid webhook URLs
        with pytest.raises(SecurityError):
            SecureValidator.validate_webhook_url("http://discord.com/api/webhooks/123/abc")  # HTTP
        
        with pytest.raises(SecurityError):
            SecureValidator.validate_webhook_url("https://example.com/webhook")  # Wrong domain
        
        with pytest.raises(SecurityError):
            SecureValidator.validate_webhook_url("https://discord.com/api/webhooks/")  # Incomplete
    
    def test_surah_number_validation(self):
        """Test Quran surah number validation."""
        # Valid surah numbers
        assert SecureValidator.validate_surah_number(1) == 1
        assert SecureValidator.validate_surah_number("114") == 114
        assert SecureValidator.validate_surah_number(36) == 36
        
        # Invalid surah numbers
        with pytest.raises(SecurityError):
            SecureValidator.validate_surah_number(0)  # Too low
        
        with pytest.raises(SecurityError):
            SecureValidator.validate_surah_number(115)  # Too high
        
        with pytest.raises(SecurityError):
            SecureValidator.validate_surah_number("abc")  # Non-numeric
    
    def test_text_input_validation(self):
        """Test text input validation and sanitization."""
        # Valid text
        valid_text = "This is a normal text input"
        assert SecureValidator.validate_text_input(valid_text) == valid_text.strip()
        
        # Text with dangerous characters
        with pytest.raises(SecurityError):
            SecureValidator.validate_text_input("Hello <script>alert('xss')</script>")
        
        with pytest.raises(SecurityError):
            SecureValidator.validate_text_input("'; DROP TABLE users; --")  # SQL injection
        
        # Text too long
        with pytest.raises(SecurityError):
            SecureValidator.validate_text_input("A" * 1001, max_length=1000)
    
    def test_file_path_validation(self):
        """Test file path validation."""
        # Valid paths
        assert SecureValidator.validate_file_path("audio/file.mp3") == "audio/file.mp3"
        assert SecureValidator.validate_file_path("data/backup.json") == "data/backup.json"
        
        # Invalid paths (path traversal)
        with pytest.raises(SecurityError):
            SecureValidator.validate_file_path("../../../etc/passwd")
        
        with pytest.raises(SecurityError):
            SecureValidator.validate_file_path("/absolute/path")
        
        with pytest.raises(SecurityError):
            SecureValidator.validate_file_path("file\x00.txt")  # Null byte
        
        # Extension validation
        with pytest.raises(SecurityError):
            SecureValidator.validate_file_path("file.exe", allowed_extensions=[".mp3", ".json"])
    
    def test_admin_user_ids_validation(self):
        """Test admin user IDs validation."""
        # Valid admin user IDs
        valid_ids = "123456789012345678,987654321098765432"
        result = SecureValidator.validate_admin_user_ids(valid_ids)
        assert len(result) == 2
        assert 123456789012345678 in result
        assert 987654321098765432 in result
        
        # Empty string
        assert SecureValidator.validate_admin_user_ids("") == []
        
        # Invalid format
        with pytest.raises(SecurityError):
            SecureValidator.validate_admin_user_ids("123,abc,456")
        
        # Duplicates
        with pytest.raises(SecurityError):
            SecureValidator.validate_admin_user_ids("123456789012345678,123456789012345678")
        
        # Too many admins
        many_ids = ",".join(["123456789012345678"] * 51)
        with pytest.raises(SecurityError):
            SecureValidator.validate_admin_user_ids(many_ids)
    
    def test_log_data_sanitization(self):
        """Test log data sanitization."""
        sensitive_data = {
            "discord_token": "secret_token_123",
            "password": "my_password",
            "user_id": "123456789012345678",
            "normal_field": "normal_value",
            "long_text": "A" * 300,
            "nested": {
                "api_key": "secret_key",
                "safe_data": "safe_value"
            }
        }
        
        sanitized = SecureValidator.sanitize_log_data(sensitive_data)
        
        # Sensitive fields should be redacted
        assert sanitized["discord_token"] == "[REDACTED]"
        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["nested"]["api_key"] == "[REDACTED]"
        
        # Safe fields should remain
        assert sanitized["user_id"] == "123456789012345678"
        assert sanitized["normal_field"] == "normal_value"
        assert sanitized["nested"]["safe_data"] == "safe_value"
        
        # Long text should be truncated
        assert sanitized["long_text"].endswith("...[TRUNCATED]")


class TestSecureErrorHandler:
    """Test secure error handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.logger = logging.getLogger("test_logger")
        self.error_handler = SecureErrorHandler(self.logger, debug_mode=False)
    
    def test_error_id_generation(self):
        """Test error ID generation."""
        error_id1 = self.error_handler.generate_error_id()
        error_id2 = self.error_handler.generate_error_id()
        
        # Error IDs should be unique
        assert error_id1 != error_id2
        
        # Should follow expected format
        assert error_id1.startswith("ERR_")
        assert len(error_id1) > 15  # Should have timestamp and random suffix
    
    def test_error_code_mapping(self):
        """Test error code mapping."""
        # Test specific exception types
        assert self.error_handler._get_error_code(ValueError("test")) == "INVALID_INPUT"
        assert self.error_handler._get_error_code(PermissionError("test")) == "AUTH_INSUFFICIENT_PERMISSIONS"
        assert self.error_handler._get_error_code(FileNotFoundError("test")) == "AUDIO_FILE_NOT_FOUND"
        
        # Test message-based mapping
        assert self.error_handler._get_error_code(Exception("token invalid")) == "AUTH_INVALID_TOKEN"
        assert self.error_handler._get_error_code(Exception("surah not found")) == "INVALID_SURAH_NUMBER"
        assert self.error_handler._get_error_code(Exception("audio playback failed")) == "AUDIO_PLAYBACK_FAILED"
    
    def test_error_severity_classification(self):
        """Test error severity classification."""
        # Critical errors
        security_error = Exception("security violation detected")
        assert self.error_handler._get_error_severity(security_error) == ErrorSeverity.CRITICAL
        
        # High severity errors
        perm_error = PermissionError("access denied")
        assert self.error_handler._get_error_severity(perm_error) == ErrorSeverity.HIGH
        
        # Medium severity errors
        value_error = ValueError("invalid input")
        assert self.error_handler._get_error_severity(value_error) == ErrorSeverity.MEDIUM
        
        # Low severity errors
        generic_error = Exception("generic error")
        assert self.error_handler._get_error_severity(generic_error) == ErrorSeverity.LOW
    
    @pytest.mark.asyncio
    async def test_user_facing_error_response(self):
        """Test user-facing error response format."""
        error = ValueError("Invalid surah number")
        response = await self.error_handler.handle_error(error, user_facing=True)
        
        # Should have proper structure
        assert "error" in response
        assert "code" in response["error"]
        assert "message" in response["error"]
        assert "error_id" in response["error"]
        assert "timestamp" in response["error"]
        
        # Should not contain sensitive information
        assert "traceback" not in response
        assert "stack_trace" not in response
        
        # Should have user-friendly message
        assert response["error"]["code"] == "INVALID_INPUT"
        assert len(response["error"]["message"]) > 0
    
    @pytest.mark.asyncio
    async def test_internal_error_response(self):
        """Test internal error response format."""
        error = ValueError("Invalid surah number")
        context = {"user_id": 123456789012345678, "surah": 150}
        
        response = await self.error_handler.handle_error(
            error, context=context, user_facing=False
        )
        
        # Should have detailed information for internal use
        assert "error_id" in response
        assert "error_type" in response
        assert "error_message" in response
        assert "context" in response
        assert "severity" in response
        
        # Context should be included
        assert response["context"]["user_id"] == 123456789012345678
        assert response["context"]["surah"] == 150
    
    @pytest.mark.asyncio
    async def test_context_sanitization(self):
        """Test context sanitization for logging."""
        sensitive_context = {
            "discord_token": "secret_token",
            "user_id": 123456789012345678,
            "error_details": "Some error occurred"
        }
        
        sanitized = self.error_handler._sanitize_context(sensitive_context)
        
        # Sensitive data should be redacted
        assert sanitized["discord_token"] == "[REDACTED]"
        
        # Non-sensitive data should remain
        assert sanitized["user_id"] == 123456789012345678
        assert sanitized["error_details"] == "Some error occurred"
    
    @pytest.mark.asyncio
    async def test_validation_error_handling(self):
        """Test specific validation error handling."""
        response = await self.error_handler.handle_validation_error(
            field="surah_number",
            value=150,
            constraint="Must be between 1 and 114"
        )
        
        assert response["error"]["code"] == "INVALID_INPUT"
        assert response["error"]["details"]["field"] == "surah_number"
        assert response["error"]["details"]["constraint"] == "Must be between 1 and 114"
    
    @pytest.mark.asyncio
    async def test_rate_limit_error_handling(self):
        """Test rate limit error handling."""
        response = await self.error_handler.handle_rate_limit_error(
            limit=10,
            window=60,
            retry_after=45
        )
        
        assert response["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert response["error"]["details"]["limit"] == 10
        assert response["error"]["details"]["window"] == "60 seconds"
        assert response["error"]["details"]["retry_after"] == 45


class TestSecurityIntegration:
    """Test security integration across components."""
    
    def test_configuration_security(self):
        """Test configuration security measures."""
        try:
            from src.config.secure_config import SecureQuranBotConfig
            
            # Test that invalid tokens are rejected
            with pytest.raises(ValueError):
                SecureQuranBotConfig(
                    discord_token="invalid_token",
                    guild_id=123456789012345678,
                    target_channel_id=123456789012345678
                )
            
            # Test that invalid IDs are rejected
            with pytest.raises(ValueError):
                SecureQuranBotConfig(
                    discord_token="A" * 59,
                    guild_id=123,  # Too small
                    target_channel_id=123456789012345678
                )
        
        except ImportError:
            pytest.skip("Secure config not available")
    
    def test_input_validation_integration(self):
        """Test input validation across different components."""
        # Test that all validators work together
        validator = SecureValidator()
        
        # Valid inputs should pass all validations
        token = "A" * 59
        user_id = "123456789012345678"
        webhook_url = "https://discord.com/api/webhooks/123456789012345678/" + "A" * 68
        
        assert validator.validate_discord_token(token) == token
        assert validator.validate_user_id(user_id) == int(user_id)
        assert validator.validate_webhook_url(webhook_url) == webhook_url
    
    def test_error_handling_integration(self):
        """Test error handling integration."""
        logger = logging.getLogger("integration_test")
        handler = SecureErrorHandler(logger)
        
        # Test that different error types are handled consistently
        errors = [
            ValueError("Invalid input"),
            PermissionError("Access denied"),
            FileNotFoundError("File not found"),
            Exception("Generic error")
        ]
        
        for error in errors:
            error_code = handler._get_error_code(error)
            severity = handler._get_error_severity(error)
            
            # All errors should have valid codes and severities
            assert error_code in handler.error_codes
            assert isinstance(severity, ErrorSeverity)


def run_security_tests():
    """Run all security tests."""
    print("Running QuranBot Security Tests...")
    
    # Run pytest with verbose output
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x"  # Stop on first failure
    ])
    
    if exit_code == 0:
        print("✅ All security tests passed!")
    else:
        print("❌ Some security tests failed!")
    
    return exit_code == 0


if __name__ == "__main__":
    success = run_security_tests()
    sys.exit(0 if success else 1)