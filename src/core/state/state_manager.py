"""
State manager for the Discord Quran Bot.
Persists bot state across restarts including current song position.

This module provides comprehensive state management including:
- Persistent state storage and retrieval
- Event-driven state change notifications
- Playback position tracking
- User action tracking
- State validation and recovery
- Comprehensive error handling and logging

Features:
    - JSON-based persistent state storage
    - Event listener system for state changes
    - Playback position tracking and recovery
    - User action history tracking
    - State validation and error recovery
    - Comprehensive logging and monitoring
    - Cross-platform file handling

Author: John (Discord: Trippxin)
Version: 2.0.0
"""

import json
import os
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable, Tuple
from src.monitoring.logging.tree_log import tree_log


class StateManager:
    """
    Manages persistent state for the Quran Bot with event notifications.

    This class provides comprehensive state management for the bot including
    persistent storage, event notifications, and state validation.

    Features:
        - JSON-based persistent state storage
        - Event listener system for state changes
        - Playback position tracking and recovery
        - User action history tracking
        - State validation and error recovery
        - Comprehensive logging and monitoring
    """

    def __init__(self, state_file: str = "bot_state.json"):
        """
        Initialize the state manager.

        Args:
            state_file (str): Path to the state file for persistence
        """
        try:
            self.state_file = state_file
            self.state = self._load_state()
            self._event_listeners: Dict[str, List[Callable]] = {
                "song_changed": [],
                "index_changed": [],
                "state_updated": [],
            }

            tree_log('info', 'State manager initialized', {'event': 'STATE_MANAGER_INIT', 'state_file': state_file})

        except Exception as e:
            tree_log('error', 'Failed to initialize state manager', {'event': 'STATE_MANAGER_INIT_ERROR', 'error': str(e), 'traceback': traceback.format_exc()})
            raise

    def add_event_listener(self, event: str, callback: Callable) -> None:
        """
        Add an event listener for state changes.

        Args:
            event (str): Event type to listen for
            callback (Callable): Function to call when event occurs
        """
        try:
            if event not in self._event_listeners:
                self._event_listeners[event] = []
            self._event_listeners[event].append(callback)

            tree_log('info', 'Event listener added', {'event': 'EVENT_LISTENER_ADDED', 'event_type': event, 'listener_count': len(self._event_listeners[event])})

        except Exception as e:
            tree_log('error', 'Error adding event listener', {'event': 'EVENT_LISTENER_ADD_ERROR', 'error': str(e), 'traceback': traceback.format_exc()})

    def remove_event_listener(self, event: str, callback: Callable) -> None:
        """
        Remove an event listener with proper error handling.

        Args:
            event (str): Event type to remove listener from
            callback (Callable): Function to remove
        """
        try:
            if event not in self._event_listeners:
                tree_log('warning', 'Remove listener: unknown event', {'event': 'REMOVE_LISTENER_UNKNOWN_EVENT', 'event_type': event, 'available_events': list(self._event_listeners.keys())})
                return

            self._event_listeners[event].remove(callback)
            tree_log('info', 'Event listener removed', {'event': 'EVENT_LISTENER_REMOVED', 'event_type': event, 'listener_count': len(self._event_listeners[event])})

        except ValueError as e:
            tree_log('warning', 'Remove listener: not found', {'event': 'REMOVE_LISTENER_NOT_FOUND', 'event_type': event, 'error': str(e), 'current_listener_count': len(self._event_listeners[event])})
        except Exception as e:
            tree_log('error', 'Error removing event listener', {'event': 'EVENT_LISTENER_REMOVE_ERROR', 'error': str(e), 'traceback': traceback.format_exc()})

    async def _emit_event(
        self, event: str, data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Emit an event to all registered listeners with comprehensive error handling.

        Args:
            event (str): Event type to emit
            data (Optional[Dict[str, Any]]): Data to pass to event listeners
        """
        try:
            if event not in self._event_listeners:
                tree_log('warning', 'Emit unknown event', {'event': 'EMIT_UNKNOWN_EVENT', 'event_type': event, 'available_events': list(self._event_listeners.keys())})
                return

            listener_count = len(self._event_listeners[event])
            if listener_count == 0:
                tree_log('debug', 'Emit: no listeners', {'event': 'EMIT_NO_LISTENERS', 'event_type': event})
                return

            tree_log('debug', 'Emitting event', {'event': 'EMITTING_EVENT', 'event_type': event, 'listener_count': listener_count, 'has_data': data is not None})

            successful_callbacks = 0
            failed_callbacks = 0

            for i, callback in enumerate(self._event_listeners[event]):
                try:
                    if data is not None:
                        await callback(data)
                    else:
                        await callback()
                    successful_callbacks += 1
                    tree_log('debug', 'Event callback success', {'event': 'EVENT_CALLBACK_SUCCESS', 'event_type': event, 'callback_index': i, 'callback_name': getattr(callback, '__name__', 'unknown')})
                except Exception as e:
                    failed_callbacks += 1
                    tree_log('error', 'Event callback failed', {'event': 'EVENT_CALLBACK_FAILED', 'event_type': event, 'callback_index': i, 'callback_name': getattr(callback, '__name__', 'unknown'), 'error': str(e), 'error_type': type(e).__name__, 'traceback': traceback.format_exc()})

            tree_log('info', 'Event emission complete', {'event': 'EVENT_EMISSION_COMPLETE', 'event_type': event, 'total_listeners': listener_count, 'successful_callbacks': successful_callbacks, 'failed_callbacks': failed_callbacks})

        except Exception as e:
            tree_log('error', 'Error emitting event', {'event': 'EMIT_EVENT_ERROR', 'event_type': event, 'error': str(e), 'traceback': traceback.format_exc()})

    def _load_state(self) -> Dict[str, Any]:
        """
        Load state from file with comprehensive logging.

        Returns:
            Dict[str, Any]: Loaded state dictionary
        """
        default_state = {
            "current_song_index": 0,
            "current_song_name": None,
            "total_songs_played": 0,
            "last_played_time": None,
            "bot_start_count": 0,
            "last_state_save": None,
            "loop_enabled_by": None,  # Stores user ID who enabled loop
            "loop_enabled_by_name": None,  # Stores username who enabled loop
            "shuffle_enabled_by": None,  # Stores user ID who enabled shuffle
            "shuffle_enabled_by_name": None,  # Stores username who enabled shuffle
            "last_change": None,  # Stores the last user action
            "last_change_time": None,  # Stores when the last change happened
            "playback_position": 0,  # Current playback position in seconds
            "playback_start_time": None,  # When playback started (for calculating position)
            "last_position_save": None,  # When position was last saved
        }

        try:
            if os.path.exists(self.state_file):
                try:
                    with open(self.state_file, "r", encoding="utf-8") as f:
                        loaded_state = json.load(f)
                        # Merge with default state to handle missing fields
                        default_state.update(loaded_state)
                        tree_log('info', 'State loaded successfully', {'event': 'STATE_LOADED', 'state_file': self.state_file, 'loaded_fields': list(loaded_state.keys()), 'current_song_index': default_state.get('current_song_index'), 'current_song_name': default_state.get('current_song_name'), 'total_songs_played': default_state.get('total_songs_played')})
                        return default_state
                except json.JSONDecodeError as e:
                    tree_log('error', 'State load JSON error', {'event': 'STATE_LOAD_JSON_ERROR', 'state_file': self.state_file, 'error': str(e), 'line': getattr(e, 'lineno', 'unknown'), 'column': getattr(e, 'colno', 'unknown'), 'traceback': traceback.format_exc()})
                    return default_state
                except PermissionError as e:
                    tree_log('error', 'State load permission error', {'event': 'STATE_LOAD_PERMISSION_ERROR', 'state_file': self.state_file, 'error': str(e), 'traceback': traceback.format_exc()})
                    return default_state
                except Exception as e:
                    tree_log('error', 'State load unexpected error', {'event': 'STATE_LOAD_UNEXPECTED_ERROR', 'state_file': self.state_file, 'error': str(e), 'error_type': type(e).__name__, 'traceback': traceback.format_exc()})
                    return default_state
            else:
                tree_log('info', 'State file not found, using defaults', {'event': 'STATE_FILE_NOT_FOUND_DEFAULTS', 'state_file': self.state_file, 'default_state': default_state})
                return default_state

        except Exception as e:
            tree_log('error', 'Error loading state', {'event': 'STATE_LOAD_ERROR', 'error': str(e), 'traceback': traceback.format_exc()})
            return default_state

    def _save_state(self) -> None:
        """
        Save current state to file with comprehensive logging.

        This method handles all error cases and provides detailed logging
        for debugging state persistence issues.
        """
        try:
            self.state["last_state_save"] = datetime.now().isoformat()

            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)

            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)

            tree_log('debug', 'State saved successfully', {'event': 'STATE_SAVED', 'state_file': self.state_file, 'current_song_index': self.state.get('current_song_index'), 'current_song_name': self.state.get('current_song_name'), 'total_songs_played': self.state.get('total_songs_played')})

        except PermissionError as e:
            tree_log('error', 'State save permission error', {'event': 'STATE_SAVE_PERMISSION_ERROR', 'state_file': self.state_file, 'error': str(e), 'traceback': traceback.format_exc()})
        except Exception as e:
            tree_log('error', 'State save unexpected error', {'event': 'STATE_SAVE_UNEXPECTED_ERROR', 'state_file': self.state_file, 'error': str(e), 'error_type': type(e).__name__, 'traceback': traceback.format_exc()})

    def get_current_song_index(self) -> int:
        """Get the current song index."""
        return self.state.get("current_song_index", 0)

    def set_current_song_index(self, index: int):
        """Set the current song index with logging and event emission."""
        if not isinstance(index, int):
            tree_log('error', 'Set song index: invalid type', {'action': 'set_song_index_invalid_type', 'provided_index': index, 'provided_type': type(index).__name__})
            return

        if index < 0:
            tree_log('warning', 'Set song index: negative', {'action': 'set_song_index_negative', 'provided_index': index})
            index = 0

        old_index = self.state.get("current_song_index", 0)
        self.state["current_song_index"] = index
        self._save_state()

        tree_log('info', 'Song index changed', {'action': 'song_index_changed', 'old_index': old_index, 'new_index': index, 'index_change': index - old_index})

        # Emit index changed event
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    self._emit_event(
                        "index_changed", {"old_index": old_index, "new_index": index}
                    )
                )
                asyncio.create_task(self._emit_event("state_updated"))
                tree_log('debug', 'Index change events scheduled', {'action': 'index_change_events_scheduled', 'old_index': old_index, 'new_index': index})
            else:
                tree_log('warning', 'Event loop not running, skipping events', {'action': 'event_loop_not_running_skipping_events', 'operation': 'set_current_song_index'})
        except RuntimeError as e:
            tree_log('warning', 'No event loop, skipping events', {'action': 'no_event_loop_skipping_events', 'operation': 'set_current_song_index', 'error': str(e)})

    def get_current_song_name(self) -> Optional[str]:
        """Get the current song name."""
        return self.state.get("current_song_name")

    def set_current_song_name(self, song_name: str):
        """Set the current song name with logging and event emission."""
        if not isinstance(song_name, str):
            tree_log('error', 'Set song name: invalid type', {'action': 'set_song_name_invalid_type', 'provided_name': song_name, 'provided_type': type(song_name).__name__})
            return

        old_song = self.state.get("current_song_name")
        self.state["current_song_name"] = song_name
        self.state["last_played_time"] = datetime.now().isoformat()
        self._save_state()

        tree_log('info', 'Song name changed', {'action': 'song_name_changed', 'old_song': old_song, 'new_song': song_name, 'timestamp': self.state["last_played_time"]})

        # Emit song changed event
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    self._emit_event(
                        "song_changed", {"old_song": old_song, "new_song": song_name}
                    )
                )
                asyncio.create_task(self._emit_event("state_updated"))
                tree_log('debug', 'Song change events scheduled', {'action': 'song_change_events_scheduled', 'old_song': old_song, 'new_song': song_name})
            else:
                tree_log('warning', 'Event loop not running, skipping events', {'action': 'event_loop_not_running_skipping_events', 'operation': 'set_current_song_name'})
        except RuntimeError as e:
            tree_log('warning', 'No event loop, skipping events', {'action': 'no_event_loop_skipping_events', 'operation': 'set_current_song_name', 'error': str(e)})

    def set_current_song_index_by_surah(self, surah_num: str, audio_files: list):
        """Set the current song index by surah number with comprehensive logging."""
        if not isinstance(surah_num, str):
            tree_log('error', 'Set index by surah: invalid surah type', {'action': 'set_index_by_surah_invalid_surah_type', 'provided_surah': surah_num, 'provided_type': type(surah_num).__name__})
            return

        if not isinstance(audio_files, list):
            tree_log('error', 'Set index by surah: invalid files type', {'action': 'set_index_by_surah_invalid_files_type', 'provided_files_type': type(audio_files).__name__, 'surah_num': surah_num})
            return

        if not audio_files:
            tree_log('warning', 'Set index by surah: empty files list', {'action': 'set_index_by_surah_empty_files_list', 'surah_num': surah_num})
            self.set_current_song_index(0)
            return

        original_surah = surah_num
        surah_num = surah_num.zfill(3)  # Ensure 3-digit format

        tree_log('debug', 'Searching for surah', {'action': 'searching_for_surah', 'original_surah': original_surah, 'formatted_surah': surah_num, 'total_files': len(audio_files)})

        for i, file_path in enumerate(audio_files):
            if not file_path:
                tree_log('warning', 'Found empty file path', {'action': 'found_empty_file_path', 'file_index': i, 'surah_num': surah_num})
                continue

            try:
                file_name = os.path.basename(file_path)
                if file_name.startswith(surah_num):
                    tree_log('info', 'Surah found, setting index', {'action': 'surah_found_setting_index', 'surah_num': surah_num, 'found_file': file_name, 'file_index': i, 'file_path': file_path})
                    self.set_current_song_index(i)
                    return
            except Exception as e:
                tree_log('warning', 'Error processing file path', {'action': 'error_processing_file_path', 'file_path': file_path, 'file_index': i, 'surah_num': surah_num, 'error': str(e), 'error_type': type(e).__name__}, e)
                continue

        # If not found, set to 0
        tree_log('warning', 'Surah not found, using default', {'action': 'surah_not_found_using_default', 'surah_num': surah_num, 'original_surah': original_surah, 'total_files_searched': len(audio_files), 'default_index': 0})
        self.set_current_song_index(0)

    def increment_songs_played(self):
        """Increment the total songs played counter with logging."""
        old_count = self.state.get("total_songs_played", 0)
        self.state["total_songs_played"] = old_count + 1
        self._save_state()

        tree_log('debug', 'Songs played incremented', {'action': 'songs_played_incremented', 'old_count': old_count, 'new_count': self.state["total_songs_played"]})

    def get_total_songs_played(self) -> int:
        """Get total songs played."""
        return self.state.get("total_songs_played", 0)

    def increment_bot_start_count(self):
        """Increment bot start count with logging."""
        old_count = self.state.get("bot_start_count", 0)
        self.state["bot_start_count"] = old_count + 1
        self._save_state()

        tree_log('info', 'Bot start count incremented', {'action': 'bot_start_count_incremented', 'old_count': old_count, 'new_count': self.state["bot_start_count"]})

    def get_bot_start_count(self) -> int:
        """Get bot start count."""
        return self.state.get("bot_start_count", 0)

    def get_last_played_time(self) -> Optional[datetime]:
        """Get last played time."""
        last_time = self.state.get("last_played_time")
        if last_time:
            try:
                return datetime.fromisoformat(last_time)
            except:
                return None
        return None

    def get_state_summary(self) -> Dict[str, Any]:
        """Get a summary of the current state."""
        last_played = self.get_last_played_time()
        return {
            "current_song_index": self.get_current_song_index(),
            "current_song_name": self.get_current_song_name(),
            "total_songs_played": self.get_total_songs_played(),
            "bot_start_count": self.get_bot_start_count(),
            "last_played_time": last_played.isoformat() if last_played else None,
            "last_state_save": self.state.get("last_state_save"),
        }

    def set_loop_enabled_by(self, user_id: int, username: str):
        """Set who enabled the loop mode with comprehensive logging."""
        try:
            tree_log('info', 'Set loop enabled by', {'action': 'set_loop_enabled_by', 'user_id': user_id, 'username': username, 'previous_user_id': self.state.get("loop_enabled_by"), 'previous_username': self.state.get("loop_enabled_by_name")})

            self.state["loop_enabled_by"] = user_id
            self.state["loop_enabled_by_name"] = username
            self._save_state()

            # Emit state update event
            import asyncio

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(
                        self._emit_event(
                            "state_updated",
                            {
                                "type": "loop_user_changed",
                                "user_id": user_id,
                                "username": username,
                            },
                        )
                    )
            except RuntimeError:
                tree_log('debug', 'No event loop for loop user event')

        except Exception as e:
            tree_log('error', 'Set loop enabled by failed', {'action': 'set_loop_enabled_by_failed', 'user_id': user_id, 'username': username, 'error': str(e), 'error_type': type(e).__name__}, e)

    def clear_loop_enabled_by(self):
        """Clear who enabled loop mode (when loop is disabled) with comprehensive logging."""
        try:
            old_user_id = self.state.get("loop_enabled_by")
            old_username = self.state.get("loop_enabled_by_name")

            tree_log('info', 'Clear loop enabled by', {'action': 'clear_loop_enabled_by', 'previous_user_id': old_user_id, 'previous_username': old_username})

            self.state["loop_enabled_by"] = None
            self.state["loop_enabled_by_name"] = None
            self._save_state()

            # Emit state update event
            import asyncio

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(
                        self._emit_event("state_updated", {"type": "loop_user_cleared"})
                    )
            except RuntimeError:
                tree_log('debug', 'No event loop for loop clear event')

        except Exception as e:
            tree_log('error', 'Clear loop enabled by failed', {'action': 'clear_loop_enabled_by_failed', 'error': str(e), 'error_type': type(e).__name__}, e)

    def get_loop_enabled_by(self) -> tuple:
        """Get who enabled loop mode as (user_id, username)."""
        return (
            self.state.get("loop_enabled_by"),
            self.state.get("loop_enabled_by_name"),
        )

    def set_shuffle_enabled_by(self, user_id: int, username: str):
        """Set who enabled the shuffle mode with comprehensive logging."""
        try:
            tree_log('info', 'Set shuffle enabled by', {'action': 'set_shuffle_enabled_by', 'user_id': user_id, 'username': username, 'previous_user_id': self.state.get("shuffle_enabled_by"), 'previous_username': self.state.get("shuffle_enabled_by_name")})

            self.state["shuffle_enabled_by"] = user_id
            self.state["shuffle_enabled_by_name"] = username
            self._save_state()

            # Emit state update event
            import asyncio

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(
                        self._emit_event(
                            "state_updated",
                            {
                                "type": "shuffle_user_changed",
                                "user_id": user_id,
                                "username": username,
                            },
                        )
                    )
            except RuntimeError:
                tree_log('debug', 'No event loop for shuffle user event')

        except Exception as e:
            tree_log('error', 'Set shuffle enabled by failed', {'action': 'set_shuffle_enabled_by_failed', 'user_id': user_id, 'username': username, 'error': str(e), 'error_type': type(e).__name__}, e)

    def clear_shuffle_enabled_by(self):
        """Clear who enabled shuffle mode (when shuffle is disabled) with comprehensive logging."""
        try:
            old_user_id = self.state.get("shuffle_enabled_by")
            old_username = self.state.get("shuffle_enabled_by_name")

            tree_log('info', 'Clear shuffle enabled by', {'action': 'clear_shuffle_enabled_by', 'previous_user_id': old_user_id, 'previous_username': old_username})

            self.state["shuffle_enabled_by"] = None
            self.state["shuffle_enabled_by_name"] = None
            self._save_state()

            # Emit state update event
            import asyncio

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(
                        self._emit_event(
                            "state_updated", {"type": "shuffle_user_cleared"}
                        )
                    )
            except RuntimeError:
                tree_log('debug', 'No event loop for shuffle clear event')

        except Exception as e:
            tree_log('error', 'Clear shuffle enabled by failed', {'action': 'clear_shuffle_enabled_by_failed', 'error': str(e), 'error_type': type(e).__name__}, e)

    def get_shuffle_enabled_by(self) -> tuple:
        """Get who enabled shuffle mode as (user_id, username)."""
        return (
            self.state.get("shuffle_enabled_by"),
            self.state.get("shuffle_enabled_by_name"),
        )

    def set_last_change(
        self, action: str, user_id: int, username: str, details: Optional[str] = None
    ):
        """Set the last change made by a user with comprehensive logging."""
        try:
            import time

            change_time = int(time.time())  # Unix timestamp for Discord formatting
            change_description = f"{action} by <@{user_id}>"
            if details:
                change_description += f" to {details}"

            tree_log('info', 'Set last change', {'action': 'set_last_change', 'user_id': user_id, 'username': username, 'change_action': action, 'details': details, 'change_time': change_time, 'previous_change': self.state.get("last_change")})

            self.state["last_change"] = change_description
            self.state["last_change_time"] = change_time
            self._save_state()

            # Emit state update event
            import asyncio

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(
                        self._emit_event(
                            "state_updated",
                            {
                                "type": "last_change_updated",
                                "change": change_description,
                                "user_id": user_id,
                                "username": username,
                                "action": action,
                                "details": details,
                            },
                        )
                    )
            except RuntimeError:
                tree_log('debug', 'No event loop for change event')

        except Exception as e:
            tree_log('error', 'Set last change failed', {'action': 'set_last_change_failed', 'user_id': user_id, 'username': username, 'change_action': action, 'error': str(e), 'error_type': type(e).__name__, 'traceback': traceback.format_exc()}, e)

    def get_last_change(self) -> tuple:
        """Get the last change as (description, timestamp)."""
        return (self.state.get("last_change"), self.state.get("last_change_time"))

    def clear_last_change(self):
        """Clear the last change info (on bot restart)."""
        try:
            tree_log('info', 'Clear last change', {'action': 'clear_last_change', 'previous_change': self.state.get("last_change"), 'previous_time': self.state.get("last_change_time")})

            self.state["last_change"] = None
            self.state["last_change_time"] = None
            self._save_state()

        except Exception as e:
            tree_log('error', 'Clear last change failed', {'action': 'clear_last_change_failed', 'error': str(e), 'error_type': type(e).__name__, 'traceback': traceback.format_exc()}, e)

    def reset_state(self):
        """Reset state to default values."""
        self.state = {
            "current_song_index": 0,
            "current_song_name": None,
            "total_songs_played": 0,
            "last_played_time": None,
            "bot_start_count": self.state.get("bot_start_count", 0),
            "last_state_save": None,
            "loop_enabled_by": None,
            "loop_enabled_by_name": None,
            "shuffle_enabled_by": None,
            "shuffle_enabled_by_name": None,
            "last_change": None,
            "last_change_time": None,
            "playback_position": 0,
            "playback_start_time": None,
            "last_position_save": None,
        }
        self._save_state()

    def get_playback_position(self) -> float:
        """Get the current playback position in seconds."""
        return self.state.get("playback_position", 0)

    def set_playback_position(self, position: float):
        """Set the current playback position in seconds."""
        try:
            tree_log('debug', 'Set playback position', {'action': 'set_playback_position', 'position': position, 'previous_position': self.state.get("playback_position", 0)})

            self.state["playback_position"] = max(0, position)  # Ensure non-negative
            self.state["last_position_save"] = datetime.now().isoformat()
            self._save_state()

        except Exception as e:
            tree_log('error', 'Set playback position failed', {'action': 'set_playback_position_failed', 'position': position, 'error': str(e), 'error_type': type(e).__name__, 'traceback': traceback.format_exc()}, e)

    def set_playback_start_time(self, start_time: float):
        """Set when playback started (Unix timestamp)."""
        try:
            tree_log('info', 'Set playback start time', {'action': 'set_playback_start_time', 'start_time': start_time, 'previous_start_time': self.state.get("playback_start_time")})

            self.state["playback_start_time"] = start_time
            self._save_state()

        except Exception as e:
            tree_log('error', 'Set playback start time failed', {'action': 'set_playback_start_time_failed', 'start_time': start_time, 'error': str(e), 'error_type': type(e).__name__, 'traceback': traceback.format_exc()}, e)

    def get_playback_start_time(self) -> Optional[float]:
        """Get when playback started (Unix timestamp)."""
        return self.state.get("playback_start_time")

    def save_playback_position(self, current_time: float):
        """Save the current playback position based on elapsed time."""
        try:
            start_time = self.get_playback_start_time()
            if start_time:
                position = current_time - start_time
                self.set_playback_position(position)

                tree_log('debug', 'Save playback position', {'action': 'save_playback_position', 'current_time': current_time, 'start_time': start_time, 'calculated_position': position})

        except Exception as e:
            tree_log('error', 'Save playback position failed', {'action': 'save_playback_position_failed', 'current_time': current_time, 'error': str(e), 'error_type': type(e).__name__, 'traceback': traceback.format_exc()}, e)

    def clear_playback_position(self):
        """Clear playback position (when stopping or changing tracks)."""
        try:
            tree_log('info', 'Clear playback position', {'action': 'clear_playback_position', 'previous_position': self.state.get("playback_position", 0), 'previous_start_time': self.state.get("playback_start_time")})

            self.state["playback_position"] = 0
            self.state["playback_start_time"] = None
            self.state["last_position_save"] = None
            self._save_state()

        except Exception as e:
            tree_log('error', 'Clear playback position failed', {'action': 'clear_playback_position_failed', 'error': str(e), 'error_type': type(e).__name__, 'traceback': traceback.format_exc()}, e)
