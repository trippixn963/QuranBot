# =============================================================================
# QuranBot - Core Error Handling Tests
# =============================================================================
# Comprehensive test suite for the error handling system including:
# - Error enums and context creation
# - Bot error types and validation
# - Error handler functionality
# - Error recovery and retry logic
# - Edge cases and integration scenarios
# =============================================================================

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import asyncio

from app.core.errors import (
    ErrorSeverity, ErrorCategory, ErrorContext, BotError, ServiceError,
    DatabaseError, AudioError, StateError, ConfigurationError, NetworkError,
    DiscordAPIError, ValidationError, PermissionError, ResourceError, ErrorHandler
)
from app.config.timezone import APP_TIMEZONE


class TestErrorEnums:
    """Test error enums and basic functionality."""
    
    def test_error_severity_values(self):
        """Test error severity enum values."""
        assert ErrorSeverity.DEBUG.value == "debug"
        assert ErrorSeverity.INFO.value == "info"
        assert ErrorSeverity.WARNING.value == "warning"
        assert ErrorSeverity.ERROR.value == "error"
        assert ErrorSeverity.CRITICAL.value == "critical"
        assert ErrorSeverity.FATAL.value == "fatal"
    
    def test_error_category_values(self):
        """Test error category enum values."""
        assert ErrorCategory.SYSTEM.value == "system"
        assert ErrorCategory.SERVICE.value == "service"
        assert ErrorCategory.DATABASE.value == "database"
        assert ErrorCategory.AUDIO.value == "audio"
        assert ErrorCategory.NETWORK.value == "network"
        assert ErrorCategory.DISCORD_API.value == "discord_api"
        assert ErrorCategory.UNKNOWN.value == "unknown"


class TestErrorContext:
    """Test error context creation and functionality."""
    
    def test_error_context_creation(self):
        """Test basic error context creation."""
        context = ErrorContext(
            operation="test_operation",
            service="test_service",
            user_id=123,
            guild_id=456
        )
        
        assert context.operation == "test_operation"
        assert context.service == "test_service"
        assert context.user_id == 123
        assert context.guild_id == 456
        assert context.severity == ErrorSeverity.ERROR
        assert context.category == ErrorCategory.UNKNOWN
        assert context.retry_count == 0
        assert context.max_retries == 3
        assert context.is_recoverable is True
    
    def test_error_context_to_dict(self):
        """Test error context to dictionary conversion."""
        context = ErrorContext(
            operation="test_operation",
            service="test_service",
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.DATABASE
        )
        
        context_dict = context.to_dict()
        
        assert context_dict["operation"] == "test_operation"
        assert context_dict["service"] == "test_service"
        assert context_dict["severity"] == "critical"
        assert context_dict["category"] == "database"
        assert context_dict["retry_count"] == 0
        assert context_dict["max_retries"] == 3
        assert context_dict["is_recoverable"] is True
        assert "timestamp" in context_dict
        assert "correlation_id" in context_dict


class TestBotError:
    """Test base bot error functionality."""
    
    def test_bot_error_creation(self):
        """Test basic bot error creation."""
        error = BotError("Test error message")
        
        assert str(error) == "Test error message"
        assert error.context is not None
        assert error.context.operation == "unknown"
        assert error.context.severity == ErrorSeverity.ERROR
        assert error.context.category == ErrorCategory.UNKNOWN
    
    def test_bot_error_with_context(self):
        """Test bot error with custom context."""
        context = ErrorContext(
            operation="test_operation",
            service="test_service",
            severity=ErrorSeverity.CRITICAL
        )
        
        error = BotError("Test error", context=context)
        
        assert error.context == context
        assert error.context.operation == "test_operation"
        assert error.context.severity == ErrorSeverity.CRITICAL
    
    def test_bot_error_user_message(self):
        """Test bot error user-friendly message generation."""
        # Test Discord API error
        error = BotError("Discord error", category=ErrorCategory.DISCORD_API)
        assert "Discord connection issue" in error.get_user_message()
        
        # Test voice connection error
        error = BotError("Voice error", category=ErrorCategory.VOICE_CONNECTION)
        assert "Voice channel connection" in error.get_user_message()
        
        # Test database error
        error = BotError("Database error", category=ErrorCategory.DATABASE)
        assert "Database operation failed" in error.get_user_message()
    
    def test_bot_error_critical_check(self):
        """Test bot error critical status check."""
        # Non-critical error
        error = BotError("Test error")
        assert not error.is_critical()
        
        # Critical error
        error = BotError("Critical error", severity=ErrorSeverity.CRITICAL)
        assert error.is_critical()
        
        # Fatal error
        error = BotError("Fatal error", severity=ErrorSeverity.FATAL)
        assert error.is_critical()
    
    def test_bot_error_recoverable_check(self):
        """Test bot error recoverable status check."""
        # Recoverable error
        error = BotError("Test error")
        assert error.is_recoverable()
        
        # Non-recoverable error
        error = BotError("Test error", is_recoverable=False)
        assert not error.is_recoverable()
        
        # Error with max retries exceeded
        error = BotError("Test error")
        error.context.retry_count = 5
        error.context.max_retries = 3
        assert not error.is_recoverable()
    
    def test_bot_error_should_retry(self):
        """Test bot error retry logic."""
        # Should retry
        error = BotError("Test error")
        assert error.should_retry()
        
        # Should not retry (max retries exceeded)
        error = BotError("Test error")
        error.context.retry_count = 3
        error.context.max_retries = 3
        assert not error.should_retry()


class TestServiceErrors:
    """Test service-specific error types."""
    
    def test_service_error(self):
        """Test service error creation."""
        error = ServiceError("Service error", "TestService")
        
        assert error.context.service == "TestService"
        assert error.context.category == ErrorCategory.SERVICE
        assert error.context.severity == ErrorSeverity.ERROR
    
    def test_database_error(self):
        """Test database error creation."""
        error = DatabaseError("Database error")
        
        assert error.context.service == "DatabaseService"
        assert error.context.category == ErrorCategory.DATABASE
        assert error.context.severity == ErrorSeverity.ERROR
    
    def test_audio_error(self):
        """Test audio error creation."""
        error = AudioError("Audio error")
        
        assert error.context.service == "AudioService"
        assert error.context.category == ErrorCategory.AUDIO
        assert error.context.severity == ErrorSeverity.ERROR
    
    def test_state_error(self):
        """Test state error creation."""
        error = StateError("State error")
        
        assert error.context.service == "StateService"
        assert error.context.category == ErrorCategory.STATE
        assert error.context.severity == ErrorSeverity.ERROR
    
    def test_configuration_error(self):
        """Test configuration error creation."""
        error = ConfigurationError("Config error")
        
        assert error.context.service == "ConfigurationService"
        assert error.context.category == ErrorCategory.CONFIGURATION
        assert error.context.severity == ErrorSeverity.CRITICAL
        assert not error.context.is_recoverable
    
    def test_network_error(self):
        """Test network error creation."""
        error = NetworkError("Network error")
        
        assert error.context.category == ErrorCategory.NETWORK
        assert error.context.severity == ErrorSeverity.WARNING
    
    def test_discord_api_error(self):
        """Test Discord API error creation."""
        error = DiscordAPIError("Discord error")
        
        assert error.context.category == ErrorCategory.DISCORD_API
        assert error.context.severity == ErrorSeverity.WARNING
    
    def test_validation_error(self):
        """Test validation error creation."""
        error = ValidationError("Validation error")
        
        assert error.context.category == ErrorCategory.VALIDATION
        assert error.context.severity == ErrorSeverity.INFO
    
    def test_permission_error(self):
        """Test permission error creation."""
        error = PermissionError("Permission error")
        
        assert error.context.category == ErrorCategory.PERMISSION
        assert error.context.severity == ErrorSeverity.WARNING
        assert not error.context.is_recoverable
    
    def test_resource_error(self):
        """Test resource error creation."""
        error = ResourceError("Resource error")
        
        assert error.context.category == ErrorCategory.RESOURCE
        assert error.context.severity == ErrorSeverity.ERROR


class TestErrorHandler:
    """Test error handler functionality."""
    
    def test_error_handler_initialization(self):
        """Test error handler initialization."""
        handler = ErrorHandler()
        
        assert handler.error_stats["total_errors"] == 0
        assert handler.error_stats["recovered_errors"] == 0
        assert handler.error_stats["critical_errors"] == 0
        assert "errors_by_category" in handler.error_stats
        assert "errors_by_severity" in handler.error_stats
        assert "retry_strategies" in handler.__dict__
    
    @pytest.mark.asyncio
    async def test_handle_critical_error(self):
        """Test handling of critical errors."""
        handler = ErrorHandler()
        
        # Create a critical error
        error = BotError("Critical test error", severity=ErrorSeverity.CRITICAL)
        
        # Mock TreeLogger to avoid actual logging
        with patch('app.core.errors.TreeLogger') as mock_logger:
            await handler.handle_error(error)
            
            # Verify error was logged
            assert mock_logger.error.called
    
    def test_create_error_context(self):
        """Test error context creation from handler."""
        handler = ErrorHandler()
        
        # Test with basic error
        error = ValueError("Test error")
        context = handler._create_error_context(error, {"operation": "test_op"}, "test_op")
        
        assert context.operation == "test_op"
        assert context.severity == ErrorSeverity.INFO  # ValueError is categorized as validation -> INFO
        assert context.category == ErrorCategory.VALIDATION
    
    def test_categorize_error(self):
        """Test error categorization."""
        handler = ErrorHandler()
        
        # Test network error
        error = ConnectionError("Connection failed")
        category, severity = handler._categorize_error(error, {})
        assert category == ErrorCategory.NETWORK
        assert severity == ErrorSeverity.WARNING
        
        # Test database error
        error = Exception("Database connection failed")
        category, severity = handler._categorize_error(error, {})
        assert category == ErrorCategory.DATABASE
        assert severity == ErrorSeverity.ERROR
        
        # Test audio error
        error = Exception("Audio playback failed")
        category, severity = handler._categorize_error(error, {})
        assert category == ErrorCategory.AUDIO
        assert severity == ErrorSeverity.ERROR
    
    def test_update_error_stats(self):
        """Test error statistics update."""
        handler = ErrorHandler()
        
        # Create error context
        context = ErrorContext(
            operation="test_op",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.ERROR
        )
        
        # Update stats
        handler._update_error_stats(context)
        
        assert handler.error_stats["total_errors"] == 1
        assert handler.error_stats["errors_by_category"]["database"] == 1
        assert handler.error_stats["errors_by_severity"]["error"] == 1
    
    def test_get_log_level(self):
        """Test log level determination."""
        handler = ErrorHandler()
        
        assert handler._get_log_level(ErrorSeverity.DEBUG) == "debug"
        assert handler._get_log_level(ErrorSeverity.INFO) == "info"
        assert handler._get_log_level(ErrorSeverity.WARNING) == "warning"
        assert handler._get_log_level(ErrorSeverity.ERROR) == "error"
        assert handler._get_log_level(ErrorSeverity.CRITICAL) == "error"
        assert handler._get_log_level(ErrorSeverity.FATAL) == "error"
    
    @pytest.mark.asyncio
    async def test_handle_critical_error_special(self):
        """Test special handling of critical errors."""
        handler = ErrorHandler()
        
        # Create a fatal error
        error = BotError("Fatal error", severity=ErrorSeverity.FATAL)
        
        # Mock TreeLogger
        with patch('app.core.errors.TreeLogger') as mock_logger:
            await handler._handle_critical_error(error, error.context)
            
            # Verify critical error was logged
            assert mock_logger.error.called
    
    @pytest.mark.asyncio
    async def test_safe_execute_with_retry(self):
        """Test safe execution with retry logic."""
        handler = ErrorHandler()
        
        # Mock operation that fails then succeeds
        call_count = 0
        def mock_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"
        
        # Mock TreeLogger
        with patch('app.core.errors.TreeLogger'):
            result = await handler.safe_execute(
                mock_operation,
                {"operation": "test_op"},
                max_retries=3
            )
            
            assert result == "success"
            assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_safe_execute_max_retries_exceeded(self):
        """Test safe execution when max retries are exceeded."""
        handler = ErrorHandler()
        
        # Mock operation that always fails
        def mock_operation():
            raise ValueError("Persistent error")
        
        # Mock TreeLogger
        with patch('app.core.errors.TreeLogger'):
            with pytest.raises(ValueError):
                await handler.safe_execute(
                    mock_operation,
                    {"operation": "test_op"},
                    max_retries=2
                )
    
    def test_should_retry(self):
        """Test retry decision logic."""
        handler = ErrorHandler()
        
        # Test critical error (should not retry)
        error = BotError("Critical error", severity=ErrorSeverity.CRITICAL)
        context = ErrorContext(operation="test_op", severity=ErrorSeverity.CRITICAL)
        assert not handler._should_retry(error, context)
        
        # Test permission error (should not retry)
        error = BotError("Permission error", category=ErrorCategory.PERMISSION)
        context = ErrorContext(operation="test_op", category=ErrorCategory.PERMISSION)
        assert not handler._should_retry(error, context)
        
        # Test validation error (should not retry)
        error = BotError("Validation error", category=ErrorCategory.VALIDATION)
        context = ErrorContext(operation="test_op", category=ErrorCategory.VALIDATION)
        assert not handler._should_retry(error, context)
        
        # Test recoverable error (should retry)
        error = BotError("Network error", category=ErrorCategory.NETWORK)
        context = ErrorContext(operation="test_op", category=ErrorCategory.NETWORK)
        assert handler._should_retry(error, context)
    
    def test_get_error_stats(self):
        """Test error statistics retrieval."""
        handler = ErrorHandler()
        
        # Add some test errors
        context1 = ErrorContext(operation="op1", category=ErrorCategory.DATABASE)
        context2 = ErrorContext(operation="op2", category=ErrorCategory.NETWORK)
        
        handler._update_error_stats(context1)
        handler._update_error_stats(context2)
        
        stats = handler.get_error_stats()
        
        assert stats["total_errors"] == 2
        assert stats["errors_by_category"]["database"] == 1
        assert stats["errors_by_category"]["network"] == 1
        assert "error_rate" in stats
        assert "recovery_rate" in stats
    
    def test_calculate_error_rate(self):
        """Test error rate calculation."""
        handler = ErrorHandler()
        
        # Currently returns 0.0 (placeholder implementation)
        rate = handler._calculate_error_rate()
        assert rate == 0.0
    
    def test_calculate_recovery_rate(self):
        """Test recovery rate calculation."""
        handler = ErrorHandler()
        
        # Test with no errors
        rate = handler._calculate_recovery_rate()
        assert rate == 100.0
        
        # Test with some errors
        handler.error_stats["total_errors"] = 10
        handler.error_stats["recovered_errors"] = 7
        rate = handler._calculate_recovery_rate()
        assert rate == 70.0


class TestErrorIntegration:
    """Test error handling integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_error_recovery_scenario(self):
        """Test complete error recovery scenario."""
        handler = ErrorHandler()
        
        # Mock operation that fails then succeeds
        call_count = 0
        def mock_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Network error")
            return "success"
        
        # Mock TreeLogger
        with patch('app.core.errors.TreeLogger'):
            result = await handler.safe_execute(
                mock_operation,
                {"operation": "network_test"},
                max_retries=3
            )
            
            assert result == "success"
            assert call_count == 2


class TestErrorEdgeCases:
    """Test error handling edge cases."""
    
    @pytest.mark.asyncio
    async def test_safe_execute_with_zero_retries(self):
        """Test safe execute with zero retries."""
        handler = ErrorHandler()
        
        def mock_operation():
            raise ValueError("Test error")
        
        # Mock TreeLogger
        with patch('app.core.errors.TreeLogger'):
            with pytest.raises(ValueError):
                await handler.safe_execute(
                    mock_operation,
                    {"operation": "test_op"},
                    max_retries=0
                )
    
    def test_error_context_with_none_values(self):
        """Test error context with None values."""
        context = ErrorContext(
            operation="test_op",
            service=None,
            user_id=None,
            guild_id=None
        )
        
        assert context.service is None
        assert context.user_id is None
        assert context.guild_id is None
        assert context.operation == "test_op"
    
    def test_bot_error_with_original_error(self):
        """Test bot error with original error."""
        original_error = ValueError("Original error")
        bot_error = BotError("Bot error", original_error=original_error)
        
        assert bot_error.original_error == original_error
        assert "Original error" in str(original_error) 