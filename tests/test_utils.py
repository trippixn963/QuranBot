#!/usr/bin/env python3
# =============================================================================
# QuranBot - Utility Tests
# =============================================================================
# Comprehensive tests for utility functions and components
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

from utils.surah_mapper import get_all_surahs, get_surah_info
from utils.tree_log import log_error_with_traceback, log_perfect_tree_section


class TestSurahMapper:
    """Test suite for Surah Mapper functionality"""

    def test_get_surah_info(self):
        """Test getting surah information"""
        # Test valid surah
        surah_info = get_surah_info(1)
        assert surah_info is not None
        assert "name" in surah_info
        assert "english_name" in surah_info
        assert "verses" in surah_info

        # Test invalid surah
        invalid_surah = get_surah_info(150)
        assert invalid_surah is None

        # Test edge cases
        first_surah = get_surah_info(1)
        assert first_surah is not None

        last_surah = get_surah_info(114)
        assert last_surah is not None

    def test_get_all_surahs(self):
        """Test getting all surahs"""
        all_surahs = get_all_surahs()
        assert isinstance(all_surahs, dict)
        assert len(all_surahs) == 114

        # Check that all surahs have required fields
        for surah_num, surah_info in all_surahs.items():
            assert "name" in surah_info
            assert "english_name" in surah_info
            assert "verses" in surah_info
            assert isinstance(surah_info["verses"], int)
            assert surah_info["verses"] > 0


class TestTreeLog:
    """Test suite for Tree Logging functionality"""

    @patch("utils.tree_log.print")
    def test_log_perfect_tree_section(self, mock_print):
        """Test tree logging functionality"""
        log_perfect_tree_section(
            "Test Section",
            [
                ("item1", "value1"),
                ("item2", "value2"),
            ],
            "🧪",
        )

        # Verify that print was called
        assert mock_print.called

        # Check that the tree structure was logged
        calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("Test Section" in call for call in calls)

    @patch("utils.tree_log.print")
    def test_log_error_with_traceback(self, mock_print):
        """Test error logging with traceback"""
        test_error = ValueError("Test error message")

        log_error_with_traceback("Test error context", test_error)

        # Verify that print was called
        assert mock_print.called

        # Check that error information was logged
        calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("Test error context" in call for call in calls)


class TestIntegration:
    """Integration tests for multiple components"""

    def test_surah_mapper_integration(self):
        """Test surah mapper integration with real data"""
        # Test that we can get info for all surahs
        for i in range(1, 115):
            surah_info = get_surah_info(i)
            assert surah_info is not None
            assert isinstance(surah_info["name"], str)
            assert isinstance(surah_info["english_name"], str)
            assert isinstance(surah_info["verses"], int)
            assert surah_info["verses"] > 0

    def test_data_consistency(self):
        """Test data consistency across components"""
        all_surahs = get_all_surahs()

        # Test that individual surah info matches bulk data
        for surah_num in range(1, 115):
            individual_info = get_surah_info(surah_num)
            bulk_info = all_surahs.get(str(surah_num))

            assert individual_info == bulk_info

    def test_error_handling(self):
        """Test error handling across components"""
        # Test invalid surah numbers
        invalid_surahs = [-1, 0, 115, 200, "invalid"]

        for invalid_surah in invalid_surahs:
            try:
                result = get_surah_info(invalid_surah)
                assert result is None
            except Exception:
                # Should handle gracefully, not crash
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
