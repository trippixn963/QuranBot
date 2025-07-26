# =============================================================================
# QuranBot - Modern Audio Service
# =============================================================================
# This module provides a modern, type-safe audio service with dependency
# injection, comprehensive error handling, and advanced features like caching,
# monitoring, and automatic recovery.
# =============================================================================

import asyncio
from datetime import UTC, datetime
from pathlib import Path
import random
import re

import discord
from discord.ext import commands

from src.config import ConfigService
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
    PlaybackPosition,
    PlaybackState,
    ReciterInfo,
)

from .metadata_cache import MetadataCache


class AudioService:
    """
    Modern audio service with dependency injection and type safety.

    This service provides comprehensive audio playback functionality including:
    - Voice channel connection management
    - Audio file playback with FFmpeg
    - Metadata caching for performance
    - Automatic error recovery
    - State persistence
    - Monitoring and health checks
    """

    def __init__(
        self,
        container: DIContainer,
        bot: commands.Bot,
        config: AudioServiceConfig,
        logger: StructuredLogger,
        metadata_cache: MetadataCache,
    ):
        """
        Initialize the audio service.

        Args:
            container: Dependency injection container
            bot: Discord bot instance
            config: Audio service configuration
            logger: Structured logger
            metadata_cache: Metadata cache service
        """
        self._container = container
        self._bot = bot
        self._config = config
        self._logger = logger
        self._cache = metadata_cache

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

    async def initialize(self) -> None:
        """Initialize the audio service"""
        await self._logger.info("Initializing audio service")

        try:
            # Initialize metadata cache
            await self._cache.initialize()

            # Discover available reciters
            await self._discover_reciters()

            # Load configuration from bot config
            await self._load_bot_configuration()

            # Start background tasks
            await self._start_background_tasks()

            await self._logger.info(
                "Audio service initialized successfully",
                {
                    "available_reciters": len(self._available_reciters),
                    "default_reciter": self._config.default_reciter,
                    "cache_enabled": self._config.cache_enabled,
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
        """Shutdown the audio service"""
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

            await self._logger.info("Audio service shutdown complete")

        except Exception as e:
            await self._logger.error(
                "Error during audio service shutdown", {"error": str(e)}
            )

    async def connect_to_voice_channel(self, channel_id: int, guild_id: int) -> bool:
        """
        Connect to a voice channel with automatic retry and monitoring.

        Args:
            channel_id: Voice channel ID to connect to
            guild_id: Guild ID containing the channel

        Returns:
            True if connection successful, False otherwise
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

            # Attempt connection with timeout
            try:
                self._voice_client = await asyncio.wait_for(
                    channel.connect(reconnect=True),
                    timeout=self._config.connection_timeout,
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
        """Disconnect from voice channel"""
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
        """
        Start audio playback with specified parameters.

        Args:
            reciter: Reciter name (uses current if None)
            surah_number: Surah to play (uses current if None)
            resume_position: Whether to resume from saved position

        Returns:
            True if playback started successfully
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

        # Stop any existing playback
        await self.stop_playback()

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

    async def stop_playback(self) -> None:
        """Stop audio playback"""
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
        """
        Pause audio playback.

        Returns:
            True if successfully paused
        """
        if not self._voice_client or not self._voice_client.is_playing():
            return False

        self._voice_client.pause()
        self._current_state.is_playing = False
        self._current_state.is_paused = True
        self._pause_timestamp = asyncio.get_event_loop().time()

        await self._logger.info("Paused audio playback")
        return True

    async def resume_playback(self) -> bool:
        """
        Resume audio playback.

        Returns:
            True if successfully resumed
        """
        if not self._voice_client or not self._voice_client.is_paused():
            return False

        self._voice_client.resume()
        self._current_state.is_playing = True
        self._current_state.is_paused = False

        # Adjust track start time for accurate position tracking
        if self._pause_timestamp and self._track_start_time:
            pause_duration = asyncio.get_event_loop().time() - self._pause_timestamp
            self._track_start_time += pause_duration

        self._pause_timestamp = None

        await self._logger.info("Resumed audio playback")
        return True

    async def set_reciter(self, reciter: str) -> bool:
        """
        Change the current reciter and restart playback.

        Args:
            reciter: Name of the reciter

        Returns:
            True if reciter changed successfully
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
                # Stop current playback and restart with new reciter
                await self.stop_playback()
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
        """
        Change the current surah and restart playback.

        Args:
            surah_number: Surah number (1-114)

        Returns:
            True if surah changed successfully
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
                # Stop current playback and restart with new surah
                await self.stop_playback()
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
        """
        Set playback volume.

        Args:
            volume: Volume level (0.0-1.0)

        Returns:
            True if volume set successfully
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
        """
        Set playback mode.

        Args:
            mode: Playback mode

        Returns:
            True if mode set successfully
        """
        old_mode = self._current_state.mode
        self._current_state.mode = mode

        await self._logger.info(
            "Changed playback mode", {"from": old_mode.value, "to": mode.value}
        )

        return True

    async def get_playback_state(self) -> PlaybackState:
        """Get current playback state"""
        # Update current position if playing
        if self._current_state.is_playing and self._track_start_time:
            current_time = asyncio.get_event_loop().time()
            elapsed = current_time - self._track_start_time
            self._current_state.current_position.position_seconds = max(0.0, elapsed)

        self._current_state.last_updated = datetime.now(UTC)
        return self._current_state.copy(deep=True)

    async def get_available_reciters(self) -> list[ReciterInfo]:
        """Get list of available reciters"""
        return self._available_reciters.copy()

    async def get_current_file_info(self) -> AudioFileInfo | None:
        """Get information about the currently playing file"""
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
        """Discover available reciters from audio folder structure"""
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
        """Load configuration from config service"""
        try:
            config_service = self._container.get(ConfigService)
            self._target_channel_id = config_service.get_voice_channel_id()
            self._guild_id = config_service.get_guild_id()

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

    async def _start_background_tasks(self) -> None:
        """Start background monitoring and maintenance tasks"""
        # Start monitoring task
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())

        # Start position saving task
        self._position_save_task = asyncio.create_task(self._position_save_loop())

        await self._logger.info("Started background tasks")

    async def _playback_loop(self, resume_position: bool = True) -> None:
        """Main playback loop"""
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
                    audio_source = await self._create_audio_source(
                        file_path,
                        resume_position
                        and self._current_state.current_position.position_seconds > 0,
                    )
                    resume_position = False  # Only resume once

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
                    self._track_start_time = asyncio.get_event_loop().time()
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

                    # Wait for playback to complete
                    await self._wait_for_playback_completion()

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
        """Create FFmpeg audio source with proper options"""
        ffmpeg_options = [
            "-vn",  # No video
            "-loglevel warning",
            f"-bufsize {self._config.playback_buffer_size}",
        ]

        if self._config.enable_reconnection:
            ffmpeg_options.extend(
                [
                    "-reconnect 1",
                    "-reconnect_streamed 1",
                    "-reconnect_delay_max 5",
                    "-multiple_requests 1",
                    "-rw_timeout 30000000",
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
        """Wait for current track to complete playback"""
        while self._voice_client and self._voice_client.is_playing():
            await asyncio.sleep(1)

            # Update position
            if self._track_start_time:
                elapsed = asyncio.get_event_loop().time() - self._track_start_time
                self._current_state.current_position.position_seconds = elapsed

    async def _advance_to_next_track(self) -> None:
        """Advance to the next track based on playback mode"""
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

    async def _get_current_audio_file_path(self) -> Path | None:
        """Get the path to the current audio file"""
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
        """Get reciter information by name"""
        for reciter_info in self._available_reciters:
            if reciter_info.name == reciter:
                return reciter_info
        return None

    def _extract_surah_number(self, filename: str) -> int | None:
        """Extract surah number from filename"""
        match = re.search(r"(\d+)", filename)
        if match:
            surah_num = int(match.group(1))
            return surah_num if 1 <= surah_num <= 114 else None
        return None

    async def _monitoring_loop(self) -> None:
        """Background monitoring loop for health checks"""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)

                # Check voice connection health
                if self._voice_client and not self._voice_client.is_connected():
                    await self._logger.warning(
                        "Voice connection lost, attempting reconnection"
                    )

                    if self._target_channel_id and self._guild_id:
                        try:
                            await self.connect_to_voice_channel(
                                self._target_channel_id, self._guild_id
                            )
                        except Exception as e:
                            await self._logger.error(
                                "Failed to reconnect to voice channel",
                                {"error": str(e)},
                            )

                # Check playback health
                time_since_playback = datetime.now(UTC) - self._last_successful_playback
                if time_since_playback.total_seconds() > 600:  # 10 minutes
                    await self._logger.warning(
                        "No successful playback in 10 minutes",
                        {"last_playback": self._last_successful_playback.isoformat()},
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                await self._logger.error("Error in monitoring loop", {"error": str(e)})

    async def _position_save_loop(self) -> None:
        """Background loop to save playback position"""
        while True:
            try:
                await asyncio.sleep(5)  # Save every 5 seconds

                if self._current_state.is_playing:
                    # Save current state (implementation would use state manager)
                    pass

            except asyncio.CancelledError:
                break
            except Exception as e:
                await self._logger.error(
                    "Error in position save loop", {"error": str(e)}
                )
