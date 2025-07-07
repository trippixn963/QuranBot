#!/usr/bin/env python3
# =============================================================================
# QuranBot - Audio Manager Tests
# =============================================================================
# Comprehensive tests for audio management functionality
# =============================================================================

import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from utils.audio_manager import AudioManager


class TestAudioManager:
    """Test suite for AudioManager class"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.audio_dir = Path(self.temp_dir) / "audio"
        self.audio_dir.mkdir()

        # Create test audio directory structure
        test_reciter_dir = self.audio_dir / "Test Reciter"
        test_reciter_dir.mkdir()

        # Create dummy audio files
        for i in range(1, 6):
            test_file = test_reciter_dir / f"{i:03d}.mp3"
            test_file.write_text("dummy audio content")

    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("utils.audio_manager.state_manager")
    def test_initialization(self, mock_state_manager):
        """Test AudioManager initialization"""
        mock_state_manager.load_playback_state.return_value = {
            "current_surah": 1,
            "current_position": 0.0,
            "current_reciter": "Test Reciter",
            "is_playing": False,
            "loop_enabled": False,
            "shuffle_enabled": False,
        }

        audio_manager = AudioManager(
            audio_dir=str(self.audio_dir), default_reciter="Test Reciter"
        )

        assert audio_manager.audio_dir == Path(self.audio_dir)
        assert audio_manager.current_reciter == "Test Reciter"
        assert audio_manager.current_surah == 1

    @patch("utils.audio_manager.state_manager")
    def test_scan_reciters(self, mock_state_manager):
        """Test reciter scanning functionality"""
        mock_state_manager.load_playback_state.return_value = {
            "current_surah": 1,
            "current_position": 0.0,
            "current_reciter": "Test Reciter",
            "is_playing": False,
            "loop_enabled": False,
            "shuffle_enabled": False,
        }

        audio_manager = AudioManager(
            audio_dir=str(self.audio_dir), default_reciter="Test Reciter"
        )

        assert "Test Reciter" in audio_manager.available_reciters
        assert len(audio_manager.available_reciters) >= 1

    @patch("utils.audio_manager.state_manager")
    def test_get_surah_files(self, mock_state_manager):
        """Test getting surah files for a reciter"""
        mock_state_manager.load_playback_state.return_value = {
            "current_surah": 1,
            "current_position": 0.0,
            "current_reciter": "Test Reciter",
            "is_playing": False,
            "loop_enabled": False,
            "shuffle_enabled": False,
        }

        audio_manager = AudioManager(
            audio_dir=str(self.audio_dir), default_reciter="Test Reciter"
        )

        files = audio_manager._get_surah_files("Test Reciter")
        assert len(files) == 5  # We created 5 test files
        assert all(f.suffix == ".mp3" for f in files)

    @patch("utils.audio_manager.state_manager")
    def test_change_reciter(self, mock_state_manager):
        """Test changing reciter"""
        mock_state_manager.load_playback_state.return_value = {
            "current_surah": 1,
            "current_position": 0.0,
            "current_reciter": "Test Reciter",
            "is_playing": False,
            "loop_enabled": False,
            "shuffle_enabled": False,
        }

        audio_manager = AudioManager(
            audio_dir=str(self.audio_dir), default_reciter="Test Reciter"
        )

        # Test changing to valid reciter
        result = audio_manager.change_reciter("Test Reciter")
        assert result is True
        assert audio_manager.current_reciter == "Test Reciter"

        # Test changing to invalid reciter
        result = audio_manager.change_reciter("Nonexistent Reciter")
        assert result is False

    @patch("utils.audio_manager.state_manager")
    def test_get_playback_status(self, mock_state_manager):
        """Test getting playback status"""
        mock_state_manager.load_playback_state.return_value = {
            "current_surah": 1,
            "current_position": 0.0,
            "current_reciter": "Test Reciter",
            "is_playing": False,
            "loop_enabled": False,
            "shuffle_enabled": False,
        }

        audio_manager = AudioManager(
            audio_dir=str(self.audio_dir), default_reciter="Test Reciter"
        )

        status = audio_manager.get_playback_status()

        assert isinstance(status, dict)
        assert "is_playing" in status
        assert "current_surah" in status
        assert "current_reciter" in status
        assert "available_reciters" in status

    @patch("utils.audio_manager.state_manager")
    def test_toggle_loop(self, mock_state_manager):
        """Test toggling loop mode"""
        mock_state_manager.load_playback_state.return_value = {
            "current_surah": 1,
            "current_position": 0.0,
            "current_reciter": "Test Reciter",
            "is_playing": False,
            "loop_enabled": False,
            "shuffle_enabled": False,
        }

        audio_manager = AudioManager(
            audio_dir=str(self.audio_dir), default_reciter="Test Reciter"
        )

        # Test toggling loop on
        initial_state = audio_manager.is_loop_enabled
        audio_manager.toggle_loop()
        assert audio_manager.is_loop_enabled != initial_state

    @patch("utils.audio_manager.state_manager")
    def test_toggle_shuffle(self, mock_state_manager):
        """Test toggling shuffle mode"""
        mock_state_manager.load_playback_state.return_value = {
            "current_surah": 1,
            "current_position": 0.0,
            "current_reciter": "Test Reciter",
            "is_playing": False,
            "loop_enabled": False,
            "shuffle_enabled": False,
        }

        audio_manager = AudioManager(
            audio_dir=str(self.audio_dir), default_reciter="Test Reciter"
        )

        # Test toggling shuffle on
        initial_state = audio_manager.is_shuffle_enabled
        audio_manager.toggle_shuffle()
        assert audio_manager.is_shuffle_enabled != initial_state


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
