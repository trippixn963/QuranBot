#!/usr/bin/env python3
# =============================================================================
# QuranBot - Rich Presence Tests
# =============================================================================
# Comprehensive tests for Discord rich presence functionality
# =============================================================================

from datetime import datetime, timedelta
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytz

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from utils.rich_presence import RichPresenceManager


class TestRichPresenceManager:
    """Test suite for RichPresenceManager class"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = Path(self.temp_dir)
        self.client = MagicMock()
        self.manager = RichPresenceManager(client=self.client, data_dir=self.data_dir)

    def test_initialization(self):
        """Test manager initialization"""
        assert self.manager.client == self.client
        assert self.manager.data_dir == self.data_dir
        assert self.manager.state_file == self.data_dir / "rich_presence_state.json"
        assert self.manager.is_enabled is True

    @patch("utils.rich_presence.datetime")
    def test_update_presence(self, mock_datetime):
        """Test updating rich presence"""
        # Mock current time
        mock_now = datetime(2023, 1, 1, 12, 0, tzinfo=pytz.UTC)
        mock_datetime.now.return_value = mock_now
        mock_datetime.fromtimestamp.side_effect = lambda ts, tz: datetime.fromtimestamp(
            ts, tz
        )

        # Test basic presence update
        result = self.manager.update_presence(
            status="Listening to Surah Al-Fatiha",
            details="Verse 1 of 7",
            state="Recited by Mishary Rashid Alafasy",
        )
        assert result is True
        self.client.change_presence.assert_called_once()

        # Test with activity type
        result = self.manager.update_presence(
            status="In a voice channel",
            details="Reading Quran",
            state="Join me!",
            activity_type="listening",
        )
        assert result is True

        # Test with start time
        result = self.manager.update_presence(
            status="Started listening",
            details="Surah Al-Baqarah",
            state="Verse 1 of 286",
            start_time=mock_now,
        )
        assert result is True

    def test_toggle_presence(self):
        """Test toggling rich presence"""
        # Test disabling
        assert self.manager.is_enabled is True
        result = self.manager.toggle_presence()
        assert result is True
        assert self.manager.is_enabled is False

        # Test enabling
        result = self.manager.toggle_presence()
        assert result is True
        assert self.manager.is_enabled is True

    def test_save_and_load_state(self):
        """Test saving and loading state"""
        # Set initial state
        self.manager.is_enabled = False
        self.manager.current_status = "Test status"
        self.manager.current_details = "Test details"
        self.manager.current_state = "Test state"

        # Save state
        result = self.manager.save_state()
        assert result is True
        assert self.manager.state_file.exists()

        # Create new manager instance
        new_manager = RichPresenceManager(client=self.client, data_dir=self.data_dir)

        # Load state
        result = new_manager.load_state()
        assert result is True
        assert new_manager.is_enabled is False
        assert new_manager.current_status == "Test status"
        assert new_manager.current_details == "Test details"
        assert new_manager.current_state == "Test state"

    def test_clear_presence(self):
        """Test clearing rich presence"""
        # Set some presence data
        self.manager.update_presence(
            status="Test status",
            details="Test details",
            state="Test state",
        )

        # Clear presence
        result = self.manager.clear_presence()
        assert result is True
        self.client.change_presence.assert_called_with(activity=None)

    def test_error_handling(self):
        """Test error handling"""
        # Test with invalid activity type
        result = self.manager.update_presence(
            status="Test",
            details="Test",
            state="Test",
            activity_type="invalid",
        )
        assert result is False

        # Test with client error
        self.client.change_presence.side_effect = Exception("Test error")
        result = self.manager.update_presence(
            status="Test",
            details="Test",
            state="Test",
        )
        assert result is False

    @patch("utils.rich_presence.datetime")
    def test_get_elapsed_time(self, mock_datetime):
        """Test elapsed time calculation"""
        # Mock current time
        mock_now = datetime(2023, 1, 1, 12, 0, tzinfo=pytz.UTC)
        mock_datetime.now.return_value = mock_now
        mock_datetime.fromtimestamp.side_effect = lambda ts, tz: datetime.fromtimestamp(
            ts, tz
        )

        # Set start time
        start_time = mock_now - timedelta(minutes=30)
        self.manager.start_time = start_time

        # Get elapsed time
        elapsed = self.manager.get_elapsed_time()
        assert isinstance(elapsed, timedelta)
        assert elapsed.total_seconds() == 1800  # 30 minutes

    def test_format_presence_text(self):
        """Test presence text formatting"""
        # Test basic formatting
        text = self.manager.format_presence_text(
            "Listening to {surah}",
            surah="Al-Fatiha",
        )
        assert text == "Listening to Al-Fatiha"

        # Test with multiple placeholders
        text = self.manager.format_presence_text(
            "{reciter} - {surah} ({verse}/{total})",
            reciter="Mishary Rashid Alafasy",
            surah="Al-Baqarah",
            verse="1",
            total="286",
        )
        assert text == "Mishary Rashid Alafasy - Al-Baqarah (1/286)"

        # Test with missing placeholder
        text = self.manager.format_presence_text(
            "{reciter} - {surah}",
            reciter="Mishary Rashid Alafasy",
        )
        assert "ERROR" in text

    def test_update_presence_with_template(self):
        """Test updating presence with template"""
        # Test with valid template
        result = self.manager.update_presence_with_template(
            "listening",
            {
                "reciter": "Mishary Rashid Alafasy",
                "surah": "Al-Fatiha",
                "verse": "1",
                "total": "7",
            },
        )
        assert result is True
        self.client.change_presence.assert_called_once()

        # Test with invalid template
        result = self.manager.update_presence_with_template(
            "invalid_template",
            {"test": "data"},
        )
        assert result is False
