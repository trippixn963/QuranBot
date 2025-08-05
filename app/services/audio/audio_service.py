# =============================================================================
# QuranBot - Audio Service
# =============================================================================
# audio service with robust retry mechanisms, comprehensive error handling,
# and advanced voice connection management for 24/7 Quran bot operation.
# =============================================================================

import asyncio
import json
import os
import random
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import discord
from mutagen.mp3 import MP3

from ...config import get_config
from ...config.timezone import APP_TIMEZONE
from ...core.errors import (
    AudioError,
    DiscordAPIError,
    ErrorCategory,
    ErrorHandler,
    ErrorSeverity,
    NetworkError,
    ResourceError,
    ValidationError,
)
from ...core.logger import TreeLogger, log_event
from ...core.validation import (
    CompositeValidator,
    DependencyValidator,
    FileSystemValidator,
)
from ...data.models import AudioFileInfo
from ..core.base_service import BaseService

# Commands removed - using discord.Client instead



class PlaybackState:
    """playback state enumeration."""

    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    BUFFERING = "buffering"
    ERROR = "error"


class AudioService(BaseService):
    """
    audio service with robust retry mechanisms and comprehensive error handling.
    Manages Quran audio playback, voice connections, and audio file management.
    """

    def __init__(self, bot: discord.Client):
        """
        Initialize audio service with error handling and retry logic.

        Args:
            bot: Discord bot instance for voice operations
        """
        # Initialize base service (logger and error handler are optional now)
        super().__init__("AudioService")

        self.bot = bot
        self.config = get_config()
        self.state_service = None  # Will be set during initialization

        # voice connection management
        self.voice_client: Optional[discord.VoiceClient] = None
        self.current_voice_channel_id: Optional[int] = None
        self.is_connected = False
        self.connection_retry_count = 0
        self.last_connection_error: Optional[datetime] = None
        self.reconnect_task: Optional[asyncio.Task] = None

        # audio playback management
        self.current_audio: Optional[AudioFileInfo] = None
        self.current_surah: Optional[int] = None
        self.current_reciter: Optional[str] = None
        self.current_volume = 1.0
        self.playback_state = PlaybackState.STOPPED
        self.loop_mode = "off"  # off, single, all
        self.shuffle_enabled = False

        # Position tracking
        self.playback_start_time: Optional[float] = None
        self.pause_time: Optional[float] = None
        self.paused_duration: float = 0.0
        self.current_duration: float = 0.0

        # audio library management
        self.available_reciters: Dict[str, Dict[str, Any]] = {}
        self.audio_files_cache: Dict[str, Dict[int, AudioFileInfo]] = {}

        # Continuous playback management
        self.continuous_playback_task: Optional[asyncio.Task] = None
        self.current_surah_index = 1
        # Ensure we get the string value from the enum
        self.current_reciter_name = (
            str(self.config.default_reciter.value)
            if hasattr(self.config.default_reciter, "value")
            else str(self.config.default_reciter)
        )
        self.manual_control_active = (
            False  # Flag to pause auto-monitoring during manual interactions
        )
        self._jump_occurred = False  # Flag to prevent auto-advance after manual jumps

        # Performance monitoring
        self.playback_stats = {
            "total_playbacks": 0,
            "successful_playbacks": 0,
            "failed_playbacks": 0,
            "total_duration_seconds": 0.0,
            "average_playback_duration": 0.0,
            "last_playback_time": None,
        }

        # Connection health monitoring
        self.connection_health = {
            "total_connections": 0,
            "successful_connections": 0,
            "failed_connections": 0,
            "average_connection_time": 0.0,
            "last_connection_time": None,
            "connection_stability_score": 100.0,
        }

    async def _initialize(self) -> None:
        """Initialize audio service with retry mechanisms."""
        TreeLogger.section(
            "Initializing audio service with error handling", service="AudioService"
        )

        try:
            # Validate audio folder structure with retry
            await self._retry_operation(
                operation=self._validate_audio_folder,
                operation_name="audio_folder_validation",
                context={
                    "service_name": "AudioService",
                    "audio_folder": self.config.audio_folder,
                },
            )

            # Discover available reciters with retry
            await self._retry_operation(
                operation=self._discover_reciters,
                operation_name="reciter_discovery",
                context={
                    "service_name": "AudioService",
                    "audio_folder": str(self.config.audio_folder),
                },
            )

            # Validate FFmpeg installation with retry
            await self._retry_operation(
                operation=self._validate_ffmpeg,
                operation_name="ffmpeg_validation",
                context={
                    "service_name": "AudioService",
                    "ffmpeg_path": self.config.ffmpeg_path,
                },
            )

            # Connect to state service and restore last position
            await self._restore_playback_state()

            TreeLogger.success(
                "Audio service initialization complete with error handling",
                service="AudioService",
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "audio_service_initialization",
                    "service_name": "AudioService",
                    "audio_folder": self.config.audio_folder,
                    "ffmpeg_path": self.config.ffmpeg_path,
                },
            )
            raise AudioError(
                f"Failed to initialize audio service: {e}",
                operation="initialize",
                severity=ErrorSeverity.CRITICAL,
            )

    async def _start(self) -> None:
        """Start audio service with connection management."""
        TreeLogger.section(
            "Starting audio service with robust connection handling",
            service="AudioService",
        )

        try:
            TreeLogger.info(
                "Audio service started - voice connection will be established after bot is ready",
                service="AudioService",
            )
            TreeLogger.success(
                "Audio service started successfully with error handling",
                service="AudioService",
            )

        except Exception as e:
            TreeLogger.error(
                f"Failed to start audio service: {e}", service="AudioService"
            )
            raise

    async def _stop(self) -> None:
        """Stop audio service with cleanup."""
        TreeLogger.section(
            "Stopping audio service with comprehensive cleanup", service="AudioService"
        )

        try:
            # Save current position before stopping
            await self._save_current_position()

            # Stop any ongoing playback with retry
            await self._retry_operation(
                operation=self._stop_playback,
                operation_name="playback_stop",
                context={
                    "service_name": "AudioService",
                    "current_playback_state": self.playback_state,
                },
            )

            # Disconnect from voice channel with retry
            await self._retry_operation(
                operation=self._disconnect_voice,
                operation_name="voice_disconnection",
                context={
                    "service_name": "AudioService",
                    "voice_channel_id": self.current_voice_channel_id,
                },
            )

            # Cancel reconnection task if running
            if self.reconnect_task and not self.reconnect_task.done():
                self.reconnect_task.cancel()
                try:
                    await self.reconnect_task
                except asyncio.CancelledError:
                    pass

            # Cancel continuous playback task if running
            if (
                self.continuous_playback_task
                and not self.continuous_playback_task.done()
            ):
                self.continuous_playback_task.cancel()
                try:
                    await asyncio.wait_for(self.continuous_playback_task, timeout=5.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass

            TreeLogger.success(
                "Audio service stopped successfully with cleanup",
                service="AudioService",
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "audio_service_shutdown",
                    "service_name": "AudioService",
                    "playback_state": self.playback_state,
                },
            )
            raise AudioError(
                f"Failed to stop audio service: {e}",
                operation="stop",
                severity=ErrorSeverity.WARNING,
            )

    async def connect_and_start_playback(self) -> None:
        """Connect to voice channel and start continuous playback after bot is ready."""
        try:
            TreeLogger.section(
                "Connecting to voice channel and starting playback",
                service="AudioService",
            )

            # Connect to voice channel if configured with retry
            if self.config.voice_channel_id:
                TreeLogger.info(
                    f"Attempting to connect to voice channel {self.config.voice_channel_id}",
                    service="AudioService",
                )

                await self._retry_operation(
                    operation=lambda: self._connect_to_voice_channel(
                        self.config.voice_channel_id
                    ),
                    operation_name="voice_channel_connection",
                    context={
                        "service_name": "AudioService",
                        "voice_channel_id": self.config.voice_channel_id,
                        "guild_id": self.config.guild_id,
                    },
                    max_retries=3,
                )

                # Start continuous playback task
                await self._start_continuous_playback()

                TreeLogger.success(
                    "Voice connection and playback started successfully",
                    service="AudioService",
                )
            else:
                TreeLogger.warning(
                    "No voice channel configured", service="AudioService"
                )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "connect_and_start_playback",
                    "service_name": "AudioService",
                },
            )

    async def _start_continuous_playback(self) -> None:
        """Start continuous 24/7 Quran audio playback."""
        try:
            TreeLogger.section(
                "Starting continuous 24/7 Quran audio playback", service="AudioService"
            )

            # Start the continuous playback task
            self.continuous_playback_task = asyncio.create_task(
                self._continuous_playback_loop()
            )

            TreeLogger.success(
                "Continuous playback task started successfully", service="AudioService"
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "start_continuous_playback",
                    "service_name": "AudioService",
                },
            )
            raise AudioError(
                f"Failed to start continuous playback: {e}",
                operation="start_continuous_playback",
            )

    async def _continuous_playback_loop(self) -> None:
        """
        Main loop for continuous 24/7 Quran audio playback.

        This is the core method that enables 24/7 Quran audio streaming. It handles:
        - Continuous surah playback in sequence (1-114)
        - Automatic reconnection on voice channel disconnection
        - Playback state management and monitoring
        - Error recovery and retry logic
        - State persistence between surahs
        - Timeout protection for stuck playback

        The loop runs indefinitely until the service is stopped or cancelled.
        """
        try:
            TreeLogger.section(
                "Starting continuous playback loop", service="AudioService"
            )

            # MAIN LOOP: Continuous 24/7 playback until service shutdown
            while True:
                try:
                    # STEP 0: Manual Control Check
                    # Skip entire loop iteration if manual control is active
                    if self.manual_control_active:
                        TreeLogger.debug(
                            "Skipping main loop iteration - manual control active",
                            service="AudioService",
                        )
                        await asyncio.sleep(1)
                        continue

                    # STEP 1: Connection Health Check
                    # Verify voice connection is still active before attempting playback
                    if not self.is_connected or not self.voice_client:
                        TreeLogger.error(
                            "Voice connection lost, attempting to reconnect",
                            service="AudioService",
                        )

                        # STEP 2: Automatic Reconnection
                        # Attempt to reconnect to voice channel with retry logic
                        reconnection_success = await self.reconnect_voice()

                        if not reconnection_success:
                            TreeLogger.error(
                                "Failed to reconnect to voice channel, waiting before retry",
                                service="AudioService",
                            )
                            # Wait longer before retrying reconnection to avoid spam
                            await asyncio.sleep(30)  # Wait 30 seconds before retrying
                            continue

                        # STEP 3: Post-Reconnection Processing
                        # If reconnection was successful, continue with playback
                        TreeLogger.success(
                            "Successfully reconnected to voice channel",
                            service="AudioService",
                        )
                        await asyncio.sleep(2)  # Brief pause after reconnection
                        continue

                    # STEP 4: Audio File Validation
                    # Get current surah audio file and validate it exists
                    audio_file = await self._get_audio_file(
                        self.current_surah_index, self.current_reciter_name
                    )

                    if not audio_file:
                        TreeLogger.error(
                            f"No audio file found for surah {self.current_surah_index}",
                            service="AudioService",
                        )
                        # Move to next surah if current one is missing
                        self.current_surah_index = (self.current_surah_index % 114) + 1
                        self.current_surah = (
                            self.current_surah_index
                        )  # Keep both variables in sync
                        continue

                    # STEP 5: Start Surah Playback
                    # Play the current surah with comprehensive logging
                    TreeLogger.success(
                        f"Playing surah {self.current_surah_index} by {self.current_reciter_name}",
                        service="AudioService",
                    )

                    # Add formatted info log for user visibility
                    TreeLogger.info(
                        f"🎵 Now playing: Surah {self.current_surah_index} by {self.current_reciter_name}",
                        service="AudioService",
                    )

                    success = await self.play_surah(
                        self.current_surah_index, self.current_reciter_name
                    )

                    if success:
                        # STEP 6: State Persistence
                        # Save state when starting a new surah for recovery
                        await self._save_current_position()

                        # STEP 7: Playback Monitoring Loop
                        # Wait for playback to complete with timeout protection
                        start_time = time.time()
                        timeout_seconds = (
                            600  # 10 minutes max per surah (prevents infinite hanging)
                        )

                        TreeLogger.section(
                            f"Waiting for surah {self.current_surah_index} to complete...",
                            service="AudioService",
                        )

                        # MONITORING LOOP: Track playback state until completion
                        # Give audio 3 seconds to start before checking is_playing()
                        await asyncio.sleep(3)

                        while self.playback_state == PlaybackState.PLAYING:
                            await asyncio.sleep(1)  # Check every second

                            # CRITICAL: Skip monitoring if manual control is active
                            if self.manual_control_active:
                                TreeLogger.debug(
                                    "Skipping monitoring - manual control active",
                                    service="AudioService",
                                )
                                # Wait longer during manual control to avoid rapid checking
                                await asyncio.sleep(2)
                                continue

                            # STEP 8: Voice Client Health Check
                            # Verify Discord voice client is still actively playing
                            # Only trigger completion if manual control is not active
                            if (
                                self.voice_client
                                and not self.voice_client.is_playing()
                                and not self.manual_control_active
                            ):
                                TreeLogger.success(
                                    f"Voice client stopped playing surah {self.current_surah_index}",
                                    service="AudioService",
                                )
                                self.playback_state = PlaybackState.STOPPED
                                break

                            # STEP 9: Timeout Protection
                            # Prevent infinite hanging if playback gets stuck
                            if time.time() - start_time > timeout_seconds:
                                TreeLogger.error(
                                    f"Playback timeout for surah {self.current_surah_index}",
                                    service="AudioService",
                                )
                                if self.voice_client and self.voice_client.is_playing():
                                    self.voice_client.stop()  # Force stop stuck playback
                                self.playback_state = PlaybackState.STOPPED
                                break

                        # STEP 10: Surah Completion Processing
                        # Log completion and prepare for next surah
                        TreeLogger.success(
                            f"Completed surah {self.current_surah_index}, moving to next surah",
                            service="AudioService",
                        )

                        # Add formatted info log for user visibility
                        TreeLogger.info(
                            f"✅ Completed Surah {self.current_surah_index}, moving to next surah...",
                            service="AudioService",
                        )

                        # STEP 11: Surah Progression
                        # Check loop mode and shuffle mode
                        if self.loop_mode == "single":
                            # Stay on the same surah when looping single
                            TreeLogger.info(
                                f"Loop mode is 'single', replaying surah {self.current_surah_index}",
                                service="AudioService",
                            )
                        elif self.shuffle_enabled:
                            # Random surah selection in shuffle mode
                            old_surah = self.current_surah_index
                            # Keep trying until we get a different surah
                            while self.current_surah_index == old_surah:
                                self.current_surah_index = random.randint(1, 114)
                            self.current_surah = self.current_surah_index
                            TreeLogger.info(
                                f"Shuffle mode: randomly selected surah {self.current_surah_index}",
                                service="AudioService",
                            )
                        else:
                            # Sequential progression (normal mode)
                            self.current_surah_index = (
                                self.current_surah_index % 114
                            ) + 1
                            self.current_surah = (
                                self.current_surah_index
                            )  # Keep both variables in sync

                        # STEP 12: State Persistence After Completion
                        # Save current position after moving to next surah
                        await self._save_current_position()

                        # STEP 13: Inter-Surah Delay
                        # Small delay between surahs for smooth transitions
                        await asyncio.sleep(2)
                    else:
                        # STEP 14: Playback Failure Handling
                        # If surah playback fails, wait before retrying
                        TreeLogger.error(
                            f"Failed to play surah {self.current_surah_index}",
                            service="AudioService",
                        )
                        await asyncio.sleep(5)  # Wait before retrying

                # STEP 15: Graceful Shutdown Handling
                # Handle cancellation when service is being stopped
                except asyncio.CancelledError:
                    TreeLogger.section(
                        "Continuous playback loop cancelled", service="AudioService"
                    )
                    break
                # STEP 16: Error Recovery
                # Catch any other exceptions and continue playback
                except Exception as e:
                    await self.error_handler.handle_error(
                        e,
                        {
                            "operation": "continuous_playback_loop",
                            "current_surah": self.current_surah_index,
                            "current_reciter": self.current_reciter_name,
                        },
                    )
                    await asyncio.sleep(10)  # Wait before retrying

        # STEP 17: Outer Exception Handling
        # Final error handling for the entire loop
        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "continuous_playback_loop",
                    "service_name": "AudioService",
                },
            )

    async def _cleanup(self) -> None:
        """Clean up audio service resources with error handling."""
        TreeLogger.section(
            "Cleaning up audio service resources", service="AudioService"
        )

        try:
            # Clear caches with validation
            self.available_reciters.clear()
            self.audio_files_cache.clear()

            # Reset state with logging
            self.current_audio = None
            self.playback_state = PlaybackState.STOPPED
            self.is_connected = False

            # Reset continuous playback state
            self.continuous_playback_task = None
            self.current_surah_index = 1
            # Ensure we get the string value from the enum
            self.current_reciter_name = (
                str(self.config.default_reciter.value)
                if hasattr(self.config.default_reciter, "value")
                else str(self.config.default_reciter)
            )

            # Reset performance metrics
            self.playback_stats = {
                "total_playbacks": 0,
                "successful_playbacks": 0,
                "failed_playbacks": 0,
                "total_duration_seconds": 0.0,
                "average_playback_duration": 0.0,
                "last_playback_time": None,
            }

            # Reset connection health
            self.connection_health = {
                "total_connections": 0,
                "successful_connections": 0,
                "failed_connections": 0,
                "average_connection_time": 0.0,
                "last_connection_time": None,
                "connection_stability_score": 100.0,
            }

            TreeLogger.success(
                "Audio service cleanup complete with resource management",
                service="AudioService",
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {"operation": "audio_service_cleanup", "service_name": "AudioService"},
            )
            raise AudioError(
                f"Failed to cleanup audio service: {e}",
                operation="cleanup",
                severity=ErrorSeverity.WARNING,
            )

    async def _health_check(self) -> Dict[str, Any]:
        """Perform comprehensive audio service health check."""
        try:
            # Basic health metrics
            health_data = {
                "voice_connected": self.is_connected,
                "voice_channel_id": self.current_voice_channel_id,
                "playback_state": self.playback_state,
                "current_reciter": self.current_reciter,
                "current_surah": self.current_surah,
                "available_reciters": len(self.available_reciters),
                "cached_audio_files": sum(
                    len(files) for files in self.audio_files_cache.values()
                ),
                "connection_retry_count": self.connection_retry_count,
                "last_connection_error": (
                    self.last_connection_error.isoformat()
                    if self.last_connection_error
                    else None
                ),
                # performance metrics
                "playback_stats": self.playback_stats,
                "connection_health": self.connection_health,
                # Resource usage
                "current_volume": self.current_volume,
                "audio_cache_size": len(self.audio_files_cache),
                "voice_client_status": (
                    self.voice_client.is_connected() if self.voice_client else False
                ),
            }

            # Calculate health score
            health_score = self._calculate_audio_health_score(health_data)
            health_data["health_score"] = health_score
            health_data["is_healthy"] = health_score >= 70.0

            return health_data

        except Exception as e:
            await self.error_handler.handle_error(
                e, {"operation": "audio_health_check", "service_name": "AudioService"}
            )

            return {
                "voice_connected": False,
                "playback_state": PlaybackState.ERROR,
                "health_score": 0.0,
                "is_healthy": False,
                "error": str(e),
            }

    def _calculate_audio_health_score(self, health_data: Dict[str, Any]) -> float:
        """Calculate comprehensive audio health score."""
        score = 100.0

        # Deduct points for connection issues
        if not health_data.get("voice_connected", False):
            score -= 20

        # Deduct points for playback errors
        if health_data.get("playback_state") == PlaybackState.ERROR:
            score -= 15

        # Deduct points for high retry count
        retry_count = health_data.get("connection_retry_count", 0)
        if retry_count > 0:
            score -= min(retry_count * 3, 15)

        # Deduct points for poor playback performance
        playback_stats = health_data.get("playback_stats", {})
        failed_playbacks = playback_stats.get("failed_playbacks", 0)
        total_playbacks = playback_stats.get("total_playbacks", 0)

        if total_playbacks > 0:
            failure_rate = failed_playbacks / total_playbacks
            score -= failure_rate * 25

        # Deduct points for connection instability
        connection_health = health_data.get("connection_health", {})
        stability_score = connection_health.get("connection_stability_score", 100.0)
        score -= (100.0 - stability_score) * 0.3

        return max(score, 0.0)

    # =========================================================================
    # State Management
    # =========================================================================

    async def _get_state_service(self):
        """Get state service from the bot's container."""
        if not self.state_service:
            self.state_service = self.bot.get_service("state")
        return self.state_service

    async def _restore_playback_state(self) -> None:
        """Restore playback state from saved data with comprehensive error handling."""
        try:
            TreeLogger.section(
                "Restoring playback state from saved data", service="AudioService"
            )

            state_service = await self._get_state_service()
            if not state_service:
                default_reciter_str = (
                    str(self.config.default_reciter.value)
                    if hasattr(self.config.default_reciter, "value")
                    else str(self.config.default_reciter)
                )
                TreeLogger.warning(
                    "State service not available, using default settings",
                    {"default_reciter": default_reciter_str, "default_surah": 1},
                    service="AudioService",
                )
                return

            # Get current state (BotState object)
            current_state = state_service.get_state()
            if not current_state:
                default_reciter_str = (
                    str(self.config.default_reciter.value)
                    if hasattr(self.config.default_reciter, "value")
                    else str(self.config.default_reciter)
                )
                TreeLogger.info(
                    "No saved state found, using default settings",
                    {"default_reciter": default_reciter_str, "default_surah": 1},
                    service="AudioService",
                )
                return

            # Restore current reciter (only if different from default)
            if (
                hasattr(current_state, "current_reciter")
                and current_state.current_reciter
            ):
                saved_reciter = current_state.current_reciter
                default_reciter_str = (
                    str(self.config.default_reciter.value)
                    if hasattr(self.config.default_reciter, "value")
                    else str(self.config.default_reciter)
                )
                if saved_reciter != default_reciter_str:
                    # Verify the saved reciter is available
                    if saved_reciter in self.available_reciters:
                        self.current_reciter_name = saved_reciter
                        TreeLogger.success(
                            f"Restored saved reciter: {self.current_reciter_name}",
                            {
                                "saved_reciter": saved_reciter,
                                "default_reciter": default_reciter_str,
                            },
                            service="AudioService",
                        )
                    else:
                        TreeLogger.warning(
                            f"Saved reciter '{saved_reciter}' not available, using default",
                            {
                                "saved_reciter": saved_reciter,
                                "default_reciter": default_reciter_str,
                                "available_reciters": list(
                                    self.available_reciters.keys()
                                ),
                            },
                            service="AudioService",
                        )
                else:
                    TreeLogger.info(
                        f"Using default reciter: {default_reciter_str}",
                        service="AudioService",
                    )

            # Restore current position
            if (
                hasattr(current_state, "current_position")
                and current_state.current_position
            ):
                position = current_state.current_position
                if hasattr(position, "surah") and position.surah:
                    saved_surah = position.surah
                    # Validate surah number
                    if 1 <= saved_surah <= 114:
                        self.current_surah_index = saved_surah
                        TreeLogger.success(
                            f"Restored playback position: Surah {self.current_surah_index}",
                            {
                                "restored_surah": self.current_surah_index,
                                "reciter": self.current_reciter_name,
                                "timestamp": (
                                    position.timestamp.isoformat()
                                    if hasattr(position, "timestamp")
                                    and position.timestamp
                                    else "unknown"
                                ),
                            },
                            service="AudioService",
                        )
                    else:
                        TreeLogger.warning(
                            f"Invalid saved surah number: {saved_surah}, starting from Surah 1",
                            service="AudioService",
                        )

            # Log final restoration summary
            TreeLogger.success(
                "Playback state restoration completed",
                {
                    "final_reciter": self.current_reciter_name,
                    "final_surah": self.current_surah_index,
                    "restoration_successful": True,
                },
                service="AudioService",
            )

        except Exception as e:
            default_reciter_str = (
                str(self.config.default_reciter.value)
                if hasattr(self.config.default_reciter, "value")
                else str(self.config.default_reciter)
            )
            TreeLogger.error(
                f"Failed to restore playback state: {e}",
                None,
                {
                    "error_type": type(e).__name__,
                    "fallback_reciter": default_reciter_str,
                    "fallback_surah": 1,
                },
                service="AudioService",
            )
            # Ensure we have valid defaults even if restoration fails
            self.current_reciter_name = default_reciter_str
            self.current_surah_index = 1

    async def _save_current_position(self) -> None:
        """Save current playback position to state with comprehensive error handling."""
        try:
            state_service = await self._get_state_service()
            if not state_service:
                TreeLogger.warning(
                    "State service not available, cannot save position",
                    service="AudioService",
                )
                return

            # Import the required classes from data models
            from ...data.models import PlaybackPosition, PlaybackState

            # Create position data object
            position_data = PlaybackPosition(
                surah=self.current_surah_index,
                position_seconds=0.0,  # For 24/7 stream, we restart each surah
                total_duration_seconds=None,
                timestamp=datetime.now(APP_TIMEZONE),
            )

            # Convert string playback state to enum if necessary
            if isinstance(self.playback_state, str):
                try:
                    playback_state_enum = PlaybackState(self.playback_state)
                except ValueError:
                    playback_state_enum = PlaybackState.STOPPED
            else:
                playback_state_enum = self.playback_state

            # Update state using the correct API
            await state_service.update_state(
                current_reciter=self.current_reciter_name,
                current_position=position_data,
                playback_state=playback_state_enum,
                last_activity=datetime.now(APP_TIMEZONE),
            )

            TreeLogger.success(
                f"Saved current position: Surah {self.current_surah_index}",
                {
                    "surah": self.current_surah_index,
                    "reciter": self.current_reciter_name,
                    "playback_state": self.playback_state,
                    "timestamp": datetime.now(APP_TIMEZONE).isoformat(),
                },
                service="AudioService",
            )

        except Exception as e:
            TreeLogger.error(
                f"Failed to save current position: {e}",
                None,
                {
                    "error_type": type(e).__name__,
                    "attempted_surah": self.current_surah_index,
                    "attempted_reciter": self.current_reciter_name,
                },
                service="AudioService",
            )

    # =========================================================================
    # Voice Connection Management
    # =========================================================================

    async def _connect_to_voice_channel(self, channel_id: int) -> bool:
        """
        Connect to Discord voice channel with error handling and retry logic.

        This method performs a comprehensive voice connection process including:
        - Guild and channel validation
        - Permission checks
        - Connection establishment with timeout
        - Health metrics tracking
        - Error categorization and logging

        Args:
            channel_id: Discord voice channel ID

        Returns:
            True if connection successful, False otherwise
        """
        try:
            TreeLogger.info(
                f"Connecting to voice channel {channel_id} with error handling",
                service="AudioService",
            )

            TreeLogger.debug(
                f"Starting voice connection process",
                {
                    "channel_id": channel_id,
                    "guild_id": self.config.guild_id,
                    "has_existing_connection": bool(self.voice_client),
                    "existing_connected": (
                        self.voice_client.is_connected() if self.voice_client else False
                    ),
                },
                service="AudioService",
            )

            # STEP 1: Validate guild exists and bot is a member
            # This ensures the bot is actually in the configured Discord server
            guild = self.bot.get_guild(self.config.guild_id)
            if not guild:
                raise DiscordAPIError(
                    f"Guild {self.config.guild_id} not found",
                    operation="voice_connection",
                    user_friendly_message="Bot is not in the configured Discord server",
                )

            # STEP 2: Validate voice channel exists and is accessible
            # This checks if the channel ID actually points to a real channel
            channel = guild.get_channel(channel_id)
            if not channel:
                raise DiscordAPIError(
                    f"Voice channel {channel_id} not found",
                    operation="voice_connection",
                    user_friendly_message="Voice channel not found",
                )

            # STEP 3: Verify channel type is actually a voice channel
            # Discord has different channel types (text, voice, stage, etc.)
            if not isinstance(channel, discord.VoiceChannel):
                raise DiscordAPIError(
                    f"Channel {channel_id} is not a voice channel",
                    operation="voice_connection",
                    user_friendly_message="Selected channel is not a voice channel",
                )

            # STEP 4: Check bot permissions for voice channel access
            # Bot needs CONNECT permission to join voice channels
            if not channel.permissions_for(guild.me).connect:
                raise DiscordAPIError(
                    f"Bot lacks permission to connect to channel {channel_id}",
                    operation="voice_connection",
                    user_friendly_message="Bot doesn't have permission to join this voice channel",
                )

            # STEP 5: Establish voice connection with timeout protection
            # 30-second timeout prevents hanging on network issues
            start_time = time.time()
            self.voice_client = await channel.connect(timeout=30.0, self_deaf=True)
            connection_time = time.time() - start_time

            # STEP 6: Update connection state and reset error counters
            # This marks the service as successfully connected
            self.is_connected = True
            self.current_voice_channel_id = channel_id
            self.connection_retry_count = 0
            self.last_connection_error = None

            # STEP 7: Update connection health metrics for monitoring
            # Tracks success rate, timing, and connection stability
            self.connection_health["total_connections"] += 1
            self.connection_health["successful_connections"] += 1
            self.connection_health["last_connection_time"] = datetime.now(
                APP_TIMEZONE
            ).isoformat()

            # STEP 8: Calculate rolling average connection time
            # Uses weighted average to track performance trends
            total_connections = self.connection_health["total_connections"]
            current_avg = self.connection_health["average_connection_time"]
            self.connection_health["average_connection_time"] = (
                current_avg * (total_connections - 1) + connection_time
            ) / total_connections

            # STEP 9: Log successful connection with detailed metrics
            # Provides comprehensive debugging information
            TreeLogger.info(
                f"Voice connection established successfully",
                {
                    "guild": guild.name,
                    "channel": channel.name,
                    "channel_id": channel_id,
                    "members": len(channel.members),
                    "bitrate": channel.bitrate,
                    "region": channel.rtc_region,
                    "connection_time_ms": connection_time * 1000,
                },
            )

            return True

        except Exception as e:
            # ERROR HANDLING: Update failure metrics and calculate stability score
            # This section handles all connection failures and tracks error patterns
            self.connection_health["total_connections"] += 1
            self.connection_health["failed_connections"] += 1
            self.connection_retry_count += 1
            self.last_connection_error = datetime.now(APP_TIMEZONE)

            # Calculate connection stability score (0-100)
            # Higher score = more reliable connections
            total_connections = self.connection_health["total_connections"]
            failed_connections = self.connection_health["failed_connections"]
            self.connection_health["connection_stability_score"] = max(
                0, 100 - (failed_connections / total_connections) * 100
            )

            await self.error_handler.handle_error(
                e,
                {
                    "operation": "voice_connection",
                    "channel_id": channel_id,
                    "guild_id": self.config.guild_id,
                    "retry_count": self.connection_retry_count,
                },
            )

            return False

    async def _disconnect_voice(self) -> None:
        """Disconnect from voice channel with error handling."""
        if not self.voice_client:
            TreeLogger.debug("No voice client to disconnect", service="AudioService")
            return

        try:
            TreeLogger.debug(
                "Attempting to disconnect voice client",
                {
                    "voice_client_connected": self.voice_client.is_connected(),
                    "current_channel_id": self.current_voice_channel_id,
                    "is_connected": self.is_connected,
                },
                service="AudioService",
            )
            TreeLogger.info("Disconnecting voice client", service="AudioService")

            await self.voice_client.disconnect()
            self.is_connected = False
            self.current_voice_channel_id = None
            self.voice_client = None

            TreeLogger.info(
                "Voice connection disconnected successfully", service="AudioService"
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "voice_disconnection",
                    "channel_id": self.current_voice_channel_id,
                },
            )

    async def reconnect_voice(self) -> bool:
        """
        Reconnect to voice channel with retry logic and exponential backoff.

        Returns:
            True if reconnection successful, False otherwise
        """
        if not self.current_voice_channel_id:
            TreeLogger.warning(
                "No voice channel to reconnect to", service="AudioService"
            )
            return False

        try:
            TreeLogger.debug(
                "Starting voice reconnection process",
                {
                    "target_channel_id": self.current_voice_channel_id,
                    "current_voice_client": bool(self.voice_client),
                    "is_connected": self.is_connected,
                    "connection_retry_count": self.connection_retry_count,
                },
                service="AudioService",
            )
            TreeLogger.info(
                f"Reconnecting to voice channel {self.current_voice_channel_id}",
                service="AudioService",
            )

            # Check if the voice channel still exists and is accessible
            guild = self.bot.get_guild(self.config.guild_id)
            if not guild:
                TreeLogger.error(
                    f"Guild {self.config.guild_id} not found during reconnection",
                    service="AudioService",
                )
                return False

            TreeLogger.debug(
                "Guild found during reconnection",
                {
                    "guild_id": guild.id,
                    "guild_name": guild.name,
                    "member_count": guild.member_count,
                },
                service="AudioService",
            )

            channel = guild.get_channel(self.current_voice_channel_id)
            if not channel:
                TreeLogger.error(
                    f"Voice channel {self.current_voice_channel_id} not found during reconnection",
                    service="AudioService",
                )
                # Reset the current voice channel ID since it doesn't exist
                self.current_voice_channel_id = None
                return False

            if not isinstance(channel, discord.VoiceChannel):
                TreeLogger.error(
                    f"Channel {self.current_voice_channel_id} is not a voice channel",
                    service="AudioService",
                )
                self.current_voice_channel_id = None
                return False

            # Check bot permissions
            permissions = channel.permissions_for(guild.me)
            TreeLogger.debug(
                "Checking bot permissions for voice channel",
                {
                    "channel_id": channel.id,
                    "channel_name": channel.name,
                    "can_connect": permissions.connect,
                    "can_speak": permissions.speak,
                    "can_use_voice_activation": permissions.use_voice_activation,
                },
                service="AudioService",
            )

            if not permissions.connect:
                TreeLogger.error(
                    f"Bot lacks permission to connect to channel {self.current_voice_channel_id}",
                    service="AudioService",
                )
                return False

            # Disconnect first if connected
            if self.voice_client:
                TreeLogger.debug(
                    "Disconnecting existing voice client before reconnection",
                    service="AudioService",
                )
                await self._disconnect_voice()

            # Attempt reconnection with retry logic
            success = await self._retry_operation(
                operation=lambda: self._connect_to_voice_channel(
                    self.current_voice_channel_id
                ),
                operation_name="voice_reconnection",
                context={
                    "service_name": "AudioService",
                    "channel_id": self.current_voice_channel_id,
                    "retry_count": self.connection_retry_count,
                },
                max_retries=3,
            )

            if success:
                TreeLogger.info("Voice reconnection successful", service="AudioService")
                return True
            else:
                TreeLogger.error(
                    "Voice reconnection failed after all retries",
                    service="AudioService",
                )
                return False

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "voice_reconnection",
                    "channel_id": self.current_voice_channel_id,
                },
            )
            return False

    # =========================================================================
    # Audio File Management
    # =========================================================================

    async def _validate_audio_folder(self) -> None:
        """Validate audio folder structure using validation utility."""
        try:
            # Create composite validator
            validator = CompositeValidator("AudioService")

            # Add file system validation
            fs_validator = FileSystemValidator("AudioService")
            fs_validator.add_path(
                path=self.config.audio_folder,
                path_type="directory",
                create_if_missing=False,
                required_space_mb=100,  # Require at least 100MB free space
            )
            validator.add_validator(fs_validator)

            # Validate
            is_valid = await validator.validate_with_logging()

            if not is_valid:
                raise ResourceError(
                    f"Audio folder validation failed: {self.config.audio_folder}",
                    operation="audio_folder_validation",
                    user_friendly_message="Audio files not found. Please check configuration.",
                )

            # Additional check for reciter folders
            audio_folder = Path(self.config.audio_folder)
            reciter_folders = [f for f in audio_folder.iterdir() if f.is_dir()]
            if not reciter_folders:
                raise ResourceError(
                    f"No reciter folders found in {self.config.audio_folder}",
                    operation="audio_folder_validation",
                    user_friendly_message="No audio reciters found. Please check audio folder structure.",
                )

            TreeLogger.info(
                "Audio folder validation successful",
                {
                    "audio_folder": str(audio_folder),
                    "reciter_folders": len(reciter_folders),
                    "reciters": [f.name for f in reciter_folders],
                },
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "audio_folder_validation",
                    "audio_folder": self.config.audio_folder,
                },
            )
            raise

    async def _extract_audio_duration(self, file_path: str) -> Optional[float]:
        """
        Extract audio duration from file using ffprobe.

        Args:
            file_path: Path to audio file

        Returns:
            Duration in seconds or None if extraction fails
        """
        try:
            # Use mutagen to get MP3 duration - much simpler than ffprobe!
            audio = MP3(file_path)
            if audio.info and hasattr(audio.info, "length"):
                duration = audio.info.length
                TreeLogger.debug(
                    f"Extracted duration: {duration}s for {file_path}",
                    service="AudioService",
                )
                return duration

        except Exception as e:
            TreeLogger.error(
                f"Error extracting duration from {file_path}: {e}",
                service="AudioService",
            )

        return None

    async def _discover_reciters(self) -> None:
        """Discover available reciters like the old QuranBot - fast and simple."""
        try:
            TreeLogger.info("Discovering audio reciters", service="AudioService")

            audio_folder = Path(self.config.audio_folder)
            total_files = 0
            total_size_mb = 0.0

            # Discover available reciters from audio folder
            available_reciter_folders = [
                folder
                for folder in audio_folder.iterdir()
                if folder.is_dir() and not folder.name.startswith(".")
            ]

            TreeLogger.debug(
                f"Found {len(available_reciter_folders)} reciter folders",
                {"folders": [f.name for f in available_reciter_folders]},
                service="AudioService",
            )

            for reciter_folder in available_reciter_folders:
                reciter_name = reciter_folder.name

                if not reciter_folder.exists():
                    TreeLogger.warning(
                        f"Reciter folder not found: {reciter_name}",
                        {"reciter_folder": str(reciter_folder)},
                    )
                    continue

                TreeLogger.debug(
                    f"Scanning reciter: {reciter_name}", service="AudioService"
                )

                # Initialize reciter data
                self.available_reciters[reciter_name] = {
                    "folder_path": str(reciter_folder),
                    "available_surahs": [],
                    "total_files": 0,
                    "total_size_mb": 0.0,
                    "last_scan": datetime.now(APP_TIMEZONE).isoformat(),
                }

                self.audio_files_cache[reciter_name] = {}

                # Scan audio files
                for audio_file in reciter_folder.glob("*.mp3"):
                    try:
                        surah_number = int(audio_file.stem)

                        if not (1 <= surah_number <= 114):
                            TreeLogger.warning(
                                f"Invalid surah number in file: {audio_file.name}",
                                {"surah_number": surah_number},
                                service="AudioService",
                            )
                            continue

                        # Get file information
                        file_size_mb = audio_file.stat().st_size / (1024 * 1024)

                        # Skip duration extraction during startup for fast loading
                        duration_seconds = 0.0

                        audio_info = AudioFileInfo(
                            file_path=str(audio_file),
                            surah_number=surah_number,
                            reciter=reciter_name,
                            file_size=int(
                                audio_file.stat().st_size
                            ),  # Use bytes for Pydantic model
                            duration_seconds=(
                                duration_seconds
                                if duration_seconds is not None
                                else 0.0
                            ),
                        )

                        # All audio files are valid if we got here
                        self.audio_files_cache[reciter_name][surah_number] = audio_info
                        self.available_reciters[reciter_name][
                            "available_surahs"
                        ].append(surah_number)
                        self.available_reciters[reciter_name]["total_files"] += 1
                        self.available_reciters[reciter_name][
                            "total_size_mb"
                        ] += file_size_mb

                        total_files += 1
                        total_size_mb += file_size_mb

                    except ValueError:
                        TreeLogger.warning(
                            f"Invalid filename format: {audio_file.name}",
                            {"file_path": str(audio_file)},
                        )
                        continue

                # Sort available surahs
                self.available_reciters[reciter_name]["available_surahs"].sort()

                TreeLogger.debug(
                    f"Reciter scan complete: {reciter_name}",
                    {
                        "available_surahs": len(
                            self.available_reciters[reciter_name]["available_surahs"]
                        ),
                        "total_files": self.available_reciters[reciter_name][
                            "total_files"
                        ],
                        "total_size_mb": round(
                            self.available_reciters[reciter_name]["total_size_mb"], 1
                        ),
                    },
                )

            TreeLogger.info(
                "Audio library scan complete with validation",
                {
                    "total_reciters": len(self.available_reciters),
                    "total_files": total_files,
                    "total_size_mb": round(total_size_mb, 1),
                    "default_reciter": self.config.default_reciter,
                    "default_reciter_found": self.config.default_reciter
                    in self.available_reciters,
                    "available_reciters": list(self.available_reciters.keys()),
                },
            )

            # Verify default reciter is available
            if self.config.default_reciter not in self.available_reciters:
                TreeLogger.warning(
                    f"Default reciter '{self.config.default_reciter}' not found in audio library",
                    {
                        "default_reciter": self.config.default_reciter,
                        "available_reciters": list(self.available_reciters.keys()),
                    },
                    service="AudioService",
                )
                # Use first available reciter as fallback
                if self.available_reciters:
                    first_reciter = list(self.available_reciters.keys())[0]
                    TreeLogger.info(
                        f"Using '{first_reciter}' as fallback reciter",
                        service="AudioService",
                    )
                    self.current_reciter_name = first_reciter
                    self.current_reciter = first_reciter

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "audio_file_scanning",
                    "audio_folder": self.config.audio_folder,
                },
            )
            raise

    async def _validate_ffmpeg(self) -> None:
        """Validate FFmpeg installation using validation utility."""
        try:
            TreeLogger.info(
                f"Validating FFmpeg installation: {self.config.ffmpeg_path}",
                service="AudioService",
            )

            # Create dependency validator
            validator = DependencyValidator("AudioService")

            # Add FFmpeg validation
            validator.add_executable(
                name=self.config.ffmpeg_path,
                test_command=f"{self.config.ffmpeg_path} -version",
                required=True,
            )

            # Validate
            is_valid = await validator.validate_with_logging()

            if not is_valid:
                raise ResourceError(
                    f"FFmpeg validation failed: {self.config.ffmpeg_path}",
                    operation="ffmpeg_validation",
                    user_friendly_message="FFmpeg not found. Please install FFmpeg for audio playback.",
                )

            TreeLogger.info(
                "FFmpeg validation successful", {"ffmpeg_path": self.config.ffmpeg_path}
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "ffmpeg_validation",
                    "ffmpeg_path": self.config.ffmpeg_path,
                },
            )
            raise

    # =========================================================================
    # Audio Playback Management
    # =========================================================================

    def _get_current_file_duration(self) -> float:
        """Get the duration of the currently playing MP3 file in seconds."""
        try:
            # Get the current audio file info from cache
            if not self.current_reciter_name:
                return 0.0

            reciter_cache = self.audio_files_cache.get(self.current_reciter_name)
            if not reciter_cache:
                return 0.0

            file_info = reciter_cache.get(self.current_surah_index)
            if file_info and file_info.duration_seconds > 0:
                return file_info.duration_seconds

            # If not in cache or duration is 0, return 0
            # The actual duration will be loaded when the file is played
            return 0.0
        except Exception as e:
            TreeLogger.error(f"Error getting MP3 duration: {e}", service="AudioService")
            return 0.0

    async def play_surah(
        self, surah_number: int, reciter: Optional[str] = None
    ) -> bool:
        """
        Play a Quran surah with error handling and retry logic.

        This method performs comprehensive surah playback including:
        - Input validation and sanitization
        - Reciter selection and availability checking
        - Audio file retrieval with retry logic
        - Playback initialization and state management
        - Statistics tracking and monitoring
        - Error recovery and user feedback

        Args:
            surah_number: Surah number (1-114)
            reciter: Reciter name (uses default if not specified)

        Returns:
            True if playback started successfully, False otherwise
        """
        try:
            TreeLogger.info(
                f"Starting playback of surah {surah_number} with error handling",
                service="AudioService",
            )

            # STEP 1: Input Validation and Sanitization
            # Validate surah number is within valid range (1-114)
            # This prevents invalid requests and potential errors
            if not (1 <= surah_number <= 114):
                raise ValidationError(
                    f"Invalid surah number: {surah_number}",
                    operation="play_surah",
                    user_friendly_message="Invalid surah number. Please choose between 1-114.",
                )

            # STEP 2: Reciter Selection and Validation
            # Use provided reciter or fall back to current reciter, then default
            # Ensure the selected reciter is available in the system
            default_reciter_str = (
                str(self.config.default_reciter.value)
                if hasattr(self.config.default_reciter, "value")
                else str(self.config.default_reciter)
            )
            selected_reciter = reciter or self.current_reciter or default_reciter_str
            if selected_reciter not in self.available_reciters:
                raise ValidationError(
                    f"Reciter not found: {selected_reciter}",
                    operation="play_surah",
                    user_friendly_message=f"Reciter '{selected_reciter}' not available.",
                )

            # STEP 3: Audio File Retrieval with Retry Logic
            # Get audio file with comprehensive retry mechanism
            # This handles file system issues and network problems
            audio_file = await self._retry_operation(
                operation=lambda: self._get_audio_file(surah_number, selected_reciter),
                operation_name="audio_file_retrieval",
                context={"surah_number": surah_number, "reciter": selected_reciter},
            )

            # STEP 4: Audio File Availability Check
            # Verify that the requested audio file actually exists
            # This prevents playback attempts on missing files
            if not audio_file:
                raise AudioError(
                    f"Audio file not found for surah {surah_number} by {selected_reciter}",
                    operation="play_surah",
                    user_friendly_message=f"Audio not available for surah {surah_number} by {selected_reciter}.",
                )

            # STEP 5: Update State BEFORE Playback
            # Update current state before starting playback so presence is correct
            self.current_surah = surah_number
            self.current_surah_index = surah_number  # Keep both variables in sync
            self.current_reciter = selected_reciter
            self.current_reciter_name = selected_reciter  # Keep both variables in sync

            # STEP 6: Playback Initialization with Retry Logic
            # Start actual audio playback with comprehensive error handling
            # This includes voice client setup and audio stream initialization
            await self._retry_operation(
                operation=lambda: self._start_playback(audio_file),
                operation_name="playback_start",
                context={
                    "surah_number": surah_number,
                    "reciter": selected_reciter,
                    "audio_file": audio_file.file_path,
                },
            )

            # STEP 7: Statistics and Metrics Tracking
            # Update playback statistics for monitoring and analytics
            # This helps track usage patterns and system performance
            self.playback_stats["total_playbacks"] += 1
            self.playback_stats["successful_playbacks"] += 1
            self.playback_stats["last_playback_time"] = datetime.now(
                APP_TIMEZONE
            ).isoformat()

            TreeLogger.info(
                f"Playback started successfully",
                {
                    "surah_number": surah_number,
                    "reciter": selected_reciter,
                    "audio_file": audio_file.file_path,
                    "file_size_mb": (
                        audio_file.file_size / (1024 * 1024)
                        if hasattr(audio_file, "file_size") and audio_file.file_size
                        else 0
                    ),
                },
                service="AudioService",
            )

            return True

        except Exception as e:
            # Update playback stats
            self.playback_stats["total_playbacks"] += 1
            self.playback_stats["failed_playbacks"] += 1

            await self.error_handler.handle_error(
                e,
                {
                    "operation": "play_surah",
                    "surah_number": surah_number,
                    "reciter": reciter,
                    "current_reciter": self.current_reciter,
                },
            )

            return False

    async def _get_audio_file(
        self, surah_number: int, reciter: str
    ) -> Optional[AudioFileInfo]:
        """
        Get audio file information with comprehensive validation and caching.

        This method performs complex audio file retrieval including:
        - Cache validation and lookup optimization
        - File system existence verification
        - Audio file integrity validation
        - Access time tracking for analytics
        - Error handling and fallback mechanisms

        Args:
            surah_number: Surah number (1-114)
            reciter: Reciter name for audio file lookup

        Returns:
            AudioFileInfo object if found and valid, None otherwise
        """
        try:
            # STEP 1: Cache Validation and Lookup
            # Check if reciter exists in the audio files cache
            # This prevents unnecessary file system operations
            if reciter not in self.audio_files_cache:
                TreeLogger.warning(
                    f"Reciter '{reciter}' not found in cache",
                    {"available_reciters": list(self.audio_files_cache.keys())},
                    service="AudioService",
                )
                return None

            # STEP 2: Surah Availability Check
            # Verify that the specific surah exists for this reciter
            # This handles missing audio files gracefully
            if surah_number not in self.audio_files_cache[reciter]:
                TreeLogger.warning(
                    f"Surah {surah_number} not found for reciter '{reciter}'",
                    {
                        "surah_number": surah_number,
                        "reciter": reciter,
                        "available_surahs": list(
                            self.audio_files_cache[reciter].keys()
                        ),
                    },
                    service="AudioService",
                )
                return None

            # STEP 3: Audio File Object Retrieval
            # Get the cached AudioFileInfo object for the requested surah
            # This contains metadata like file path, size, duration, etc.
            audio_file = self.audio_files_cache[reciter][surah_number]

            # STEP 4: File System Validation
            # Verify that the audio file still exists on disk
            # This handles cases where files were moved or deleted
            if not os.path.exists(audio_file.file_path):
                TreeLogger.warning(
                    f"Audio file no longer exists: {audio_file.file_path}",
                    {
                        "surah_number": surah_number,
                        "reciter": reciter,
                        "file_exists": False,
                    },
                    service="AudioService",
                )
                return None

            # STEP 5: Access Time Tracking
            # Note: AudioFileInfo is frozen (immutable) so we can't update last_accessed
            # The metadata cache service handles access time tracking

            TreeLogger.debug(
                f"Audio file retrieved successfully",
                {
                    "surah_number": surah_number,
                    "reciter": reciter,
                    "file_path": audio_file.file_path,
                    "file_size_mb": (
                        audio_file.file_size / (1024 * 1024)
                        if hasattr(audio_file, "file_size") and audio_file.file_size
                        else 0
                    ),
                    "duration_seconds": audio_file.duration_seconds,
                },
                service="AudioService",
            )

            TreeLogger.info(
                f"Audio file retrieved for surah {surah_number}",
                {"reciter": reciter, "file_path": audio_file.file_path},
                service="AudioService",
            )

            return audio_file

        except Exception as e:
            # ERROR HANDLING: Comprehensive error tracking and recovery
            # This section handles all file retrieval failures and provides debugging context
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "get_audio_file",
                    "surah_number": surah_number,
                    "reciter": reciter,
                },
            )
            return None

    async def _start_playback(self, audio_file: AudioFileInfo) -> None:
        """
        Start audio playback with comprehensive FFmpeg configuration and error handling.

        This method performs complex audio playback initialization including:
        - Voice client connection validation
        - Current playback termination
        - FFmpeg audio source configuration
        - Audio stream setup with error callbacks
        - Playback state management
        - Position tracking initialization
        - Duration calculation and validation

        Args:
            audio_file: AudioFileInfo object containing file metadata and path
        """
        try:
            # STEP 1: Voice Client Connection Validation
            # Ensure voice client is connected before attempting playback
            # This prevents playback attempts on disconnected clients
            if not self.voice_client or not self.voice_client.is_connected():
                raise AudioError(
                    "Voice client not connected",
                    operation="start_playback",
                    user_friendly_message="Bot is not connected to voice channel.",
                )

            # STEP 2: Current Playback Termination
            # Stop any currently playing audio to prevent conflicts
            # This ensures clean transition between audio files
            if self.voice_client.is_playing():
                TreeLogger.info(
                    "Stopping current playback for new audio", service="AudioService"
                )
                self.voice_client.stop()

            # STEP 3: FFmpeg Configuration with Advanced Options
            # Configure FFmpeg with volume control and reconnection capabilities
            # This ensures robust audio streaming with error recovery
            ffmpeg_options = {
                "options": f'-vn -filter:a "volume={self.current_volume}" -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 2 -loglevel quiet'
            }

            TreeLogger.debug(
                "FFmpeg options configured",
                {
                    "volume": self.current_volume,
                    "audio_file": audio_file.file_path,
                    "ffmpeg_path": str(self.config.ffmpeg_path),
                },
                service="AudioService",
            )

            # STEP 4: Audio Source Creation with FFmpeg
            # Create Discord-compatible audio source using FFmpeg
            # This handles various audio formats and provides streaming capabilities
            audio_source = discord.FFmpegPCMAudio(
                audio_file.file_path,
                executable=str(self.config.ffmpeg_path),
                **ffmpeg_options,
            )

            # STEP 5: Playback Initialization with Error Callback
            # Start playing audio with completion callback for state management
            # This enables tracking of playback completion and errors
            self.voice_client.play(audio_source, after=self._playback_finished)

            # STEP 6: Playback State Management
            # Update internal state to reflect active playback
            # This enables other components to track playback status
            self.current_audio = audio_file
            self.playback_state = PlaybackState.PLAYING

            # STEP 7: Position Tracking Initialization
            # Initialize position tracking variables for accurate timing
            # This enables precise playback position reporting
            self.playback_start_time = time.time()
            self.pause_time = None
            self.paused_duration = 0.0

            # STEP 8: Duration Calculation and Validation
            # Set duration from audio file metadata or calculate it
            # This provides accurate duration information for UI display
            if hasattr(audio_file, "duration_seconds") and audio_file.duration_seconds:
                self.current_duration = float(audio_file.duration_seconds)
            else:
                # Extract duration on-the-fly if not available
                TreeLogger.debug(
                    f"Duration not cached for {audio_file.file_path}, extracting...",
                    service="AudioService",
                )
                duration = await self._extract_audio_duration(audio_file.file_path)
                if duration:
                    TreeLogger.debug(
                        f"Extracted duration: {duration}s for {audio_file.file_path}",
                        service="AudioService",
                    )
                    self.current_duration = duration
                else:
                    # Fall back to get_duration method with estimates
                    self.current_duration = self.get_duration()

            TreeLogger.info(
                f"Playback started successfully",
                {
                    "audio_file": audio_file.file_path,
                    "surah_number": audio_file.surah_number,
                    "reciter": audio_file.reciter,
                    "volume": self.current_volume,
                    "duration_seconds": self.current_duration,
                },
                service="AudioService",
            )

            # Update rich presence if available
            try:
                presence_service = self.bot.services.get("presence")
                if presence_service and hasattr(
                    presence_service, "update_for_playback"
                ):
                    surah_info = self.get_current_surah()
                    await presence_service.update_for_playback(
                        surah_name=surah_info.get(
                            "name_english", f"Surah {self.current_surah_index}"
                        ),
                        surah_number=self.current_surah_index,
                        reciter_name=self.current_reciter_name,
                        current_verse=1,
                        total_verses=surah_info.get("verses", 0),
                        emoji=surah_info.get("emoji", "🎧"),
                    )
            except Exception as e:
                TreeLogger.debug(
                    f"Could not update presence: {e}", service="AudioService"
                )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "start_playback",
                    "audio_file": audio_file.file_path if audio_file else None,
                    "voice_connected": self.is_connected,
                },
            )
            raise

    async def _stop_playback(self) -> None:
        """Stop current audio playback with error handling."""
        try:
            if self.voice_client and self.voice_client.is_playing():
                self.voice_client.stop()
                TreeLogger.info(
                    "Audio playback stopped successfully", service="AudioService"
                )

            self.playback_state = PlaybackState.STOPPED
            self.current_audio = None

            # Update presence to idle
            try:
                presence_service = self.bot.services.get("presence")
                if presence_service and hasattr(presence_service, "update_to_idle"):
                    await presence_service.update_to_idle()
            except Exception as e:
                TreeLogger.debug(
                    f"Could not update presence to idle: {e}", service="AudioService"
                )

            # Reset position tracking
            self.playback_start_time = None
            self.pause_time = None
            self.paused_duration = 0.0
            self.current_duration = 0.0

        except Exception as e:
            await self.error_handler.handle_error(
                e, {"operation": "stop_playback", "playback_state": self.playback_state}
            )
            raise

    def _playback_finished(self, error: Optional[Exception]) -> None:
        """Callback when playback finishes with error handling."""
        try:
            # Check jump flag to prevent auto-advance after manual changes
            if hasattr(self, "_jump_occurred") and self._jump_occurred:
                TreeLogger.debug(
                    "Ignoring playback finished callback - jump occurred",
                    service="AudioService",
                )
                self._jump_occurred = False  # Clear the flag
                return

            # Update state immediately (synchronous)
            self.playback_state = PlaybackState.STOPPED
            self.current_audio = None

            # Reset position tracking
            self.playback_start_time = None
            self.pause_time = None
            self.paused_duration = 0.0
            self.current_duration = 0.0

            # Use synchronous logging that's consistent with project
            if error:
                # Log error synchronously
                TreeLogger.error(
                    f"Playback finished with error: {error}",
                    None,
                    {
                        "operation": "audio_playback_callback",
                        "current_surah": self.current_surah,
                        "current_reciter": self.current_reciter,
                        "voice_connected": self.is_connected,
                        "playback_state": self.playback_state,
                    },
                    service="AudioService",
                )
            else:
                # Log success synchronously
                TreeLogger.info(
                    "Playback finished successfully",
                    {
                        "operation": "audio_playback_callback",
                        "current_surah": self.current_surah,
                        "current_reciter": self.current_reciter,
                    },
                    service="AudioService",
                )

            # Log completion for continuous playback
            TreeLogger.info(
                "Playback completed - ready for next surah",
                {
                    "operation": "playback_completion",
                    "completed_surah": self.current_surah,
                    "completed_reciter": self.current_reciter,
                    "playback_state": self.playback_state,
                },
                service="AudioService",
            )

        except Exception as e:
            # Fallback error handling for callback (synchronous logging)
            TreeLogger.error(
                f"Playback finished callback error: {e}",
                None,
                {
                    "operation": "playback_finished_callback",
                    "original_error": str(error) if error else None,
                },
            )

    # =========================================================================
    # Public Interface with Error Handling
    # =========================================================================

    def get_available_reciters(self) -> List[str]:
        """Get list of available reciter names."""
        return list(self.available_reciters.keys())

    def get_available_surahs(self, reciter: Optional[str] = None) -> List[int]:
        """Get list of available surah numbers for a reciter."""
        selected_reciter = reciter or self.current_reciter

        if selected_reciter not in self.available_reciters:
            return []

        return self.available_reciters[selected_reciter]["available_surahs"]

    async def set_volume(self, volume: float) -> bool:
        """
        Set audio volume with validation.

        Args:
            volume: Volume level (0.0 to 1.0)

        Returns:
            True if volume set successfully
        """
        try:
            if not 0.0 <= volume <= 1.0:
                raise ValidationError(
                    f"Invalid volume level: {volume}",
                    operation="set_volume",
                    user_friendly_message="Volume must be between 0 and 100%.",
                )

            self.current_volume = volume
            TreeLogger.info(f"Volume set to {volume}", service="AudioService")
            return True

        except Exception as e:
            await self.error_handler.handle_error(
                e, {"operation": "set_volume", "requested_volume": volume}
            )
            return False

    async def pause_playback(self) -> bool:
        """Pause current playback with error handling."""
        try:
            TreeLogger.debug(
                "Attempting to pause playback",
                {
                    "has_voice_client": bool(self.voice_client),
                    "is_playing": (
                        self.voice_client.is_playing() if self.voice_client else False
                    ),
                    "is_paused": (
                        self.voice_client.is_paused() if self.voice_client else False
                    ),
                    "current_state": self.playback_state,
                },
                service="AudioService",
            )

            if self.voice_client and self.voice_client.is_playing():
                self.voice_client.pause()
                self.playback_state = PlaybackState.PAUSED
                self.pause_time = time.time()
                TreeLogger.info("Playback paused successfully", service="AudioService")
                return True

            TreeLogger.debug(
                "Cannot pause - not currently playing", service="AudioService"
            )
            return False

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {"operation": "pause_playback", "playback_state": self.playback_state},
            )
            return False

    async def resume_playback(self) -> bool:
        """Resume paused playback with error handling."""
        try:
            TreeLogger.debug(
                "Attempting to resume playback",
                {
                    "has_voice_client": bool(self.voice_client),
                    "is_playing": (
                        self.voice_client.is_playing() if self.voice_client else False
                    ),
                    "is_paused": (
                        self.voice_client.is_paused() if self.voice_client else False
                    ),
                    "current_state": self.playback_state,
                    "pause_time": self.pause_time,
                },
                service="AudioService",
            )

            if self.voice_client and self.voice_client.is_paused():
                self.voice_client.resume()
                self.playback_state = PlaybackState.PLAYING

                # Track paused duration
                if self.pause_time:
                    pause_duration = time.time() - self.pause_time
                    self.paused_duration += pause_duration
                    TreeLogger.debug(
                        f"Tracked pause duration: {pause_duration:.2f}s",
                        {"total_paused_duration": self.paused_duration},
                        service="AudioService",
                    )
                    self.pause_time = None
                TreeLogger.info("Playback resumed successfully", service="AudioService")
                return True

            TreeLogger.debug(
                "Cannot resume - not currently paused", service="AudioService"
            )
            return False

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {"operation": "resume_playback", "playback_state": self.playback_state},
            )
            return False

    async def stop_playback(self) -> bool:
        """Stop current playback with error handling."""
        try:
            await self._stop_playback()
            return True

        except Exception as e:
            await self.error_handler.handle_error(
                e, {"operation": "stop_playback", "playback_state": self.playback_state}
            )
            return False

    async def next_surah(self) -> bool:
        """
        Skip to the next surah in sequence.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Set manual control flag to prevent monitoring interference
            self.manual_control_active = True
            TreeLogger.debug(
                "Manual control: Next surah activated", service="AudioService"
            )

            current_surah = self.current_surah_index
            next_surah_number = current_surah + 1

            # Wrap around to surah 1 if we've reached the end
            if next_surah_number > 114:
                next_surah_number = 1

            TreeLogger.info(
                f"Skipping to next surah: {next_surah_number}",
                {"current_surah": current_surah, "next_surah": next_surah_number},
                service="AudioService",
            )

            # Set jump flag before changing to prevent auto-advance
            self._jump_occurred = True

            # Play the next surah
            success = await self.play_surah(next_surah_number)

            if success:
                TreeLogger.info(
                    f"Successfully skipped to surah {next_surah_number}",
                    service="AudioService",
                )
                # Clear manual control flag after a delay to allow playback to stabilize
                asyncio.create_task(self._clear_manual_control_after_delay())
            else:
                TreeLogger.error(
                    f"Failed to skip to surah {next_surah_number}",
                    None,
                    {"current_surah": current_surah, "target_surah": next_surah_number},
                    service="AudioService",
                )
                self.manual_control_active = False

            return success

        except Exception as e:
            self.manual_control_active = False
            await self.error_handler.handle_error(
                e,
                {"operation": "next_surah", "current_surah": self.current_surah_index},
            )
            return False

    async def previous_surah(self) -> bool:
        """
        Skip to the previous surah in sequence.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Set manual control flag to prevent monitoring interference
            self.manual_control_active = True
            TreeLogger.debug(
                "Manual control: Previous surah activated", service="AudioService"
            )

            current_surah = self.current_surah_index
            prev_surah_number = current_surah - 1

            # Wrap around to surah 114 if we've gone before surah 1
            if prev_surah_number < 1:
                prev_surah_number = 114

            TreeLogger.info(
                f"Skipping to previous surah: {prev_surah_number}",
                {"current_surah": current_surah, "previous_surah": prev_surah_number},
                service="AudioService",
            )

            # Set jump flag before changing to prevent auto-advance
            self._jump_occurred = True

            # Play the previous surah
            success = await self.play_surah(prev_surah_number)

            if success:
                TreeLogger.info(
                    f"Successfully skipped to surah {prev_surah_number}",
                    service="AudioService",
                )
                # Clear manual control flag after a delay to allow playback to stabilize
                asyncio.create_task(self._clear_manual_control_after_delay())
            else:
                TreeLogger.error(
                    f"Failed to skip to surah {prev_surah_number}",
                    None,
                    {"current_surah": current_surah, "target_surah": prev_surah_number},
                    service="AudioService",
                )
                self.manual_control_active = False

            return success

        except Exception as e:
            self.manual_control_active = False
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "previous_surah",
                    "current_surah": self.current_surah_index,
                },
            )
            return False

    async def cycle_loop_mode(self) -> str:
        """
        Cycle through loop modes: off -> single -> all -> off.

        Returns:
            The new loop mode as a string
        """
        try:
            # Set manual control flag to prevent monitoring interference
            self.manual_control_active = True
            TreeLogger.debug(
                "Manual control: Cycle loop mode activated", service="AudioService"
            )

            # Define loop mode cycle
            loop_modes = ["off", "single", "all"]
            current_mode = getattr(self, "loop_mode", "off")

            # Find current index and cycle to next
            try:
                current_index = loop_modes.index(current_mode)
                next_index = (current_index + 1) % len(loop_modes)
            except ValueError:
                # If current mode is invalid, start from beginning
                next_index = 0

            new_mode = loop_modes[next_index]

            # Set the new loop mode
            self.loop_mode = new_mode

            TreeLogger.info(
                f"Loop mode cycled from '{current_mode}' to '{new_mode}'",
                {"previous_mode": current_mode, "new_mode": new_mode},
                service="AudioService",
            )

            # Save the state if state service is available
            await self._save_current_position()

            # Clear manual control flag after a short delay
            asyncio.create_task(self._clear_manual_control_after_delay(delay=2))

            return new_mode

        except Exception as e:
            self.manual_control_active = False
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "cycle_loop_mode",
                    "current_loop_mode": getattr(self, "loop_mode", "unknown"),
                },
            )
            return "off"

    async def toggle_shuffle(self) -> bool:
        """
        Toggle shuffle mode on/off.

        Returns:
            True if shuffle is now enabled, False if disabled
        """
        try:
            # Set manual control flag to prevent monitoring interference
            self.manual_control_active = True
            TreeLogger.debug(
                "Manual control: Toggle shuffle activated", service="AudioService"
            )

            current_shuffle = getattr(self, "shuffle_enabled", False)
            new_shuffle = not current_shuffle

            self.shuffle_enabled = new_shuffle

            TreeLogger.info(
                f"Shuffle mode {'enabled' if new_shuffle else 'disabled'}",
                {"previous_shuffle": current_shuffle, "new_shuffle": new_shuffle},
                service="AudioService",
            )

            # Save the state if state service is available
            await self._save_current_position()

            # Clear manual control flag after a short delay
            asyncio.create_task(self._clear_manual_control_after_delay(delay=2))

            return new_shuffle

        except Exception as e:
            self.manual_control_active = False
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "toggle_shuffle",
                    "current_shuffle": getattr(self, "shuffle_enabled", False),
                },
            )
            return False

    async def change_surah(self, surah_number: int) -> bool:
        """
        Change to a specific surah.

        Args:
            surah_number: The surah number to play (1-114)

        Returns:
            True if successful, False otherwise
        """
        try:
            TreeLogger.debug(
                f"change_surah called with surah_number: {surah_number}",
                {
                    "current_surah": self.current_surah,
                    "current_reciter": self.current_reciter,
                    "is_playing": self.is_playing(),
                    "voice_connected": bool(
                        self.voice_client and self.voice_client.is_connected()
                    ),
                },
                service="AudioService",
            )

            if not (1 <= surah_number <= 114):
                return False

            TreeLogger.info(
                f"Changing to surah {surah_number}",
                {
                    "current_surah": self.current_surah_index,
                    "target_surah": surah_number,
                },
                service="AudioService",
            )

            # Stop current playback to prevent callback interference
            if self.voice_client and self.voice_client.is_playing():
                self.voice_client.stop()

            # Set jump flag before changing to prevent auto-advance
            self._jump_occurred = True

            # Update state directly
            self.current_surah_index = surah_number
            self.current_surah = surah_number

            # Play the selected surah
            success = await self.play_surah(surah_number)

            if success:
                TreeLogger.info(
                    f"Successfully changed to surah {surah_number}",
                    service="AudioService",
                )
            else:
                # Clear flag if playback failed
                self._jump_occurred = False

            return success

        except Exception as e:
            self._jump_occurred = False  # Clear flag on error
            TreeLogger.error(f"Error changing surah: {e}", service="AudioService")
            return False

    async def change_reciter(self, reciter_name: str) -> bool:
        """
        Change to a different reciter.

        Args:
            reciter_name: Name of the reciter to switch to

        Returns:
            True if successful, False otherwise
        """
        try:
            TreeLogger.debug(
                f"change_reciter called with reciter_name: {reciter_name}",
                {
                    "current_reciter": self.current_reciter,
                    "current_surah": self.current_surah,
                    "is_playing": self.is_playing(),
                    "available_reciters": list(self.available_reciters.keys()),
                },
                service="AudioService",
            )

            if reciter_name not in self.available_reciters:
                TreeLogger.error(
                    f"Reciter not available: {reciter_name}",
                    None,
                    {
                        "requested_reciter": reciter_name,
                        "available_reciters": list(self.available_reciters.keys()),
                    },
                    service="AudioService",
                )
                return False

            TreeLogger.info(
                f"Changing reciter to {reciter_name}",
                {
                    "current_reciter": self.current_reciter,
                    "target_reciter": reciter_name,
                },
                service="AudioService",
            )

            # Update the current reciter (both variables for consistency)
            old_reciter = self.current_reciter
            self.current_reciter = reciter_name
            self.current_reciter_name = reciter_name  # Keep both variables in sync

            # If currently playing, restart with the new reciter
            if (
                self.current_surah_index
                and self.playback_state == PlaybackState.PLAYING
            ):
                # Stop current playback to prevent callback interference
                if self.voice_client and self.voice_client.is_playing():
                    self.voice_client.stop()

                # Set jump flag before changing to prevent auto-advance
                self._jump_occurred = True

                # Ensure manual control flag is active BEFORE any audio operations
                self.manual_control_active = True

                # Store the current playback state to restore if needed
                saved_playback_state = self.playback_state

                success = await self.play_surah(self.current_surah_index, reciter_name)
                if not success:
                    # Revert to old reciter if failed (both variables)
                    self.current_reciter = old_reciter
                    self.current_reciter_name = old_reciter
                    TreeLogger.error(
                        f"Failed to change to reciter {reciter_name}, reverted",
                        None,
                        {"failed_reciter": reciter_name, "reverted_to": old_reciter},
                        service="AudioService",
                    )
                    return False

                # Clear manual control flag after a longer delay for reciter changes
                asyncio.create_task(self._clear_manual_control_after_delay(delay=8))
            else:
                # Not currently playing, clear flag immediately
                self.manual_control_active = False

            # Save the state
            await self._save_current_position()

            TreeLogger.info(
                f"Successfully changed reciter to {reciter_name}",
                service="AudioService",
            )
            return True

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "change_reciter",
                    "reciter_name": reciter_name,
                    "current_reciter": self.current_reciter,
                },
            )
            return False

    def is_playing(self) -> bool:
        """
        Check if audio is currently playing.

        Returns:
            True if playing, False otherwise
        """
        try:
            return (
                self.voice_client is not None
                and self.voice_client.is_playing()
                and self.playback_state == PlaybackState.PLAYING
            )
        except Exception:
            return False

    def is_paused(self) -> bool:
        """
        Check if audio is currently paused.

        Returns:
            True if paused, False otherwise
        """
        try:
            return (
                self.voice_client is not None
                and self.voice_client.is_paused()
                and self.playback_state == PlaybackState.PAUSED
            )
        except Exception:
            return False

    def get_current_surah(self) -> dict:
        """
        Get information about the currently playing surah.

        Returns:
            Dict with surah information
        """
        try:
            if not self.current_surah_index:
                return {}

            # Import surah data to get proper names
            from ...data.surahs_data import COMPLETE_SURAHS_DATA

            # Find the current surah in the data
            surah_info = None
            for surah in COMPLETE_SURAHS_DATA:
                if surah["number"] == self.current_surah_index:
                    surah_info = surah
                    break

            if surah_info:
                return {
                    "number": self.current_surah_index,
                    "name": f"{surah_info['name_english']} - {surah_info['name_arabic']}",
                    "name_english": surah_info["name_english"],
                    "name_arabic": surah_info["name_arabic"],
                    "verses": surah_info["verses"],
                    "emoji": surah_info["emoji"],
                    "reciter": self.current_reciter or "Unknown",
                }
            else:
                # Fallback if surah not found in data
                return {
                    "number": self.current_surah_index,
                    "name": f"Surah {self.current_surah_index}",
                    "reciter": self.current_reciter or "Unknown",
                }
        except Exception as e:
            TreeLogger.error(
                f"Error getting current surah info: {e}", service="AudioService"
            )
            return {}

    def get_current_reciter(self) -> dict:
        """
        Get information about the current reciter.

        Returns:
            Dict with reciter information including Arabic name
        """
        try:
            if not self.current_reciter:
                return {}

            # Mapping of English reciter names to Arabic names
            reciter_arabic_names = {
                "Abdul Basit Abdul Samad": "عبد الباسط عبد الصمد",
                "Maher Al Muaiqly": "ماهر المعيقلي",
                "Muhammad Al Luhaidan": "محمد اللحيدان",
                "Rashid Al Afasy": "راشد العفاسي",
                "Saad Al Ghamdi": "سعد الغامدي",
                "Yasser Al Dosari": "ياسر الدوسري",
            }

            return {
                "name": self.current_reciter,
                "name_arabic": reciter_arabic_names.get(
                    self.current_reciter, self.current_reciter
                ),
                "available_surahs": len(
                    self.available_reciters.get(self.current_reciter, {})
                ),
            }
        except Exception:
            return {}

    def get_position(self) -> float:
        """
        Get current playback position in seconds.

        Returns:
            Current position in seconds
        """
        try:
            if (
                self.playback_state == PlaybackState.STOPPED
                or not self.playback_start_time
            ):
                return 0.0

            current_time = time.time()

            if self.playback_state == PlaybackState.PAUSED:
                # Return position at time of pause
                if self.pause_time:
                    elapsed = (
                        self.pause_time - self.playback_start_time
                    ) - self.paused_duration
                    return max(0.0, min(elapsed, self.current_duration))
                return 0.0

            # Calculate elapsed time since playback started, minus any paused time
            elapsed = (current_time - self.playback_start_time) - self.paused_duration

            # Ensure position never exceeds duration
            position = max(0.0, min(elapsed, self.current_duration))

            return position

        except Exception as e:
            TreeLogger.error(f"Error getting position: {e}", service="AudioService")
            return 0.0

    def get_duration(self) -> float:
        """
        Get total duration of current audio in seconds.

        Returns:
            Total duration in seconds
        """
        try:
            # Use the working duration method to get actual MP3 duration
            duration = self._get_current_file_duration()
            if duration > 0:
                return duration

            # Return cached duration if available
            if self.current_duration > 0:
                return self.current_duration

            # Try to get from current audio metadata
            if self.current_audio and hasattr(self.current_audio, "duration_seconds"):
                duration = float(self.current_audio.duration_seconds or 0)
                if duration > 0:
                    self.current_duration = duration
                    return duration

            # Default fallback durations for common surahs (in seconds)
            fallback_durations = {
                1: 180,  # Al-Fatiha ~3 minutes
                2: 8640,  # Al-Baqarah ~2.4 hours
                18: 4200,  # Al-Kahf ~70 minutes
                36: 1800,  # Ya-Sin ~30 minutes
                55: 1500,  # Ar-Rahman ~25 minutes
                67: 900,  # Al-Mulk ~15 minutes
                112: 60,  # Al-Ikhlas ~1 minute
                113: 90,  # Al-Falaq ~1.5 minutes
                114: 120,  # An-Nas ~2 minutes
            }

            if self.current_surah and self.current_surah in fallback_durations:
                duration = fallback_durations[self.current_surah]
                self.current_duration = duration
                return duration

            # General fallback based on surah number
            if self.current_surah:
                if self.current_surah <= 10:  # Long surahs
                    duration = 3600  # 60 minutes
                elif self.current_surah <= 50:  # Medium surahs
                    duration = 1800  # 30 minutes
                else:  # Short surahs
                    duration = 600  # 10 minutes

                self.current_duration = duration
                return duration

            return 1800.0  # Default 30 minutes

        except Exception as e:
            TreeLogger.error(f"Error getting duration: {e}", service="AudioService")
            return 1800.0

    def get_loop_mode(self) -> str:
        """
        Get current loop mode.

        Returns:
            Current loop mode (off, single, all)
        """
        try:
            return getattr(self, "loop_mode", "off")
        except Exception:
            return "off"

    def get_shuffle_mode(self) -> bool:
        """
        Get current shuffle mode.

        Returns:
            True if shuffle is enabled, False otherwise
        """
        try:
            return getattr(self, "shuffle_enabled", False)
        except Exception:
            return False

    async def _clear_manual_control_after_delay(self, delay: int = 5):
        """Clear manual control flag after a delay to allow playback to stabilize."""
        try:
            await asyncio.sleep(delay)
            self.manual_control_active = False
            TreeLogger.debug(
                f"Manual control cleared after {delay}s delay", service="AudioService"
            )
        except Exception as e:
            TreeLogger.error(
                f"Error clearing manual control flag: {e}", service="AudioService"
            )
            self.manual_control_active = False
