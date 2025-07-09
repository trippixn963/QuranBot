#!/usr/bin/env python3
# =============================================================================
# QuranBot - Control Panel Tests
# =============================================================================
# Comprehensive tests for Discord UI control panel functionality
# =============================================================================

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from utils.control_panel import (
    ReciterSelect,
    SearchResultsView,
    SimpleControlPanelView,
    SurahSearchModal,
    SurahSelect,
    cleanup_all_control_panels,
    create_control_panel,
    setup_control_panel,
)


class TestControlPanel:
    """Test suite for control panel functionality"""

    def setup_method(self):
        """Set up test environment"""
        # Mock bot
        self.mock_bot = MagicMock()
        self.mock_bot.user = MagicMock()
        self.mock_bot.user.avatar = MagicMock()
        self.mock_bot.user.avatar.url = "https://example.com/avatar.png"

        # Mock audio manager
        self.mock_audio_manager = MagicMock()
        self.mock_audio_manager.get_playback_status.return_value = {
            "is_playing": True,
            "is_paused": False,
            "current_surah": 1,
            "current_reciter": "Test Reciter",
            "is_loop_enabled": False,
            "is_shuffle_enabled": False,
            "current_track": 1,
            "total_tracks": 114,
            "available_reciters": ["Test Reciter"],
            "current_time": 30.0,
            "total_time": 300.0,
        }

        # Mock interaction
        self.mock_interaction = AsyncMock()
        self.mock_interaction.user = MagicMock()
        self.mock_interaction.user.display_name = "Test User"
        self.mock_interaction.user.id = 123456789

        # Create control panel view
        self.panel = SimpleControlPanelView(self.mock_bot, self.mock_audio_manager)

    def test_initial_state(self):
        """Test initial control panel state"""
        assert self.panel.bot == self.mock_bot
        assert self.panel.audio_manager == self.mock_audio_manager
        assert self.panel.current_page == 0
        assert self.panel.loop_enabled is False
        assert self.panel.shuffle_enabled is False
        assert len(self.panel.children) > 0

        # Verify components
        components = {type(item).__name__ for item in self.panel.children}
        assert "SurahSelect" in components
        assert "ReciterSelect" in components

    def test_last_activity_tracking(self):
        """Test last activity tracking functionality"""
        # Initial state
        assert self.panel.last_activity_user is None
        assert self.panel.last_activity_time is None
        assert self.panel.last_activity_action is None

        # Update activity
        self.panel._update_last_activity(self.mock_interaction.user, "test action")
        assert self.panel.last_activity_user == self.mock_interaction.user
        assert isinstance(self.panel.last_activity_time, datetime)
        assert self.panel.last_activity_action == "test action"

        # Test time formatting
        time = datetime.now(timezone.utc)
        formatted = self.panel._format_time_elapsed(time)
        assert isinstance(formatted, str)
        assert "ago" in formatted

    @pytest.mark.asyncio
    async def test_panel_updates(self):
        """Test panel update functionality"""
        # Mock message
        mock_message = AsyncMock()
        mock_message.channel = AsyncMock()
        mock_message.channel.fetch_message = AsyncMock(return_value=mock_message)
        mock_message.edit = AsyncMock()

        # Set panel message
        self.panel.panel_message = mock_message
        self.panel.start_updates()

        # Verify update task started
        assert self.panel.update_task is not None
        assert not self.panel.update_task.done()

        # Test update
        await self.panel.update_panel()
        mock_message.edit.assert_called_once()

        # Cleanup
        self.panel.cleanup()
        assert self.panel.update_task.cancelled()

    @pytest.mark.asyncio
    async def test_button_callbacks(self):
        """Test button callback functionality"""
        # Test loop toggle
        loop_button = next(
            item
            for item in self.panel.children
            if getattr(item, "label", "") == "🔁 Loop"
        )
        assert loop_button is not None

        # Initial state
        assert not self.panel.loop_enabled
        assert loop_button.style == discord.ButtonStyle.secondary

        # Toggle on
        await self.panel.toggle_loop(self.mock_interaction, loop_button)
        assert self.panel.loop_enabled
        assert loop_button.style == discord.ButtonStyle.success

        # Toggle off
        await self.panel.toggle_loop(self.mock_interaction, loop_button)
        assert not self.panel.loop_enabled
        assert loop_button.style == discord.ButtonStyle.secondary

    @pytest.mark.asyncio
    async def test_surah_selection(self):
        """Test surah selection functionality"""
        # Get surah select
        surah_select = next(
            item for item in self.panel.children if isinstance(item, SurahSelect)
        )
        assert surah_select is not None

        # Verify initial options
        assert len(surah_select.options) == 10  # First page
        assert all("Surah" in opt.label for opt in surah_select.options)

        # Test selection
        surah_select.values = ["1"]  # Al-Fatiha
        await surah_select.callback(self.mock_interaction)
        self.mock_audio_manager.jump_to_surah.assert_called_with(1)

    @pytest.mark.asyncio
    async def test_reciter_selection(self):
        """Test reciter selection functionality"""
        # Get reciter select
        reciter_select = next(
            item for item in self.panel.children if isinstance(item, ReciterSelect)
        )
        assert reciter_select is not None

        # Test selection
        reciter_select.values = ["Test Reciter"]
        await reciter_select.callback(self.mock_interaction)
        self.mock_audio_manager.switch_reciter.assert_called_with("Test Reciter")

    @pytest.mark.asyncio
    async def test_search_functionality(self):
        """Test surah search functionality"""
        # Create search modal
        search_modal = SurahSearchModal(
            audio_manager=self.mock_audio_manager, control_panel_view=self.panel
        )

        # Test empty search
        search_modal.search_input.value = ""
        await search_modal.on_submit(self.mock_interaction)
        self.mock_interaction.response.send_message.assert_called_with(
            "❌ Please enter a search term!", ephemeral=True
        )

        # Test valid search
        search_modal.search_input.value = "fatiha"
        await search_modal.on_submit(self.mock_interaction)
        # Verify search results view was created

    @pytest.mark.asyncio
    async def test_page_navigation(self):
        """Test page navigation functionality"""
        # Initial state
        assert self.panel.current_page == 0

        # Test next page
        next_button = next(
            item
            for item in self.panel.children
            if getattr(item, "label", "") == "➡️ Next Page"
        )
        assert next_button is not None

        await self.panel.next_page(self.mock_interaction, next_button)
        assert self.panel.current_page == 1

        # Verify surah select updated
        surah_select = next(
            item for item in self.panel.children if isinstance(item, SurahSelect)
        )
        assert surah_select.page == 1

    @pytest.mark.asyncio
    async def test_panel_creation(self):
        """Test control panel creation"""
        # Mock channel
        mock_channel = AsyncMock()
        mock_channel.name = "test-channel"
        mock_channel.id = 123456789
        mock_channel.send = AsyncMock()
        mock_channel.history = AsyncMock(return_value=[])
        mock_channel.guild = MagicMock()
        mock_channel.guild.me = MagicMock()

        # Test permissions
        mock_channel.permissions_for.return_value = MagicMock(
            send_messages=True, manage_messages=True
        )

        # Create panel
        message = await create_control_panel(
            self.mock_bot, mock_channel, self.mock_audio_manager
        )
        assert message is not None

        # Verify cleanup
        cleanup_all_control_panels()
        assert len(_active_panels) == 0

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in control panel"""
        # Test message deletion error
        mock_message = AsyncMock()
        mock_message.delete.side_effect = discord.NotFound(MagicMock(), "Not found")

        mock_channel = AsyncMock()
        mock_channel.history.return_value = [mock_message]
        mock_channel.permissions_for.return_value = MagicMock(
            send_messages=True, manage_messages=True
        )

        # Should handle error gracefully
        message = await create_control_panel(
            self.mock_bot, mock_channel, self.mock_audio_manager
        )
        assert message is not None

        # Test rate limit handling
        mock_channel.send.side_effect = [
            discord.HTTPException(MagicMock(), "Rate limited"),
            AsyncMock(),  # Second attempt succeeds
        ]

        message = await create_control_panel(
            self.mock_bot, mock_channel, self.mock_audio_manager
        )
        assert message is not None

    def test_progress_bar(self):
        """Test progress bar creation"""
        # Test zero duration
        bar = self.panel._create_progress_bar(0, 0)
        assert "0%" in bar
        assert "▱" * 20 in bar

        # Test partial progress
        bar = self.panel._create_progress_bar(150, 300)
        assert "50%" in bar
        assert "▰" * 10 in bar
        assert "▱" * 10 in bar

        # Test complete
        bar = self.panel._create_progress_bar(300, 300)
        assert "100%" in bar
        assert "▰" * 20 in bar

    def test_time_formatting(self):
        """Test time formatting functionality"""
        # Test zero
        assert self.panel._format_time(0) == "00:00"

        # Test minutes and seconds
        assert self.panel._format_time(65) == "01:05"

        # Test hours
        assert self.panel._format_time(3665) == "1:01:05"

        # Test invalid input
        assert self.panel._format_time(-1) == "00:00"
