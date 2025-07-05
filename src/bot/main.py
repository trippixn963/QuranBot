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

load_dotenv()

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

from utils.tree_log import (
    log_async_error,
    log_critical_error,
    log_discord_error,
    log_error_with_traceback,
    log_progress,
    log_section_start,
    log_status,
    log_tree,
    log_tree_branch,
    log_tree_end,
    log_tree_final,
    log_warning_with_context,
)


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
BOT_VERSION = "1.2.0"
BOT_NAME = "QuranBot"

# Configuration from Environment Variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID") or "0")
GUILD_ID = int(os.getenv("GUILD_ID") or "0")
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")
AUDIO_FOLDER = "audio/Saad Al Ghamdi"


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
    try:
        log_section_start(f"{BOT_NAME} v{BOT_VERSION} Started")
        log_tree_branch("bot_user", f"{bot.user}")
        log_tree_branch("version", BOT_VERSION)
        log_tree_branch("guild_id", GUILD_ID)
        log_tree_final("target_channel_id", TARGET_CHANNEL_ID)

        # Validate configuration before proceeding
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

        log_tree("Attempting voice connection")
        log_tree_branch("channel_name", channel.name)
        log_tree_final("channel_id", channel.id)

        # Connect to voice channel
        try:
            voice_client = await channel.connect()
            log_tree("Voice connection successful", "SUCCESS")
            log_tree_final("connected_to", channel.name)

            # Start playing audio
            await play_audio(voice_client)

        except Exception as e:
            log_discord_error("on_ready", e, GUILD_ID, TARGET_CHANNEL_ID)

    except Exception as e:
        log_critical_error("Fatal error in on_ready event", e)


# =============================================================================
# Audio Playback Functions
# =============================================================================
async def play_audio(voice_client):
    """Play audio files from the audio folder"""

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

            except Exception as e:
                log_error_with_traceback(f"Error playing {filename}", e)
                continue

        log_tree_end("Finished playing all audio files", "SUCCESS")

    except Exception as e:
        log_async_error("play_audio", e, f"Audio folder: {AUDIO_FOLDER}")


# =============================================================================
# Voice State Event Handlers
# =============================================================================
@bot.event
async def on_voice_state_update(member, before, after):
    """Handle voice state changes"""
    try:
        # If bot gets disconnected, try to reconnect
        if member == bot.user and before.channel and not after.channel:
            log_section_start("Bot Disconnected - Attempting Reconnection", "🔄")
            log_tree_branch("member", member.display_name)
            log_tree_branch(
                "before_channel", before.channel.name if before.channel else "None"
            )
            log_tree_final(
                "after_channel", after.channel.name if after.channel else "None"
            )

            guild = bot.get_guild(GUILD_ID)
            channel = guild.get_channel(TARGET_CHANNEL_ID)
            if channel:
                try:
                    log_tree("Attempting reconnection", "RETRY")
                    voice_client = await channel.connect()
                    log_tree("Reconnection successful", "SUCCESS")
                    await play_audio(voice_client)
                except Exception as e:
                    log_discord_error(
                        "voice_reconnection", e, GUILD_ID, TARGET_CHANNEL_ID
                    )
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
    try:
        log_section_start("Discord Disconnection", "⚠️")
        log_tree_branch("event", "on_disconnect")
        log_tree_final("status", "Bot disconnected from Discord")
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
