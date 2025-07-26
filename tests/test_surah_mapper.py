#!/usr/bin/env python3
# =============================================================================
# QuranBot - Surah Mapper Tests
# =============================================================================
# Comprehensive tests for Surah information management
# =============================================================================

import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

import discord
import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from utils.surah_mapper import (
    RevelationType,
    SurahInfo,
    format_now_playing,
    format_surah_embed,
    get_meccan_surahs,
    get_medinan_surahs,
    get_quran_statistics,
    get_surah_info,
    get_surah_name,
    load_surah_database,
    search_surahs,
    validate_surah_number,
)


class TestSurahMapper:
    """Test suite for Surah information management"""

    @pytest.fixture(autouse=True)
    def setup_test(self):
        """Set up test environment"""
        self.test_dir = Path("test_data")
        if not self.test_dir.exists():
            self.test_dir.mkdir(parents=True)

        # Create test database
        self.test_db = {
            1: {
                "number": 1,
                "name_arabic": "الفاتحة",
                "name_english": "The Opening",
                "name_transliteration": "Al-Fatihah",
                "emoji": "📖",
                "verses": 7,
                "revelation_type": "Meccan",
                "meaning": "The Opening",
                "description": "The first chapter of the Quran",
            },
            2: {
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
            3: {
                "number": 3,
                "name_arabic": "آل عمران",
                "name_english": "The Family of Imran",
                "name_transliteration": "Aali Imran",
                "emoji": "👨‍👩‍👧‍👦",
                "verses": 200,
                "revelation_type": "Medinan",
                "meaning": "The Family of Imran",
                "description": "Named after the family of Mary",
            },
        }

        # Write test database to file
        db_file = self.test_dir / "surahs.json"
        with db_file.open("w", encoding="utf-8") as f:
            json.dump(self.test_db, f, ensure_ascii=False, indent=2)

        yield

        # Clean up
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
        """Test loading Surah database"""
        with patch("pathlib.Path.parent", return_value=self.test_dir):
            db = load_surah_database()
            assert len(db) == 3
            assert isinstance(db[1], SurahInfo)
            assert db[1].name_transliteration == "Al-Fatihah"

    def test_surah_lookup(self):
        """Test looking up Surah by number"""
        with patch("pathlib.Path.parent", return_value=self.test_dir):
            surah = get_surah_info(1)
            assert surah is not None
            assert surah.name_transliteration == "Al-Fatihah"
            assert surah.name_arabic == "الفاتحة"

    def test_surah_name_formatting(self):
        """Test Surah name formatting"""
        with patch("pathlib.Path.parent", return_value=self.test_dir):
            name = get_surah_name(1)
            assert name == "Al-Fatihah"

    def test_surah_search(self):
        """Test searching for Surahs"""
        with patch("pathlib.Path.parent", return_value=self.test_dir):
            results = search_surahs("opening")
            assert len(results) == 1
            assert results[0].name_transliteration == "Al-Fatihah"

    def test_surah_categorization(self):
        """Test Surah categorization"""
        with patch("pathlib.Path.parent", return_value=self.test_dir):
            meccan = get_meccan_surahs()
            medinan = get_medinan_surahs()
            assert len(meccan) == 1
            assert len(medinan) == 2

    def test_quran_statistics(self):
        """Test Quran statistics"""
        with patch("pathlib.Path.parent", return_value=self.test_dir):
            stats = get_quran_statistics()
            assert stats["total_surahs"] == 3
            assert stats["total_verses"] == 493
            assert stats["meccan_surahs"] == 1
            assert stats["medinan_surahs"] == 2

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
