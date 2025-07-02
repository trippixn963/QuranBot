"""
State manager for the Discord Quran Bot.
Persists bot state across restarts including current song position.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from .log_helpers import log_function_call, log_operation

class StateManager:
    """Manages persistent state for the Quran Bot with event notifications."""
    
    def __init__(self, state_file: str = "bot_state.json"):
        """Initialize the state manager."""
        self.state_file = state_file
        self.state = self._load_state()
        self._event_listeners: Dict[str, List[Callable]] = {
            'song_changed': [],
            'index_changed': [],
            'state_updated': []
        }
        
    def add_event_listener(self, event: str, callback: Callable):
        """Add an event listener for state changes."""
        if event not in self._event_listeners:
            self._event_listeners[event] = []
        self._event_listeners[event].append(callback)
        log_operation("events", "INFO", {
            "action": "event_listener_added",
            "event": event,
            "listener_count": len(self._event_listeners[event])
        })
    
    def remove_event_listener(self, event: str, callback: Callable):
        """Remove an event listener with proper error handling."""
        if event not in self._event_listeners:
            log_operation("events", "WARNING", {
                "action": "remove_listener_unknown_event",
                "event": event,
                "available_events": list(self._event_listeners.keys())
            })
            return
            
        try:
            self._event_listeners[event].remove(callback)
            log_operation("events", "INFO", {
                "action": "event_listener_removed",
                "event": event,
                "listener_count": len(self._event_listeners[event])
            })
        except ValueError as e:
            log_operation("events", "WARNING", {
                "action": "remove_listener_not_found",
                "event": event,
                "error": str(e),
                "current_listener_count": len(self._event_listeners[event])
            })
    
    async def _emit_event(self, event: str, data: Optional[Dict[str, Any]] = None):
        """Emit an event to all registered listeners with comprehensive error handling."""
        if event not in self._event_listeners:
            log_operation("events", "WARNING", {
                "action": "emit_unknown_event",
                "event": event,
                "available_events": list(self._event_listeners.keys())
            })
            return
            
        listener_count = len(self._event_listeners[event])
        if listener_count == 0:
            log_operation("events", "DEBUG", {
                "action": "emit_no_listeners",
                "event": event
            })
            return
            
        log_operation("events", "DEBUG", {
            "action": "emitting_event",
            "event": event,
            "listener_count": listener_count,
            "has_data": data is not None
        })
        
        successful_callbacks = 0
        failed_callbacks = 0
        
        for i, callback in enumerate(self._event_listeners[event]):
            try:
                if data is not None:
                    await callback(data)
                else:
                    await callback()
                successful_callbacks += 1
                log_operation("events", "DEBUG", {
                    "action": "event_callback_success",
                    "event": event,
                    "callback_index": i,
                    "callback_name": getattr(callback, '__name__', 'unknown')
                })
            except Exception as e:
                failed_callbacks += 1
                log_operation("events", "ERROR", {
                    "action": "event_callback_failed",
                    "event": event,
                    "callback_index": i,
                    "callback_name": getattr(callback, '__name__', 'unknown'),
                    "error": str(e),
                    "error_type": type(e).__name__
                }, e)
        
        log_operation("events", "INFO", {
            "action": "event_emission_complete",
            "event": event,
            "total_listeners": listener_count,
            "successful_callbacks": successful_callbacks,
            "failed_callbacks": failed_callbacks
        })
    
    def _load_state(self) -> Dict[str, Any]:
        """Load state from file with comprehensive logging."""
        default_state = {
            'current_song_index': 0,
            'current_song_name': None,
            'total_songs_played': 0,
            'last_played_time': None,
            'bot_start_count': 0,
            'last_state_save': None
        }
        
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    loaded_state = json.load(f)
                    # Merge with default state to handle missing fields
                    default_state.update(loaded_state)
                    log_operation("state_load", "INFO", {
                        "action": "state_loaded_successfully",
                        "state_file": self.state_file,
                        "loaded_fields": list(loaded_state.keys()),
                        "current_song_index": default_state.get('current_song_index'),
                        "current_song_name": default_state.get('current_song_name'),
                        "total_songs_played": default_state.get('total_songs_played')
                    })
                    return default_state
            except json.JSONDecodeError as e:
                log_operation("state_load", "ERROR", {
                    "action": "state_load_json_error",
                    "state_file": self.state_file,
                    "error": str(e),
                    "line": getattr(e, 'lineno', 'unknown'),
                    "column": getattr(e, 'colno', 'unknown')
                }, e)
                return default_state
            except PermissionError as e:
                log_operation("state_load", "ERROR", {
                    "action": "state_load_permission_error",
                    "state_file": self.state_file,
                    "error": str(e)
                }, e)
                return default_state
            except Exception as e:
                log_operation("state_load", "ERROR", {
                    "action": "state_load_unexpected_error",
                    "state_file": self.state_file,
                    "error": str(e),
                    "error_type": type(e).__name__
                }, e)
                return default_state
        else:
            log_operation("state_load", "INFO", {
                "action": "state_file_not_found_using_defaults",
                "state_file": self.state_file,
                "default_state": default_state
            })
            return default_state
            
    def _save_state(self):
        """Save current state to file with comprehensive logging."""
        try:
            self.state['last_state_save'] = datetime.now().isoformat()
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
            log_operation("state_save", "DEBUG", {
                "action": "state_saved_successfully",
                "state_file": self.state_file,
                "current_song_index": self.state.get('current_song_index'),
                "current_song_name": self.state.get('current_song_name'),
                "total_songs_played": self.state.get('total_songs_played')
            })
        except PermissionError as e:
            log_operation("state_save", "ERROR", {
                "action": "state_save_permission_error",
                "state_file": self.state_file,
                "error": str(e)
            }, e)
        except OSError as e:
            log_operation("state_save", "ERROR", {
                "action": "state_save_os_error",
                "state_file": self.state_file,
                "error": str(e),
                "errno": getattr(e, 'errno', 'unknown')
            }, e)
        except Exception as e:
            log_operation("state_save", "ERROR", {
                "action": "state_save_unexpected_error",
                "state_file": self.state_file,
                "error": str(e),
                "error_type": type(e).__name__
            }, e)
            
    def get_current_song_index(self) -> int:
        """Get the current song index."""
        return self.state.get('current_song_index', 0)
        
    def set_current_song_index(self, index: int):
        """Set the current song index with logging and event emission."""
        if not isinstance(index, int):
            log_operation("state", "ERROR", {
                "action": "set_song_index_invalid_type",
                "provided_index": index,
                "provided_type": type(index).__name__
            })
            return
            
        if index < 0:
            log_operation("state", "WARNING", {
                "action": "set_song_index_negative",
                "provided_index": index
            })
            index = 0
            
        old_index = self.state.get('current_song_index', 0)
        self.state['current_song_index'] = index
        self._save_state()
        
        log_operation("state", "INFO", {
            "action": "song_index_changed",
            "old_index": old_index,
            "new_index": index,
            "index_change": index - old_index
        })
        
        # Emit index changed event
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._emit_event('index_changed', {
                    'old_index': old_index,
                    'new_index': index
                }))
                asyncio.create_task(self._emit_event('state_updated'))
                log_operation("events", "DEBUG", {
                    "action": "index_change_events_scheduled",
                    "old_index": old_index,
                    "new_index": index
                })
            else:
                log_operation("events", "WARNING", {
                    "action": "event_loop_not_running_skipping_events",
                    "operation": "set_current_song_index"
                })
        except RuntimeError as e:
            log_operation("events", "WARNING", {
                "action": "no_event_loop_skipping_events",
                "operation": "set_current_song_index",
                "error": str(e)
            })
        
    def get_current_song_name(self) -> Optional[str]:
        """Get the current song name."""
        return self.state.get('current_song_name')
        
    def set_current_song_name(self, song_name: str):
        """Set the current song name with logging and event emission."""
        if not isinstance(song_name, str):
            log_operation("state", "ERROR", {
                "action": "set_song_name_invalid_type",
                "provided_name": song_name,
                "provided_type": type(song_name).__name__
            })
            return
            
        old_song = self.state.get('current_song_name')
        self.state['current_song_name'] = song_name
        self.state['last_played_time'] = datetime.now().isoformat()
        self._save_state()
        
        log_operation("state", "INFO", {
            "action": "song_name_changed",
            "old_song": old_song,
            "new_song": song_name,
            "timestamp": self.state['last_played_time']
        })
        
        # Emit song changed event
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._emit_event('song_changed', {
                    'old_song': old_song,
                    'new_song': song_name
                }))
                asyncio.create_task(self._emit_event('state_updated'))
                log_operation("events", "DEBUG", {
                    "action": "song_change_events_scheduled",
                    "old_song": old_song,
                    "new_song": song_name
                })
            else:
                log_operation("events", "WARNING", {
                    "action": "event_loop_not_running_skipping_events",
                    "operation": "set_current_song_name"
                })
        except RuntimeError as e:
            log_operation("events", "WARNING", {
                "action": "no_event_loop_skipping_events",
                "operation": "set_current_song_name",
                "error": str(e)
            })
        
    def set_current_song_index_by_surah(self, surah_num: str, audio_files: list):
        """Set the current song index by surah number with comprehensive logging."""
        if not isinstance(surah_num, str):
            log_operation("state", "ERROR", {
                "action": "set_index_by_surah_invalid_surah_type",
                "provided_surah": surah_num,
                "provided_type": type(surah_num).__name__
            })
            return
            
        if not isinstance(audio_files, list):
            log_operation("state", "ERROR", {
                "action": "set_index_by_surah_invalid_files_type",
                "provided_files_type": type(audio_files).__name__,
                "surah_num": surah_num
            })
            return
            
        if not audio_files:
            log_operation("state", "WARNING", {
                "action": "set_index_by_surah_empty_files_list",
                "surah_num": surah_num
            })
            self.set_current_song_index(0)
            return
        
        original_surah = surah_num
        surah_num = surah_num.zfill(3)  # Ensure 3-digit format
        
        log_operation("state", "DEBUG", {
            "action": "searching_for_surah",
            "original_surah": original_surah,
            "formatted_surah": surah_num,
            "total_files": len(audio_files)
        })
        
        for i, file_path in enumerate(audio_files):
            if not file_path:
                log_operation("state", "WARNING", {
                    "action": "found_empty_file_path",
                    "file_index": i,
                    "surah_num": surah_num
                })
                continue
                
            try:
                file_name = os.path.basename(file_path)
                if file_name.startswith(surah_num):
                    log_operation("state", "INFO", {
                        "action": "surah_found_setting_index",
                        "surah_num": surah_num,
                        "found_file": file_name,
                        "file_index": i,
                        "file_path": file_path
                    })
                    self.set_current_song_index(i)
                    return
            except Exception as e:
                log_operation("state", "WARNING", {
                    "action": "error_processing_file_path",
                    "file_path": file_path,
                    "file_index": i,
                    "surah_num": surah_num,
                    "error": str(e),
                    "error_type": type(e).__name__
                }, e)
                continue
        
        # If not found, set to 0
        log_operation("state", "WARNING", {
            "action": "surah_not_found_using_default",
            "surah_num": surah_num,
            "original_surah": original_surah,
            "total_files_searched": len(audio_files),
            "default_index": 0
        })
        self.set_current_song_index(0)
        
    def increment_songs_played(self):
        """Increment the total songs played counter with logging."""
        old_count = self.state.get('total_songs_played', 0)
        self.state['total_songs_played'] = old_count + 1
        self._save_state()
        
        log_operation("state", "DEBUG", {
            "action": "songs_played_incremented",
            "old_count": old_count,
            "new_count": self.state['total_songs_played']
        })
        
    def get_total_songs_played(self) -> int:
        """Get total songs played."""
        return self.state.get('total_songs_played', 0)
        
    def increment_bot_start_count(self):
        """Increment bot start count with logging."""
        old_count = self.state.get('bot_start_count', 0)
        self.state['bot_start_count'] = old_count + 1
        self._save_state()
        
        log_operation("state", "INFO", {
            "action": "bot_start_count_incremented", 
            "old_count": old_count,
            "new_count": self.state['bot_start_count']
        })
        
    def get_bot_start_count(self) -> int:
        """Get bot start count."""
        return self.state.get('bot_start_count', 0)
        
    def get_last_played_time(self) -> Optional[datetime]:
        """Get last played time."""
        last_time = self.state.get('last_played_time')
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
            'current_song_index': self.get_current_song_index(),
            'current_song_name': self.get_current_song_name(),
            'total_songs_played': self.get_total_songs_played(),
            'bot_start_count': self.get_bot_start_count(),
            'last_played_time': last_played.isoformat() if last_played else None,
            'last_state_save': self.state.get('last_state_save')
        }
        
    def reset_state(self):
        """Reset state to default values."""
        self.state = {
            'current_song_index': 0,
            'current_song_name': None,
            'total_songs_played': 0,
            'last_played_time': None,
            'bot_start_count': self.state.get('bot_start_count', 0),
            'last_state_save': None
        }
        self._save_state() 