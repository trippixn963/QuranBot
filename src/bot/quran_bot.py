"""
Main Discord Quran Bot implementation.
Professional 24/7 Quran streaming bot with local audio support.
"""

import discord
import asyncio
import os
import sys
import tempfile
import subprocess
from datetime import datetime
from typing import Optional, Dict
import time
import itertools
import signal
import logging
import traceback
import json

# Add src to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config.config import Config
from monitoring.logging.tree_log import tree_log
from monitoring.health.health import HealthMonitor
from monitoring.health.health_reporter import HealthReporter
from monitoring.logging.discord_logger import DiscordEmbedLogger
from core.state.state_manager import StateManager
from core.mapping.surah_mapper import get_surah_from_filename, get_surah_emoji, get_surah_display_name
from monitoring.logging.log_helpers import log_async_function_call, log_function_call, log_operation, get_system_metrics, get_discord_context, get_bot_state
from monitoring.logging.logger import log_error, log_performance, log_bot_startup, log_discord_event, log_state_load, log_connection_attempt, log_connection_success

class QuranBot(discord.Client):
    """Professional Discord bot for 24/7 Quran streaming."""
    
    def __init__(self):
        """Initialize the QuranBot with enhanced error handling and monitoring."""
        # Initialize base client with all intents
        intents = discord.Intents.all()
        super().__init__(intents=intents)
        
        # Bot state
        self.start_time = datetime.now()  # Track when the bot starts
        self.is_streaming = False
        self.loop_enabled = False
        self.shuffle_enabled = False
        self.current_audio_file = None
        self.current_reciter = None
        self._voice_clients = {}
        self._was_streaming_before_disconnect = False
        self.connection_failures = 0
        self.max_connection_failures = 5  # Maximum number of consecutive failures before giving up
        self.playback_start_time = None
        
        # Initialize command tree for slash commands
        self.tree = discord.app_commands.CommandTree(self)
        
        # Initialize bot state
        self.current_song_index = 0
        self._intended_streaming = False  # Track if we want to be streaming
        self.original_playlist = []  # Store original order for shuffle
        
        # Connection management
        self.connection_failures = 0
        self.max_connection_failures = 5
        
        # Initialize components
        self.health_monitor = HealthMonitor()  # Initialize immediately
        self.discord_logger = DiscordEmbedLogger(
            self, 
            Config.LOGS_CHANNEL_ID,  # Use channel ID from config
            Config.TARGET_CHANNEL_ID  # Use target VC ID from config
        )
        self.state_manager = StateManager("bot_state.json")  # Initialize immediately
        
        # Health checks tracking
        self.health_checks = {
            'failed': [],  # List of failed checks
            'last_check': None,  # Timestamp of last check
            'status': 'Not Started'  # Overall status
        }
        
        # Health reporting
        self.health_reporter = None  # Will be initialized in setup_hook
        
        # Setup environment
        Config.setup_environment()
        
        # Setup graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Set a default reciter to ensure select menus have options
        try:
            # Always set Saad Al Ghamdi as default reciter on startup
            self.set_current_reciter("Saad Al Ghamdi")
        except Exception as e:
            tree_log('warning', f"Failed to set default reciter: {e}", {'traceback': traceback.format_exc()})
        
        self._voice_clients = {}
        
        tree_log('info', 'QuranBot initialized', {'event': 'INIT', 'time': str(self.start_time)})
        
    async def setup_hook(self):
        """Setup hook for bot initialization."""
        t0 = time.time()
        tree_log('info', 'Setting up Quran Bot...', {'event': 'STARTUP'})
        
        # Run initial health checks
        try:
            self.health_checks['status'] = 'Running'
            self.health_checks['last_check'] = datetime.now()
            
            # Basic checks
            checks = [
                ('Audio Files', os.path.exists('audio')),
                ('Config', hasattr(Config, 'DEFAULT_RECITER')),
                ('Permissions', os.access('audio', os.R_OK)),
                ('FFmpeg', self._check_ffmpeg())
            ]
            
            self.health_checks['failed'] = [name for name, passed in checks if not passed]
            self.health_checks['status'] = 'OK' if not self.health_checks['failed'] else 'Issues Found'
            
            tree_log('info', 'Health checks completed', {'status': self.health_checks['status'], 'failed': self.health_checks['failed']})
        except Exception as e:
            tree_log('error', f'Failed to run health checks: {e}', {'traceback': traceback.format_exc()})
            self.health_checks['status'] = 'Error'
            self.health_checks['failed'].append('Health Check System')
        
        # Load individual command files
        commands_to_load = [
            'src.cogs.admin.bot_control.restart',
            'src.cogs.admin.monitoring.status',
            'src.cogs.admin.bot_control.reconnect',
            'src.cogs.admin.misc.credits',
            'src.cogs.admin.monitoring.utility_logs',
            'src.cogs.user_commands.control_panel'
        ]
        
        for command in commands_to_load:
            try:
                await self.load_extension(command)
                tree_log('info', 'Command loaded successfully', {'event': 'COMMAND_LOAD', 'command': command})
            except Exception as e:
                tree_log('error', f'Failed to load command {command}: {e}', {'event': 'COMMAND_LOAD_ERROR', 'traceback': traceback.format_exc()})
        
        # Sync command tree
        try:
            await self.tree.sync()
            tree_log('info', 'Command tree synced successfully', {'event': 'COMMAND_SYNC'})
        except Exception as e:
            tree_log('error', f'Failed to sync command tree: {e}', {'event': 'COMMAND_SYNC_ERROR', 'traceback': traceback.format_exc()})
        
        t1 = time.time()
        log_performance("setup_hook", t1-t0)
    
    async def load_extension(self, extension_name: str):
        """Load a cog extension."""
        try:
            import importlib
            module = importlib.import_module(extension_name)
            if hasattr(module, 'setup'):
                await module.setup(self)
                tree_log('info', 'Loaded extension', {'event': 'EXTENSION_LOAD', 'extension': extension_name})
            else:
                tree_log('error', f'Extension {extension_name} has no setup function', {'event': 'EXTENSION_ERROR'})
        except Exception as e:
            tree_log('error', f'Failed to load extension {extension_name}: {e}', {'event': 'EXTENSION_ERROR', 'traceback': traceback.format_exc()})
            raise
        
    @log_async_function_call
    async def on_ready(self):
        """Called when bot is ready."""
        t0 = time.time()
        tree_log('info', 'on_ready called', {'event': 'ON_READY', 'guilds': len(self.guilds)})
        if self.user:
            log_bot_startup(self.user.name, self.user.id)
            log_discord_event("ready", {"guilds": len(self.guilds)})
            t1 = time.time()
            log_performance("discord_ready", t1-t0)
            
            # Set up dynamic rich presence
            self.presence_messages = [
                (discord.ActivityType.listening, "📖 Quran 24/7"),
                (discord.ActivityType.playing, "🕋 Surah Al-Fatiha"),
                (discord.ActivityType.watching, "🕌 for your requests"),
                (discord.ActivityType.listening, "🎧 Beautiful Recitations"),
                (discord.ActivityType.playing, "📿 Dhikr & Remembrance")
            ]
            self.current_presence_index = 0
            self.presence_cycle = self._presence_cycle()
            await self.set_presence()
            
            # Start presence cycling
            try:
                self.presence_task = asyncio.create_task(self.cycle_presence())
            except Exception as e:
                tree_log('error', f'Failed to start presence cycling: {e}', {'traceback': traceback.format_exc()})
            
            # Initialize health monitoring
            try:
                self.health_reporter = HealthReporter(self, self.health_monitor, Config.LOGS_CHANNEL_ID)
                await self.health_reporter.start()
            except Exception as e:
                tree_log('error', f'Failed to start health reporter: {e}', {'traceback': traceback.format_exc()})
            
            # Initialize Discord logger sessions for users already in VC
            try:
                await self.discord_logger.initialize_existing_users()
            except Exception as e:
                tree_log('error', f'Failed to initialize discord logger sessions: {e}', {'traceback': traceback.format_exc()})
            
            # Initialize state management
            try:
                self.state_manager.increment_bot_start_count()
                start_count = self.state_manager.get_bot_start_count()
                log_state_load("bot_start_count", {"start_count": start_count})
            except Exception as e:
                tree_log('error', f'Failed to increment bot start count: {e}', {'traceback': traceback.format_exc()})
            
            # Clear last change on restart (always starts fresh)
            try:
                self.state_manager.clear_last_change()
            except Exception as e:
                tree_log('error', f'Failed to clear last change: {e}', {'traceback': traceback.format_exc()})
            
            # Find and join target voice channel
            t2 = time.time()
            tree_log('info', 'Finding and joining target voice channel', {'event': 'FIND_AND_JOIN', 'time': t2})
            await self.find_and_join_channel()
            if Config.AUTO_VOICE_CONNECT:
                tree_log('info', 'Bot ready - voice connection enabled', {'event': 'READY'})
            else:
                tree_log('info', 'Bot ready - voice connection disabled', {'event': 'READY'})
            t3 = time.time()
            log_performance("find_and_join_channel", t3-t2)
            
            # Log health status
            tree_log('info', 'Bot health monitoring initialized', {'event': 'HEALTH'})
            t4 = time.time()
            log_performance("state_manager_init", t4-t3)
            
            tree_log('info', 'Health reporting started', {'event': 'HEALTH'})
            t5 = time.time()
            log_performance("health_reporter_start", t5-t4)
        
    async def find_and_join_channel(self):
        """Find the target channel and join it."""
        t0 = time.time()
        tree_log('info', 'Searching for target channel', {'event': 'SEARCH_CHANNEL'})
        target_channel = None
        
        # Search through all guilds for the target channel
        for guild in self.guilds:
            channel = guild.get_channel(Config.TARGET_CHANNEL_ID)
            if channel and isinstance(channel, discord.VoiceChannel):
                target_channel = channel
                Config.TARGET_GUILD_ID = guild.id
                tree_log('info', 'Found target channel', {'channel': channel.name, 'guild': guild.name})
                break
        
        t1 = time.time()
        log_performance("guild_channel_search", t1-t0)
        
        if target_channel:
            if Config.AUTO_VOICE_CONNECT:
                tree_log('info', 'Auto voice connect enabled, starting stream', {'event': 'AUTO_VOICE_CONNECT'})
                await self.start_stream(target_channel)
            else:
                tree_log('info', 'Auto voice connect disabled', {'event': 'VOICE_DISABLED'})
        else:
            tree_log('error', 'Target channel not found', {'event': 'CHANNEL_NOT_FOUND', 'channel_id': Config.TARGET_CHANNEL_ID})
            logger.info("Make sure the bot has access to the target channel")
        t2 = time.time()
        log_performance("find_and_join_channel_total", t2-t0)
        
    async def on_voice_state_update(self, member, before, after):
        """Handle voice state updates for reconnection logic."""
        try:
            tree_log('debug', 'on_voice_state_update triggered', {'member': getattr(member, 'id', None), 'before': str(before.channel), 'after': str(after.channel)})
            if self.user and member.id == self.user.id:
                if before.channel and not after.channel:
                    # Bot was disconnected
                    log_disconnection(before.channel.name, "Disconnected from voice channel")
                    await self.discord_logger.log_bot_disconnected(before.channel.name, "Disconnected from voice channel")
                    # Properly reset streaming state on disconnection
                    self._was_streaming_before_disconnect = self.is_streaming
                    self.is_streaming = False
                    self.health_monitor.set_streaming_status(False)
                    
                    # Check if we've had too many failures
                    self.connection_failures += 1
                    if self.connection_failures >= self.max_connection_failures:
                        tree_log('error', f"Too many connection failures ({self.connection_failures}). Stopping reconnection attempts.", {'event': 'CONNECTION_FAILURE_LIMIT'})
                        self.is_streaming = False
                        return
                    
                    # Wait much longer before reconnecting to break the reconnection loop
                    wait_time = min(60 * self.connection_failures, 300)  # Progressive delay up to 5 minutes
                    tree_log('info', f"Waiting {wait_time} seconds before reconnection attempt {self.connection_failures}/{self.max_connection_failures}...", {'event': 'RECONNECT_WAIT', 'wait_time': wait_time, 'failures': self.connection_failures})
                    await asyncio.sleep(wait_time)
                    
                    if self.is_streaming:
                        tree_log('info', "Attempting to reconnect after disconnection...", {'event': 'RECONNECT_ATTEMPT'})
                        await self.find_and_join_channel()
                elif not before.channel and after.channel:
                    # Bot connected to voice
                    log_connection_success(after.channel.name, after.channel.guild.name)
                    await self.discord_logger.log_bot_connected(after.channel.name, after.channel.guild.name)
                    # Reset connection failure counter on successful connection
                    if self.connection_failures > 0:
                        tree_log('info', f"Connection successful! Reset failure counter from {self.connection_failures} to 0.", {'event': 'CONNECTION_SUCCESS'})
                        self.connection_failures = 0
                    # Resume streaming if it was previously active (with proper delay and checks)
                    # Check if we were streaming before the last disconnection
                    if hasattr(self, '_was_streaming_before_disconnect') and self._was_streaming_before_disconnect:
                        tree_log('info', "Bot was streaming before disconnect, scheduling resume...", {'event': 'STREAM_RESUME_SCHEDULED'})
                        
                        # Schedule delayed resume to ensure voice connection is stable
                        async def delayed_resume():
                            await asyncio.sleep(3)  # Wait 3 seconds for connection to stabilize
                            guild_id = after.channel.guild.id
                            if (guild_id in self._voice_clients and 
                                self._voice_clients[guild_id].is_connected() and
                                not self.is_streaming):  # Only resume if not already streaming
                                tree_log('info', "Resuming streaming after stable reconnection...", {'event': 'STREAM_RESUME_EXECUTE'})
                                self._was_streaming_before_disconnect = False  # Clear flag
                                await self.start_stream(after.channel)
                            else:
                                tree_log('warning', "Cannot resume streaming - connection not stable or already streaming", {'event': 'STREAM_RESUME_FAILED'})
                                self._was_streaming_before_disconnect = False  # Clear flag anyway
                        
                        asyncio.create_task(delayed_resume())
                    else:
                        tree_log('info', "Voice connected (no auto-resume needed)", {'event': 'VOICE_CONNECTED'})
                elif before.channel and after.channel and before.channel != after.channel:
                    # Bot moved to different channel
                    log_connection_success(after.channel.name, after.channel.guild.name)
                
            # Handle user voice state changes (not the bot) - only track target Quran VC
            elif member != self.user:
                target_vc_id = self.discord_logger.target_vc_id
                
                # User joined the target Quran VC from nowhere or different channel
                if after.channel and after.channel.id == target_vc_id and (not before.channel or before.channel.id != target_vc_id):
                    await self.discord_logger.log_user_joined_vc(member, after.channel.name)
                
                # User left the target Quran VC to nowhere or different channel  
                elif before.channel and before.channel.id == target_vc_id and (not after.channel or after.channel.id != target_vc_id):
                    await self.discord_logger.log_user_left_vc(member, before.channel.name)
        except Exception as e:
            tree_log('error', f'Error in on_voice_state_update: {e}', {'traceback': traceback.format_exc()})

    async def on_disconnect(self):
        """Handle bot disconnection."""
        tree_log('warning', 'Bot disconnected from Discord', {'event': 'DISCONNECT'})
        self.is_streaming = False
        self.health_monitor.set_streaming_status(False)

    async def handle_voice_session_expired(self, guild_id):
        """Handle voice session expired (4006) errors."""
        tree_log('warning', 'Voice session expired, waiting before reconnect', {'event': 'VOICE_SESSION_EXPIRED', 'guild_id': guild_id})
        
        # Remove from voice clients
        if guild_id in self._voice_clients:
            del self._voice_clients[guild_id]
        
        # Wait much longer before reconnecting to break the reconnection loop
        await asyncio.sleep(120)  # Wait 2 minutes
        
        # Try to reconnect if still streaming
        if self.is_streaming:
            tree_log('info', "Attempting reconnection after session expired...", {'event': 'SESSION_RECONNECT'})
            await self.find_and_join_channel()

    async def handle_voice_error(self, voice_client, error):
        """Handle voice connection errors with retry logic."""
        guild_id = voice_client.guild.id if voice_client.guild else None
        error_msg = str(error)
        
        if "4006" in error_msg or "session expired" in error_msg.lower():
            tree_log('warning', f"Voice session expired (4006) for guild {guild_id}. Waiting before reconnection...", {'event': 'VOICE_ERROR', 'error_code': '4006'})
            # Remove from voice clients
            if guild_id in self._voice_clients:
                del self._voice_clients[guild_id]
            
            # Wait much longer before reconnecting to break the reconnection loop
            await asyncio.sleep(120)  # Wait 2 minutes
            
            # Try to reconnect
            if self.is_streaming:
                tree_log('info', "Attempting reconnection after session expired...", {'event': 'SESSION_RECONNECT'})
                await self.find_and_join_channel()
        else:
            tree_log('error', f"Voice error for guild {guild_id}: {error_msg}", {'event': 'VOICE_ERROR', 'error': error_msg})
            self.health_monitor.record_error(error, f"voice_error_guild_{guild_id}")

    async def start_stream(self, channel: discord.VoiceChannel):
        """Start streaming Quran to the voice channel with improved error handling."""
        t0 = time.time()
        tree_log('info', 'Starting stream', {'event': 'START_STREAM', 'channel': getattr(channel, 'name', None)})
        max_retries = 3  # Reduced retries to prevent spam
        retry_delay = 30   # Start with longer delay
        
        for attempt in range(max_retries):
            try:
                guild_id = channel.guild.id
                
                # Disconnect if already connected
                if guild_id in self._voice_clients:
                    try:
                        await self._voice_clients[guild_id].disconnect()
                        await asyncio.sleep(5)  # Wait longer for disconnect to complete
                    except Exception as e:
                        log_error(e, "disconnect_old_client")
                        self.health_monitor.record_error(e, "disconnect_old_client")
                    
                # Connect to voice channel
                log_connection_attempt(channel.name, attempt + 1, max_retries)
                t1 = time.time()
                voice_client = await channel.connect()
                
                t2 = time.time()
                log_performance("voice_connect", t2-t1)
                self._voice_clients[guild_id] = voice_client
                
                # Record successful connection
                log_connection_success(channel.name, channel.guild.name)
                self.health_monitor.record_reconnection()
                
                # Start playbook in background task
                asyncio.create_task(self.play_quran_files(voice_client, channel))
                break
                
            except discord.ClientException as e:
                if "Already connected to a voice channel" in str(e):
                    # Already connected, just start playback
                    guild_id = channel.guild.id
                    if guild_id in self._voice_clients:
                        voice_client = self._voice_clients[guild_id]
                        asyncio.create_task(self.play_quran_files(voice_client, channel))
                        break
                else:
                    log_connection_failure(channel.name, e, attempt + 1)
                    self.health_monitor.record_error(e, "voice_connection")
            
            # Exponential backoff with longer delays for 4006 errors
            if attempt < max_retries - 1:
                delay = min(retry_delay * (3 ** attempt), 300)  # Cap at 5 minutes, use 3x multiplier
                tree_log('info', f"Retrying connection in {delay} seconds...", {'event': 'RETRY', 'attempt': attempt + 1, 'delay': delay})
                await asyncio.sleep(delay)
                
        t3 = time.time()
        log_performance("start_stream_total", t3-t0)
        
        # Log warning if still slow
        if (t3-t0) > 3.0:
            tree_log('warning', f"Connection took {t3-t0:.2f}s - consider Discord server issues", {'event': 'SLOW_CONNECTION', 'duration': t3-t0})
        
    def get_audio_files(self) -> list:
        """Get list of audio files from the current reciter."""
        return Config.get_audio_files(self.current_reciter)
    
    def get_available_reciters(self) -> list:
        """Get list of available reciters."""
        return Config.get_available_reciters()
    
    def get_current_reciter(self) -> str:
        """Get the current active reciter display name."""
        return Config.get_reciter_display_name(self.current_reciter)
    
    def set_current_reciter(self, reciter_name: str) -> bool:
        """Set the current reciter and validate it exists."""
        # Convert display name to folder name if needed
        folder_name = Config.get_folder_name_from_display(reciter_name)
        
        # Check if the folder exists
        reciter_path = os.path.join(Config.AUDIO_FOLDER, folder_name)
        if os.path.exists(reciter_path) and os.path.isdir(reciter_path):
            # Check if the folder contains MP3 files
            has_mp3 = any(f.lower().endswith('.mp3') for f in os.listdir(reciter_path))
            if has_mp3:
                self.current_reciter = folder_name  # Store the folder name
                self.original_playlist = []  # Reset playlist cache on reciter switch
                tree_log('info', f"Switched to reciter: {reciter_name} (folder: {folder_name})", {'event': 'RECITER_CHANGE', 'reciter': reciter_name, 'folder': folder_name})
                return True
        
        tree_log('warning', f"Reciter not found: {reciter_name} (folder: {folder_name})", {'event': 'RECITER_NOT_FOUND', 'reciter': reciter_name, 'folder': folder_name})
        return False
    
    def toggle_loop(self, user_id: Optional[int] = None, username: Optional[str] = None) -> bool:
        """Toggle loop mode for current surah with user tracking."""
        self.loop_enabled = not self.loop_enabled
        
        if self.loop_enabled and user_id is not None and username is not None:
            # Track who enabled the loop
            self.state_manager.set_loop_enabled_by(user_id, username)
            tree_log('info', f"Loop mode enabled by {username} (ID: {user_id})", {'event': 'LOOP_TOGGLE', 'loop_enabled': True, 'user_id': user_id, 'username': username})
        elif not self.loop_enabled:
            # Clear loop tracking when disabled
            self.state_manager.clear_loop_enabled_by()
            tree_log('info', "Loop mode disabled", {'event': 'LOOP_TOGGLE', 'loop_enabled': False})
        else:
            tree_log('info', f"Loop mode {'enabled' if self.loop_enabled else 'disabled'}", {'event': 'LOOP_TOGGLE', 'loop_enabled': self.loop_enabled})
        
        return self.loop_enabled
    
    def toggle_shuffle(self, user_id: Optional[int] = None, username: Optional[str] = None) -> bool:
        """Toggle shuffle mode for surah order with user tracking."""
        self.shuffle_enabled = not self.shuffle_enabled
        
        if self.shuffle_enabled and user_id is not None and username is not None:
            # Track who enabled the shuffle
            self.state_manager.set_shuffle_enabled_by(user_id, username)
            tree_log('info', f"Shuffle mode enabled by {username} (ID: {user_id})", {'event': 'SHUFFLE_TOGGLE', 'shuffle_enabled': True, 'user_id': user_id, 'username': username})
        elif not self.shuffle_enabled:
            # Clear shuffle tracking when disabled
            self.state_manager.clear_shuffle_enabled_by()
            tree_log('info', "Shuffle mode disabled", {'event': 'SHUFFLE_TOGGLE', 'shuffle_enabled': False})
        else:
            tree_log('info', f"Shuffle mode {'enabled' if self.shuffle_enabled else 'disabled'}", {'event': 'SHUFFLE_TOGGLE', 'shuffle_enabled': self.shuffle_enabled})
        
        return self.shuffle_enabled
    
    def get_shuffled_playlist(self) -> list:
        """Get shuffled playlist while preserving original order."""
        import random
        mp3_files = self.get_audio_files()
        if not self.original_playlist:
            self.original_playlist = mp3_files.copy()
        
        if self.shuffle_enabled:
            shuffled = mp3_files.copy()
            random.shuffle(shuffled)
            return shuffled
        else:
            return self.original_playlist if self.original_playlist else mp3_files

    async def get_audio_duration(self, file_path):
        """Get the duration of an audio file using FFmpeg."""
        try:
            # Try ffprobe first
            cmd = [
                'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                '-of', 'csv=p=0', file_path
            ]
            result = await asyncio.to_thread(subprocess.run, cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                return duration
        except Exception as e:
            tree_log('debug', f"ffprobe failed for {file_path}: {e}", {'event': 'FFPROBE', 'file': file_path})
        
        # Fallback: try to get duration using ffmpeg
        try:
            cmd = [
                'ffmpeg', '-i', file_path, '-f', 'null', '-'
            ]
            result = await asyncio.to_thread(subprocess.run, cmd, capture_output=True, text=True, timeout=30)
            # Parse duration from ffmpeg output
            import re
            for line in result.stderr.split('\n'):
                if 'Duration:' in line:
                    # Extract duration from line like "Duration: 00:03:45.00, start: 0.000000, bitrate: 128 kb/s"
                    duration_match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})', line)
                    if duration_match:
                        hours = int(duration_match.group(1))
                        minutes = int(duration_match.group(2))
                        seconds = int(duration_match.group(3))
                        centiseconds = int(duration_match.group(4))
                        total_seconds = hours * 3600 + minutes * 60 + seconds + centiseconds / 100
                        return total_seconds
        except Exception as e:
            tree_log('debug', f"ffmpeg duration fallback failed for {file_path}: {e}", {'event': 'FFMPEG_DURATION', 'file': file_path})
        
        # Final fallback: estimate based on file size (rough approximation)
        try:
            file_size = os.path.getsize(file_path)
            # Rough estimate: 1 MB ≈ 1 minute for typical MP3 quality
            estimated_duration = file_size / (1024 * 1024) * 60
            tree_log('info', f"Using estimated duration for {file_path}: {estimated_duration:.1f} seconds", {'event': 'ESTIMATED_DURATION', 'file': file_path})
            return estimated_duration
        except Exception as e:
            tree_log('warning', f"Could not estimate duration for {file_path}: {e}", {'event': 'DURATION_FAILED', 'file': file_path})
            return None

    async def play_surah_with_retries(self, voice_client, mp3_file, max_retries=2):
        tree_log('info', 'Entered play_surah_with_retries', {'file': mp3_file})
        try:
            for attempt in range(max_retries + 1):
                tree_log('debug', 'Playback attempt', {'attempt': attempt+1, 'file': mp3_file})
                try:
                    source = discord.FFmpegPCMAudio(mp3_file)
                    tree_log('info', f"Created FFmpeg source for {mp3_file}")
                    voice_client.play(source)
                    tree_log('info', f"Started playback for {mp3_file}")
                    while voice_client.is_playing():
                        await asyncio.sleep(1)
                    tree_log('info', f"Finished playback for {mp3_file}")
                    break
                except Exception as e:
                    tree_log('error', f"Exception during playback attempt {attempt+1} for {mp3_file}: {e}", {'attempt': attempt+1, 'file': mp3_file, 'traceback': traceback.format_exc()})
        except Exception as e:
            tree_log('error', f"Exception in play_surah_with_retries: {e}", {'file': mp3_file, 'traceback': traceback.format_exc()})
        tree_log('info', 'Exiting play_surah_with_retries', {'file': mp3_file})

    async def play_quran_files(self, voice_client, channel):
        tree_log('debug', 'play_quran_files called', {'channel': str(channel)})
        try:
            # Log current state before getting playlist
            if hasattr(self, 'state_manager') and hasattr(self.state_manager, 'get_current_song_index'):
                current_index = self.state_manager.get_current_song_index()
            else:
                current_index = None
            tree_log('debug', 'Current playback state', {
                'current_reciter': getattr(self, 'current_reciter', None),
                'current_song_index': current_index,
                'is_streaming': getattr(self, 'is_streaming', None)
            })
            mp3_files = self.get_shuffled_playlist()
            tree_log('debug', 'Playlist for playback', {'playlist': mp3_files, 'playlist_length': len(mp3_files)})
            if not mp3_files:
                tree_log('error', 'No MP3 files found for playback.')
                return
            # Start from the current surah index
            start_index = 0
            if hasattr(self, 'state_manager') and hasattr(self.state_manager, 'get_current_song_index'):
                start_index = self.state_manager.get_current_song_index() or 0
            tree_log('debug', 'Starting playback from index', {'start_index': start_index, 'start_file': mp3_files[start_index] if start_index < len(mp3_files) else None})
            for i, mp3_file in enumerate(mp3_files[start_index:], start=start_index):
                tree_log('debug', 'Attempting to play file', {'file': mp3_file, 'index': i})
                valid = await self.validate_audio_file(mp3_file)
                tree_log('debug', 'Validation result', {'file': mp3_file, 'valid': valid})
                if not valid:
                    continue
                await self.play_surah_with_retries(voice_client, mp3_file)
                # Log after playing each file
                tree_log('debug', 'Finished playing file', {'file': mp3_file, 'index': i})
        except Exception as e:
            tree_log('error', f"Exception in play_quran_files: {e}", {'traceback': traceback.format_exc()})
        tree_log('debug', 'Exiting play_quran_files', {'channel': str(channel)})
            
    async def close(self):
        """Cleanup when bot is shutting down."""
        tree_log('info', 'Closing bot', {'event': 'CLOSE'})
        if self.health_reporter:
            await self.health_reporter.stop()
        await super().close()

    async def update_presence_for_surah(self, surah_info):
        """Update the bot's presence to show the currently playing surah."""
        try:
            tree_log('debug', 'Updating presence for surah', {'surah_info': surah_info})
            emoji = get_surah_emoji(surah_info['number'])
            activity_type = discord.ActivityType.listening
            message = f"{emoji} {surah_info['english_name']}"
            
            await self.change_presence(activity=discord.Activity(type=activity_type, name=message))
            tree_log('debug', f"Updated presence to: {message}")
        except Exception as e:
            tree_log('error', f'Error in update_presence_for_surah: {e}', {'traceback': traceback.format_exc()})

    async def cycle_presence(self):
        """Cycle through different rich presences every 2 minutes."""
        try:
            tree_log('info', 'Starting cycle_presence loop', {})
            while True:
                # Check if we're currently playing a surah
                if hasattr(self, 'current_audio_file') and self.current_audio_file:
                    surah_info = get_surah_from_filename(self.current_audio_file)
                    await self.update_presence_for_surah(surah_info)
                else:
                    # Fallback to cycling through general messages
                    activity_type, message = next(self.presence_cycle)
                    await self.change_presence(activity=discord.Activity(type=activity_type, name=message))
                
                await asyncio.sleep(120)  # 2 minutes instead of 5
        except Exception as e:
            tree_log('error', f'Error in cycle_presence: {e}', {'traceback': traceback.format_exc()})

    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        tree_log('warning', f"\n🛑 Received signal {signum}. Starting graceful shutdown...", {})
        asyncio.create_task(self.graceful_shutdown())
        
    async def graceful_shutdown(self):
        """Perform graceful shutdown with state saving and cleanup."""
        try:
            tree_log('info', 'Graceful shutdown initiated', {'event': 'GRACEFUL_SHUTDOWN'})
            
            # Stop streaming
            self.is_streaming = False
            self.health_monitor.set_streaming_status(False)
            
            # Stop health reporting
            if self.health_reporter:
                await self.health_reporter.stop()
                tree_log('info', 'Health reporting stopped', {})
            
            # Cleanup Discord logger sessions
            if hasattr(self, 'discord_logger'):
                await self.discord_logger.cleanup_sessions()
            
            # Stop presence cycling
            if self.presence_task and not self.presence_task.done():
                self.presence_task.cancel()
                try:
                    await self.presence_task
                except asyncio.CancelledError:
                    pass
                tree_log('info', 'Presence cycling stopped', {})
            
            # Disconnect from all voice channels
            for guild_id, voice_client in self._voice_clients.items():
                try:
                    if voice_client.is_connected():
                        await voice_client.disconnect()
                        tree_log('info', f"Disconnected from voice channel in guild {guild_id}", {'guild_id': guild_id})
                except Exception as e:
                    log_error(e, f"disconnect_voice_guild_{guild_id}")
            
            # Save final state
            if hasattr(self, 'current_audio_file') and self.current_audio_file:
                self.state_manager.set_current_song_name(self.current_audio_file)
                tree_log('info', f"Saved final state: {self.current_audio_file}", {})
            
            # Close Discord client
            await self.close()
            
            tree_log('info', '✅ Graceful shutdown completed successfully!', {})
            
        except Exception as e:
            tree_log('error', f'❌ Error during shutdown: {e}', {'traceback': traceback.format_exc()})
        finally:
            # Force exit after cleanup
            sys.exit(0)

    def _presence_cycle(self):
        """Generator for cycling through presence messages."""
        while True:
            for activity_type, message in self.presence_messages:
                yield activity_type, message

    async def set_presence(self):
        """Set initial presence for the bot."""
        try:
            tree_log('debug', 'Setting initial presence', {})
            activity_type, message = next(self.presence_cycle)
            await self.change_presence(activity=discord.Activity(type=activity_type, name=message))
        except Exception as e:
            tree_log('error', f'Error in set_presence: {e}', {'traceback': traceback.format_exc()})

    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available and working."""
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    async def play_audio(self):
        """Restart audio playback - wrapper for control panel compatibility."""
        try:
            tree_log('info', 'Restarting audio playback', {})
            # Find the current voice client
            voice_client = None
            channel = None
            
            for guild in self.guilds:
                if guild.voice_client:
                    voice_client = guild.voice_client
                    channel = voice_client.channel
                    break
            
            if voice_client and channel and hasattr(voice_client, 'is_connected') and voice_client.is_connected():
                # Stop current playback
                self.is_streaming = False
                await asyncio.sleep(1)  # Give time for current playback to stop
                
                # Restart playback
                self.is_streaming = True
                # Type cast to ensure compatibility
                if isinstance(voice_client, discord.VoiceClient) and isinstance(channel, discord.VoiceChannel):
                    asyncio.create_task(self.play_quran_files(voice_client, channel))
                    tree_log('info', 'Audio playback restarted via control panel', {})
                else:
                    tree_log('warning', 'Invalid voice client or channel type', {})
            else:
                tree_log('warning', 'No voice client found for audio restart', {})
        except Exception as e:
            tree_log('error', f'Error restarting audio playback: {e}', {'traceback': traceback.format_exc()})
            log_error(e, "play_audio")

    def get_current_playback_time(self):
        if self.playback_start_time:
            return time.time() - self.playback_start_time
        return 0

    async def validate_audio_file(self, file_path):
        try:
            tree_log('debug', 'Validating audio file', {'file_path': file_path})
            if not os.path.exists(file_path):
                tree_log('error', f"Audio file not found during validation: {file_path}", {'traceback': traceback.format_exc()})
                return False
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                tree_log('error', f"Audio file is empty during validation: {file_path}", {'traceback': traceback.format_exc()})
                return False
            # Check if file is a valid audio file using ffprobe
            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-select_streams",
                "a:0",
                "-show_entries",
                "stream=codec_name",
                "-of",
                "csv=p=0",
                file_path,
            ]
            result = await asyncio.to_thread(subprocess.run, cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout.strip():
                codec = result.stdout.strip()
                tree_log('debug', f"Audio file validation successful for {file_path}: codec={codec}, size={file_size/1024/1024:.1f}MB", {'file_path': file_path})
                return True
            else:
                tree_log('error', f"Audio file validation failed for {file_path}: {result.stderr}", {'traceback': traceback.format_exc()})
                return False
        except subprocess.TimeoutExpired:
            tree_log('error', f"Audio file validation timeout for {file_path}", {'traceback': traceback.format_exc()})
            return False
        except Exception as e:
            tree_log('error', f"Error in validate_audio_file for {file_path}: {e}", {'traceback': traceback.format_exc()})
            return False

def main():
    """Main entry point for the Quran Bot."""
    from monitoring.logging.logger import logger
    
    # Validate configuration
    if not Config.validate():
        logger.critical("❌ Configuration validation failed!")
        return
    if not Config.DISCORD_TOKEN:
        logger.critical("❌ Discord token not set in environment!")
        return
    # Create bot instance
    bot = QuranBot()
    tree_log('info', 'Starting Quran Bot...', {})
    try:
        bot.run(Config.DISCORD_TOKEN)
    except Exception as e:
        log_error(e, "main")
        logger.critical(f"❌ Failed to start bot: {e}")

if __name__ == "__main__":
    main() 