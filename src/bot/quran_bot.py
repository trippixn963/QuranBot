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

# Add src to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config.config import Config
from monitoring.logging.logger import (
    logger, log_bot_startup, log_audio_playback,
    log_connection_attempt, log_connection_success, log_connection_failure,
    log_health_report, log_state_save, log_state_load, log_performance,
    log_error, log_discord_event, log_ffmpeg_operation, log_security_event,
    log_retry_operation, log_shutdown, log_disconnection, track_performance
)
from monitoring.health.health import HealthMonitor
from monitoring.health.health_reporter import HealthReporter
from monitoring.logging.discord_logger import DiscordEmbedLogger
from core.state.state_manager import StateManager
from core.mapping.surah_mapper import get_surah_from_filename, get_surah_emoji, get_surah_display_name
from monitoring.logging.log_helpers import log_async_function_call, log_function_call, log_operation, get_system_metrics, get_discord_context, get_bot_state

class QuranBot(discord.Client):
    """Professional Discord bot for 24/7 Quran streaming."""
    
    def __init__(self):
        """Initialize the Quran Bot."""
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True

        super().__init__(intents=intents)
        
        # Initialize command tree for slash commands
        self.tree = discord.app_commands.CommandTree(self)
        
        # Bot state
        self._voice_clients: Dict[int, discord.VoiceClient] = {}
        self.is_streaming = False
        self.current_audio_file: Optional[str] = None
        # Store the folder name internally, but use display name for UI
        # Get the default reciter display name and convert to folder name
        default_reciter_display = Config.DEFAULT_RECITER
        self.current_reciter: str = Config.get_folder_name_from_display(default_reciter_display)
        self.connection_failures = 0  # Track connection failures
        self.max_connection_failures = 5  # Stop trying after 5 failures
        self.start_time = time.time()  # For uptime calculation
        
        # Playback control
        self.loop_enabled = False  # Loop current surah
        self.shuffle_enabled = False  # Shuffle surah order
        self.original_playlist = []  # Store original playlist for shuffle
        
        # Health monitoring
        self.health_monitor = HealthMonitor()
        
        # Health reporting
        self.health_reporter = None
        
        # Discord embed logging
        self.discord_logger = DiscordEmbedLogger(
            self, 
            1389683881078423567,  # logs channel
            1389675580253016144   # target VC to track
        )
        
        # State management
        self.state_manager = StateManager()
        
        # Setup environment
        Config.setup_environment()
        
        # Setup graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
    async def setup_hook(self):
        """Setup hook for bot initialization."""
        t0 = time.time()
        logger.info("Setting up Quran Bot...", extra={'event': 'STARTUP'})
        
        # Load individual command files
        commands_to_load = [
            'src.cogs.admin.bot_control.restart',
            'src.cogs.admin.monitoring.status',
            'src.cogs.admin.misc.skip',
            'src.cogs.admin.bot_control.reconnect',
            'src.cogs.admin.misc.credits',
            'src.cogs.admin.monitoring.utility_logs',
            'src.cogs.user_commands.control_panel'
        ]
        
        for command in commands_to_load:
            try:
                await self.load_extension(command)
                logger.info(f"Command loaded successfully: {command}", extra={'event': 'COMMAND_LOAD'})
            except Exception as e:
                logger.error(f"Failed to load command {command}: {e}", extra={'event': 'COMMAND_LOAD_ERROR'})
        
        # Sync command tree
        try:
            await self.tree.sync()
            logger.info("Command tree synced successfully", extra={'event': 'COMMAND_SYNC'})
        except Exception as e:
            logger.error(f"Failed to sync command tree: {e}", extra={'event': 'COMMAND_SYNC_ERROR'})
        
        t1 = time.time()
        log_performance("setup_hook", t1-t0)
    
    async def load_extension(self, extension_name: str):
        """Load a cog extension."""
        try:
            import importlib
            module = importlib.import_module(extension_name)
            if hasattr(module, 'setup'):
                await module.setup(self)
                logger.info(f"Loaded extension: {extension_name}", extra={'event': 'EXTENSION_LOAD'})
            else:
                logger.error(f"Extension {extension_name} has no setup function", extra={'event': 'EXTENSION_ERROR'})
        except Exception as e:
            logger.error(f"Failed to load extension {extension_name}: {e}", extra={'event': 'EXTENSION_ERROR'})
            raise
        
    @log_async_function_call
    async def on_ready(self):
        """Called when bot is ready."""
        t0 = time.time()
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
            self.presence_task = asyncio.create_task(self.cycle_presence())
            
            # Initialize health monitoring
            self.health_reporter = HealthReporter(self, self.health_monitor, Config.LOGS_CHANNEL_ID)
            await self.health_reporter.start()
            
            # Initialize Discord logger sessions for users already in VC
            await self.discord_logger.initialize_existing_users()
            
            # Initialize state manager
            self.state_manager = StateManager()
            
            # Find and join target voice channel
            t2 = time.time()
            logger.info(f"Auto voice connect setting: {Config.AUTO_VOICE_CONNECT}", 
                       extra={'event': 'CONFIG_CHECK', 'auto_voice_connect': Config.AUTO_VOICE_CONNECT})
            await self.find_and_join_channel()
            if Config.AUTO_VOICE_CONNECT:
                logger.info("Bot ready - voice connection enabled", extra={'event': 'READY'})
            else:
                logger.info("Bot ready - voice connection disabled", extra={'event': 'READY'})
            t3 = time.time()
            log_performance("find_and_join_channel", t3-t2)
            
            # Log health status
            logger.info("Bot health monitoring initialized", extra={'event': 'HEALTH'})
            logger.info("DEBUG: About to initialize state management", extra={'event': 'DEBUG_STATE_INIT'})
            
            # Initialize state management
            self.state_manager.increment_bot_start_count()
            start_count = self.state_manager.get_bot_start_count()
            log_state_load("bot_start_count", {"start_count": start_count})
            
            # Clear last change on restart (always starts fresh)
            self.state_manager.clear_last_change()
            t4 = time.time()
            log_performance("state_manager_init", t4-t3)
            
            logger.info("Health reporting started", extra={'event': 'HEALTH'})
            t5 = time.time()
            log_performance("health_reporter_start", t5-t4)
        
    async def find_and_join_channel(self):
        """Find the target channel and join it."""
        t0 = time.time()
        target_channel = None
        
        # Search through all guilds for the target channel
        for guild in self.guilds:
            channel = guild.get_channel(Config.TARGET_CHANNEL_ID)
            if channel and isinstance(channel, discord.VoiceChannel):
                target_channel = channel
                Config.TARGET_GUILD_ID = guild.id
                logger.info(f"Found target channel: {channel.name} in guild: {guild.name}", 
                           extra={'event': 'channel_found', 'channel': channel.name, 'guild': guild.name})
                break
        
        t1 = time.time()
        log_performance("guild_channel_search", t1-t0)
        
        if target_channel:
            if Config.AUTO_VOICE_CONNECT:
                await self.start_stream(target_channel)
            else:
                logger.info("Automatic voice connection disabled - bot will start without voice connection", 
                           extra={'event': 'VOICE_DISABLED'})
        else:
            log_error(Exception("Channel not found"), "find_and_join_channel", 
                     additional_data={"channel_id": Config.TARGET_CHANNEL_ID})
            logger.info("Make sure the bot has access to the target channel")
        t2 = time.time()
        log_performance("find_and_join_channel_total", t2-t0)
        
    async def on_voice_state_update(self, member, before, after):
        """Handle voice state updates for reconnection logic and user tracking."""
        # Handle bot's own voice state changes
        if self.user and member.id == self.user.id:
            if before.channel and not after.channel:
                # Bot was disconnected
                log_disconnection(before.channel.name, "Disconnected from voice channel")
                await self.discord_logger.log_bot_disconnected(before.channel.name, "Disconnected from voice channel")
                self.is_streaming = False
                self.health_monitor.set_streaming_status(False)
                
                # Check if we've had too many failures
                self.connection_failures += 1
                if self.connection_failures >= self.max_connection_failures:
                    logger.error(f"Too many connection failures ({self.connection_failures}). Stopping reconnection attempts.", 
                               extra={'event': 'CONNECTION_FAILURE_LIMIT'})
                    self.is_streaming = False
                    return
                
                # TEMPORARILY DISABLE AUTO-RECONNECTION TO BREAK THE LOOP
                logger.warning(f"Connection lost. Auto-reconnection temporarily disabled to prevent loops. Failures: {self.connection_failures}/{self.max_connection_failures}",
                             extra={'event': 'RECONNECT_DISABLED', 'failures': self.connection_failures})
                # Stop streaming to break the reconnection cycle
                self.is_streaming = False
                
                # Uncomment below to re-enable auto-reconnection after testing
                # wait_time = min(60 * self.connection_failures, 300)  # Progressive delay up to 5 minutes
                # logger.info(f"Waiting {wait_time} seconds before reconnection attempt {self.connection_failures}/{self.max_connection_failures}...", 
                #            extra={'event': 'RECONNECT_WAIT', 'wait_time': wait_time, 'failures': self.connection_failures})
                # await asyncio.sleep(wait_time)
                # 
                # if self.is_streaming:
                #     logger.info("Attempting to reconnect after disconnection...", 
                #                extra={'event': 'RECONNECT_ATTEMPT'})
                #     await self.find_and_join_channel()
            elif not before.channel and after.channel:
                # Bot connected to voice
                log_connection_success(after.channel.name, after.channel.guild.name)
                await self.discord_logger.log_bot_connected(after.channel.name, after.channel.guild.name)
                # Reset connection failure counter on successful connection
                if self.connection_failures > 0:
                    logger.info(f"Connection successful! Reset failure counter from {self.connection_failures} to 0.", 
                               extra={'event': 'CONNECTION_SUCCESS'})
                    self.connection_failures = 0
                # Resume streaming if it was active
                if self.is_streaming:
                    logger.info("Resuming streaming after reconnection...", 
                               extra={'event': 'STREAM_RESUME'})
                    await self.start_stream(after.channel)
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

    async def on_disconnect(self):
        """Handle bot disconnection."""
        log_disconnection("Discord", "Bot disconnected from Discord")
        self.is_streaming = False
        self.health_monitor.set_streaming_status(False)

    async def handle_voice_session_expired(self, guild_id):
        """Handle voice session expired (4006) errors."""
        logger.warning(f"Voice session expired (4006) for guild {guild_id}. Waiting before reconnection...", 
                      extra={'event': 'VOICE_ERROR', 'error_code': '4006'})
        
        # Remove from voice clients
        if guild_id in self._voice_clients:
            del self._voice_clients[guild_id]
        
        # Wait much longer before reconnecting to break the reconnection loop
        await asyncio.sleep(120)  # Wait 2 minutes
        
        # Try to reconnect if still streaming
        if self.is_streaming:
            logger.info("Attempting reconnection after session expired...", 
                       extra={'event': 'SESSION_RECONNECT'})
            await self.find_and_join_channel()

    async def handle_voice_error(self, voice_client, error):
        """Handle voice connection errors with retry logic."""
        guild_id = voice_client.guild.id if voice_client.guild else None
        error_msg = str(error)
        
        if "4006" in error_msg or "session expired" in error_msg.lower():
            logger.warning(f"Voice session expired (4006) for guild {guild_id}. Waiting before reconnection...", 
                          extra={'event': 'VOICE_ERROR', 'error_code': '4006'})
            # Remove from voice clients
            if guild_id in self._voice_clients:
                del self._voice_clients[guild_id]
            
            # Wait much longer before reconnecting to break the reconnection loop
            await asyncio.sleep(120)  # Wait 2 minutes
            
            # Try to reconnect
            if self.is_streaming:
                logger.info("Attempting reconnection after session expired...", 
                           extra={'event': 'SESSION_RECONNECT'})
                await self.find_and_join_channel()
        else:
            logger.error(f"Voice error for guild {guild_id}: {error_msg}", 
                        extra={'event': 'VOICE_ERROR', 'error': error_msg})
            self.health_monitor.record_error(error, f"voice_error_guild_{guild_id}")

    async def start_stream(self, channel: discord.VoiceChannel):
        """Start streaming Quran to the voice channel with improved error handling."""
        t0 = time.time()
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
                
                # Voice client connected successfully
                
                # Record successful connection
                log_connection_success(channel.name, channel.guild.name)
                self.health_monitor.record_reconnection()
                
                # Start playback in background task
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
                logger.info(f"Retrying connection in {delay} seconds...", 
                           extra={'event': 'RETRY', 'attempt': attempt + 1, 'delay': delay})
                await asyncio.sleep(delay)
                
        t3 = time.time()
        log_performance("start_stream_total", t3-t0)
        
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
                logger.info(f"Switched to reciter: {reciter_name} (folder: {folder_name})", 
                           extra={'event': 'RECITER_CHANGE', 'reciter': reciter_name, 'folder': folder_name})
                return True
        
        logger.warning(f"Reciter not found: {reciter_name} (folder: {folder_name})", 
                      extra={'event': 'RECITER_NOT_FOUND', 'reciter': reciter_name, 'folder': folder_name})
        return False
    
    def toggle_loop(self, user_id: Optional[int] = None, username: Optional[str] = None) -> bool:
        """Toggle loop mode for current surah with user tracking."""
        self.loop_enabled = not self.loop_enabled
        
        if self.loop_enabled and user_id is not None and username is not None:
            # Track who enabled the loop
            self.state_manager.set_loop_enabled_by(user_id, username)
            logger.info(f"Loop mode enabled by {username} (ID: {user_id})", 
                       extra={'event': 'LOOP_TOGGLE', 'loop_enabled': True, 'user_id': user_id, 'username': username})
        elif not self.loop_enabled:
            # Clear loop tracking when disabled
            self.state_manager.clear_loop_enabled_by()
            logger.info("Loop mode disabled", 
                       extra={'event': 'LOOP_TOGGLE', 'loop_enabled': False})
        else:
            logger.info(f"Loop mode {'enabled' if self.loop_enabled else 'disabled'}", 
                       extra={'event': 'LOOP_TOGGLE', 'loop_enabled': self.loop_enabled})
        
        return self.loop_enabled
    
    def toggle_shuffle(self, user_id: Optional[int] = None, username: Optional[str] = None) -> bool:
        """Toggle shuffle mode for surah order with user tracking."""
        self.shuffle_enabled = not self.shuffle_enabled
        
        if self.shuffle_enabled and user_id is not None and username is not None:
            # Track who enabled the shuffle
            self.state_manager.set_shuffle_enabled_by(user_id, username)
            logger.info(f"Shuffle mode enabled by {username} (ID: {user_id})", 
                       extra={'event': 'SHUFFLE_TOGGLE', 'shuffle_enabled': True, 'user_id': user_id, 'username': username})
        elif not self.shuffle_enabled:
            # Clear shuffle tracking when disabled
            self.state_manager.clear_shuffle_enabled_by()
            logger.info("Shuffle mode disabled", 
                       extra={'event': 'SHUFFLE_TOGGLE', 'shuffle_enabled': False})
        else:
            logger.info(f"Shuffle mode {'enabled' if self.shuffle_enabled else 'disabled'}", 
                       extra={'event': 'SHUFFLE_TOGGLE', 'shuffle_enabled': self.shuffle_enabled})
        
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

    def get_audio_duration(self, file_path):
        """Get the duration of an audio file using FFmpeg."""
        try:
            # Try ffprobe first
            cmd = [
                'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                '-of', 'csv=p=0', file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                return duration
        except Exception as e:
            logger.debug(f"ffprobe failed for {file_path}: {e}", extra={"event": "FFPROBE", "file": file_path})
        
        # Fallback: try to get duration using ffmpeg
        try:
            cmd = [
                'ffmpeg', '-i', file_path, '-f', 'null', '-'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
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
            logger.debug(f"ffmpeg duration fallback failed for {file_path}: {e}", extra={"event": "FFMPEG_DURATION", "file": file_path})
        
        # Final fallback: estimate based on file size (rough approximation)
        try:
            file_size = os.path.getsize(file_path)
            # Rough estimate: 1 MB ≈ 1 minute for typical MP3 quality
            estimated_duration = file_size / (1024 * 1024) * 60
            logger.info(f"Using estimated duration for {file_path}: {estimated_duration:.1f} seconds", 
                       extra={"event": "ESTIMATED_DURATION", "file": file_path})
            return estimated_duration
        except Exception as e:
            logger.warning(f"Could not estimate duration for {file_path}: {e}", extra={"event": "DURATION_FAILED", "file": file_path})
            return None

    async def play_surah_with_retries(self, voice_client, mp3_file, max_retries=2):
        """Play a surah with retries and robust FFmpeg error handling. Also updates dynamic presence timer."""
        file_name = os.path.basename(mp3_file)
        surah_info = get_surah_from_filename(file_name)
        surah_display = get_surah_display_name(surah_info['number'])
        total_duration = self.get_audio_duration(mp3_file)
        for attempt in range(max_retries + 1):
            try:
                # Ensure previous audio is stopped
                if voice_client.is_playing():
                    voice_client.stop()
                    # Wait up to 5 seconds for audio to stop
                    for _ in range(5):
                        if not voice_client.is_playing():
                            break
                        await asyncio.sleep(1)
                    if voice_client.is_playing():
                        logger.warning(f"Previous audio did not stop in time, skipping {file_name}", extra={"event": "AUDIO", "file": file_name})
                        return False
                source = discord.FFmpegPCMAudio(mp3_file)
                voice_client.play(source)
                wait_count = 0
                max_wait = int(total_duration) if total_duration else 900
                start_time = time.time()
                # Dynamic presence update loop
                while voice_client.is_playing() and voice_client.is_connected() and wait_count < max_wait:
                    elapsed = int(time.time() - start_time)
                    # Format elapsed and total
                    elapsed_str = f"{elapsed//60}:{elapsed%60:02d}"
                    total_str = f"{int(total_duration)//60}:{int(total_duration)%60:02d}" if total_duration else "?"
                    emoji = get_surah_emoji(surah_info['number'])
                    presence_str = f"{emoji} {surah_info['english_name']} — {elapsed_str} / {total_str}"
                    activity = discord.Activity(
                        type=discord.ActivityType.listening, 
                        name=presence_str,
                        # You can add small images here if you have them
                        # large_image="quran_icon",  # Large image key
                        # small_image="playing",     # Small image key
                        # large_text=f"Listening to {surah_info['english_name']}",  # Hover text
                        # small_text="Quran Bot"     # Small image hover text
                    )
                    await self.change_presence(activity=activity)
                    # Wait 5 seconds or until playback ends
                    for _ in range(5):
                        if not voice_client.is_playing() or not voice_client.is_connected():
                            break
                        await asyncio.sleep(1)
                        wait_count += 1
                
                # Wait for playback to actually finish (FFmpeg might have terminated but audio could still be buffered)
                if voice_client.is_connected():
                    # Give a small buffer for any remaining audio
                    await asyncio.sleep(2)
                # Final update to show full duration
                if total_duration:
                    emoji = get_surah_emoji(surah_info['number'])
                    presence_str = f"{emoji} {surah_info['english_name']} — {int(total_duration)//60}:{int(total_duration)%60:02d} / {int(total_duration)//60}:{int(total_duration)%60:02d}"
                    await self.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=presence_str))
                # Additional buffer
                await asyncio.sleep(3)
                return True  # Success
            except discord.errors.ConnectionClosed as e:
                if "4006" in str(e) or "session expired" in str(e).lower():
                    # Handle session expired error
                    guild_id = voice_client.guild.id if voice_client.guild else None
                    await self.handle_voice_session_expired(guild_id)
                    return False
                else:
                    log_error(e, f"voice_connection_{file_name}", additional_data={"attempt": attempt+1})
                    self.health_monitor.record_error(e, f"voice_connection_{file_name}")
            except Exception as e:
                log_error(e, f"ffmpeg_playback_{file_name}", additional_data={"attempt": attempt+1})
                self.health_monitor.record_error(e, f"ffmpeg_playback_{file_name}")
                # Try to forcibly stop playback if stuck
                if voice_client.is_playing():
                    voice_client.stop()
                    for _ in range(5):
                        if not voice_client.is_playing():
                            break
                        await asyncio.sleep(1)
                await asyncio.sleep(2)  # Short delay before retry
        logger.error(f"FFmpeg failed for {file_name} after {max_retries+1} attempts. Skipping.", extra={"event": "FFMPEG", "file": file_name})
        return False

    async def play_quran_files(self, voice_client: discord.VoiceClient, channel: discord.VoiceChannel):
        """Play Quran MP3 files in a continuous loop with robust FFmpeg handling."""
        t0 = time.time()
        try:
            logger.info(f"Starting Quran playback in channel: {channel.name} with reciter: {self.current_reciter}", 
                       extra={'event': 'playback_start', 'channel': channel.name, 'reciter': self.current_reciter})
            
            # Get playlist based on shuffle setting
            mp3_files = self.get_shuffled_playlist()
            
            t1 = time.time()
            log_performance("audio_file_scan", t1-t0)
            if not mp3_files:
                log_error(Exception("No MP3 files found"), "play_quran_files", 
                         additional_data={"folder": Config.AUDIO_FOLDER, "reciter": self.current_reciter})
                return
            logger.info(f"Found {len(mp3_files)} audio files from reciter: {self.current_reciter}", 
                       extra={'event': 'AUDIO', 'reciter': self.current_reciter})
            
            current_index = self.state_manager.get_current_song_index()
            last_song = self.state_manager.get_current_song_name()
            if last_song and current_index < len(mp3_files):
                logger.info(f"Resuming from song {current_index}: {last_song} (Reciter: {self.current_reciter})", 
                           extra={'event': 'resume_playback', 'song_index': current_index, 'song_name': last_song, 'reciter': self.current_reciter})
            else:
                logger.info(f"Starting from beginning (Reciter: {self.current_reciter})", extra={'event': 'start_playback', 'reciter': self.current_reciter})
                current_index = 0
            self.is_streaming = True
            self.health_monitor.set_streaming_status(True)
            t2 = time.time()
            log_performance("playback_init", t2-t1)
            consecutive_failures = 0
            
            while self.is_streaming and voice_client.is_connected():
                # Handle loop mode - if enabled, play current surah repeatedly
                if self.loop_enabled and self.current_audio_file:
                    # Dedicated loop for continuous surah repetition
                    while self.loop_enabled and self.is_streaming and voice_client.is_connected() and self.current_audio_file:
                        mp3_file = os.path.join(Config.AUDIO_FOLDER, self.current_reciter, self.current_audio_file)
                        if os.path.exists(mp3_file):
                            file_name = os.path.basename(mp3_file)
                            try:
                                surah_info = get_surah_from_filename(file_name)
                                surah_display = get_surah_display_name(surah_info['number'])
                                log_audio_playback(f"{surah_display} ({file_name}) - Reciter: {self.current_reciter} [LOOP]")
                                self.state_manager.increment_songs_played()
                                self.health_monitor.update_current_song(file_name)
                                # Log surah change to Discord (loop mode)
                                await self.discord_logger.log_surah_changed(surah_info, Config.get_reciter_display_name(self.current_reciter))
                                await self.update_presence_for_surah(surah_info)
                                success = await self.play_surah_with_retries(voice_client, mp3_file)
                                if not success:
                                    consecutive_failures += 1
                                    if consecutive_failures >= 3:
                                        logger.error(f"Multiple consecutive FFmpeg failures with reciter {self.current_reciter}. Check your audio files and FFmpeg installation.", 
                                                   extra={"event": "FFMPEG", "reciter": self.current_reciter})
                                        consecutive_failures = 0
                                        # Wait before retrying
                                        await asyncio.sleep(5)
                                    continue
                                else:
                                    consecutive_failures = 0
                                # Small gap between loops for smooth transition
                                if self.is_streaming and voice_client.is_connected() and self.loop_enabled:
                                    await asyncio.sleep(1)
                            except Exception as e:
                                log_error(e, f"playing {mp3_file}")
                                self.health_monitor.record_error(e, f"audio_playback_{file_name}")
                                # Wait before retrying on error
                                await asyncio.sleep(2)
                                continue
                        else:
                            logger.warning(f"Loop file not found: {mp3_file}. Disabling loop mode.", 
                                         extra={"event": "AUDIO", "file": mp3_file})
                            self.loop_enabled = False
                            break
                    # If we exit the loop mode while, continue to normal playback
                    continue
                
                # Normal playback mode - play through playlist
                for i in range(current_index, len(mp3_files)):
                    if not self.is_streaming or not voice_client.is_connected():
                        break
                    mp3_file = mp3_files[i]
                    file_name = os.path.basename(mp3_file)
                    try:
                        surah_info = get_surah_from_filename(file_name)
                        surah_display = get_surah_display_name(surah_info['number'])
                        log_audio_playback(f"{surah_display} ({file_name}) - Reciter: {self.current_reciter}")
                        self.state_manager.set_current_song_index(i)
                        self.state_manager.set_current_song_name(file_name)
                        self.state_manager.increment_songs_played()
                        self.health_monitor.update_current_song(file_name)
                        self.current_audio_file = file_name
                        # Log surah change to Discord
                        await self.discord_logger.log_surah_changed(surah_info, Config.get_reciter_display_name(self.current_reciter))
                        await self.update_presence_for_surah(surah_info)
                        success = await self.play_surah_with_retries(voice_client, mp3_file)
                        if not success:
                            consecutive_failures += 1
                            if consecutive_failures >= 3:
                                logger.error(f"Multiple consecutive FFmpeg failures with reciter {self.current_reciter}. Check your audio files and FFmpeg installation.", 
                                           extra={"event": "FFMPEG", "reciter": self.current_reciter})
                                consecutive_failures = 0
                            continue
                        else:
                            consecutive_failures = 0
                        # Small gap between surahs for smooth transition
                        if self.is_streaming and voice_client.is_connected():
                            await asyncio.sleep(1)
                    except Exception as e:
                        log_error(e, f"playing {mp3_file}")
                        self.health_monitor.record_error(e, f"audio_playback_{file_name}")
                        continue
                        
                # Reset to beginning for next cycle (unless loop mode is enabled)
                if not self.loop_enabled:
                    current_index = 0
                    self.state_manager.set_current_song_index(0)
                if self.is_streaming:
                    await asyncio.sleep(2)
        except Exception as e:
            log_error(e, "play_quran_files")
            self.is_streaming = False
            self.health_monitor.set_streaming_status(False)
        t3 = time.time()
        log_performance("play_quran_files_total", t3-t0)
            
    async def close(self):
        """Cleanup when bot is shutting down."""
        if self.health_reporter:
            await self.health_reporter.stop()
        await super().close()

    async def update_presence_for_surah(self, surah_info):
        """Update the bot's presence to show the currently playing surah."""
        try:
            emoji = get_surah_emoji(surah_info['number'])
            activity_type = discord.ActivityType.listening
            message = f"{emoji} {surah_info['english_name']}"
            
            await self.change_presence(activity=discord.Activity(type=activity_type, name=message))
            logger.debug(f"Updated presence to: {message}")
        except Exception as e:
            log_error(e, "update_presence_for_surah")

    async def cycle_presence(self):
        """Cycle through different rich presences every 2 minutes."""
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

    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.warning(f"\n🛑 Received signal {signum}. Starting graceful shutdown...")
        asyncio.create_task(self.graceful_shutdown())
        
    async def graceful_shutdown(self):
        """Perform graceful shutdown with state saving and cleanup."""
        try:
            log_shutdown("Graceful shutdown initiated")
            
            # Stop streaming
            self.is_streaming = False
            self.health_monitor.set_streaming_status(False)
            
            # Stop health reporting
            if self.health_reporter:
                await self.health_reporter.stop()
                logger.info("Health reporting stopped")
            
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
                logger.info("Presence cycling stopped")
            
            # Disconnect from all voice channels
            for guild_id, voice_client in self._voice_clients.items():
                try:
                    if voice_client.is_connected():
                        await voice_client.disconnect()
                        logger.info(f"Disconnected from voice channel in guild {guild_id}")
                except Exception as e:
                    log_error(e, f"disconnect_voice_guild_{guild_id}")
            
            # Save final state
            if hasattr(self, 'current_audio_file') and self.current_audio_file:
                self.state_manager.set_current_song_name(self.current_audio_file)
                logger.info(f"Saved final state: {self.current_audio_file}")
            
            # Close Discord client
            await self.close()
            
            log_shutdown("Graceful shutdown completed")
            logger.info("✅ Graceful shutdown completed successfully!")
            
        except Exception as e:
            log_error(e, "graceful_shutdown")
            logger.error(f"❌ Error during shutdown: {e}")
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
            activity_type, message = next(self.presence_cycle)
            await self.change_presence(activity=discord.Activity(type=activity_type, name=message))
            logger.debug(f"Set initial presence to: {message}")
        except Exception as e:
            log_error(e, "set_presence")

def main():
    """Main entry point for the Quran Bot."""
    # Validate configuration
    if not Config.validate():
        logger.critical("❌ Configuration validation failed!")
        return
    if not Config.DISCORD_TOKEN:
        logger.critical("❌ Discord token not set in environment!")
        return
    # Create bot instance
    bot = QuranBot()
    logger.info("Starting Quran Bot...", extra={'event': 'startup'})
    try:
        bot.run(Config.DISCORD_TOKEN)
    except Exception as e:
        log_error(e, "main")
        logger.critical(f"❌ Failed to start bot: {e}")

if __name__ == "__main__":
    main() 