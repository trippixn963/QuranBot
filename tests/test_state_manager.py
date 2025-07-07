#!/usr/bin/env python3
# =============================================================================
# QuranBot - State Manager Tests
# =============================================================================
# Comprehensive tests for state management functionality
# =============================================================================

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from utils.state_manager import StateManager


class TestStateManager:
    """Test suite for StateManager class"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.state_manager = StateManager(
            data_dir=self.temp_dir,
            default_reciter="Test Reciter",
            default_shuffle=False,
            default_loop=False,
        )

    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initialization(self):
        """Test StateManager initialization"""
        assert self.state_manager.data_dir == Path(self.temp_dir)
        assert self.state_manager.backup_interval == 300
        assert (
            self.state_manager.default_playback_state["current_reciter"]
            == "Test Reciter"
        )

    def test_save_playback_state(self):
        """Test saving playback state"""
        result = self.state_manager.save_playback_state(
            current_surah=5,
            current_position=120.5,
            current_reciter="Test Reciter",
            total_duration=3600.0,
            is_playing=True,
            loop_enabled=False,
            shuffle_enabled=False,
        )

        assert result is True
        assert self.state_manager.playback_state_file.exists()

        # Verify saved data
        with open(self.state_manager.playback_state_file, "r") as f:
            data = json.load(f)

        assert data["current_surah"] == 5
        assert data["current_position"] == 120.5
        assert data["current_reciter"] == "Test Reciter"
        assert data["is_playing"] is True

    def test_load_playback_state(self):
        """Test loading playback state"""
        # First save some state
        self.state_manager.save_playback_state(
            current_surah=10, current_position=200.0, current_reciter="Test Reciter 2"
        )

        # Then load it
        state = self.state_manager.load_playback_state()

        assert state["current_surah"] == 10
        assert state["current_position"] == 200.0
        assert state["current_reciter"] == "Test Reciter 2"

    def test_load_default_state(self):
        """Test loading default state when no file exists"""
        state = self.state_manager.load_playback_state()

        assert state["current_surah"] == 1
        assert state["current_position"] == 0.0
        assert state["current_reciter"] == "Test Reciter"

    def test_invalid_surah_number(self):
        """Test handling invalid surah numbers"""
        # Test surah number too high
        result = self.state_manager.save_playback_state(
            current_surah=150, current_position=0.0, current_reciter="Test Reciter"
        )
        assert result is False

        # Test surah number too low
        result = self.state_manager.save_playback_state(
            current_surah=0, current_position=0.0, current_reciter="Test Reciter"
        )
        assert result is False

    def test_backup_creation(self):
        """Test backup file creation"""
        # Save initial state
        self.state_manager.save_playback_state(
            current_surah=1, current_position=0.0, current_reciter="Test Reciter"
        )

        # Save different state to trigger backup
        self.state_manager.save_playback_state(
            current_surah=2, current_position=100.0, current_reciter="Test Reciter"
        )

        backup_file = self.state_manager.playback_state_file.with_suffix(".json.backup")
        assert backup_file.exists()

    def test_data_integrity_verification(self):
        """Test data integrity verification"""
        # Save valid state
        self.state_manager.save_playback_state(
            current_surah=1, current_position=0.0, current_reciter="Test Reciter"
        )

        # Verify integrity
        is_valid = self.state_manager.verify_data_integrity()
        assert is_valid is True

    def test_backup_state(self):
        """Test manual backup creation"""
        # Save some state first
        self.state_manager.save_playback_state(
            current_surah=3, current_position=50.0, current_reciter="Test Reciter"
        )

        # Create backup
        result = self.state_manager.backup_state("test_backup")
        assert result is True

        # Check backup directory exists
        backup_dir = self.state_manager.data_dir / "backups"
        assert backup_dir.exists()

    def test_clear_state(self):
        """Test clearing all state"""
        # Save some state first
        self.state_manager.save_playback_state(
            current_surah=5, current_position=100.0, current_reciter="Test Reciter"
        )

        # Clear state
        result = self.state_manager.clear_state()
        assert result is True

        # Verify state is cleared
        state = self.state_manager.load_playback_state()
        assert state["current_surah"] == 1
        assert state["current_position"] == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
