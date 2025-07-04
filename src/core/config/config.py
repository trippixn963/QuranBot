"""
Configuration management for the Discord Quran Bot.
Centralized configuration for all bot settings with comprehensive validation and error handling.

This module provides a centralized configuration system for the Quran Bot including:
- Discord bot settings and tokens
- Audio configuration and FFmpeg settings
- Logging configuration
- Bot behavior settings
- Performance and reconnection settings
- Reciter management and display names
- Environment setup and validation

Features:
    - Environment variable loading with fallbacks
    - Cross-platform FFmpeg path detection
    - Comprehensive configuration validation
    - Reciter name mapping and display
    - User activity tracking
    - Timezone management
    - Error handling and logging

Author: John (Discord: Trippxin)
Version: 2.0.0
"""

import os
import platform
import shutil
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from src.monitoring.logging.tree_log import tree_log
import datetime
import pytz
import time
import traceback

# Load environment variables from .env file
load_dotenv()


class Config:
    """
    Configuration class for the Quran Bot.

    This class provides centralized configuration management for all bot settings
    including Discord tokens, audio settings, logging configuration, and more.

    Features:
        - Environment variable loading with validation
        - Cross-platform FFmpeg path detection
        - Reciter name mapping and display
        - User activity and timezone tracking
        - Comprehensive error handling and logging

    Attributes:
        DISCORD_TOKEN (str): Discord bot token
        TARGET_CHANNEL_ID (int): Target voice channel ID
        PANEL_CHANNEL_ID (int): Control panel channel ID
        LOGS_CHANNEL_ID (int): Logs channel ID
        AUDIO_FOLDER (str): Audio files directory
        DEFAULT_RECITER (str): Default reciter name
        AUTO_VOICE_CONNECT (bool): Auto-connect to voice channel
        MAX_RECONNECT_ATTEMPTS (int): Maximum reconnection attempts
    """

    # Discord Bot Configuration
    DISCORD_TOKEN: Optional[str] = os.getenv("DISCORD_TOKEN")
    TARGET_CHANNEL_ID: int = int(os.getenv("TARGET_CHANNEL_ID", "0"))
    PANEL_CHANNEL_ID: int = int(os.getenv("PANEL_CHANNEL_ID", "0"))
    LOGS_CHANNEL_ID: int = int(os.getenv("LOGS_CHANNEL_ID", "0"))
    TARGET_GUILD_ID: Optional[int] = None
    DAILY_VERSE_CHANNEL_ID: int = int(os.getenv("DAILY_VERSE_CHANNEL_ID", "0"))

    # Audio Configuration
    AUDIO_FOLDER: str = os.getenv("AUDIO_FOLDER", "audio")
    AUDIO_QUALITY: str = os.getenv("AUDIO_QUALITY", "128k")
    AUDIO_FORMAT: str = "mp3"
    DEFAULT_RECITER: str = os.getenv("DEFAULT_RECITER", "Saad Al Ghamdi")

    # FFmpeg Configuration
    FFMPEG_OPTIONS: str = (
        "-vn -b:a 128k -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
    )

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

    # User Activity Tracking
    last_activity = {"action": "", "user_id": None, "user_name": ""}
    loop_user_id = None
    shuffle_user_id = None
    user_timezones = {}  # user_id -> timezone string

    # Developer Configuration
    DEVELOPER_ID: int = int(os.getenv("DEVELOPER_ID", "0"))

    @classmethod
    def get_ffmpeg_path(cls) -> str:
        """
        Get FFmpeg path with cross-platform detection and fallbacks.

        This method attempts to locate FFmpeg on the system using multiple strategies:
        1. Check environment variable FFMPEG_PATH
        2. Search system PATH for ffmpeg binary
        3. Check platform-specific common installation paths
        4. Fall back to default paths

        Returns:
            str: Path to directory containing FFmpeg executable

        Raises:
            FileNotFoundError: If FFmpeg cannot be found on the system
        """
        try:
            # First check if explicitly set in environment
            env_path = os.getenv("FFMPEG_PATH")
            if env_path and os.path.exists(env_path):
                tree_log('info', 'Using FFmpeg from environment', {'event': 'FFMPEG_ENV', 'path': env_path})
                return env_path

            # Try to find ffmpeg in system PATH
            ffmpeg_binary = shutil.which("ffmpeg")
            if ffmpeg_binary:
                # Get the directory containing ffmpeg
                ffmpeg_dir = os.path.dirname(ffmpeg_binary)
                tree_log('info', 'Found FFmpeg in PATH', {'event': 'FFMPEG_PATH', 'path': ffmpeg_dir})
                return ffmpeg_dir

            # Platform-specific fallback paths
            system = platform.system().lower()
            tree_log('info', 'Searching for FFmpeg', {'event': 'FFMPEG_SEARCH', 'system': system})

            if system == "windows":
                windows_paths = [
                    r"C:\ffmpeg\bin",
                    r"C:\Program Files\ffmpeg\bin",
                    r"C:\Program Files (x86)\ffmpeg\bin",
                    os.path.expanduser(r"~\ffmpeg\bin"),
                    r"C:\ProgramData\chocolatey\lib\ffmpeg\tools\ffmpeg\bin",
                ]
                for path in windows_paths:
                    if os.path.exists(path) and os.path.exists(
                        os.path.join(path, "ffmpeg.exe")
                    ):
                        tree_log('info', 'Found FFmpeg on Windows', {'event': 'FFMPEG_WIN', 'path': path})
                        return path

            elif system == "linux":
                linux_paths = [
                    "/usr/bin",
                    "/usr/local/bin",
                    "/opt/ffmpeg/bin",
                    "/snap/bin",
                ]
                for path in linux_paths:
                    if os.path.exists(path) and os.path.exists(
                        os.path.join(path, "ffmpeg")
                    ):
                        tree_log('info', 'Found FFmpeg on Linux', {'event': 'FFMPEG_LINUX', 'path': path})
                        return path

            elif system == "darwin":  # macOS
                mac_paths = ["/usr/local/bin", "/opt/homebrew/bin", "/usr/bin"]
                for path in mac_paths:
                    if os.path.exists(path) and os.path.exists(
                        os.path.join(path, "ffmpeg")
                    ):
                        tree_log('info', 'Found FFmpeg on macOS', {'event': 'FFMPEG_MAC', 'path': path})
                        return path

            # Final fallback based on platform
            if system == "windows":
                fallback_path = r"C:\ffmpeg\bin"
            else:
                fallback_path = "/usr/bin"

            tree_log('warning', 'Using fallback FFmpeg path', {'event': 'FFMPEG_FALLBACK', 'path': fallback_path})
            return fallback_path

        except Exception as e:
            tree_log('error', 'Error detecting FFmpeg path', {'event': 'FFMPEG_ERROR', 'error': str(e), 'traceback': traceback.format_exc()})

            # Return a reasonable default
            if platform.system().lower() == "windows":
                return r"C:\ffmpeg\bin"
            else:
                return "/usr/bin"

    @classmethod
    def validate(cls) -> bool:
        """
        Validate configuration settings.

        This method performs comprehensive validation of all critical
        configuration settings and reports any issues found.

        Returns:
            bool: True if configuration is valid, False otherwise
        """
        try:
            tree_log('info', 'Validating configuration settings', {'event': 'CONFIG_VALIDATE_START'})

            # Check Discord token
            if not cls.DISCORD_TOKEN or cls.DISCORD_TOKEN == "your_token_here":
                tree_log('critical', 'Discord token not configured', {'event': 'CONFIG_TOKEN_MISSING'})
                tree_log('critical', 'Please set DISCORD_TOKEN in your .env file', {'event': 'CONFIG_TOKEN_HINT'})
                return False
            else:
                tree_log('info', 'Discord token configured', {'event': 'CONFIG_TOKEN_OK'})

            # Check audio folder
            if not os.path.exists(cls.AUDIO_FOLDER):
                tree_log('warning', 'Audio folder not found', {'event': 'CONFIG_AUDIO_FOLDER_MISSING', 'folder': cls.AUDIO_FOLDER})
                tree_log('warning', 'Please ensure the audio folder exists and contains reciter subfolders', {'event': 'CONFIG_AUDIO_FOLDER_HINT'})
            else:
                tree_log('info', 'Audio folder found', {'event': 'CONFIG_AUDIO_FOLDER_OK', 'folder': cls.AUDIO_FOLDER})

            # Check FFmpeg
            ffmpeg_path = cls.get_ffmpeg_path()
            ffmpeg_bin = "ffmpeg.exe" if platform.system().lower() == "windows" else "ffmpeg"
            if os.path.exists(os.path.join(ffmpeg_path, ffmpeg_bin)):
                tree_log('info', 'FFmpeg found', {'event': 'CONFIG_FFMPEG_OK', 'path': ffmpeg_path})
            else:
                tree_log('warning', 'FFmpeg not found', {'event': 'CONFIG_FFMPEG_MISSING', 'path': ffmpeg_path})
                tree_log('warning', 'Please install FFmpeg for audio playback', {'event': 'CONFIG_FFMPEG_HINT'})

            # Check required directories
            required_dirs = ["logs", "data"]
            for dir_name in required_dirs:
                if not os.path.exists(dir_name):
                    tree_log('info', 'Creating required directory', {'event': 'CONFIG_MKDIR', 'dir': dir_name})
                    os.makedirs(dir_name, exist_ok=True)
                else:
                    tree_log('info', 'Required directory exists', {'event': 'CONFIG_DIR_OK', 'dir': dir_name})

            tree_log('info', 'Configuration validation completed', {'event': 'CONFIG_VALIDATE_DONE'})
            return True

        except Exception as e:
            tree_log('error', 'Configuration validation failed', {'event': 'CONFIG_VALIDATE_ERROR', 'error': str(e), 'traceback': traceback.format_exc()})
            return False

    @classmethod
    def get_reciter_display_name(cls, folder_name: str) -> str:
        """
        Get the display name for a reciter folder name.

        This method maps internal folder names to user-friendly display names
        for the bot's interface.

        Args:
            folder_name (str): Internal folder name of the reciter

        Returns:
            str: User-friendly display name for the reciter
        """
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
    def get_reciter_arabic_name(cls, folder_name: str) -> str:
        """
        Get the Arabic name for a reciter folder name.

        This method provides Arabic names for reciters to support
        multilingual display in the bot interface.

        Args:
            folder_name (str): Internal folder name of the reciter

        Returns:
            str: Arabic name for the reciter
        """
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
    def get_available_reciters(cls) -> List[str]:
        """
        Get list of available reciters from the audio folder.

        This method scans the audio folder for reciter subdirectories
        and returns a list of available reciters with proper display names.

        Returns:
            List[str]: List of available reciter display names
        """
        try:
            reciters = []

            if not os.path.exists(cls.AUDIO_FOLDER):
                tree_log('warning', 'Audio folder not found', {'event': 'RECITERS_AUDIO_FOLDER_MISSING', 'folder': cls.AUDIO_FOLDER})
                return reciters

            tree_log('info', 'Scanning for reciters', {'event': 'RECITERS_SCAN', 'folder': cls.AUDIO_FOLDER})

            for item in os.listdir(cls.AUDIO_FOLDER):
                item_path = os.path.join(cls.AUDIO_FOLDER, item)
                if os.path.isdir(item_path):
                    # Check if the folder contains MP3 files
                    try:
                        has_mp3 = any(
                            f.lower().endswith(".mp3") for f in os.listdir(item_path)
                        )
                        if has_mp3:
                            display_name = cls.get_reciter_display_name(item)
                            reciters.append(display_name)
                            tree_log('debug', 'Found reciter', {'event': 'RECITER_FOUND', 'display_name': display_name})
                    except (PermissionError, OSError) as e:
                        tree_log('warning', 'Cannot access reciter folder', {'event': 'RECITER_FOLDER_ACCESS_ERROR', 'folder': item, 'error': str(e)})
                        continue

            tree_log('info', 'Available reciters found', {'event': 'RECITERS_FOUND', 'count': len(reciters)})
            return sorted(reciters)

        except Exception as e:
            tree_log('error', 'Error scanning for reciters', {'event': 'RECITERS_SCAN_ERROR', 'error': str(e), 'traceback': traceback.format_exc()})
            return []

    @classmethod
    def get_folder_name_from_display(cls, display_name: str) -> str:
        """
        Get the folder name from a display name.

        This method performs reverse mapping from display names
        back to internal folder names.

        Args:
            display_name (str): User-friendly display name

        Returns:
            str: Internal folder name for the reciter
        """
        folder_to_display = {
            "Saad Al Ghamdi": "Saad Al Ghamdi",
            "Maher Al Muaiqly": "Maher Al Muaiqly",
            "Muhammad Al Luhaidan": "Muhammad Al Luhaidan",
            "Rashid Al Afasy": "Rashid Al Afasy",
            "Abdul Basit Abdul Samad": "Abdul Basit Abdul Samad",
            "Yasser Al Dosari": "Yasser Al Dosari",
            # Add more mappings as needed
        }

        # Reverse the mapping
        display_to_folder = {v: k for k, v in folder_to_display.items()}
        return display_to_folder.get(display_name, display_name)

    @classmethod
    def get_reciter_info(cls, reciter_name: str) -> Dict[str, Any]:
        """
        Get comprehensive information about a specific reciter.

        This method provides detailed information about a reciter including
        file count, display names, and path information.

        Args:
            reciter_name (str): Name of the reciter folder

        Returns:
            Dict[str, Any]: Dictionary containing reciter information
        """
        try:
            reciter_path = os.path.join(cls.AUDIO_FOLDER, reciter_name)

            if not os.path.exists(reciter_path) or not os.path.isdir(reciter_path):
                tree_log('warning', 'Reciter path not found', {'event': 'RECITER_PATH_MISSING', 'path': reciter_path})
                return {"exists": False, "files": 0, "path": reciter_path}

            mp3_files = [
                f for f in os.listdir(reciter_path) if f.lower().endswith(".mp3")
            ]

            tree_log('debug', 'Found MP3 files for reciter', {'event': 'RECITER_MP3_FOUND', 'reciter': reciter_name, 'count': len(mp3_files)})

            return {
                "exists": True,
                "files": len(mp3_files),
                "path": reciter_path,
                "file_list": sorted(mp3_files),
                "display_name": cls.get_reciter_display_name(reciter_name),
                "arabic_name": cls.get_reciter_arabic_name(reciter_name),
            }

        except Exception as e:
            tree_log('error', 'Error getting reciter info', {'event': 'RECITER_INFO_ERROR', 'reciter': reciter_name, 'error': str(e), 'traceback': traceback.format_exc()})
            return {"exists": False, "files": 0, "path": "", "error": str(e)}

    @classmethod
    def get_audio_files(cls, reciter_name: Optional[str] = None) -> List[str]:
        """
        Get list of audio files from the configured folder or specific reciter.

        This method scans for MP3 files either from a specific reciter folder
        or from all reciter folders if no specific reciter is provided.

        Args:
            reciter_name (Optional[str]): Specific reciter folder name, or None for all

        Returns:
            List[str]: Sorted list of audio file paths
        """
        try:
            audio_files = []

            if not os.path.exists(cls.AUDIO_FOLDER):
                tree_log('warning', 'Audio folder not found', {'event': 'AUDIO_FILES_FOLDER_MISSING', 'folder': cls.AUDIO_FOLDER})
                return audio_files

            if reciter_name:
                # Get files from specific reciter
                reciter_path = os.path.join(cls.AUDIO_FOLDER, reciter_name)
                if os.path.exists(reciter_path) and os.path.isdir(reciter_path):
                    for file in os.listdir(reciter_path):
                        if file.lower().endswith(".mp3"):
                            audio_files.append(os.path.join(reciter_path, file))
                    tree_log('debug', 'Found audio files for reciter', {'event': 'AUDIO_FILES_RECITER', 'reciter': reciter_name, 'count': len(audio_files)})
                else:
                    tree_log('warning', 'Reciter path not found', {'event': 'AUDIO_FILES_RECITER_PATH_MISSING', 'reciter': reciter_name, 'path': reciter_path})
            else:
                # Get files from all reciters (legacy behavior)
                for root, dirs, files in os.walk(cls.AUDIO_FOLDER):
                    for file in files:
                        if file.lower().endswith(".mp3"):
                            audio_files.append(os.path.join(root, file))
                tree_log('debug', 'Found total audio files', {'event': 'AUDIO_FILES_TOTAL', 'count': len(audio_files)})

            return sorted(audio_files)

        except Exception as e:
            tree_log('error', 'Error getting audio files', {'event': 'AUDIO_FILES_ERROR', 'error': str(e), 'traceback': traceback.format_exc()})
            return []

    @classmethod
    def get_current_reciter(cls) -> str:
        """Get the current active reciter display name."""
        # Convert the default reciter (which is a display name) to folder name first
        folder_name = cls.get_folder_name_from_display(cls.DEFAULT_RECITER)
        return cls.get_reciter_display_name(folder_name)

    @classmethod
    def setup_environment(cls) -> None:
        """
        Setup environment variables and paths.

        This method configures the runtime environment including:
        - Adding FFmpeg to system PATH
        - Creating necessary directories
        - Setting up logging paths

        The method includes comprehensive error handling and logging
        to ensure reliable environment setup.
        """
        try:
            tree_log('info', 'Setting up environment', {'event': 'ENV_SETUP_START'})

            # Add FFmpeg to PATH
            ffmpeg_path = cls.get_ffmpeg_path()
            if ffmpeg_path not in os.environ.get("PATH", ""):
                os.environ["PATH"] += os.pathsep + ffmpeg_path
                tree_log('info', 'Added FFmpeg to PATH', {'event': 'ENV_FFMPEG_PATH_ADDED', 'path': ffmpeg_path})
            else:
                tree_log('info', 'FFmpeg already in PATH', {'event': 'ENV_FFMPEG_PATH_EXISTS'})

            # Create necessary directories
            required_dirs = ["logs", cls.AUDIO_FOLDER, "data"]
            for dir_name in required_dirs:
                try:
                    os.makedirs(dir_name, exist_ok=True)
                    tree_log('info', 'Directory ready', {'event': 'ENV_DIR_READY', 'dir': dir_name})
                except Exception as e:
                    tree_log('error', 'Failed to create directory', {'event': 'ENV_DIR_ERROR', 'dir': dir_name, 'error': str(e)})

            tree_log('info', 'Environment setup completed', {'event': 'ENV_SETUP_DONE'})

        except Exception as e:
            tree_log('error', 'Environment setup failed', {'event': 'ENV_SETUP_ERROR', 'error': str(e), 'traceback': traceback.format_exc()})
            raise

    @classmethod
    def set_last_activity(cls, action: str, user_id: int, user_name: str) -> None:
        """
        Set the last activity performed by a user.

        This method tracks user activities with timestamps for display
        in Discord messages with automatic timezone conversion.

        Args:
            action (str): Description of the action performed
            user_id (int): Discord user ID
            user_name (str): Discord username
        """
        try:
            cls.last_activity = {
                "action": action,
                "user_id": user_id,
                "user_name": user_name,
                "timestamp_unix": int(time.time()),
            }
            tree_log('debug', 'Activity logged', {'event': 'LAST_ACTIVITY_SET', 'action': action, 'user_id': user_id, 'user_name': user_name})
        except Exception as e:
            tree_log('error', 'Failed to set last activity', {'event': 'LAST_ACTIVITY_ERROR', 'error': str(e)})

    @classmethod
    def set_user_timezone(cls, user_id: int, timezone_str: str) -> None:
        """
        Set the timezone for a specific user.

        Args:
            user_id (int): Discord user ID
            timezone_str (str): Timezone string (e.g., 'US/Eastern')
        """
        try:
            cls.user_timezones[user_id] = timezone_str
            tree_log('debug', 'Timezone set for user', {'event': 'USER_TZ_SET', 'user_id': user_id, 'timezone': timezone_str})
        except Exception as e:
            tree_log('error', 'Failed to set timezone for user', {'event': 'USER_TZ_ERROR', 'user_id': user_id, 'error': str(e)})

    @classmethod
    def get_user_timezone(cls, user_id: int) -> str:
        """
        Get the timezone for a specific user.

        Args:
            user_id (int): Discord user ID

        Returns:
            str: Timezone string, defaults to 'US/Eastern'
        """
        return cls.user_timezones.get(user_id, "US/Eastern")

    @classmethod
    def get_last_activity(cls) -> Optional[Dict[str, Any]]:
        """
        Get the last activity data.

        Returns:
            Optional[Dict[str, Any]]: Last activity data or None
        """
        return getattr(cls, "last_activity", None)

    @classmethod
    def get_loop_user(cls) -> Optional[int]:
        """
        Get the user ID who enabled loop.

        Returns:
            Optional[int]: User ID who enabled loop, or None
        """
        return getattr(cls, "loop_user_id", None)

    @classmethod
    def get_shuffle_user(cls) -> Optional[int]:
        """
        Get the user ID who enabled shuffle.

        Returns:
            Optional[int]: User ID who enabled shuffle, or None
        """
        return getattr(cls, "shuffle_user_id", None)

    @classmethod
    def get_last_activity_discord_time(cls) -> Optional[str]:
        """
        Get the last activity time in Discord timestamp format for automatic timezone conversion.

        Returns:
            Optional[str]: Discord timestamp format string or None
        """
        last = getattr(cls, "last_activity", None)
        if not last or "timestamp_unix" not in last:
            return None
        return f"<t:{last['timestamp_unix']}:t>"  # Short time format with AM/PM in user's timezone

    @classmethod
    def should_show_last_activity(cls) -> bool:
        """
        Check if the last activity should be displayed (within 15 minutes of the action).

        Returns:
            bool: True if activity should be shown, False otherwise
        """
        last = getattr(cls, "last_activity", None)
        if not last or "timestamp_unix" not in last:
            return False

        current_time = int(time.time())
        time_diff = current_time - last["timestamp_unix"]
        return time_diff <= 900  # 15 minutes = 900 seconds

    @classmethod
    def set_loop_user(cls, user_id: int) -> None:
        """
        Set the user ID who enabled loop.

        Args:
            user_id (int): Discord user ID who enabled loop
        """
        try:
            cls.loop_user_id = user_id
            tree_log('debug', 'Loop enabled by user', {'event': 'LOOP_USER_SET', 'user_id': user_id})
        except Exception as e:
            tree_log('error', 'Failed to set loop user', {'event': 'LOOP_USER_ERROR', 'error': str(e)})

    @classmethod
    def set_shuffle_user(cls, user_id: int) -> None:
        """
        Set the user ID who enabled shuffle.

        Args:
            user_id (int): Discord user ID who enabled shuffle
        """
        try:
            cls.shuffle_user_id = user_id
            tree_log('debug', 'Shuffle enabled by user', {'event': 'SHUFFLE_USER_SET', 'user_id': user_id})
        except Exception as e:
            tree_log('error', 'Failed to set shuffle user', {'event': 'SHUFFLE_USER_ERROR', 'error': str(e)})


def set_loop_user(user_id: int) -> None:
    """
    Set the user ID who enabled loop (standalone function).

    Args:
        user_id (int): Discord user ID who enabled loop
    """
    Config.set_loop_user(user_id)


def get_loop_user() -> Optional[int]:
    """
    Get the user ID who enabled loop (standalone function).

    Returns:
        Optional[int]: User ID who enabled loop, or None
    """
    return Config.get_loop_user()


def set_shuffle_user(user_id: int) -> None:
    """
    Set the user ID who enabled shuffle (standalone function).

    Args:
        user_id (int): Discord user ID who enabled shuffle
    """
    Config.set_shuffle_user(user_id)


def get_shuffle_user() -> Optional[int]:
    """
    Get the user ID who enabled shuffle (standalone function).

    Returns:
        Optional[int]: User ID who enabled shuffle, or None
    """
    return Config.get_shuffle_user()
