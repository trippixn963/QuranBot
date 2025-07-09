#!/usr/bin/env python3
# =============================================================================
# QuranBot - Tree Logger Tests
# =============================================================================
# Comprehensive tests for tree-style logging functionality
# =============================================================================

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import pytz

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from utils.tree_log import (
    TREE_SYMBOLS,
    end_tree_section,
    get_log_date,
    get_timestamp,
    get_tree_prefix,
    log_error_with_traceback,
    log_initialization_tree,
    log_perfect_tree_section,
    log_progress,
    log_run_end,
    log_run_header,
    log_status,
    log_tree_group,
    log_user_interaction,
    log_version_info,
    log_voice_activity_tree,
    log_warning_with_context,
    reset_section_tracking,
    reset_tree_structure,
    setup_log_directories,
    start_tree_section,
    write_to_log_files,
)


class TestTreeLog:
    """Test suite for tree-style logging functionality"""

    def setup_method(self):
        """Set up test environment"""
        # Create test log directory
        self.test_dir = Path("test_logs")
        self.test_dir.mkdir(exist_ok=True)

        # Mock datetime for consistent timestamps
        self.mock_now = datetime(2024, 1, 1, 12, 0, tzinfo=pytz.UTC)
        self.mock_est = self.mock_now.astimezone(pytz.timezone("US/Eastern"))

        # Reset tree structure
        reset_tree_structure()
        reset_section_tracking()

    def teardown_method(self):
        """Clean up test environment"""
        if self.test_dir.exists():
            import shutil

            shutil.rmtree(self.test_dir)

    def test_tree_structure(self):
        """Test tree structure generation"""
        # Test root level
        assert get_tree_prefix() == TREE_SYMBOLS["branch"]
        assert get_tree_prefix(is_last_item=True) == TREE_SYMBOLS["last"]

        # Test nested level
        start_tree_section()
        assert get_tree_prefix() == TREE_SYMBOLS["pipe"] + TREE_SYMBOLS["branch"]
        assert (
            get_tree_prefix(is_last_item=True)
            == TREE_SYMBOLS["pipe"] + TREE_SYMBOLS["last"]
        )

        # Test multiple levels
        start_tree_section()
        prefix = get_tree_prefix()
        assert prefix.count(TREE_SYMBOLS["pipe"]) == 2
        assert prefix.endswith(TREE_SYMBOLS["branch"])

        # Test section ending
        end_tree_section()
        end_tree_section()
        assert get_tree_prefix() == TREE_SYMBOLS["branch"]

    def test_timestamp_formatting(self):
        """Test timestamp generation and formatting"""
        with patch("datetime.datetime") as mock_dt:
            mock_dt.now.return_value = self.mock_now
            timestamp = get_timestamp()
            assert timestamp == "[01/01 07:00 AM EST]"  # 12:00 UTC = 07:00 EST

    def test_log_date(self):
        """Test log date generation"""
        with patch("datetime.datetime") as mock_dt:
            mock_dt.now.return_value = self.mock_now
            log_date = get_log_date()
            assert log_date == "2024-01-01"

    def test_log_directories(self):
        """Test log directory setup"""
        with patch("pathlib.Path") as mock_path:
            mock_path.return_value = self.test_dir
            log_dir = setup_log_directories()
            assert log_dir is not None
            assert (self.test_dir / "logs/2024-01-01").exists()

    def test_file_writing(self):
        """Test log file writing"""
        with patch("pathlib.Path") as mock_path:
            mock_path.return_value = self.test_dir
            write_to_log_files("Test message", "INFO", "test")

            # Check main log file
            log_file = self.test_dir / "2024-01-01.log"
            assert log_file.exists()
            content = log_file.read_text()
            assert "Test message" in content

            # Check JSON log file
            json_file = self.test_dir / "2024-01-01.json"
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
            run_id = log_run_header("TestBot", "1.0.0")
            assert run_id is not None

            # Check header content
            log_file = self.test_dir / "2024-01-01.log"
            content = log_file.read_text()
            assert "TestBot v1.0.0" in content
            assert run_id in content

            # Test run footer
            log_run_end(run_id, "Test complete")
            content = log_file.read_text()
            assert "Bot Run Ended" in content
            assert "Test complete" in content

    def test_user_interaction_logging(self):
        """Test user interaction logging"""
        with patch("pathlib.Path") as mock_path:
            mock_path.return_value = self.test_dir

            # Log user interaction
            log_user_interaction(
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
            log_voice_activity_tree(
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

    def test_initialization_logging(self):
        """Test initialization logging"""
        with patch("pathlib.Path") as mock_path:
            mock_path.return_value = self.test_dir

            # Log initialization steps
            steps = [
                ("Database", "success", "Connected successfully"),
                ("Cache", "success", "Initialized"),
                ("API", "error", "Connection failed"),
            ]
            log_initialization_tree("TestComponent", steps)

            # Check log content
            log_file = self.test_dir / "2024-01-01.log"
            content = log_file.read_text()
            assert "TestComponent Initialization" in content
            assert "Database: ✅" in content
            assert "Cache: ✅" in content
            assert "API: ❌" in content

    def test_error_logging(self):
        """Test error logging with traceback"""
        with patch("pathlib.Path") as mock_path:
            mock_path.return_value = self.test_dir

            # Create test exception
            try:
                raise ValueError("Test error")
            except ValueError as e:
                log_error_with_traceback("Error occurred", e)

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
            log_warning_with_context(
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
            log_progress(5, 10, "📊")

            # Check log content
            log_file = self.test_dir / "2024-01-01.log"
            content = log_file.read_text()
            assert "📊 Progress (5/10)" in content

    def test_status_logging(self):
        """Test status logging"""
        with patch("pathlib.Path") as mock_path:
            mock_path.return_value = self.test_dir

            # Log different status types
            log_status("Normal message")
            log_status("Warning message", "WARNING", "⚠️")
            log_status("Error message", "ERROR", "❌")

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
            log_version_info(
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
            log_tree_group("Test Group", items, "📊")

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
            log_perfect_tree_section(
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
