# =============================================================================
# QuranBot - Rich Presence Manager
# =============================================================================
# Manages Discord Rich Presence for audio playback with progress tracking
# Features Spotify-style progress bars and real-time updates
# =============================================================================

import asyncio
import os
import subprocess
import time
import traceback

import discord
from aiohttp.client_exceptions import ClientConnectionResetError

from .surah_mapper import get_surah_info
from .tree_log import (
    log_async_error,
    log_critical_error,
    log_error_with_traceback,
    log_perfect_tree_section,
    log_spacing,
    log_warning_with_context,
)


# =============================================================================
# Rich Presence State Management
# =============================================================================
class RichPresenceManager:
    """Manages Discord Rich Presence for audio playback"""

    def __init__(self, bot, ffmpeg_path="ffmpeg"):
        """
        Initialize Rich Presence Manager

        Args:
            bot: Discord bot instance
            ffmpeg_path: Path to FFmpeg executable (for FFprobe)
        """
        try:
            self.bot = bot
            self.ffmpeg_path = ffmpeg_path
            self.current_track = None
            self.track_start_time = None
            self.track_duration = None
            self.is_playing = False
            self.update_task = None

            log_perfect_tree_section(
                "Rich Presence Manager Initialization",
                [
                    ("ffmpeg_path", ffmpeg_path),
                    ("status", "✅ Rich Presence Manager ready"),
                    ("bot_user", str(bot.user) if bot.user else "Not connected"),
                ],
                "🎵",
            )

        except Exception as e:
            log_critical_error("Failed to initialize Rich Presence Manager", e)
            raise

    def get_audio_duration(self, audio_file):
        """
        Get duration of audio file using FFprobe

        Args:
            audio_file: Path to audio file

        Returns:
            float: Duration in seconds, or None if detection fails
        """
        try:
            log_perfect_tree_section(
                "Audio Duration Detection",
                [
                    ("file", os.path.basename(audio_file)),
                    ("status", "🔄 Analyzing audio file"),
                    ("tool", "FFprobe"),
                ],
                "🎵",
            )

            # Use FFprobe to get duration
            ffprobe_path = self.ffmpeg_path.replace("ffmpeg", "ffprobe")
            cmd = [
                ffprobe_path,
                "-v",
                "quiet",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                audio_file,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                log_perfect_tree_section(
                    "Audio Duration - Success",
                    [
                        ("duration_formatted", self.format_time(duration)),
                        ("duration_seconds", f"{duration:.1f}s"),
                        ("status", "✅ Duration detected successfully"),
                    ],
                    "⏱️",
                )
                return duration
            else:
                log_warning_with_context(
                    "Could not get audio duration with FFprobe",
                    f"Return code: {result.returncode}",
                )
                return None

        except subprocess.TimeoutExpired:
            log_warning_with_context("FFprobe timeout", "Duration detection timed out")
            return None
        except FileNotFoundError:
            log_warning_with_context(
                "FFprobe not found",
                "Install FFmpeg with FFprobe for duration detection",
            )
            return None
        except ValueError as e:
            log_error_with_traceback("Invalid duration value from FFprobe", e)
            return None
        except Exception as e:
            log_error_with_traceback("Error getting audio duration", e)
            return None

    def format_time(self, seconds):
        """
        Format seconds to MM:SS or H:MM:SS format

        Args:
            seconds: Time in seconds

        Returns:
            str: Formatted time string (MM:SS or H:MM:SS)
        """
        try:
            if seconds is None:
                return "00:00"

            if not isinstance(seconds, (int, float)) or seconds < 0:
                log_warning_with_context(
                    "Invalid time value for formatting",
                    f"Value: {seconds}, Type: {type(seconds)}",
                )
                return "00:00"

            total_seconds = int(seconds)
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            secs = total_seconds % 60

            if hours > 0:
                return f"{hours}:{minutes:02d}:{secs:02d}"  # H:MM:SS (no leading zero for hours)
            else:
                return f"{minutes:02d}:{secs:02d}"  # MM:SS

        except Exception as e:
            log_error_with_traceback("Error formatting time", e)
            return "00:00"

    def get_progress_bar(self, current_time, total_time, length=20):
        """
        Generate a visual progress bar string

        Args:
            current_time: Current playback position in seconds
            total_time: Total track duration in seconds
            length: Length of progress bar in characters

        Returns:
            str: Progress bar string with filled/unfilled blocks
        """
        try:
            if total_time is None or total_time <= 0:
                return "▬" * length

            if current_time is None or current_time < 0:
                current_time = 0

            progress = min(current_time / total_time, 1.0)
            filled_length = int(length * progress)

            bar = "▰" * filled_length + "▱" * (length - filled_length)
            return bar

        except Exception as e:
            log_error_with_traceback("Error generating progress bar", e)
            return "▬" * length

    async def start_track(self, surah_number, audio_file, reciter="Saad Al Ghamdi"):
        """
        Start tracking a new audio track with Rich Presence

        Args:
            surah_number: Surah number (1-114)
            audio_file: Path to audio file
            reciter: Name of reciter
        """
        try:
            log_perfect_tree_section(
                "🎵 Starting Rich Presence Track",
                [
                    ("surah_number", surah_number),
                    ("audio_file", os.path.basename(audio_file)),
                    ("reciter", reciter),
                ],
                "🎵",
            )

            # Stop any existing track
            await self.stop_track()

            # Validate inputs
            if not os.path.exists(audio_file):
                log_error_with_traceback(
                    "Audio file not found for Rich Presence",
                    FileNotFoundError(f"File not found: {audio_file}"),
                )
                return

            # Set up new track
            self.current_track = {
                "surah_number": surah_number,
                "audio_file": audio_file,
                "reciter": reciter,
            }
            self.track_start_time = time.time()
            self.track_duration = self.get_audio_duration(audio_file)
            self.is_playing = True

            # Get Surah info for rich presence
            surah_info = get_surah_info(surah_number)

            if surah_info:
                # Set initial rich presence - emoji and transliterated Arabic name with starting message
                activity = discord.Activity(
                    type=discord.ActivityType.listening,
                    name=f"{surah_info.emoji} {surah_info.name_transliteration} • 🎵 Starting...",
                )

                await self.bot.change_presence(activity=activity)

                # Start the progress update task
                self.update_task = self.bot.loop.create_task(self.update_progress())

                log_perfect_tree_section(
                    "Rich Presence - Track Started",
                    [
                        (
                            "rich_presence",
                            f"✅ Started: {surah_info.name_transliteration}",
                        ),
                        ("progress_task", "✅ Progress update task started"),
                        (
                            "duration",
                            (
                                self.format_time(self.track_duration)
                                if self.track_duration
                                else "Unknown"
                            ),
                        ),
                    ],
                    "🎵",
                )
            else:
                log_warning_with_context(
                    "Could not get Surah info for Rich Presence",
                    f"Surah number: {surah_number}",
                )

        except discord.HTTPException as e:
            log_error_with_traceback("Discord API error in Rich Presence", e)
        except Exception as e:
            log_error_with_traceback("Error starting track in Rich Presence", e)

    async def stop_track(self):
        """Stop tracking the current track and clear Rich Presence"""
        try:
            if not self.current_track and not self.update_task:
                return  # Nothing to stop

            # Stop the update task
            task_status = "No task running"
            if self.update_task and not self.update_task.done():
                self.update_task.cancel()
                try:
                    await self.update_task
                    task_status = "✅ Progress task cancelled"
                except asyncio.CancelledError:
                    task_status = "✅ Progress task cancelled gracefully"

            # Reset state
            self.is_playing = False
            self.current_track = None
            self.track_start_time = None
            self.track_duration = None
            self.update_task = None

            # Clear rich presence (only if bot is still connected)
            presence_status = "Bot not connected"
            if self.bot and not self.bot.is_closed():
                try:
                    await self.bot.change_presence(activity=None)
                    presence_status = "✅ Stopped playback and cleared presence"
                except (
                    discord.ConnectionClosed,
                    discord.HTTPException,
                    ConnectionResetError,
                    Exception,
                ) as e:
                    # Bot is disconnecting/closed, can't update presence - this is normal
                    if "closing transport" in str(e) or "ConnectionReset" in str(
                        type(e).__name__
                    ):
                        presence_status = "✅ Stopped playback (bot disconnecting)"
                    else:
                        presence_status = f"✅ Stopped playback (presence clear failed: {type(e).__name__})"
            else:
                presence_status = "✅ Stopped playback (bot already closed)"

            log_perfect_tree_section(
                "Rich Presence - Track Stopped",
                [
                    ("status", "🛑 Stopping track"),
                    ("task_cleanup", task_status),
                    ("presence_status", presence_status),
                ],
                "🛑",
            )

        except discord.HTTPException as e:
            log_error_with_traceback("Discord API error stopping Rich Presence", e)
        except Exception as e:
            # Check if it's a connection-related error during shutdown
            if "closing transport" in str(e) or "ConnectionReset" in str(
                type(e).__name__
            ):
                log_perfect_tree_section(
                    "Rich Presence - Track Stopped (Connection Closing)",
                    [
                        ("status", "✅ Stopped playback (connection closing)"),
                        ("error_type", type(e).__name__),
                    ],
                    "🛑",
                )
            else:
                log_error_with_traceback("Error stopping track in Rich Presence", e)

    async def update_progress(self):
        """
        Update rich presence with current playback progress
        Runs continuously while track is playing
        """
        try:
            log_perfect_tree_section(
                "Rich Presence - Progress Updates",
                [
                    ("status", "🔄 Starting progress updates"),
                    (
                        "track",
                        (
                            self.current_track["surah_number"]
                            if self.current_track
                            else "Unknown"
                        ),
                    ),
                ],
                "🔄",
            )
            update_count = 0

            while self.is_playing and self.current_track:
                try:
                    if self.track_start_time is None:
                        await asyncio.sleep(1)
                        continue

                    # Calculate current position
                    current_time = time.time() - self.track_start_time

                    # Clamp current time to not exceed total duration
                    if self.track_duration and current_time > self.track_duration:
                        current_time = self.track_duration

                    # Check if track should be finished
                    if self.track_duration and current_time >= self.track_duration:
                        log_perfect_tree_section(
                            "Rich Presence - Track Complete",
                            [
                                ("status", "✅ Track duration reached"),
                                ("final_time", self.format_time(current_time)),
                            ],
                            "✅",
                        )
                        break

                    # Get Surah info
                    surah_info = get_surah_info(self.current_track["surah_number"])
                    if not surah_info:
                        log_warning_with_context(
                            "Could not get Surah info during progress update",
                            f"Surah: {self.current_track['surah_number']}",
                        )
                        await asyncio.sleep(1)
                        continue

                    # Format time display
                    current_formatted = self.format_time(current_time)
                    total_formatted = (
                        self.format_time(self.track_duration)
                        if self.track_duration
                        else "∞"
                    )
                    time_display = f"{current_formatted} / {total_formatted}"

                    # Generate progress bar
                    progress_bar = self.get_progress_bar(
                        current_time, self.track_duration
                    )

                    # Create rich presence activity - emoji and transliterated Arabic name with timer
                    activity = discord.Activity(
                        type=discord.ActivityType.listening,
                        name=f"{surah_info.emoji} {surah_info.name_transliteration} • {time_display}",
                    )

                    # Only update presence if bot is still connected
                    if self.bot and not self.bot.is_closed():
                        try:
                            await self.bot.change_presence(activity=activity)
                        except (
                            ClientConnectionResetError,
                            discord.ConnectionClosed,
                        ) as e:
                            # Connection is closing, stop updates gracefully
                            log_perfect_tree_section(
                                "Rich Presence - Disconnecting",
                                [
                                    (
                                        "status",
                                        "🛑 Bot disconnecting, stopping updates",
                                    ),
                                    ("error_type", type(e).__name__),
                                ],
                                "🛑",
                            )
                            break
                        except discord.HTTPException as e:
                            log_error_with_traceback(
                                "Discord API error during progress update", e
                            )
                            await asyncio.sleep(10)  # Wait longer on Discord errors
                            continue

                    update_count += 1
                    if (
                        update_count % 120 == 0
                    ):  # Log every 10 minutes (120 * 5 seconds)
                        log_perfect_tree_section(
                            "Rich Presence - Progress Update",
                            [
                                ("time_display", f"🎵 {time_display}"),
                                ("updates_count", update_count),
                            ],
                            "🎵",
                        )

                    # Update every 5 seconds to avoid rate limiting
                    await asyncio.sleep(5)

                except (ClientConnectionResetError, discord.ConnectionClosed):
                    # Connection is closing, stop updates gracefully
                    log_perfect_tree_section(
                        "Rich Presence - Connection Lost",
                        [
                            ("status", "🛑 Bot disconnecting, stopping updates"),
                            ("context", "Progress update loop"),
                        ],
                        "🛑",
                    )
                    break
                except discord.HTTPException as e:
                    log_error_with_traceback(
                        "Discord API error during progress update", e
                    )
                    await asyncio.sleep(10)  # Wait longer on Discord errors
                except Exception as e:
                    log_error_with_traceback("Error in progress update loop", e)
                    await asyncio.sleep(5)

            log_perfect_tree_section(
                "Rich Presence - Updates Complete",
                [
                    ("status", "✅ Progress updates completed"),
                    ("total_updates", update_count),
                ],
                "✅",
            )

        except asyncio.CancelledError:
            # Task was cancelled, this is expected
            log_perfect_tree_section(
                "Rich Presence - Updates Cancelled",
                [
                    ("status", "🛑 Progress updates cancelled"),
                    ("reason", "Task cancellation"),
                ],
                "🛑",
            )
        except Exception as e:
            log_async_error("update_progress", e, "Rich Presence progress update")

    async def pause_track(self):
        """Pause the current track (stops progress updates but keeps state)"""
        try:
            if not self.is_playing or not self.current_track:
                log_warning_with_context(
                    "Attempted to pause when not playing", "No active track"
                )
                return

            log_perfect_tree_section(
                "Rich Presence - Pause Track",
                [
                    ("status", "⏸️ Pausing track"),
                    ("track", self.current_track["surah_number"]),
                ],
                "⏸️",
            )
            self.is_playing = False

            # Stop the update task
            if self.update_task and not self.update_task.done():
                self.update_task.cancel()
                try:
                    await self.update_task
                except asyncio.CancelledError:
                    pass

            # Update rich presence to show paused state - emoji and transliterated Arabic name
            surah_info = get_surah_info(self.current_track["surah_number"])
            if surah_info:
                activity = discord.Activity(
                    type=discord.ActivityType.listening,
                    name=f"{surah_info.emoji} {surah_info.name_transliteration} • ⏸️ Paused",
                )
                await self.bot.change_presence(activity=activity)
                log_perfect_tree_section(
                    "Rich Presence - Pause Complete",
                    [
                        ("status", "✅ Paused playback"),
                        ("surah", surah_info.name_transliteration),
                    ],
                    "⏸️",
                )
            else:
                log_warning_with_context(
                    "Could not update Rich Presence for pause",
                    f"Surah: {self.current_track['surah_number']}",
                )

        except discord.HTTPException as e:
            log_error_with_traceback("Discord API error pausing Rich Presence", e)
        except Exception as e:
            log_error_with_traceback("Error pausing track in Rich Presence", e)

    async def resume_track(self):
        """Resume the current track (restarts progress updates)"""
        try:
            if self.is_playing or not self.current_track:
                log_warning_with_context(
                    "Attempted to resume when already playing or no track",
                    "Check state",
                )
                return

            log_perfect_tree_section(
                "Rich Presence - Resume Track",
                [
                    ("status", "▶️ Resuming track"),
                    ("track", self.current_track["surah_number"]),
                ],
                "▶️",
            )

            # Adjust start time to account for pause duration
            if self.track_start_time:
                current_time = time.time() - self.track_start_time
                self.track_start_time = time.time() - current_time
            else:
                self.track_start_time = time.time()

            self.is_playing = True

            # Restart the progress update task
            self.update_task = self.bot.loop.create_task(self.update_progress())
            log_perfect_tree_section(
                "Rich Presence - Resume Complete",
                [
                    ("status", "✅ Resumed playback"),
                    ("progress_task", "✅ Progress updates restarted"),
                ],
                "▶️",
            )

        except Exception as e:
            log_error_with_traceback("Error resuming track in Rich Presence", e)

    def is_active(self):
        """
        Check if Rich Presence is currently active

        Returns:
            bool: True if currently tracking a track
        """
        try:
            return self.is_playing and self.current_track is not None
        except Exception as e:
            log_error_with_traceback("Error checking Rich Presence active state", e)
            return False

    def get_current_track_info(self):
        """
        Get information about the currently playing track

        Returns:
            dict: Current track information or None
        """
        try:
            if self.current_track:
                current_time = (
                    time.time() - self.track_start_time if self.track_start_time else 0
                )

                # Clamp current time to not exceed total duration
                if self.track_duration and current_time > self.track_duration:
                    current_time = self.track_duration

                return {
                    "surah_number": self.current_track["surah_number"],
                    "reciter": self.current_track["reciter"],
                    "current_time": current_time,
                    "duration": self.track_duration,
                    "is_playing": self.is_playing,
                }
            return None
        except Exception as e:
            log_error_with_traceback("Error getting current track info", e)
            return None

    async def seek_to_position(self, position_seconds: float):
        """
        Seek to a specific position in the current track

        Args:
            position_seconds: Position to seek to in seconds
        """
        try:
            if not self.current_track or not self.is_playing:
                log_warning_with_context(
                    "Cannot seek - no active track",
                    f"Position: {position_seconds:.1f}s",
                )
                return

            # Validate position
            if self.track_duration and position_seconds > self.track_duration:
                position_seconds = self.track_duration

            if position_seconds < 0:
                position_seconds = 0

            # Adjust the start time to simulate seeking
            self.track_start_time = time.time() - position_seconds

            log_perfect_tree_section(
                "Rich Presence - Seek Position",
                [
                    ("position", f"{position_seconds:.1f}s"),
                    ("status", "✅ Seeked to new position"),
                    ("track", self.current_track["surah_number"]),
                ],
                "⏩",
            )

        except Exception as e:
            log_error_with_traceback("Error seeking to position in Rich Presence", e)


# =============================================================================
# Utility Functions
# =============================================================================
def validate_rich_presence_dependencies(ffmpeg_path="ffmpeg"):
    """
    Validate that required dependencies for Rich Presence are available

    Args:
        ffmpeg_path: Path to FFmpeg executable

    Returns:
        dict: Validation results with status and warnings
    """
    try:
        results = {"ffmpeg": False, "ffprobe": False, "warnings": []}

        # Check FFmpeg
        try:
            subprocess.run(
                [ffmpeg_path, "-version"], capture_output=True, check=True, timeout=5
            )
            results["ffmpeg"] = True
            log_perfect_tree_section(
                "Rich Presence - FFmpeg Check",
                [
                    ("ffmpeg_path", ffmpeg_path),
                    ("status", "✅ FFmpeg is accessible"),
                ],
                "✅",
            )
        except subprocess.TimeoutExpired:
            results["warnings"].append("FFmpeg check timed out - may be slow")
            log_warning_with_context("FFmpeg validation timeout", "Check may be slow")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            results["warnings"].append(
                f"FFmpeg not found at '{ffmpeg_path}' - Rich Presence may be limited"
            )
            log_perfect_tree_section(
                "Rich Presence - FFmpeg Error",
                [
                    ("ffmpeg_path", ffmpeg_path),
                    ("status", f"❌ FFmpeg not accessible: {e}"),
                    ("warning", "Rich Presence may be limited"),
                ],
                "❌",
            )

        # Check FFprobe
        try:
            ffprobe_path = ffmpeg_path.replace("ffmpeg", "ffprobe")
            subprocess.run(
                [ffprobe_path, "-version"], capture_output=True, check=True, timeout=5
            )
            results["ffprobe"] = True
            log_perfect_tree_section(
                "Rich Presence - FFprobe Check",
                [
                    ("ffprobe_path", ffprobe_path),
                    ("status", "✅ FFprobe is accessible"),
                ],
                "✅",
            )
        except subprocess.TimeoutExpired:
            results["warnings"].append("FFprobe check timed out - may be slow")
            log_warning_with_context("FFprobe validation timeout", "Check may be slow")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            results["warnings"].append(
                "FFprobe not found - Rich Presence progress bars will be limited"
            )
            log_perfect_tree_section(
                "Rich Presence - FFprobe Error",
                [
                    ("ffprobe_path", ffprobe_path),
                    ("status", f"❌ FFprobe not accessible: {e}"),
                    ("warning", "Progress bars will be limited"),
                ],
                "❌",
            )

        # Summary
        if results["ffmpeg"] and results["ffprobe"]:
            validation_status = "✅ All Rich Presence dependencies available"
        elif results["ffmpeg"]:
            validation_status = "⚠️ FFmpeg available, FFprobe missing"
        else:
            validation_status = "❌ Critical Rich Presence dependencies missing"

        log_perfect_tree_section(
            "Rich Presence Dependencies Validation",
            [
                ("ffmpeg", "✅ Available" if results["ffmpeg"] else "❌ Missing"),
                ("ffprobe", "✅ Available" if results["ffprobe"] else "❌ Missing"),
                ("result", validation_status),
                ("warnings_count", len(results["warnings"])),
            ],
            "🔍",
        )

        return results

    except Exception as e:
        log_critical_error("Failed to validate Rich Presence dependencies", e)
        return {"ffmpeg": False, "ffprobe": False, "warnings": ["Validation failed"]}


# =============================================================================
# Export Rich Presence Manager
# =============================================================================
__all__ = ["RichPresenceManager", "validate_rich_presence_dependencies"]
