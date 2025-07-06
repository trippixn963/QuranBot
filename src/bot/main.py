# =============================================================================
# QuranBot - Minimal Discord Audio Bot
# =============================================================================
# Simple Discord bot that connects to voice channels and plays Quran audio
# =============================================================================

import asyncio
import glob
import os
import traceback
from pathlib import Path

import discord
from discord.ext import commands

# =============================================================================
# Environment Configuration
# =============================================================================
from dotenv import load_dotenv

# Load environment variables from the correct path
env_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", ".env")
load_dotenv(env_path)

import os

# =============================================================================
# Import Tree Logging Functions
# =============================================================================
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# =============================================================================
# Discord Logging Configuration
# =============================================================================
import logging

# =============================================================================
# Import Audio Manager
# =============================================================================
from utils.audio_manager import AudioManager

# =============================================================================
# Import Control Panel Functions
# =============================================================================
from utils.control_panel import setup_control_panel

# =============================================================================
# Import Rich Presence Manager
# =============================================================================
from utils.rich_presence import RichPresenceManager, validate_rich_presence_dependencies

# =============================================================================
# Import State Manager
# =============================================================================
from utils.state_manager import state_manager

# =============================================================================
# Import Surah Mapping Functions
# =============================================================================
from utils.surah_mapper import (
    format_now_playing,
    get_surah_display,
    get_surah_info,
    validate_surah_number,
)
from utils.tree_log import (
    log_async_error,
    log_critical_error,
    log_discord_error,
    log_error_with_traceback,
    log_progress,
    log_section_start,
    log_spacing,
    log_status,
    log_tree,
    log_tree_branch,
    log_tree_end,
    log_tree_final,
    log_warning_with_context,
)

# =============================================================================
# Global Managers
# =============================================================================
rich_presence = None
audio_manager = None


class DiscordTreeHandler(logging.Handler):
    """
    Custom logging handler that formats Discord logs in tree-style format.

    This handler intercepts Discord.py log messages and reformats them using
    the QuranBot tree logging system for consistent visual presentation.
    It filters out verbose messages and maps Discord log levels to appropriate
    tree logging functions.

    Features:
    - Filters out heartbeat and other verbose Discord messages
    - Maps Discord modules to appropriate tree logging categories
    - Preserves log levels while using tree formatting
    - Writes formatted logs to both console and file systems

    Discord Modules Handled:
    - voice_state: Voice connection status and changes
    - gateway: Discord gateway connection events
    - client: Discord client authentication and status
    """

    def emit(self, record):
        """
        Handle a Discord log record by formatting it in tree style.

        Processes incoming Discord log records and converts them to tree-style
        logging with appropriate categorization and filtering. Skips verbose
        messages that would clutter the logs.

        Args:
            record: LogRecord object from Discord.py logging system
        """
        try:
            # Get the log message
            message = self.format(record)

            # Skip certain verbose messages to prevent log spam
            if any(
                skip in message.lower()
                for skip in [
                    "keeping websocket alive",
                    "sending heartbeat",
                    "received heartbeat",
                    "heartbeat acknowledged",
                ]
            ):
                return

            # Map Discord log levels to tree logging
            level_name = record.levelname
            logger_name = record.name

            # Import the file logging function for dual output
            from utils.tree_log import write_to_log_files

            # Format based on the Discord module for appropriate categorization
            if "voice_state" in logger_name:
                self._handle_voice_state_log(message, level_name)
            elif "gateway" in logger_name:
                self._handle_gateway_log(message, level_name)
            elif "client" in logger_name:
                self._handle_client_log(message, level_name)
            else:
                # Generic Discord log handling
                log_tree_branch("discord_info", f"📡 {message}")
                write_to_log_files(f"Discord: {message}", level_name, "discord_generic")

        except Exception as e:
            # Prevent logging errors from crashing the handler
            from utils.tree_log import log_error_with_traceback

            log_error_with_traceback("Error in DiscordTreeHandler.emit", e)

    def _handle_voice_state_log(self, message, level_name):
        """
        Handle voice state related log messages with appropriate categorization.

        Args:
            message: Log message content
            level_name: Original log level from Discord
        """
        from utils.tree_log import write_to_log_files

        if "connecting" in message.lower():
            log_tree_branch("voice_status", "🔄 Connecting to voice...")
            write_to_log_files(
                f"Discord Voice: Connecting to voice - {message}",
                level_name,
                "discord_voice",
            )
        elif "handshake" in message.lower():
            log_tree_branch("voice_handshake", "🤝 Voice handshake in progress")
            write_to_log_files(
                f"Discord Voice: Handshake in progress - {message}",
                level_name,
                "discord_voice",
            )
        elif "connection complete" in message.lower():
            log_tree_branch("voice_result", "✅ Voice connection established")
            write_to_log_files(
                f"Discord Voice: Connection established - {message}",
                level_name,
                "discord_voice",
            )
        elif "disconnected" in message.lower():
            log_tree_branch("voice_status", "⚠️ Voice disconnected - reconnecting...")
            write_to_log_files(
                f"Discord Voice: Disconnected - {message}",
                "WARNING",
                "discord_voice",
            )
        elif "terminated" in message.lower():
            log_tree_branch("voice_cleanup", "🧹 Voice connection terminated")
            write_to_log_files(
                f"Discord Voice: Connection terminated - {message}",
                level_name,
                "discord_voice",
            )
        else:
            log_tree_branch("voice_info", f"🎵 {message}")
            write_to_log_files(f"Discord Voice: {message}", level_name, "discord_voice")

    def _handle_gateway_log(self, message, level_name):
        """
        Handle Discord gateway related log messages.

        Args:
            message: Log message content
            level_name: Original log level from Discord
        """
        from utils.tree_log import write_to_log_files

        if "connected" in message.lower():
            log_tree_branch("discord_gateway", "✅ Connected to Discord Gateway")
            write_to_log_files(
                f"Discord Gateway: Connected - {message}",
                level_name,
                "discord_gateway",
            )
        elif "session" in message.lower():
            log_tree_branch("discord_session", "🔑 Discord session established")
            write_to_log_files(
                f"Discord Gateway: Session established - {message}",
                level_name,
                "discord_gateway",
            )
        else:
            log_tree_branch("discord_info", f"📡 {message}")
            write_to_log_files(
                f"Discord Gateway: {message}", level_name, "discord_gateway"
            )

    def _handle_client_log(self, message, level_name):
        """
        Handle Discord client related log messages.

        Args:
            message: Log message content
            level_name: Original log level from Discord
        """
        from utils.tree_log import write_to_log_files

        if "logging in" in message.lower():
            log_tree_branch("discord_auth", "🔐 Authenticating with Discord...")
            write_to_log_files(
                f"Discord Client: Authenticating - {message}",
                level_name,
                "discord_client",
            )
        else:
            log_tree_branch("discord_client", f"🤖 {message}")
            write_to_log_files(
                f"Discord Client: {message}", level_name, "discord_client"
            )


def setup_discord_logging():
    """
    Configure Discord loggers to use tree-style formatting consistently.

    Sets up custom logging handlers for all Discord.py loggers to ensure
    consistent tree-style formatting throughout the application. Replaces
    default Discord handlers with our custom DiscordTreeHandler.

    Features:
    - Removes default Discord logging handlers
    - Applies custom tree-style formatting
    - Prevents log duplication through propagation control
    - Configures appropriate log levels for each Discord module

    Discord Loggers Configured:
    - discord: Main Discord.py logger
    - discord.client: Client connection and authentication
    - discord.gateway: Gateway connection and session management
    - discord.voice_state: Voice connection state changes
    - discord.player: Audio player events and status
    """
    try:
        # Create our custom handler
        tree_handler = DiscordTreeHandler()
        tree_handler.setLevel(logging.INFO)

        # Configure main Discord loggers
        discord_loggers = [
            "discord",
            "discord.client",
            "discord.gateway",
            "discord.voice_state",
            "discord.player",
        ]

        for logger_name in discord_loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.INFO)

            # Remove existing handlers to prevent duplication
            logger.handlers.clear()

            # Add our tree handler
            logger.addHandler(tree_handler)

            # Prevent propagation to avoid duplicate logs
            logger.propagate = False

        log_tree_branch("discord_logging", "✅ Tree-style Discord logging configured")

    except Exception as e:
        log_error_with_traceback("Error setting up Discord logging", e)


# Initialize Discord logging
setup_discord_logging()

# =============================================================================
# Bot Setup & Configuration
# =============================================================================
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)

# =============================================================================
# Bot Version & Configuration
# =============================================================================
BOT_VERSION = "1.6.0"
BOT_NAME = "QuranBot"

# Configuration from Environment Variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID") or "0")
PANEL_CHANNEL_ID = int(os.getenv("PANEL_CHANNEL_ID") or "0")
GUILD_ID = int(os.getenv("GUILD_ID") or "0")
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")
AUDIO_FOLDER = "audio/Saad Al Ghamdi"

# Default Audio Settings from Environment
DEFAULT_RECITER = os.getenv("DEFAULT_RECITER", "Saad Al Ghamdi")
DEFAULT_SHUFFLE = os.getenv("DEFAULT_SHUFFLE", "false").lower() == "true"
DEFAULT_LOOP = os.getenv("DEFAULT_LOOP", "false").lower() == "true"


# =============================================================================
# Configuration Validation
# =============================================================================
def validate_configuration():
    """
    Validate bot configuration and environment variables comprehensively.

    Performs thorough validation of all required configuration parameters
    including Discord credentials, channel IDs, file paths, and external
    dependencies. Provides detailed error reporting and warnings for
    potential issues.

    Validation Categories:
    - Discord Authentication: Token validation and format checking
    - Server Configuration: Guild and channel ID validation
    - File System: Audio folder and FFmpeg executable checks
    - External Dependencies: Rich Presence and audio processing tools

    Returns:
        bool: True if all critical configuration is valid, False otherwise

    Note:
        Warnings are logged but don't prevent bot startup. Only critical
        errors (missing Discord token, invalid IDs) cause startup failure.
    """
    try:
        log_section_start("Configuration Validation", "🔧")

        errors = []
        warnings = []

        # =============================================================================
        # Discord Authentication Validation
        # =============================================================================
        if not DISCORD_TOKEN:
            errors.append("DISCORD_TOKEN is missing from environment variables")
        elif not isinstance(DISCORD_TOKEN, str):
            errors.append("DISCORD_TOKEN must be a string")
        elif len(DISCORD_TOKEN) < 50:
            warnings.append("DISCORD_TOKEN appears to be invalid (too short)")
        elif not DISCORD_TOKEN.startswith(("Bot ", "Bearer ")):
            # Discord tokens typically start with these prefixes
            warnings.append("DISCORD_TOKEN format may be incorrect")

        # =============================================================================
        # Server Configuration Validation
        # =============================================================================
        if GUILD_ID == 0:
            errors.append("GUILD_ID is missing or invalid in environment variables")
        elif not isinstance(GUILD_ID, int) or GUILD_ID < 0:
            errors.append("GUILD_ID must be a positive integer")

        if TARGET_CHANNEL_ID == 0:
            errors.append(
                "TARGET_CHANNEL_ID is missing or invalid in environment variables"
            )
        elif not isinstance(TARGET_CHANNEL_ID, int) or TARGET_CHANNEL_ID < 0:
            errors.append("TARGET_CHANNEL_ID must be a positive integer")

        if PANEL_CHANNEL_ID == 0:
            warnings.append(
                "PANEL_CHANNEL_ID is missing - control panel will not be created"
            )
        elif not isinstance(PANEL_CHANNEL_ID, int) or PANEL_CHANNEL_ID < 0:
            warnings.append("PANEL_CHANNEL_ID must be a positive integer")

        # =============================================================================
        # File System Validation
        # =============================================================================
        if not AUDIO_FOLDER:
            errors.append("AUDIO_FOLDER is not specified")
        elif not os.path.exists(AUDIO_FOLDER):
            warnings.append(f"Audio folder '{AUDIO_FOLDER}' does not exist")
        elif not os.path.isdir(AUDIO_FOLDER):
            warnings.append(f"Audio folder '{AUDIO_FOLDER}' is not a directory")
        else:
            # Check for audio files in the folder
            try:
                audio_files = glob.glob(os.path.join(AUDIO_FOLDER, "*.mp3"))
                if not audio_files:
                    warnings.append(f"No MP3 files found in '{AUDIO_FOLDER}'")
                else:
                    log_tree_branch(
                        "audio_files", f"Found {len(audio_files)} MP3 files"
                    )
            except Exception as e:
                warnings.append(f"Error scanning audio folder: {str(e)}")

        # =============================================================================
        # FFmpeg Validation
        # =============================================================================
        if not FFMPEG_PATH:
            errors.append("FFMPEG_PATH is not specified")
        else:
            try:
                import subprocess

                result = subprocess.run(
                    [FFMPEG_PATH, "-version"],
                    capture_output=True,
                    check=True,
                    timeout=10,
                )
                log_tree_branch("ffmpeg_check", "✅ FFmpeg is accessible")

                # Check FFmpeg version for compatibility
                version_output = result.stdout.decode("utf-8", errors="ignore")
                if "ffmpeg version" in version_output.lower():
                    version_line = version_output.split("\n")[0]
                    log_tree_branch("ffmpeg_version", version_line.strip())

            except subprocess.TimeoutExpired:
                warnings.append(f"FFmpeg at '{FFMPEG_PATH}' is not responding")
            except subprocess.CalledProcessError as e:
                warnings.append(
                    f"FFmpeg at '{FFMPEG_PATH}' returned error: {e.returncode}"
                )
            except FileNotFoundError:
                warnings.append(
                    f"FFmpeg not found at '{FFMPEG_PATH}' - audio playback may fail"
                )
            except Exception as e:
                log_error_with_traceback("Error checking FFmpeg availability", e)
                warnings.append(f"Could not validate FFmpeg: {str(e)}")

        # =============================================================================
        # Environment Defaults Validation
        # =============================================================================
        if not DEFAULT_RECITER:
            warnings.append("DEFAULT_RECITER is not specified, using fallback")
        elif not isinstance(DEFAULT_RECITER, str):
            warnings.append("DEFAULT_RECITER should be a string")

        if not isinstance(DEFAULT_SHUFFLE, bool):
            warnings.append("DEFAULT_SHUFFLE should be a boolean (true/false)")

        if not isinstance(DEFAULT_LOOP, bool):
            warnings.append("DEFAULT_LOOP should be a boolean (true/false)")

        # =============================================================================
        # External Dependencies Validation
        # =============================================================================
        try:
            rp_validation = validate_rich_presence_dependencies(FFMPEG_PATH)
            warnings.extend(rp_validation["warnings"])

            if rp_validation.get("errors"):
                warnings.extend(rp_validation["errors"])

        except Exception as e:
            log_error_with_traceback("Error validating Rich Presence dependencies", e)
            warnings.append("Could not validate Rich Presence dependencies")

        # =============================================================================
        # Results Reporting
        # =============================================================================
        if errors:
            log_tree_branch(
                "validation_errors", f"Found {len(errors)} critical errors:"
            )
            for error in errors:
                log_tree_branch("config_error", f"❌ {error}")
            log_tree_final("validation_result", "❌ Configuration validation failed")
            return False

        if warnings:
            log_tree_branch("validation_warnings", f"Found {len(warnings)} warnings:")
            for warning in warnings:
                log_tree_branch("config_warning", f"⚠️ {warning}")

        log_tree_final("validation_result", "✅ Configuration validation passed")
        return True

    except Exception as e:
        log_error_with_traceback("Critical error during configuration validation", e)
        log_tree_final(
            "validation_result", "❌ Configuration validation failed with error"
        )
        return False


# =============================================================================
# Discord Bot Events
# =============================================================================
@bot.event
async def on_ready():
    """
    Handle Discord bot ready event and initialize all bot systems.

    This is the main initialization event that sets up all bot components
    after successful Discord connection. It handles:
    - State manager initialization and session tracking
    - Rich Presence and Audio Manager setup
    - Configuration validation and error handling
    - Voice channel connection with retry logic
    - Control panel setup and integration
    - Graceful error recovery and logging

    The function implements robust error handling with retry logic for
    voice connections and comprehensive logging for troubleshooting.

    Raises:
        Various exceptions are caught and handled gracefully with appropriate
        logging and cleanup. Critical errors may cause bot shutdown.
    """
    global rich_presence, audio_manager

    try:
        # =============================================================================
        # Bot Startup and State Management
        # =============================================================================
        # Mark startup in state manager for session tracking
        state_manager.mark_startup()

        log_section_start(f"{BOT_NAME} v{BOT_VERSION} Started")
        log_tree_branch("bot_user", f"{bot.user}")
        log_tree_branch("version", BOT_VERSION)
        log_tree_branch("guild_id", GUILD_ID)
        log_tree_final("target_channel_id", TARGET_CHANNEL_ID)

        # =============================================================================
        # Manager Initialization
        # =============================================================================
        # Initialize Rich Presence Manager
        log_spacing()
        try:
            rich_presence = RichPresenceManager(bot, FFMPEG_PATH)
            log_tree_branch("rich_presence", "✅ Rich Presence Manager initialized")
        except Exception as e:
            log_error_with_traceback("Error initializing Rich Presence Manager", e)
            # Continue without Rich Presence if it fails
            rich_presence = None

        # Initialize Audio Manager with environment defaults
        try:
            audio_manager = AudioManager(
                bot,
                FFMPEG_PATH,
                default_reciter=DEFAULT_RECITER,
                default_shuffle=DEFAULT_SHUFFLE,
                default_loop=DEFAULT_LOOP,
            )
            audio_manager.set_rich_presence(rich_presence)
            log_tree_branch("audio_manager", "✅ Audio Manager initialized")
        except Exception as e:
            log_error_with_traceback("Error initializing Audio Manager", e)
            log_critical_error("Cannot continue without Audio Manager")
            await bot.close()
            return

        # =============================================================================
        # Configuration Validation
        # =============================================================================
        # Validate configuration before proceeding
        log_spacing()
        if not validate_configuration():
            log_critical_error("Bot configuration validation failed")
            await bot.close()
            return

        # =============================================================================
        # Discord Server and Channel Setup
        # =============================================================================
        # Get the guild and voice channel
        guild = bot.get_guild(GUILD_ID)
        if not guild:
            log_critical_error(f"Guild with ID {GUILD_ID} not found")
            return

        channel = guild.get_channel(TARGET_CHANNEL_ID)
        if not channel:
            log_critical_error(f"Channel with ID {TARGET_CHANNEL_ID} not found")
            return

        # Validate channel type
        if not isinstance(channel, discord.VoiceChannel):
            log_critical_error(f"Channel {TARGET_CHANNEL_ID} is not a voice channel")
            return

        log_spacing()
        log_tree("Attempting voice connection")
        log_tree_branch("channel_name", channel.name)
        log_tree_branch("channel_id", channel.id)
        log_tree_final("channel_type", "Voice Channel")

        # =============================================================================
        # Voice Connection with Retry Logic
        # =============================================================================
        # Connect to voice channel with retry logic
        max_retries = 3
        retry_delay = 10  # Longer delay to prevent rapid connection attempts
        voice_client = None

        for attempt in range(max_retries):
            try:
                # Check if already connected to avoid conflicts
                existing_voice_client = guild.voice_client
                if existing_voice_client and existing_voice_client.is_connected():
                    log_tree_branch(
                        "voice_status", "Already connected, using existing connection"
                    )
                    voice_client = existing_voice_client
                else:
                    log_tree_branch(
                        "voice_connection", f"Attempt {attempt + 1}/{max_retries}"
                    )
                    voice_client = await channel.connect(reconnect=False, timeout=60)
                    log_tree_branch("voice_connection", "✅ New connection established")

                log_tree_branch("connected_to", channel.name)

                # =============================================================================
                # Audio System Setup
                # =============================================================================
                # Set up AudioManager with voice client
                try:
                    audio_manager.set_voice_client(voice_client)
                    log_tree_branch("audio_setup", "✅ Audio system configured")
                except Exception as e:
                    log_error_with_traceback("Error setting up audio system", e)
                    raise  # Re-raise to trigger retry

                # =============================================================================
                # Control Panel Setup
                # =============================================================================
                # Set up control panel with AudioManager
                if PANEL_CHANNEL_ID != 0:
                    try:
                        await setup_control_panel(bot, PANEL_CHANNEL_ID, audio_manager)
                        log_tree_branch(
                            "control_panel", "✅ Control panel setup successful"
                        )
                    except Exception as e:
                        log_error_with_traceback("Error setting up control panel", e)
                        # Control panel failure is not critical, continue without it

                # =============================================================================
                # Commands Setup (Slash Commands Only)
                # =============================================================================
                # Set up slash commands - prefix commands are disabled
                log_spacing()
                log_tree_branch(
                    "command_system",
                    "Setting up slash commands (prefix commands disabled)",
                )
                log_tree_branch(
                    "prefix_status",
                    "⚠️ Prefix commands only work when bot is mentioned (@bot)",
                )
                log_tree_branch("slash_status", "✅ Slash commands enabled")

                try:
                    from src.commands import setup_credits_command

                    setup_credits_command(bot)

                    # Sync commands to Discord
                    await bot.tree.sync()
                    log_tree_branch(
                        "slash_commands", "✅ Slash commands synced successfully"
                    )
                    log_tree_branch("available_commands", "/credits")

                except Exception as e:
                    log_error_with_traceback("Error setting up slash commands", e)
                    # Command setup failure is not critical, continue without them

                # =============================================================================
                # Audio Playback Initialization
                # =============================================================================
                # Start playing audio using AudioManager
                try:
                    await audio_manager.start_playback()
                    log_tree_final(
                        "startup_complete", "✅ Bot initialization successful"
                    )
                except Exception as e:
                    log_error_with_traceback("Error starting audio playback", e)
                    raise  # Re-raise to trigger retry

                break  # Success, exit retry loop

            except discord.errors.ClientException as e:
                log_tree_branch(
                    "connection_error",
                    f"Discord client error on attempt {attempt + 1}: {str(e)}",
                )
                if "already connected" in str(e).lower():
                    # Handle already connected case
                    voice_client = guild.voice_client
                    if voice_client:
                        break

            except asyncio.TimeoutError:
                log_tree_branch(
                    "connection_error",
                    f"Connection timeout on attempt {attempt + 1}",
                )

            except Exception as e:
                log_tree_branch(
                    "connection_error",
                    f"Attempt {attempt + 1} failed: {type(e).__name__}: {str(e)}",
                )

            # Handle retry logic
            if attempt < max_retries - 1:
                log_tree_branch("retry", f"Waiting {retry_delay} seconds before retry")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                log_discord_error("on_ready", e, GUILD_ID, TARGET_CHANNEL_ID)
                log_tree_final("connection_status", "❌ All connection attempts failed")
                return

    except Exception as e:
        log_critical_error("Fatal error in on_ready event", e)
        # Attempt graceful shutdown on critical error
        try:
            await bot.close()
        except:
            pass  # Ignore errors during emergency shutdown


# =============================================================================
# Audio Playback Functions
# =============================================================================
async def play_audio(voice_client):
    """Play audio files from the audio folder with Rich Presence"""
    global rich_presence

    log_section_start("Audio Playback Started", "🎵")
    log_tree_branch("audio_folder", AUDIO_FOLDER)
    log_tree_final("ffmpeg_path", FFMPEG_PATH)

    try:
        # Get all mp3 files and sort them
        audio_files = sorted(glob.glob(os.path.join(AUDIO_FOLDER, "*.mp3")))

        if not audio_files:
            log_tree_end("No audio files found!", "ERROR")
            return

        log_tree("Audio files discovered", "SUCCESS")
        log_tree_branch("total_files", len(audio_files))
        log_tree_final("first_file", os.path.basename(audio_files[0]))

        # Play each file
        for i, audio_file in enumerate(audio_files, 1):
            try:
                if not voice_client.is_connected():
                    log_warning_with_context(
                        "Voice client disconnected, stopping playback",
                        f"File {i}/{len(audio_files)}",
                    )
                    break

                filename = os.path.basename(audio_file)

                # Extract Surah number from filename (assumes format like "001.mp3" or "1.mp3")
                try:
                    surah_number = int(filename.split(".")[0])
                    if validate_surah_number(surah_number):
                        surah_display = get_surah_display(surah_number, "detailed")
                        now_playing = format_now_playing(surah_number, "Saad Al Ghamdi")

                        log_progress(i, len(audio_files))
                        log_tree_branch("surah", surah_display)
                        log_tree_final("progress", f"{i}/{len(audio_files)}")

                        # Log the beautiful now playing format
                        log_section_start("Now Playing", "🎵")
                        for line in now_playing.split("\n"):
                            if line.strip():
                                log_tree_branch("info", line.strip())

                        # Start Rich Presence tracking
                        if rich_presence:
                            await rich_presence.start_track(
                                surah_number, audio_file, "Saad Al Ghamdi"
                            )

                    else:
                        # Fallback to filename if not a valid Surah number
                        log_progress(i, len(audio_files))
                        log_tree_branch("file", filename)
                        log_tree_final("progress", f"{i}/{len(audio_files)}")

                except (ValueError, IndexError):
                    # Fallback to filename if we can't extract Surah number
                    log_progress(i, len(audio_files))
                    log_tree_branch("file", filename)
                    log_tree_final("progress", f"{i}/{len(audio_files)}")

                # Create FFmpeg audio source
                source = discord.FFmpegPCMAudio(
                    audio_file, executable=FFMPEG_PATH, options="-vn"
                )

                # Play the audio
                voice_client.play(source)

                # Wait for playback to finish
                while voice_client.is_playing():
                    await asyncio.sleep(1)

                # Stop Rich Presence for this track
                if rich_presence:
                    await rich_presence.stop_track()

            except Exception as e:
                log_error_with_traceback(f"Error playing {filename}", e)
                # Stop Rich Presence on error
                if rich_presence:
                    await rich_presence.stop_track()
                continue

        log_tree_end("Finished playing all audio files", "SUCCESS")

    except Exception as e:
        log_async_error("play_audio", e, f"Audio folder: {AUDIO_FOLDER}")
        # Stop Rich Presence on error
        if rich_presence:
            await rich_presence.stop_track()


# =============================================================================
# Voice State Event Handlers
# =============================================================================
@bot.event
async def on_voice_state_update(member, before, after):
    """
    Handle voice state changes with intelligent reconnection logic.

    Monitors voice state changes and implements smart reconnection when the bot
    is disconnected from voice channels. Includes loop prevention and graceful
    error handling to maintain stable voice connections.

    Features:
    - Detects bot disconnection from voice channels
    - Implements delay to prevent rapid reconnection loops
    - Automatically restarts audio playback after reconnection
    - Comprehensive logging for troubleshooting connection issues

    Args:
        member: Discord member whose voice state changed
        before: Previous voice state
        after: New voice state
    """
    global rich_presence, audio_manager

    try:
        # Only handle bot's own voice state changes
        if member != bot.user:
            return

        # Detect disconnection (was in channel, now not in channel)
        if before.channel and not after.channel:
            log_section_start("Bot Disconnected", "⚠️")
            log_tree_branch("member", member.display_name)
            log_tree_branch(
                "before_channel", before.channel.name if before.channel else "None"
            )
            log_tree_final(
                "after_channel", after.channel.name if after.channel else "None"
            )

            # Stop AudioManager when disconnected to prevent resource leaks
            if audio_manager:
                try:
                    await audio_manager.stop_playback()
                    log_tree_branch("audio_cleanup", "✅ Audio playback stopped")
                except Exception as e:
                    log_error_with_traceback("Error stopping audio playback", e)

            # Smart reconnection with delay to prevent loops
            guild = before.channel.guild
            channel = before.channel

            # Add delay to prevent rapid reconnection attempts
            log_tree_branch("reconnection", "Waiting 5 seconds before reconnection")
            await asyncio.sleep(5)

            try:
                log_tree_branch("reconnection", "Attempting reconnect after disconnect")
                voice_client = await channel.connect(reconnect=False, timeout=60)

                if audio_manager:
                    audio_manager.set_voice_client(voice_client)
                    await audio_manager.start_playback()

                log_tree_final("reconnect", f"✅ Reconnected to {channel.name}")

            except discord.errors.ClientException as e:
                if "already connected" in str(e).lower():
                    log_tree_branch("reconnect_info", "Already connected to voice")
                else:
                    log_error_with_traceback(
                        "Discord client error during reconnection", e
                    )
                    log_tree_final("reconnect_status", "❌ Reconnection failed")

            except asyncio.TimeoutError:
                log_error_with_traceback(
                    "Reconnection timeout", TimeoutError("Connection timeout")
                )
                log_tree_final("reconnect_status", "❌ Reconnection timed out")

            except Exception as e:
                log_error_with_traceback("Reconnection failed", e)
                log_tree_final("reconnect_status", "❌ Will retry on next disconnect")

        # Handle channel switches (moved from one channel to another)
        elif before.channel and after.channel and before.channel != after.channel:
            log_tree_branch(
                "channel_switch",
                f"Moved from {before.channel.name} to {after.channel.name}",
            )

            # Update audio manager with new voice client if needed
            if audio_manager and hasattr(after.channel.guild, "voice_client"):
                voice_client = after.channel.guild.voice_client
                if voice_client:
                    audio_manager.set_voice_client(voice_client)

    except Exception as e:
        log_discord_error("on_voice_state_update", e, GUILD_ID)


# =============================================================================
# Discord Error Event Handlers
# =============================================================================
@bot.event
async def on_error(event, *args, **kwargs):
    """
    Handle Discord errors with comprehensive error categorization and recovery.

    Provides centralized error handling for all Discord events with specific
    handling for common error types and automatic recovery mechanisms where
    possible.

    Features:
    - Specific handling for voice connection errors (4006, 4014, etc.)
    - Automatic reconnection for recoverable errors
    - Detailed error logging with context information
    - Graceful degradation for non-critical errors

    Args:
        event: Name of the Discord event that caused the error
        *args: Event arguments
        **kwargs: Event keyword arguments
    """
    try:
        # Get the current exception information
        exc_type, exc_value, exc_traceback = sys.exc_info()

        if exc_value:
            # =============================================================================
            # Voice Connection Error Handling
            # =============================================================================
            if isinstance(exc_value, discord.errors.ConnectionClosed):
                await _handle_voice_connection_error(exc_value, event, kwargs)

            # =============================================================================
            # HTTP Error Handling
            # =============================================================================
            elif isinstance(exc_value, discord.errors.HTTPException):
                await _handle_http_error(exc_value, event, kwargs)

            # =============================================================================
            # Generic Error Handling
            # =============================================================================
            else:
                log_discord_error(
                    f"discord_event_{event}",
                    exc_value,
                    kwargs.get("guild_id"),
                    kwargs.get("channel_id"),
                )
        else:
            log_error_with_traceback(f"Unknown error in Discord event: {event}")

    except Exception as e:
        log_critical_error("Error in error handler", e)


async def _handle_voice_connection_error(exc_value, event, kwargs):
    """
    Handle voice connection specific errors with appropriate recovery actions.

    Args:
        exc_value: The ConnectionClosed exception
        event: Event name that caused the error
        kwargs: Event context information
    """
    global audio_manager

    try:
        error_code = getattr(exc_value, "code", None)

        if error_code == 4006:
            # Voice server not responding
            log_critical_error(
                "Voice server not responding (4006). Attempting reconnect."
            )
            await _attempt_voice_reconnection("Voice server error 4006")

        elif error_code == 4014:
            # Disconnected from voice channel
            log_tree_branch("voice_error", "Disconnected from voice channel (4014)")
            await _attempt_voice_reconnection("Voice disconnection 4014")

        else:
            # Other connection errors
            log_error_with_traceback(f"Voice connection error {error_code}", exc_value)

    except Exception as e:
        log_error_with_traceback("Error handling voice connection error", e)


async def _handle_http_error(exc_value, event, kwargs):
    """
    Handle HTTP errors from Discord API with appropriate responses.

    Args:
        exc_value: The HTTPException
        event: Event name that caused the error
        kwargs: Event context information
    """
    try:
        status_code = getattr(exc_value, "status", None)

        if status_code == 429:
            # Rate limiting
            log_tree_branch("rate_limit", "Discord API rate limit encountered")
            retry_after = getattr(exc_value, "retry_after", 60)
            log_tree_branch("rate_limit_wait", f"Waiting {retry_after} seconds")

        elif status_code == 403:
            # Forbidden - permissions issue
            log_tree_branch("permissions_error", "Bot lacks required permissions")

        elif status_code == 404:
            # Not found - channel/guild may have been deleted
            log_tree_branch("not_found", "Discord resource not found (deleted?)")

        else:
            # Other HTTP errors
            log_error_with_traceback(f"Discord HTTP error {status_code}", exc_value)

    except Exception as e:
        log_error_with_traceback("Error handling HTTP error", e)


async def _attempt_voice_reconnection(reason):
    """
    Attempt to reconnect to voice channel with error recovery.

    Args:
        reason: Reason for reconnection attempt
    """
    global audio_manager

    try:
        guild = bot.get_guild(GUILD_ID)
        if guild:
            channel = guild.get_channel(TARGET_CHANNEL_ID)
            if channel:
                log_tree_branch("reconnect_attempt", f"Reconnecting due to: {reason}")
                voice_client = await channel.connect(reconnect=False, timeout=30)

                if audio_manager:
                    audio_manager.set_voice_client(voice_client)
                    await audio_manager.start_playback()

                log_tree_final("reconnect", f"✅ Reconnected to {channel.name}")

    except Exception as reconnect_error:
        log_error_with_traceback(f"Reconnection failed after {reason}", reconnect_error)


@bot.event
async def on_disconnect():
    """
    Handle Discord disconnection with proper cleanup and state management.

    Performs cleanup operations when the bot disconnects from Discord,
    including stopping audio playback and updating state management
    for session tracking.
    """
    global rich_presence, audio_manager

    try:
        log_section_start("Discord Disconnection", "⚠️")
        log_tree_branch("event", "on_disconnect")
        log_tree_final("status", "Bot disconnected from Discord")

        # Stop AudioManager when disconnected to prevent resource leaks
        if audio_manager:
            try:
                await audio_manager.stop_playback()
                log_tree_branch("audio_cleanup", "✅ Audio playback stopped")
            except Exception as e:
                log_error_with_traceback("Error stopping audio during disconnect", e)

        # Mark shutdown in state manager for session tracking
        try:
            state_manager.mark_shutdown()
            log_tree_branch("state_update", "✅ Shutdown recorded in state manager")
        except Exception as e:
            log_error_with_traceback("Error updating state manager", e)

    except Exception as e:
        log_error_with_traceback("Error handling disconnect event", e)


@bot.event
async def on_resumed():
    """
    Handle Discord reconnection after temporary disconnection.

    Logs the reconnection event and performs any necessary reinitialization
    of bot services after a temporary disconnection.
    """
    try:
        log_section_start("Discord Reconnection", "🔄")
        log_tree_branch("event", "on_resumed")
        log_tree_final("status", "Bot reconnected to Discord")

        # Verify voice connection is still active
        if audio_manager and hasattr(bot, "voice_clients"):
            voice_clients = bot.voice_clients
            if voice_clients:
                log_tree_branch(
                    "voice_status", f"Voice connections: {len(voice_clients)}"
                )
            else:
                log_tree_branch("voice_status", "No active voice connections")

    except Exception as e:
        log_error_with_traceback("Error handling resume event", e)


@bot.event
async def on_command_error(ctx, error):
    """
    Handle command errors with detailed logging (slash commands only).

    Since prefix commands are disabled, this handler primarily deals with
    slash command errors and provides appropriate logging.

    Args:
        ctx: Command context
        error: Command error that occurred
    """
    try:
        # Skip logging for CommandNotFound since we don't use prefix commands
        if isinstance(error, commands.CommandNotFound):
            return

        # Log the error with context information
        log_discord_error(
            "command_error",
            error,
            ctx.guild.id if ctx.guild else None,
            ctx.channel.id if ctx.channel else None,
        )

        # Add command-specific context
        log_tree_branch("command", ctx.command.name if ctx.command else "Unknown")
        log_tree_branch("user", str(ctx.author))
        log_tree_branch(
            "command_type",
            "slash_command" if hasattr(ctx, "interaction") else "legacy_command",
        )
        log_tree_final("error_type", type(error).__name__)

    except Exception as e:
        log_critical_error("Error in command error handler", e)


@bot.event
async def on_guild_unavailable(guild):
    """
    Handle guild becoming unavailable due to Discord outages.

    Logs when a guild becomes unavailable, typically due to Discord
    server issues or network problems.

    Args:
        guild: Guild that became unavailable
    """
    try:
        log_section_start("Guild Unavailable", "⚠️")
        log_tree_branch("guild_id", guild.id)
        log_tree_branch("guild_name", guild.name)
        log_tree_final("status", "Guild became unavailable")

        # Check if this is our target guild
        if guild.id == GUILD_ID:
            log_tree_branch("target_guild", "⚠️ Target guild is unavailable")

    except Exception as e:
        log_error_with_traceback("Error handling guild unavailable event", e)


@bot.event
async def on_guild_available(guild):
    """
    Handle guild becoming available again after being unavailable.

    Logs when a guild becomes available again and performs any necessary
    reinitialization if it's our target guild.

    Args:
        guild: Guild that became available
    """
    try:
        log_section_start("Guild Available", "✅")
        log_tree_branch("guild_id", guild.id)
        log_tree_branch("guild_name", guild.name)
        log_tree_final("status", "Guild became available")

        # Check if this is our target guild
        if guild.id == GUILD_ID:
            log_tree_branch("target_guild", "✅ Target guild is now available")

            # Verify voice channel is still accessible
            channel = guild.get_channel(TARGET_CHANNEL_ID)
            if channel:
                log_tree_branch(
                    "target_channel",
                    f"✅ Target channel '{channel.name}' is accessible",
                )
            else:
                log_tree_branch("target_channel", "⚠️ Target channel is not accessible")

    except Exception as e:
        log_error_with_traceback("Error handling guild available event", e)


# =============================================================================
# Bot Export for Main Entry Point
# =============================================================================
# This module exports the bot configuration and instance for use by main.py
