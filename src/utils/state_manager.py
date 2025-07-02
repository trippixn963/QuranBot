"""
State manager for the Discord Quran Bot.
Persists bot state across restarts including current song position.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

class StateManager:
    """Manages persistent state for the Quran Bot."""
    
    def __init__(self, state_file: str = "data/bot_state.json"):
        """Initialize the state manager."""
        self.state_file = state_file
        self.state = self._load_state()
        
    def _load_state(self) -> Dict[str, Any]:
        """Load state from file."""
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
                    return default_state
            except Exception as e:
                print(f"Failed to load state file: {e}")
                return default_state
        else:
            return default_state
            
    def _save_state(self):
        """Save current state to file."""
        try:
            self.state['last_state_save'] = datetime.now().isoformat()
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save state file: {e}")
            
    def get_current_song_index(self) -> int:
        """Get the current song index."""
        return self.state.get('current_song_index', 0)
        
    def set_current_song_index(self, index: int):
        """Set the current song index."""
        self.state['current_song_index'] = index
        self._save_state()
        
    def get_current_song_name(self) -> Optional[str]:
        """Get the current song name."""
        return self.state.get('current_song_name')
        
    def set_current_song_name(self, song_name: str):
        """Set the current song name."""
        self.state['current_song_name'] = song_name
        self.state['last_played_time'] = datetime.now().isoformat()
        self._save_state()
        
    def set_current_song_index_by_surah(self, surah_num: str, audio_files: list):
        """Set the current song index by surah number."""
        surah_num = surah_num.zfill(3)  # Ensure 3-digit format
        for i, file_path in enumerate(audio_files):
            file_name = os.path.basename(file_path)
            if file_name.startswith(surah_num):
                self.set_current_song_index(i)
                return
        # If not found, set to 0
        self.set_current_song_index(0)
        
    def increment_songs_played(self):
        """Increment the total songs played counter."""
        self.state['total_songs_played'] = self.state.get('total_songs_played', 0) + 1
        self._save_state()
        
    def get_total_songs_played(self) -> int:
        """Get total songs played."""
        return self.state.get('total_songs_played', 0)
        
    def increment_bot_start_count(self):
        """Increment bot start count."""
        self.state['bot_start_count'] = self.state.get('bot_start_count', 0) + 1
        self._save_state()
        
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