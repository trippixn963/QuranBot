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

from .surah_mapper import get_surah_info
from .tree_log import (
    log_async_error,
    log_critical_error,
    log_error_with_traceback,
    log_section_start,
    log_tree,
    log_tree_branch,
    log_tree_end,
    log_tree_final,
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
            log_section_start("Rich Presence Manager Initialization", "🎵")

            self.bot = bot
            self.ffmpeg_path = ffmpeg_path
            self.current_track = None
            self.track_start_time = None
            self.track_duration = None
            self.is_playing = False
            self.update_task = None

            log_tree_branch("ffmpeg_path", ffmpeg_path)
            log_tree_final("initialization", "✅ Rich Presence Manager ready")

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
            log_tree_branch(
                "duration_detection", f"Analyzing: {os.path.basename(audio_file)}"
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
                log_tree_branch(
                    "audio_duration",
                    f"✅ {self.format_time(duration)} ({duration:.1f}s)",
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
        Format seconds to MM:SS format

        Args:
            seconds: Time in seconds

        Returns:
            str: Formatted time string (MM:SS)
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

            minutes = int(seconds // 60)
            seconds = int(seconds % 60)
            return f"{minutes:02d}:{seconds:02d}"

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
            log_section_start("Starting Rich Presence Track", "🎵")
            log_tree_branch("surah_number", surah_number)
            log_tree_branch("audio_file", os.path.basename(audio_file))
            log_tree_branch("reciter", reciter)

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
                # Set initial rich presence - emoji and Arabic name with starting message
                activity = discord.Activity(
                    type=discord.ActivityType.listening,
                    name=f"{surah_info.emoji} {surah_info.name_arabic} • 🎵 Starting...",
                )

                await self.bot.change_presence(activity=activity)
                log_tree_branch(
                    "rich_presence", f"✅ Started: {surah_info.name_english}"
                )

                # Start the progress update task
                self.update_task = self.bot.loop.create_task(self.update_progress())
                log_tree_final("progress_task", "✅ Progress update task started")
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

            log_tree_branch("rich_presence", "🛑 Stopping track")

            # Stop the update task
            if self.update_task and not self.update_task.done():
                self.update_task.cancel()
                try:
                    await self.update_task
                    log_tree_branch("task_cleanup", "✅ Progress task cancelled")
                except asyncio.CancelledError:
                    log_tree_branch(
                        "task_cleanup", "✅ Progress task cancelled gracefully"
                    )

            # Reset state
            self.is_playing = False
            self.current_track = None
            self.track_start_time = None
            self.track_duration = None
            self.update_task = None

            # Clear rich presence
            await self.bot.change_presence(activity=None)
            log_tree_final("rich_presence", "✅ Stopped playback and cleared presence")

        except discord.HTTPException as e:
            log_error_with_traceback("Discord API error stopping Rich Presence", e)
        except Exception as e:
            log_error_with_traceback("Error stopping track in Rich Presence", e)

    async def update_progress(self):
        """
        Update rich presence with current playback progress
        Runs continuously while track is playing
        """
        try:
            log_tree_branch("progress_updates", "🔄 Starting progress updates")
            update_count = 0

            while self.is_playing and self.current_track:
                try:
                    if self.track_start_time is None:
                        await asyncio.sleep(1)
                        continue

                    # Calculate current position
                    current_time = time.time() - self.track_start_time

                    # Check if track should be finished
                    if self.track_duration and current_time >= self.track_duration:
                        log_tree_branch(
                            "progress_complete", "✅ Track duration reached"
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

                    # Create rich presence activity - emoji and Arabic name with timer
                    activity = discord.Activity(
                        type=discord.ActivityType.listening,
                        name=f"{surah_info.emoji} {surah_info.name_arabic} • {time_display}",
                    )

                    await self.bot.change_presence(activity=activity)

                    update_count += 1
                    if update_count % 12 == 0:  # Log every minute (12 * 5 seconds)
                        log_tree_branch("progress_update", f"🎵 {time_display}")

                    # Update every 5 seconds to avoid rate limiting
                    await asyncio.sleep(5)

                except discord.HTTPException as e:
                    log_error_with_traceback(
                        "Discord API error during progress update", e
                    )
                    await asyncio.sleep(10)  # Wait longer on Discord errors
                except Exception as e:
                    log_error_with_traceback("Error in progress update loop", e)
                    await asyncio.sleep(5)

            log_tree_final("progress_updates", "✅ Progress updates completed")

        except asyncio.CancelledError:
            # Task was cancelled, this is expected
            log_tree_branch("progress_updates", "🛑 Progress updates cancelled")
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

            log_tree_branch("rich_presence", "⏸️ Pausing track")
            self.is_playing = False

            # Stop the update task
            if self.update_task and not self.update_task.done():
                self.update_task.cancel()
                try:
                    await self.update_task
                except asyncio.CancelledError:
                    pass

            # Update rich presence to show paused state - emoji and Arabic name
            surah_info = get_surah_info(self.current_track["surah_number"])
            if surah_info:
                activity = discord.Activity(
                    type=discord.ActivityType.listening,
                    name=f"{surah_info.emoji} {surah_info.name_arabic} • ⏸️ Paused",
                )
                await self.bot.change_presence(activity=activity)
                log_tree_final("rich_presence", "✅ Paused playback")
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

            log_tree_branch("rich_presence", "▶️ Resuming track")

            # Adjust start time to account for pause duration
            if self.track_start_time:
                current_time = time.time() - self.track_start_time
                self.track_start_time = time.time() - current_time
            else:
                self.track_start_time = time.time()

            self.is_playing = True

            # Restart the progress update task
            self.update_task = self.bot.loop.create_task(self.update_progress())
            log_tree_final("rich_presence", "✅ Resumed playback")

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
        log_section_start("Rich Presence Dependencies Validation", "🔍")
        results = {"ffmpeg": False, "ffprobe": False, "warnings": []}

        # Check FFmpeg
        try:
            subprocess.run(
                [ffmpeg_path, "-version"], capture_output=True, check=True, timeout=5
            )
            results["ffmpeg"] = True
            log_tree_branch("rich_presence_deps", "✅ FFmpeg is accessible")
        except subprocess.TimeoutExpired:
            results["warnings"].append("FFmpeg check timed out - may be slow")
            log_warning_with_context("FFmpeg validation timeout", "Check may be slow")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            results["warnings"].append(
                f"FFmpeg not found at '{ffmpeg_path}' - Rich Presence may be limited"
            )
            log_tree_branch("rich_presence_deps", f"❌ FFmpeg not accessible: {e}")

        # Check FFprobe
        try:
            ffprobe_path = ffmpeg_path.replace("ffmpeg", "ffprobe")
            subprocess.run(
                [ffprobe_path, "-version"], capture_output=True, check=True, timeout=5
            )
            results["ffprobe"] = True
            log_tree_branch("rich_presence_deps", "✅ FFprobe is accessible")
        except subprocess.TimeoutExpired:
            results["warnings"].append("FFprobe check timed out - may be slow")
            log_warning_with_context("FFprobe validation timeout", "Check may be slow")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            results["warnings"].append(
                "FFprobe not found - Rich Presence progress bars will be limited"
            )
            log_tree_branch("rich_presence_deps", f"❌ FFprobe not accessible: {e}")

        # Summary
        if results["ffmpeg"] and results["ffprobe"]:
            log_tree_final(
                "validation_result", "✅ All Rich Presence dependencies available"
            )
        elif results["ffmpeg"]:
            log_tree_final("validation_result", "⚠️ FFmpeg available, FFprobe missing")
        else:
            log_tree_final(
                "validation_result", "❌ Critical Rich Presence dependencies missing"
            )

        return results

    except Exception as e:
        log_critical_error("Failed to validate Rich Presence dependencies", e)
        return {"ffmpeg": False, "ffprobe": False, "warnings": ["Validation failed"]}


# =============================================================================
# Export Rich Presence Manager
# =============================================================================
__all__ = ["RichPresenceManager", "validate_rich_presence_dependencies"]
