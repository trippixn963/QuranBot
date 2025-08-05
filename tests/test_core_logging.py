# =============================================================================
# QuranBot - Logging Tests
# =============================================================================
# Comprehensive tests for the tree logger, log retention,
# performance tracking, and file management.
# =============================================================================

import pytest
import tempfile
import json
import gzip
import shutil
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from app.core.logger import (
    TreeLogger, LogFileManager, LogRetentionManager,
    PerformanceTracker, PerformanceTimer, JSONEncoder,
    setup_logging, get_logger, get_performance_summary,
    log_event
)
from app.config.timezone import APP_TIMEZONE


class TestTreeLogger:
    """Test the tree logger functionality."""
    
    @pytest.mark.logging
    @pytest.mark.unit
    def test_logger_initialization(self):
        """Test logger initialization and constants."""
        # Test tree drawing characters
        assert TreeLogger.TREE_BRANCH == "├─"
        assert TreeLogger.TREE_LAST == "└─"
        assert TreeLogger.TREE_CONTINUE == "│ "
        assert TreeLogger.TREE_SPACE == "  "
        
        # Test color codes
        assert TreeLogger.COLORS['INFO'] == '\033[36m'
        assert TreeLogger.COLORS['SUCCESS'] == '\033[32m'
        assert TreeLogger.COLORS['ERROR'] == '\033[31m'
        assert TreeLogger.COLORS['RESET'] == '\033[0m'
        
        # Test level icons
        assert TreeLogger.LEVEL_ICONS['INFO'] == "📍"
        assert TreeLogger.LEVEL_ICONS['SUCCESS'] == "✅"
        assert TreeLogger.LEVEL_ICONS['ERROR'] == "❌"
    
    @pytest.mark.logging
    @pytest.mark.unit
    def test_format_timestamp(self):
        """Test timestamp formatting."""
        timestamp = TreeLogger._format_timestamp()
        assert isinstance(timestamp, str)
        assert len(timestamp) > 0
    
    @pytest.mark.logging
    @pytest.mark.unit
    def test_get_service_icon(self):
        """Test service icon retrieval."""
        # Test known services
        assert TreeLogger._get_service_icon("audio") in TreeLogger.SERVICE_ICONS.values()
        assert TreeLogger._get_service_icon("database") in TreeLogger.SERVICE_ICONS.values()
        
        # Test unknown service
        assert TreeLogger._get_service_icon("unknown_service") == "⚙️"
    
    @pytest.mark.logging
    @pytest.mark.unit
    def test_format_context_tree(self):
        """Test context tree formatting."""
        context = {
            "user_id": 123456789,
            "guild_id": 987654321,
            "operation": "test_operation",
            "nested": {
                "key1": "value1",
                "key2": "value2"
            }
        }
        
        timestamp = TreeLogger._format_timestamp()
        formatted_lines = TreeLogger._format_context_tree(context, timestamp)
        
        assert isinstance(formatted_lines, list)
        assert len(formatted_lines) > 0
        
        # Check that context keys are present
        formatted_text = "\n".join(formatted_lines)
        assert "user_id" in formatted_text
        assert "guild_id" in formatted_text
        assert "operation" in formatted_text
    
    @pytest.mark.logging
    @pytest.mark.unit
    def test_info_logging(self):
        """Test info level logging."""
        # This test just verifies the method doesn't raise an exception
        TreeLogger.info("Test info message", {"test": "context"}, "test_service")
        # If we get here, the test passed

    
    @pytest.mark.logging
    @pytest.mark.unit
    def test_success_logging(self):
        """Test success level logging."""
        # This test just verifies the method doesn't raise an exception
        TreeLogger.success("Test success message", {"test": "context"}, "test_service")
        # If we get here, the test passed
    
    @pytest.mark.logging
    @pytest.mark.unit
    def test_error_logging(self):
        """Test error level logging."""
        # This test just verifies the method doesn't raise an exception
        test_error = ValueError("Test error")
        TreeLogger.error("Test error message", test_error, {"test": "context"}, "test_service")
        # If we get here, the test passed
    
    @pytest.mark.logging
    @pytest.mark.unit
    def test_critical_logging(self):
        """Test critical level logging."""
        # This test just verifies the method doesn't raise an exception
        test_error = RuntimeError("Critical error")
        TreeLogger.critical("Test critical message", test_error, {"test": "context"}, "test_service")
        # If we get here, the test passed
    
    @pytest.mark.logging
    @pytest.mark.unit
    def test_performance_logging(self):
        """Test performance logging."""
        # This test just verifies the method doesn't raise an exception
        TreeLogger.performance("test_operation", 150.5, True, {"test": "context"}, "test_service")
        # If we get here, the test passed
    
    @pytest.mark.logging
    @pytest.mark.unit
    def test_health_logging(self):
        """Test health logging."""
        # This test just verifies the method doesn't raise an exception
        health_data = {
            "state": "running",
            "is_healthy": True,
            "uptime_seconds": 100.0
        }
        TreeLogger.health("test_service", health_data)
        # If we get here, the test passed


class TestLogFileManager:
    """Test log file management functionality."""
    
    @pytest.mark.logging
    @pytest.mark.unit
    def test_log_file_manager_initialization(self, temp_dir):
        """Test log file manager initialization."""
        manager = LogFileManager(temp_dir)
        
        assert manager.base_log_folder == temp_dir
        assert manager.base_log_folder == temp_dir
        assert manager.base_log_folder == temp_dir
        assert manager.performance_tracker is not None
    
    @pytest.mark.logging
    @pytest.mark.unit
    def test_get_log_folder(self, temp_dir):
        """Test log folder creation and naming."""
        manager = LogFileManager(temp_dir)
        log_folder, date_str, time_str = manager._get_log_folder()
        
        assert isinstance(log_folder, Path)
        assert isinstance(date_str, str)
        assert isinstance(time_str, str)
        assert log_folder.parent.parent == temp_dir
        assert date_str in str(log_folder)
        assert time_str in str(log_folder)
    
    @pytest.mark.logging
    @pytest.mark.unit
    def test_write_log(self, temp_dir):
        """Test writing log messages."""
        manager = LogFileManager(temp_dir)
        
        # Write test log
        manager.write_log("Test log message", "INFO", {"test": "context"}, "test_service")
        
        # Check that log files were created
        log_files = list(temp_dir.rglob("*.log"))
        assert len(log_files) > 0
        
        # Check log content
        for log_file in log_files:
            if log_file.name == "log.log":
                content = log_file.read_text()
                assert "Test log message" in content
                assert "Test log message" in content
    
    @pytest.mark.logging
    @pytest.mark.unit
    def test_write_performance(self, temp_dir):
        """Test writing performance data."""
        manager = LogFileManager(temp_dir)
        
        # Write test performance data
        manager.write_performance("test_operation", 150.5, True, "test_service", {"test": "context"})
        
        # Check that performance files were created
        perf_files = list(temp_dir.rglob("*.json"))
        assert len(perf_files) > 0
        
        # Check performance content
        for perf_file in perf_files:
            if perf_file.name == "performance.json":
                content = perf_file.read_text()
                data = json.loads(content)
                assert "test_operation" in str(data)
    
    @pytest.mark.logging
    @pytest.mark.unit
    def test_rotate_if_needed(self, temp_dir):
        """Test log rotation functionality."""
        manager = LogFileManager(temp_dir)
        
        # Write initial log
        manager.write_log("Initial log message", "INFO")
        
        # Simulate rotation by changing time
        with patch('app.core.logger.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime.now() + timedelta(hours=2)
            
            # Write another log (should trigger rotation)
            manager.write_log("Rotated log message", "INFO")
            
            # Check that multiple log files exist
            log_files = list(temp_dir.rglob("*.log"))
            assert len(log_files) > 1


class TestLogRetentionManager:
    """Test log retention and cleanup functionality."""
    
    @pytest.mark.logging
    @pytest.mark.unit
    def test_retention_manager_initialization(self, temp_dir):
        """Test retention manager initialization."""
        manager = LogRetentionManager(temp_dir, retention_days=7, compression_days=3)
        
        assert manager.base_log_folder == temp_dir
        assert manager.retention_days == 7
        assert manager.compression_days == 3
        assert manager.retention_file == temp_dir / "retention.json"
    
    @pytest.mark.logging
    @pytest.mark.unit
    def test_cleanup_old_logs(self, temp_dir):
        """Test cleanup of old log files."""
        manager = LogRetentionManager(temp_dir, retention_days=1, compression_days=1)
        
        # Create old log folders
        old_date = datetime.now() - timedelta(days=2)
        old_folder = temp_dir / old_date.strftime("%Y-%m-%d")
        old_folder.mkdir(exist_ok=True)
        
        # Create a log file in old folder
        (old_folder / "test.log").write_text("old log content")
        
        # Run cleanup
        stats = manager.cleanup_old_logs()
        
        assert isinstance(stats, dict)
        assert "compressed_folders" in stats
        assert "deleted_files" in stats
        assert "freed_bytes" in stats
        assert "errors" in stats
    
    @pytest.mark.logging
    @pytest.mark.unit
    def test_is_date_folder(self):
        """Test date folder detection."""
        manager = LogRetentionManager(Path("test"))
        
        assert manager._is_date_folder("2024-01-15") is True
        assert manager._is_date_folder("2024-13-15") is False  # Invalid month
        assert manager._is_date_folder("invalid-date") is False
        assert manager._is_date_folder("2024-01-15-extra") is False
    
    @pytest.mark.logging
    @pytest.mark.unit
    def test_get_folder_size(self, temp_dir):
        """Test folder size calculation."""
        manager = LogRetentionManager(temp_dir)
        
        # Create test files
        test_file1 = temp_dir / "file1.txt"
        test_file1.write_text("test content 1")
        
        test_file2 = temp_dir / "file2.txt"
        test_file2.write_text("test content 2")
        
        size = manager._get_folder_size(temp_dir)
        assert size > 0
    
    @pytest.mark.logging
    @pytest.mark.unit
    def test_update_retention_metadata(self, temp_dir):
        """Test retention metadata updates."""
        manager = LogRetentionManager(temp_dir)
        
        cleanup_stats = {
            "compressed_folders": 2,
            "deleted_files": 5,
            "freed_bytes": 1024,
            "errors": []
        }
        
        manager._update_retention_metadata(cleanup_stats)
        
        # Check that metadata file was created
        assert manager.retention_file.exists()
        
        # Check metadata content
        metadata = json.loads(manager.retention_file.read_text())
        assert "last_cleanup" in metadata
        assert "last_cleanup" in metadata


class TestPerformanceTracker:
    """Test performance tracking functionality."""
    
    def test_performance_tracker_initialization(self):
        """Test performance tracker initialization."""
        tracker = PerformanceTracker()
        
        assert hasattr(tracker, 'metrics')
        assert 'operations' in tracker.metrics
        assert 'errors_per_hour' in tracker.metrics
        assert 'service_health' in tracker.metrics
        assert 'system_metrics' in tracker.metrics
    
    def test_track_operation(self):
        """Test operation tracking."""
        tracker = PerformanceTracker()
        
        tracker.track_operation("test_operation", 100.0, True, "test_service")
        
        assert len(tracker.metrics["operations"]) == 1
        op = tracker.metrics["operations"][0]
        assert op["operation"] == "test_operation"
        assert op["duration_ms"] == 100.0
        assert op["success"] is True
        assert op["service"] == "test_service"
    
    def test_track_error(self):
        """Test error tracking."""
        tracker = PerformanceTracker()
        
        tracker.track_error("test_service")
        
        # Check that errors_per_hour has an entry for the current hour
        now = datetime.now(APP_TIMEZONE)
        hour_key = now.strftime("%Y-%m-%d_%H")
        assert hour_key in tracker.metrics["errors_per_hour"]
        assert tracker.metrics["errors_per_hour"][hour_key] == 1
    
    def test_update_service_health(self):
        """Test service health tracking."""
        tracker = PerformanceTracker()
        
        health_data = {"status": "healthy", "uptime": 3600}
        tracker.update_service_health("test_service", health_data)
        
        assert "test_service" in tracker.metrics["service_health"]
        service_health = tracker.metrics["service_health"]["test_service"]
        assert service_health["status"] == "healthy"
        assert service_health["uptime"] == 3600
    
    def test_get_performance_summary(self):
        """Test performance summary generation."""
        tracker = PerformanceTracker()
        
        # Add some test data
        tracker.track_operation("test_op", 100.0, True, "test_service")
        tracker.track_error("test_service")
        
        summary = tracker.get_performance_summary()
        
        assert "recent_operations_count" in summary
        assert "successful_operations" in summary
        assert "failed_operations" in summary
        assert "average_duration_ms" in summary
        assert "errors_this_hour" in summary
        assert "service_health_count" in summary
        assert "performance_warnings" in summary


class TestPerformanceTimer:
    """Test performance timer functionality."""
    
    @pytest.mark.logging
    @pytest.mark.unit
    def test_performance_timer_context_manager(self):
        """Test performance timer as context manager."""
        with PerformanceTimer("test_operation", "test_service") as timer:
            # Simulate some work
            import time
            time.sleep(0.01)
        
        # Timer should have recorded the operation
        assert timer.operation == "test_operation"
        assert timer.service == "test_service"
        assert timer.duration_ms > 0
    
    @pytest.mark.logging
    @pytest.mark.unit
    def test_performance_timer_with_exception(self):
        """Test performance timer with exception handling."""
        with pytest.raises(ValueError):
            with PerformanceTimer("test_operation", "test_service") as timer:
                # Simulate an exception
                raise ValueError("Test exception")
        
        # Timer should still record duration even with exception
        # Note: We can't access timer after the exception, but the timer should handle it gracefully


class TestJSONEncoder:
    """Test JSON encoder for complex objects."""
    
    @pytest.mark.logging
    @pytest.mark.unit
    def test_json_encoder_path_objects(self):
        """Test JSON encoding of Path objects."""
        encoder = JSONEncoder()
        path_obj = Path("/test/path")
        
        result = encoder.default(path_obj)
        assert result == "/test/path"
    
    @pytest.mark.logging
    @pytest.mark.unit
    def test_json_encoder_datetime_objects(self):
        """Test JSON encoding of datetime objects."""
        encoder = JSONEncoder()
        dt_obj = datetime.now()
        
        result = encoder.default(dt_obj)
        assert isinstance(result, str)
        assert "T" in result  # ISO format
    
    @pytest.mark.logging
    @pytest.mark.unit
    def test_json_encoder_exception_objects(self):
        """Test JSON encoding of exception objects."""
        encoder = JSONEncoder()
        exc_obj = ValueError("Test error")
        
        result = encoder.default(exc_obj)
        assert isinstance(result, dict)
        assert "type" in result
        assert "message" in result
        assert result["type"] == "ValueError"
        assert result["message"] == "Test error"


class TestLoggingIntegration:
    """Test logging integration scenarios."""
    
    @pytest.mark.logging
    @pytest.mark.integration
    def test_setup_logging(self, temp_dir):
        """Test logging setup."""
        setup_logging("DEBUG", temp_dir, retention_days=7, compression_days=3)
        
        # Check that log directory was created
        assert temp_dir.exists()
    
    @pytest.mark.logging
    @pytest.mark.integration
    def test_get_logger(self):
        """Test logger retrieval."""
        logger = get_logger()
        assert logger is not None
    
    @pytest.mark.logging
    @pytest.mark.integration
    def test_get_performance_summary(self):
        """Test performance summary retrieval."""
        summary = get_performance_summary()
        assert isinstance(summary, dict)
    
    @pytest.mark.logging
    @pytest.mark.integration
    @patch('app.core.logger.TreeLogger.info')
    def test_log_event(self, mock_info):
        """Test log event function."""
        log_event("INFO", "Test message", {"test": "context"}, "test_service")
        
        mock_info.assert_called_once()
        call_args = mock_info.call_args
        assert call_args[0][0] == "Test message"
        assert call_args[1]["context"] == {"test": "context"}
        assert call_args[1]["service"] == "test_service"


class TestLoggingEdgeCases:
    """Test logging edge cases and error conditions."""
    
    def test_logging_with_none_context(self):
        """Test logging with None context."""
        # Should not raise any exceptions
        TreeLogger.info("Test message", context=None)
        TreeLogger.success("Test message", context=None)
        TreeLogger.error("Test message", context=None)
    
    def test_logging_with_complex_context(self):
        """Test logging with complex context objects."""
        complex_context = {
            "list_data": [1, 2, 3],
            "dict_data": {"nested": {"key": "value"}},
            "set_data": {1, 2, 3},
            "tuple_data": (1, 2, 3)
        }
        
        # Should handle complex context without errors
        TreeLogger.info("Test message", context=complex_context)
    
    def test_logging_with_unicode_content(self):
        """Test logging with Unicode content."""
        unicode_context = {
            "arabic": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ"
        }
        
        # Should handle Unicode content without errors
        TreeLogger.info("Test message with Unicode: 🕌 📖 🎵", context=unicode_context)
    
    def test_performance_timer_with_zero_duration(self):
        """Test performance timer with zero duration."""
        with PerformanceTimer("instant_operation", "test_service") as timer:
            pass  # Instant operation
        
        assert timer.duration_ms >= 0
        assert timer.operation == "instant_operation" 