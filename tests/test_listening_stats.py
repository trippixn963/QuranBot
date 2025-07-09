#!/usr/bin/env python3
# =============================================================================
# QuranBot - Listening Statistics Tests
# =============================================================================
# Comprehensive tests for user listening time tracking
# =============================================================================

import asyncio
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

from utils.listening_stats import (
    ActiveSession,
    ListeningStatsManager,
    UserStats,
    get_data_protection_status,
    verify_data_integrity,
)


class TestListeningStats:
    """Test suite for listening statistics functionality"""

    def setup_method(self):
        """Set up test environment"""
        # Create temporary test directories
        self.test_dir = Path("test_listening_data")
        self.data_dir = self.test_dir / "data"
        self.backup_dir = self.test_dir / "backup"
        self.temp_backup_dir = self.backup_dir / "temp"

        # Create directories
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.temp_backup_dir.mkdir(parents=True, exist_ok=True)

        # Initialize manager with test paths
        self.manager = ListeningStatsManager()
        self.manager.data_dir = self.data_dir
        self.manager.backup_dir = self.backup_dir
        self.manager.temp_backup_dir = self.temp_backup_dir

        # Test user IDs
        self.test_user_id = 123456789
        self.test_user_id_2 = 987654321

    def teardown_method(self):
        """Clean up test environment"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_user_stats_creation(self):
        """Test UserStats class functionality"""
        # Test creation with defaults
        stats = UserStats(self.test_user_id)
        assert stats.user_id == self.test_user_id
        assert stats.total_time == 0.0
        assert stats.sessions == 0
        assert stats.last_seen is not None

        # Test creation with values
        stats = UserStats(self.test_user_id, total_time=100.0, sessions=5)
        assert stats.total_time == 100.0
        assert stats.sessions == 5

        # Test dictionary conversion
        data = stats.to_dict()
        assert data["user_id"] == self.test_user_id
        assert data["total_time"] == 100.0
        assert data["sessions"] == 5
        assert "last_seen" in data

        # Test creation from dictionary
        new_stats = UserStats.from_dict(data)
        assert new_stats.user_id == stats.user_id
        assert new_stats.total_time == stats.total_time
        assert new_stats.sessions == stats.sessions
        assert new_stats.last_seen == stats.last_seen

    def test_active_session(self):
        """Test ActiveSession class functionality"""
        # Create session
        session = ActiveSession(self.test_user_id)
        assert session.user_id == self.test_user_id
        assert session.start_time is not None

        # Test duration calculation
        with patch("datetime.datetime") as mock_dt:
            # Set current time to 30 seconds after start
            mock_dt.now.return_value = session.start_time + timedelta(seconds=30)
            duration = session.get_duration()
            assert duration == pytest.approx(30.0)

        # Test dictionary conversion
        data = session.to_dict()
        assert data["user_id"] == self.test_user_id
        assert "start_time" in data

        # Test creation from dictionary
        new_session = ActiveSession.from_dict(data)
        assert new_session.user_id == session.user_id
        assert new_session.start_time == session.start_time

    def test_user_join_leave(self):
        """Test user join/leave tracking"""
        # Test join
        self.manager.user_joined_voice(self.test_user_id)
        assert self.test_user_id in self.manager.active_sessions
        assert self.test_user_id in self.manager.users

        # Wait and test leave
        with patch("datetime.datetime") as mock_dt:
            # Set current time to 60 seconds after join
            join_time = self.manager.active_sessions[self.test_user_id].start_time
            mock_dt.now.return_value = join_time + timedelta(seconds=60)

            # Test leave
            duration = self.manager.user_left_voice(self.test_user_id)
            assert duration == pytest.approx(60.0)
            assert self.test_user_id not in self.manager.active_sessions

            # Verify stats updated
            user_stats = self.manager.users[self.test_user_id]
            assert user_stats.total_time == pytest.approx(60.0)
            assert user_stats.sessions == 1

    def test_multiple_sessions(self):
        """Test handling of multiple user sessions"""
        # First session
        self.manager.user_joined_voice(self.test_user_id)
        with patch("datetime.datetime") as mock_dt:
            # 30 seconds session
            join_time = self.manager.active_sessions[self.test_user_id].start_time
            mock_dt.now.return_value = join_time + timedelta(seconds=30)
            duration = self.manager.user_left_voice(self.test_user_id)
            assert duration == pytest.approx(30.0)

        # Second session
        self.manager.user_joined_voice(self.test_user_id)
        with patch("datetime.datetime") as mock_dt:
            # 45 seconds session
            join_time = self.manager.active_sessions[self.test_user_id].start_time
            mock_dt.now.return_value = join_time + timedelta(seconds=45)
            duration = self.manager.user_left_voice(self.test_user_id)
            assert duration == pytest.approx(45.0)

        # Verify cumulative stats
        user_stats = self.manager.users[self.test_user_id]
        assert user_stats.total_time == pytest.approx(75.0)  # 30 + 45
        assert user_stats.sessions == 2

    def test_concurrent_users(self):
        """Test handling of multiple concurrent users"""
        # Both users join
        self.manager.user_joined_voice(self.test_user_id)
        self.manager.user_joined_voice(self.test_user_id_2)

        with patch("datetime.datetime") as mock_dt:
            # Set current time to 30 seconds after join
            join_time = self.manager.active_sessions[self.test_user_id].start_time
            mock_dt.now.return_value = join_time + timedelta(seconds=30)

            # First user leaves
            duration1 = self.manager.user_left_voice(self.test_user_id)
            assert duration1 == pytest.approx(30.0)

            # Second user continues for 30 more seconds
            mock_dt.now.return_value = join_time + timedelta(seconds=60)
            duration2 = self.manager.user_left_voice(self.test_user_id_2)
            assert duration2 == pytest.approx(60.0)

        # Verify individual stats
        assert self.manager.users[self.test_user_id].total_time == pytest.approx(30.0)
        assert self.manager.users[self.test_user_id_2].total_time == pytest.approx(60.0)

        # Verify total stats
        assert self.manager.total_listening_time == pytest.approx(90.0)
        assert self.manager.total_sessions == 2

    def test_data_persistence(self):
        """Test data saving and loading"""
        # Create some test data
        self.manager.user_joined_voice(self.test_user_id)
        with patch("datetime.datetime") as mock_dt:
            join_time = self.manager.active_sessions[self.test_user_id].start_time
            mock_dt.now.return_value = join_time + timedelta(seconds=30)
            self.manager.user_left_voice(self.test_user_id)

        # Save data
        self.manager.save_stats()
        assert self.manager.last_updated is not None

        # Create new manager and load data
        new_manager = ListeningStatsManager()
        new_manager.data_dir = self.data_dir
        new_manager.backup_dir = self.backup_dir
        new_manager.temp_backup_dir = self.temp_backup_dir
        new_manager.load_stats()

        # Verify data loaded correctly
        assert self.test_user_id in new_manager.users
        assert new_manager.users[self.test_user_id].total_time == pytest.approx(30.0)
        assert new_manager.users[self.test_user_id].sessions == 1
        assert new_manager.total_listening_time == pytest.approx(30.0)
        assert new_manager.total_sessions == 1

    def test_data_backup(self):
        """Test backup functionality"""
        # Create test data
        self.manager.user_joined_voice(self.test_user_id)
        with patch("datetime.datetime") as mock_dt:
            join_time = self.manager.active_sessions[self.test_user_id].start_time
            mock_dt.now.return_value = join_time + timedelta(seconds=30)
            self.manager.user_left_voice(self.test_user_id)

        # Save with backup
        self.manager.save_stats()

        # Verify backup file exists
        backup_file = self.temp_backup_dir / "listening_stats.backup"
        assert backup_file.exists()

        # Corrupt main file
        stats_file = self.data_dir / "listening_stats.json"
        stats_file.write_text("corrupted data")

        # Load from backup
        new_manager = ListeningStatsManager()
        new_manager.data_dir = self.data_dir
        new_manager.backup_dir = self.backup_dir
        new_manager.temp_backup_dir = self.temp_backup_dir
        new_manager.load_stats()

        # Verify data recovered
        assert self.test_user_id in new_manager.users
        assert new_manager.users[self.test_user_id].total_time == pytest.approx(30.0)

    def test_leaderboard(self):
        """Test leaderboard generation"""
        # Create test data for multiple users
        users_data = [
            (self.test_user_id, 100.0, 2),
            (self.test_user_id_2, 200.0, 3),
            (123, 50.0, 1),
            (456, 150.0, 2),
        ]

        for user_id, time, sessions in users_data:
            self.manager.users[user_id] = UserStats(
                user_id=user_id, total_time=time, sessions=sessions
            )

        # Get top users
        top_users = self.manager.get_top_users(limit=3)
        assert len(top_users) == 3

        # Verify order (by total time)
        assert top_users[0][0] == self.test_user_id_2  # Most time
        assert top_users[0][1] == 200.0
        assert top_users[1][0] == 456  # Second most time
        assert top_users[1][1] == 150.0
        assert top_users[2][0] == self.test_user_id  # Third most time
        assert top_users[2][1] == 100.0

    def test_time_formatting(self):
        """Test time formatting functionality"""
        # Test various durations
        assert self.manager.format_time(30) == "30s"
        assert self.manager.format_time(90) == "1m 30s"
        assert self.manager.format_time(3600) == "1h 0m"
        assert self.manager.format_time(3661) == "1h 1m"
        assert self.manager.format_time(86400) == "1d 0h"
        assert self.manager.format_time(90000) == "1d 1h"

    def test_data_integrity(self):
        """Test data integrity verification"""
        # Test with valid data
        self.manager.user_joined_voice(self.test_user_id)
        with patch("datetime.datetime") as mock_dt:
            join_time = self.manager.active_sessions[self.test_user_id].start_time
            mock_dt.now.return_value = join_time + timedelta(seconds=30)
            self.manager.user_left_voice(self.test_user_id)

        self.manager.save_stats()
        assert verify_data_integrity() is True

        # Test with corrupted data
        stats_file = self.data_dir / "listening_stats.json"
        stats_file.write_text("corrupted data")
        assert verify_data_integrity() is False

        # Test with missing file
        stats_file.unlink()
        assert verify_data_integrity() is False

    def test_protection_status(self):
        """Test data protection status reporting"""
        # Create test data and save
        self.manager.user_joined_voice(self.test_user_id)
        with patch("datetime.datetime") as mock_dt:
            join_time = self.manager.active_sessions[self.test_user_id].start_time
            mock_dt.now.return_value = join_time + timedelta(seconds=30)
            self.manager.user_left_voice(self.test_user_id)

        self.manager.save_stats()

        # Get protection status
        status = get_data_protection_status()
        assert status["main_file_exists"] is True
        assert status["backup_exists"] is True
        assert status["data_integrity"] is True
        assert status["total_protection_files"] >= 1
