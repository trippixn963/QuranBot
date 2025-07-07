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

from .state_manager import state_manager
from .surah_mapper import (
    format_now_playing,
    get_surah_display,
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


class AudioManager:
    """Manages audio playback state and controls"""

    def __init__(
        self,
        bot,
        ffmpeg_path: str,
        audio_base_folder: str = "audio",
        default_reciter: str = "Saad Al Ghamdi",
        default_shuffle: bool = False,
        default_loop: bool = False,
    ):
        self.bot = bot
        self.ffmpeg_path = ffmpeg_path
        self.audio_base_folder = audio_base_folder
        self.voice_client: Optional[discord.VoiceClient] = None
        self.rich_presence = None

        # Store default values from environment
        self.default_reciter = default_reciter
        self.default_shuffle = default_shuffle
        self.default_loop = default_loop

        # Playback state - will be restored from saved state
        self.current_surah = 1
        self.current_reciter = default_reciter
        self.current_position = 0.0  # Position in seconds within current track
        self.is_playing = False
        self.is_paused = False
        self.is_loop_enabled = default_loop
        self.is_shuffle_enabled = default_shuffle
        self.current_audio_files: List[str] = []
        self.current_file_index = 0

        # Jump operation flag to prevent automatic index increment
        self._jump_occurred = False

        # Control panel reference
        self.control_panel_view = None

        # Playback task
        self.playback_task: Optional[asyncio.Task] = None
        self.position_save_task: Optional[asyncio.Task] = None

        # Available reciters (based on audio folder structure)
        self.available_reciters = self._discover_reciters()

        # Load previous state
        self._load_saved_state()

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
            if self.position_save_task and not self.position_save_task.done():
                self.position_save_task.cancel()

            self.position_save_task = asyncio.create_task(self._position_save_loop())
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
            while True:
                await asyncio.sleep(5)  # Save every 5 seconds

                if self.is_playing and self.rich_presence:
                    try:
                        # Get current position from rich presence
                        track_info = self.rich_presence.get_current_track_info()
                        if track_info:
                            current_time = track_info.get("current_time", 0)
                            total_time = track_info.get("duration", 0)

                            # Save state
                            state_manager.save_playback_state(
                                current_surah=self.current_surah,
                                current_position=current_time,
                                current_reciter=self.current_reciter,
                                total_duration=total_time,
                                is_playing=self.is_playing,
                                loop_enabled=self.is_loop_enabled,
                                shuffle_enabled=self.is_shuffle_enabled,
                            )
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
        """Start the audio playback loop"""
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

            # Start position saving
            self._start_position_saving()

            # Start new playback task
            self.playback_task = asyncio.create_task(
                self._playback_loop(resume_position=resume_position)
            )
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
            log_async_error("start_playback", e, f"Reciter: {self.current_reciter}")

    async def stop_playback(self):
        """Stop the audio playback"""
        try:
            # Save final state before stopping
            if self.is_playing:
                try:
                    if self.rich_presence:
                        track_info = self.rich_presence.get_current_track_info()
                        if track_info:
                            current_time = track_info.get("current_time", 0)
                            total_time = track_info.get("duration", 0)

                            state_manager.save_playback_state(
                                current_surah=self.current_surah,
                                current_position=current_time,
                                current_reciter=self.current_reciter,
                                total_duration=total_time,
                                is_playing=False,
                                loop_enabled=self.is_loop_enabled,
                                shuffle_enabled=self.is_shuffle_enabled,
                            )
                except Exception as e:
                    log_error_with_traceback("Error saving final state", e)

            # Stop position saving task
            if self.position_save_task and not self.position_save_task.done():
                self.position_save_task.cancel()

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

                    # Log successful update
                    log_perfect_tree_section(
                        "Audio Manager - Surah Update",
                        [
                            (
                                "update_debug_index",
                                f"Using file index: {self.current_file_index}",
                            ),
                            ("update_debug_file", f"Reading file: {filename}"),
                            ("surah_updated", f"Current: {surah_number}"),
                        ],
                        "📖",
                    )
            except (ValueError, IndexError):
                log_warning_with_context(
                    "Could not parse Surah number from filename",
                    f"Filename: {filename}",
                )

        except Exception as e:
            log_error_with_traceback("Error updating current Surah", e)

    async def _playback_loop(self, resume_position: bool = True):
        """Main playback loop with resume capability"""
        try:
            # Check if we should resume from saved position
            should_resume = resume_position and self.current_position > 0

            resume_items = [("playback_loop_started", "Beginning audio playback loop")]
            if should_resume:
                resume_items.append(
                    ("resuming_playback", f"Resuming from {self.current_position:.1f}s")
                )

            log_perfect_tree_section(
                "Audio Playback Loop - Started",
                resume_items,
                "🎵",
            )

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
                                await self.rich_presence.start_track(
                                    self.current_surah,
                                    current_file,
                                    self.current_reciter,
                                )

                                # If resuming, seek to saved position
                                if should_resume:
                                    await self.rich_presence.seek_to_position(
                                        self.current_position
                                    )
                                    should_resume = False  # Only resume once

                            except Exception as e:
                                log_error_with_traceback(
                                    "Error starting rich presence track", e
                                )

                    # Create and play audio source with resume capability
                    try:
                        if should_resume and self.current_position > 0:
                            # Use FFmpeg to start from specific position
                            seek_options = f"-ss {self.current_position}"
                            source = discord.FFmpegPCMAudio(
                                current_file,
                                executable=self.ffmpeg_path,
                                before_options=seek_options,
                                options="-vn",
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
                                current_file, executable=self.ffmpeg_path, options="-vn"
                            )

                        self.voice_client.play(source)
                        self.is_playing = True
                        self.is_paused = False

                        # Update control panel
                        if self.control_panel_view:
                            try:
                                await self.control_panel_view.update_panel()
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

                        # Mark surah as completed
                        state_manager.mark_surah_completed()

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

                    # Reset position for next track
                    self.current_position = 0.0

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

                    # 24/7 mode - never break the loop, always continue playing

                except Exception as e:
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

            # Get time information from rich presence if available
            if self.rich_presence:
                try:
                    track_info = self.rich_presence.get_current_track_info()
                    if track_info:
                        status["current_time"] = track_info.get("current_time", 0)
                        status["total_time"] = track_info.get("duration", 0)
                except Exception as e:
                    log_error_with_traceback("Error getting time from rich presence", e)

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
