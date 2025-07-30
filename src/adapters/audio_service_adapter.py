# =============================================================================
# QuranBot - Audio Service Adapter
# =============================================================================
# Adapter to make AudioService compatible with the control panel's expectations.
# This adapter bridges the gap between the modern AudioService and legacy
# control panel interface, providing backward compatibility while using
# modern architecture patterns.
# =============================================================================

import traceback
from pathlib import Path
from typing import Dict, Any

from src.data.models import PlaybackMode
from src.services.audio_service import AudioService


class AudioServiceAdapter:
    """
    Adapter to make AudioService compatible with the control panel's expectations.

    The control panel was designed for the old AudioManager, but we're using the new AudioService.
    This adapter bridges the gap by providing the expected interface.
    
    This adapter is crucial for maintaining backward compatibility while using the modern
    AudioService architecture. It translates control panel expectations into AudioService
    method calls and handles the asynchronous nature of the new service.
    
    Key Responsibilities:
    - Translating synchronous control panel calls to async AudioService methods
    - Converting AudioService state format to control panel expected format
    - Handling metadata caching and file information retrieval
    - Providing fallback values when AudioService is unavailable
    - Managing playback state updates for real-time control panel display
    """

    def __init__(self, audio_service: AudioService):
        self.audio_service = audio_service

    def get_playback_status(self) -> Dict[str, Any]:
        """Get playback status in the format expected by the control panel.
        
        This method performs complex state translation between the modern AudioService
        and the legacy control panel interface. It handles:
        
        - Real-time playback position calculation
        - Metadata retrieval with caching fallbacks
        - Audio file duration extraction from multiple sources
        - State format conversion for UI compatibility
        
        The method tries multiple approaches to get accurate timing information:
        1. From AudioService current state
        2. From cache service if available
        3. Direct MP3 metadata reading as fallback
        4. Known duration constants for common surahs
        
        Returns:
            dict: Complete playback status containing playback state, position,
                 reciter info, available options, and timing data in control panel format
        """
        try:
            # Can't use asyncio.run() within Discord's event loop, so access internal state directly
            # but make sure we get the most recent state
            state = self.audio_service._current_state

            # Force refresh the state by calling the internal update method if available
            try:
                if hasattr(self.audio_service, "_update_playback_state"):
                    self.audio_service._update_playback_state()
                elif hasattr(self.audio_service, "update_position"):
                    self.audio_service.update_position()
            except:
                pass  # Continue with existing state if update fails

            if not state:
                return self._get_default_status()

            # Get available reciters from the audio service
            available_reciters = []
            try:
                reciters_info = self.audio_service._available_reciters
                available_reciters = (
                    [r.name for r in reciters_info]
                    if reciters_info
                    else ["Saad Al Ghamdi"]
                )
            except:
                available_reciters = ["Saad Al Ghamdi"]

            # Get current time and total time
            current_time = (
                getattr(getattr(state, "current_position", None), "position_seconds", 0)
                if hasattr(state, "current_position")
                else 0
            )
            total_time = (
                getattr(
                    getattr(state, "current_position", None), "total_duration", None
                )
                or 0
                if hasattr(state, "current_position")
                else 0
            )

            # If total_time is 0, try to get from cache
            if total_time == 0:
                total_time = self._get_duration_from_cache(state)

            # Convert AudioService state to control panel format
            result = {
                "is_playing": getattr(state, "is_playing", False),
                "is_paused": getattr(state, "is_paused", False),
                "current_surah": getattr(
                    getattr(state, "current_position", None), "surah_number", 1
                ),
                "current_reciter": getattr(state, "current_reciter", "Saad Al Ghamdi"),
                "is_loop_enabled": getattr(state, "mode", None) == "loop",
                "is_shuffle_enabled": getattr(state, "mode", None) == "shuffle",
                "current_track": getattr(
                    getattr(state, "current_position", None), "surah_number", 1
                ),
                "total_tracks": 114,
                "available_reciters": available_reciters,
                "current_time": current_time,
                "total_time": total_time,
            }

            return result

        except Exception as e:
            traceback.print_exc()
            return self._get_default_status()

    def _get_duration_from_cache(self, state) -> float:
        """Get audio duration from cache or metadata."""
        try:
            current_surah = getattr(
                getattr(state, "current_position", None), "surah_number", 1
            )
            current_reciter = getattr(state, "current_reciter", "Saad Al Ghamdi")

            # Build file path
            file_path = f"audio/{current_reciter}/{current_surah:03d}.mp3"

            # Try to access cache directly from the audio service
            cache_service = getattr(self.audio_service, "_cache", None)

            if cache_service and hasattr(cache_service, "get"):
                cache_key = f"duration_{file_path}"
                try:
                    cached_duration = cache_service.get(cache_key)
                    if cached_duration:
                        return cached_duration
                except:
                    pass

            # If no cache hit, try to read MP3 metadata directly
            full_path = Path(file_path)
            if full_path.exists():
                try:
                    from mutagen.mp3 import MP3
                    audio_file = MP3(str(full_path))
                    return audio_file.info.length
                except Exception:
                    # Fallback: use some known durations for testing
                    if current_surah == 1:
                        return 47.0625  # Al-Fatiha
                    elif current_surah == 2:
                        return 7054.331125  # Al-Baqarah
                    else:
                        return 300  # Default 5 minutes

            return 0

        except Exception:
            return 0

    def _get_default_status(self) -> Dict[str, Any]:
        """Return safe default status when AudioService is unavailable.
        
        Provides a complete fallback status structure that prevents control panel
        errors when the AudioService is not accessible. This ensures the UI remains
        functional even during service initialization or failure states.
        
        Returns:
            dict: Safe default status with all required fields and sensible defaults
        """
        return {
            "is_playing": False,
            "is_paused": False,
            "current_surah": 1,
            "current_reciter": "Saad Al Ghamdi",
            "is_loop_enabled": False,
            "is_shuffle_enabled": False,
            "current_track": 1,
            "total_tracks": 114,
            "available_reciters": ["Saad Al Ghamdi"],
            "current_time": 0,
            "total_time": 0,
        }

    # Control methods expected by the control panel
    async def jump_to_surah(self, surah_number: int):
        """Jump to a specific surah."""
        try:
            await self.audio_service.set_surah(surah_number)
        except Exception as e:
            traceback.print_exc()

    async def switch_reciter(self, reciter_name: str):
        """Switch to a different reciter."""
        try:
            await self.audio_service.set_reciter(reciter_name)
        except Exception as e:
            traceback.print_exc()

    async def skip_to_next(self):
        """Skip to the next surah."""
        try:
            current_state = self.audio_service._current_state
            current_surah = getattr(
                getattr(current_state, "current_position", None), "surah_number", 1
            )
            next_surah = current_surah + 1 if current_surah < 114 else 1
            await self.audio_service.set_surah(next_surah)
        except Exception as e:
            traceback.print_exc()

    async def skip_to_previous(self):
        """Skip to the previous surah."""
        try:
            current_state = self.audio_service._current_state
            current_surah = getattr(
                getattr(current_state, "current_position", None), "surah_number", 1
            )
            previous_surah = current_surah - 1 if current_surah > 1 else 114
            await self.audio_service.set_surah(previous_surah)
        except Exception as e:
            traceback.print_exc()

    async def toggle_loop(self):
        """Toggle loop mode."""
        try:
            current_state = self.audio_service._current_state
            if current_state and hasattr(current_state, "mode"):
                current_mode = getattr(current_state, "mode", "normal")
                if current_mode == PlaybackMode.LOOP_TRACK:
                    await self.audio_service.set_playback_mode(PlaybackMode.NORMAL)
                else:
                    await self.audio_service.set_playback_mode(PlaybackMode.LOOP_TRACK)
        except Exception as e:
            traceback.print_exc()

    async def toggle_shuffle(self):
        """Toggle shuffle mode."""
        try:
            current_state = self.audio_service._current_state
            if current_state and hasattr(current_state, "mode"):
                current_mode = getattr(current_state, "mode", "normal")
                if current_mode == PlaybackMode.SHUFFLE:
                    await self.audio_service.set_playback_mode(PlaybackMode.NORMAL)
                else:
                    await self.audio_service.set_playback_mode(PlaybackMode.SHUFFLE)
        except Exception as e:
            traceback.print_exc()

    @property
    def is_loop_enabled(self) -> bool:
        """Check if loop mode is enabled."""
        try:
            current_state = self.audio_service._current_state
            if current_state and hasattr(current_state, "mode"):
                current_mode = getattr(current_state, "mode", "normal")
                return current_mode == PlaybackMode.LOOP_TRACK
            return False
        except Exception:
            return False

    @property
    def is_shuffle_enabled(self) -> bool:
        """Check if shuffle mode is enabled."""
        try:
            current_state = self.audio_service._current_state
            if current_state and hasattr(current_state, "mode"):
                current_mode = getattr(current_state, "mode", "normal")
                return current_mode == PlaybackMode.SHUFFLE
            return False
        except Exception:
            return False

    async def pause_playback(self):
        """Disabled - 24/7 Quran bot should never be paused."""
        try:
            # 24/7 bot never pauses - this is a no-op for control panel compatibility
            pass
        except Exception as e:
            traceback.print_exc()

    async def resume_playback(self):
        """Disabled - 24/7 Quran bot should never need resuming as it never pauses."""
        try:
            # 24/7 bot never needs resuming - this is a no-op for control panel compatibility
            pass
        except Exception as e:
            traceback.print_exc()

    async def toggle_playback(self):
        """Start playback if stopped - pause/resume disabled for 24/7 operation."""
        try:
            state = self.audio_service._current_state
            if not state.is_playing:
                await self.audio_service.start_playback(resume_position=True)
            else:
                # Already playing - no action needed
                pass
        except Exception as e:
            traceback.print_exc()