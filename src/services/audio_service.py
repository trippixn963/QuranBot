# =============================================================================
# QuranBot - Modern Audio Service
# =============================================================================
# This module provides a modern, type-safe audio service with dependency
# injection, comprehensive error handling, and advanced features.
# =============================================================================

"""
The AudioService is the core component responsible for:
- Voice channel connection management with automatic reconnection
- Audio file playback using FFmpeg with stability optimizations
- Metadata caching for improved performance
- Automatic error recovery and health monitoring
- State persistence for seamless resume functionality
- 24/7 continuous operation with aggressive reconnection strategies

Classes:
    AudioService: Main audio service with comprehensive playback management

Exceptions:
    AudioError: Generic audio-related error
    FFmpegError: FFmpeg-specific error
    ValidationError: Input validation error
    VoiceConnectionError: Voice connection-related error
"""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
import random
import re

import discord
from discord.ext import commands

from src.config import get_guild_id, get_target_channel_id
from src.core.di_container import DIContainer
from src.core.exceptions import (
    AudioError,
    FFmpegError,
    ValidationError,
    VoiceConnectionError,
)
from src.core.logger import StructuredLogger
from src.core.webhook_logger import LogLevel
from src.data.models import (
    AudioFileInfo,
    AudioServiceConfig,
    PlaybackMode,
    PlaybackPosition,
    PlaybackState,
    ReciterInfo,
)

from .metadata_cache import MetadataCache
from .state_service import SQLiteStateService


class AudioService:
    """Modern audio service with dependency injection and type safety.

    This service provides comprehensive audio playback functionality including:
    - Voice channel connection management with automatic reconnection
    - Audio file playback with FFmpeg and stability optimizations
    - Metadata caching for improved performance
    - Automatic error recovery and health monitoring
    - State persistence using SQLite database
    - 24/7 monitoring and health checks with aggressive reconnection
    - Support for multiple playback modes (normal, loop, shuffle)

    Attributes:
        _container: Dependency injection container
        _bot: Discord bot instance
        _config: Audio service configuration
        _logger: Structured logger instance
        _cache: Metadata cache service
        _health_monitor: Health monitoring service
        _voice_client: Discord voice client for audio playback
        _current_state: Current playback state
        _available_reciters: List of discovered reciters
        _playback_task: Background playback task
        _monitoring_task: Background monitoring task
        _position_save_task: Background position saving task
    """

    def __init__(
        self,
        container: DIContainer,
        bot: commands.Bot,
        config: AudioServiceConfig,
        logger: StructuredLogger,
        metadata_cache: MetadataCache,
    ) -> None:
        """Initialize the audio service.

        Sets up all necessary components for audio playback including voice client
        management, state tracking, and background task initialization.

        Args:
            container: Dependency injection container for service access
            bot: Discord bot instance for voice connections
            config: Audio service configuration with playback settings
            logger: Structured logger for comprehensive logging
            metadata_cache: Metadata cache service for performance optimization
        """
        self._container = container
        self._bot = bot
        self._config = config
        self._logger = logger
        self._cache = metadata_cache

        # Health monitor (will be set during initialization)
        self._health_monitor = None

        # Voice client management
        self._voice_client: discord.VoiceClient | None = None
        self._target_channel_id: int | None = None
        self._guild_id: int | None = None

        # Playback state
        self._current_state = PlaybackState(
            current_reciter=config.default_reciter,
            current_position=PlaybackPosition(surah_number=1),
            volume=config.default_volume,
        )

        # Available reciters
        self._available_reciters: list[ReciterInfo] = []

        # Background tasks
        self._playback_task: asyncio.Task | None = None
        self._monitoring_task: asyncio.Task | None = None
        self._position_save_task: asyncio.Task | None = None

        # Recovery and monitoring
        self._connection_attempts = 0
        self._last_successful_playback = datetime.now(UTC)
        self._health_check_interval = 60  # seconds

        # Track state for resume functionality
        self._track_start_time: float | None = None
        self._pause_timestamp: float | None = None
        self._resume_offset: float = 0.0

    async def initialize(self) -> None:
        """Initialize the audio service.

        Performs complete initialization including:
        - Metadata cache initialization
        - Saved state loading from SQLite database
        - Reciter discovery from audio folder structure
        - Bot configuration loading
        - Background task startup
        - Health monitor integration

        Raises:
            AudioError: If initialization fails at any critical step
        """
        await self._logger.info("Initializing audio service")

        try:
            # Initialize metadata cache
            await self._cache.initialize()

            # Load saved playback state
            await self._load_saved_state()

            # Discover available reciters
            await self._discover_reciters()

            # Load configuration from bot config
            await self._load_bot_configuration()

            # Start background tasks
            await self._start_background_tasks()

            # Get health monitor if available
            try:
                from ..core.health_monitor import HealthMonitor

                self._health_monitor = self._container.get(HealthMonitor)
            except (ImportError, AttributeError, Exception) as e:
                await self._logger.debug(
                    "Health monitor not available", {"error": str(e)}
                )
                self._health_monitor = None

            await self._logger.info(
                "Audio service initialized successfully",
                {
                    "available_reciters": len(self._available_reciters),
                    "default_reciter": self._config.default_reciter,
                    "cache_enabled": self._config.cache_enabled,
                    "restored_surah": self._current_state.current_position.surah_number,
                    "restored_position": f"{self._current_state.current_position.position_seconds:.1f}s",
                    "health_monitor": self._health_monitor is not None,
                },
            )

        except Exception as e:
            await self._logger.error(
                "Failed to initialize audio service", {"error": str(e)}
            )
            raise AudioError(
                "Audio service initialization failed",
                context={"operation": "initialization"},
                original_error=e,
            )

    async def shutdown(self) -> None:
        """Shutdown the audio service gracefully.

        Performs orderly shutdown including:
        - Stopping active playback
        - Disconnecting from voice channels
        - Canceling all background tasks
        - Final state persistence
        - Resource cleanup
        """
        await self._logger.info("Shutting down audio service")

        try:
            # Stop playback
            await self.stop_playback()

            # Disconnect from voice
            await self.disconnect()

            # Cancel background tasks
            tasks = [
                self._playback_task,
                self._monitoring_task,
                self._position_save_task,
            ]

            for task in tasks:
                if task and not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

            # Shutdown cache
            await self._cache.shutdown()

            # Shutdown state service
            try:
                state_service = self._container.get(SQLiteStateService)
                if state_service:
                    await state_service.shutdown()
            except Exception as e:
                await self._logger.warning(
                    "Failed to shutdown state service", {"error": str(e)}
                )

            await self._logger.info("Audio service shutdown complete")

        except Exception as e:
            await self._logger.error(
                "Error during audio service shutdown", {"error": str(e)}
            )

    async def connect_to_voice_channel(self, channel_id: int, guild_id: int) -> bool:
        """Connect to a voice channel with automatic retry and monitoring.

        Establishes voice connection with comprehensive error handling and validation.
        Includes automatic disconnection of existing connections and permission checks.

        Args:
            channel_id: Voice channel ID to connect to
            guild_id: Guild ID containing the channel

        Returns:
            bool: True if connection successful, False otherwise

        Raises:
            VoiceConnectionError: If connection fails due to various reasons:
                - Guild not found
                - Channel not found or invalid type
                - Missing permissions
                - Connection timeout
                - Connection validation failure
        """
        self._target_channel_id = channel_id
        self._guild_id = guild_id

        await self._logger.info(
            "Attempting voice channel connection",
            {
                "channel_id": channel_id,
                "guild_id": guild_id,
                "attempt": self._connection_attempts + 1,
            },
        )

        try:
            # Disconnect existing connection
            if self._voice_client and self._voice_client.is_connected():
                await self._voice_client.disconnect(force=True)
                await asyncio.sleep(2)  # Allow Discord to process disconnection

            # Get guild and channel
            guild = self._bot.get_guild(guild_id)
            if not guild:
                raise VoiceConnectionError(
                    f"Guild not found: {guild_id}",
                    guild_id=guild_id,
                    context={"operation": "guild_lookup"},
                )

            channel = guild.get_channel(channel_id)
            if not channel or not isinstance(channel, discord.VoiceChannel):
                raise VoiceConnectionError(
                    f"Voice channel not found: {channel_id}",
                    voice_channel_id=channel_id,
                    guild_id=guild_id,
                    context={"operation": "channel_lookup"},
                )

            # Check permissions
            if not channel.permissions_for(guild.me).connect:
                raise VoiceConnectionError(
                    f"Missing permission to connect to channel {channel_id}",
                    voice_channel_id=channel_id,
                    guild_id=guild_id,
                    context={
                        "operation": "permission_check",
                        "required_permission": "connect",
                    },
                )

            # Attempt connection with longer timeout for stability
            try:
                self._voice_client = await asyncio.wait_for(
                    channel.connect(reconnect=True),
                    timeout=max(
                        self._config.connection_timeout, 45
                    ),  # At least 45 seconds
                )
            except TimeoutError:
                raise VoiceConnectionError(
                    f"Connection timeout after {self._config.connection_timeout}s",
                    voice_channel_id=channel_id,
                    guild_id=guild_id,
                    context={"operation": "connection_timeout"},
                )

            # Validate connection
            if not self._voice_client or not self._voice_client.is_connected():
                raise VoiceConnectionError(
                    "Voice client connection validation failed",
                    voice_channel_id=channel_id,
                    guild_id=guild_id,
                    context={"operation": "connection_validation"},
                )

            # Update state
            self._current_state.is_connected = True
            self._current_state.voice_channel_id = channel_id
            self._current_state.guild_id = guild_id
            self._connection_attempts = 0
            


            await self._logger.info(
                "Successfully connected to voice channel",
                {
                    "channel_id": channel_id,
                    "guild_id": guild_id,
                    "channel_name": channel.name,
                },
            )



            return True

        except VoiceConnectionError:
            # Re-raise voice connection errors as-is
            self._connection_attempts += 1
            raise
        except Exception as e:
            self._connection_attempts += 1
            raise VoiceConnectionError(
                f"Unexpected error connecting to voice channel {channel_id}",
                voice_channel_id=channel_id,
                guild_id=guild_id,
                context={
                    "operation": "connection_attempt",
                    "attempt_number": self._connection_attempts,
                },
                original_error=e,
            )

    async def disconnect(self) -> None:
        """Disconnect from voice channel gracefully.

        Safely disconnects from the current voice channel, handles errors,
        and updates internal state to reflect the disconnection.
        """
        if self._voice_client:
            try:
                await self._voice_client.disconnect(force=True)
                await self._logger.info("Disconnected from voice channel")
                    
            except Exception as e:
                await self._logger.warning(
                    "Error disconnecting from voice channel", {"error": str(e)}
                )
            finally:
                self._voice_client = None
                self._current_state.is_connected = False
                self._current_state.voice_channel_id = None

    async def start_playback(
        self,
        reciter: str | None = None,
        surah_number: int | None = None,
        resume_position: bool = True,
    ) -> bool:
        """Start audio playback with specified parameters.

        Initiates audio playback with optional parameter overrides. Validates
        voice connection, updates playback state, and starts background playback loop.

        Args:
            reciter: Reciter name to use (uses current if None)
            surah_number: Surah number to play (uses current if None)
            resume_position: Whether to resume from saved position

        Returns:
            bool: True if playback started successfully

        Raises:
            AudioError: If not connected to voice channel or other playback issues
        """
        if not self._voice_client or not self._voice_client.is_connected():
            raise AudioError(
                "Cannot start playback: not connected to voice channel",
                context={"operation": "playback_start_validation"},
            )

        # Update playback parameters
        if reciter:
            await self.set_reciter(reciter)

        if surah_number:
            await self.set_surah(surah_number)

        # Stop any existing playback (this is a transition, not a real stop)
        await self.stop_playback(is_transition=True)

        # Start new playback task
        self._playback_task = asyncio.create_task(
            self._playback_loop(resume_position=resume_position)
        )

        await self._logger.info(
            "Started audio playback",
            {
                "reciter": self._current_state.current_reciter,
                "surah": self._current_state.current_position.surah_number,
                "resume_position": resume_position,
            },
        )
        


        return True

    async def stop_playback(self, is_transition: bool = False) -> None:
        """Stop audio playback immediately.

        Cancels the playback task, stops the voice client, and updates
        playback state to reflect the stopped status.

        Args:
            is_transition: If True, this is part of a transition (skip/change) and shouldn't log as a stop
        """
        if self._playback_task and not self._playback_task.done():
            self._playback_task.cancel()
            try:
                await self._playback_task
            except asyncio.CancelledError:
                pass

        if self._voice_client and self._voice_client.is_playing():
            self._voice_client.stop()

        self._current_state.is_playing = False
        self._current_state.is_paused = False

        await self._logger.info("Stopped audio playback")
        


    async def pause_playback(self) -> bool:
        """Disabled - 24/7 Quran bot should never be paused.

        This method is intentionally disabled to maintain continuous 24/7 operation.
        The bot is designed for uninterrupted Quran recitation.

        Returns:
            bool: False - pause is not allowed for 24/7 operation
        """
        await self._logger.warning(
            "Pause attempt blocked - 24/7 continuous playback only"
        )
        return False

    async def resume_playback(self) -> bool:
        """Disabled - 24/7 Quran bot should never need resuming as it never pauses.

        This method is intentionally disabled since the bot never pauses.
        For starting stopped playback, use start_playback() instead.

        Returns:
            bool: False - resume is not needed for 24/7 operation
        """
        await self._logger.warning(
            "Resume attempt ignored - bot should never be paused"
        )
        return False

    async def set_reciter(self, reciter: str) -> bool:
        """Change the current reciter and restart playback.

        Validates the reciter exists, updates internal state, and restarts
        playback if currently active. Only restarts if reciter actually changes.

        Args:
            reciter: Name of the reciter to switch to

        Returns:
            bool: True if reciter changed successfully

        Raises:
            ValidationError: If reciter not found in available reciters
        """
        # Validate reciter exists
        reciter_info = await self._get_reciter_info(reciter)
        if not reciter_info:
            raise ValidationError(
                f"Reciter not found: {reciter}",
                context={
                    "field_name": "reciter",
                    "field_value": reciter,
                    "available_reciters": [r.name for r in self._available_reciters],
                },
            )

        old_reciter = self._current_state.current_reciter

        # Only restart playback if reciter is actually changing
        if old_reciter == reciter:
            return True

        # Check if we're currently playing
        was_playing = self._current_state.is_playing

        # Update state
        self._current_state.current_reciter = reciter

        await self._logger.info(
            "Changed reciter",
            {
                "from": old_reciter,
                "to": reciter,
                "available_surahs": reciter_info.total_surahs,
            },
        )

        # If we were playing, restart playback with the new reciter
        if was_playing and self._voice_client and self._voice_client.is_connected():
            try:
                # Stop current playback and restart with new reciter (this is a transition)
                await self.stop_playback(is_transition=True)
                await self.start_playback(resume_position=False)
                await self._logger.info(
                    "Restarted playback for new reciter", {"reciter": reciter}
                )
            except Exception as e:
                await self._logger.error(
                    "Failed to restart playback for new reciter",
                    {"reciter": reciter, "error": str(e)},
                )
                # Still return True since state was updated successfully

        return True

    async def set_surah(self, surah_number: int) -> bool:
        """Change the current surah and restart playback.

        Validates the surah number, updates internal state, and restarts
        playback if currently active. Resets position to beginning of new surah.

        Args:
            surah_number: Surah number to jump to (1-114)

        Returns:
            bool: True if surah changed successfully

        Raises:
            ValidationError: If surah number is not between 1 and 114
        """
        if not (1 <= surah_number <= 114):
            raise ValidationError(
                f"Invalid surah number: {surah_number}",
                context={
                    "field_name": "surah_number",
                    "field_value": surah_number,
                    "validation_rule": "Must be between 1 and 114",
                },
            )

        old_surah = self._current_state.current_position.surah_number

        # Only restart playback if surah is actually changing
        if old_surah == surah_number:
            return True

        # Check if we're currently playing
        was_playing = self._current_state.is_playing

        # Update state
        self._current_state.current_position.surah_number = surah_number
        self._current_state.current_position.position_seconds = 0.0

        await self._logger.info(
            "Changed surah", {"from": old_surah, "to": surah_number}
        )

        # If we were playing, restart playback with the new surah
        if was_playing and self._voice_client and self._voice_client.is_connected():
            try:
                # Stop current playback and restart with new surah (this is a transition)
                await self.stop_playback(is_transition=True)
                await self.start_playback(resume_position=False)
                await self._logger.info(
                    "Restarted playback for new surah", {"surah": surah_number}
                )
            except Exception as e:
                await self._logger.error(
                    "Failed to restart playback for new surah",
                    {"surah": surah_number, "error": str(e)},
                )
                # Still return True since state was updated successfully

        return True

    async def set_volume(self, volume: float) -> bool:
        """Set playback volume.

        Updates volume level for current and future playback. Applies immediately
        to active audio source if currently playing.

        Args:
            volume: Volume level between 0.0 (silent) and 1.0 (maximum)

        Returns:
            bool: True if volume set successfully

        Raises:
            ValidationError: If volume is not between 0.0 and 1.0
        """
        if not (0.0 <= volume <= 1.0):
            raise ValidationError(
                f"Invalid volume level: {volume}",
                context={
                    "field_name": "volume",
                    "field_value": volume,
                    "validation_rule": "Must be between 0.0 and 1.0",
                },
            )

        old_volume = self._current_state.volume
        self._current_state.volume = volume

        # Apply volume to current playback if active
        if self._voice_client and hasattr(self._voice_client.source, "volume"):
            self._voice_client.source.volume = volume

        await self._logger.info("Changed volume", {"from": old_volume, "to": volume})

        return True

    async def set_playback_mode(self, mode: PlaybackMode) -> bool:
        """Set playback mode.

        Changes how tracks advance after completion:
        - NORMAL: Sequential progression through surahs
        - LOOP_TRACK: Repeat current surah indefinitely
        - LOOP_PLAYLIST: Loop back to surah 1 after reaching the end
        - SHUFFLE: Random surah selection

        Args:
            mode: Playback mode from PlaybackMode enum

        Returns:
            bool: True if mode set successfully
        """
        old_mode = self._current_state.mode
        self._current_state.mode = mode

        await self._logger.info(
            "Changed playback mode", {"from": old_mode.value, "to": mode.value}
        )

        return True

    async def get_playback_state(self) -> PlaybackState:
        """Get current playback state.

        Returns a deep copy of the current playback state including position,
        reciter, volume, mode, and connection status. Updates position if playing.

        Returns:
            PlaybackState: Deep copy of current playback state
        """
        # Update current position if playing
        if self._current_state.is_playing and self._track_start_time:
            current_time = asyncio.get_event_loop().time()
            elapsed = current_time - self._track_start_time
            self._current_state.current_position.position_seconds = max(0.0, elapsed)

        self._current_state.last_updated = datetime.now(UTC)
        return self._current_state.copy(deep=True)

    async def get_available_reciters(self) -> list[ReciterInfo]:
        """Get list of available reciters.

        Returns a copy of the discovered reciters list with information about
        each reciter including name, total surahs, and file count.

        Returns:
            list[ReciterInfo]: List of available reciter information
        """
        return self._available_reciters.copy()

    async def get_current_file_info(self) -> AudioFileInfo | None:
        """Get information about the currently playing file.

        Retrieves cached metadata for the currently playing audio file including
        duration, bitrate, and other technical information.

        Returns:
            AudioFileInfo | None: File information if available, None if not found
        """
        try:
            file_path = await self._get_current_audio_file_path()
            if not file_path:
                return None

            return await self._cache.get_file_info(
                file_path,
                self._current_state.current_reciter,
                self._current_state.current_position.surah_number,
            )
        except Exception as e:
            await self._logger.warning(
                "Failed to get current file info", {"error": str(e)}
            )
            return None

    async def _discover_reciters(self) -> None:
        """Discover available reciters from audio folder structure.

        Scans the audio base folder for subdirectories containing MP3 files,
        analyzes file naming patterns to determine surah counts, and builds
        the available reciters list. Optionally warms cache for default reciter.
        """
        await self._logger.info(
            "Discovering available reciters",
            {"audio_folder": str(self._config.audio_base_folder)},
        )

        self._available_reciters.clear()

        if not self._config.audio_base_folder.exists():
            await self._logger.warning(
                "Audio base folder does not exist",
                {"folder": str(self._config.audio_base_folder)},
            )
            return

        # Scan directories for reciters
        for item in self._config.audio_base_folder.iterdir():
            if item.is_dir():
                mp3_files = list(item.glob("*.mp3"))
                if mp3_files:
                    reciter_info = ReciterInfo(
                        name=item.name,
                        folder_name=item.name,
                        total_surahs=len(
                            [f for f in mp3_files if self._extract_surah_number(f.name)]
                        ),
                        file_count=len(mp3_files),
                        audio_quality=None,  # Could be detected from files
                        language="Arabic",
                    )
                    self._available_reciters.append(reciter_info)

        # Sort by name
        self._available_reciters.sort(key=lambda r: r.name)

        # Warm cache for default reciter
        if self._config.preload_metadata:
            default_reciter = await self._get_reciter_info(self._config.default_reciter)
            if default_reciter:
                await self._cache.warm_cache_for_reciter(
                    default_reciter, self._config.audio_base_folder
                )

        await self._logger.info(
            "Reciter discovery complete",
            {
                "reciters_found": len(self._available_reciters),
                "reciters": [r.name for r in self._available_reciters],
            },
        )

    async def _load_bot_configuration(self) -> None:
        """Load configuration from config service.

        Retrieves voice channel ID and guild ID from the bot configuration
        service for automatic connection management.
        """
        try:
            self._target_channel_id = get_target_channel_id()
            self._guild_id = get_guild_id()

            await self._logger.info(
                "Loaded bot configuration",
                {
                    "guild_id": self._guild_id,
                    "voice_channel_id": self._target_channel_id,
                },
            )
        except Exception as e:
            await self._logger.warning(
                "Failed to load bot configuration", {"error": str(e)}
            )

    async def _load_saved_state(self) -> None:
        """Load saved playback state from SQLiteStateService.

        Attempts to restore previous playback state from SQLite database
        including current surah, position, reciter, and playback mode.
        Falls back to defaults if loading fails.
        """
        try:
            state_service = self._container.get(SQLiteStateService)
            saved_data = await state_service.load_playback_state()

            if saved_data:
                # Convert SQLite data to PlaybackState objects
                current_position = saved_data.get("current_position", {})
                position = PlaybackPosition(
                    surah_number=current_position.get("surah_number", 1),
                    position_seconds=current_position.get("position_seconds", 0.0),
                    total_duration=current_position.get("total_duration"),
                    track_index=current_position.get("track_index", 0),
                    timestamp=datetime.now(UTC),
                )

                saved_state = PlaybackState(
                    is_playing=False,  # Always start stopped
                    is_paused=False,
                    current_reciter=saved_data.get(
                        "current_reciter", self._config.default_reciter
                    ),
                    current_position=position,
                    mode=PlaybackMode(saved_data.get("playback_mode", "normal")),
                    volume=saved_data.get("volume", 1.0),
                    voice_channel_id=saved_data.get("voice_channel_id"),
                    guild_id=saved_data.get("guild_id"),
                    last_updated=datetime.now(UTC),
                )

                # Update current state with saved data
                self._current_state = saved_state

                await self._logger.info(
                    "Loaded saved playback state from SQLite",
                    {
                        "surah": position.surah_number,
                        "position": f"{position.position_seconds:.1f}s",
                        "reciter": saved_state.current_reciter,
                        "mode": saved_state.mode.value,
                    },
                )
            else:
                await self._logger.info("No saved playback state found, using defaults")

        except Exception as e:
            await self._logger.warning(
                "Failed to load saved state, using defaults", {"error": str(e)}
            )
            # Keep the default state if loading fails

    async def _start_background_tasks(self) -> None:
        """Start background monitoring and maintenance tasks.

        Initiates background tasks for:
        - Connection monitoring and automatic reconnection
        - Periodic position saving for resume functionality
        """
        # Start monitoring task
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())

        # Start position saving task
        self._position_save_task = asyncio.create_task(self._position_save_loop())

        await self._logger.info("Started background tasks")

    async def _playback_loop(self, resume_position: bool = True) -> None:
        """Main playback loop for continuous audio playback.

        Manages the core playback cycle:
        1. Validates voice connection
        2. Gets current audio file and metadata
        3. Creates optimized audio source with FFmpeg
        4. Starts playback and monitors completion
        5. Advances to next track based on playback mode
        6. Repeats until cancelled

        Args:
            resume_position: Whether to resume from saved position on first track

        Raises:
            FFmpegError: If audio source creation fails
            AudioError: If playback fails
        """
        try:
            await self._logger.info("Starting playback loop")

            while True:
                # Validate voice connection
                if not self._voice_client or not self._voice_client.is_connected():
                    await self._logger.warning(
                        "Voice client disconnected, stopping playback"
                    )
                    break

                # Get current audio file
                file_path = await self._get_current_audio_file_path()
                if not file_path:
                    await self._logger.warning("No audio file found for current track")
                    await self._advance_to_next_track()
                    continue

                # Get file info
                file_info = await self._cache.get_file_info(
                    file_path,
                    self._current_state.current_reciter,
                    self._current_state.current_position.surah_number,
                )

                if not file_info:
                    await self._logger.warning(
                        "Failed to get file info", {"file": str(file_path)}
                    )
                    await self._advance_to_next_track()
                    continue

                # Create audio source
                try:
                    should_resume = (
                        resume_position
                        and self._current_state.current_position.position_seconds > 0
                    )
                    audio_source = await self._create_audio_source(
                        file_path,
                        should_resume,
                    )

                except Exception as e:
                    raise FFmpegError(
                        f"Failed to create audio source for {file_path}",
                        ffmpeg_command=f"{self._config.ffmpeg_path} -i {file_path}",
                        context={
                            "file_path": str(file_path),
                            "reciter": self._current_state.current_reciter,
                            "surah": self._current_state.current_position.surah_number,
                        },
                        original_error=e,
                    )

                # Start playback
                try:
                    self._voice_client.play(audio_source)
                    self._current_state.is_playing = True

                    # Set track start time for position tracking
                    current_time = asyncio.get_event_loop().time()
                    if (
                        resume_position
                        and self._current_state.current_position.position_seconds > 0
                    ):
                        # If resuming, store the original position and start tracking from now
                        self._resume_offset = (
                            self._current_state.current_position.position_seconds
                        )
                        self._track_start_time = current_time
                    else:
                        # Normal start from beginning
                        self._resume_offset = 0.0
                        self._track_start_time = current_time

                    self._last_successful_playback = datetime.now(UTC)

                    # Update position info
                    if file_info.duration_seconds:
                        self._current_state.current_position.total_duration = (
                            file_info.duration_seconds
                        )

                    await self._logger.info(
                        "Started playing track",
                        {
                            "file": file_path.name,
                            "reciter": self._current_state.current_reciter,
                            "surah": self._current_state.current_position.surah_number,
                            "duration": file_info.duration_seconds,
                        },
                    )

                    # Report audio activity to health monitor
                    if self._health_monitor:
                        await self._health_monitor.report_audio_activity(
                            "track_started",
                            {
                                "file": file_path.name,
                                "reciter": self._current_state.current_reciter,
                                "surah": self._current_state.current_position.surah_number,
                                "duration": file_info.duration_seconds,
                            },
                        )

                    # Wait for playback to complete
                    await self._wait_for_playback_completion()

                    # Reset resume flag after first track
                    resume_position = False

                except Exception as e:
                    raise AudioError(
                        f"Playback failed for {file_path}",
                        context={
                            "file_path": str(file_path),
                            "reciter": self._current_state.current_reciter,
                            "surah": self._current_state.current_position.surah_number,
                            "operation": "playback",
                        },
                        original_error=e,
                    )

                # Move to next track
                await self._advance_to_next_track()

        except asyncio.CancelledError:
            await self._logger.info("Playback loop cancelled")
            raise
        except Exception as e:
            await self._logger.error("Error in playback loop", {"error": str(e)})
            raise
        finally:
            self._current_state.is_playing = False
            self._track_start_time = None

    async def _create_audio_source(
        self, file_path: Path, resume: bool = False
    ) -> discord.AudioSource:
        """Create FFmpeg audio source with robust options for 24/7 stability.

        Configures FFmpeg with stability-focused options including:
        - Large buffer sizes for smooth playback
        - Reconnection options for network resilience
        - Timestamp handling for seamless audio
        - Resume capability from specific positions

        Args:
            file_path: Path to the audio file
            resume: Whether to resume from saved position

        Returns:
            discord.AudioSource: Configured FFmpeg audio source
        """
        ffmpeg_options = [
            "-vn",  # No video
            "-loglevel warning",
            f"-bufsize {self._config.playback_buffer_size}",
            "-avoid_negative_ts make_zero",  # Handle timestamp issues
            "-fflags +genpts",  # Generate timestamps
            "-thread_queue_size 512",  # Larger thread queue
        ]

        if self._config.enable_reconnection:
            ffmpeg_options.extend(
                [
                    "-reconnect 1",
                    "-reconnect_streamed 1",
                    "-reconnect_delay_max 10",  # Increased delay
                    "-reconnect_at_eof 1",  # Reconnect at end of file
                    "-multiple_requests 1",
                    "-rw_timeout 60000000",  # 60 second timeout (increased)
                    "-timeout 60000000",  # Connection timeout
                    "-user_agent 'QuranBot/4.0'",  # Custom user agent
                ]
            )

        before_options = []
        if resume and self._current_state.current_position.position_seconds > 0:
            before_options.append(
                f"-ss {self._current_state.current_position.position_seconds}"
            )

        return discord.FFmpegPCMAudio(
            str(file_path),
            executable=self._config.ffmpeg_path,
            before_options=" ".join(before_options) if before_options else None,
            options=" ".join(ffmpeg_options),
        )

    async def _wait_for_playback_completion(self) -> None:
        """Wait for current track to complete playback.

        Monitors playback status and updates position tracking while waiting
        for the current track to finish. Updates position every second.
        """
        while self._voice_client and self._voice_client.is_playing():
            await asyncio.sleep(1)

            # Update position
            if self._track_start_time:
                elapsed = asyncio.get_event_loop().time() - self._track_start_time
                # Add resume offset to the elapsed time for correct position tracking
                total_position = self._resume_offset + max(0.0, elapsed)
                self._current_state.current_position.position_seconds = total_position

    async def _advance_to_next_track(self) -> None:
        """Advance to the next track based on playback mode.

        Determines next track based on current playback mode:
        - LOOP_TRACK: Restarts current surah
        - SHUFFLE: Selects random different surah
        - NORMAL/LOOP_PLAYLIST: Sequential progression

        Updates position tracking and reports progression to health monitor.
        """
        current_surah = self._current_state.current_position.surah_number

        if self._current_state.mode == PlaybackMode.LOOP_TRACK:
            # Reset position for loop
            self._current_state.current_position.position_seconds = 0.0
            return

        elif self._current_state.mode == PlaybackMode.SHUFFLE:
            # Random surah
            reciter_info = await self._get_reciter_info(
                self._current_state.current_reciter
            )
            if reciter_info and reciter_info.total_surahs > 1:
                available_surahs = list(range(1, reciter_info.total_surahs + 1))
                available_surahs.remove(current_surah)  # Don't repeat current
                next_surah = random.choice(available_surahs)
                self._current_state.current_position.surah_number = next_surah

        else:
            # Normal progression
            next_surah = current_surah + 1
            reciter_info = await self._get_reciter_info(
                self._current_state.current_reciter
            )
            max_surah = reciter_info.total_surahs if reciter_info else 114

            if next_surah > max_surah:
                if self._current_state.mode == PlaybackMode.LOOP_PLAYLIST:
                    next_surah = 1  # Loop back to beginning
                else:
                    await self._logger.info("Reached end of playlist")
                    return

            self._current_state.current_position.surah_number = next_surah

        # Reset position for new track
        self._current_state.current_position.position_seconds = 0.0

        await self._logger.info(
            "Advanced to next track",
            {
                "from_surah": current_surah,
                "to_surah": self._current_state.current_position.surah_number,
                "mode": self._current_state.mode.value,
            },
        )

        # Report progression to health monitor
        if self._health_monitor:
            await self._health_monitor.report_audio_activity(
                "track_advanced",
                {
                    "from_surah": current_surah,
                    "to_surah": self._current_state.current_position.surah_number,
                    "mode": self._current_state.mode.value,
                },
            )

    async def _get_current_audio_file_path(self) -> Path | None:
        """Get the path to the current audio file.

        Constructs the file path based on current reciter and surah number,
        searching for MP3 files that match the expected naming pattern.

        Returns:
            Path | None: Path to audio file if found, None otherwise
        """
        reciter_folder = (
            self._config.audio_base_folder / self._current_state.current_reciter
        )
        if not reciter_folder.exists():
            return None

        surah_number = self._current_state.current_position.surah_number

        # Look for files that match the surah number
        for file_path in reciter_folder.glob("*.mp3"):
            if self._extract_surah_number(file_path.name) == surah_number:
                return file_path

        return None

    async def _get_reciter_info(self, reciter: str) -> ReciterInfo | None:
        """Get reciter information by name.

        Args:
            reciter: Name of the reciter to find

        Returns:
            ReciterInfo | None: Reciter information if found, None otherwise
        """
        for reciter_info in self._available_reciters:
            if reciter_info.name == reciter:
                return reciter_info
        return None

    def _extract_surah_number(self, filename: str) -> int | None:
        """Extract surah number from filename.

        Uses regex to find numeric patterns in filenames and validates
        they represent valid surah numbers (1-114).

        Args:
            filename: Audio filename to analyze

        Returns:
            int | None: Surah number if valid, None otherwise
        """
        match = re.search(r"(\d+)", filename)
        if match:
            surah_num = int(match.group(1))
            return surah_num if 1 <= surah_num <= 114 else None
        return None

    async def _monitoring_loop(self) -> None:
        """Enhanced background monitoring loop with aggressive reconnection for 24/7 stability.

        Provides comprehensive health monitoring including:
        - Voice connection health checks with WebSocket monitoring
        - Automatic reconnection with exponential backoff
        - Playback health monitoring and recovery
        - Audio stuck detection and recovery
        - Emergency webhook notifications for critical failures

        Uses aggressive reconnection strategies optimized for 24/7 operation
        with multiple retry attempts and escalating intervention levels.
        """
        consecutive_failures = 0
        max_consecutive_failures = 5
        base_retry_delay = 2  # Start with 2 seconds
        max_retry_delay = 30  # Cap at 30 seconds

        while True:
            try:
                # Less frequent health checks to avoid aggressive reconnection
                await asyncio.sleep(
                    min(self._health_check_interval, 30)
                )  # Increased from 10 to 30 seconds

                # Check voice connection health - only disconnect if clearly disconnected
                connection_lost = False
                if not self._voice_client or not self._voice_client.is_connected():
                    connection_lost = True
                # Removed aggressive WebSocket checking that was causing false disconnections

                if connection_lost:
                    consecutive_failures += 1
                    retry_delay = min(
                        base_retry_delay * (2 ** min(consecutive_failures - 1, 4)),
                        max_retry_delay,
                    )

                    await self._logger.warning(
                        "Voice connection lost, attempting aggressive reconnection",
                        {
                            "consecutive_failures": consecutive_failures,
                            "retry_delay": retry_delay,
                            "max_failures": max_consecutive_failures,
                        },
                    )

                    if self._target_channel_id and self._guild_id:
                        try:
                            # Force disconnect any existing connection
                            if self._voice_client:
                                try:
                                    await self._voice_client.disconnect(force=True)
                                except (
                                    discord.ConnectionClosed,
                                    discord.HTTPException,
                                    Exception,
                                ) as e:
                                    await self._logger.debug(
                                        "Error on forced disconnect (expected)",
                                        {"error": str(e)},
                                    )
                                await asyncio.sleep(1)  # Brief pause

                            # Attempt reconnection with retries
                            success = False
                            for attempt in range(
                                1
                            ):  # Reduced from 3 to 1 attempt per health check
                                try:
                                    await self.connect_to_voice_channel(
                                        self._target_channel_id, self._guild_id
                                    )
                                    success = True
                                    consecutive_failures = 0  # Reset on success

                                    # Resume playback if we were playing
                                    if (
                                        self._current_state.is_playing
                                        and not self._playback_task
                                    ):
                                        await self._logger.info(
                                            "Resuming playback after reconnection"
                                        )
                                        await self.start_playback(resume_position=True)
                                    break

                                except Exception as e:
                                    await self._logger.warning(
                                        f"Reconnection attempt {attempt + 1}/1 failed",
                                        {"error": str(e)},
                                    )
                                    # No sleep needed since we only try once

                            if not success:
                                await self._logger.error(
                                    "All reconnection attempts failed",
                                    {"consecutive_failures": consecutive_failures},
                                )

                                # Critical webhook for connection failures


                                # If we've failed too many times consecutively, take drastic action
                                if consecutive_failures >= max_consecutive_failures:
                                    await self._logger.critical(
                                        "Too many consecutive connection failures - requesting bot restart",
                                        {"consecutive_failures": consecutive_failures},
                                    )


                        except Exception as e:
                            await self._logger.error(
                                "Critical error in reconnection logic",
                                {
                                    "error": str(e),
                                    "consecutive_failures": consecutive_failures,
                                },
                            )

                    # Apply exponential backoff delay
                    await asyncio.sleep(retry_delay)
                elif consecutive_failures > 0:
                    await self._logger.info(
                        "Voice connection restored and stable",
                        {"was_failing_for": consecutive_failures},
                    )
                    consecutive_failures = 0



                # Additional health checks for 24/7 stability
                if self._voice_client and self._voice_client.is_connected():
                    # Check if we should be playing but aren't
                    if (
                        self._current_state.is_playing
                        and not self._voice_client.is_playing()
                    ):
                        await self._logger.warning(
                            "Audio should be playing but isn't - attempting restart"
                        )
                        try:
                            await self.start_playback(resume_position=True)
                        except Exception as e:
                            await self._logger.error(
                                "Failed to restart playback", {"error": str(e)}
                            )

                # Enhanced playback health monitoring
                time_since_playback = datetime.now(UTC) - self._last_successful_playback
                if time_since_playback.total_seconds() > 600:  # 10 minutes
                    await self._logger.warning(
                        "No successful playback in 10 minutes - attempting recovery",
                        {"last_playback": self._last_successful_playback.isoformat()},
                    )

                    # Report audio stuck to health monitor for webhook alert
                    if self._health_monitor:
                        await self._health_monitor.report_audio_activity(
                            "audio_stuck",
                            {
                                "last_playback": self._last_successful_playback.isoformat(),
                                "minutes_since_playback": time_since_playback.total_seconds()
                                / 60,
                                "current_surah": self._current_state.current_position.surah_number,
                                "is_connected": (
                                    self._voice_client.is_connected()
                                    if self._voice_client
                                    else False
                                ),
                                "is_playing": (
                                    self._voice_client.is_playing()
                                    if self._voice_client
                                    else False
                                ),
                                "consecutive_failures": consecutive_failures,
                            },
                        )

                    # Attempt recovery for stuck audio
                    if self._voice_client and self._voice_client.is_connected():
                        try:
                            await self._logger.info(
                                "Attempting audio recovery - restarting playback"
                            )
                            await self.start_playback(resume_position=True)
                        except Exception as e:
                            await self._logger.error(
                                "Audio recovery failed", {"error": str(e)}
                            )

            except asyncio.CancelledError:
                await self._logger.info("Audio monitoring cancelled")
                break
            except Exception as e:
                await self._logger.error(
                    "Error in audio monitoring loop", {"error": str(e)}
                )
                # Don't let monitoring loop die
                await asyncio.sleep(5)

    async def _position_save_loop(self) -> None:
        """Background loop to save playback position periodically.

        Saves current playback state to SQLite database every 5 seconds while
        playing, enabling seamless resume functionality across bot restarts.
        Also ensures final position is saved during shutdown.
        """
        while True:
            try:
                await asyncio.sleep(5)  # Save every 5 seconds

                if self._current_state.is_playing and self._voice_client:
                    try:
                        # Get current state service
                        state_service = self._container.get(SQLiteStateService)

                        # Prepare state data for SQLite
                        state_data = {
                            "current_position": {
                                "surah_number": self._current_state.current_position.surah_number,
                                "position_seconds": self._current_state.current_position.position_seconds,
                                "total_duration": self._current_state.current_position.total_duration,
                            },
                            "current_reciter": self._current_state.current_reciter,
                            "volume": self._current_state.volume,
                            "is_playing": self._current_state.is_playing,
                            "is_paused": self._current_state.is_paused,
                            "mode": self._current_state.mode.value,
                            "voice_channel_id": self._current_state.voice_channel_id,
                            "guild_id": self._current_state.guild_id,
                        }

                        # Save to SQLite with proper structure
                        await state_service.save_playback_state(state_data)

                        await self._logger.debug(
                            "Saved playback position",
                            {
                                "surah": state_data["current_position"]["surah_number"],
                                "position": f"{state_data['current_position']['position_seconds']:.1f}s",
                                "reciter": state_data["current_reciter"],
                            },
                        )

                    except Exception as e:
                        await self._logger.error(
                            "Failed to save playback position", {"error": str(e)}
                        )

            except asyncio.CancelledError:
                # Save final position before exiting
                try:
                    if self._current_state.is_playing:
                        state_service = self._container.get(SQLiteStateService)
                        state_data = {
                            "current_position": {
                                "surah_number": self._current_state.current_position.surah_number,
                                "position_seconds": self._current_state.current_position.position_seconds,
                                "total_duration": self._current_state.current_position.total_duration,
                            },
                            "current_reciter": self._current_state.current_reciter,
                            "volume": self._current_state.volume,
                            "is_playing": self._current_state.is_playing,
                            "is_paused": self._current_state.is_paused,
                            "mode": self._current_state.mode.value,
                            "voice_channel_id": self._current_state.voice_channel_id,
                            "guild_id": self._current_state.guild_id,
                        }
                        await state_service.save_playback_state(state_data)
                        await self._logger.info(
                            "Saved final playback position before shutdown"
                        )
                except Exception as e:
                    await self._logger.error(
                        "Failed to save final position", {"error": str(e)}
                    )
                break
            except Exception as e:
                await self._logger.error(
                    "Error in position save loop", {"error": str(e)}
                )
