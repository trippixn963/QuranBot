#!/usr/bin/env python3
# =============================================================================
# QuranBot - Surah Mapper Tests
# =============================================================================
# Comprehensive tests for Surah information management
# =============================================================================

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import discord
import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from utils.surah_mapper import (
    RevelationType,
    SurahInfo,
    format_now_playing,
    format_surah_embed,
    get_all_surahs,
    get_long_surahs,
    get_meccan_surahs,
    get_medinan_surahs,
    get_quran_statistics,
    get_random_surah,
    get_short_surahs,
    get_surah_display,
    get_surah_info,
    get_surah_name,
    load_surah_database,
    search_surahs,
    validate_surah_number,
)


class TestSurahMapper:
    """Test suite for Surah mapping functionality"""

    def setup_method(self):
        """Set up test environment"""
        # Create test data directory
        self.test_dir = Path("test_surah_data")
        self.test_dir.mkdir(exist_ok=True)

        # Create test database
        self.test_database = {
            "1": {
                "number": 1,
                "name_arabic": "الفاتحة",
                "name_english": "The Opening",
                "name_transliteration": "Al-Fatihah",
                "emoji": "🕌",
                "verses": 7,
                "revelation_type": "Meccan",
                "meaning": "The Opening",
                "description": "The first chapter of the Quran",
            },
            "2": {
                "number": 2,
                "name_arabic": "البقرة",
                "name_english": "The Cow",
                "name_transliteration": "Al-Baqarah",
                "emoji": "🐄",
                "verses": 286,
                "revelation_type": "Medinan",
                "meaning": "The Cow",
                "description": "The longest chapter of the Quran",
            },
            "114": {
                "number": 114,
                "name_arabic": "الناس",
                "name_english": "Mankind",
                "name_transliteration": "An-Nas",
                "emoji": "👥",
                "verses": 6,
                "revelation_type": "Meccan",
                "meaning": "Mankind",
                "description": "The last chapter of the Quran",
            },
        }

        # Write test database to file
        test_json = self.test_dir / "surahs.json"
        with open(test_json, "w", encoding="utf-8") as f:
            json.dump(self.test_database, f, ensure_ascii=False, indent=2)

    def teardown_method(self):
        """Clean up test environment"""
        if self.test_dir.exists():
            import shutil

            shutil.rmtree(self.test_dir)

    def test_surah_info_class(self):
        """Test SurahInfo dataclass functionality"""
        # Create test instance
        surah = SurahInfo(
            number=1,
            name_arabic="الفاتحة",
            name_english="The Opening",
            name_transliteration="Al-Fatihah",
            emoji="🕌",
            verses=7,
            revelation_type=RevelationType.MECCAN,
            meaning="The Opening",
            description="The first chapter",
        )

        # Test attributes
        assert surah.number == 1
        assert surah.name_arabic == "الفاتحة"
        assert surah.name_english == "The Opening"
        assert surah.name_transliteration == "Al-Fatihah"
        assert surah.emoji == "🕌"
        assert surah.verses == 7
        assert surah.revelation_type == RevelationType.MECCAN
        assert surah.meaning == "The Opening"
        assert surah.description == "The first chapter"

        # Test subscript access
        assert surah["name"] == "Al-Fatihah"
        assert surah["name_arabic"] == "الفاتحة"
        assert surah["revelation_type"] == "Meccan"

        # Test iteration
        keys = list(surah)
        assert "name" in keys
        assert "verses" in keys
        assert "revelation_type" in keys

        # Test equality
        surah2 = SurahInfo(
            number=1,
            name_arabic="الفاتحة",
            name_english="The Opening",
            name_transliteration="Al-Fatihah",
            emoji="🕌",
            verses=7,
            revelation_type=RevelationType.MECCAN,
            meaning="The Opening",
            description="The first chapter",
        )
        assert surah == surah2

    def test_database_loading(self):
        """Test Surah database loading"""
        with patch("pathlib.Path.parent", return_value=self.test_dir):
            database = load_surah_database()
            assert len(database) == 3
            assert 1 in database
            assert 2 in database
            assert 114 in database

            # Test data integrity
            surah1 = database[1]
            assert surah1.name_transliteration == "Al-Fatihah"
            assert surah1.verses == 7
            assert surah1.revelation_type == RevelationType.MECCAN

    def test_surah_lookup(self):
        """Test Surah information lookup"""
        with patch("pathlib.Path.parent", return_value=self.test_dir):
            # Test valid lookup
            surah = get_surah_info(1)
            assert surah is not None
            assert surah.name_transliteration == "Al-Fatihah"

            # Test invalid lookup
            assert get_surah_info(115) is None
            assert get_surah_info(0) is None

    def test_surah_name_formatting(self):
        """Test Surah name formatting"""
        with patch("pathlib.Path.parent", return_value=self.test_dir):
            # Test name retrieval
            assert get_surah_name(1) == "Al-Fatihah"
            assert get_surah_name(2) == "Al-Baqarah"

            # Test display formatting
            assert get_surah_display(1) == "1. Al-Fatihah"
            assert get_surah_display(2) == "2. Al-Baqarah"

            # Test invalid numbers
            assert get_surah_name(115) == "Surah 115"
            assert get_surah_display(0) == "Surah 0"

    def test_random_surah(self):
        """Test random Surah selection"""
        with patch("pathlib.Path.parent", return_value=self.test_dir):
            # Test multiple random selections
            for _ in range(10):
                surah = get_random_surah()
                assert surah is not None
                assert 1 <= surah.number <= 114
                assert isinstance(surah, SurahInfo)

    def test_surah_search(self):
        """Test Surah search functionality"""
        with patch("pathlib.Path.parent", return_value=self.test_dir):
            # Test number search
            results = search_surahs("1")
            assert len(results) == 1
            assert results[0].name_transliteration == "Al-Fatihah"

            # Test name search
            results = search_surahs("cow")
            assert len(results) == 1
            assert results[0].name_transliteration == "Al-Baqarah"

            # Test Arabic search
            results = search_surahs("البقرة")
            assert len(results) == 1
            assert results[0].name_english == "The Cow"

            # Test no results
            assert len(search_surahs("xyz")) == 0

    def test_surah_categorization(self):
        """Test Surah categorization functions"""
        with patch("pathlib.Path.parent", return_value=self.test_dir):
            # Test Meccan/Medinan filtering
            meccan = get_meccan_surahs()
            assert len(meccan) == 2
            assert all(s.revelation_type == RevelationType.MECCAN for s in meccan)

            medinan = get_medinan_surahs()
            assert len(medinan) == 1
            assert all(s.revelation_type == RevelationType.MEDINAN for s in medinan)

            # Test verse count filtering
            short = get_short_surahs(max_verses=10)
            assert len(short) == 2
            assert all(s.verses <= 10 for s in short)

            long = get_long_surahs(min_verses=100)
            assert len(long) == 1
            assert all(s.verses >= 100 for s in long)

    def test_quran_statistics(self):
        """Test Quran statistics generation"""
        with patch("pathlib.Path.parent", return_value=self.test_dir):
            stats = get_quran_statistics()
            assert stats["total_surahs"] == 3
            assert stats["meccan_surahs"] == 2
            assert stats["medinan_surahs"] == 1
            assert stats["total_verses"] == 299  # 7 + 286 + 6
            assert stats["shortest_surah"] == 6  # An-Nas
            assert stats["longest_surah"] == 286  # Al-Baqarah

    def test_discord_formatting(self):
        """Test Discord message formatting"""
        with patch("pathlib.Path.parent", return_value=self.test_dir):
            surah = get_surah_info(1)
            assert surah is not None

            # Test now playing format
            now_playing = format_now_playing(surah, "Test Reciter")
            assert "Now Playing" in now_playing
            assert "Al-Fatihah" in now_playing
            assert "Test Reciter" in now_playing

            # Test embed format
            embed = format_surah_embed(surah)
            assert isinstance(embed, discord.Embed)
            assert embed.title == "🕌 Al-Fatihah"
            assert "The Opening" in embed.description

            # Test error cases
            assert "Error" in format_now_playing(None)
            error_embed = format_surah_embed(None)
            assert error_embed is not None
            assert error_embed.title == "❌ Error"

    def test_validation(self):
        """Test Surah number validation"""
        # Test valid numbers
        assert validate_surah_number(1) is True
        assert validate_surah_number(114) is True

        # Test invalid numbers
        assert validate_surah_number(0) is False
        assert validate_surah_number(115) is False
        assert validate_surah_number(-1) is False

    def test_error_handling(self):
        """Test error handling in various scenarios"""
        with patch("pathlib.Path.parent", return_value=self.test_dir):
            # Test missing file
            self.test_dir.joinpath("surahs.json").unlink()
            database = load_surah_database()
            assert database == {}

            # Test corrupted JSON
            with open(self.test_dir / "surahs.json", "w") as f:
                f.write("invalid json")
            database = load_surah_database()
            assert database == {}

            # Test invalid data structure
            with open(self.test_dir / "surahs.json", "w") as f:
                json.dump(["invalid", "structure"], f)
            database = load_surah_database()
            assert database == {}
