#!/usr/bin/env python3
# =============================================================================
# QuranBot - Tree Logger Tests
# =============================================================================
# Comprehensive tests for tree-style logging functionality
# =============================================================================

from datetime import datetime
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

import pytest
import pytz

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from utils.tree_log import TREE_SYMBOLS, TreeLogger


class TestTreeLog:
    """Test suite for tree-style logging functionality"""

    @pytest.fixture(autouse=True)
    def setup_test(self):
        """Set up test environment"""
        # Create test log directory
        self.test_dir = Path("test_logs")
        if not self.test_dir.exists():
            self.test_dir.mkdir(parents=True)

        # Create logs subdirectory
        self.logs_dir = self.test_dir / "logs"
        if not self.logs_dir.exists():
            self.logs_dir.mkdir(parents=True)

        # Create test date directory
        self.date_dir = self.logs_dir / "2024-01-01"
        if not self.date_dir.exists():
            self.date_dir.mkdir(parents=True)

        # Initialize TreeLogger
        self.logger = TreeLogger()
        self.logger.log_dir = self.test_dir

        # Mock datetime for consistent timestamps
        self.mock_now = datetime(2024, 1, 1, 12, 0, tzinfo=pytz.UTC)
        self.mock_est = self.mock_now.astimezone(pytz.timezone("US/Eastern"))

        # Create initial log files
        self.log_file = self.date_dir / "2024-01-01.log"
        self.log_file.touch()
        self.json_file = self.date_dir / "2024-01-01.json"
        self.json_file.touch()
        self.error_file = self.date_dir / "2024-01-01-errors.log"
        self.error_file.touch()

        # Mock datetime globally
        self.datetime_patcher = patch("datetime.datetime")
        self.mock_datetime = self.datetime_patcher.start()
        self.mock_datetime.now.return_value = self.mock_now

        yield

        # Clean up
        self.datetime_patcher.stop()
        if self.test_dir.exists():
            import shutil

            shutil.rmtree(self.test_dir)

    def test_tree_structure(self):
        """Test tree structure generation"""
        # Test root level
        assert self.logger.get_tree_prefix() == TREE_SYMBOLS["branch"]
        assert self.logger.get_tree_prefix(is_last_item=True) == TREE_SYMBOLS["last"]

        # Test nested level
        self.logger.start_tree_section()
        assert (
            self.logger.get_tree_prefix()
            == TREE_SYMBOLS["pipe"] + TREE_SYMBOLS["branch"]
        )
        assert (
            self.logger.get_tree_prefix(is_last_item=True)
            == TREE_SYMBOLS["pipe"] + TREE_SYMBOLS["last"]
        )

        # Test multiple levels
        self.logger.start_tree_section()
        prefix = self.logger.get_tree_prefix()
        assert prefix.count(TREE_SYMBOLS["pipe"]) == 2
        assert prefix.endswith(TREE_SYMBOLS["branch"])

        # Test section ending
        self.logger.end_tree_section()
        self.logger.end_tree_section()
        assert self.logger.get_tree_prefix() == TREE_SYMBOLS["branch"]

    def test_timestamp_formatting(self):
        """Test timestamp generation and formatting"""
        timestamp = self.logger._get_timestamp()
        assert timestamp == "[01/01 07:00 AM EST]"  # 12:00 UTC = 07:00 EST

    def test_log_date(self):
        """Test log date generation"""
        log_date = self.logger._get_log_date()
        assert log_date == "2024-01-01"

    def test_log_directories(self):
        """Test log directory setup"""
        log_dir = self.logger._setup_log_directories()
        assert log_dir is not None
        assert (self.test_dir / "logs/2024-01-01").exists()

    def test_file_writing(self):
        """Test log file writing"""
        self.logger._write_to_log_files("Test message", "INFO", "test")

        # Check main log file
        log_file = self.date_dir / "2024-01-01.log"
        assert log_file.exists()
        content = log_file.read_text()
        assert "Test message" in content

        # Check JSON log file
        json_file = self.date_dir / "2024-01-01.json"
        assert json_file.exists()
        content = json_file.read_text()
        data = json.loads(content)
        assert data["message"] == "Test message"
        assert data["level"] == "INFO"
        assert data["type"] == "test"

    def test_run_logging(self):
        """Test run header and footer logging"""
        with patch("pathlib.Path") as mock_path:
            mock_path.return_value = self.test_dir

            # Test run header
            run_id = self.logger.log_run_header("TestBot", "1.0.0")
            assert run_id is not None

            # Check header content
            log_file = self.test_dir / "2024-01-01.log"
            content = log_file.read_text()
            assert "TestBot v1.0.0" in content
            assert run_id in content

            # Test run footer
            self.logger.log_run_end(run_id, "Test complete")
            content = log_file.read_text()
            assert "Bot Run Ended" in content
            assert "Test complete" in content

    def test_user_interaction_logging(self):
        """Test user interaction logging"""
        with patch("pathlib.Path") as mock_path:
            mock_path.return_value = self.test_dir

            # Log user interaction
            self.logger.log_user_interaction(
                "button_click",
                "TestUser",
                123456789,
                "Clicked play button",
                {"button_id": "play", "state": "playing"},
            )

            # Check log content
            log_file = self.test_dir / "2024-01-01.log"
            content = log_file.read_text()
            assert "User Interaction" in content
            assert "TestUser" in content
            assert "123456789" in content
            assert "Clicked play button" in content
            assert "button_id: play" in content

    def test_voice_activity_logging(self):
        """Test voice activity logging"""
        with patch("pathlib.Path") as mock_path:
            mock_path.return_value = self.test_dir

            # Log voice activity
            self.logger.log_voice_activity_tree(
                "TestUser",
                "join",
                {
                    "channel": "Test Channel",
                    "timestamp": "2024-01-01T12:00:00Z",
                },
            )

            # Check log content
            log_file = self.test_dir / "2024-01-01.log"
            content = log_file.read_text()
            assert "Voice Activity" in content
            assert "TestUser" in content
            assert "Test Channel" in content

    def test_error_logging(self):
        """Test error logging with traceback"""
        with patch("pathlib.Path") as mock_path:
            mock_path.return_value = self.test_dir

            # Create test exception
            try:
                raise ValueError("Test error")
            except ValueError as e:
                self.logger.log_error_with_traceback("Error occurred", e)

            # Check error log
            error_log = self.test_dir / "2024-01-01-errors.log"
            content = error_log.read_text()
            assert "Error occurred" in content
            assert "ValueError" in content
            assert "Test error" in content
            assert "Traceback" in content

    def test_warning_logging(self):
        """Test warning logging with context"""
        with patch("pathlib.Path") as mock_path:
            mock_path.return_value = self.test_dir

            # Log warning
            self.logger.log_warning_with_context(
                "Resource not found",
                "File missing: config.json",
            )

            # Check warning log
            log_file = self.test_dir / "2024-01-01.log"
            content = log_file.read_text()
            assert "WARNING" in content
            assert "Resource not found" in content
            assert "File missing: config.json" in content

    def test_progress_logging(self):
        """Test progress logging"""
        with patch("pathlib.Path") as mock_path:
            mock_path.return_value = self.test_dir

            # Log progress
            self.logger.log_progress(5, 10, "📊")

            # Check log content
            log_file = self.test_dir / "2024-01-01.log"
            content = log_file.read_text()
            assert "📊 Progress (5/10)" in content

    def test_status_logging(self):
        """Test status logging"""
        with patch("pathlib.Path") as mock_path:
            mock_path.return_value = self.test_dir

            # Log different status types
            self.logger.log_status("Normal message")
            self.logger.log_status("Warning message", "WARNING", "⚠️")
            self.logger.log_status("Error message", "ERROR", "❌")

            # Check log content
            log_file = self.test_dir / "2024-01-01.log"
            content = log_file.read_text()
            assert "📍 Normal message" in content
            assert "⚠️ Warning message" in content
            assert "❌ Error message" in content

    def test_version_logging(self):
        """Test version information logging"""
        with patch("pathlib.Path") as mock_path:
            mock_path.return_value = self.test_dir

            # Log version info
            self.logger.log_version_info(
                "TestBot",
                "1.0.0",
                {"build": "123", "environment": "test"},
            )

            # Check log content
            log_file = self.test_dir / "2024-01-01.log"
            content = log_file.read_text()
            assert "TestBot Version Information" in content
            assert "version: 1.0.0" in content
            assert "build: 123" in content
            assert "environment: test" in content

    def test_tree_group_logging(self):
        """Test tree group logging"""
        with patch("pathlib.Path") as mock_path:
            mock_path.return_value = self.test_dir

            # Log tree group
            items = [
                ("name", "TestGroup"),
                ("status", "active"),
                ("count", 5),
            ]
            self.logger.log_tree_group("Test Group", items, "📊")

            # Check log content
            log_file = self.test_dir / "2024-01-01.log"
            content = log_file.read_text()
            assert "📊 Test Group" in content
            assert "name: TestGroup" in content
            assert "status: active" in content
            assert "count: 5" in content

    def test_perfect_tree_section(self):
        """Test perfect tree section logging"""
        with patch("pathlib.Path") as mock_path:
            mock_path.return_value = self.test_dir

            # Log perfect tree section
            items = [
                ("name", "TestSection"),
                ("status", "active"),
            ]
            nested_groups = {
                "Group1": [
                    ("item1", "value1"),
                    ("item2", "value2"),
                ],
                "Group2": [
                    ("item3", "value3"),
                    ("item4", "value4"),
                ],
            }
            self.logger.log_perfect_tree_section(
                "Test Section",
                items,
                "📊",
                nested_groups,
            )

            # Check log content
            log_file = self.test_dir / "2024-01-01.log"
            content = log_file.read_text()
            assert "📊 Test Section" in content
            assert "name: TestSection" in content
            assert "status: active" in content
            assert "Group1" in content
            assert "item1: value1" in content
            assert "Group2" in content
            assert "item4: value4" in content
