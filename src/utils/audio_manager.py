# =============================================================================
# QuranBot - Audio Manager
# =============================================================================
# Manages audio playback state and controls for integration with control panel
# =============================================================================

import asyncio
import glob
import os
from typing import Any, Dict, List, Optional

import discord

from utils.surah_mapper import (
    format_now_playing,
    get_surah_display,
    get_surah_name,
    validate_surah_number,
)
from utils.tree_log import (
    log_async_error,
    log_error_with_traceback,
    log_progress,
    log_section_start,
    log_tree_branch,
    log_tree_final,
    log_warning_with_context,
)


class AudioManager:
    """Manages audio playback state and controls"""

    def __init__(self, bot, ffmpeg_path: str, audio_base_folder: str = "audio"):
        self.bot = bot
        self.ffmpeg_path = ffmpeg_path
        self.audio_base_folder = audio_base_folder
        self.voice_client: Optional[discord.VoiceClient] = None
        self.rich_presence = None

        # Playback state
        self.current_surah = 1
        self.current_reciter = "Saad Al Ghamdi"
        self.is_playing = False
        self.is_paused = False
        self.is_loop_enabled = False
        self.is_shuffle_enabled = False
        self.current_audio_files: List[str] = []
        self.current_file_index = 0

        # Control panel reference
        self.control_panel_view = None

        # Playback task
        self.playback_task: Optional[asyncio.Task] = None

        # Available reciters (based on audio folder structure)
        self.available_reciters = self._discover_reciters()

    def _discover_reciters(self) -> List[str]:
        """Discover available reciters from audio folder structure"""
        try:
            log_tree_branch(
                "discovering_reciters", f"Scanning: {self.audio_base_folder}"
            )
            reciters = []

            if os.path.exists(self.audio_base_folder):
                for item in os.listdir(self.audio_base_folder):
                    folder_path = os.path.join(self.audio_base_folder, item)
                    if os.path.isdir(folder_path):
                        # Check if folder contains mp3 files
                        mp3_files = glob.glob(os.path.join(folder_path, "*.mp3"))
                        if mp3_files:
                            reciters.append(item)
                            log_tree_branch(
                                "reciter_found", f"{item} ({len(mp3_files)} files)"
                            )

            result = sorted(reciters) if reciters else ["Saad Al Ghamdi"]
            log_tree_final("reciters_discovered", f"{len(result)} reciters available")
            return result

        except Exception as e:
            log_error_with_traceback("Error discovering reciters", e)
            return ["Saad Al Ghamdi"]

    def set_rich_presence(self, rich_presence_manager):
        """Set the rich presence manager"""
        try:
            self.rich_presence = rich_presence_manager
            log_tree_branch("rich_presence_set", "✅ Rich presence manager connected")
        except Exception as e:
            log_error_with_traceback("Error setting rich presence manager", e)

    def set_control_panel(self, control_panel_view):
        """Set the control panel view for updates"""
        try:
            self.control_panel_view = control_panel_view
            log_tree_branch("control_panel_set", "✅ Control panel view connected")
        except Exception as e:
            log_error_with_traceback("Error setting control panel view", e)

    def set_voice_client(self, voice_client: discord.VoiceClient):
        """Set the voice client for audio playback"""
        try:
            self.voice_client = voice_client
            log_tree_branch("voice_client_set", "✅ Voice client connected")
        except Exception as e:
            log_error_with_traceback("Error setting voice client", e)

    def get_current_audio_folder(self) -> str:
        """Get the current audio folder path"""
        return os.path.join(self.audio_base_folder, self.current_reciter)

    def load_audio_files(self) -> bool:
        """Load audio files for current reciter"""
        try:
            log_tree_branch("loading_audio_files", f"Reciter: {self.current_reciter}")
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

            log_tree_branch(
                "audio_files_loaded", f"{len(self.current_audio_files)} files"
            )
            return True

        except Exception as e:
            log_error_with_traceback("Error loading audio files", e)
            return False

    async def start_playback(self):
        """Start the audio playback loop"""
        try:
            log_tree_branch("starting_playback", "Initializing audio playback")

            if not self.voice_client or not self.voice_client.is_connected():
                log_warning_with_context(
                    "Cannot start playback", "Voice client not connected"
                )
                return

            if not self.load_audio_files():
                log_warning_with_context(
                    "Cannot start playback", "No audio files loaded"
                )
                return

            # Stop any existing playback
            await self.stop_playback()

            # Start new playback task
            self.playback_task = asyncio.create_task(self._playback_loop())
            log_tree_branch("playback_started", "✅ Audio playback started")

        except Exception as e:
            log_async_error("start_playback", e, f"Reciter: {self.current_reciter}")

    async def stop_playback(self):
        """Stop the audio playback"""
        try:
            log_tree_branch("stopping_playback", "Cleaning up audio playback")

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
                    await self.rich_presence.stop_track()
                except Exception as e:
                    log_error_with_traceback("Error stopping rich presence", e)

            self.is_playing = False
            self.is_paused = False

            # Update control panel
            if self.control_panel_view:
                try:
                    await self.control_panel_view.update_display()
                except Exception as e:
                    log_error_with_traceback("Error updating control panel", e)

            log_tree_branch("playback_stopped", "✅ Audio playback stopped")

        except Exception as e:
            log_async_error("stop_playback", e, "Failed to stop playback cleanly")

    async def pause_playback(self):
        """Pause the audio playback"""
        try:
            if self.voice_client and self.voice_client.is_playing():
                self.voice_client.pause()
                self.is_paused = True
                log_tree_branch("playback_paused", "⏸️ Audio paused")

                # Update control panel
                if self.control_panel_view:
                    try:
                        await self.control_panel_view.update_display()
                    except Exception as e:
                        log_error_with_traceback(
                            "Error updating control panel after pause", e
                        )

        except Exception as e:
            log_async_error("pause_playback", e, "Failed to pause playback")

    async def resume_playback(self):
        """Resume the audio playback"""
        try:
            if self.voice_client and self.voice_client.is_paused():
                self.voice_client.resume()
                self.is_paused = False
                log_tree_branch("playback_resumed", "▶️ Audio resumed")

                # Update control panel
                if self.control_panel_view:
                    try:
                        await self.control_panel_view.update_display()
                    except Exception as e:
                        log_error_with_traceback(
                            "Error updating control panel after resume", e
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
            log_tree_branch("skipped_to_next", f"Track {self.current_file_index + 1}")

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
            log_tree_branch(
                "skipped_to_previous", f"Track {self.current_file_index + 1}"
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

            for i, audio_file in enumerate(self.current_audio_files):
                if os.path.basename(audio_file) == target_filename:
                    target_index = i
                    break

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

            log_tree_branch(
                "jumped_to_surah",
                f"Surah {surah_number}: {get_surah_name(surah_number)}",
            )

        except Exception as e:
            log_async_error("jump_to_surah", e, f"Target Surah: {surah_number}")

    async def switch_reciter(self, reciter_name: str):
        """Switch to a different reciter"""
        try:
            log_tree_branch(
                "switching_reciter", f"From {self.current_reciter} to {reciter_name}"
            )

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
                log_tree_branch("reciter_switched", f"{old_reciter} → {reciter_name}")

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
        """Toggle loop mode"""
        try:
            self.is_loop_enabled = not self.is_loop_enabled
            log_tree_branch("loop_toggled", "ON" if self.is_loop_enabled else "OFF")
        except Exception as e:
            log_error_with_traceback("Error toggling loop mode", e)

    def toggle_shuffle(self):
        """Toggle shuffle mode"""
        try:
            self.is_shuffle_enabled = not self.is_shuffle_enabled
            log_tree_branch(
                "shuffle_toggled", "ON" if self.is_shuffle_enabled else "OFF"
            )
        except Exception as e:
            log_error_with_traceback("Error toggling shuffle mode", e)

    def _update_current_surah(self):
        """Update current Surah based on current file index"""
        try:
            if not self.current_audio_files or self.current_file_index >= len(
                self.current_audio_files
            ):
                return

            current_file = self.current_audio_files[self.current_file_index]
            filename = os.path.basename(current_file)

            try:
                surah_number = int(filename.split(".")[0])
                if validate_surah_number(surah_number):
                    self.current_surah = surah_number
                    log_tree_branch("surah_updated", f"Current: {surah_number}")
            except (ValueError, IndexError):
                log_warning_with_context(
                    "Could not parse Surah number from filename",
                    f"Filename: {filename}",
                )

        except Exception as e:
            log_error_with_traceback("Error updating current Surah", e)

    async def _playback_loop(self):
        """Main playback loop"""
        try:
            log_tree_branch("playback_loop_started", "Beginning audio playback loop")

            while True:
                try:
                    if not self.voice_client or not self.voice_client.is_connected():
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
                            log_tree_branch("playback_complete", "All tracks played")
                            break

                    current_file = self.current_audio_files[self.current_file_index]
                    filename = os.path.basename(current_file)

                    # Update current Surah
                    self._update_current_surah()

                    # Log current track
                    log_progress(
                        self.current_file_index + 1, len(self.current_audio_files)
                    )

                    if validate_surah_number(self.current_surah):
                        surah_display = get_surah_display(
                            self.current_surah, "detailed"
                        )
                        log_tree_branch("surah", surah_display)

                        # Start Rich Presence tracking
                        if self.rich_presence:
                            try:
                                await self.rich_presence.start_track(
                                    self.current_surah,
                                    current_file,
                                    self.current_reciter,
                                )
                            except Exception as e:
                                log_error_with_traceback(
                                    "Error starting rich presence track", e
                                )

                    # Create and play audio source
                    try:
                        source = discord.FFmpegPCMAudio(
                            current_file, executable=self.ffmpeg_path, options="-vn"
                        )

                        self.voice_client.play(source)
                        self.is_playing = True
                        self.is_paused = False

                        # Update control panel
                        if self.control_panel_view:
                            try:
                                await self.control_panel_view.update_display()
                            except Exception as e:
                                log_error_with_traceback(
                                    "Error updating control panel during playback", e
                                )

                        # Wait for playback to finish
                        while (
                            self.voice_client.is_playing()
                            or self.voice_client.is_paused()
                        ):
                            await asyncio.sleep(1)

                    except Exception as e:
                        log_error_with_traceback(
                            f"Error playing audio file: {filename}", e
                        )
                        # Continue to next track on error

                    finally:
                        # Stop Rich Presence for this track
                        if self.rich_presence:
                            try:
                                await self.rich_presence.stop_track()
                            except Exception as e:
                                log_error_with_traceback(
                                    "Error stopping rich presence track", e
                                )

                    # Move to next track
                    if self.is_shuffle_enabled:
                        import random

                        self.current_file_index = random.randint(
                            0, len(self.current_audio_files) - 1
                        )
                    else:
                        self.current_file_index += 1

                    # Check if we should loop
                    if (
                        self.current_file_index >= len(self.current_audio_files)
                        and not self.is_loop_enabled
                    ):
                        break

                except Exception as e:
                    log_error_with_traceback("Error in playback loop iteration", e)
                    # Wait a bit before continuing to avoid rapid error loops
                    await asyncio.sleep(2)

        except asyncio.CancelledError:
            log_tree_branch("playback_cancelled", "Playback loop cancelled")
        except Exception as e:
            log_error_with_traceback("Critical error in playback loop", e)
        finally:
            try:
                self.is_playing = False
                self.is_paused = False

                # Update control panel
                if self.control_panel_view:
                    try:
                        await self.control_panel_view.update_display()
                    except Exception as e:
                        log_error_with_traceback(
                            "Error updating control panel in finally block", e
                        )

                log_tree_branch("playback_loop_ended", "Audio playback loop terminated")

            except Exception as e:
                log_error_with_traceback("Error in playback loop cleanup", e)

    def get_playback_status(self) -> Dict[str, Any]:
        """Get current playback status for control panel"""
        try:
            return {
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
            }
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
            }
