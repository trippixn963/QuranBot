#!/usr/bin/env python3
# =============================================================================
# QuranBot - Daily Verses Tests
# =============================================================================
# Comprehensive tests for daily verses functionality
# =============================================================================

from datetime import datetime, timedelta
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

import pytz

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from utils.daily_verses import DailyVerseManager


class TestDailyVerseManager:
    """Test suite for DailyVerseManager class"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = Path(self.temp_dir)
        self.manager = DailyVerseManager(data_dir=self.data_dir)

        # Sample verse data
        self.sample_verse = {
            "surah": 1,
            "verse": 1,
            "text": "In the name of Allah, the Most Gracious, the Most Merciful",
            "translation": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
            "transliteration": "Bismillah ir-Rahman ir-Raheem",
        }

    def test_initialization(self):
        """Test manager initialization"""
        assert self.manager.data_dir == self.data_dir
        assert self.manager.state_file == self.data_dir / "daily_verse_state.json"
        assert self.manager.verses_file == self.data_dir / "daily_verses_pool.json"

    @patch("utils.daily_verses.datetime")
    def test_should_update_verse(self, mock_datetime):
        """Test verse update timing logic"""
        # Mock current time
        mock_now = datetime(2023, 1, 1, 12, 0, tzinfo=pytz.UTC)
        mock_datetime.now.return_value = mock_now
        mock_datetime.fromtimestamp.side_effect = lambda ts, tz: datetime.fromtimestamp(
            ts, tz
        )

        # Test when no current verse exists
        assert self.manager.should_update_verse() is True

        # Set current verse with recent timestamp
        self.manager.current_verse = {
            **self.sample_verse,
            "timestamp": mock_now.timestamp(),
        }
        assert self.manager.should_update_verse() is False

        # Test with old verse
        old_time = mock_now - timedelta(days=2)
        self.manager.current_verse["timestamp"] = old_time.timestamp()
        assert self.manager.should_update_verse() is True

    def test_add_verse(self):
        """Test adding a verse to the pool"""
        result = self.manager.add_verse(
            surah=1,
            verse=1,
            text="Test verse",
            translation="اختبار",
            transliteration="Test",
        )
        assert result is True

        # Verify verse was added
        assert len(self.manager.verse_pool) == 1
        added_verse = self.manager.verse_pool[0]
        assert added_verse["surah"] == 1
        assert added_verse["verse"] == 1
        assert added_verse["text"] == "Test verse"
        assert added_verse["translation"] == "اختبار"
        assert added_verse["transliteration"] == "Test"

    def test_get_verse_by_number(self):
        """Test getting a specific verse"""
        # Add test verse
        self.manager.add_verse(
            surah=1,
            verse=1,
            text="Test verse",
            translation="اختبار",
            transliteration="Test",
        )

        # Get verse
        verse = self.manager.get_verse_by_number(1, 1)
        assert verse is not None
        assert verse["surah"] == 1
        assert verse["verse"] == 1
        assert verse["text"] == "Test verse"

        # Test non-existent verse
        verse = self.manager.get_verse_by_number(999, 999)
        assert verse is None

    def test_get_random_verse(self):
        """Test getting a random verse"""
        # Add multiple test verses
        for i in range(1, 6):
            self.manager.add_verse(
                surah=1,
                verse=i,
                text=f"Test verse {i}",
                translation=f"اختبار {i}",
                transliteration=f"Test {i}",
            )

        # Get random verse
        verse = self.manager.get_random_verse()
        assert verse is not None
        assert 1 <= verse["verse"] <= 5
        assert verse["surah"] == 1
        assert verse["text"].startswith("Test verse")

    def test_save_and_load_state(self):
        """Test saving and loading state"""
        # Set current verse
        self.manager.current_verse = self.sample_verse.copy()

        # Save state
        result = self.manager.save_state()
        assert result is True
        assert self.manager.state_file.exists()

        # Create new manager instance
        new_manager = DailyVerseManager(data_dir=self.data_dir)

        # Load state
        result = new_manager.load_state()
        assert result is True
        assert new_manager.current_verse == self.sample_verse

    def test_save_and_load_verses(self):
        """Test saving and loading verses"""
        # Add test verses
        for i in range(1, 6):
            self.manager.add_verse(
                surah=1,
                verse=i,
                text=f"Test verse {i}",
                translation=f"اختبار {i}",
                transliteration=f"Test {i}",
            )

        # Save verses
        result = self.manager.save_verses()
        assert result is True
        assert self.manager.verses_file.exists()

        # Create new manager instance
        new_manager = DailyVerseManager(data_dir=self.data_dir)

        # Load verses
        result = new_manager.load_verses()
        assert result is True
        assert len(new_manager.verse_pool) == 5

    @patch("utils.daily_verses.datetime")
    def test_get_time_until_next_verse(self, mock_datetime):
        """Test next verse timing calculation"""
        # Mock current time
        mock_now = datetime(2023, 1, 1, 12, 0, tzinfo=pytz.UTC)
        mock_datetime.now.return_value = mock_now
        mock_datetime.fromtimestamp.side_effect = lambda ts, tz: datetime.fromtimestamp(
            ts, tz
        )

        # Set current verse time
        self.manager.current_verse = {
            **self.sample_verse,
            "timestamp": mock_now.timestamp(),
        }

        # Calculate time until next verse
        time_left = self.manager.get_time_until_next_verse()
        assert isinstance(time_left, timedelta)
        assert time_left.total_seconds() > 0

    def test_error_handling(self):
        """Test error handling"""
        # Test invalid verse numbers
        result = self.manager.add_verse(
            surah=0,  # Invalid surah number
            verse=1,
            text="Test",
            translation="Test",
            transliteration="Test",
        )
        assert result is False

        result = self.manager.add_verse(
            surah=1,
            verse=0,  # Invalid verse number
            text="Test",
            translation="Test",
            transliteration="Test",
        )
        assert result is False

        # Test missing required fields
        result = self.manager.add_verse(
            surah=1,
            verse=1,
            text="",  # Empty text
            translation="Test",
            transliteration="Test",
        )
        assert result is False
