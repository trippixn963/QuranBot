# =============================================================================
# QuranBot - Minimal Discord Audio Bot
# =============================================================================
# Simple Discord bot that connects to voice channels and plays Quran audio
# =============================================================================

import discord
from discord.ext import commands
import os
import asyncio
import glob
from pathlib import Path

# =============================================================================
# Environment Configuration
# =============================================================================
from dotenv import load_dotenv
load_dotenv()

# =============================================================================
# Import Tree Logging Functions
# =============================================================================
import sys
import os
# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.tree_log import (
    log_tree, log_tree_end, log_tree_branch, log_tree_final,
    log_section_start, log_progress, log_status
)

# =============================================================================
# Discord Logging Configuration
# =============================================================================
import logging

class DiscordTreeHandler(logging.Handler):
    """Custom logging handler that formats Discord logs in tree style"""
    
    def emit(self, record):
        """Handle a log record by formatting it in tree style"""
        try:
            # Get the log message
            message = self.format(record)
            
            # Skip certain verbose messages
            if any(skip in message.lower() for skip in [
                'keeping websocket alive',
                'sending heartbeat',
                'received heartbeat',
                'heartbeat acknowledged'
            ]):
                return
            
            # Map Discord log levels to tree logging
            level_name = record.levelname
            logger_name = record.name
            
            # Import the file logging function
            from utils.tree_log import write_to_log_files
            
            # Format based on the Discord module
            if 'voice_state' in logger_name:
                if 'connecting' in message.lower():
                    log_tree_branch("voice_status", "🔄 Connecting to voice...")
                    write_to_log_files(f"Discord Voice: Connecting to voice - {message}", level_name, "discord_voice")
                elif 'handshake' in message.lower():
                    log_tree_branch("voice_handshake", "🤝 Voice handshake in progress")
                    write_to_log_files(f"Discord Voice: Handshake in progress - {message}", level_name, "discord_voice")
                elif 'connection complete' in message.lower():
                    log_tree_branch("voice_result", "✅ Voice connection established")
                    write_to_log_files(f"Discord Voice: Connection established - {message}", level_name, "discord_voice")
                elif 'disconnected' in message.lower():
                    log_tree_branch("voice_status", "⚠️ Voice disconnected - reconnecting...")
                    write_to_log_files(f"Discord Voice: Disconnected - {message}", "WARNING", "discord_voice")
                elif 'terminated' in message.lower():
                    log_tree_branch("voice_cleanup", "🧹 Voice connection terminated")
                    write_to_log_files(f"Discord Voice: Connection terminated - {message}", level_name, "discord_voice")
                else:
                    log_tree_branch("voice_info", f"🎵 {message}")
                    write_to_log_files(f"Discord Voice: {message}", level_name, "discord_voice")
            
            elif 'gateway' in logger_name:
                if 'connected' in message.lower():
                    log_tree_branch("discord_gateway", "✅ Connected to Discord Gateway")
                    write_to_log_files(f"Discord Gateway: Connected - {message}", level_name, "discord_gateway")
                elif 'session' in message.lower():
                    log_tree_branch("discord_session", "🔑 Discord session established")
                    write_to_log_files(f"Discord Gateway: Session established - {message}", level_name, "discord_gateway")
                else:
                    log_tree_branch("discord_info", f"📡 {message}")
                    write_to_log_files(f"Discord Gateway: {message}", level_name, "discord_gateway")
            
            elif 'client' in logger_name:
                if 'logging in' in message.lower():
                    log_tree_branch("discord_auth", "🔐 Authenticating with Discord...")
                    write_to_log_files(f"Discord Client: Authenticating - {message}", level_name, "discord_client")
                else:
                    log_tree_branch("discord_client", f"🤖 {message}")
                    write_to_log_files(f"Discord Client: {message}", level_name, "discord_client")
            
            elif 'player' in logger_name:
                if 'ffmpeg' in message.lower():
                    if 'terminated' in message.lower():
                        log_tree_branch("audio_status", "🎵 Audio track completed")
                        write_to_log_files(f"Discord Player: Audio track completed - {message}", level_name, "discord_player")
                    else:
                        log_tree_branch("audio_ffmpeg", f"🎧 {message}")
                        write_to_log_files(f"Discord Player: FFmpeg - {message}", level_name, "discord_player")
                else:
                    log_tree_branch("audio_player", f"🎵 {message}")
                    write_to_log_files(f"Discord Player: {message}", level_name, "discord_player")
            
            else:
                # Generic Discord log
                icon = "🔧" if level_name == "DEBUG" else "ℹ️" if level_name == "INFO" else "⚠️"
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
        'discord',
        'discord.client',
        'discord.gateway',
        'discord.voice_state',
        'discord.player'
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

bot = commands.Bot(command_prefix='!', intents=intents)

# =============================================================================
# Bot Version & Configuration
# =============================================================================
BOT_VERSION = "1.1.0"
BOT_NAME = "QuranBot"

# Configuration from Environment Variables
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
TARGET_CHANNEL_ID = int(os.getenv('TARGET_CHANNEL_ID') or '0')
GUILD_ID = int(os.getenv('GUILD_ID') or '0')
FFMPEG_PATH = os.getenv('FFMPEG_PATH', 'ffmpeg')
AUDIO_FOLDER = 'audio/Saad Al Ghamdi'

# =============================================================================
# Discord Bot Events
# =============================================================================
@bot.event
async def on_ready():
    log_section_start(f"{BOT_NAME} v{BOT_VERSION} Started")
    log_tree_branch("bot_user", f"{bot.user}")
    log_tree_branch("version", BOT_VERSION)
    log_tree_branch("guild_id", GUILD_ID)
    log_tree_final("target_channel_id", TARGET_CHANNEL_ID)
    
    # Get the guild and voice channel
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        log_tree_end(f"Guild with ID {GUILD_ID} not found", "ERROR")
        return
        
    channel = guild.get_channel(TARGET_CHANNEL_ID)
    if not channel:
        log_tree_end(f"Channel with ID {TARGET_CHANNEL_ID} not found", "ERROR")
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
        log_tree_end(f"Voice connection failed: {e}", "ERROR")

# =============================================================================
# Audio Playback Functions
# =============================================================================
async def play_audio(voice_client):
    """Play audio files from the audio folder"""
    
    log_section_start("Audio Playback Started", "🎵")
    log_tree_branch("audio_folder", AUDIO_FOLDER)
    log_tree_final("ffmpeg_path", FFMPEG_PATH)
    
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
        if not voice_client.is_connected():
            log_tree_end("Voice client disconnected, stopping playback", "WARNING")
            break
            
        filename = os.path.basename(audio_file)
        log_progress(i, len(audio_files))
        log_tree_branch("file", filename)
        log_tree_final("progress", f"{i}/{len(audio_files)}")
        
        try:
            # Create FFmpeg audio source
            source = discord.FFmpegPCMAudio(
                audio_file,
                executable=FFMPEG_PATH,
                options='-vn'
            )
            
            # Play the audio
            voice_client.play(source)
            
            # Wait for playback to finish
            while voice_client.is_playing():
                await asyncio.sleep(1)
                
        except Exception as e:
            log_tree_end(f"Error playing {filename}: {e}", "ERROR")
            continue
    
    log_tree_end("Finished playing all audio files", "SUCCESS")

# =============================================================================
# Voice State Event Handlers
# =============================================================================
@bot.event
async def on_voice_state_update(member, before, after):
    """Handle voice state changes"""
    # If bot gets disconnected, try to reconnect
    if member == bot.user and before.channel and not after.channel:
        log_section_start("Bot Disconnected - Attempting Reconnection", "🔄")
        log_tree_branch("member", member.display_name)
        log_tree_branch("before_channel", before.channel.name if before.channel else "None")
        log_tree_final("after_channel", after.channel.name if after.channel else "None")
        
        guild = bot.get_guild(GUILD_ID)
        channel = guild.get_channel(TARGET_CHANNEL_ID)
        if channel:
            try:
                log_tree("Attempting reconnection", "RETRY")
                voice_client = await channel.connect()
                log_tree("Reconnection successful", "SUCCESS")
                await play_audio(voice_client)
            except Exception as e:
                log_tree_end(f"Reconnection failed: {e}", "ERROR")

# =============================================================================
# Bot Export for Main Entry Point
# =============================================================================
# This module exports the bot configuration and instance for use by main.py 