# =============================================================================
# QuranBot - Audio Manager (Open Source Edition)
# =============================================================================
# This is an open source project provided AS-IS without official support.
# Feel free to use, modify, and learn from this code under the license terms.
#
# Purpose:
# Advanced audio playback system for Discord voice channels with state management
# and control panel integration. Handles Quranic audio with multiple reciters.
#
# Key Features:
# - Multi-reciter support with dynamic discovery
# - State persistence across bot restarts
# - Precise playback position tracking
# - Shuffle and loop functionality
# - Control panel integration
# - Rich presence updates
#
# Technical Implementation:
# - Uses FFmpeg for audio processing
# - Async/await for non-blocking operations
# - Mutagen for MP3 metadata handling
# - State persistence with JSON storage
# - Event-driven architecture
#
# Required Dependencies:
# - discord.py: Discord API wrapper
# - mutagen: MP3 metadata reading
# - FFmpeg: Audio processing (path configurable)
# =============================================================================

import asyncio
import glob
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pathlib import Path
import random

import discord
from mutagen.mp3 import MP3  # For MP3 duration detection

from .state_manager import state_manager
from .surah_mapper import (
    get_surah_display,
    get_surah_info,
    get_surah_name,
    validate_surah_number,
)
from .tree_log import (
    log_async_error,
    log_error_with_traceback,
    log_perfect_tree_section,
    log_progress,
    log_warning_with_context,
)

# =============================================================================
# Audio Monitoring System
# =============================================================================

class AudioPlaybackMonitor:
    """Monitor audio playback health and send Discord alerts"""
    
    def __init__(self):
        self.last_successful_playback = datetime.now(timezone.utc)
        self.last_voice_connection = datetime.now(timezone.utc)
        self.consecutive_playback_failures = 0
        self.consecutive_connection_failures = 0
        self.last_playback_alert = None
        self.last_connection_alert = None
        self.alert_cooldown = 600  # 10 minutes between alerts
        self.playback_failure_threshold = 3
        self.connection_failure_threshold = 2
        self.is_audio_healthy = True
        self.is_connection_healthy = True
        self.expected_playback_interval = 300  # 5 minutes max between tracks
        
        # Auto-recovery settings
        self.auto_recovery_enabled = True
        self.max_recovery_attempts = 3
        self.recovery_cooldown = 300  # 5 minutes between recovery attempts
        self.last_recovery_attempt = None
        self.recovery_attempts = 0
        
    def record_successful_playback(self):
        """Record successful audio playback start"""
        if self.consecutive_playback_failures > 0:
            # Audio recovered
            self.consecutive_playback_failures = 0
            self.last_successful_playback = datetime.now(timezone.utc)
            self.recovery_attempts = 0  # Reset recovery attempts on success
            if not self.is_audio_healthy:
                self.is_audio_healthy = True
                asyncio.create_task(self._send_audio_recovery_alert())
        else:
            self.last_successful_playback = datetime.now(timezone.utc)
    
    def record_successful_connection(self):
        """Record successful voice connection"""
        if self.consecutive_connection_failures > 0:
            # Connection recovered
            self.consecutive_connection_failures = 0
            self.last_voice_connection = datetime.now(timezone.utc)
            self.recovery_attempts = 0  # Reset recovery attempts on success
            if not self.is_connection_healthy:
                self.is_connection_healthy = True
                asyncio.create_task(self._send_connection_recovery_alert())
        else:
            self.last_voice_connection = datetime.now(timezone.utc)
    
    def record_playback_failure(self, error_type: str, error_message: str):
        """Record audio playback failure"""
        self.consecutive_playback_failures += 1
        
        if (self.consecutive_playback_failures >= self.playback_failure_threshold and 
            self.is_audio_healthy and
            self._should_send_playback_alert()):
            self.is_audio_healthy = False
            asyncio.create_task(self._send_playback_failure_alert(error_type, error_message))
            
            # Trigger auto-recovery if enabled
            if self.auto_recovery_enabled and self._should_attempt_recovery():
                asyncio.create_task(self._attempt_audio_recovery())
    
    def record_connection_failure(self, error_type: str, error_message: str):
        """Record voice connection failure"""
        self.consecutive_connection_failures += 1
        
        if (self.consecutive_connection_failures >= self.connection_failure_threshold and 
            self.is_connection_healthy and
            self._should_send_connection_alert()):
            self.is_connection_healthy = False
            asyncio.create_task(self._send_connection_failure_alert(error_type, error_message))
            
            # Trigger auto-recovery if enabled
            if self.auto_recovery_enabled and self._should_attempt_recovery():
                asyncio.create_task(self._attempt_connection_recovery())
    
    def check_playback_timeout(self):
        """Check if audio hasn't played for too long"""
        time_since_playback = datetime.now(timezone.utc) - self.last_successful_playback
        if (time_since_playback.total_seconds() > self.expected_playback_interval and 
            self.is_audio_healthy and
            self._should_send_playback_alert()):
            self.is_audio_healthy = False
            minutes_silent = int(time_since_playback.total_seconds() / 60)
            asyncio.create_task(self._send_playback_timeout_alert(minutes_silent))
            
            # Trigger auto-recovery for timeout
            if self.auto_recovery_enabled and self._should_attempt_recovery():
                asyncio.create_task(self._attempt_audio_recovery())
    
    def _should_send_playback_alert(self) -> bool:
        """Check if enough time has passed since last playback alert"""
        if not self.last_playback_alert:
            return True
        time_since_last = datetime.now(timezone.utc) - self.last_playback_alert
        return time_since_last.total_seconds() >= self.alert_cooldown
    
    def _should_send_connection_alert(self) -> bool:
        """Check if enough time has passed since last connection alert"""
        if not self.last_connection_alert:
            return True
        time_since_last = datetime.now(timezone.utc) - self.last_connection_alert
        return time_since_last.total_seconds() >= self.alert_cooldown
    
    def _should_attempt_recovery(self) -> bool:
        """Check if we should attempt auto-recovery"""
        if not self.auto_recovery_enabled:
            return False
            
        if self.recovery_attempts >= self.max_recovery_attempts:
            return False
            
        if self.last_recovery_attempt:
            time_since_last = datetime.now(timezone.utc) - self.last_recovery_attempt
            if time_since_last.total_seconds() < self.recovery_cooldown:
                return False
                
        return True
    
    async def _attempt_audio_recovery(self):
        """Attempt to recover audio playback automatically"""
        try:
            self.recovery_attempts += 1
            self.last_recovery_attempt = datetime.now(timezone.utc)
            
            log_perfect_tree_section(
                "Audio Recovery - Attempting Auto-Recovery",
                [
                    ("attempt_number", f"{self.recovery_attempts}/{self.max_recovery_attempts}"),
                    ("recovery_type", "Audio Playback Recovery"),
                    ("trigger", "Automatic recovery system"),
                    ("action", "Restarting audio system"),
                ],
                "🔄",
            )
            
            # Get the audio manager instance
            audio_manager = getattr(self, '_audio_manager', None)
            if not audio_manager:
                log_error_with_traceback("Auto-recovery failed", Exception("No audio manager reference"))
                return
            
            # Attempt to restart audio playback
            try:
                await audio_manager.stop_playback()
                await asyncio.sleep(2)  # Brief pause before restart
                await audio_manager.start_playback(resume_position=True)
                
                # Send recovery attempt notification
                from src.utils.discord_logger import get_discord_logger
                discord_logger = get_discord_logger()
                if discord_logger:
                    await discord_logger.log_bot_activity(
                        "auto_recovery",
                        f"automatically restarted audio system (attempt {self.recovery_attempts}/{self.max_recovery_attempts})",
                        {
                            "Recovery Type": "Audio Playback",
                            "Trigger": "Automatic monitoring system",
                            "Attempt": f"{self.recovery_attempts}/{self.max_recovery_attempts}",
                            "Action": "Restarted audio playback",
                            "Status": "🔄 Recovery in progress"
                        }
                    )
                
            except Exception as e:
                log_error_with_traceback("Audio recovery attempt failed", e)
                
                # If this was the last attempt, send final failure alert
                if self.recovery_attempts >= self.max_recovery_attempts:
                    from src.utils.discord_logger import get_discord_logger
                    discord_logger = get_discord_logger()
                    if discord_logger:
                        await discord_logger.log_critical_error(
                            "Auto-Recovery Failed - Manual Intervention Required",
                            None,
                            {
                                "Component": "Audio Recovery System",
                                "Failed Attempts": f"{self.recovery_attempts}/{self.max_recovery_attempts}",
                                "Status": "❌ Auto-recovery exhausted",
                                "Action Required": "Manual restart needed",
                                "Recommendation": "Check VPS and restart bot service"
                            }
                        )
                
        except Exception as e:
            log_error_with_traceback("Critical error in audio recovery", e)
    
    async def _attempt_connection_recovery(self):
        """Attempt to recover voice connection automatically"""
        try:
            self.recovery_attempts += 1
            self.last_recovery_attempt = datetime.now(timezone.utc)
            
            log_perfect_tree_section(
                "Audio Recovery - Attempting Connection Recovery",
                [
                    ("attempt_number", f"{self.recovery_attempts}/{self.max_recovery_attempts}"),
                    ("recovery_type", "Voice Connection Recovery"),
                    ("trigger", "Automatic recovery system"),
                    ("action", "Reconnecting to voice channel"),
                ],
                "🔄",
            )
            
            # Get the audio manager instance
            audio_manager = getattr(self, '_audio_manager', None)
            if not audio_manager:
                log_error_with_traceback("Connection recovery failed", Exception("No audio manager reference"))
                return
            
            # Attempt to reconnect to voice channel
            try:
                # Try to reconnect to voice channel
                if hasattr(audio_manager, 'connect_to_voice_channel'):
                    await audio_manager.connect_to_voice_channel()
                    await asyncio.sleep(2)  # Brief pause before restart
                    await audio_manager.start_playback(resume_position=True)
                
                # Send recovery attempt notification
                from src.utils.discord_logger import get_discord_logger
                discord_logger = get_discord_logger()
                if discord_logger:
                    await discord_logger.log_bot_activity(
                        "auto_recovery",
                        f"automatically reconnected to voice channel (attempt {self.recovery_attempts}/{self.max_recovery_attempts})",
                        {
                            "Recovery Type": "Voice Connection",
                            "Trigger": "Automatic monitoring system",
                            "Attempt": f"{self.recovery_attempts}/{self.max_recovery_attempts}",
                            "Action": "Reconnected to voice channel",
                            "Status": "🔄 Recovery in progress"
                        }
                    )
                
            except Exception as e:
                log_error_with_traceback("Connection recovery attempt failed", e)
                
        except Exception as e:
            log_error_with_traceback("Critical error in connection recovery", e)
    
    async def _send_playback_failure_alert(self, error_type: str, error_message: str):
        """Send Discord alert for audio playback failure"""
        try:
            from src.utils.discord_logger import get_discord_logger
            discord_logger = get_discord_logger()
            if discord_logger:
                self.last_playback_alert = datetime.now(timezone.utc)
                
                time_since_success = datetime.now(timezone.utc) - self.last_successful_playback
                minutes_down = int(time_since_success.total_seconds() / 60)
                
                await discord_logger.log_critical_error(
                    "Audio Playback Failure Detected",
                    None,
                    {
                        "Component": "Audio Manager",
                        "Error Type": error_type,
                        "Error Message": error_message[:500],
                        "Consecutive Failures": str(self.consecutive_playback_failures),
                        "Time Since Success": f"{minutes_down} minutes ago",
                        "Impact": "❌ Audio playback stopped - bot is silent",
                        "Status": "🔇 Audio System Down",
                        "Action Required": "Check voice connection and audio files"
                    }
                )
                
                log_perfect_tree_section(
                    "Audio Monitor - Playback Alert Sent",
                    [
                        ("alert_type", "Audio Playback Failure"),
                        ("consecutive_failures", str(self.consecutive_playback_failures)),
                        ("time_since_success", f"{minutes_down}m ago"),
                        ("discord_alert", "✅ Sent"),
                    ],
                    "🚨",
                )
        except Exception as e:
            log_error_with_traceback("Failed to send audio playback failure alert", e)
    
    async def _send_connection_failure_alert(self, error_type: str, error_message: str):
        """Send Discord alert for voice connection failure"""
        try:
            from src.utils.discord_logger import get_discord_logger
            discord_logger = get_discord_logger()
            if discord_logger:
                self.last_connection_alert = datetime.now(timezone.utc)
                
                time_since_success = datetime.now(timezone.utc) - self.last_voice_connection
                minutes_down = int(time_since_success.total_seconds() / 60)
                
                await discord_logger.log_critical_error(
                    "Voice Connection Failure Detected",
                    None,
                    {
                        "Component": "Voice Connection",
                        "Error Type": error_type,
                        "Error Message": error_message[:500],
                        "Consecutive Failures": str(self.consecutive_connection_failures),
                        "Time Since Success": f"{minutes_down} minutes ago",
                        "Impact": "❌ Bot disconnected from voice channel",
                        "Status": "🔌 Voice Connection Down",
                        "Action Required": "Check voice channel permissions and reconnect"
                    }
                )
                
                log_perfect_tree_section(
                    "Audio Monitor - Connection Alert Sent",
                    [
                        ("alert_type", "Voice Connection Failure"),
                        ("consecutive_failures", str(self.consecutive_connection_failures)),
                        ("time_since_success", f"{minutes_down}m ago"),
                        ("discord_alert", "✅ Sent"),
                    ],
                    "🚨",
                )
        except Exception as e:
            log_error_with_traceback("Failed to send voice connection failure alert", e)
    
    async def _send_playback_timeout_alert(self, minutes_silent: int):
        """Send Discord alert for audio playback timeout"""
        try:
            from src.utils.discord_logger import get_discord_logger
            discord_logger = get_discord_logger()
            if discord_logger:
                self.last_playback_alert = datetime.now(timezone.utc)
                
                await discord_logger.log_critical_error(
                    "Audio Playback Timeout Detected",
                    None,
                    {
                        "Component": "Audio Manager",
                        "Error Type": "playback_timeout",
                        "Silent Duration": f"{minutes_silent} minutes",
                        "Expected Interval": f"{self.expected_playback_interval//60} minutes max",
                        "Impact": "❌ Bot has been silent too long",
                        "Status": "🔇 Audio Timeout",
                        "Action Required": "Check audio playback loop and restart if needed"
                    }
                )
                
                log_perfect_tree_section(
                    "Audio Monitor - Timeout Alert Sent",
                    [
                        ("alert_type", "Audio Playback Timeout"),
                        ("silent_duration", f"{minutes_silent}m"),
                        ("expected_max", f"{self.expected_playback_interval//60}m"),
                        ("discord_alert", "✅ Sent"),
                    ],
                    "🚨",
                )
        except Exception as e:
            log_error_with_traceback("Failed to send audio timeout alert", e)
    
    async def _send_audio_recovery_alert(self):
        """Send Discord alert for audio recovery"""
        try:
            from src.utils.discord_logger import get_discord_logger
            discord_logger = get_discord_logger()
            if discord_logger:
                await discord_logger.log_success(
                    "Audio Playback Recovered",
                    {
                        "Component": "Audio Manager",
                        "Status": "✅ Audio Playback Restored",
                        "Recovery Time": datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
                        "Action": "Audio playback resumed successfully"
                    }
                )
                
                log_perfect_tree_section(
                    "Audio Monitor - Playback Recovery",
                    [
                        ("status", "✅ Audio recovered"),
                        ("recovery_time", datetime.now(timezone.utc).strftime("%H:%M:%S")),
                        ("discord_alert", "✅ Sent"),
                    ],
                    "✅",
                )
        except Exception as e:
            log_error_with_traceback("Failed to send audio recovery alert", e)
    
    async def _send_connection_recovery_alert(self):
        """Send Discord alert for connection recovery"""
        try:
            from src.utils.discord_logger import get_discord_logger
            discord_logger = get_discord_logger()
            if discord_logger:
                await discord_logger.log_success(
                    "Voice Connection Recovered",
                    {
                        "Component": "Voice Connection",
                        "Status": "✅ Voice Connection Restored",
                        "Recovery Time": datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
                        "Action": "Voice connection resumed successfully"
                    }
                )
                
                log_perfect_tree_section(
                    "Audio Monitor - Connection Recovery",
                    [
                        ("status", "✅ Connection recovered"),
                        ("recovery_time", datetime.now(timezone.utc).strftime("%H:%M:%S")),
                        ("discord_alert", "✅ Sent"),
                    ],
                    "✅",
                )
        except Exception as e:
            log_error_with_traceback("Failed to send connection recovery alert", e)

# Global monitor instance
_audio_monitor = AudioPlaybackMonitor()

# =============================================================================
# Monitoring Task
# =============================================================================

async def start_audio_monitoring_task(audio_manager):
    """Start a background task to monitor audio health"""
    # Link the audio manager to the monitor for auto-recovery
    _audio_monitor._audio_manager = audio_manager
    
    async def monitoring_loop():
        """Monitor audio health every 2 minutes"""
        while True:
            try:
                await asyncio.sleep(120)  # Check every 2 minutes
                
                # Check if audio manager exists and is healthy
                if audio_manager:
                    # Check for playback timeout
                    _audio_monitor.check_playback_timeout()
                    
                    # Check voice connection
                    if not audio_manager.voice_client or not audio_manager.voice_client.is_connected():
                        _audio_monitor.record_connection_failure("monitoring_check", "Voice client not connected during health check")
                    else:
                        _audio_monitor.record_successful_connection()
                    
                    # Check if audio should be playing but isn't
                    if (hasattr(audio_manager, 'playback_task') and 
                        audio_manager.playback_task and 
                        not audio_manager.playback_task.done() and
                        not audio_manager.is_playing):
                        _audio_monitor.record_playback_failure("monitoring_check", "Playback task running but audio not playing")
                    
                    # Log monitoring status occasionally
                    if hasattr(_audio_monitor, '_monitoring_cycles'):
                        _audio_monitor._monitoring_cycles += 1
                    else:
                        _audio_monitor._monitoring_cycles = 1
                    
                    # Log every 30 minutes (15 cycles)
                    if _audio_monitor._monitoring_cycles % 15 == 0:
                        log_perfect_tree_section(
                            "Audio Monitor - Health Check",
                            [
                                ("cycles_completed", str(_audio_monitor._monitoring_cycles)),
                                ("audio_healthy", "✅ Yes" if _audio_monitor.is_audio_healthy else "❌ No"),
                                ("connection_healthy", "✅ Yes" if _audio_monitor.is_connection_healthy else "❌ No"),
                                ("last_playback", _audio_monitor.last_successful_playback.strftime("%H:%M:%S")),
                                ("auto_recovery", "✅ Enabled" if _audio_monitor.auto_recovery_enabled else "❌ Disabled"),
                                ("recovery_attempts", f"{_audio_monitor.recovery_attempts}/{_audio_monitor.max_recovery_attempts}"),
                            ],
                            "🔍",
                        )
                        
            except Exception as e:
                log_error_with_traceback("Error in audio monitoring loop", e)
                await asyncio.sleep(60)  # Wait a minute before trying again
    
    # Start the monitoring task
    return asyncio.create_task(monitoring_loop())


class AudioManager:
    """Advanced audio playback system for Discord voice channels"""

    def __init__(
        self,
        bot,
        ffmpeg_path: str,
        audio_base_folder: str = "audio",
        default_reciter: str = "Saad Al Ghamdi",
        default_shuffle: bool = False,
        default_loop: bool = False,
    ):
        """Initialize audio manager with configuration"""
        self.bot = bot
        self.ffmpeg_path = ffmpeg_path
        self.audio_base_folder = audio_base_folder
        self.default_reciter = default_reciter
        
        # State variables
        self.current_reciter = default_reciter
        self.current_surah = 1
        self.current_position = 0.0
        self.is_playing = False
        self.is_paused = False
        self.is_loop_enabled = default_loop
        self.is_shuffle_enabled = default_shuffle
        self.current_audio_files = []
        self.current_file_index = 0
        
        # Initialize components
        self.voice_client = None
        self.rich_presence = None
        self.control_panel = None
        self.monitor = AudioPlaybackMonitor()
        
        # Initialize task variables
        self._position_save_task = None
        self._position_tracking_task = None
        self._jump_occurred = False
        
        # Load saved state
        self._load_saved_state()
        
        # Start background tasks
        if bot and bot.loop:
            self._start_position_saving()
            asyncio.create_task(start_audio_monitoring_task(self))

    def _load_saved_state(self):
        """Load previous playback state from state manager"""
        try:
            state = state_manager.load_playback_state()
            resume_info = state_manager.get_resume_info()

            # Restore state (but reset reciter, loop, shuffle to environment defaults on restart)
            self.current_surah = state["current_surah"]

            # Always reset to default reciter on restart
            self.current_reciter = self.default_reciter

            self.current_position = state["current_position"]

            # Always reset loop and shuffle to environment defaults on restart
            self.is_loop_enabled = self.default_loop
            self.is_shuffle_enabled = self.default_shuffle

            # Create session info
            session_items = [
                ("status", "🔄 Restoring previous session"),
                ("current_surah", self.current_surah),
                ("current_position", f"{self.current_position:.1f}s"),
                ("default_reciter", self.current_reciter),
                ("default_loop", "ON" if self.is_loop_enabled else "OFF"),
                ("default_shuffle", "ON" if self.is_shuffle_enabled else "OFF"),
            ]

            if resume_info["should_resume"]:
                session_items.append(
                    (
                        "resume_action",
                        f"Will resume Surah {resume_info['surah']} at {resume_info['position']:.1f}s",
                    )
                )
            else:
                session_items.append(("resume_action", "Starting fresh session"))

            log_perfect_tree_section(
                "Audio Manager - State Loading",
                session_items,
                "💾",
            )

        except Exception as e:
            log_error_with_traceback("Error loading saved state", e)

    def _start_position_saving(self):
        """Start the periodic position saving task"""
        try:
            if hasattr(self, '_position_save_task') and self._position_save_task and not self._position_save_task.done():
                self._position_save_task.cancel()

            self._position_save_task = asyncio.create_task(self._position_save_loop())
            log_perfect_tree_section(
                "Audio Manager - Position Saving",
                [
                    ("status", "✅ Started periodic state saving"),
                    ("interval", "5 seconds"),
                ],
                "💾",
            )

        except Exception as e:
            log_error_with_traceback("Error starting position saving", e)

    async def _position_save_loop(self):
        """Periodically save playback position"""
        try:
            save_counter = 0  # Counter to control logging frequency
            while True:
                await asyncio.sleep(5)  # Save every 5 seconds
                save_counter += 1

                if self.is_playing and self.rich_presence:
                    try:
                        # Use current position from audio manager instead of rich presence
                        # since get_current_track_info doesn't exist
                        current_time = self.current_position
                        total_time = 0  # Could be enhanced with audio file metadata

                        # Save state silently most of the time, only log every 5 minutes
                        should_log = (
                            save_counter >= 60
                        )  # Log every 60th save (5 minutes)

                        state_manager.save_playback_state(
                            current_surah=self.current_surah,
                            current_position=current_time,
                            current_reciter=self.current_reciter,
                            is_playing=self.is_playing,
                            loop_enabled=self.is_loop_enabled,
                            shuffle_enabled=self.is_shuffle_enabled,
                            silent=not should_log,  # Silent unless it's time to log
                        )

                        # Reset counter after logging
                        if should_log:
                            save_counter = 0
                    except Exception as e:
                        log_error_with_traceback("Error in position save loop", e)

        except asyncio.CancelledError:
            log_perfect_tree_section(
                "Audio Manager - Position Saving Stopped",
                [
                    ("status", "🛑 Position saving stopped"),
                    ("reason", "Task cancelled"),
                ],
                "💾",
            )
        except Exception as e:
            log_error_with_traceback("Critical error in position save loop", e)

    async def _position_tracking_loop(self):
        """Track playback position and update UI every 15 seconds"""
        try:
            update_counter = 0  # Counter to control status logging frequency

            while True:
                await asyncio.sleep(15)  # Update every 15 seconds
                update_counter += 1

                if self.is_playing and self.track_start_time:
                    try:
                        # Calculate current position based on elapsed time
                        import time

                        current_time = time.time()
                        elapsed_time = current_time - self.track_start_time

                        # Get track duration to ensure we don't exceed it
                        track_duration = self._get_current_file_duration()

                        # Ensure position doesn't exceed track duration
                        if track_duration > 0:
                            self.current_position = min(elapsed_time, track_duration)
                            
                            # SAFEGUARD: Check if we've reached the end of the track
                            # If position is within 5 seconds of the end and voice client is still playing,
                            # this indicates a potential stuck state - force progression
                            if (self.current_position >= (track_duration - 5) and 
                                self.voice_client and self.voice_client.is_playing()):
                                
                                # Log the safeguard activation
                                log_perfect_tree_section(
                                    "Audio Safeguard - Track End Detected",
                                    [
                                        ("current_position", f"{self.current_position:.1f}s"),
                                        ("track_duration", f"{track_duration:.1f}s"),
                                        ("action", "Force stopping to prevent stuck state"),
                                        ("safeguard", "✅ Automatic progression activated"),
                                    ],
                                    "🛡️"
                                )
                                
                                # Force stop the voice client to trigger progression
                                try:
                                    self.voice_client.stop()
                                except Exception as e:
                                    log_error_with_traceback("Error force-stopping voice client", e)
                        else:
                            self.current_position = elapsed_time

                        # Update control panel every 4th iteration (1 minute)
                        if update_counter % 4 == 0 and self.control_panel_view:
                            try:
                                await self.control_panel_view.update_panel()
                            except Exception as e:
                                log_error_with_traceback(
                                    "Error updating control panel during position tracking",
                                    e,
                                )

                    except Exception as e:
                        log_error_with_traceback("Error in position tracking", e)

        except asyncio.CancelledError:
            log_perfect_tree_section(
                "Audio Manager - Position Tracking Stopped",
                [
                    ("status", "🛑 Position tracking stopped"),
                    ("reason", "Task cancelled"),
                ],
                "📍",
            )
        except Exception as e:
            log_error_with_traceback("Critical error in position tracking loop", e)

    def _discover_reciters(self) -> List[str]:
        """Discover available reciters from audio folder structure"""
        try:
            log_perfect_tree_section(
                "Audio Manager - Discovering Reciters",
                [
                    ("status", "🔍 Scanning audio folders"),
                    ("base_folder", self.audio_base_folder),
                ],
                "🔍",
            )
            reciters = []

            if os.path.exists(self.audio_base_folder):
                # First pass: collect all valid reciters
                items = sorted(os.listdir(self.audio_base_folder))
                for item in items:
                    folder_path = os.path.join(self.audio_base_folder, item)
                    if os.path.isdir(folder_path):
                        # Check if folder contains mp3 files
                        mp3_files = glob.glob(os.path.join(folder_path, "*.mp3"))
                        if mp3_files:
                            reciters.append((item, len(mp3_files)))

            result = (
                sorted([r[0] for r in reciters]) if reciters else ["Saad Al Ghamdi"]
            )

            # Log discovery results
            reciter_items = [
                ("reciters_found", len(result)),
                ("status", "✅ Reciter discovery complete"),
            ]

            # Add first few reciters as examples
            for i, (reciter, file_count) in enumerate(reciters[:3]):
                reciter_items.append(
                    (f"reciter_{i+1}", f"{reciter} ({file_count} files)")
                )

            if len(reciters) > 3:
                reciter_items.append(
                    ("additional", f"... and {len(reciters) - 3} more")
                )

            log_perfect_tree_section(
                "Audio Manager - Reciters Discovered",
                reciter_items,
                "🎙️",
            )
            return result

        except Exception as e:
            log_error_with_traceback("Error discovering reciters", e)
            return ["Saad Al Ghamdi"]

    def set_rich_presence(self, rich_presence_manager):
        """Set the rich presence manager"""
        try:
            self.rich_presence = rich_presence_manager
            log_perfect_tree_section(
                "Audio Manager - Rich Presence Connected",
                [
                    ("status", "✅ Rich presence manager connected"),
                    ("manager_type", type(rich_presence_manager).__name__),
                ],
                "🎵",
            )
        except Exception as e:
            log_error_with_traceback("Error setting rich presence manager", e)

    def set_control_panel(self, control_panel_view):
        """Set the control panel view for updates"""
        try:
            self.control_panel_view = control_panel_view

            # Sync toggle states with control panel
            if hasattr(control_panel_view, "loop_enabled"):
                control_panel_view.loop_enabled = self.is_loop_enabled
            if hasattr(control_panel_view, "shuffle_enabled"):
                control_panel_view.shuffle_enabled = self.is_shuffle_enabled

            # Update button styles to match current state
            self._sync_control_panel_buttons()

            log_perfect_tree_section(
                "Audio Manager - Control Panel Connected",
                [
                    ("status", "✅ Control panel view connected"),
                    ("loop_state", "ON" if self.is_loop_enabled else "OFF"),
                    ("shuffle_state", "ON" if self.is_shuffle_enabled else "OFF"),
                ],
                "🎛️",
            )
        except Exception as e:
            log_error_with_traceback("Error setting control panel view", e)

    def _sync_control_panel_buttons(self):
        """Sync control panel button styles with current toggle states"""
        try:
            if not self.control_panel_view:
                return

            # Find and update loop button
            for item in self.control_panel_view.children:
                if hasattr(item, "custom_id"):
                    if "loop" in str(item.custom_id).lower() or "🔁" in str(item.label):
                        item.style = (
                            discord.ButtonStyle.success
                            if self.is_loop_enabled
                            else discord.ButtonStyle.secondary
                        )
                    elif "shuffle" in str(item.custom_id).lower() or "🔀" in str(
                        item.label
                    ):
                        item.style = (
                            discord.ButtonStyle.success
                            if self.is_shuffle_enabled
                            else discord.ButtonStyle.secondary
                        )

        except Exception as e:
            log_error_with_traceback("Error syncing control panel buttons", e)

    def set_voice_client(self, voice_client: discord.VoiceClient):
        """Set the voice client for audio playback"""
        try:
            self.voice_client = voice_client
            log_perfect_tree_section(
                "Audio Manager - Voice Client Connected",
                [
                    ("status", "✅ Voice client connected"),
                    ("client_type", type(voice_client).__name__),
                ],
                "🎤",
            )
        except Exception as e:
            log_error_with_traceback("Error setting voice client", e)

    async def connect_to_voice_channel(self):
        """Connect to the voice channel with auto-recovery support"""
        try:
            import os
            
            # Disconnect from any existing voice client first
            if self.voice_client:
                try:
                    await self.voice_client.disconnect(force=True)
                    self.voice_client = None
                    await asyncio.sleep(2)  # Give Discord time to process disconnection
                except:
                    pass
            
            # Get the bot's target guild and channel
            guild_id = int(os.getenv("GUILD_ID", "0"))
            channel_id = int(os.getenv("VOICE_CHANNEL_ID", "0"))

            if not guild_id or not channel_id:
                log_warning_with_context(
                    "Missing configuration", "GUILD_ID or VOICE_CHANNEL_ID not set"
                )
                return False

            guild = self.bot.get_guild(guild_id)
            if not guild:
                log_warning_with_context(
                    "Guild not found", f"Guild ID: {guild_id}"
                )
                return False

            channel = guild.get_channel(channel_id)
            if not channel:
                log_warning_with_context(
                    "Voice channel not found", f"Channel ID: {channel_id}"
                )
                return False

            # Connect to voice channel
            log_perfect_tree_section(
                "Voice Channel Connection - Auto Recovery",
                [
                    ("status", "🔄 Attempting voice connection"),
                    ("channel_name", channel.name),
                    ("channel_id", channel_id),
                    ("channel_type", "Voice Channel"),
                    ("guild_name", guild.name),
                    ("guild_id", guild_id),
                    ("recovery_mode", "✅ Auto-recovery active"),
                ],
                "🎤",
            )

            self.voice_client = await channel.connect(reconnect=False, timeout=60)

            log_perfect_tree_section(
                "Voice Channel Connection - Recovery Success",
                [
                    ("status", "✅ Connected to voice channel"),
                    ("channel_name", channel.name),
                    ("channel_id", channel_id),
                    ("guild_name", guild.name),
                    ("guild_id", guild_id),
                    ("recovery_result", "✅ Voice connection restored"),
                ],
                "✅",
            )

            return True

        except Exception as e:
            log_error_with_traceback("Error connecting to voice channel during recovery", e)
            return False

    def get_current_audio_folder(self) -> str:
        """Get the current audio folder path"""
        return os.path.join(self.audio_base_folder, self.current_reciter)

    def load_audio_files(self) -> bool:
        """Load audio files for current reciter"""
        try:
            log_perfect_tree_section(
                "Audio Manager - Loading Files",
                [
                    ("reciter", self.current_reciter),
                    ("status", "🔄 Loading audio files"),
                ],
                "📁",
            )
            audio_folder = self.get_current_audio_folder()

            if not os.path.exists(audio_folder):
                log_warning_with_context(
                    f"Audio folder not found: {audio_folder}",
                    f"Reciter: {self.current_reciter}",
                )
                return False

            self.current_audio_files = sorted(
                glob.glob(os.path.join(audio_folder, "*.mp3"))
            )

            if not self.current_audio_files:
                log_warning_with_context(
                    f"No audio files found in: {audio_folder}",
                    f"Reciter: {self.current_reciter}",
                )
                return False

            # Update file index to match current surah
            self._update_file_index_for_surah()

            # Check for missing surahs and log them
            self._check_missing_surahs()

            log_perfect_tree_section(
                "Audio Files - Loaded",
                [
                    ("audio_files_loaded", f"{len(self.current_audio_files)} files"),
                ],
                "✅",
            )
            return True

        except Exception as e:
            log_error_with_traceback("Error loading audio files", e)
            return False

    def _update_file_index_for_surah(self):
        """Update file index to match current surah"""
        try:
            target_filename = f"{self.current_surah:03d}.mp3"
            for i, audio_file in enumerate(self.current_audio_files):
                if os.path.basename(audio_file) == target_filename:
                    self.current_file_index = i
                    break
        except Exception as e:
            log_error_with_traceback("Error updating file index for surah", e)

    def _check_missing_surahs(self):
        """Check for missing surahs in the current reciter's collection"""
        try:
            # Get list of available surah numbers from filenames
            available_surahs = set()
            for audio_file in self.current_audio_files:
                filename = os.path.basename(audio_file)
                try:
                    # Extract surah number from filename (e.g., "001.mp3" -> 1)
                    surah_num = int(filename.split(".")[0])
                    if 1 <= surah_num <= 114:  # Valid surah range
                        available_surahs.add(surah_num)
                except (ValueError, IndexError):
                    continue

            # Find missing surahs
            all_surahs = set(range(1, 115))  # Surahs 1-114
            missing_surahs = sorted(all_surahs - available_surahs)

            if missing_surahs:
                # Log missing surahs in groups for better readability
                missing_ranges = []
                start = missing_surahs[0]
                end = start

                for i in range(1, len(missing_surahs)):
                    if missing_surahs[i] == end + 1:
                        end = missing_surahs[i]
                    else:
                        if start == end:
                            missing_ranges.append(str(start))
                        else:
                            missing_ranges.append(f"{start}-{end}")
                        start = missing_surahs[i]
                        end = start

                # Add the last range
                if start == end:
                    missing_ranges.append(str(start))
                else:
                    missing_ranges.append(f"{start}-{end}")

                log_perfect_tree_section(
                    "Audio Collection - Missing Surahs",
                    [
                        ("reciter", self.current_reciter),
                        ("available_surahs", f"{len(available_surahs)}/114"),
                        ("missing_count", len(missing_surahs)),
                        ("missing_surahs", ", ".join(missing_ranges)),
                        (
                            "note",
                            "This explains why surah numbers don't match file indices",
                        ),
                    ],
                    "⚠️",
                )
            else:
                log_perfect_tree_section(
                    "Audio Collection - Complete",
                    [
                        ("reciter", self.current_reciter),
                        ("status", "✅ All 114 surahs available"),
                    ],
                    "✅",
                )

        except Exception as e:
            log_error_with_traceback("Error checking missing surahs", e)

    async def start_playback(self, resume_position: bool = True):
        """Start the audio playback loop with monitoring"""
        global _audio_monitor
        
        try:
            log_perfect_tree_section(
                "Audio Manager - Starting Playback",
                [
                    ("status", "🎵 Initializing audio playback"),
                    ("resume_position", resume_position),
                ],
                "▶️",
            )

            if not self.voice_client or not self.voice_client.is_connected():
                _audio_monitor.record_connection_failure("no_voice_client", "Voice client not connected")
                log_warning_with_context(
                    "Cannot start playback", "Voice client not connected"
                )
                return

            if not self.load_audio_files():
                _audio_monitor.record_playback_failure("no_audio_files", "No audio files loaded")
                log_warning_with_context(
                    "Cannot start playback", "No audio files loaded"
                )
                return

            # Stop any existing playback
            await self.stop_playback()

            # Start position saving
            self._start_position_saving()

            # Start new playback task
            self.playback_task = asyncio.create_task(
                self._playback_loop(resume_position=resume_position)
            )
            
            # Record successful start
            _audio_monitor.record_successful_connection()
            
            log_perfect_tree_section(
                "Audio Manager - Playback Started",
                [
                    ("status", "✅ Audio playback started"),
                    ("current_surah", self.current_surah),
                    ("reciter", self.current_reciter),
                ],
                "✅",
            )

        except Exception as e:
            _audio_monitor.record_playback_failure("start_playback_error", str(e))
            log_async_error("start_playback", e, f"Reciter: {self.current_reciter}")

    async def stop_playback(self):
        """Stop the audio playback"""
        try:
            # Save final state before stopping
            if self.is_playing:
                try:
                    if self.rich_presence:
                        # Use current position from audio manager instead of rich presence
                        current_time = self.current_position
                        total_time = 0  # Could be enhanced with audio file metadata

                        state_manager.save_playback_state(
                            current_surah=self.current_surah,
                            current_position=current_time,
                            current_reciter=self.current_reciter,
                            is_playing=False,
                            loop_enabled=self.is_loop_enabled,
                            shuffle_enabled=self.is_shuffle_enabled,
                        )
                except Exception as e:
                    log_error_with_traceback("Error saving final state", e)

            # Stop position saving task
            if hasattr(self, '_position_save_task') and self._position_save_task and not self._position_save_task.done():
                self._position_save_task.cancel()

            # Stop position tracking task
            if hasattr(self, '_position_tracking_task') and self._position_tracking_task and not self._position_tracking_task.done():
                self._position_tracking_task.cancel()

            if self.playback_task and not self.playback_task.done():
                self.playback_task.cancel()
                try:
                    await self.playback_task
                except asyncio.CancelledError:
                    pass

            if self.voice_client and self.voice_client.is_playing():
                self.voice_client.stop()

            if self.rich_presence:
                try:
                    # Use clear_presence instead of stop_track
                    self.rich_presence.clear_presence()
                except Exception as e:
                    log_error_with_traceback("Error stopping rich presence", e)

            self.is_playing = False
            self.is_paused = False

            # Update control panel
            if self.control_panel_view:
                try:
                    await self.control_panel_view.update_panel()
                except Exception as e:
                    log_error_with_traceback("Error updating control panel", e)

            log_perfect_tree_section(
                "Audio Playback - Stopped",
                [
                    ("stopping_playback", "Cleaning up audio playback"),
                    ("playback_stopped", "✅ Audio playback stopped"),
                ],
                "🛑",
            )

        except Exception as e:
            log_async_error("stop_playback", e, "Failed to stop playback cleanly")

    async def pause_playback(self):
        """Pause the audio playback"""
        try:
            if self.voice_client and self.voice_client.is_playing():
                self.voice_client.pause()
                self.is_paused = True

                # Store pause time to maintain accurate position tracking
                import time

                self.track_pause_time = time.time()

                # Update current position based on elapsed time before pause
                if self.track_start_time:
                    self.current_position = (
                        self.track_pause_time - self.track_start_time
                    )

                # Update control panel
                if self.control_panel_view:
                    try:
                        await self.control_panel_view.update_panel()
                    except Exception as e:
                        log_error_with_traceback(
                            "Error updating control panel after pause", e
                        )

                log_perfect_tree_section(
                    "Audio Playback - Paused",
                    [
                        ("playback_paused", "⏸️ Audio paused"),
                    ],
                    "⏸️",
                )

        except Exception as e:
            log_async_error("pause_playback", e, "Failed to pause playback")

    async def resume_playback(self):
        """Resume the audio playback"""
        try:
            if self.voice_client and self.voice_client.is_paused():
                self.voice_client.resume()
                self.is_paused = False

                # Adjust track start time to account for pause duration
                if self.track_pause_time and self.track_start_time:
                    import time

                    pause_duration = time.time() - self.track_pause_time
                    self.track_start_time += pause_duration  # Shift start time forward
                    self.track_pause_time = None  # Clear pause time

                # Update control panel
                if self.control_panel_view:
                    try:
                        await self.control_panel_view.update_panel()
                    except Exception as e:
                        log_error_with_traceback(
                            "Error updating control panel after resume", e
                        )

                log_perfect_tree_section(
                    "Audio Playback - Resumed",
                    [
                        ("playback_resumed", "▶️ Audio resumed"),
                    ],
                    "▶️",
                )

        except Exception as e:
            log_async_error("resume_playback", e, "Failed to resume playback")

    async def skip_to_next(self):
        """Skip to the next track"""
        try:
            if not self.current_audio_files:
                log_warning_with_context("Cannot skip to next", "No audio files loaded")
                return

            # Stop current playback
            if self.voice_client and self.voice_client.is_playing():
                self.voice_client.stop()

            # Move to next track
            if self.is_shuffle_enabled:
                import random

                self.current_file_index = random.randint(
                    0, len(self.current_audio_files) - 1
                )
            else:
                self.current_file_index = (self.current_file_index + 1) % len(
                    self.current_audio_files
                )

            # Update current surah
            self._update_current_surah()

            # The playback loop will automatically play the next track
            log_perfect_tree_section(
                "Audio Playback - Skipped Next",
                [
                    ("skipped_to_next", f"Track {self.current_file_index + 1}"),
                ],
                "⏭️",
            )

        except Exception as e:
            log_async_error(
                "skip_to_next", e, f"Current index: {self.current_file_index}"
            )

    async def skip_to_previous(self):
        """Skip to the previous track"""
        try:
            if not self.current_audio_files:
                log_warning_with_context(
                    "Cannot skip to previous", "No audio files loaded"
                )
                return

            # Stop current playback
            if self.voice_client and self.voice_client.is_playing():
                self.voice_client.stop()

            # Move to previous track
            if self.is_shuffle_enabled:
                import random

                self.current_file_index = random.randint(
                    0, len(self.current_audio_files) - 1
                )
            else:
                self.current_file_index = (self.current_file_index - 1) % len(
                    self.current_audio_files
                )

            # Update current surah
            self._update_current_surah()

            # The playback loop will automatically play the previous track
            log_perfect_tree_section(
                "Audio Playback - Skipped Previous",
                [
                    ("skipped_to_previous", f"Track {self.current_file_index + 1}"),
                ],
                "⏮️",
            )

        except Exception as e:
            log_async_error(
                "skip_to_previous", e, f"Current index: {self.current_file_index}"
            )

    async def jump_to_surah(self, surah_number: int):
        """Jump to a specific Surah"""
        try:
            if not validate_surah_number(surah_number):
                log_warning_with_context(
                    "Invalid Surah number", f"Surah: {surah_number}"
                )
                return

            # Find the audio file for this Surah
            target_filename = f"{surah_number:03d}.mp3"
            target_index = None

            # Debug: Log the search process
            search_items = [("jump_search_target", f"Looking for: {target_filename}")]

            for i, audio_file in enumerate(self.current_audio_files):
                filename = os.path.basename(audio_file)
                search_items.append(("jump_search_check", f"Index {i}: {filename}"))
                if filename == target_filename:
                    target_index = i
                    search_items.append(("jump_search_found", f"Found at index: {i}"))
                    break

            log_perfect_tree_section(
                "Audio Jump - Search Process",
                search_items,
                "🔍",
            )

            if target_index is None:
                log_warning_with_context(
                    f"Audio file not found for Surah {surah_number}",
                    f"Looking for: {target_filename}",
                )
                return

            # Stop current playback
            if self.voice_client and self.voice_client.is_playing():
                self.voice_client.stop()

            # Jump to the target Surah
            self.current_file_index = target_index
            self.current_surah = surah_number

            # Reset position to start from beginning of jumped surah
            self.current_position = 0.0

            # Set jump flag to prevent automatic increment
            self._jump_occurred = True

            # Log successful jump
            log_perfect_tree_section(
                "Audio Jump - Success",
                [
                    ("jump_debug_index", f"Set file index to: {target_index}"),
                    (
                        "jump_debug_file",
                        f"Target file: {os.path.basename(self.current_audio_files[target_index])}",
                    ),
                    ("jump_flag_set", "Jump flag set to prevent auto-increment"),
                    (
                        "jumped_to_surah",
                        f"Surah {surah_number}: {get_surah_name(surah_number)}",
                    ),
                ],
                "✅",
            )

        except Exception as e:
            log_async_error("jump_to_surah", e, f"Target Surah: {surah_number}")

    async def switch_reciter(self, reciter_name: str):
        """Switch to a different reciter"""
        try:
            if reciter_name not in self.available_reciters:
                log_warning_with_context(
                    "Reciter not available", f"Reciter: {reciter_name}"
                )
                return

            # Stop current playback
            await self.stop_playback()

            # Switch reciter
            old_reciter = self.current_reciter
            self.current_reciter = reciter_name

            # Reload audio files
            if self.load_audio_files():
                log_perfect_tree_section(
                    "Reciter Switch - Success",
                    [
                        ("switching_reciter", f"From {old_reciter} to {reciter_name}"),
                        ("reciter_switched", f"{old_reciter} → {reciter_name}"),
                    ],
                    "🎙️",
                )

                # Log reciter switch to Discord
                from src.utils.discord_logger import get_discord_logger
                discord_logger = get_discord_logger()
                if discord_logger:
                    try:
                        await discord_logger.log_bot_activity(
                            "reciter_switch",
                            f"switched reciter from {old_reciter} to {reciter_name}",
                            {
                                "Previous Reciter": old_reciter,
                                "New Reciter": reciter_name,
                                "Current Surah": f"{self.current_surah}. {self._get_surah_name(self.current_surah)}",
                                "Audio Files": f"{len(self.current_audio_files)} files loaded",
                                "Action": "Automatic restart with new reciter"
                            }
                        )
                    except:
                        pass

                # Restart playback
                await self.start_playback()
            else:
                # Revert if failed
                self.current_reciter = old_reciter
                self.load_audio_files()
                log_warning_with_context(
                    "Failed to switch reciter", f"Reverted to: {old_reciter}"
                )

        except Exception as e:
            log_async_error("switch_reciter", e, f"Target reciter: {reciter_name}")

    def toggle_loop(self):
        """Toggle individual surah loop mode (24/7 playback continues regardless)"""
        try:
            self.is_loop_enabled = not self.is_loop_enabled
            log_perfect_tree_section(
                "Audio Settings - Loop Toggle",
                [
                    ("loop_toggled", "ON" if self.is_loop_enabled else "OFF"),
                    (
                        "loop_behavior",
                        (
                            "Individual surah repeat"
                            if self.is_loop_enabled
                            else "Normal progression"
                        ),
                    ),
                    ("continuous_playback", "24/7 mode always active"),
                ],
                "🔁",
            )
        except Exception as e:
            log_error_with_traceback("Error toggling loop mode", e)

    def toggle_shuffle(self):
        """Toggle shuffle mode"""
        try:
            self.is_shuffle_enabled = not self.is_shuffle_enabled
            log_perfect_tree_section(
                "Audio Settings - Shuffle Toggle",
                [
                    ("shuffle_toggled", "ON" if self.is_shuffle_enabled else "OFF"),
                ],
                "🔀",
            )
        except Exception as e:
            log_error_with_traceback("Error toggling shuffle mode", e)

    def _update_current_surah(self):
        """Update current surah based on current file index"""
        try:
            if self.current_audio_files and self.current_file_index < len(
                self.current_audio_files
            ):
                current_file = self.current_audio_files[self.current_file_index]
                filename = os.path.basename(current_file)

                # Extract surah number from filename
                match = re.search(r"(\d+)", filename)
                if match:
                    self.current_surah = int(match.group(1))
                else:
                    # Fallback: use file index + 1
                    self.current_surah = self.current_file_index + 1

                # Ensure surah is within valid range
                if not (1 <= self.current_surah <= 114):
                    self.current_surah = 1

        except Exception as e:
            log_error_with_traceback("Error updating current surah", e)
            self.current_surah = 1

    def _format_time(self, seconds: float) -> str:
        """Format seconds to MM:SS or H:MM:SS like the control panel"""
        try:
            total_seconds = int(seconds)
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            secs = total_seconds % 60

            if hours > 0:
                return f"{hours}:{minutes:02d}:{secs:02d}"  # H:MM:SS (no leading zero for hours)
            else:
                return f"{minutes:02d}:{secs:02d}"  # MM:SS

        except Exception:
            return "00:00"

    def _get_current_file_duration(self) -> float:
        """Get the duration of the currently playing MP3 file in seconds"""
        try:
            if not self.current_audio_files or self.current_file_index >= len(
                self.current_audio_files
            ):
                return 0.0

            current_file = self.current_audio_files[self.current_file_index]

            # Use mutagen to get MP3 duration
            audio = MP3(current_file)
            if audio.info and hasattr(audio.info, "length"):
                return float(audio.info.length)
            else:
                return 0.0

        except Exception as e:
            log_error_with_traceback("Error getting MP3 duration", e)
            return 0.0

    def _get_playback_time_display(self) -> str:
        """Get formatted playback time display like control panel"""
        try:
            # Calculate real-time position based on track start time
            current_time_seconds = 0.0

            if self.is_playing and self.track_start_time:
                import time

                current_time = time.time()
                # This calculation already accounts for resumed position
                current_time_seconds = current_time - self.track_start_time
            else:
                # Use saved position when not playing
                current_time_seconds = self.current_position

            # Get the real duration of the current MP3 file
            total_time_seconds = self._get_current_file_duration()

            # Ensure current time doesn't exceed total time
            if total_time_seconds > 0:
                current_time_seconds = min(current_time_seconds, total_time_seconds)

                # Format both times
                current_str = self._format_time(current_time_seconds)
                total_str = self._format_time(total_time_seconds)
                return f"{current_str} / {total_str}"
            else:
                return "00:00 / 00:00"

        except Exception as e:
            log_error_with_traceback("Error getting playback time display", e)
            return "00:00 / 00:00"

    async def _playback_loop(self, resume_position: bool = True):
        """Main playback loop with resume capability"""
        try:
            # Check if we should resume from saved position
            should_resume = resume_position and self.current_position > 0

            # Special handling for tracks that are complete or nearly complete
            if should_resume and self.rich_presence:
                try:
                    # Get the duration of the current track
                    current_file = (
                        self.current_audio_files[self.current_file_index]
                        if self.current_audio_files
                        else None
                    )
                    if current_file:
                        # Get actual duration using the existing method
                        duration = self._get_current_file_duration()
                        if duration > 0:
                            # Check if track is complete or nearly complete (within 30 seconds of end)
                            # Reduced from 10 seconds to 30 seconds for better detection
                            if self.current_position >= (duration - 30):
                                # Track is complete or nearly complete - skip to next track
                                log_perfect_tree_section(
                                    "Audio Playback - Track Complete on Startup",
                                    [
                                        (
                                            "current_position",
                                            f"{self.current_position:.1f}s",
                                        ),
                                        ("track_duration", f"{duration:.1f}s"),
                                        ("remaining_time", f"{duration - self.current_position:.1f}s"),
                                        ("action", "Skipping to next track"),
                                        ("reason", "Track nearly complete (< 30s remaining)"),
                                    ],
                                    "⏭️",
                                )
                                should_resume = False
                                self.current_position = 0
                                self.current_file_index += 1
                                if self.current_file_index >= len(
                                    self.current_audio_files
                                ):
                                    if self.is_loop_enabled:
                                        self.current_file_index = 0
                                    else:
                                        self.current_file_index = (
                                            0  # Start over from beginning
                                        )

                                # Save the updated state to prevent this issue from recurring
                                state_manager.save_playback_state(
                                    current_surah=self.current_surah,
                                    current_position=0,
                                    current_reciter=self.current_reciter,
                                    is_playing=False,
                                    loop_enabled=self.is_loop_enabled,
                                    shuffle_enabled=self.is_shuffle_enabled,
                                )
                            else:
                                # Ensure position doesn't exceed track duration
                                self.current_position = min(
                                    self.current_position, duration
                                )
                except Exception as e:
                    log_error_with_traceback(
                        "Error checking track completion on startup", e
                    )

            resume_items = [("playback_loop_started", "Beginning audio playback loop")]
            if should_resume:
                resume_items.append(
                    ("resuming_playback", f"Resuming from {self.current_position:.1f}s")
                )
            else:
                resume_items.append(
                    ("starting_fresh", "Starting from beginning of track")
                )

            log_perfect_tree_section(
                "Audio Playback Loop - Started",
                resume_items,
                "🎵",
            )

            while True:
                try:
                    if not self.voice_client or not self.voice_client.is_connected():
                        _audio_monitor.record_connection_failure("voice_disconnected", "Voice client disconnected during playback")
                        log_warning_with_context(
                            "Voice client disconnected", "Stopping playback"
                        )
                        break

                    if not self.current_audio_files:
                        log_warning_with_context(
                            "No audio files available", "Stopping playback"
                        )
                        break

                    # Get current audio file
                    if self.current_file_index >= len(self.current_audio_files):
                        if self.is_loop_enabled:
                            self.current_file_index = 0
                        else:
                            log_perfect_tree_section(
                                "Audio Playback - Complete",
                                [
                                    ("playback_complete", "All tracks played"),
                                ],
                                "✅",
                            )
                            break

                    current_file = self.current_audio_files[self.current_file_index]
                    filename = os.path.basename(current_file)

                    # Update current Surah
                    self._update_current_surah()

                    # Log current track
                    log_progress(
                        self.current_file_index + 1, len(self.current_audio_files)
                    )

                    # Log automatic surah start to Discord
                    from src.utils.discord_logger import get_discord_logger
                    discord_logger = get_discord_logger()
                    if discord_logger:
                        try:
                            surah_name = self._get_surah_name(self.current_surah)
                            await discord_logger.log_bot_activity(
                                "surah_start",
                                f"started playing {surah_name}",
                                {
                                    "Surah Number": str(self.current_surah),
                                    "Surah Name": surah_name,
                                    "Reciter": self.current_reciter,
                                    "File Index": f"{self.current_file_index + 1}/{len(self.current_audio_files)}",
                                    "Position": f"{self.current_position:.1f}s" if self.current_position > 0 else "From beginning"
                                }
                            )
                        except:
                            pass

                    if validate_surah_number(self.current_surah):
                        surah_display = get_surah_display(self.current_surah)
                        log_perfect_tree_section(
                            "Now Playing",
                            [
                                ("surah", surah_display),
                            ],
                            "🎵",
                        )

                        # Start Rich Presence tracking
                        if self.rich_presence:
                            try:
                                # Use update_presence_with_template instead of start_track
                                from src.utils.surah_mapper import (
                                    get_surah_info,
                                    get_surah_name,
                                )

                                surah_name = get_surah_name(self.current_surah)
                                surah_info = get_surah_info(self.current_surah)
                                verse_count = (
                                    str(surah_info.verses) if surah_info else "Unknown"
                                )
                                surah_emoji = surah_info.emoji if surah_info else "📖"

                                # Calculate the actual start time for Discord's automatic elapsed time
                                # This accounts for resume position by adjusting the start time backwards
                                from datetime import datetime, timezone
                                import time
                                
                                # If we're resuming, adjust start time to account for current position
                                actual_start_time = datetime.now(timezone.utc)
                                if self.current_position > 0:
                                    from datetime import timedelta
                                    actual_start_time -= timedelta(seconds=self.current_position)

                                self.rich_presence.update_presence_with_template(
                                    "listening",
                                    {
                                        "emoji": surah_emoji,
                                        "surah": surah_name,
                                        "verse": "1",  # Could be enhanced with actual verse tracking
                                        "total": verse_count,  # Now shows actual verse count
                                        "reciter": self.current_reciter,
                                    },
                                    start_time=actual_start_time,  # Pass start_time for automatic elapsed time
                                )

                                # Note: seek_to_position doesn't exist either, so we'll skip that
                                should_resume = False  # Only resume once

                            except Exception as e:
                                log_error_with_traceback(
                                    "Error starting rich presence track", e
                                )

                    # Create and play audio source with resume capability
                    try:
                        if should_resume and self.current_position > 0:
                            # Validate resume position against track duration
                            track_duration = self._get_current_file_duration()
                            if (
                                track_duration > 0
                                and self.current_position >= (track_duration - 30)
                            ):
                                # Position is too close to end - start from beginning
                                log_perfect_tree_section(
                                    "Audio Resume - Position Too Close to End",
                                    [
                                        (
                                            "saved_position",
                                            f"{self.current_position:.1f}s",
                                        ),
                                        ("track_duration", f"{track_duration:.1f}s"),
                                        ("remaining_time", f"{track_duration - self.current_position:.1f}s"),
                                        ("action", "Starting from beginning instead"),
                                        ("reason", "Less than 30s remaining"),
                                    ],
                                    "⚠️",
                                )
                                self.current_position = 0.0
                                should_resume = False

                        if should_resume and self.current_position > 0:
                            # Use FFmpeg to start from specific position
                            seek_options = f"-ss {self.current_position}"
                            source = discord.FFmpegPCMAudio(
                                current_file,
                                executable=self.ffmpeg_path,
                                before_options=seek_options,
                                options="-vn -loglevel quiet",  # Suppress FFmpeg logs
                            )
                            should_resume = False  # Only resume once
                            log_perfect_tree_section(
                                "Audio Resume",
                                [
                                    ("resumed_from", f"{self.current_position:.1f}s"),
                                ],
                                "⏯️",
                            )
                        else:
                            source = discord.FFmpegPCMAudio(
                                current_file,
                                executable=self.ffmpeg_path,
                                options="-vn -loglevel quiet",  # Suppress FFmpeg logs
                            )

                        # Use a wrapper to catch FFmpeg process errors
                        try:
                            self.voice_client.play(source)
                            self.is_playing = True
                            self.is_paused = False

                            # Record successful playback start
                            _audio_monitor.record_successful_playback()

                            # Set track start time for position tracking
                            import time

                            # Always account for current position when setting track start time
                            # This ensures position tracking works correctly on resume
                            self.track_start_time = time.time() - self.current_position

                            # Start position tracking task
                            if (
                                not hasattr(self, '_position_tracking_task') or not self._position_tracking_task
                                or self._position_tracking_task.done()
                            ):
                                self._position_tracking_task = asyncio.create_task(
                                    self._position_tracking_loop()
                                )

                            # Update control panel
                            if self.control_panel_view:
                                try:
                                    await self.control_panel_view.update_panel()
                                except Exception as e:
                                    log_error_with_traceback(
                                        "Error updating control panel during playback",
                                        e,
                                    )

                            # Wait for playback to finish with better error handling
                            playback_start_time = time.time()
                            track_duration = self._get_current_file_duration()
                            
                            # Set a reasonable timeout: track duration + 30 seconds buffer
                            # This prevents infinite waiting if the track gets stuck
                            timeout_duration = track_duration + 30 if track_duration > 0 else 300  # 5 min default
                            
                            while (
                                self.voice_client.is_playing()
                                or self.voice_client.is_paused()
                            ):
                                await asyncio.sleep(1)
                                
                                # SAFEGUARD: Check for timeout to prevent infinite waiting
                                elapsed_playback = time.time() - playback_start_time
                                if elapsed_playback > timeout_duration:
                                    log_perfect_tree_section(
                                        "Audio Safeguard - Playback Timeout",
                                        [
                                            ("elapsed_time", f"{elapsed_playback:.1f}s"),
                                            ("timeout_limit", f"{timeout_duration:.1f}s"),
                                            ("track_duration", f"{track_duration:.1f}s"),
                                            ("action", "Force stopping stuck playback"),
                                            ("safeguard", "✅ Timeout protection activated"),
                                        ],
                                        "⏰"
                                    )
                                    
                                    # Force stop the stuck playback
                                    try:
                                        self.voice_client.stop()
                                    except Exception as e:
                                        log_error_with_traceback("Error force-stopping stuck playback", e)
                                    break

                            # Mark surah as completed
                            state_manager.mark_surah_completed()

                            # Log successful completion
                            log_perfect_tree_section(
                                "Audio Track - Completed",
                                [
                                    (
                                        "track_completed",
                                        f"Finished playing: {filename}",
                                    ),
                                    ("surah", self.current_surah),
                                    ("status", "✅ Track completed successfully"),
                                ],
                                "✅",
                            )

                        except Exception as voice_error:
                            # Handle voice client specific errors
                            error_msg = str(voice_error).lower()
                            if any(
                                keyword in error_msg
                                for keyword in ["broken pipe", "ffmpeg", "terminated"]
                            ):
                                # This is a normal FFmpeg termination - not an error
                                log_perfect_tree_section(
                                    "Audio Track - Normal Completion",
                                    [
                                        ("track_finished", f"Track ended: {filename}"),
                                        ("surah", self.current_surah),
                                        ("status", "✅ Normal track completion"),
                                    ],
                                    "✅",
                                )
                            else:
                                _audio_monitor.record_playback_failure("voice_client_error", str(voice_error))
                                log_error_with_traceback(
                                    f"Voice client error for: {filename}", voice_error
                                )

                    except Exception as e:
                        # Log the error but don't crash - continue to next track
                        error_msg = str(e).lower()
                        if "broken pipe" in error_msg or "ffmpeg" in error_msg:
                            log_perfect_tree_section(
                                "Audio Track - FFmpeg Transition",
                                [
                                    (
                                        "track_transition",
                                        f"Track completed: {filename}",
                                    ),
                                    ("surah", self.current_surah),
                                    ("status", "✅ Moving to next track"),
                                ],
                                "✅",
                            )
                        else:
                            _audio_monitor.record_playback_failure("audio_file_error", str(e))
                            log_error_with_traceback(
                                f"Error playing audio file: {filename}", e
                            )

                        # Continue to next track on any error
                        pass

                    finally:
                        # Stop Rich Presence for this track
                        if self.rich_presence:
                            try:
                                # Use clear_presence instead of stop_track
                                self.rich_presence.clear_presence()
                            except Exception as e:
                                log_error_with_traceback(
                                    "Error stopping rich presence track", e
                                )

                    # Reset position for next track
                    self.current_position = 0.0
                    self.track_start_time = None  # Reset track timing for next track

                    # Handle loop mode for individual surah
                    if self.is_loop_enabled:
                        # Loop button is ON - repeat the same surah
                        log_perfect_tree_section(
                            "Audio Loop - Individual Surah",
                            [
                                ("loop_mode", "Repeating current surah"),
                                ("current_surah", self.current_surah),
                            ],
                            "🔁",
                        )
                        # Don't increment index - stay on same surah
                        continue

                    # Move to next track (unless a jump occurred)
                    if self._jump_occurred:
                        # Jump occurred, don't increment - just clear the flag
                        self._jump_occurred = False
                        log_perfect_tree_section(
                            "Audio Jump - Handled",
                            [
                                (
                                    "jump_handled",
                                    "Jump detected, skipping auto-increment",
                                ),
                            ],
                            "🔄",
                        )
                    elif self.is_shuffle_enabled:
                        import random

                        self.current_file_index = random.randint(
                            0, len(self.current_audio_files) - 1
                        )
                    else:
                        # Normal progression - always continue 24/7
                        self.current_file_index += 1

                        # 24/7 Continuous Playback: Always restart from beginning after last surah
                        if self.current_file_index >= len(self.current_audio_files):
                            self.current_file_index = 0
                            log_perfect_tree_section(
                                "Audio Playback - 24/7 Restart",
                                [
                                    ("continuous_playback", "Restarting from Surah 1"),
                                    ("reason", "24/7 mode - completed all surahs"),
                                ],
                                "🔄",
                            )

                            # Log 24/7 restart to Discord
                            from src.utils.discord_logger import get_discord_logger
                            discord_logger = get_discord_logger()
                            if discord_logger:
                                try:
                                    await discord_logger.log_bot_activity(
                                        "surah_switch",
                                        f"completed all surahs, restarting from Al-Fatiha for 24/7 continuous playback",
                                        {
                                            "Playback Mode": "24/7 Continuous",
                                            "Action": "Restart from beginning",
                                            "Reason": "Completed all 114 surahs",
                                            "Next Surah": "1. Al-Fatiha",
                                            "Reciter": self.current_reciter
                                        }
                                    )
                                except:
                                    pass

                    # Update control panel after track change
                    if self.control_panel_view:
                        try:
                            await self.control_panel_view.update_panel()
                        except Exception as e:
                            log_error_with_traceback(
                                "Error updating control panel after track change", e
                            )

                    # Small delay to prevent rapid cycling on repeated errors
                    await asyncio.sleep(0.5)

                    # 24/7 mode - never break the loop, always continue playing

                except Exception as e:
                    _audio_monitor.record_playback_failure("playback_loop_error", str(e))
                    log_error_with_traceback("Error in playback loop iteration", e)
                    # Wait a bit before continuing to avoid rapid error loops
                    await asyncio.sleep(2)

        except asyncio.CancelledError:
            log_perfect_tree_section(
                "Audio Playback Loop - Cancelled",
                [
                    ("playback_cancelled", "Playback loop cancelled"),
                ],
                "🛑",
            )
        except Exception as e:
            log_error_with_traceback("Critical error in playback loop", e)
        finally:
            try:
                self.is_playing = False
                self.is_paused = False

                # Update control panel
                if self.control_panel_view:
                    try:
                        await self.control_panel_view.update_panel()
                    except Exception as e:
                        log_error_with_traceback(
                            "Error updating control panel in finally block", e
                        )

                log_perfect_tree_section(
                    "Audio Playback Loop - Ended",
                    [
                        ("playback_loop_ended", "Audio playback loop terminated"),
                    ],
                    "🎵",
                )

            except Exception as e:
                log_error_with_traceback("Error in playback loop cleanup", e)

    def get_playback_status(self) -> Dict[str, Any]:
        """Get current playback status for control panel"""
        try:
            # Get basic status
            status = {
                "is_playing": self.is_playing,
                "is_paused": self.is_paused,
                "current_surah": self.current_surah,
                "current_reciter": self.current_reciter,
                "is_loop_enabled": self.is_loop_enabled,
                "is_shuffle_enabled": self.is_shuffle_enabled,
                "current_track": (
                    self.current_file_index + 1 if self.current_audio_files else 0
                ),
                "total_tracks": len(self.current_audio_files),
                "available_reciters": self.available_reciters,
                "current_time": 0,
                "total_time": 0,
            }

            # Use the exact same time calculation as rich presence
            # This ensures both control panel and rich presence show identical times
            status[
                "current_time"
            ] = self.current_position  # Use actual current position

            # Get the real duration of the current MP3 file
            status["total_time"] = self._get_current_file_duration()

            return status

        except Exception as e:
            log_error_with_traceback("Error getting playback status", e)
            # Return safe defaults
            return {
                "is_playing": False,
                "is_paused": False,
                "current_surah": 1,
                "current_reciter": "Saad Al Ghamdi",
                "is_loop_enabled": False,
                "is_shuffle_enabled": False,
                "current_track": 0,
                "total_tracks": 0,
                "available_reciters": ["Saad Al Ghamdi"],
                "current_time": 0,
                "total_time": 0,
            }

    def _get_surah_name(self, surah_number: int) -> str:
        """Get the name of a surah by its number"""
        try:
            from .surah_mapper import get_surah_info
            surah_info = get_surah_info(surah_number)
            return surah_info.name_transliteration if surah_info else f"Surah {surah_number}"
        except Exception:
            return f"Surah {surah_number}"

    def _get_surah_files(self, reciter: str) -> List[str]:
        """Get list of surah files for a reciter"""
        reciter_dir = Path(self.audio_base_folder) / reciter
        if not reciter_dir.exists():
            return []
        
        files = sorted(glob.glob(str(reciter_dir / "*.mp3")))
        return [str(Path(f)) for f in files]

    def change_reciter(self, reciter_name: str) -> bool:
        """Change current reciter"""
        reciter_dir = Path(self.audio_base_folder) / reciter_name
        if not reciter_dir.exists():
            return False
        
        self.current_reciter = reciter_name
        return True

    def get_current_surah_file(self) -> Optional[str]:
        """Get current surah audio file path"""
        return self.get_surah_file(self.current_surah)

    def get_surah_file(self, surah_number: int) -> Optional[str]:
        """Get specific surah audio file path"""
        files = self._get_surah_files(self.current_reciter)
        if not files:
            return None
        
        try:
            return files[surah_number - 1]
        except IndexError:
            return None

    def get_surah_count(self, reciter: str) -> int:
        """Get total number of surahs for reciter"""
        return len(self._get_surah_files(reciter))

    @property
    def loop_enabled(self) -> bool:
        """Get loop mode status"""
        return self.is_loop_enabled

    @property
    def shuffle_enabled(self) -> bool:
        """Get shuffle mode status"""
        return self.is_shuffle_enabled

    def toggle_loop(self) -> None:
        """Toggle loop mode"""
        self.is_loop_enabled = not self.is_loop_enabled

    def toggle_shuffle(self) -> None:
        """Toggle shuffle mode"""
        self.is_shuffle_enabled = not self.is_shuffle_enabled

    def next_surah(self) -> None:
        """Move to next surah"""
        total_surahs = self.get_surah_count(self.current_reciter)
        if total_surahs == 0:
            return

        if self.shuffle_enabled:
            self.current_surah = random.randint(1, total_surahs)
        else:
            self.current_surah = (self.current_surah % total_surahs) + 1

    def previous_surah(self) -> None:
        """Move to previous surah"""
        total_surahs = self.get_surah_count(self.current_reciter)
        if total_surahs == 0:
            return

        if self.current_surah > 1:
            self.current_surah -= 1
        else:
            self.current_surah = total_surahs
