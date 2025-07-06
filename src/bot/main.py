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
    """Custom logging handler that formats Discord logs in tree style"""

    def emit(self, record):
        """Handle a log record by formatting it in tree style"""
        try:
            # Get the log message
            message = self.format(record)

            # Skip certain verbose messages
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

            # Import the file logging function
            from utils.tree_log import write_to_log_files

            # Format based on the Discord module
            if "voice_state" in logger_name:
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
                    log_tree_branch(
                        "voice_status", "⚠️ Voice disconnected - reconnecting..."
                    )
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
                    write_to_log_files(
                        f"Discord Voice: {message}", level_name, "discord_voice"
                    )

            elif "gateway" in logger_name:
                if "connected" in message.lower():
                    log_tree_branch(
                        "discord_gateway", "✅ Connected to Discord Gateway"
                    )
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

            elif "client" in logger_name:
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

            elif "player" in logger_name:
                if "ffmpeg" in message.lower():
                    if "terminated" in message.lower():
                        log_tree_branch("audio_status", "🎵 Audio track completed")
                        write_to_log_files(
                            f"Discord Player: Audio track completed - {message}",
                            level_name,
                            "discord_player",
                        )
                    else:
                        log_tree_branch("audio_ffmpeg", f"🎧 {message}")
                        write_to_log_files(
                            f"Discord Player: FFmpeg - {message}",
                            level_name,
                            "discord_player",
                        )
                else:
                    log_tree_branch("audio_player", f"🎵 {message}")
                    write_to_log_files(
                        f"Discord Player: {message}", level_name, "discord_player"
                    )

            else:
                # Generic Discord log
                icon = (
                    "🔧"
                    if level_name == "DEBUG"
                    else "ℹ️" if level_name == "INFO" else "⚠️"
                )
                log_tree_branch("discord_log", f"{icon} {message}")
                write_to_log_files(f"Discord: {message}", level_name, "discord_general")

        except Exception:
            # If there's an error in our custom handler, don't crash
            pass


# Configure Discord logging
def setup_discord_logging():
    """Configure Discord loggers to use our tree-style formatting"""

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

        # Remove existing handlers
        logger.handlers.clear()

        # Add our tree handler
        logger.addHandler(tree_handler)

        # Prevent propagation to avoid duplicate logs
        logger.propagate = False


# Initialize Discord logging
setup_discord_logging()

# =============================================================================
# Bot Setup & Configuration
# =============================================================================
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =============================================================================
# Bot Version & Configuration
# =============================================================================
BOT_VERSION = "1.5.0"
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
    """Validate bot configuration and environment variables"""
    log_section_start("Configuration Validation", "🔧")

    errors = []
    warnings = []

    # Check Discord token
    if not DISCORD_TOKEN:
        errors.append("DISCORD_TOKEN is missing from environment variables")
    elif len(DISCORD_TOKEN) < 50:
        warnings.append("DISCORD_TOKEN appears to be invalid (too short)")

    # Check Guild ID
    if GUILD_ID == 0:
        errors.append("GUILD_ID is missing or invalid in environment variables")

    # Check Channel ID
    if TARGET_CHANNEL_ID == 0:
        errors.append(
            "TARGET_CHANNEL_ID is missing or invalid in environment variables"
        )

    # Check Panel Channel ID
    if PANEL_CHANNEL_ID == 0:
        warnings.append(
            "PANEL_CHANNEL_ID is missing - control panel will not be created"
        )

    # Check audio folder
    if not os.path.exists(AUDIO_FOLDER):
        warnings.append(f"Audio folder '{AUDIO_FOLDER}' does not exist")

    # Check FFmpeg
    try:
        import subprocess

        subprocess.run([FFMPEG_PATH, "-version"], capture_output=True, check=True)
        log_tree_branch("ffmpeg_check", "✅ FFmpeg is accessible")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        warnings.append(
            f"FFmpeg not found at '{FFMPEG_PATH}' - audio playback may fail"
        )
    except Exception as e:
        log_error_with_traceback("Error checking FFmpeg availability", e)

    # Validate Rich Presence dependencies
    rp_validation = validate_rich_presence_dependencies(FFMPEG_PATH)
    warnings.extend(rp_validation["warnings"])

    # Report results
    if errors:
        for error in errors:
            log_tree_branch("config_error", f"❌ {error}")
        log_tree_final("validation_result", "❌ Configuration validation failed")
        return False

    if warnings:
        for warning in warnings:
            log_tree_branch("config_warning", f"⚠️ {warning}")

    log_tree_final("validation_result", "✅ Configuration validation passed")
    return True


# =============================================================================
# Discord Bot Events
# =============================================================================
@bot.event
async def on_ready():
    global rich_presence, audio_manager

    try:
        # Mark startup in state manager
        state_manager.mark_startup()

        log_section_start(f"{BOT_NAME} v{BOT_VERSION} Started")
        log_tree_branch("bot_user", f"{bot.user}")
        log_tree_branch("version", BOT_VERSION)
        log_tree_branch("guild_id", GUILD_ID)
        log_tree_final("target_channel_id", TARGET_CHANNEL_ID)

        # Initialize Rich Presence Manager
        log_spacing()
        rich_presence = RichPresenceManager(bot, FFMPEG_PATH)
        log_tree_branch("rich_presence", "✅ Rich Presence Manager initialized")

        # Initialize Audio Manager with environment defaults
        audio_manager = AudioManager(
            bot,
            FFMPEG_PATH,
            default_reciter=DEFAULT_RECITER,
            default_shuffle=DEFAULT_SHUFFLE,
            default_loop=DEFAULT_LOOP,
        )
        audio_manager.set_rich_presence(rich_presence)
        log_tree_branch("audio_manager", "✅ Audio Manager initialized")

        # Validate configuration before proceeding
        log_spacing()
        if not validate_configuration():
            log_critical_error("Bot configuration validation failed")
            await bot.close()
            return

        # Get the guild and voice channel
        guild = bot.get_guild(GUILD_ID)
        if not guild:
            log_critical_error(f"Guild with ID {GUILD_ID} not found")
            return

        channel = guild.get_channel(TARGET_CHANNEL_ID)
        if not channel:
            log_critical_error(f"Channel with ID {TARGET_CHANNEL_ID} not found")
            return

        log_spacing()
        log_tree("Attempting voice connection")
        log_tree_branch("channel_name", channel.name)
        log_tree_final("channel_id", channel.id)

        # Connect to voice channel with retry logic
        max_retries = 3
        retry_delay = 10  # Longer delay to prevent rapid connection attempts

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

                # Set up AudioManager with voice client
                audio_manager.set_voice_client(voice_client)

                # Set up control panel with AudioManager
                if PANEL_CHANNEL_ID != 0:
                    try:
                        await setup_control_panel(bot, PANEL_CHANNEL_ID, audio_manager)
                        log_tree_branch(
                            "control_panel", "✅ Control panel setup successful"
                        )
                    except Exception as e:
                        log_error_with_traceback("Error setting up control panel", e)

                # Start playing audio using AudioManager
                await audio_manager.start_playback()
                break  # Success, exit retry loop

            except Exception as e:
                log_tree_branch(
                    "connection_error",
                    f"Attempt {attempt + 1} failed: {type(e).__name__}",
                )
                if attempt < max_retries - 1:
                    log_tree_branch(
                        "retry", f"Waiting {retry_delay} seconds before retry"
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    log_discord_error("on_ready", e, GUILD_ID, TARGET_CHANNEL_ID)
                    log_tree_final(
                        "connection_status", "❌ All connection attempts failed"
                    )
                    return

    except Exception as e:
        log_critical_error("Fatal error in on_ready event", e)


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
    """Handle voice state changes - Smart reconnection with loop prevention"""
    global rich_presence, audio_manager

    try:
        # Attempt reconnection when disconnected
        if member == bot.user and before.channel and not after.channel:
            log_section_start("Bot Disconnected", "⚠️")
            log_tree_branch("member", member.display_name)
            log_tree_branch(
                "before_channel", before.channel.name if before.channel else "None"
            )
            log_tree_final(
                "after_channel", after.channel.name if after.channel else "None"
            )

            # Stop AudioManager when disconnected
            if audio_manager:
                await audio_manager.stop_playback()

            # Smart reconnection with delay to prevent loops
            guild = before.channel.guild
            channel = before.channel

            # Add delay to prevent rapid reconnection attempts
            log_tree_branch("reconnection", "Waiting 5 seconds before reconnection")
            await asyncio.sleep(5)

            try:
                log_tree_branch("reconnection", "Attempting reconnect after disconnect")
                voice_client = await channel.connect(reconnect=False, timeout=60)
                audio_manager.set_voice_client(voice_client)
                await audio_manager.start_playback()
                log_tree_final("reconnect", f"✅ Reconnected to {channel.name}")
            except Exception as e:
                log_error_with_traceback("Reconnection failed", e)
                log_tree_final("reconnect_status", "❌ Will retry on next disconnect")

    except Exception as e:
        log_discord_error("on_voice_state_update", e, GUILD_ID)


# =============================================================================
# Discord Error Event Handlers
# =============================================================================
@bot.event
async def on_error(event, *args, **kwargs):
    """Handle Discord errors"""
    try:
        # Get the current exception
        exc_type, exc_value, exc_traceback = sys.exc_info()

        if exc_value:
            # Specific handling for voice connection error 4006
            if isinstance(exc_value, discord.errors.ConnectionClosed):
                if exc_value.code == 4006:
                    log_critical_error(
                        "Voice server not responding (4006). Attempting reconnect."
                    )
                    try:
                        guild = bot.get_guild(GUILD_ID)
                        if guild:
                            channel = guild.get_channel(TARGET_CHANNEL_ID)
                            if channel:
                                voice_client = await channel.connect(
                                    reconnect=False, timeout=30
                                )
                                audio_manager.set_voice_client(voice_client)
                                await audio_manager.start_playback()
                                log_tree_final(
                                    "reconnect", f"✅ Reconnected to {channel.name}"
                                )
                    except Exception as reconnect_error:
                        log_error_with_traceback(
                            "Reconnection after 4006 failed", reconnect_error
                        )
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


@bot.event
async def on_disconnect():
    """Handle Discord disconnection"""
    global rich_presence, audio_manager

    try:
        log_section_start("Discord Disconnection", "⚠️")
        log_tree_branch("event", "on_disconnect")
        log_tree_final("status", "Bot disconnected from Discord")

        # Stop AudioManager when disconnected
        if audio_manager:
            await audio_manager.stop_playback()

        # Mark shutdown in state manager
        state_manager.mark_shutdown()

    except Exception as e:
        log_error_with_traceback("Error handling disconnect event", e)


@bot.event
async def on_resumed():
    """Handle Discord reconnection"""
    try:
        log_section_start("Discord Reconnection", "🔄")
        log_tree_branch("event", "on_resumed")
        log_tree_final("status", "Bot reconnected to Discord")
    except Exception as e:
        log_error_with_traceback("Error handling resume event", e)


@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    try:
        log_discord_error(
            "command_error",
            error,
            ctx.guild.id if ctx.guild else None,
            ctx.channel.id if ctx.channel else None,
        )
    except Exception as e:
        log_critical_error("Error in command error handler", e)


@bot.event
async def on_guild_unavailable(guild):
    """Handle guild becoming unavailable"""
    try:
        log_section_start("Guild Unavailable", "⚠️")
        log_tree_branch("guild_id", guild.id)
        log_tree_branch("guild_name", guild.name)
        log_tree_final("status", "Guild became unavailable")
    except Exception as e:
        log_error_with_traceback("Error handling guild unavailable event", e)


@bot.event
async def on_guild_available(guild):
    """Handle guild becoming available again"""
    try:
        log_section_start("Guild Available", "✅")
        log_tree_branch("guild_id", guild.id)
        log_tree_branch("guild_name", guild.name)
        log_tree_final("status", "Guild became available")
    except Exception as e:
        log_error_with_traceback("Error handling guild available event", e)


# =============================================================================
# Bot Export for Main Entry Point
# =============================================================================
# This module exports the bot configuration and instance for use by main.py
