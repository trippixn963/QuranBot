"""
QuranBot - Configuration Management
==================================

Centralized configuration management for the QuranBot Discord application.
This module provides a comprehensive configuration system that handles all
bot settings, environment variables, and reciter management.

Key Features:
    - Environment variable loading from .env files
    - Discord bot configuration (tokens, channel IDs)
    - Audio and FFmpeg configuration
    - Reciter management and discovery
    - Logging configuration
    - Bot behavior settings
    - Configuration validation

Classes:
    Config: Main configuration class with all bot settings and utility methods

Environment Variables:
    DISCORD_TOKEN: Discord bot token (required)
    TARGET_CHANNEL_ID: Voice channel ID for streaming (required)
    PANEL_CHANNEL_ID: Control panel channel ID (required)
    LOGS_CHANNEL_ID: Logs channel ID (optional)
    AUDIO_FOLDER: Directory containing reciter folders (default: 'audio')
    DEFAULT_RECITER: Default reciter name (default: 'Saad Al Ghamdi')
    FFMPEG_PATH: Path to FFmpeg installation (default: 'C:\\ffmpeg\\bin')
    AUDIO_QUALITY: Audio quality for streaming (default: '128k')

Author: Trippixn (Discord)
License: MIT
Version: 2.1.0
"""

import os
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
# This allows configuration to be stored in a separate file
load_dotenv()


class Config:
    """
    Configuration class for the QuranBot Discord application.
    
    This class provides centralized access to all bot configuration settings,
    including Discord credentials, audio settings, reciter management, and
    bot behavior parameters. All settings can be configured via environment
    variables or have sensible defaults.
    
    Attributes:
        DISCORD_TOKEN (Optional[str]): Discord bot token from environment
        TARGET_CHANNEL_ID (int): Voice channel ID for Quran streaming
        PANEL_CHANNEL_ID (int): Channel ID for control panel
        LOGS_CHANNEL_ID (int): Channel ID for bot logs
        TARGET_GUILD_ID (Optional[int]): Guild ID (set at runtime)
        AUDIO_FOLDER (str): Directory containing reciter folders
        AUDIO_QUALITY (str): Audio quality for streaming
        AUDIO_FORMAT (str): Audio format (always 'mp3')
        DEFAULT_RECITER (str): Default reciter name
        FFMPEG_PATH (str): Path to FFmpeg installation
        FFMPEG_OPTIONS (str): FFmpeg command line options
        LOG_LEVEL (str): Logging level
        LOG_FILE (str): Log file path
        LOG_FORMAT (str): Log message format
        AUTO_RECONNECT (bool): Enable automatic reconnection
        RECONNECT_DELAY (int): Delay between reconnection attempts
        STREAM_TIMEOUT (int): Timeout for streaming operations
        AUTO_VOICE_CONNECT (bool): Enable automatic voice connection
        MAX_RECONNECT_ATTEMPTS (int): Maximum reconnection attempts
        HEARTBEAT_INTERVAL (int): Health check interval
    """
    
    # =============================================================================
    # Discord Bot Configuration
    # =============================================================================
    
    # Discord API credentials and channel IDs
    DISCORD_TOKEN: Optional[str] = os.getenv('DISCORD_TOKEN')
    TARGET_CHANNEL_ID: int = int(os.getenv('TARGET_CHANNEL_ID', '1389675580253016144'))
    PANEL_CHANNEL_ID: int = int(os.getenv('PANEL_CHANNEL_ID', '1389716643512455219'))
    LOGS_CHANNEL_ID: int = int(os.getenv('LOGS_CHANNEL_ID', '1389683881078423567'))
    TARGET_GUILD_ID: Optional[int] = None  # Set at runtime when channel is found
    
    # =============================================================================
    # Audio Configuration
    # =============================================================================
    
    # Audio file and streaming settings
    AUDIO_FOLDER: str = os.getenv('AUDIO_FOLDER', 'audio')
    AUDIO_QUALITY: str = os.getenv('AUDIO_QUALITY', '128k')
    AUDIO_FORMAT: str = "mp3"  # Currently only supports MP3
    DEFAULT_RECITER: str = os.getenv('DEFAULT_RECITER', 'Saad Al Ghamdi')
    
    # =============================================================================
    # FFmpeg Configuration
    # =============================================================================
    
    # FFmpeg installation path and streaming options
    FFMPEG_PATH: str = os.getenv('FFMPEG_PATH', r"C:\ffmpeg\bin")
    FFMPEG_OPTIONS: str = "-vn -b:a 128k -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
    
    # =============================================================================
    # Logging Configuration
    # =============================================================================
    
    # Logging settings and file paths
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/quran_bot.log"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # =============================================================================
    # Bot Behavior Configuration
    # =============================================================================
    
    # Connection and reconnection settings
    AUTO_RECONNECT: bool = True
    RECONNECT_DELAY: int = 5  # seconds between reconnection attempts
    STREAM_TIMEOUT: int = 30  # seconds timeout for streaming operations
    AUTO_VOICE_CONNECT: bool = True  # Enable automatic voice connection on startup
    
    # =============================================================================
    # Performance Settings
    # =============================================================================
    
    # Performance and reliability settings
    MAX_RECONNECT_ATTEMPTS: int = 10
    HEARTBEAT_INTERVAL: int = 5  # seconds between health checks
    
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration settings."""
        if not cls.DISCORD_TOKEN or cls.DISCORD_TOKEN == "your_token_here":
            print("❌ Error: Discord token not configured!")
            return False
            
        if not os.path.exists(cls.AUDIO_FOLDER):
            print(f"⚠️  Warning: Audio folder '{cls.AUDIO_FOLDER}' not found!")
            
        return True
    
    @classmethod
    def get_reciter_display_name(cls, folder_name: str) -> str:
        """Get the display name for a reciter folder name."""
        display_names = {
            "Saad Al Ghamdi": "Saad Al Ghamdi",
            "Maher Al Muaiqly": "Maher Al Muaiqly",
            "Muhammad Al Luhaidan": "Muhammad Al Luhaidan",
            "Rashid Al Afasy": "Rashid Al Afasy",
            # Add more mappings as needed
        }
        return display_names.get(folder_name, folder_name)
    
    @classmethod
    def get_available_reciters(cls) -> List[str]:
        """Get list of available reciters from the audio folder."""
        reciters = []
        
        if not os.path.exists(cls.AUDIO_FOLDER):
            return reciters
            
        for item in os.listdir(cls.AUDIO_FOLDER):
            item_path = os.path.join(cls.AUDIO_FOLDER, item)
            if os.path.isdir(item_path):
                # Check if the folder contains MP3 files
                has_mp3 = any(f.lower().endswith('.mp3') for f in os.listdir(item_path))
                if has_mp3:
                    display_name = cls.get_reciter_display_name(item)
                    if display_name in [
                        "Saad Al Ghamdi",
                        "Maher Al Muaiqly",
                        "Muhammad Al Luhaidan",
                        "Rashid Al Afasy"
                    ]:
                        reciters.append(display_name)
        return sorted(reciters)
    
    @classmethod
    def get_folder_name_from_display(cls, display_name: str) -> str:
        """Get the folder name from a display name."""
        folder_to_display = {
            "Saad Al Ghamdi": "Saad Al Ghamdi",
            "Maher Al Muaiqly": "Maher Al Muaiqly",
            "Muhammad Al Luhaidan": "Muhammad Al Luhaidan",
            "Rashid Al Afasy": "Rashid Al Afasy",
            # Add more mappings as needed
        }
        
        # Reverse lookup
        for folder, display in folder_to_display.items():
            if display == display_name:
                return folder
        
        # If no mapping found, return the display name as is
        return display_name
    
    @classmethod
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
    def get_current_reciter(cls) -> str:
        """Get the current active reciter display name."""
        # Convert the default reciter (which is a display name) to folder name first
        folder_name = cls.get_folder_name_from_display(cls.DEFAULT_RECITER)
        return cls.get_reciter_display_name(folder_name)
    
    @classmethod
    def setup_environment(cls) -> None:
        """Setup environment variables and paths."""
        # Add FFmpeg to PATH
        if cls.FFMPEG_PATH not in os.environ.get("PATH", ""):
            os.environ["PATH"] += os.pathsep + cls.FFMPEG_PATH
            
        # Create necessary directories
        os.makedirs("logs", exist_ok=True)
        os.makedirs(cls.AUDIO_FOLDER, exist_ok=True) 