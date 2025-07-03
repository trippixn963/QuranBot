"""
Configuration management for the Discord Quran Bot.
Centralized configuration for all bot settings.
"""

import os
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from monitoring.logging.log_helpers import log_function_call, log_operation
import datetime
import pytz
import time

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for the Quran Bot."""
    
    # Discord Bot Configuration
    DISCORD_TOKEN: Optional[str] = os.getenv('DISCORD_TOKEN')
    TARGET_CHANNEL_ID: int = int(os.getenv('TARGET_CHANNEL_ID', '1389675580253016144'))
    PANEL_CHANNEL_ID: int = int(os.getenv('PANEL_CHANNEL_ID', '1389716643512455219'))
    LOGS_CHANNEL_ID: int = int(os.getenv('LOGS_CHANNEL_ID', '1389683881078423567'))
    TARGET_GUILD_ID: Optional[int] = None
    DAILY_VERSE_CHANNEL_ID: int = int(os.getenv('DAILY_VERSE_CHANNEL_ID'))
    
    # Audio Configuration
    AUDIO_FOLDER: str = os.getenv('AUDIO_FOLDER', 'audio')
    AUDIO_QUALITY: str = os.getenv('AUDIO_QUALITY', '128k')
    AUDIO_FORMAT: str = "mp3"
    DEFAULT_RECITER: str = os.getenv('DEFAULT_RECITER', 'Saad Al Ghamdi')
    
    # FFmpeg Configuration
    FFMPEG_PATH: str = os.getenv('FFMPEG_PATH', r"C:\ffmpeg\bin")
    FFMPEG_OPTIONS: str = "-vn -b:a 128k -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/quran_bot.log"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Bot Behavior
    AUTO_RECONNECT: bool = True
    RECONNECT_DELAY: int = 5  # seconds
    STREAM_TIMEOUT: int = 30  # seconds
    AUTO_VOICE_CONNECT: bool = True  # Enable automatic voice connection
    
    # Performance Settings
    MAX_RECONNECT_ATTEMPTS: int = 10
    HEARTBEAT_INTERVAL: int = 5  # seconds
    
    # Add to Config or the appropriate state manager:
    last_activity = {'action': '', 'user_id': None, 'user_name': ''}
    loop_user_id = None
    shuffle_user_id = None
    user_timezones = {}  # user_id -> timezone string
    
    DEVELOPER_ID: int = int(os.getenv('DEVELOPER_ID'))
    
    @classmethod
    @log_function_call
    def validate(cls) -> bool:
        """Validate configuration settings."""
        if not cls.DISCORD_TOKEN or cls.DISCORD_TOKEN == "your_token_here":
            from monitoring.logging.logger import logger
            logger.critical("❌ Error: Discord token not configured!")
            return False
            
        if not os.path.exists(cls.AUDIO_FOLDER):
            from monitoring.logging.logger import logger
            logger.warning(f"⚠️  Warning: Audio folder '{cls.AUDIO_FOLDER}' not found!")
            
        return True
    
    @classmethod
    @log_function_call
    def get_reciter_display_name(cls, folder_name: str) -> str:
        """Get the display name for a reciter folder name."""
        display_names = {
            "Saad Al Ghamdi": "Saad Al Ghamdi",
            "Maher Al Muaiqly": "Maher Al Muaiqly",
            "Muhammad Al Luhaidan": "Muhammad Al Luhaidan",
            "Rashid Al Afasy": "Rashid Al Afasy",
            "Abdul Basit Abdul Samad": "Abdul Basit Abdul Samad",
            "Yasser Al Dosari": "Yasser Al Dosari",
            # Add more mappings as needed
        }
        return display_names.get(folder_name, folder_name)
    
    @classmethod
    @log_function_call
    def get_reciter_arabic_name(cls, folder_name: str) -> str:
        """Get the Arabic name for a reciter folder name."""
        arabic_names = {
            "Saad Al Ghamdi": "سعد الغامدي",
            "Maher Al Muaiqly": "ماهر المعيقلي",
            "Muhammad Al Luhaidan": "محمد اللحيدان",
            "Rashid Al Afasy": "مشاري راشد العفاسي",
            "Abdul Basit Abdul Samad": "عبد الباسط عبد الصمد",
            "Yasser Al Dosari": "ياسر الدوسري",
            # Add more mappings as needed
        }
        return arabic_names.get(folder_name, "")
    
    @classmethod
    @log_function_call
    def get_available_reciters(cls) -> List[str]:
        """Get list of available reciters from the audio folder."""
        reciters = []
        
        if not os.path.exists(cls.AUDIO_FOLDER):
            return reciters
            
        for item in os.listdir(cls.AUDIO_FOLDER):
            item_path = os.path.join(cls.AUDIO_FOLDER, item)
            if os.path.isdir(item_path):
                # Check if the folder contains MP3 files
                try:
                    has_mp3 = any(f.lower().endswith('.mp3') for f in os.listdir(item_path))
                    if has_mp3:
                        display_name = cls.get_reciter_display_name(item)
                        reciters.append(display_name)
                except (PermissionError, OSError):
                    # Skip folders we can't access
                    continue
                    
        return sorted(reciters)
    
    @classmethod
    @log_function_call
    def get_folder_name_from_display(cls, display_name: str) -> str:
        """Get the folder name from a display name."""
        folder_to_display = {
            "Saad Al Ghamdi": "Saad Al Ghamdi",
            "Maher Al Muaiqly": "Maher Al Muaiqly",
            "Muhammad Al Luhaidan": "Muhammad Al Luhaidan",
            "Rashid Al Afasy": "Rashid Al Afasy",
            "Abdul Basit Abdul Samad": "Abdul Basit Abdul Samad",
            "Yasser Al Dosari": "Yasser Al Dosari",
            # Add more mappings as needed
        }
        
        # Reverse lookup
        for folder, display in folder_to_display.items():
            if display == display_name:
                return folder
        
        # If no mapping found, return the display name as is
        return display_name
    
    @classmethod
    @log_function_call
    def get_reciter_info(cls, reciter_name: str) -> Dict[str, Any]:
        """Get information about a specific reciter."""
        reciter_path = os.path.join(cls.AUDIO_FOLDER, reciter_name)
        
        if not os.path.exists(reciter_path) or not os.path.isdir(reciter_path):
            return {"exists": False, "files": 0, "path": reciter_path}
        
        mp3_files = [f for f in os.listdir(reciter_path) if f.lower().endswith('.mp3')]
        
        return {
            "exists": True,
            "files": len(mp3_files),
            "path": reciter_path,
            "file_list": sorted(mp3_files)
        }
    
    @classmethod
    @log_function_call
    def get_audio_files(cls, reciter_name: Optional[str] = None) -> List[str]:
        """Get list of audio files from the configured folder or specific reciter."""
        audio_files = []
        
        if not os.path.exists(cls.AUDIO_FOLDER):
            return audio_files
        
        if reciter_name:
            # Get files from specific reciter
            reciter_path = os.path.join(cls.AUDIO_FOLDER, reciter_name)
            if os.path.exists(reciter_path) and os.path.isdir(reciter_path):
                for file in os.listdir(reciter_path):
                    if file.lower().endswith('.mp3'):
                        audio_files.append(os.path.join(reciter_path, file))
        else:
            # Get files from all reciters (legacy behavior)
            for root, dirs, files in os.walk(cls.AUDIO_FOLDER):
                for file in files:
                    if file.lower().endswith('.mp3'):
                        audio_files.append(os.path.join(root, file))
                    
        return sorted(audio_files)
    
    @classmethod
    @log_function_call
    def get_current_reciter(cls) -> str:
        """Get the current active reciter display name."""
        # Convert the default reciter (which is a display name) to folder name first
        folder_name = cls.get_folder_name_from_display(cls.DEFAULT_RECITER)
        return cls.get_reciter_display_name(folder_name)
    
    @classmethod
    @log_function_call
    def setup_environment(cls) -> None:
        """Setup environment variables and paths."""
        # Add FFmpeg to PATH
        if cls.FFMPEG_PATH not in os.environ.get("PATH", ""):
            os.environ["PATH"] += os.pathsep + cls.FFMPEG_PATH
            
        # Create necessary directories
        os.makedirs("logs", exist_ok=True)
        os.makedirs(cls.AUDIO_FOLDER, exist_ok=True)

    @classmethod
    def set_last_activity(cls, action, user_id, user_name):
        # Save last activity with Unix timestamp for Discord formatting
        cls.last_activity = {
            'action': action,
            'user_id': user_id,
            'user_name': user_name,
            'timestamp_unix': int(time.time())  # Unix timestamp for Discord formatting
        }

    @classmethod
    def set_user_timezone(cls, user_id, timezone_str):
        cls.user_timezones[user_id] = timezone_str

    @classmethod
    def get_user_timezone(cls, user_id):
        return cls.user_timezones.get(user_id, 'US/Eastern')

    @classmethod
    def get_last_activity(cls):
        """Get the last activity data."""
        return getattr(cls, 'last_activity', None)

    @classmethod
    def get_loop_user(cls):
        """Get the user ID who enabled loop."""
        return getattr(cls, 'loop_user_id', None)
    
    @classmethod
    def get_shuffle_user(cls):
        """Get the user ID who enabled shuffle."""
        return getattr(cls, 'shuffle_user_id', None)
    
    @classmethod
    def get_last_activity_discord_time(cls):
        """Get the last activity time in Discord timestamp format for automatic timezone conversion."""
        last = getattr(cls, 'last_activity', None)
        if not last or 'timestamp_unix' not in last:
            return None
        return f"<t:{last['timestamp_unix']}:t>"  # Short time format with AM/PM in user's timezone

    @classmethod
    def should_show_last_activity(cls):
        """Check if the last activity should be displayed (within 15 minutes of the action)."""
        last = getattr(cls, 'last_activity', None)
        if not last or 'timestamp_unix' not in last:
            return False
        
        current_time = int(time.time())
        time_diff = current_time - last['timestamp_unix']
        return time_diff <= 900  # 15 minutes = 900 seconds

    @classmethod
    def set_loop_user(cls, user_id):
        """Set the user ID who enabled loop."""
        cls.loop_user_id = user_id
    
    @classmethod
    def set_shuffle_user(cls, user_id):
        """Set the user ID who enabled shuffle."""
        cls.shuffle_user_id = user_id

def set_loop_user(user_id):
    Config.loop_user_id = user_id

def get_loop_user():
    return getattr(Config, 'loop_user_id', None)

def set_shuffle_user(user_id):
    Config.shuffle_user_id = user_id

def get_shuffle_user():
    return getattr(Config, 'shuffle_user_id', None) 