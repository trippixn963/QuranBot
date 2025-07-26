# =============================================================================
# QuranBot - Structured Logger Tests
# =============================================================================
# Comprehensive tests for the structured logging system including JSON
# formatting, correlation ID management, async support, and logging service.
# =============================================================================

import asyncio
import json
import logging
from pathlib import Path
import tempfile
from unittest.mock import MagicMock

import pytest

from src.core.structured_logger import (
    LoggingService,
    StructuredFormatter,
    StructuredLogger,
    correlation_id,
    create_correlation_context,
    get_logging_service,
    log_with_correlation,
    set_logging_service,
)


class TestStructuredFormatter:
    """Test cases for StructuredFormatter class."""

    def test_format_basic_log_record(self):
        """Test basic log record formatting to JSON."""
        formatter = StructuredFormatter()

        # Create a log record
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.module = "test_module"
        record.funcName = "test_function"

        # Format the record
        result = formatter.format(record)

        # Parse JSON result
        log_data = json.loads(result)

        # Verify required fields
        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test_logger"
        assert log_data["message"] == "Test message"
        assert log_data["module"] == "test_module"
        assert log_data["function"] == "test_function"
        assert log_data["line"] == 42
        assert "timestamp" in log_data
        assert "correlation_id" in log_data

        # Verify timestamp format
        assert log_data["timestamp"].endswith("Z")

    def test_format_with_context(self):
        """Test log record formatting with context data."""
        formatter = StructuredFormatter()

        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="/test/path.py",
            lineno=42,
            msg="Error occurred",
            args=(),
            exc_info=None,
        )
        record.module = "test_module"
        record.funcName = "test_function"
        record.context = {"user_id": 12345, "action": "play_audio"}

        result = formatter.format(record)
        log_data = json.loads(result)

        assert log_data["context"] == {"user_id": 12345, "action": "play_audio"}

    def test_format_with_exception(self):
        """Test log record formatting with exception information."""
        formatter = StructuredFormatter()

        try:
            raise ValueError("Test exception")
        except ValueError:
            import sys

            exc_info = sys.exc_info()
            record = logging.LogRecord(
                name="test_logger",
                level=logging.ERROR,
                pathname="/test/path.py",
                lineno=42,
                msg="Exception occurred",
                args=(),
                exc_info=exc_info,
            )
            record.module = "test_module"
            record.funcName = "test_function"

        result = formatter.format(record)
        log_data = json.loads(result)

        assert "exception" in log_data
        assert log_data["exception"]["type"] == "ValueError"
        assert log_data["exception"]["message"] == "Test exception"
        assert "traceback" in log_data["exception"]

    def test_format_with_correlation_id(self):
        """Test log record formatting with correlation ID from context."""
        formatter = StructuredFormatter()
        test_correlation_id = "test-correlation-123"

        # Set correlation ID in context
        correlation_id.set(test_correlation_id)

        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.module = "test_module"
        record.funcName = "test_function"

        result = formatter.format(record)
        log_data = json.loads(result)

        assert log_data["correlation_id"] == test_correlation_id


class TestStructuredLogger:
    """Test cases for StructuredLogger class."""

    @pytest.fixture
    def temp_log_file(self):
        """Create temporary log file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
            temp_path = Path(f.name)
        yield temp_path
        # Cleanup
        if temp_path.exists():
            temp_path.unlink()

    def test_logger_initialization(self, temp_log_file):
        """Test logger initialization with various configurations."""
        logger = StructuredLogger(
            name="test_logger",
            level=logging.DEBUG,
            log_file=temp_log_file,
            console_output=False,
        )

        assert logger._logger.name == "test_logger"
        assert logger._logger.level == logging.DEBUG
        assert len(logger._logger.handlers) == 1  # File handler only

    def test_correlation_id_management(self):
        """Test correlation ID setting and getting."""
        logger = StructuredLogger("test_logger", console_output=False)

        # Test setting custom correlation ID
        test_id = "custom-correlation-id"
        result_id = logger.set_correlation_id(test_id)
        assert result_id == test_id
        assert logger.get_correlation_id() == test_id

        # Test generating new correlation ID
        new_id = logger.set_correlation_id()
        assert new_id != test_id
        assert logger.get_correlation_id() == new_id

    @pytest.mark.asyncio
    async def test_async_logging_methods(self, temp_log_file):
        """Test all async logging methods."""
        logger = StructuredLogger(
            name="test_logger", log_file=temp_log_file, console_output=False
        )

        test_context = {"test_key": "test_value"}

        # Test all log levels
        await logger.debug("Debug message", test_context)
        await logger.info("Info message", test_context)
        await logger.warning("Warning message", test_context)
        await logger.error("Error message", test_context)
        await logger.critical("Critical message", test_context)

        # Verify log file was written
        assert temp_log_file.exists()

        # Read and verify log entries
        log_content = temp_log_file.read_text()
        log_lines = [line for line in log_content.strip().split("\n") if line]

        assert len(log_lines) == 5

        # Verify each log entry
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        messages = [
            "Debug message",
            "Info message",
            "Warning message",
            "Error message",
            "Critical message",
        ]

        for i, (level, message) in enumerate(zip(levels, messages, strict=False)):
            log_data = json.loads(log_lines[i])
            assert log_data["level"] == level
            assert log_data["message"] == message
            assert log_data["context"] == test_context

    @pytest.mark.asyncio
    async def test_error_logging_with_exception(self, temp_log_file):
        """Test error logging with exception information."""
        logger = StructuredLogger(
            name="test_logger", log_file=temp_log_file, console_output=False
        )

        try:
            raise RuntimeError("Test runtime error")
        except RuntimeError:
            await logger.error("Error with exception", exc_info=True)

        # Verify exception info was logged
        log_content = temp_log_file.read_text()
        log_data = json.loads(log_content.strip())

        assert "exception" in log_data
        assert log_data["exception"]["type"] == "RuntimeError"
        assert log_data["exception"]["message"] == "Test runtime error"

    @pytest.mark.asyncio
    async def test_concurrent_logging(self, temp_log_file):
        """Test concurrent logging operations."""
        logger = StructuredLogger(
            name="test_logger", log_file=temp_log_file, console_output=False
        )

        # Create multiple concurrent logging tasks
        async def log_task(task_id: int):
            for i in range(5):
                await logger.info(
                    f"Task {task_id} message {i}", {"task_id": task_id, "iteration": i}
                )

        # Run concurrent tasks
        tasks = [log_task(i) for i in range(3)]
        await asyncio.gather(*tasks)

        # Verify all messages were logged
        log_content = temp_log_file.read_text()
        log_lines = [line for line in log_content.strip().split("\n") if line]

        assert len(log_lines) == 15  # 3 tasks * 5 messages each


class TestLoggingService:
    """Test cases for LoggingService class."""

    @pytest.fixture
    def temp_log_dir(self):
        """Create temporary log directory for testing."""
        import shutil
        import tempfile

        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        # Cleanup
        shutil.rmtree(temp_dir)

    def test_service_initialization(self, temp_log_dir):
        """Test logging service initialization."""
        service = LoggingService(
            default_level=logging.DEBUG,
            log_directory=temp_log_dir,
            console_output=False,
        )

        assert service._default_level == logging.DEBUG
        assert service._log_directory == temp_log_dir
        assert service._console_output is False
        assert temp_log_dir.exists()

    def test_get_logger(self, temp_log_dir):
        """Test logger creation and retrieval."""
        service = LoggingService(log_directory=temp_log_dir, console_output=False)

        # Get logger with default settings
        logger1 = service.get_logger("test.module1")
        assert isinstance(logger1, StructuredLogger)
        assert logger1._logger.name == "test.module1"

        # Get same logger again (should return cached instance)
        logger2 = service.get_logger("test.module1")
        assert logger1 is logger2

        # Get logger with custom settings
        logger3 = service.get_logger(
            "test.module2", level=logging.ERROR, log_file="custom.log"
        )
        assert logger3._logger.level == logging.ERROR

    def test_set_global_level(self, temp_log_dir):
        """Test setting global logging level."""
        service = LoggingService(
            default_level=logging.INFO, log_directory=temp_log_dir, console_output=False
        )

        # Create some loggers
        logger1 = service.get_logger("test.module1")
        logger2 = service.get_logger("test.module2")

        assert logger1._logger.level == logging.INFO
        assert logger2._logger.level == logging.INFO

        # Change global level
        service.set_global_level(logging.ERROR)

        assert logger1._logger.level == logging.ERROR
        assert logger2._logger.level == logging.ERROR

    @pytest.mark.asyncio
    async def test_service_shutdown(self, temp_log_dir):
        """Test logging service shutdown."""
        service = LoggingService(log_directory=temp_log_dir, console_output=False)

        # Create logger and log some messages
        logger = service.get_logger("test.module")
        await logger.info("Test message before shutdown")

        # Mock handlers to verify shutdown calls
        mock_handler = MagicMock()
        logger._logger.handlers = [mock_handler]

        # Shutdown service
        await service.shutdown()

        # Verify handlers were flushed and closed
        mock_handler.flush.assert_called_once()
        mock_handler.close.assert_called_once()


class TestUtilityFunctions:
    """Test cases for utility functions."""

    @pytest.mark.asyncio
    async def test_log_with_correlation(self):
        """Test log_with_correlation utility function."""
        logger = StructuredLogger("test_logger", console_output=False)

        # Test with custom correlation ID
        custom_id = "custom-correlation-123"
        result_id = await log_with_correlation(
            logger, "info", "Test message", {"key": "value"}, custom_id
        )

        assert result_id == custom_id
        assert logger.get_correlation_id() == custom_id

        # Test with auto-generated correlation ID
        result_id2 = await log_with_correlation(logger, "warning", "Another message")

        assert result_id2 != custom_id
        assert logger.get_correlation_id() == result_id2

    def test_create_correlation_context(self):
        """Test create_correlation_context utility function."""
        # Test with custom correlation ID
        custom_id = "test-correlation-456"
        result_id = create_correlation_context(custom_id)

        assert result_id == custom_id
        assert correlation_id.get() == custom_id

        # Test with auto-generated correlation ID
        result_id2 = create_correlation_context()

        assert result_id2 != custom_id
        assert correlation_id.get() == result_id2

    def test_global_logging_service(self):
        """Test global logging service management."""
        # Initially should be None
        assert get_logging_service() is None

        # Set service
        service = LoggingService(console_output=False)
        set_logging_service(service)

        # Should return the set service
        assert get_logging_service() is service


class TestIntegration:
    """Integration tests for the structured logging system."""

    @pytest.mark.asyncio
    async def test_end_to_end_logging_workflow(self, tmp_path):
        """Test complete logging workflow from service to file output."""
        log_dir = tmp_path / "logs"

        # Initialize logging service
        service = LoggingService(
            default_level=logging.INFO, log_directory=log_dir, console_output=False
        )
        set_logging_service(service)

        # Get logger
        logger = service.get_logger("integration.test")

        # Set correlation ID
        correlation_id = logger.set_correlation_id("integration-test-123")

        # Log various messages
        await logger.info(
            "Starting integration test",
            {"test_type": "integration", "component": "structured_logger"},
        )

        await logger.warning("Test warning message", {"warning_type": "test"})

        try:
            raise ValueError("Integration test exception")
        except ValueError:
            await logger.error(
                "Test error with exception",
                {"error_context": "integration_test"},
                exc_info=True,
            )

        # Verify log file was created
        log_file = log_dir / "integration_test.log"
        assert log_file.exists()

        # Read and verify log content
        log_content = log_file.read_text()
        log_lines = [line for line in log_content.strip().split("\n") if line]

        assert len(log_lines) == 3

        # Verify each log entry
        for line in log_lines:
            log_data = json.loads(line)
            assert log_data["correlation_id"] == correlation_id
            assert log_data["logger"] == "integration.test"
            assert "timestamp" in log_data
            assert "context" in log_data

        # Verify specific log entries
        info_log = json.loads(log_lines[0])
        assert info_log["level"] == "INFO"
        assert info_log["message"] == "Starting integration test"
        assert info_log["context"]["test_type"] == "integration"

        warning_log = json.loads(log_lines[1])
        assert warning_log["level"] == "WARNING"
        assert warning_log["message"] == "Test warning message"

        error_log = json.loads(log_lines[2])
        assert error_log["level"] == "ERROR"
        assert error_log["message"] == "Test error with exception"
        assert "exception" in error_log
        assert error_log["exception"]["type"] == "ValueError"

        # Cleanup
        await service.shutdown()


if __name__ == "__main__":
    pytest.main([__file__])
