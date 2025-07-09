#!/usr/bin/env python3
# =============================================================================
# QuranBot - State Manager Tests
# =============================================================================
# Comprehensive tests for state persistence and data protection
# =============================================================================

import json
import os
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from utils.state_manager import StateManager


class TestStateManager:
    """Test suite for state persistence functionality"""

    def setup_method(self):
        """Set up test environment"""
        # Create temporary test directories
        self.test_dir = Path("test_state_data")
        self.data_dir = self.test_dir / "data"
        self.backup_dir = self.test_dir / "backup"
        self.temp_backup_dir = self.backup_dir / "temp"

        # Create directories
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.temp_backup_dir.mkdir(parents=True, exist_ok=True)

        # Initialize manager with test paths
        self.manager = StateManager()
        self.manager.data_dir = self.data_dir
        self.manager.backup_dir = self.backup_dir
        self.manager.temp_backup_dir = self.temp_backup_dir

        # Test data
        self.test_surah = 2
        self.test_position = 30.0
        self.test_reciter = "Test Reciter"
        self.test_duration = 300.0

    def teardown_method(self):
        """Clean up test environment"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_default_state(self):
        """Test default state initialization"""
        # Test default playback state
        state = self.manager.load_playback_state()
        assert state["current_surah"] == 1
        assert state["current_position"] == 0.0
        assert state["current_reciter"] == "Saad Al Ghamdi"
        assert state["is_playing"] is False
        assert state["loop_enabled"] is False
        assert state["shuffle_enabled"] is False

        # Test default bot stats
        stats = self.manager.load_bot_stats()
        assert stats["total_runtime"] == 0.0
        assert stats["total_sessions"] == 0
        assert stats["surahs_completed"] == 0
        assert stats["favorite_reciter"] == "Saad Al Ghamdi"

    def test_playback_state_save_load(self):
        """Test playback state persistence"""
        # Save playback state
        success = self.manager.save_playback_state(
            current_surah=self.test_surah,
            current_position=self.test_position,
            current_reciter=self.test_reciter,
            is_playing=True,
            loop_enabled=True,
            shuffle_enabled=True,
        )
        assert success is True

        # Load and verify
        state = self.manager.load_playback_state()
        assert state["current_surah"] == self.test_surah
        assert state["current_position"] == self.test_position
        assert state["current_reciter"] == self.test_reciter
        assert state["is_playing"] is True
        assert state["loop_enabled"] is True
        assert state["shuffle_enabled"] is True

    def test_bot_stats_save_load(self):
        """Test bot statistics persistence"""
        # Save bot stats
        success = self.manager.save_bot_stats(
            total_runtime=100.0,
            increment_sessions=True,
            last_startup="2024-01-01T00:00:00Z",
            last_shutdown="2024-01-01T01:00:00Z",
            increment_completed=True,
            favorite_reciter=self.test_reciter,
        )
        assert success is True

        # Load and verify
        stats = self.manager.load_bot_stats()
        assert stats["total_runtime"] == 100.0
        assert stats["total_sessions"] == 1
        assert stats["surahs_completed"] == 1
        assert stats["last_startup"] == "2024-01-01T00:00:00Z"
        assert stats["last_shutdown"] == "2024-01-01T01:00:00Z"
        assert stats["favorite_reciter"] == self.test_reciter

    def test_backup_recovery(self):
        """Test backup creation and recovery"""
        # Save initial state
        self.manager.save_playback_state(
            current_surah=self.test_surah,
            current_position=self.test_position,
            current_reciter=self.test_reciter,
        )

        # Verify backup created
        backup_file = self.temp_backup_dir / "playback_state.backup"
        assert backup_file.exists()

        # Corrupt main file
        playback_file = self.data_dir / "playback_state.json"
        playback_file.write_text("corrupted data")

        # Load should recover from backup
        state = self.manager.load_playback_state()
        assert state["current_surah"] == self.test_surah
        assert state["current_position"] == self.test_position
        assert state["current_reciter"] == self.test_reciter

    def test_emergency_recovery(self):
        """Test emergency backup recovery"""
        # Create emergency backup
        emergency_file = self.data_dir / "emergency_playback_test.json"
        emergency_data = {
            "playback_state": {
                "current_surah": self.test_surah,
                "current_position": self.test_position,
                "current_reciter": self.test_reciter,
                "is_playing": False,
                "loop_enabled": False,
                "shuffle_enabled": False,
            }
        }
        emergency_file.write_text(json.dumps(emergency_data))

        # Corrupt main and backup files
        playback_file = self.data_dir / "playback_state.json"
        backup_file = self.temp_backup_dir / "playback_state.backup"
        playback_file.write_text("corrupted data")
        backup_file.write_text("corrupted data")

        # Load should recover from emergency backup
        state = self.manager.load_playback_state()
        assert state["current_surah"] == self.test_surah
        assert state["current_position"] == self.test_position
        assert state["current_reciter"] == self.test_reciter

    def test_startup_shutdown_tracking(self):
        """Test startup and shutdown time tracking"""
        # Mark startup
        with patch("datetime.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
            success = self.manager.mark_startup()
            assert success is True

        # Verify startup recorded
        stats = self.manager.load_bot_stats()
        assert stats["last_startup"] == "2024-01-01T00:00:00+00:00"
        assert stats["total_sessions"] == 1

        # Mark shutdown
        with patch("datetime.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 1, 1, 0, tzinfo=timezone.utc)
            success = self.manager.mark_shutdown()
            assert success is True

        # Verify shutdown recorded
        stats = self.manager.load_bot_stats()
        assert stats["last_shutdown"] == "2024-01-01T01:00:00+00:00"

    def test_surah_completion_tracking(self):
        """Test surah completion tracking"""
        # Mark multiple completions
        for _ in range(3):
            success = self.manager.mark_surah_completed()
            assert success is True

        # Verify completions counted
        stats = self.manager.load_bot_stats()
        assert stats["surahs_completed"] == 3

    def test_resume_info(self):
        """Test resume information retrieval"""
        # Save playback state
        self.manager.save_playback_state(
            current_surah=self.test_surah,
            current_position=self.test_position,
            current_reciter=self.test_reciter,
            total_duration=self.test_duration,
        )

        # Get resume info
        info = self.manager.get_resume_info()
        assert info["surah"] == self.test_surah
        assert info["position"] == self.test_position
        assert info["reciter"] == self.test_reciter
        assert info["duration"] == self.test_duration
        assert info["should_resume"] is True

    def test_state_clearing(self):
        """Test state file clearing"""
        # Create state files
        self.manager.save_playback_state(
            current_surah=self.test_surah,
            current_position=self.test_position,
            current_reciter=self.test_reciter,
        )
        self.manager.save_bot_stats(total_runtime=100.0)

        # Clear state
        success = self.manager.clear_state()
        assert success is True

        # Verify files removed
        playback_file = self.data_dir / "playback_state.json"
        stats_file = self.data_dir / "bot_stats.json"
        assert not playback_file.exists()
        assert not stats_file.exists()

    def test_data_protection_status(self):
        """Test data protection status reporting"""
        # Create state files and backups
        self.manager.save_playback_state(
            current_surah=self.test_surah,
            current_position=self.test_position,
            current_reciter=self.test_reciter,
        )
        self.manager.save_bot_stats(total_runtime=100.0)

        # Get protection status
        status = self.manager.get_data_protection_status()
        assert status["playback_state_exists"] is True
        assert status["bot_stats_exists"] is True
        assert status["playback_backup_exists"] is True
        assert status["stats_backup_exists"] is True
        assert status["data_integrity"] is True

    def test_backup_cleanup(self):
        """Test old backup cleanup"""
        # Create old emergency backups
        old_time = datetime.now().timestamp() - (8 * 24 * 60 * 60)  # 8 days old
        for i in range(3):
            file = self.data_dir / f"emergency_playback_{i}.json"
            file.write_text("{}")
            os.utime(file, (old_time, old_time))

        # Create recent emergency backup
        new_file = self.data_dir / "emergency_playback_new.json"
        new_file.write_text("{}")

        # Clean up old backups (keep 7 days)
        cleaned = self.manager.cleanup_old_backups(keep_days=7)
        assert cleaned == 3  # 3 old files removed

        # Verify only new file remains
        emergency_files = list(self.data_dir.glob("emergency_playback_*.json"))
        assert len(emergency_files) == 1
        assert emergency_files[0] == new_file

    def test_data_validation(self):
        """Test data validation and error handling"""
        # Test invalid surah number
        success = self.manager.save_playback_state(
            current_surah=115,  # Invalid
            current_position=self.test_position,
            current_reciter=self.test_reciter,
        )
        assert success is False

        # Test invalid runtime
        success = self.manager.save_bot_stats(total_runtime=-1.0)  # Invalid
        assert success is False

        # Test invalid timestamps
        success = self.manager.save_bot_stats(
            last_startup=123,  # Invalid type
            last_shutdown=[],  # Invalid type
        )
        assert success is True  # Should succeed but skip invalid values

        # Verify defaults used for invalid values
        stats = self.manager.load_bot_stats()
        assert stats["last_startup"] is None
        assert stats["last_shutdown"] is None
