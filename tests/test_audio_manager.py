#!/usr/bin/env python3
# =============================================================================
# QuranBot - Audio Manager Tests
# =============================================================================
# Comprehensive tests for audio playback functionality
# =============================================================================

import asyncio
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from utils.audio_manager import AudioManager


@pytest.mark.asyncio
class TestAudioManager:
    """Test suite for AudioManager class"""

    @pytest.fixture(autouse=True)
    async def setup_test(self):
        """Set up test environment"""
        # Create test directories
        self.temp_dir = tempfile.mkdtemp()
        self.audio_dir = Path(self.temp_dir) / "audio"
        self.audio_dir.mkdir(parents=True)

        # Create test reciter directories and files
        self.create_test_files()

        # Mock bot
        self.mock_bot = MagicMock()
        self.mock_bot.loop = asyncio.get_event_loop()

        # Mock state manager
        self.mock_state_manager = MagicMock()
        self.mock_state_manager.load_playback_state.return_value = {
            "current_surah": 1,
            "current_position": 0.0,
            "current_reciter": "Test Reciter",
            "is_playing": False,
            "loop_enabled": False,
            "shuffle_enabled": False,
        }

        # Mock voice client
        self.mock_voice_client = AsyncMock(spec=discord.VoiceClient)
        self.mock_voice_client.is_connected.return_value = True
        self.mock_voice_client.is_playing.return_value = False
        self.mock_voice_client.is_paused.return_value = False

        # Mock rich presence
        self.mock_rich_presence = AsyncMock()
        self.mock_rich_presence.get_current_track_info.return_value = {
            "current_time": 30.0,
            "duration": 300.0,
        }

        # Create audio manager instance with new constructor signature
        self.manager = AudioManager(
            bot=self.mock_bot,
            ffmpeg_path="/usr/local/bin/ffmpeg",  # Use system FFmpeg for tests
            audio_base_folder=str(self.audio_dir),
            default_reciter="Test Reciter",
            default_shuffle=False,
            default_loop=False,
        )
        self.manager.voice_client = self.mock_voice_client
        self.manager.rich_presence = self.mock_rich_presence

        yield

        # Clean up
        shutil.rmtree(self.temp_dir)

    def create_test_files(self):
        """Create test audio files"""
        reciter_dir = self.audio_dir / "Test Reciter"
        reciter_dir.mkdir(parents=True)

        # Create test MP3 files
        for i in range(1, 6):
            file_path = reciter_dir / f"{i:03d}.mp3"
            file_path.touch()

        # Create another reciter directory
        other_reciter_dir = self.audio_dir / "Other Reciter"
        other_reciter_dir.mkdir(parents=True)
        for i in range(1, 4):
            file_path = other_reciter_dir / f"{i:03d}.mp3"
            file_path.touch()

    async def test_initialization(self):
        """Test manager initialization"""
        assert self.manager.audio_base_folder == str(self.audio_dir)
        assert self.manager.current_reciter == "Test Reciter"
        assert self.manager.current_surah == 1
        assert self.manager.current_position == 0.0
        assert self.manager.is_playing is False
        assert self.manager.loop_enabled is False
        assert self.manager.shuffle_enabled is False
        assert len(self.manager.available_reciters) == 2

    async def test_get_surah_files(self):
        """Test getting surah files for a reciter"""
        files = self.manager._get_surah_files("Test Reciter")
        assert len(files) == 5
        assert all(f.endswith(".mp3") for f in files)
        assert all(Path(f).stem.isdigit() for f in files)

        # Test non-existent reciter
        files = self.manager._get_surah_files("Non-existent")
        assert len(files) == 0

    async def test_change_reciter(self):
        """Test changing reciter"""
        # Test valid reciter
        result = self.manager.change_reciter("Other Reciter")
        assert result is True
        assert self.manager.current_reciter == "Other Reciter"

        # Test invalid reciter
        result = self.manager.change_reciter("Non-existent")
        assert result is False
        assert self.manager.current_reciter == "Other Reciter"

    async def test_get_available_reciters(self):
        """Test getting available reciters"""
        reciters = self.manager.available_reciters
        assert len(reciters) == 2
        assert "Test Reciter" in reciters
        assert "Other Reciter" in reciters

    async def test_get_current_surah_file(self):
        """Test getting current surah file"""
        file = self.manager.get_current_surah_file()
        assert file is not None
        assert file.endswith("001.mp3")

        # Test invalid surah
        self.manager.current_surah = 999
        file = self.manager.get_current_surah_file()
        assert file is None

    async def test_get_surah_file(self):
        """Test getting specific surah file"""
        file = self.manager.get_surah_file(2)
        assert file is not None
        assert file.endswith("002.mp3")

        # Test invalid surah
        file = self.manager.get_surah_file(999)
        assert file is None

    async def test_get_surah_count(self):
        """Test getting surah count for reciter"""
        count = self.manager.get_surah_count("Test Reciter")
        assert count == 5

        count = self.manager.get_surah_count("Other Reciter")
        assert count == 3

        count = self.manager.get_surah_count("Non-existent")
        assert count == 0

    async def test_toggle_loop(self):
        """Test toggling loop mode"""
        assert self.manager.loop_enabled is False
        self.manager.toggle_loop()
        assert self.manager.loop_enabled is True
        self.manager.toggle_loop()
        assert self.manager.loop_enabled is False

    async def test_toggle_shuffle(self):
        """Test toggling shuffle mode"""
        assert self.manager.shuffle_enabled is False
        self.manager.toggle_shuffle()
        assert self.manager.shuffle_enabled is True
        self.manager.toggle_shuffle()
        assert self.manager.shuffle_enabled is False

    async def test_next_surah(self):
        """Test moving to next surah"""
        assert self.manager.current_surah == 1
        self.manager.next_surah()
        assert self.manager.current_surah == 2

        # Test loop behavior
        self.manager.current_surah = 5
        self.manager.next_surah()
        assert self.manager.current_surah == 1  # Should wrap around

    async def test_previous_surah(self):
        """Test moving to previous surah"""
        self.manager.current_surah = 3
        self.manager.previous_surah()
        assert self.manager.current_surah == 2

        # Test loop behavior
        self.manager.current_surah = 1
        self.manager.previous_surah()
        assert self.manager.current_surah == 5  # Should wrap around

    async def test_jump_to_surah(self):
        """Test jumping to specific surah"""
        result = self.manager.jump_to_surah(3)
        assert result is True
        assert self.manager.current_surah == 3

        # Test invalid surah
        result = self.manager.jump_to_surah(999)
        assert result is False
        assert self.manager.current_surah == 3  # Should not change

    async def test_get_playback_state(self):
        """Test getting playback state"""
        state = self.manager.get_playback_status()
        assert isinstance(state, dict)
        assert state["current_surah"] == 1
        assert state["current_reciter"] == "Test Reciter"
        assert state["is_playing"] is False
        assert state["is_loop_enabled"] is False
        assert state["is_shuffle_enabled"] is False
        assert state["current_time"] == 30.0
        assert state["total_time"] == 300.0

    @pytest.mark.asyncio
    async def test_start_playback(self):
        """Test starting playback"""
        # Test normal start
        await self.manager.start_playback(resume_position=False)
        assert self.manager.is_playing is True
        self.mock_voice_client.play.assert_called_once()
        self.mock_rich_presence.start_track.assert_called_once()

        # Test start with resume
        self.mock_voice_client.play.reset_mock()
        self.mock_rich_presence.start_track.reset_mock()
        self.manager.current_position = 30.0
        await self.manager.start_playback(resume_position=True)
        assert self.manager.is_playing is True
        self.mock_voice_client.play.assert_called_once()
        self.mock_rich_presence.start_track.assert_called_once()
        self.mock_rich_presence.seek_to_position.assert_called_once_with(30.0)

    @pytest.mark.asyncio
    async def test_stop_playback(self):
        """Test stopping playback"""
        # Start playback first
        await self.manager.start_playback()
        assert self.manager.is_playing is True

        # Test stop
        await self.manager.stop_playback()
        assert self.manager.is_playing is False
        self.mock_voice_client.stop.assert_called_once()
        self.mock_rich_presence.stop_track.assert_called_once()

    @pytest.mark.asyncio
    async def test_pause_resume_playback(self):
        """Test pausing and resuming playback"""
        # Start playback
        await self.manager.start_playback()
        assert self.manager.is_playing is True

        # Test pause
        await self.manager.pause_playback()
        assert self.manager.is_paused is True
        self.mock_voice_client.pause.assert_called_once()

        # Test resume
        await self.manager.resume_playback()
        assert self.manager.is_paused is False
        self.mock_voice_client.resume.assert_called_once()

    @pytest.mark.asyncio
    async def test_skip_navigation(self):
        """Test skip to next/previous"""
        # Test skip to next
        await self.manager.skip_to_next()
        assert self.manager.current_surah == 2
        self.mock_voice_client.stop.assert_called_once()
        self.mock_voice_client.play.assert_called_once()

        # Reset mocks
        self.mock_voice_client.stop.reset_mock()
        self.mock_voice_client.play.reset_mock()

        # Test skip to previous
        await self.manager.skip_to_previous()
        assert self.manager.current_surah == 1
        self.mock_voice_client.stop.assert_called_once()
        self.mock_voice_client.play.assert_called_once()

    @pytest.mark.asyncio
    async def test_reciter_switch(self):
        """Test switching reciters"""
        # Start with Test Reciter
        assert self.manager.current_reciter == "Test Reciter"
        await self.manager.start_playback()

        # Switch to Other Reciter
        await self.manager.switch_reciter("Other Reciter")
        assert self.manager.current_reciter == "Other Reciter"
        self.mock_voice_client.stop.assert_called_once()
        self.mock_voice_client.play.call_count == 2  # Stop old + start new

        # Test invalid reciter
        await self.manager.switch_reciter("Non-existent")
        assert self.manager.current_reciter == "Other Reciter"  # Should not change

    def test_error_handling(self):
        """Test error handling for various scenarios"""
        # Test missing audio directory
        shutil.rmtree(self.temp_dir)
        self.manager._scan_reciters()
        assert len(self.manager.available_reciters) == 0

        # Test corrupted state load
        self.mock_state_manager.load_playback_state.side_effect = Exception("Corrupt")
        self.manager._load_initial_state()
        assert self.manager.current_surah == 1  # Should use defaults
        assert self.manager.current_position == 0.0

        # Test voice client errors
        self.mock_voice_client.play.side_effect = Exception("Voice error")
        with pytest.raises(Exception):
            self.manager.voice_client.play(None)

    @pytest.mark.asyncio
    async def test_position_saving(self):
        """Test position saving functionality"""
        # Start playback to trigger position saving
        await self.manager.start_playback()
        assert self.manager.position_save_task is not None

        # Wait for a save cycle
        await asyncio.sleep(6)

        # Verify state was saved
        self.mock_state_manager.save_playback_state.assert_called_with(
            current_surah=1,
            current_position=30.0,
            current_reciter="Test Reciter",
            total_duration=300.0,
            is_playing=True,
            loop_enabled=False,
            shuffle_enabled=False,
        )

        # Stop playback
        await self.manager.stop_playback()
        assert self.manager.position_save_task.cancelled()

    @pytest.mark.asyncio
    async def test_control_panel_integration(self):
        """Test control panel integration"""
        # Mock control panel
        mock_control_panel = AsyncMock()
        mock_control_panel.update_panel = AsyncMock()
        mock_control_panel.loop_enabled = False
        mock_control_panel.shuffle_enabled = False

        # Set control panel
        self.manager.set_control_panel(mock_control_panel)

        # Test button state sync
        self.manager.toggle_loop()
        assert mock_control_panel.loop_enabled is True

        self.manager.toggle_shuffle()
        assert mock_control_panel.shuffle_enabled is True

        # Test panel updates on playback changes
        await self.manager.start_playback()
        mock_control_panel.update_panel.assert_called_once()

        mock_control_panel.update_panel.reset_mock()
        await self.manager.pause_playback()
        mock_control_panel.update_panel.assert_called_once()

        mock_control_panel.update_panel.reset_mock()
        await self.manager.stop_playback()
        mock_control_panel.update_panel.assert_called_once()

    @pytest.mark.asyncio
    async def test_playback_loop_functionality(self):
        """Test playback loop functionality"""
        # Enable loop mode
        self.manager.toggle_loop()
        assert self.manager.loop_enabled is True

        # Start playback
        await self.manager.start_playback()
        assert self.manager.is_playing is True

        # Simulate playback completion
        self.mock_voice_client.play.reset_mock()
        await self.manager._on_playback_complete()

        # Should restart same surah
        assert self.manager.current_surah == 1
        self.mock_voice_client.play.assert_called_once()

        # Disable loop and test normal progression
        self.manager.toggle_loop()
        assert self.manager.loop_enabled is False

        self.mock_voice_client.play.reset_mock()
        await self.manager._on_playback_complete()

        # Should move to next surah
        assert self.manager.current_surah == 2
        self.mock_voice_client.play.assert_called_once()

    @pytest.mark.asyncio
    async def test_shuffle_functionality(self):
        """Test shuffle functionality"""
        # Enable shuffle mode
        self.manager.toggle_shuffle()
        assert self.manager.shuffle_enabled is True

        # Track surah order
        initial_surah = self.manager.current_surah
        visited_surahs = {initial_surah}

        # Simulate multiple playback completions
        for _ in range(5):
            await self.manager._on_playback_complete()
            current_surah = self.manager.current_surah
            assert (
                current_surah not in visited_surahs
            )  # Should not repeat until all played
            visited_surahs.add(current_surah)

        # Verify we visited different surahs
        assert len(visited_surahs) == 6  # Initial + 5 shuffled

    @pytest.mark.asyncio
    async def test_rich_presence_integration(self):
        """Test rich presence integration and templates"""
        # Start playback to trigger rich presence
        await self.manager.start_playback()

        # Verify rich presence was updated
        self.mock_rich_presence.start_track.assert_called_once()
        args = self.mock_rich_presence.start_track.call_args[1]

        # Check template values
        assert "Surah 1" in args.get("title", "")
        assert "Test Reciter" in args.get("artist", "")
        assert args.get("duration") == 300.0

        # Test pause/resume updates
        self.mock_rich_presence.pause_track.reset_mock()
        await self.manager.pause_playback()
        self.mock_rich_presence.pause_track.assert_called_once()

        self.mock_rich_presence.resume_track.reset_mock()
        await self.manager.resume_playback()
        self.mock_rich_presence.resume_track.assert_called_once()

        # Test surah change updates
        self.mock_rich_presence.start_track.reset_mock()
        await self.manager.jump_to_surah(2)
        self.mock_rich_presence.start_track.assert_called_once()
        args = self.mock_rich_presence.start_track.call_args[1]
        assert "Surah 2" in args.get("title", "")

    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test handling of concurrent operations"""
        # Start playback
        await self.manager.start_playback()
        assert self.manager.is_playing is True

        # Simulate concurrent operations
        tasks = [
            self.manager.pause_playback(),
            self.manager.resume_playback(),
            self.manager.skip_to_next(),
            self.manager.skip_to_previous(),
        ]

        # Run operations concurrently
        await asyncio.gather(*tasks)

        # Verify final state is consistent
        assert self.manager.is_playing in [True, False]  # Should be in a valid state
        assert 1 <= self.manager.current_surah <= 5  # Should be within valid range

        # Test rapid surah changes
        rapid_changes = [self.manager.jump_to_surah(i) for i in range(1, 6)]
        await asyncio.gather(*rapid_changes)

        # Verify we ended up at a valid surah
        assert 1 <= self.manager.current_surah <= 5

    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """Test error recovery scenarios"""
        # Test voice client connection loss
        self.mock_voice_client.is_connected.return_value = False

        # Should handle gracefully
        await self.manager.start_playback()
        assert self.manager.is_playing is False

        # Restore connection and retry
        self.mock_voice_client.is_connected.return_value = True
        await self.manager.start_playback()
        assert self.manager.is_playing is True

        # Test playback error recovery
        self.mock_voice_client.play.side_effect = Exception("Playback error")
        await self.manager.start_playback()
        assert self.manager.is_playing is False  # Should handle error gracefully

        # Clear error and retry
        self.mock_voice_client.play.side_effect = None
        await self.manager.start_playback()
        assert self.manager.is_playing is True

        # Test state corruption recovery
        self.manager.current_surah = 999  # Invalid state
        await self.manager.start_playback()
        assert self.manager.current_surah == 1  # Should reset to valid state

    @pytest.mark.asyncio
    async def test_cleanup_and_shutdown(self):
        """Test cleanup and shutdown procedures"""
        # Start various background tasks
        await self.manager.start_playback()
        assert self.manager.position_save_task is not None
        assert self.manager.is_playing is True

        # Simulate shutdown
        await self.manager.cleanup()

        # Verify everything is cleaned up
        assert self.manager.position_save_task.cancelled()
        assert self.manager.is_playing is False
        assert self.manager.voice_client is None

        # Verify state was saved
        self.mock_state_manager.save_playback_state.assert_called()

    @pytest.mark.asyncio
    async def test_resource_management(self):
        """Test resource management and cleanup"""
        # Start playback with resources
        await self.manager.start_playback()

        # Simulate resource intensive operations
        tasks = []
        for i in range(1, 6):
            tasks.append(self.manager.jump_to_surah(i))
            tasks.append(asyncio.sleep(0.1))  # Simulate processing time

        await asyncio.gather(*tasks)

        # Verify resource cleanup
        await self.manager.stop_playback()
        assert self.manager.voice_client is not None  # Should maintain voice connection
        assert not self.manager.is_playing  # But stop playback

        # Test resource cleanup on errors
        self.mock_voice_client.play.side_effect = Exception("Resource error")
        await self.manager.start_playback()
        assert not self.manager.is_playing  # Should cleanup on error

    @pytest.mark.asyncio
    async def test_state_persistence(self):
        """Test state persistence across operations"""
        # Configure initial state
        self.manager.current_surah = 3
        self.manager.current_position = 45.0
        self.manager.toggle_loop()
        self.manager.toggle_shuffle()

        # Save state
        state = self.manager.get_playback_status()
        assert state["current_surah"] == 3
        assert state["current_time"] == 30.0  # From mock rich presence
        assert state["is_loop_enabled"] is True
        assert state["is_shuffle_enabled"] is True

        # Simulate restart/reload
        new_manager = AudioManager(
            bot=self.mock_bot,
            ffmpeg_path="/usr/local/bin/ffmpeg",
            audio_base_folder=str(self.audio_dir),
            default_reciter="Test Reciter",
            default_shuffle=False,
            default_loop=False,
        )
        new_manager.voice_client = self.mock_voice_client
        new_manager.rich_presence = self.mock_rich_presence

        # Load saved state
        new_manager._load_initial_state()

        # Verify state restoration
        assert new_manager.current_surah == 3
        assert new_manager.loop_enabled is True
        assert new_manager.shuffle_enabled is True

        # Test state consistency after operations
        await new_manager.start_playback(resume_position=True)
        assert new_manager.is_playing is True
        self.mock_rich_presence.seek_to_position.assert_called_with(45.0)

    def test_reciter_discovery(self):
        """Test reciter discovery and validation"""
        # Create test directory structure
        reciter_dir = self.audio_dir / "Test Reciter 2"
        reciter_dir.mkdir(parents=True)

        # Create valid and invalid files
        valid_files = ["001.mp3", "002.mp3", "114.mp3"]
        invalid_files = ["invalid.mp3", "115.mp3", "000.mp3", "test.txt"]

        for file in valid_files + invalid_files:
            (reciter_dir / file).touch()

        # Test discovery
        self.manager._scan_reciters()
        assert "Test Reciter 2" in self.manager.available_reciters

        # Test file validation
        files = self.manager._get_surah_files("Test Reciter 2")
        assert len(files) == 3  # Only valid files
        assert all(f.endswith((".mp3")) for f in files)
        assert all(1 <= int(Path(f).stem) <= 114 for f in files)

    def test_missing_surah_detection(self):
        """Test detection of missing surahs"""
        # Create sparse surah collection
        reciter_dir = self.audio_dir / "Sparse Reciter"
        reciter_dir.mkdir(parents=True)

        # Create files with gaps
        available_surahs = [1, 2, 4, 7, 10, 114]
        for surah in available_surahs:
            (reciter_dir / f"{surah:03d}.mp3").touch()

        # Switch to sparse reciter
        self.manager.change_reciter("Sparse Reciter")
        self.manager.load_audio_files()

        # Verify file count
        files = self.manager._get_surah_files("Sparse Reciter")
        assert len(files) == len(available_surahs)

        # Test navigation with missing surahs
        self.manager.current_surah = 2
        self.manager.next_surah()
        assert self.manager.current_surah == 4  # Should skip to next available

        self.manager.previous_surah()
        assert self.manager.current_surah == 2  # Should skip to previous available

    @pytest.mark.asyncio
    async def test_ffmpeg_integration(self):
        """Test FFmpeg audio source creation and seeking"""
        # Create mock FFmpeg process
        mock_ffmpeg = AsyncMock()
        mock_ffmpeg.returncode = 0

        # Mock FFmpeg audio source
        with patch("discord.FFmpegPCMAudio") as mock_ffmpeg_audio:
            # Test normal playback
            await self.manager.start_playback(resume_position=False)
            mock_ffmpeg_audio.assert_called_once()
            args = mock_ffmpeg_audio.call_args[1]
            assert "-vn" in args["options"]
            assert "-loglevel quiet" in args["options"]

            # Test seeking
            mock_ffmpeg_audio.reset_mock()
            self.manager.current_position = 30.0
            await self.manager.start_playback(resume_position=True)
            args = mock_ffmpeg_audio.call_args[1]
            assert "-ss 30.0" in args["before_options"]

            # Test error handling
            mock_ffmpeg_audio.side_effect = Exception("FFmpeg error")
            await self.manager.start_playback()
            assert not self.manager.is_playing

    @pytest.mark.asyncio
    async def test_playback_completion(self):
        """Test playback completion handling"""
        # Start playback
        await self.manager.start_playback()
        assert self.manager.is_playing

        # Mock state manager
        mock_state = MagicMock()
        self.manager.state_manager = mock_state

        # Simulate track completion
        await self.manager._on_playback_complete()

        # Verify state updates
        mock_state.mark_surah_completed.assert_called_once()
        assert self.manager.current_position == 0.0

        # Test completion with loop enabled
        self.manager.toggle_loop()
        initial_surah = self.manager.current_surah
        await self.manager._on_playback_complete()
        assert self.manager.current_surah == initial_surah

        # Test completion with shuffle enabled
        self.manager.toggle_loop()  # Disable loop
        self.manager.toggle_shuffle()
        initial_surah = self.manager.current_surah
        await self.manager._on_playback_complete()
        assert self.manager.current_surah != initial_surah

    @pytest.mark.asyncio
    async def test_file_format_validation(self):
        """Test audio file format validation"""
        # Create test files with various formats
        reciter_dir = self.audio_dir / "Format Test"
        reciter_dir.mkdir(parents=True)

        # Valid formats
        (reciter_dir / "001.mp3").touch()
        (reciter_dir / "002.mp3").touch()

        # Invalid formats
        (reciter_dir / "003.wav").touch()  # Wrong extension
        (reciter_dir / "004.MP3").touch()  # Wrong case
        (reciter_dir / "surah_005.mp3").touch()  # Wrong naming
        (reciter_dir / "006").touch()  # No extension

        # Switch to test reciter
        self.manager.change_reciter("Format Test")
        self.manager.load_audio_files()

        # Verify only valid files are loaded
        files = self.manager._get_surah_files("Format Test")
        assert len(files) == 2  # Only properly named .mp3 files
        assert all(f.endswith(".mp3") for f in files)
        assert all(Path(f).stem.isdigit() for f in files)

    @pytest.mark.asyncio
    async def test_track_transition(self):
        """Test smooth track transitions"""
        # Start playback
        await self.manager.start_playback()
        assert self.manager.is_playing

        # Track current state
        initial_surah = self.manager.current_surah
        initial_position = self.manager.current_position

        # Simulate track completion
        self.mock_voice_client.is_playing.return_value = False
        await asyncio.sleep(1)  # Let the playback loop detect completion

        # Verify clean transition
        assert self.manager.current_surah != initial_surah
        assert self.manager.current_position == 0.0
        assert self.manager.is_playing

        # Verify rich presence update
        self.mock_rich_presence.stop_track.assert_called_once()
        self.mock_rich_presence.start_track.call_count >= 2  # Initial + next track

    @pytest.mark.asyncio
    async def test_resource_cleanup(self):
        """Test thorough resource cleanup"""
        # Start multiple background tasks
        await self.manager.start_playback()
        original_task = self.manager.playback_task
        original_save_task = self.manager.position_save_task

        # Verify tasks are running
        assert not original_task.done()
        assert not original_save_task.done()

        # Stop playback
        await self.manager.stop_playback()

        # Verify all tasks are cleaned up
        assert original_task.cancelled()
        assert original_save_task.cancelled()
        assert self.manager.voice_client is not None  # Should maintain connection
        assert not self.manager.is_playing
        assert not self.manager.is_paused

        # Verify rich presence cleanup
        self.mock_rich_presence.stop_track.assert_called_once()

        # Test cleanup after errors
        await self.manager.start_playback()
        self.mock_voice_client.play.side_effect = Exception("Playback error")
        await self.manager.start_playback()  # Should handle error gracefully
        assert not self.manager.is_playing
        assert self.manager.playback_task.done()
