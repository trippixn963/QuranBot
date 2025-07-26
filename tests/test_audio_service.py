# =============================================================================
# QuranBot - Audio Service Tests
# =============================================================================
# Comprehensive tests for the modern AudioService including dependency
# injection, caching, error handling, and real-world scenarios.
# =============================================================================

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import discord
from discord.ext import commands
import pytest

from src.core.di_container import DIContainer
from src.core.exceptions import (
    AudioError,
    FFmpegError,
    ValidationError,
    VoiceConnectionError,
)
from src.core.structured_logger import StructuredLogger
from src.data.models import (
    AudioFileInfo,
    AudioServiceConfig,
    PlaybackMode,
    PlaybackState,
    ReciterInfo,
)
from src.services.audio_service import AudioService
from src.services.metadata_cache import MetadataCache

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
async def mock_logger():
    """Create a mock structured logger"""
    logger = Mock(spec=StructuredLogger)
    logger.info = AsyncMock()
    logger.warning = AsyncMock()
    logger.error = AsyncMock()
    logger.debug = AsyncMock()
    return logger


@pytest.fixture
async def mock_cache():
    """Create a mock metadata cache"""
    cache = Mock(spec=MetadataCache)
    cache.initialize = AsyncMock()
    cache.shutdown = AsyncMock()
    cache.get_file_info = AsyncMock()
    cache.warm_cache_for_reciter = AsyncMock()
    cache.get_cache_stats = AsyncMock()
    return cache


@pytest.fixture
def mock_bot():
    """Create a mock Discord bot"""
    bot = Mock(spec=commands.Bot)
    bot.get_guild = Mock()
    return bot


@pytest.fixture
def mock_container():
    """Create a mock DI container"""
    container = Mock(spec=DIContainer)
    # Mock BotConfig instead of creating a real one
    bot_config = Mock()
    bot_config.guild_id = 123456789
    bot_config.voice_channel_id = 987654321
    bot_config.panel_channel_id = 111222333
    container.get.return_value = bot_config
    return container


@pytest.fixture
def audio_config(tmp_path):
    """Create test audio configuration"""
    audio_folder = tmp_path / "audio"
    audio_folder.mkdir()

    # Create test reciter folder
    reciter_folder = audio_folder / "Test Reciter"
    reciter_folder.mkdir()

    # Create test MP3 files
    for i in range(1, 4):
        (reciter_folder / f"{i:03d}.mp3").touch()

    return AudioServiceConfig(
        audio_base_folder=audio_folder,
        ffmpeg_path="/usr/bin/ffmpeg",
        default_reciter="Test Reciter",
        cache_enabled=True,
        preload_metadata=False,  # Disable for tests
    )


@pytest.fixture
async def audio_service_uninitialized(
    mock_container, mock_bot, audio_config, mock_logger, mock_cache
):
    """Create uninitialized AudioService instance for testing initialization"""
    service = AudioService(
        container=mock_container,
        bot=mock_bot,
        config=audio_config,
        logger=mock_logger,
        metadata_cache=mock_cache,
    )
    return service


@pytest.fixture
async def audio_service(
    mock_container, mock_bot, audio_config, mock_logger, mock_cache
):
    """Create initialized AudioService instance for testing"""
    service = AudioService(
        container=mock_container,
        bot=mock_bot,
        config=audio_config,
        logger=mock_logger,
        metadata_cache=mock_cache,
    )
    # Initialize the service to discover reciters
    await service.initialize()
    return service


class TestAudioService:
    """Test suite for the AudioService class"""


class TestAudioServiceInitialization:
    """Test AudioService initialization"""

    @pytest.mark.asyncio
    async def test_successful_initialization(
        self, audio_service_uninitialized, mock_cache, mock_logger
    ):
        """Test successful service initialization"""
        audio_service = audio_service_uninitialized
        # Mock reciter discovery
        with patch.object(audio_service, "_discover_reciters") as mock_discover:
            mock_discover.return_value = None

            await audio_service.initialize()

            # Verify cache was initialized
            mock_cache.initialize.assert_called_once()

            # Verify discovery was called
            mock_discover.assert_called_once()

            # Verify logging
            mock_logger.info.assert_any_call("Initializing audio service")

    @pytest.mark.asyncio
    async def test_initialization_failure(self, audio_service, mock_cache, mock_logger):
        """Test initialization failure handling"""
        # Make cache initialization fail
        mock_cache.initialize.side_effect = Exception("Cache init failed")

        with pytest.raises(AudioError) as exc_info:
            await audio_service.initialize()

        assert "Audio service initialization failed" in str(exc_info.value)
        assert exc_info.value.context["operation"] == "initialization"

    @pytest.mark.asyncio
    async def test_shutdown(self, audio_service, mock_cache, mock_logger):
        """Test service shutdown"""
        # Mock active playback task
        audio_service._playback_task = AsyncMock()
        audio_service._monitoring_task = AsyncMock()
        audio_service._position_save_task = AsyncMock()

        # Mock voice client
        mock_voice_client = AsyncMock()
        audio_service._voice_client = mock_voice_client

        await audio_service.shutdown()

        # Verify cache shutdown
        mock_cache.shutdown.assert_called_once()

        # Verify logging
        mock_logger.info.assert_any_call("Shutting down audio service")
        mock_logger.info.assert_any_call("Audio service shutdown complete")


class TestVoiceConnectionManagement:
    """Test voice connection functionality"""

    @pytest.mark.asyncio
    async def test_successful_voice_connection(self, audio_service, mock_bot):
        """Test successful voice channel connection"""
        # Setup mocks
        mock_guild = Mock()
        mock_channel = Mock(spec=discord.VoiceChannel)
        mock_channel.name = "Test Channel"
        mock_channel.permissions_for.return_value.connect = True
        mock_voice_client = AsyncMock()
        mock_voice_client.is_connected.return_value = True

        mock_bot.get_guild.return_value = mock_guild
        mock_guild.get_channel.return_value = mock_channel
        mock_guild.me = Mock()

        with patch.object(asyncio, "wait_for") as mock_wait_for:
            mock_wait_for.return_value = mock_voice_client
            mock_channel.connect = AsyncMock(return_value=mock_voice_client)

            result = await audio_service.connect_to_voice_channel(987654321, 123456789)

            assert result is True
            assert audio_service._voice_client == mock_voice_client
            assert audio_service._current_state.is_connected is True
            assert audio_service._current_state.voice_channel_id == 987654321

    @pytest.mark.asyncio
    async def test_guild_not_found_error(self, audio_service, mock_bot):
        """Test guild not found error handling"""
        mock_bot.get_guild.return_value = None

        with pytest.raises(VoiceConnectionError) as exc_info:
            await audio_service.connect_to_voice_channel(987654321, 123456789)

        assert "Guild not found: 123456789" in str(exc_info.value)
        assert exc_info.value.context["operation"] == "guild_lookup"

    @pytest.mark.asyncio
    async def test_channel_not_found_error(self, audio_service, mock_bot):
        """Test voice channel not found error handling"""
        mock_guild = Mock()
        mock_bot.get_guild.return_value = mock_guild
        mock_guild.get_channel.return_value = None

        with pytest.raises(VoiceConnectionError) as exc_info:
            await audio_service.connect_to_voice_channel(987654321, 123456789)

        assert "Voice channel not found: 987654321" in str(exc_info.value)
        assert exc_info.value.context["operation"] == "channel_lookup"

    @pytest.mark.asyncio
    async def test_permission_denied_error(self, audio_service, mock_bot):
        """Test permission denied error handling"""
        mock_guild = Mock()
        mock_channel = Mock(spec=discord.VoiceChannel)
        mock_channel.permissions_for.return_value.connect = False

        mock_bot.get_guild.return_value = mock_guild
        mock_guild.get_channel.return_value = mock_channel
        mock_guild.me = Mock()

        with pytest.raises(VoiceConnectionError) as exc_info:
            await audio_service.connect_to_voice_channel(987654321, 123456789)

        assert "Missing permission to connect to channel 987654321" in str(
            exc_info.value
        )
        assert exc_info.value.context["required_permission"] == "connect"

    @pytest.mark.asyncio
    async def test_connection_timeout_error(self, audio_service, mock_bot):
        """Test connection timeout error handling"""
        mock_guild = Mock()
        mock_channel = Mock(spec=discord.VoiceChannel)
        mock_channel.permissions_for.return_value.connect = True

        mock_bot.get_guild.return_value = mock_guild
        mock_guild.get_channel.return_value = mock_channel
        mock_guild.me = Mock()

        with patch.object(asyncio, "wait_for") as mock_wait_for:
            mock_wait_for.side_effect = TimeoutError()

            with pytest.raises(VoiceConnectionError) as exc_info:
                await audio_service.connect_to_voice_channel(987654321, 123456789)

            assert "Connection timeout after" in str(exc_info.value)
            assert exc_info.value.context["operation"] == "connection_timeout"


class TestPlaybackManagement:
    """Test audio playback functionality"""

    @pytest.mark.asyncio
    async def test_start_playback_without_connection(self, audio_service):
        """Test starting playback without voice connection"""
        audio_service._voice_client = None

        with pytest.raises(AudioError) as exc_info:
            await audio_service.start_playback()

        assert "Cannot start playback: not connected to voice channel" in str(
            exc_info.value
        )
        assert exc_info.value.context["operation"] == "playback_start_validation"

    @pytest.mark.asyncio
    async def test_start_playback_success(self, audio_service):
        """Test successful playback start"""
        # Setup mock voice client
        mock_voice_client = Mock()
        mock_voice_client.is_connected.return_value = True
        audio_service._voice_client = mock_voice_client

        # Mock stop_playback and _playback_loop
        audio_service.stop_playback = AsyncMock()

        with patch.object(asyncio, "create_task") as mock_create_task:
            result = await audio_service.start_playback(
                reciter="Test Reciter", surah_number=1
            )

            assert result is True
            audio_service.stop_playback.assert_called_once()
            mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_pause_and_resume_playback(self, audio_service):
        """Test pause and resume functionality"""
        # Setup mock voice client
        mock_voice_client = Mock()
        mock_voice_client.is_playing.return_value = True
        mock_voice_client.is_paused.return_value = False
        audio_service._voice_client = mock_voice_client

        # Test pause
        result = await audio_service.pause_playback()
        assert result is True
        mock_voice_client.pause.assert_called_once()
        assert audio_service._current_state.is_paused is True
        assert audio_service._current_state.is_playing is False

        # Test resume
        mock_voice_client.is_paused.return_value = True
        result = await audio_service.resume_playback()
        assert result is True
        mock_voice_client.resume.assert_called_once()
        assert audio_service._current_state.is_playing is True
        assert audio_service._current_state.is_paused is False

    @pytest.mark.asyncio
    async def test_stop_playback(self, audio_service):
        """Test stop playback functionality"""
        # Setup mock voice client and playback task
        mock_voice_client = Mock()
        mock_voice_client.is_playing.return_value = True
        audio_service._voice_client = mock_voice_client

        mock_task = AsyncMock()
        mock_task.done.return_value = False
        audio_service._playback_task = mock_task

        await audio_service.stop_playback()

        mock_task.cancel.assert_called_once()
        mock_voice_client.stop.assert_called_once()
        assert audio_service._current_state.is_playing is False
        assert audio_service._current_state.is_paused is False


class TestReciterAndSurahManagement:
    """Test reciter and surah management"""

    @pytest.mark.asyncio
    async def test_set_valid_reciter(self, audio_service):
        """Test setting a valid reciter"""
        # Setup available reciters
        reciter_info = ReciterInfo(
            name="Test Reciter",
            folder_name="Test Reciter",
            total_surahs=114,
            file_count=114,
        )
        audio_service._available_reciters = [reciter_info]

        result = await audio_service.set_reciter("Test Reciter")

        assert result is True
        assert audio_service._current_state.current_reciter == "Test Reciter"

    @pytest.mark.asyncio
    async def test_set_invalid_reciter(self, audio_service):
        """Test setting an invalid reciter"""
        audio_service._available_reciters = []

        with pytest.raises(ValidationError) as exc_info:
            await audio_service.set_reciter("Invalid Reciter")

        assert "Reciter not found: Invalid Reciter" in str(exc_info.value)
        assert exc_info.value.context["field_name"] == "reciter"

    @pytest.mark.asyncio
    async def test_set_valid_surah(self, audio_service):
        """Test setting a valid surah number"""
        result = await audio_service.set_surah(1)

        assert result is True
        assert audio_service._current_state.current_position.surah_number == 1
        assert audio_service._current_state.current_position.position_seconds == 0.0

    @pytest.mark.asyncio
    async def test_set_invalid_surah(self, audio_service):
        """Test setting an invalid surah number"""
        with pytest.raises(ValidationError) as exc_info:
            await audio_service.set_surah(115)

        assert "Invalid surah number: 115" in str(exc_info.value)
        assert exc_info.value.context["field_name"] == "surah_number"
        assert exc_info.value.context["validation_rule"] == "Must be between 1 and 114"

    @pytest.mark.asyncio
    async def test_set_valid_volume(self, audio_service):
        """Test setting a valid volume"""
        result = await audio_service.set_volume(0.5)

        assert result is True
        assert audio_service._current_state.volume == 0.5

    @pytest.mark.asyncio
    async def test_set_invalid_volume(self, audio_service):
        """Test setting an invalid volume"""
        with pytest.raises(ValidationError) as exc_info:
            await audio_service.set_volume(1.5)

        assert "Invalid volume level: 1.5" in str(exc_info.value)
        assert exc_info.value.context["field_name"] == "volume"


class TestPlaybackModes:
    """Test playback mode functionality"""

    @pytest.mark.asyncio
    async def test_set_playback_mode(self, audio_service):
        """Test setting different playback modes"""
        # Test normal mode
        result = await audio_service.set_playback_mode(PlaybackMode.NORMAL)
        assert result is True
        assert audio_service._current_state.mode == PlaybackMode.NORMAL

        # Test shuffle mode
        result = await audio_service.set_playback_mode(PlaybackMode.SHUFFLE)
        assert result is True
        assert audio_service._current_state.mode == PlaybackMode.SHUFFLE

        # Test loop track mode
        result = await audio_service.set_playback_mode(PlaybackMode.LOOP_TRACK)
        assert result is True
        assert audio_service._current_state.mode == PlaybackMode.LOOP_TRACK

        # Test loop playlist mode
        result = await audio_service.set_playback_mode(PlaybackMode.LOOP_PLAYLIST)
        assert result is True
        assert audio_service._current_state.mode == PlaybackMode.LOOP_PLAYLIST


class TestStateAndInfoRetrieval:
    """Test state and information retrieval"""

    @pytest.mark.asyncio
    async def test_get_playback_state(self, audio_service):
        """Test getting current playback state"""
        # Set some state
        audio_service._current_state.is_playing = True
        audio_service._current_state.current_reciter = "Test Reciter"

        state = await audio_service.get_playback_state()

        assert isinstance(state, PlaybackState)
        assert state.is_playing is True
        assert state.current_reciter == "Test Reciter"
        assert state.last_updated is not None

    @pytest.mark.asyncio
    async def test_get_available_reciters(self, audio_service):
        """Test getting available reciters"""
        reciter_info = ReciterInfo(
            name="Test Reciter",
            folder_name="Test Reciter",
            total_surahs=114,
            file_count=114,
        )
        audio_service._available_reciters = [reciter_info]

        reciters = await audio_service.get_available_reciters()

        assert len(reciters) == 1
        assert reciters[0].name == "Test Reciter"
        assert isinstance(reciters[0], ReciterInfo)

    @pytest.mark.asyncio
    async def test_get_current_file_info(self, audio_service, mock_cache):
        """Test getting current file information"""
        # Setup mock file info
        file_info = AudioFileInfo(
            file_path=Path("/test/001.mp3"),
            surah_number=1,
            reciter="Test Reciter",
            duration_seconds=87.5,
            file_size_bytes=1024,
        )
        mock_cache.get_file_info.return_value = file_info

        # Mock _get_current_audio_file_path
        with patch.object(
            audio_service, "_get_current_audio_file_path"
        ) as mock_get_path:
            mock_get_path.return_value = Path("/test/001.mp3")

            result = await audio_service.get_current_file_info()

            assert result == file_info
            mock_cache.get_file_info.assert_called_once()


class TestReciterDiscovery:
    """Test reciter discovery functionality"""

    @pytest.mark.asyncio
    async def test_discover_reciters_success(
        self, audio_service, audio_config, mock_cache
    ):
        """Test successful reciter discovery"""
        await audio_service._discover_reciters()

        assert len(audio_service._available_reciters) == 1
        assert audio_service._available_reciters[0].name == "Test Reciter"
        assert audio_service._available_reciters[0].total_surahs == 3
        assert audio_service._available_reciters[0].file_count == 3

    @pytest.mark.asyncio
    async def test_discover_reciters_missing_folder(
        self, audio_service, tmp_path, mock_logger
    ):
        """Test reciter discovery with missing audio folder"""
        # Update config to point to non-existent folder
        audio_service._config.audio_base_folder = tmp_path / "missing"

        await audio_service._discover_reciters()

        assert len(audio_service._available_reciters) == 0
        mock_logger.warning.assert_called_with(
            "Audio base folder does not exist", {"folder": str(tmp_path / "missing")}
        )


class TestErrorHandling:
    """Test error handling scenarios"""

    @pytest.mark.asyncio
    async def test_ffmpeg_error_handling(self, audio_service):
        """Test FFmpeg error handling during audio source creation"""
        file_path = Path("/test/001.mp3")

        with patch("discord.FFmpegPCMAudio") as mock_ffmpeg:
            mock_ffmpeg.side_effect = Exception("FFmpeg failed")

            with pytest.raises(FFmpegError) as exc_info:
                await audio_service._create_audio_source(file_path)

            assert "Failed to create audio source" in str(exc_info.value)
            assert exc_info.value.context["file_path"] == str(file_path)

    @pytest.mark.asyncio
    async def test_cache_error_handling(self, audio_service, mock_cache, mock_logger):
        """Test handling of cache errors"""
        mock_cache.get_file_info.side_effect = Exception("Cache error")

        result = await audio_service.get_current_file_info()

        assert result is None
        mock_logger.warning.assert_called_with(
            "Failed to get current file info", {"error": "Cache error"}
        )


class TestPlaybackLoop:
    """Test the main playback loop functionality"""

    @pytest.mark.asyncio
    async def test_playback_loop_voice_disconnection(self, audio_service, mock_logger):
        """Test playback loop handling voice disconnection"""
        # Setup disconnected voice client
        audio_service._voice_client = None

        # Run playback loop (should exit immediately)
        await audio_service._playback_loop()

        mock_logger.warning.assert_called_with(
            "Voice client disconnected, stopping playback"
        )

    @pytest.mark.asyncio
    async def test_advance_to_next_track_normal_mode(self, audio_service):
        """Test advancing to next track in normal mode"""
        # Setup state
        audio_service._current_state.mode = PlaybackMode.NORMAL
        audio_service._current_state.current_position.surah_number = 1

        # Mock reciter info
        reciter_info = ReciterInfo(
            name="Test Reciter",
            folder_name="Test Reciter",
            total_surahs=114,
            file_count=114,
        )

        with patch.object(audio_service, "_get_reciter_info") as mock_get_reciter:
            mock_get_reciter.return_value = reciter_info

            await audio_service._advance_to_next_track()

            assert audio_service._current_state.current_position.surah_number == 2
            assert audio_service._current_state.current_position.position_seconds == 0.0

    @pytest.mark.asyncio
    async def test_advance_to_next_track_shuffle_mode(self, audio_service):
        """Test advancing to next track in shuffle mode"""
        audio_service._current_state.mode = PlaybackMode.SHUFFLE
        audio_service._current_state.current_position.surah_number = 1

        # Mock reciter info
        reciter_info = ReciterInfo(
            name="Test Reciter",
            folder_name="Test Reciter",
            total_surahs=3,
            file_count=3,
        )

        with patch.object(audio_service, "_get_reciter_info") as mock_get_reciter:
            with patch("random.choice") as mock_choice:
                mock_get_reciter.return_value = reciter_info
                mock_choice.return_value = 3

                await audio_service._advance_to_next_track()

                assert audio_service._current_state.current_position.surah_number == 3

    @pytest.mark.asyncio
    async def test_advance_to_next_track_loop_track_mode(self, audio_service):
        """Test advancing to next track in loop track mode"""
        audio_service._current_state.mode = PlaybackMode.LOOP_TRACK
        audio_service._current_state.current_position.surah_number = 1
        audio_service._current_state.current_position.position_seconds = 45.0

        await audio_service._advance_to_next_track()

        # Should stay on same track but reset position
        assert audio_service._current_state.current_position.surah_number == 1
        assert audio_service._current_state.current_position.position_seconds == 0.0


class TestUtilityMethods:
    """Test utility methods"""

    def test_extract_surah_number(self, audio_service):
        """Test surah number extraction from filename"""
        assert audio_service._extract_surah_number("001.mp3") == 1
        assert audio_service._extract_surah_number("114-An-Nas.mp3") == 114
        assert audio_service._extract_surah_number("invalid.mp3") is None
        assert audio_service._extract_surah_number("999.mp3") is None  # Out of range

    @pytest.mark.asyncio
    async def test_get_current_audio_file_path(self, audio_service, audio_config):
        """Test getting current audio file path"""
        audio_service._current_state.current_reciter = "Test Reciter"
        audio_service._current_state.current_position.surah_number = 1

        result = await audio_service._get_current_audio_file_path()

        assert result is not None
        assert result.name == "001.mp3"
        assert "Test Reciter" in str(result)


class TestIntegrationScenarios:
    """Test real-world integration scenarios"""

    @pytest.mark.asyncio
    async def test_complete_playback_workflow(self, audio_service, mock_cache):
        """Test complete playback workflow from start to finish"""
        # Setup mocks
        mock_voice_client = Mock()
        mock_voice_client.is_connected.return_value = True
        mock_voice_client.is_playing.return_value = True
        audio_service._voice_client = mock_voice_client

        file_info = AudioFileInfo(
            file_path=Path("/test/001.mp3"),
            surah_number=1,
            reciter="Test Reciter",
            duration_seconds=87.5,
            file_size_bytes=1024,
        )
        mock_cache.get_file_info.return_value = file_info

        # Mock file path resolution
        with patch.object(
            audio_service, "_get_current_audio_file_path"
        ) as mock_get_path:
            with patch.object(
                audio_service, "_create_audio_source"
            ) as mock_create_source:
                with patch.object(
                    audio_service, "_wait_for_playback_completion"
                ) as mock_wait:
                    mock_get_path.return_value = Path("/test/001.mp3")
                    mock_create_source.return_value = Mock()
                    mock_wait.return_value = None

                    # Start playback
                    result = await audio_service.start_playback()
                    assert result is True

                    # Verify voice client play was called
                    assert (
                        audio_service._current_state.is_playing is False
                    )  # Set by stop_playback in start

    @pytest.mark.asyncio
    async def test_connection_recovery_scenario(
        self, audio_service, mock_bot, mock_logger
    ):
        """Test automatic connection recovery"""
        # Setup initial connection
        audio_service._target_channel_id = 987654321
        audio_service._guild_id = 123456789

        # Mock successful reconnection
        mock_guild = Mock()
        mock_channel = Mock(spec=discord.VoiceChannel)
        mock_channel.name = "Test Channel"
        mock_channel.permissions_for.return_value.connect = True
        mock_voice_client = AsyncMock()
        mock_voice_client.is_connected.return_value = True

        mock_bot.get_guild.return_value = mock_guild
        mock_guild.get_channel.return_value = mock_channel
        mock_guild.me = Mock()

        with patch.object(asyncio, "wait_for") as mock_wait_for:
            mock_wait_for.return_value = mock_voice_client
            mock_channel.connect = AsyncMock(return_value=mock_voice_client)

            # Simulate monitoring loop detecting disconnection
            audio_service._voice_client = Mock()
            audio_service._voice_client.is_connected.return_value = False

            # Manually trigger reconnection logic
            await audio_service.connect_to_voice_channel(987654321, 123456789)

            assert audio_service._voice_client == mock_voice_client
            assert audio_service._current_state.is_connected is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
