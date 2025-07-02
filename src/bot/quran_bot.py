"""
QuranBot - Main Discord Bot Implementation
=========================================

Core Discord bot class for 24/7 Quran streaming service.
This module contains the main QuranBot class that handles all Discord interactions,
audio streaming, command management, and bot lifecycle.

Key Features:
    - Discord voice channel management
    - Audio streaming with FFmpeg
    - Slash command system
    - Health monitoring and reporting
    - State persistence across restarts
    - Auto-reconnection and error recovery
    - Dynamic rich presence cycling
    - Graceful shutdown handling

Classes:
    QuranBot: Main Discord client class with Quran streaming capabilities

Dependencies:
    - discord.py: Discord API wrapper
    - asyncio: Asynchronous programming
    - FFmpeg: Audio processing
    - Custom utils: config, logger, health, state_manager, surah_mapper

Author: Trippixn (Discord)
License: MIT
Version: 2.1.0
"""

import discord
import asyncio
import os
import sys
import tempfile
import subprocess
from datetime import datetime
from typing import Optional, Dict, List
import time
import itertools
import signal
import aiofiles
import json

# Add src directory to Python path for module imports
# This allows importing from utils.config, utils.logger, etc.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import utility modules
from utils.config import Config
from utils.logger import (
    logger, log_bot_startup, log_audio_playback,
    log_connection_attempt, log_connection_success, log_connection_failure,
    log_health_report, log_state_save, log_state_load, log_performance,
    log_error, log_discord_event, log_ffmpeg_operation, log_security_event,
    log_retry_operation, log_shutdown, log_disconnection, track_performance
)
from utils.health import HealthMonitor
from utils.health_reporter import HealthReporter
from utils.state_manager import StateManager
from utils.surah_mapper import get_surah_from_filename, get_surah_emoji, get_surah_display_name

VOICE_JOINS_FILE = os.path.join('data', 'voice_joins.json')

class QuranBot(discord.Client):
    """
    Professional Discord bot for 24/7 Quran streaming.
    
    This class extends discord.Client to provide Quran streaming capabilities
    with comprehensive error handling, health monitoring, and state management.
    
    Attributes:
        _voice_clients (Dict[int, discord.VoiceClient]): Active voice connections
        is_streaming (bool): Current streaming status
        current_audio_file (Optional[str]): Currently playing audio file
        current_reciter (str): Active reciter folder name
        connection_failures (int): Number of consecutive connection failures
        max_connection_failures (int): Maximum allowed connection failures
        start_time (float): Bot startup timestamp for uptime calculation
        loop_enabled (bool): Whether current surah should loop
        shuffle_enabled (bool): Whether surah order should be shuffled
        original_playlist (List[str]): Original playlist for shuffle functionality
        health_monitor (HealthMonitor): Health monitoring instance
        health_reporter (Optional[HealthReporter]): Health reporting instance
        state_manager (StateManager): State persistence manager
        presence_messages (List[tuple]): Dynamic presence messages
        current_presence_index (int): Current presence message index
        presence_task (Optional[asyncio.Task]): Presence cycling task
        user_join_times (Dict[int, float]): User join times
        user_interaction_counts (Dict[int, int]): User interaction counts
        presence_locked (bool): Flag to prevent conflicts between presence update methods
        current_surah_playing (Optional[str]): Currently playing surah
    """
    
    def __init__(self):
        """
        Initialize the QuranBot Discord client.
        
        Sets up Discord intents, command tree, bot state variables,
        health monitoring, state management, and signal handlers.
        """
        # Configure Discord intents for required permissions
        intents = discord.Intents.default()
        intents.message_content = True  # Required for slash commands
        intents.voice_states = True     # Required for voice channel access

        super().__init__(intents=intents)
        
        # Initialize Discord slash command tree
        self.tree = discord.app_commands.CommandTree(self)
        
        # Bot state management
        self._voice_clients: Dict[int, discord.VoiceClient] = {}
        self.is_streaming = False
        self.current_audio_file: Optional[str] = None
        
        # User tracking for voice channel joins/leaves
        self.user_join_times: Dict[int, float] = {}
        self.user_interaction_counts: Dict[int, int] = {}
        
        # Reciter management - store folder name internally, use display name for UI
        self.current_reciter = Config.DEFAULT_RECITER
        self.current_audio_file = None
        
        # Playback control
        self.loop_enabled = False
        self.shuffle_enabled = False
        self.original_playlist = []  # Store original playlist for shuffle
        
        # Updated presence messages
        self.presence_messages = [
            (discord.ActivityType.listening, "🕋 The Holy Quran"),
            (discord.ActivityType.listening, "📖 Recitation of Allah's Words"),
            (discord.ActivityType.listening, "🕌 Beautiful Quranic Verses"),
            (discord.ActivityType.listening, "🌟 Divine Revelation"),
            (discord.ActivityType.listening, "💫 Sacred Scripture"),
            (discord.ActivityType.listening, "🕯️ Illuminating Verses"),
            (discord.ActivityType.listening, "🌙 Blessed Recitation"),
            (discord.ActivityType.listening, "✨ Words of Guidance"),
            (discord.ActivityType.listening, "🕊️ Peaceful Verses"),
            (discord.ActivityType.listening, "🎵 Melodic Quran"),
        ]
        self.current_presence_index = 0
        self.presence_cycle = self._presence_cycle()
        self.presence_task = None
        
        # Presence control flag to prevent conflicts
        self.presence_locked = False
        self.current_surah_playing = None
        
        # Connection failure tracking
        self.connection_failures = 0
        self.max_connection_failures = 5  # Stop trying after 5 consecutive failures
        self.start_time = time.time()     # For uptime calculation
        
        # Initialize monitoring and management systems
        self.health_monitor = HealthMonitor()
        self.health_reporter = None
        self.state_manager = StateManager()
        
        # Setup environment configuration
        Config.setup_environment()
        
        # Setup graceful shutdown signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)   # Ctrl+C
        signal.signal(signal.SIGTERM, self.signal_handler)  # Termination signal
        
        # Track notifications to avoid spam in loop mode
        last_notified_surah = None
        
        self.load_voice_joins()
        
    def load_voice_joins(self):
        if os.path.exists(VOICE_JOINS_FILE):
            try:
                with open(VOICE_JOINS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.user_join_times = {int(k): v for k, v in data.items()}
            except Exception as e:
                print(f"Failed to load voice joins: {e}")

    def save_voice_joins(self):
        try:
            os.makedirs(os.path.dirname(VOICE_JOINS_FILE), exist_ok=True)
            with open(VOICE_JOINS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.user_join_times, f)
        except Exception as e:
            print(f"Failed to save voice joins: {e}")

    async def send_hourly_log_task(self):
        await self.wait_until_ready()
        channel_id = 1389683881078423567
        while not self.is_closed():
            try:
                channel = self.get_channel(channel_id)
                if channel and isinstance(channel, discord.TextChannel):
                    log_path = self.get_latest_log_file()
                    if log_path:
                        async with aiofiles.open(log_path, 'r', encoding='utf-8') as f:
                            lines = await f.readlines()
                        last_lines = lines[-10:] if len(lines) > 10 else lines
                        log_content = ''.join(last_lines)
                        # Discord message limit is 2000 chars
                        for chunk in [log_content[i:i+1900] for i in range(0, len(log_content), 1900)]:
                            embed = discord.Embed(
                                title="📋 Hourly Log Report",
                                description=f"```py\n{chunk}\n```",
                                color=discord.Color.blue()
                            )
                            # Add creator as author and bot as thumbnail
                            try:
                                creator = await self.fetch_user(259725211664908288)
                                if creator and creator.avatar:
                                    embed.set_author(name=creator.display_name, icon_url=creator.avatar.url)
                            except Exception as e:
                                logger.warning(f"Failed to set creator avatar: {e}")
                            
                            if self.user and self.user.avatar:
                                embed.set_thumbnail(url=self.user.avatar.url)
                            
                            embed.set_footer(text="QuranBot Hourly Log • Auto-generated")
                            embed.timestamp = discord.utils.utcnow()
                            await channel.send(embed=embed)
                else:
                    logger.warning(f"Log channel {channel_id} not found or not a TextChannel.")
            except Exception as e:
                logger.error(f"Failed to send hourly log: {e}")
            await asyncio.sleep(3600)  # 1 hour

    def get_latest_log_file(self):
        import glob, os
        log_dir = os.path.join(os.getcwd(), 'logs')
        log_files = glob.glob(os.path.join(log_dir, '*.log'))
        if not log_files:
            return None
        return max(log_files, key=os.path.getctime)

    async def log_user_interaction(self, interaction, extra_info=None):
        channel_id = 1389683881078423567
        channel = self.get_channel(channel_id)
        user = getattr(interaction, 'user', None) or getattr(interaction, 'author', None)
        user_str = f"<@{user.id}> ({user})" if user else "Unknown user"
        content = f"User interaction: {user_str}\nCommand: {getattr(interaction, 'command', 'N/A')}\nChannel: {getattr(interaction.channel, 'name', 'N/A')}"
        if extra_info:
            content += f"\nExtra: {extra_info}"
        if user and hasattr(user, 'id') and user.id in self.user_join_times:
            # Increment interaction count for user while in voice channel
            self.user_interaction_counts[user.id] = self.user_interaction_counts.get(user.id, 0) + 1
        if channel and isinstance(channel, discord.TextChannel):
            embed = discord.Embed(
                title="👤 User Interaction Log",
                description=content,
                color=discord.Color.green()
            )
            
            # Add creator as author
            try:
                creator = await self.fetch_user(259725211664908288)
                if creator and creator.avatar:
                    embed.set_author(name=creator.display_name, icon_url=creator.avatar.url)
            except Exception as e:
                logger.warning(f"Failed to set creator avatar: {e}")
            
            # Add user avatar as thumbnail since this is a user interaction log
            if user and user.avatar:
                embed.set_thumbnail(url=user.avatar.url)
            
            if user:
                embed.add_field(name="User", value=f"<@{user.id}> ({user})", inline=True)
            embed.add_field(name="Channel", value=getattr(interaction.channel, 'name', 'N/A'), inline=True)
            embed.set_footer(text="QuranBot Interaction Logger")
            embed.timestamp = discord.utils.utcnow()
            await channel.send(embed=embed)
            
            confirmation_embed = discord.Embed(
                title="✅ Interaction Captured",
                description=f"Successfully captured interaction from {user_str}",
                color=discord.Color.blue()
            )
            
            # Add creator as author
            try:
                creator = await self.fetch_user(259725211664908288)
                if creator and creator.avatar:
                    confirmation_embed.set_author(name=creator.display_name, icon_url=creator.avatar.url)
            except Exception as e:
                logger.warning(f"Failed to set creator avatar: {e}")
            
            # Add user avatar as thumbnail since this is a user interaction log
            if user and user.avatar:
                confirmation_embed.set_thumbnail(url=user.avatar.url)
            
            if user:
                confirmation_embed.add_field(name="User", value=f"<@{user.id}> ({user})", inline=True)
            confirmation_embed.add_field(name="Status", value="Logged", inline=True)
            confirmation_embed.set_footer(text="QuranBot Interaction Logger")
            confirmation_embed.timestamp = discord.utils.utcnow()
            await channel.send(embed=confirmation_embed)
        else:
            logger.warning(f"Log channel {channel_id} not found or not a TextChannel for user interaction log.")

    async def setup_hook(self):
        """
        Discord.py setup hook for bot initialization.
        
        This method is called during bot startup and is responsible for:
        - Loading all slash command extensions (cogs)
        - Syncing the command tree with Discord
        - Performance monitoring of the setup process
        
        The setup process loads commands from the following categories:
        - Admin commands: restart, status, skip, reconnect, credits
        - User commands: control_panel
        - Utility commands: logs
        """
        t0 = time.time()
        logger.info("Setting up Quran Bot...", extra={'event': 'STARTUP'})
        
        # Define all command extensions to load
        commands_to_load = [
            'src.cogs.admin_commands.restart',
            'src.cogs.admin_commands.status',
            'src.cogs.admin_commands.skip',
            'src.cogs.admin_commands.reconnect',
            'src.cogs.admin_commands.credits',
            'src.cogs.utility_commands.logs',
            'src.cogs.user_commands.control_panel'
        ]
        
        # Load each command extension
        for command in commands_to_load:
            try:
                await self.load_extension(command)
                logger.info(f"Command loaded successfully: {command}", extra={'event': 'COMMAND_LOAD'})
            except Exception as e:
                logger.error(f"Failed to load command {command}: {e}", extra={'event': 'COMMAND_LOAD_ERROR'})
        
        # Sync command tree with Discord to register slash commands
        try:
            await self.tree.sync()
            logger.info("Command tree synced successfully", extra={'event': 'COMMAND_SYNC'})
        except Exception as e:
            logger.error(f"Failed to sync command tree: {e}", extra={'event': 'COMMAND_SYNC_ERROR'})
        
        t1 = time.time()
        log_performance("setup_hook", t1-t0)
        await super().setup_hook()
        # Start background log sender
        self.bg_log_task = asyncio.create_task(self.send_hourly_log_task())
    
    async def load_extension(self, extension_name: str):
        """
        Load a Discord.py cog extension.
        
        Args:
            extension_name (str): The module path to the extension (e.g., 'src.cogs.admin_commands.restart')
            
        Raises:
            Exception: If the extension fails to load or doesn't have a setup function
        """
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
        
    async def on_ready(self):
        """
        Discord.py event handler called when the bot is ready.
        
        This method is called once the bot has successfully connected to Discord
        and is ready to handle events. It performs the following initialization:
        
        - Logs bot startup information
        - Sets up dynamic rich presence cycling
        - Initializes health monitoring and reporting
        - Sets up state management
        - Attempts to join the target voice channel
        - Starts presence cycling task
        
        The method includes comprehensive performance monitoring for each
        initialization step to help identify bottlenecks.
        """
        t0 = time.time()
        if self.user:
            # Log successful bot startup
            log_bot_startup(self.user.name, self.user.id)
            log_discord_event("ready", {"guilds": len(self.guilds)})
            t1 = time.time()
            log_performance("discord_ready", t1-t0)
            
            # Initialize dynamic rich presence system
            self.presence_messages = [
                (discord.ActivityType.listening, "�� The Holy Quran"),
                (discord.ActivityType.listening, "📖 Recitation of Allah's Words"),
                (discord.ActivityType.listening, "🕌 Beautiful Quranic Verses"),
                (discord.ActivityType.listening, "🌟 Divine Revelation"),
                (discord.ActivityType.listening, "💫 Sacred Scripture"),
                (discord.ActivityType.listening, "🕯️ Illuminating Verses"),
                (discord.ActivityType.listening, "🌙 Blessed Recitation"),
                (discord.ActivityType.listening, "✨ Words of Guidance"),
                (discord.ActivityType.listening, "🕊️ Peaceful Verses"),
                (discord.ActivityType.listening, "🎵 Melodic Quran"),
            ]
            self.current_presence_index = 0
            self.presence_cycle = self._presence_cycle()
            await self.set_presence()
            
            # Start background task for presence cycling
            self.presence_task = asyncio.create_task(self.cycle_presence())
            
            # Initialize health monitoring and reporting system
            self.health_reporter = HealthReporter(self, self.health_monitor, Config.LOGS_CHANNEL_ID)
            await self.health_reporter.start()
            
            # Initialize state management system
            self.state_manager = StateManager()
            
            # Attempt to find and join the target voice channel
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
            
            # Log health monitoring initialization
            logger.info("Bot health monitoring initialized", extra={'event': 'HEALTH'})
            logger.info("DEBUG: About to initialize state management", extra={'event': 'DEBUG_STATE_INIT'})
            
            # Initialize state management and track bot starts
            self.state_manager.increment_bot_start_count()
            start_count = self.state_manager.get_bot_start_count()
            log_state_load("bot_start_count", {"start_count": start_count})
            t4 = time.time()
            log_performance("state_manager_init", t4-t3)
            
            logger.info("Health reporting started", extra={'event': 'HEALTH'})
            t5 = time.time()
            log_performance("health_reporter_start", t5-t4)
        
    async def find_and_join_channel(self):
        """
        Find and join the target voice channel.
        
        This method searches through all guilds the bot is in to find the
        configured target voice channel. If found and auto-connection is enabled,
        it will attempt to start streaming. If not found, it logs an error.
        
        The method includes performance monitoring to track how long the
        search and connection process takes.
        """
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
        # Handle user joins and leaves (excluding bot itself)
        if member and hasattr(member, 'id') and self.user and hasattr(self.user, 'id') and member.id != self.user.id:
            current_time = time.time()
            target_channel_id = 1389675580253016144
            # User joins the Quran channel (from anywhere)
            if (after.channel and after.channel.id == target_channel_id) and (not before.channel or before.channel.id != target_channel_id):
                self.user_join_times[member.id] = current_time
                self.save_voice_joins()
                logger.info(f"User joined voice channel: {member.display_name} ({member.id}) joined {after.channel.name} in {after.channel.guild.name}", 
                           extra={'event': 'USER_JOIN', 'user_id': member.id, 'user_name': member.display_name, 
                                 'channel_name': after.channel.name, 'guild_name': after.channel.guild.name})
                await self.log_user_voice_activity(member, "joined", after.channel)
            # User leaves the Quran channel (by disconnecting or moving to another channel)
            elif (before.channel and before.channel.id == target_channel_id) and (not after.channel or after.channel.id != target_channel_id):
                join_time = self.user_join_times.get(member.id)
                duration = None
                if join_time:
                    duration = current_time - join_time
                    del self.user_join_times[member.id]
                    self.save_voice_joins()
                interaction_count = self.user_interaction_counts.get(member.id, 0)
                if member.id in self.user_interaction_counts:
                    del self.user_interaction_counts[member.id]
                duration_str = self.format_duration(duration) if duration else "Unknown duration"
                logger.info(f"User left voice channel: {member.display_name} ({member.id}) left {before.channel.name} in {before.channel.guild.name} - Stayed for {duration_str} | Interactions: {interaction_count}", 
                           extra={'event': 'USER_LEAVE', 'user_id': member.id, 'user_name': member.display_name, 
                                 'channel_name': before.channel.name, 'guild_name': before.channel.guild.name, 'duration': duration, 'interactions': interaction_count})
                await self.log_user_voice_activity(member, "left", before.channel, duration, interaction_count=interaction_count)
        # Handle bot voice state changes (existing logic)
        if self.user and member and member.id == self.user.id:
            if before.channel and not after.channel:
                # Bot was disconnected from voice channel
                log_disconnection(before.channel.name, "Disconnected from voice channel")
                self.is_streaming = False
                self.health_monitor.set_streaming_status(False)
                # Increment connection failure counter
                self.connection_failures += 1
                if self.connection_failures >= self.max_connection_failures:
                    logger.error(f"Too many connection failures ({self.connection_failures}). Stopping reconnection attempts.", 
                               extra={'event': 'CONNECTION_FAILURE_LIMIT'})
                    self.is_streaming = False
                    return
                # Implement progressive delay to prevent rapid reconnection loops
                wait_time = min(60 * self.connection_failures, 300)  # Progressive delay up to 5 minutes
                logger.info(f"Waiting {wait_time} seconds before reconnection attempt {self.connection_failures}/{self.max_connection_failures}...", 
                           extra={'event': 'RECONNECT_WAIT', 'wait_time': wait_time, 'failures': self.connection_failures})
                await asyncio.sleep(wait_time)
                if self.is_streaming:
                    logger.info("Attempting to reconnect after disconnection...", 
                               extra={'event': 'RECONNECT_ATTEMPT'})
                    await self.find_and_join_channel()
            elif not before.channel and after.channel:
                # Bot connected to voice
                log_connection_success(after.channel.name, after.channel.guild.name)
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

    async def on_disconnect(self):
        """Handle bot disconnection with enhanced recovery."""
        log_disconnection("Discord", "Bot disconnected from Discord")
        self.is_streaming = False
        self.health_monitor.set_streaming_status(False)
        
        # Unlock presence when streaming stops
        self.presence_locked = False
        self.current_surah_playing = None
        logger.debug("Unlocked presence after streaming stopped")
        
        # Start automatic reconnection after a delay
        logger.info("Bot disconnected from Discord. Starting automatic reconnection in 30 seconds...", 
                   extra={'event': 'AUTO_RECONNECT'})
        asyncio.create_task(self.auto_reconnect_after_disconnect())
    
    async def auto_reconnect_after_disconnect(self):
        """Automatically attempt to reconnect after Discord disconnection."""
        await asyncio.sleep(30)  # Wait 30 seconds before attempting reconnection
        
        if not self.is_ready():
            logger.info("Bot not ready yet, waiting for reconnection...", 
                       extra={'event': 'WAITING_FOR_READY'})
            return
        
        logger.info("Attempting automatic reconnection to Discord...", 
                   extra={'event': 'AUTO_RECONNECT_ATTEMPT'})
        
        # Try to reconnect to voice channel
        try:
            await self.find_and_join_channel()
        except Exception as e:
            logger.error(f"Auto-reconnection failed: {e}", 
                        extra={'event': 'AUTO_RECONNECT_FAILED'})
            # Try again in 5 minutes
            asyncio.create_task(self.retry_reconnection_later())
    
    async def retry_reconnection_later(self):
        """Retry reconnection after a longer delay."""
        await asyncio.sleep(300)  # Wait 5 minutes
        if self.is_ready() and not self.is_streaming:
            logger.info("Retrying reconnection after delay...", 
                       extra={'event': 'RETRY_RECONNECTION'})
            try:
                await self.find_and_join_channel()
            except Exception as e:
                logger.error(f"Retry reconnection failed: {e}", 
                            extra={'event': 'RETRY_RECONNECT_FAILED'})

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
    
    def toggle_loop(self) -> bool:
        """Toggle loop mode for current surah."""
        self.loop_enabled = not self.loop_enabled
        logger.info(f"Loop mode {'enabled' if self.loop_enabled else 'disabled'}", 
                   extra={'event': 'LOOP_TOGGLE', 'loop_enabled': self.loop_enabled})
        return self.loop_enabled
    
    def toggle_shuffle(self) -> bool:
        """Toggle shuffle mode for surah order."""
        self.shuffle_enabled = not self.shuffle_enabled
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
                    )
                    # Only update if not locked by another process
                    if not self.presence_locked or self.current_surah_playing == surah_info['english_name']:
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
                
                # Unlock presence when this surah finishes
                if self.current_surah_playing == surah_info['english_name']:
                    self.presence_locked = False
                    self.current_surah_playing = None
                    logger.debug(f"Unlocked presence after finishing {surah_info['english_name']}")
                
                # Send Discord notification for surah change
                asyncio.create_task(self.send_surah_change_notification(
                    surah_info, 
                    Config.get_reciter_display_name(self.current_reciter), 
                    voice_client.channel
                ))
                
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
        # Unlock presence if this was the current surah
        if self.current_surah_playing == surah_info['english_name']:
            self.presence_locked = False
            self.current_surah_playing = None
            logger.debug(f"Unlocked presence after FFmpeg failure for {surah_info['english_name']}")
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
            last_successful_playback = time.time()
            
            # Track notifications to avoid spam in loop mode
            last_notified_surah = None
            
            # Start health monitoring task
            health_task = asyncio.create_task(self.monitor_playback_health(voice_client, last_successful_playback))
            
            while self.is_streaming and voice_client.is_connected():
                # Handle loop mode - if enabled, play current surah repeatedly
                if self.loop_enabled and self.current_audio_file:
                    mp3_file = os.path.join(Config.AUDIO_FOLDER, self.current_reciter, self.current_audio_file)
                    if os.path.exists(mp3_file):
                        file_name = os.path.basename(mp3_file)
                        try:
                            surah_info = get_surah_from_filename(file_name)
                            surah_display = get_surah_display_name(surah_info['number'])
                            log_audio_playback(f"{surah_display} ({file_name}) - Reciter: {self.current_reciter} [LOOP]")
                            self.state_manager.increment_songs_played()
                            self.health_monitor.update_current_song(file_name)
                            await self.update_presence_for_surah(surah_info)
                            
                            # Send Discord notification for surah change (only once per surah in loop mode)
                            if last_notified_surah != surah_info['number']:
                                asyncio.create_task(self.send_surah_change_notification(
                                    surah_info, 
                                    Config.get_reciter_display_name(self.current_reciter), 
                                    channel
                                ))
                                last_notified_surah = surah_info['number']
                            
                            success = await self.play_surah_with_retries(voice_client, mp3_file)
                            if success:
                                last_successful_playback = time.time()
                                consecutive_failures = 0
                            else:
                                consecutive_failures += 1
                                if consecutive_failures >= 3:
                                    logger.error(f"Multiple consecutive FFmpeg failures with reciter {self.current_reciter}. Check your audio files and FFmpeg installation.", 
                                               extra={"event": "FFMPEG", "reciter": self.current_reciter})
                                    consecutive_failures = 0
                                continue
                            # Small gap between loops for smooth transition
                            if self.is_streaming and voice_client.is_connected():
                                await asyncio.sleep(1)
                            continue  # Continue looping the same surah
                        except Exception as e:
                            log_error(e, f"playing {mp3_file}")
                            self.health_monitor.record_error(e, f"audio_playback_{file_name}")
                            consecutive_failures += 1
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
                        await self.update_presence_for_surah(surah_info)
                        
                        # Send Discord notification for surah change
                        asyncio.create_task(self.send_surah_change_notification(
                            surah_info, 
                            Config.get_reciter_display_name(self.current_reciter), 
                            channel
                        ))
                        
                        success = await self.play_surah_with_retries(voice_client, mp3_file)
                        if success:
                            last_successful_playback = time.time()
                            consecutive_failures = 0
                        else:
                            consecutive_failures += 1
                            if consecutive_failures >= 3:
                                logger.error(f"Multiple consecutive FFmpeg failures with reciter {self.current_reciter}. Check your audio files and FFmpeg installation.", 
                                           extra={"event": "FFMPEG", "reciter": self.current_reciter})
                                consecutive_failures = 0
                            continue
                        # Small gap between surahs for smooth transition
                        if self.is_streaming and voice_client.is_connected():
                            await asyncio.sleep(1)
                    except Exception as e:
                        log_error(e, f"playing {mp3_file}")
                        self.health_monitor.record_error(e, f"audio_playback_{file_name}")
                        consecutive_failures += 1
                        continue
                        
                # Reset to beginning for next cycle (unless loop mode is enabled)
                if not self.loop_enabled:
                    current_index = 0
                    self.state_manager.set_current_song_index(0)
                if self.is_streaming:
                    await asyncio.sleep(2)
            
            # Cancel health monitoring task
            health_task.cancel()
            
        except Exception as e:
            log_error(e, "play_quran_files")
            self.is_streaming = False
            self.health_monitor.set_streaming_status(False)
        t3 = time.time()
        log_performance("play_quran_files_total", t3-t0)
    
    async def monitor_playback_health(self, voice_client, last_successful_playback):
        """Monitor playback health and restart if needed."""
        while self.is_streaming and voice_client.is_connected():
            await asyncio.sleep(60)  # Check every minute
            
            # If no successful playback in 30 minutes, restart playback
            if time.time() - last_successful_playback > 1800:  # 30 minutes
                logger.warning("No successful audio playback in 30 minutes. Restarting playback...", 
                              extra={'event': 'PLAYBACK_HEALTH_RESTART'})
                try:
                    # Restart playback
                    self.is_streaming = False
                    await asyncio.sleep(5)
                    self.is_streaming = True
                    asyncio.create_task(self.play_quran_files(voice_client, voice_client.channel))
                    break
                except Exception as e:
                    logger.error(f"Failed to restart playback: {e}", 
                               extra={'event': 'PLAYBACK_RESTART_FAILED'})

    async def close(self):
        """
        Cleanup method called when the bot is shutting down.
        
        Stops health reporting and calls the parent class close method
        to properly clean up Discord client resources.
        """
        if self.health_reporter:
            await self.health_reporter.stop()
        await super().close()

    async def send_surah_change_notification(self, surah_info, reciter_name, channel=None):
        """
        Send a Discord embed notification when the bot changes surahs.
        
        Args:
            surah_info (dict): Dictionary containing surah information
            reciter_name (str): Name of the current reciter
            channel (discord.VoiceChannel, optional): Voice channel the bot is connected to
        """
        try:
            from utils.config import Config
            
            logs_channel = self.get_channel(Config.LOGS_CHANNEL_ID)
            if not logs_channel or not isinstance(logs_channel, discord.TextChannel):
                return
            
            emoji = get_surah_emoji(surah_info['number'])
            
            # Create embed
            embed = discord.Embed(
                title=f"🎵 Now Playing",
                description=f"{emoji} **{surah_info['english_name']}**",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="📖 Surah",
                value=f"#{surah_info['number']:03d} - {surah_info['english_name']}",
                inline=True
            )
            
            embed.add_field(
                name="🎤 Reciter",
                value=reciter_name,
                inline=True
            )
            
            if channel and hasattr(channel, 'name'):
                embed.add_field(
                    name="🔊 Voice Channel",
                    value=channel.name,
                    inline=True
                )
            
            embed.add_field(
                name="📈 Progress",
                value=f"Surah {self.state_manager.get_current_song_index() + 1} of {len(self.get_audio_files())}",
                inline=False
            )
            
            # Add creator as author and bot as thumbnail
            try:
                creator = await self.fetch_user(259725211664908288)
                if creator and hasattr(creator, 'avatar') and creator.avatar:
                    embed.set_author(name=creator.display_name, icon_url=creator.avatar.url)
            except Exception as e:
                logger.debug(f"Could not fetch creator for surah notification: {e}")
            
            if self.user and hasattr(self.user, 'avatar') and self.user.avatar:
                embed.set_thumbnail(url=self.user.avatar.url)
            
            embed.set_footer(text=f"QuranBot • {datetime.now().strftime('%m-%d | %I:%M:%S %p')}")
            
            await logs_channel.send(embed=embed)
            logger.debug(f"Sent surah change notification for {surah_info['english_name']}")
            
        except Exception as e:
            logger.error(f"Failed to send surah change notification: {e}")

    async def update_presence_for_surah(self, surah_info):
        """
        Update the bot's Discord presence to show the currently playing surah.
        
        Args:
            surah_info (dict): Dictionary containing surah information including
                             'number' and 'english_name'
        """
        try:
            # Lock presence updates to prevent conflicts
            self.presence_locked = True
            self.current_surah_playing = surah_info['english_name']
            
            emoji = get_surah_emoji(surah_info['number'])
            activity_type = discord.ActivityType.listening
            message = f"{emoji} {surah_info['english_name']}"
            
            await self.change_presence(activity=discord.Activity(type=activity_type, name=message))
            logger.debug(f"Updated presence to: {message}")
        except Exception as e:
            log_error(e, "update_presence_for_surah")
        finally:
            # Keep locked while surah is playing
            pass

    async def cycle_presence(self):
        """
        Background task that cycles through different rich presences every 2 minutes.
        
        This method runs continuously and updates the bot's Discord presence
        to show either the currently playing surah or general Quran-related messages.
        """
        while True:
            try:
                # Only update if not locked (no surah currently playing)
                if not self.presence_locked:
                    # Fallback to cycling through general messages
                    activity_type, message = next(self.presence_cycle)
                    await self.change_presence(activity=discord.Activity(type=activity_type, name=message))
                    logger.debug(f"Cycled presence to: {message}")
                else:
                    logger.debug(f"Presence locked, skipping cycle (playing: {self.current_surah_playing})")
                
                await asyncio.sleep(120)  # 2 minutes
            except Exception as e:
                log_error(e, "cycle_presence")
                await asyncio.sleep(120)  # Continue cycling even if there's an error

    def signal_handler(self, signum, frame):
        """
        Handle shutdown signals gracefully.
        
        This method is called when the bot receives SIGINT (Ctrl+C) or SIGTERM.
        It initiates a graceful shutdown process to clean up resources properly.
        
        Args:
            signum: The signal number received
            frame: The current stack frame
        """
        print(f"\n🛑 Received signal {signum}. Starting graceful shutdown...")
        asyncio.create_task(self.graceful_shutdown())
        
    async def graceful_shutdown(self):
        """
        Perform graceful shutdown with comprehensive cleanup.
        
        This method ensures all resources are properly cleaned up when the bot
        is shutting down, including:
        - Stopping audio streaming
        - Stopping health reporting
        - Cancelling background tasks
        - Disconnecting from voice channels
        - Saving final state
        - Closing Discord client
        """
        try:
            log_shutdown("Graceful shutdown initiated")
            
            # Stop streaming and update health status
            self.is_streaming = False
            self.health_monitor.set_streaming_status(False)
            
            # Unlock presence when streaming stops
            self.presence_locked = False
            self.current_surah_playing = None
            logger.debug("Unlocked presence after streaming stopped")
            
            # Stop health reporting system
            if self.health_reporter:
                await self.health_reporter.stop()
                logger.info("Health reporting stopped")
            
            # Stop presence cycling task
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
            
            # Save final state for next startup
            if hasattr(self, 'current_audio_file') and self.current_audio_file:
                self.state_manager.set_current_song_name(self.current_audio_file)
                logger.info(f"Saved final state: {self.current_audio_file}")
            
            # Close Discord client
            await self.close()
            
            log_shutdown("Graceful shutdown completed")
            print("✅ Graceful shutdown completed successfully!")
            
        except Exception as e:
            log_error(e, "graceful_shutdown")
            print(f"❌ Error during shutdown: {e}")
        finally:
            # Force exit after cleanup
            sys.exit(0)

    def _presence_cycle(self):
        """
        Generator for cycling through presence messages.
        
        Returns:
            Generator that yields tuples of (activity_type, message) for
            Discord presence updates.
        """
        while True:
            for activity_type, message in self.presence_messages:
                yield activity_type, message

    async def set_presence(self):
        """
        Set initial presence for the bot.
        
        Called during startup to set the bot's initial Discord presence
        before the cycling begins.
        """
        try:
            activity_type, message = next(self.presence_cycle)
            await self.change_presence(activity=discord.Activity(type=activity_type, name=message))
            logger.debug(f"Set initial presence to: {message}")
        except Exception as e:
            log_error(e, "set_presence")

    def format_duration(self, duration_seconds: float) -> str:
        """Format duration in seconds to a human-readable string."""
        if duration_seconds is None:
            return "Unknown duration"
        
        if duration_seconds < 60:
            return f"{int(duration_seconds)} seconds"
        elif duration_seconds < 3600:
            minutes = int(duration_seconds // 60)
            seconds = int(duration_seconds % 60)
            return f"{minutes}m {seconds}s"
        else:
            hours = int(duration_seconds // 3600)
            minutes = int((duration_seconds % 3600) // 60)
            return f"{hours}h {minutes}m"

    async def log_user_voice_activity(self, member, action: str, channel, duration: Optional[float] = None, from_channel=None, interaction_count: Optional[int] = None):
        """Log user voice activity to Discord channel."""
        channel_id = 1389683881078423567
        log_channel = self.get_channel(channel_id)
        if not log_channel or not isinstance(log_channel, discord.TextChannel):
            return
        # Determine color and title based on action
        if action == "joined":
            color = discord.Color.green()
            title = "User Joined Voice Channel"
        elif action == "left":
            color = discord.Color.red()
            title = "User Left Voice Channel"
        else:
            color = discord.Color.blue()
            title = "User Voice Channel Activity"
        embed = discord.Embed(
            title=title,
            color=color,
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="User", value=f"<@{member.id}>", inline=True)
        embed.add_field(name="User ID", value=str(member.id), inline=True)
        embed.add_field(name="Channel", value=channel.name, inline=True)
        embed.add_field(name="Server", value=channel.guild.name, inline=True)
        if action == "left" and duration is not None:
            embed.add_field(name="Duration", value=self.format_duration(duration), inline=True)
        if action == "left" and interaction_count is not None:
            embed.add_field(name="Interactions", value=str(interaction_count), inline=True)
        embed.set_footer(text="QuranBot Voice Activity Logger • Professional Log")
        
        # Add creator as author
        try:
            creator = await self.fetch_user(259725211664908288)
            if creator and creator.avatar:
                embed.set_author(name=creator.display_name, icon_url=creator.avatar.url)
        except Exception as e:
            logger.warning(f"Failed to set creator avatar: {e}")
        
        # Set user avatar as thumbnail
        if member and member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        
        try:
            await log_channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to send voice activity log to Discord: {e}")

def main():
    """
    Main entry point for the QuranBot Discord application.
    
    This function:
    1. Validates the configuration
    2. Creates a QuranBot instance
    3. Starts the bot with the Discord token
    4. Handles any startup errors
    
    The bot will run continuously until interrupted or an error occurs.
    """
    # Validate configuration before starting
    if not Config.validate():
        print("❌ Configuration validation failed!")
        return
    
    # Check for required Discord token
    if not Config.DISCORD_TOKEN:
        print("❌ Discord token not set in environment!")
        return
    
    # Create and start the bot instance
    bot = QuranBot()
    logger.info("Starting Quran Bot...", extra={'event': 'startup'})
    
    try:
        bot.run(Config.DISCORD_TOKEN)
    except Exception as e:
        log_error(e, "main")
        print(f"❌ Failed to start bot: {e}")

if __name__ == "__main__":
    main() 