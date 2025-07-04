"""
Main Discord Quran Bot implementation.
Professional 24/7 Quran streaming bot with local audio support.

This module contains the core QuranBot class that handles:
- Discord bot initialization and management
- Voice channel connections and audio streaming
- Playlist management (loop, shuffle, etc.)
- Health monitoring and reporting
- State management and persistence
- Backup operations
- Error handling and recovery
- Performance tracking and logging

Features:
    - 24/7 Quran audio streaming
    - Multiple reciter support
    - Loop and shuffle playback modes
    - Automatic reconnection on disconnection
    - Comprehensive health monitoring
    - State persistence and backup
    - Graceful shutdown handling
    - Performance tracking and logging
    - Instance cleanup to prevent duplicates

Author: John (Discord: Trippxin)
Version: 2.0.0
"""

import discord
from discord.ext import commands
import asyncio
import os
import sys
import tempfile
import subprocess
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
import time
import itertools
import signal
import psutil
import traceback
from pathlib import Path

# Add src to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config.config import Config
from monitoring.logging.logger import (
    logger,
    log_bot_startup,
    log_audio_playback,
    log_connection_attempt,
    log_connection_success,
    log_connection_failure,
    log_health_report,
    log_state_save,
    log_state_load,
    log_performance,
    log_error,
    log_discord_event,
    log_ffmpeg_operation,
    log_security_event,
    log_retry_operation,
    log_shutdown,
    log_disconnection,
    track_performance,
    log_tree_start,
    log_tree_item,
    log_tree_end,
)
from monitoring.health.health import HealthMonitor
from monitoring.health.health_reporter import HealthReporter
from monitoring.logging.discord_logger import DiscordEmbedLogger
from core.state.state_manager import StateManager
from core.state.backup_manager import BackupManager
from core.mapping.surah_mapper import (
    get_surah_from_filename,
    get_surah_emoji,
    get_surah_display_name,
)
from monitoring.logging.log_helpers import (
    log_async_function_call,
    log_function_call,
    log_operation,
    get_system_metrics,
    get_discord_context,
    get_bot_state,
)


def cleanup_existing_instances():
    """
    Kill any existing instances of the Quran bot specifically.

    This function ensures only one instance of the Quran bot is running
    by terminating any existing processes that match our criteria.

    Safety Features:
    - Only targets processes in the specific Quran bot directory
    - Excludes the current process
    - Uses graceful termination first, then force kill if needed
    - Comprehensive error handling and logging
    """
    current_pid = os.getpid()
    killed_count = 0

    try:
        logger.info("🔍 Checking for existing Quran bot instances...")

        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                # Check if this is a Python process running our specific Quran bot
                if (
                    proc.info["name"] == "python"
                    and proc.info["cmdline"]
                    and "run.py" in " ".join(proc.info["cmdline"])
                    and "/home/QuranAudioBot"
                    in " ".join(proc.info["cmdline"])  # Only Quran bot directory
                    and proc.info["pid"] != current_pid
                ):

                    logger.info(
                        f"🔫 Killing existing Quran bot instance (PID: {proc.info['pid']})"
                    )
                    proc.terminate()
                    killed_count += 1

                    # Wait a moment for graceful shutdown
                    try:
                        proc.wait(timeout=5)
                        logger.info(
                            f"✅ Successfully terminated Quran bot instance (PID: {proc.info['pid']})"
                        )
                    except psutil.TimeoutExpired:
                        logger.warning(
                            f"⚠️ Force killing Quran bot instance (PID: {proc.info['pid']})"
                        )
                        proc.kill()
                        logger.info(
                            f"✅ Force killed Quran bot instance (PID: {proc.info['pid']})"
                        )

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
            ) as e:
                logger.debug(f"Skipping process {proc.info.get('pid', 'unknown')}: {e}")
                continue

        if killed_count > 0:
            logger.info(f"🧹 Cleaned up {killed_count} existing Quran bot instance(s)")
            time.sleep(2)  # Give time for cleanup
        else:
            logger.info("✅ No existing Quran bot instances found")

    except Exception as e:
        logger.error(f"❌ Error during Quran bot instance cleanup: {e}")
        logger.error(f"🔍 Full traceback: {traceback.format_exc()}")


class QuranBot(commands.Bot):
    """
    Professional Discord bot for 24/7 Quran streaming.

    This class provides a comprehensive Discord bot implementation for
    continuous Quran audio streaming with advanced features including:

    Core Features:
        - 24/7 audio streaming with multiple reciters
        - Automatic reconnection and error recovery
        - Playlist management (loop, shuffle, etc.)
        - Health monitoring and reporting
        - State persistence and backup
        - Performance tracking and logging

    Advanced Features:
        - Graceful shutdown handling
        - Instance cleanup to prevent duplicates
        - Comprehensive error handling
        - Real-time health monitoring
        - Automated backup operations
        - Performance metrics collection

    Attributes:
        start_time (datetime): When the bot started
        is_streaming (bool): Current streaming status
        loop_enabled (bool): Loop playback mode status
        shuffle_enabled (bool): Shuffle playback mode status
        current_audio_file (str): Currently playing audio file
        current_reciter (str): Currently selected reciter
        connection_failures (int): Number of consecutive connection failures
        max_connection_failures (int): Maximum allowed connection failures
        playback_start_time (datetime): When current playback started
        health_monitor (HealthMonitor): Health monitoring instance
        discord_logger (DiscordEmbedLogger): Discord logging instance
        state_manager (StateManager): State management instance
        backup_manager (BackupManager): Backup management instance
    """

    def __init__(self):
        """
        Initialize the QuranBot with enhanced error handling and monitoring.

        This method sets up all necessary components for the bot including:
        - Discord client initialization
        - Component initialization (health, logging, state, backup)
        - Environment setup and validation
        - Signal handling for graceful shutdown
        - Default configuration setup

        Raises:
            Exception: If critical initialization fails
        """
        try:
            logger.info("🚀 Initializing QuranBot...")

            # Clean up any existing instances first
            cleanup_existing_instances()

            # Initialize base client with all intents
            intents = discord.Intents.all()
            super().__init__(command_prefix="!", intents=intents)

            # Bot state initialization
            self.start_time = datetime.now()  # Track when the bot starts
            self.is_streaming = False
            self.loop_enabled = False
            self.shuffle_enabled = False
            self.current_audio_file = None
            self.current_reciter = None
            self._voice_clients = {}
            self._was_streaming_before_disconnect = False
            self.connection_failures = 0
            self.max_connection_failures = (
                5  # Maximum number of consecutive failures before giving up
            )
            self.playback_start_time = None

            # Command tree is automatically created by commands.Bot

            # Initialize bot state
            self.current_song_index = 0
            self._intended_streaming = False  # Track if we want to be streaming
            self.original_playlist = []  # Store original order for shuffle

            # Connection management
            self.connection_failures = 0
            self.max_connection_failures = 5

            # Initialize components with error handling
            try:
                self.health_monitor = HealthMonitor()  # Initialize immediately
                logger.info("✅ Health monitor initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize health monitor: {e}")
                raise

            try:
                self.discord_logger = DiscordEmbedLogger(
                    self,
                    Config.LOGS_CHANNEL_ID,  # Use channel ID from config
                    Config.TARGET_CHANNEL_ID,  # Use target VC ID from config
                )
                logger.info("✅ Discord logger initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Discord logger: {e}")
                raise

            try:
                self.state_manager = StateManager("data/bot_state.json")  # Use data directory for state
                logger.info("✅ State manager initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize state manager: {e}")
                raise

            try:
                self.backup_manager = BackupManager()  # Initialize backup manager
                logger.info("✅ Backup manager initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize backup manager: {e}")
                raise

            # Initialize backup task as None
            self.backup_task = None

            # Health checks tracking
            self.health_checks = {
                "failed": [],  # List of failed checks
                "last_check": None,  # Timestamp of last check
                "status": "Not Started",  # Overall status
            }

            # Health reporting
            self.health_reporter = None  # Will be initialized in setup_hook

            # Setup environment
            try:
                Config.setup_environment()
                logger.info("✅ Environment setup completed")
            except Exception as e:
                logger.error(f"❌ Environment setup failed: {e}")
                raise

            # Setup graceful shutdown
            try:
                signal.signal(signal.SIGINT, self.signal_handler)
                signal.signal(signal.SIGTERM, self.signal_handler)
                logger.info("✅ Signal handlers configured")
            except Exception as e:
                logger.error(f"❌ Failed to setup signal handlers: {e}")
                raise

            # Set a default reciter to ensure select menus have options
            try:
                # Always set Saad Al Ghamdi as default reciter on startup
                self.set_current_reciter("Saad Al Ghamdi")
                logger.info("✅ Default reciter set")
            except Exception as e:
                logger.warning(f"⚠️ Failed to set default reciter: {e}")

            self._voice_clients = {}

            logger.info("✅ QuranBot initialization completed successfully")

        except Exception as e:
            logger.error(f"❌ QuranBot initialization failed: {e}")
            logger.error(f"🔍 Full traceback: {traceback.format_exc()}")
            raise

    async def setup_hook(self):
        """
        Setup hook for bot initialization.

        This method is called during bot startup and handles:
        - Health checks and system validation
        - Command loading and synchronization
        - Log cleanup system initialization
        - Backup task startup
        - Performance monitoring setup

        The method includes comprehensive error handling and logging
        for each initialization step to ensure reliable startup.
        """
        t0 = time.time()
        logger.info("🔧 Setting up Quran Bot...", extra={"event": "STARTUP"})

        # Run initial health checks with enhanced error handling
        try:
            logger.info("🏥 Running initial health checks...")
            self.health_checks["status"] = "Running"
            self.health_checks["last_check"] = datetime.now()

            # Comprehensive health checks
            checks = [
                ("Audio Files", os.path.exists("audio")),
                ("Config", hasattr(Config, "DEFAULT_RECITER")),
                ("Permissions", os.access("audio", os.R_OK)),
                ("FFmpeg", self._check_ffmpeg()),
                ("Data Directory", os.path.exists("data")),
                ("Logs Directory", os.path.exists("logs")),
            ]

            self.health_checks["failed"] = [
                name for name, passed in checks if not passed
            ]
            self.health_checks["status"] = (
                "OK" if not self.health_checks["failed"] else "Issues Found"
            )

            if self.health_checks["failed"]:
                logger.warning(
                    f"⚠️ Health check issues found: {self.health_checks['failed']}"
                )
            else:
                logger.info("✅ All health checks passed")

            logger.info(f"🏥 Health checks completed: {self.health_checks['status']}")

        except Exception as e:
            logger.error(f"❌ Failed to run health checks: {e}")
            logger.error(f"🔍 Health check error traceback: {traceback.format_exc()}")
            self.health_checks["status"] = "Error"
            self.health_checks["failed"].append("Health Check System")

        # Load individual command files with enhanced error handling
        logger.info("📦 Loading bot commands...")
        commands_to_load = [
            "src.cogs.admin.bot_control.restart",
            "src.cogs.admin.misc.credits",
            "src.cogs.admin.monitoring.utility_logs",
            "src.cogs.user_commands.control_panel",
            "src.cogs.user_commands.daily_verse",
            "src.cogs.user_commands.quran_question",
        ]

        loaded_commands = 0
        failed_commands = 0

        for command in commands_to_load:
            try:
                await self.load_extension(command)
                logger.info(
                    f"✅ Command loaded successfully: {command}",
                    extra={"event": "COMMAND_LOAD"},
                )
                loaded_commands += 1
            except Exception as e:
                logger.error(
                    f"❌ Failed to load command {command}: {e}",
                    extra={"event": "COMMAND_LOAD_ERROR"},
                )
                logger.error(
                    f"🔍 Command load error traceback: {traceback.format_exc()}"
                )
                failed_commands += 1

        logger.info(
            f"📦 Command loading completed: {loaded_commands} loaded, {failed_commands} failed"
        )

        # Sync command tree with enhanced error handling
        try:
            logger.info("🔄 Syncing command tree...")
            await self.tree.sync()
            logger.info(
                "✅ Command tree synced successfully", extra={"event": "COMMAND_SYNC"}
            )
        except Exception as e:
            logger.error(
                f"❌ Failed to sync command tree: {e}",
                extra={"event": "COMMAND_SYNC_ERROR"},
            )
            logger.error(f"🔍 Command sync error traceback: {traceback.format_exc()}")

        # Initialize log cleanup system with enhanced error handling
        try:
            logger.info("🧹 Initializing log cleanup system...")
            from monitoring.logging.log_cleanup import (
                LogCleanupManager,
                setup_log_cleanup_scheduler,
            )

            # Run initial cleanup
            cleanup_manager = LogCleanupManager()
            cleanup_results = cleanup_manager.run_full_cleanup()

            logger.info(
                f"🧹 Log cleanup initialized: {cleanup_results['stats']['active_folders']} active folders, "
                f"{cleanup_results['stats']['archived_folders']} archived, "
                f"{cleanup_results['stats']['total_size_mb']}MB total",
                extra={"event": "LOG_CLEANUP_INIT"},
            )

            # Start cleanup scheduler
            self.cleanup_scheduler_task = asyncio.create_task(
                setup_log_cleanup_scheduler()()
            )
            logger.info(
                "✅ Log cleanup scheduler started",
                extra={"event": "LOG_CLEANUP_SCHEDULER"},
            )

        except Exception as e:
            logger.error(
                f"❌ Failed to initialize log cleanup: {e}",
                extra={"event": "LOG_CLEANUP_ERROR"},
            )
            logger.error(f"🔍 Log cleanup error traceback: {traceback.format_exc()}")

        # Start backup task with enhanced error handling
        try:
            logger.info("💾 Starting backup task...")
            self.backup_task = asyncio.create_task(self._backup_loop())
            logger.info("✅ Backup task started", extra={"event": "BACKUP_SCHEDULER"})
        except Exception as e:
            logger.error(f"❌ Failed to start backup task: {e}")
            logger.error(f"🔍 Backup task error traceback: {traceback.format_exc()}")

        # Initialize health reporter
        try:
            logger.info("📊 Initializing health reporter...")
            self.health_reporter = HealthReporter(
                self, self.health_monitor, Config.LOGS_CHANNEL_ID
            )
            logger.info("✅ Health reporter initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize health reporter: {e}")
            logger.error(
                f"🔍 Health reporter error traceback: {traceback.format_exc()}"
            )

        t1 = time.time()
        setup_time = t1 - t0
        log_performance("setup_hook", setup_time)
        logger.info(f"✅ Bot setup completed in {setup_time:.2f} seconds")

    async def _backup_loop(self):
        """
        Background task to create backups periodically.

        This method runs continuously in the background and creates
        automated backups of the bot's data every hour. It includes
        comprehensive error handling and logging for reliability.

        Features:
        - Hourly automated backups
        - Error recovery and retry logic
        - Detailed logging of backup operations
        - Graceful shutdown handling
        """
        logger.info("💾 Backup loop started - will create backups every hour")

        while True:
            try:
                # Wait for 1 hour (3600 seconds) before next backup
                await asyncio.sleep(3600)

                logger.info(
                    "🔄 Creating scheduled backup...", extra={"event": "BACKUP"}
                )

                # Create backup with enhanced error handling
                backup_success = await self.backup_manager.create_backup()

                if backup_success:
                    logger.info(
                        "✅ Scheduled backup completed successfully",
                        extra={"event": "BACKUP_SUCCESS"},
                    )
                else:
                    logger.error(
                        "❌ Scheduled backup failed", extra={"event": "BACKUP_FAILURE"}
                    )

            except asyncio.CancelledError:
                logger.info("🛑 Backup task cancelled - shutting down gracefully")
                break

            except Exception as e:
                logger.error(f"❌ Error in backup loop: {str(e)}")
                logger.error(f"🔍 Backup error traceback: {traceback.format_exc()}")

                # Wait a minute before retrying on error
                logger.info("⏳ Waiting 60 seconds before retrying backup...")
                await asyncio.sleep(60)

    async def load_extension(self, extension_name: str):
        """Load a cog extension."""
        try:
            import importlib

            module = importlib.import_module(extension_name)
            if hasattr(module, "setup"):
                await module.setup(self)
                logger.info(
                    f"Loaded extension: {extension_name}",
                    extra={"event": "EXTENSION_LOAD"},
                )
            else:
                logger.error(
                    f"Extension {extension_name} has no setup function",
                    extra={"event": "EXTENSION_ERROR"},
                )
        except Exception as e:
            logger.error(
                f"Failed to load extension {extension_name}: {e}",
                extra={"event": "EXTENSION_ERROR"},
            )
            raise

    @log_async_function_call
    async def on_ready(self):
        """
        Called when bot is ready and connected to Discord.

        This method handles the bot's startup sequence including:
        - Bot startup logging and performance tracking
        - Rich presence setup and cycling
        - Health monitoring initialization
        - Discord logger setup
        - State management initialization
        - Voice channel connection
        - Final startup completion logging

        The method includes comprehensive error handling and detailed
        logging for each startup step to ensure reliable initialization.
        """
        t0 = time.time()

        try:
            if self.user:
                log_tree_start("Bot Ready Info")
                log_tree_item(f"🤖 Bot Name: {self.user.name}")
                log_tree_item(f"🆔 Bot ID: {self.user.id}")
                log_tree_item(f"🏠 Connected to {len(self.guilds)} guild(s)", is_last=True)
                log_tree_end()

                log_bot_startup(self.user.name, self.user.id)
                log_discord_event("ready", {"guilds": len(self.guilds)})
                t1 = time.time()
                log_performance("discord_ready", t1 - t0)

                # Set up dynamic rich presence with enhanced error handling
                try:
                    logger.info("🎭 Setting up rich presence...")
                    self.presence_messages = [
                        (discord.ActivityType.listening, "📖 Quran 24/7"),
                        (discord.ActivityType.playing, "🕋 Surah Al-Fatiha"),
                        (discord.ActivityType.watching, "🕌 for your requests"),
                        (discord.ActivityType.listening, "🎧 Beautiful Recitations"),
                        (discord.ActivityType.playing, "📿 Dhikr & Remembrance"),
                    ]
                    self.current_presence_index = 0
                    self.presence_cycle = self._presence_cycle()
                    await self.set_presence()
                    logger.info("✅ Rich presence setup completed")

                    # Start presence cycling
                    self.presence_task = asyncio.create_task(self.cycle_presence())
                    logger.info("✅ Presence cycling started")
                except Exception as e:
                    logger.error(f"❌ Failed to setup rich presence: {e}")
                    logger.error(
                        f"🔍 Presence setup error traceback: {traceback.format_exc()}"
                    )

                # Initialize health monitoring with enhanced error handling
                try:
                    logger.info("📊 Initializing health monitoring...")
                    self.health_reporter = HealthReporter(
                        self, self.health_monitor, Config.LOGS_CHANNEL_ID
                    )
                    await self.health_reporter.start()
                    logger.info("✅ Health monitoring started")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize health monitoring: {e}")
                    logger.error(
                        f"🔍 Health monitoring error traceback: {traceback.format_exc()}"
                    )

                # Initialize Discord logger sessions with enhanced error handling
                try:
                    logger.info("📝 Initializing Discord logger sessions...")
                    await self.discord_logger.initialize_existing_users()
                    logger.info("✅ Discord logger sessions initialized")
                except Exception as e:
                    logger.error(
                        f"❌ Failed to initialize Discord logger sessions: {e}"
                    )
                    logger.error(
                        f"🔍 Discord logger error traceback: {traceback.format_exc()}"
                    )

                # Initialize state management with enhanced error handling
                try:
                    logger.info("💾 Initializing state management...")
                    self.state_manager.increment_bot_start_count()
                    start_count = self.state_manager.get_bot_start_count()
                    log_state_load("bot_start_count", {"start_count": start_count})
                    logger.info(
                        f"✅ State management initialized (start count: {start_count})"
                    )

                    # Clear last change on restart (always starts fresh)
                    self.state_manager.clear_last_change()
                    logger.info("✅ State cleared for fresh start")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize state management: {e}")
                    logger.error(
                        f"🔍 State management error traceback: {traceback.format_exc()}"
                    )

                # Find and join target voice channel with enhanced error handling
                t2 = time.time()
                try:
                    logger.info(
                        f"🔗 Auto voice connect setting: {Config.AUTO_VOICE_CONNECT}"
                    )
                    await self.find_and_join_channel()

                    if Config.AUTO_VOICE_CONNECT:
                        logger.info(
                            "✅ Bot ready - voice connection enabled",
                            extra={"event": "READY"},
                        )
                    else:
                        logger.info(
                            "✅ Bot ready - voice connection disabled",
                            extra={"event": "READY"},
                        )
                except Exception as e:
                    logger.error(f"❌ Failed to find and join voice channel: {e}")
                    logger.error(
                        f"🔍 Voice channel error traceback: {traceback.format_exc()}"
                    )

                t3 = time.time()
                log_performance("find_and_join_channel", t3 - t2)

                # Log health status with enhanced error handling
                try:
                    logger.info(
                        "🏥 Bot health monitoring initialized",
                        extra={"event": "HEALTH"},
                    )
                    t4 = time.time()
                    log_performance("state_manager_init", t4 - t3)

                    logger.info(
                        "📊 Health reporting started", extra={"event": "HEALTH"}
                    )
                    t5 = time.time()
                    log_performance("health_reporter_start", t5 - t4)

                    # Log final startup completion
                    total_startup_time = t5 - t0
                    logger.info(
                        f"🎉 Bot startup completed successfully in {total_startup_time:.2f} seconds"
                    )
                    logger.info("=" * 50)
                    logger.info("🚀 Quran Bot is now ready to serve!")
                    logger.info("=" * 50)

                except Exception as e:
                    logger.error(f"❌ Failed to complete health status logging: {e}")
                    logger.error(
                        f"🔍 Health status error traceback: {traceback.format_exc()}"
                    )

        except Exception as e:
            logger.error(f"❌ Critical error during bot startup: {e}")
            logger.error(f"🔍 Startup error traceback: {traceback.format_exc()}")
            raise

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
                logger.info(
                    f"Found target channel: {channel.name} in guild: {guild.name}",
                    extra={
                        "event": "channel_found",
                        "channel": channel.name,
                        "guild": guild.name,
                    },
                )
                break

        t1 = time.time()
        log_performance("guild_channel_search", t1 - t0)

        if target_channel:
            if Config.AUTO_VOICE_CONNECT:
                await self.start_stream(target_channel)
            else:
                logger.info(
                    "Automatic voice connection disabled - bot will start without voice connection",
                    extra={"event": "VOICE_DISABLED"},
                )
        else:
            log_error(
                Exception("Channel not found"),
                "find_and_join_channel",
                additional_data={"channel_id": Config.TARGET_CHANNEL_ID},
            )
            logger.info("Make sure the bot has access to the target channel")
        t2 = time.time()
        log_performance("find_and_join_channel_total", t2 - t0)

    async def on_voice_state_update(self, member, before, after):
        """Handle voice state updates for reconnection logic."""
        # Log all voice state updates for debugging
        logger.debug(
            f"Voice state update triggered: {member.display_name} ({member.id}) - Before: {before.channel.name if before.channel else 'None'} -> After: {after.channel.name if after.channel else 'None'}",
            extra={
                "event": "VOICE_STATE_UPDATE",
                "user_id": member.id,
                "user_name": member.display_name,
            },
        )

        if self.user and member.id == self.user.id:
            if before.channel and not after.channel:
                # Bot was disconnected
                log_disconnection(
                    before.channel.name, "Disconnected from voice channel"
                )
                await self.discord_logger.log_bot_disconnected(
                    before.channel.name, "Disconnected from voice channel"
                )
                # Properly reset streaming state on disconnection
                self._was_streaming_before_disconnect = self.is_streaming
                self.is_streaming = False
                self.health_monitor.set_streaming_status(False)

                # Always attempt reconnection unless we've exceeded max failures
                if self.connection_failures < self.max_connection_failures:
                    # Check if we've had too many failures
                    self.connection_failures += 1
                    if self.connection_failures >= self.max_connection_failures:
                        logger.error(
                            f"Too many connection failures ({self.connection_failures}). Stopping reconnection attempts.",
                            extra={"event": "CONNECTION_FAILURE_LIMIT"},
                        )
                        self.is_streaming = False
                        return

                    # Wait before reconnecting (shorter delays for more aggressive reconnection)
                    wait_time = min(
                        30 * self.connection_failures, 180
                    )  # Progressive delay up to 3 minutes
                    logger.info(
                        f"Waiting {wait_time} seconds before reconnection attempt {self.connection_failures}/{self.max_connection_failures}...",
                        extra={
                            "event": "RECONNECT_WAIT",
                            "wait_time": wait_time,
                            "failures": self.connection_failures,
                        },
                    )
                    await asyncio.sleep(wait_time)

                    logger.info(
                        "Attempting to reconnect after disconnection...",
                        extra={"event": "RECONNECT_ATTEMPT"},
                    )
                    await self.find_and_join_channel()
                else:
                    logger.info(
                        "Bot disconnected - max failures reached, not attempting reconnection",
                        extra={"event": "DISCONNECT_MAX_FAILURES"},
                    )
            elif not before.channel and after.channel:
                # Bot connected to voice
                log_connection_success(after.channel.name, after.channel.guild.name)
                await self.discord_logger.log_bot_connected(
                    after.channel.name, after.channel.guild.name
                )
                # Reset connection failure counter on successful connection
                if self.connection_failures > 0:
                    logger.info(
                        f"Connection successful! Reset failure counter from {self.connection_failures} to 0.",
                        extra={"event": "CONNECTION_SUCCESS"},
                    )
                    self.connection_failures = 0
                # Resume streaming if it was previously active (with proper delay and checks)
                # Check if we were streaming before the last disconnection
                if (
                    hasattr(self, "_was_streaming_before_disconnect")
                    and self._was_streaming_before_disconnect
                ):
                    logger.info(
                        "Bot was streaming before disconnect, scheduling resume...",
                        extra={"event": "STREAM_RESUME_SCHEDULED"},
                    )

                    # Schedule delayed resume to ensure voice connection is stable
                    async def delayed_resume():
                        await asyncio.sleep(
                            5
                        )  # Wait 5 seconds for connection to stabilize
                        guild_id = after.channel.guild.id
                        if (
                            guild_id in self._voice_clients
                            and hasattr(self._voice_clients[guild_id], "is_connected")
                            and self._voice_clients[guild_id].is_connected()
                            and not self.is_streaming
                        ):  # Only resume if not already streaming
                            logger.info(
                                "Resuming streaming after stable reconnection...",
                                extra={"event": "STREAM_RESUME_EXECUTE"},
                            )
                            self._was_streaming_before_disconnect = False  # Clear flag
                            await self.start_stream(after.channel)
                        else:
                            logger.warning(
                                "Cannot resume streaming - connection not stable or already streaming",
                                extra={"event": "STREAM_RESUME_FAILED"},
                            )
                            self._was_streaming_before_disconnect = (
                                False  # Clear flag anyway
                            )

                    asyncio.create_task(delayed_resume())
                else:
                    logger.info(
                        "Voice connected (no auto-resume needed)",
                        extra={"event": "VOICE_CONNECTED"},
                    )
            elif before.channel and after.channel and before.channel != after.channel:
                # Bot moved to different channel
                log_connection_success(after.channel.name, after.channel.guild.name)

        # Handle user voice state changes (not the bot) - only track target Quran VC
        elif member != self.user:
            target_vc_id = self.discord_logger.target_vc_id

            # Debug logging to see what's happening
            logger.debug(
                f"Voice state update: {member.display_name} ({member.id}) - Before: {before.channel.name if before.channel else 'None'} -> After: {after.channel.name if after.channel else 'None'}",
                extra={
                    "event": "VOICE_STATE_DEBUG",
                    "user_id": member.id,
                    "target_vc": target_vc_id,
                },
            )

            # User joined the target Quran VC from nowhere or different channel
            if (
                after.channel
                and after.channel.id == target_vc_id
                and (not before.channel or before.channel.id != target_vc_id)
            ):
                logger.info(
                    f"User {member.display_name} joined target VC {after.channel.name}",
                    extra={
                        "event": "USER_JOINED_VC",
                        "user_id": member.id,
                        "channel_id": after.channel.id,
                    },
                )
                logger.info(
                    f"├─ 👤 User Details: {member.name}#{member.discriminator} (ID: {member.id})",
                    extra={
                        "event": "USER_JOINED_VC_DETAILS",
                        "user_id": member.id,
                        "username": member.name,
                        "discriminator": member.discriminator,
                    },
                )
                logger.info(
                    f"├─ 🏠 Guild: {member.guild.name} (ID: {member.guild.id})",
                    extra={
                        "event": "USER_JOINED_VC_DETAILS",
                        "guild_id": member.guild.id,
                        "guild_name": member.guild.name,
                    },
                )
                logger.info(
                    f"├─ 📅 Account Created: {member.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
                    extra={
                        "event": "USER_JOINED_VC_DETAILS",
                        "account_created": member.created_at.isoformat(),
                    },
                )
                logger.info(
                    f"└─ 🎭 Roles: {len(member.roles)} roles",
                    extra={
                        "event": "USER_JOINED_VC_DETAILS",
                        "role_count": len(member.roles),
                    },
                )
                await self.discord_logger.log_user_joined_vc(member, after.channel.name)

            # User left the target Quran VC to nowhere or different channel
            elif (
                before.channel
                and before.channel.id == target_vc_id
                and (not after.channel or after.channel.id != target_vc_id)
            ):
                logger.info(
                    f"User {member.display_name} left target VC {before.channel.name}",
                    extra={
                        "event": "USER_LEFT_VC",
                        "user_id": member.id,
                        "channel_id": before.channel.id,
                    },
                )
                logger.info(
                    f"├─ 👤 User Details: {member.name}#{member.discriminator} (ID: {member.id})",
                    extra={
                        "event": "USER_LEFT_VC_DETAILS",
                        "user_id": member.id,
                        "username": member.name,
                        "discriminator": member.discriminator,
                    },
                )
                logger.info(
                    f"├─ 🏠 Guild: {member.guild.name} (ID: {member.guild.id})",
                    extra={
                        "event": "USER_LEFT_VC_DETAILS",
                        "guild_id": member.guild.id,
                        "guild_name": member.guild.name,
                    },
                )
                logger.info(
                    f"├─ 📅 Account Created: {member.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
                    extra={
                        "event": "USER_LEFT_VC_DETAILS",
                        "account_created": member.created_at.isoformat(),
                    },
                )
                logger.info(
                    f"└─ 🎭 Roles: {len(member.roles)} roles",
                    extra={
                        "event": "USER_LEFT_VC_DETAILS",
                        "role_count": len(member.roles),
                    },
                )
                await self.discord_logger.log_user_left_vc(member, before.channel.name)

    async def on_disconnect(self):
        """Handle bot disconnection."""
        log_disconnection("Discord", "Bot disconnected from Discord")
        self.is_streaming = False
        self.health_monitor.set_streaming_status(False)

    async def handle_voice_session_expired(self, guild_id):
        """Handle voice session expired (4006) errors."""
        logger.warning(
            f"Voice session expired (4006) for guild {guild_id}. Waiting before reconnection...",
            extra={"event": "VOICE_ERROR", "error_code": "4006"},
        )

        # Remove from voice clients
        if guild_id in self._voice_clients:
            del self._voice_clients[guild_id]

        # Wait much longer before reconnecting to break the reconnection loop
        await asyncio.sleep(120)  # Wait 2 minutes

        # Try to reconnect if still streaming
        if self.is_streaming:
            logger.info(
                "Attempting reconnection after session expired...",
                extra={"event": "SESSION_RECONNECT"},
            )
            await self.find_and_join_channel()

    async def handle_voice_error(self, voice_client, error):
        """Handle voice connection errors with retry logic."""
        guild_id = voice_client.guild.id if voice_client.guild else None
        error_msg = str(error)

        if "4006" in error_msg or "session expired" in error_msg.lower():
            logger.warning(
                f"Voice session expired (4006) for guild {guild_id}. Waiting before reconnection...",
                extra={"event": "VOICE_ERROR", "error_code": "4006"},
            )
            # Remove from voice clients
            if guild_id in self._voice_clients:
                del self._voice_clients[guild_id]

            # Wait much longer before reconnecting to break the reconnection loop
            await asyncio.sleep(120)  # Wait 2 minutes

            # Try to reconnect
            if self.is_streaming:
                logger.info(
                    "Attempting reconnection after session expired...",
                    extra={"event": "SESSION_RECONNECT"},
                )
                await self.find_and_join_channel()
        else:
            logger.error(
                f"Voice error for guild {guild_id}: {error_msg}",
                extra={"event": "VOICE_ERROR", "error": error_msg},
            )
            self.health_monitor.record_error(error, f"voice_error_guild_{guild_id}")

    async def start_stream(self, channel: discord.VoiceChannel):
        """Start streaming Quran to the voice channel with improved error handling."""
        t0 = time.time()
        max_retries = 3  # Reduced retries to prevent spam
        retry_delay = 30  # Start with longer delay

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
                log_performance("voice_connect", t2 - t1)
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
                        asyncio.create_task(
                            self.play_quran_files(voice_client, channel)
                        )
                        break
                else:
                    log_connection_failure(channel.name, e, attempt + 1)
                    self.health_monitor.record_error(e, "voice_connection")

            # Exponential backoff with longer delays for 4006 errors
            if attempt < max_retries - 1:
                delay = min(
                    retry_delay * (3**attempt), 300
                )  # Cap at 5 minutes, use 3x multiplier
                logger.info(
                    f"Retrying connection in {delay} seconds...",
                    extra={"event": "RETRY", "attempt": attempt + 1, "delay": delay},
                )
                await asyncio.sleep(delay)

        t3 = time.time()
        log_performance("start_stream_total", t3 - t0)

        # Log warning if still slow
        if (t3 - t0) > 3.0:
            logger.warning(
                f"Connection took {t3-t0:.2f}s - consider Discord server issues",
                extra={"event": "SLOW_CONNECTION", "duration": t3 - t0},
            )

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
            has_mp3 = any(f.lower().endswith(".mp3") for f in os.listdir(reciter_path))
            if has_mp3:
                # Preserve current surah when switching reciters
                current_surah_index = self.state_manager.get_current_song_index()

                self.current_reciter = folder_name  # Store the folder name
                self.original_playlist = []  # Reset playlist cache on reciter switch

                # Reset playback timer and position when switching reciters (but keep surah)
                if hasattr(self, "playback_start_time"):
                    self.playback_start_time = None
                    self.state_manager.clear_playback_position()
                    logger.info(f"Reset playback timer for new reciter: {reciter_name}")

                # Keep the same surah index (stay on current surah)
                if current_surah_index is not None:
                    # Verify the surah exists in the new reciter's folder
                    new_audio_files = self.get_audio_files()
                    if new_audio_files and current_surah_index < len(new_audio_files):
                        # Keep the same surah index
                        self.state_manager.set_current_song_index(current_surah_index)
                        # Update the song name for the new reciter
                        new_file_name = os.path.basename(
                            new_audio_files[current_surah_index]
                        )
                        self.state_manager.set_current_song_name(new_file_name)
                        self.current_audio_file = new_file_name
                        logger.info(
                            f"Kept same surah {current_surah_index + 1} with new reciter: {reciter_name}"
                        )
                    else:
                        # Fallback to beginning if current surah doesn't exist in new reciter
                        self.state_manager.set_current_song_index(0)
                        self.state_manager.set_current_song_name("")
                        logger.info(
                            f"Reset to beginning - current surah not available in new reciter: {reciter_name}"
                        )
                else:
                    # No current surah, start from beginning
                    self.state_manager.set_current_song_index(0)
                    self.state_manager.set_current_song_name("")
                    logger.info(
                        f"Started from beginning with new reciter: {reciter_name}"
                    )

                logger.info(
                    f"Switched to reciter: {reciter_name} (folder: {folder_name})",
                    extra={
                        "event": "RECITER_CHANGE",
                        "reciter": reciter_name,
                        "folder": folder_name,
                    },
                )
                return True

        logger.warning(
            f"Reciter not found: {reciter_name} (folder: {folder_name})",
            extra={
                "event": "RECITER_NOT_FOUND",
                "reciter": reciter_name,
                "folder": folder_name,
            },
        )
        return False

    def toggle_loop(
        self, user_id: Optional[int] = None, username: Optional[str] = None
    ) -> bool:
        """Toggle loop mode for current surah with user tracking."""
        self.loop_enabled = not self.loop_enabled

        if self.loop_enabled and user_id is not None and username is not None:
            # Track who enabled the loop
            self.state_manager.set_loop_enabled_by(user_id, username)
            logger.info(
                f"Loop mode enabled by {username} (ID: {user_id})",
                extra={
                    "event": "LOOP_TOGGLE",
                    "loop_enabled": True,
                    "user_id": user_id,
                    "username": username,
                },
            )
        elif not self.loop_enabled:
            # Clear loop tracking when disabled
            self.state_manager.clear_loop_enabled_by()
            logger.info(
                "Loop mode disabled",
                extra={"event": "LOOP_TOGGLE", "loop_enabled": False},
            )
        else:
            logger.info(
                f"Loop mode {'enabled' if self.loop_enabled else 'disabled'}",
                extra={"event": "LOOP_TOGGLE", "loop_enabled": self.loop_enabled},
            )

        return self.loop_enabled

    def toggle_shuffle(
        self, user_id: Optional[int] = None, username: Optional[str] = None
    ) -> bool:
        """Toggle shuffle mode for surah order with user tracking."""
        self.shuffle_enabled = not self.shuffle_enabled

        if self.shuffle_enabled and user_id is not None and username is not None:
            # Track who enabled the shuffle
            self.state_manager.set_shuffle_enabled_by(user_id, username)
            logger.info(
                f"Shuffle mode enabled by {username} (ID: {user_id})",
                extra={
                    "event": "SHUFFLE_TOGGLE",
                    "shuffle_enabled": True,
                    "user_id": user_id,
                    "username": username,
                },
            )
        elif not self.shuffle_enabled:
            # Clear shuffle tracking when disabled
            self.state_manager.clear_shuffle_enabled_by()
            logger.info(
                "Shuffle mode disabled",
                extra={"event": "SHUFFLE_TOGGLE", "shuffle_enabled": False},
            )
        else:
            logger.info(
                f"Shuffle mode {'enabled' if self.shuffle_enabled else 'disabled'}",
                extra={
                    "event": "SHUFFLE_TOGGLE",
                    "shuffle_enabled": self.shuffle_enabled,
                },
            )

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
        """Get the duration of an audio file using FFmpeg with enhanced error handling."""
        if not os.path.exists(file_path):
            logger.error(
                f"Audio file not found: {file_path}",
                extra={"event": "FILE_NOT_FOUND", "file": file_path},
            )
            return None

        if os.path.getsize(file_path) == 0:
            logger.error(
                f"Audio file is empty: {file_path}",
                extra={"event": "EMPTY_FILE", "file": file_path},
            )
            return None

        try:
            # Try ffprobe first with timeout and better error handling
            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                file_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0 and result.stdout.strip():
                duration = float(result.stdout.strip())
                if duration > 0:
                    logger.debug(
                        f"Got duration via ffprobe for {file_path}: {duration}s",
                        extra={
                            "event": "FFPROBE_SUCCESS",
                            "file": file_path,
                            "duration": duration,
                        },
                    )
                    return duration
                else:
                    logger.warning(
                        f"ffprobe returned zero duration for {file_path}",
                        extra={"event": "FFPROBE_ZERO_DURATION", "file": file_path},
                    )
            else:
                logger.debug(
                    f"ffprobe failed for {file_path}: {result.stderr}",
                    extra={
                        "event": "FFPROBE_FAILED",
                        "file": file_path,
                        "stderr": result.stderr,
                    },
                )
        except subprocess.TimeoutExpired:
            logger.warning(
                f"ffprobe timeout for {file_path}",
                extra={"event": "FFPROBE_TIMEOUT", "file": file_path},
            )
        except Exception as e:
            logger.debug(
                f"ffprobe exception for {file_path}: {e}",
                extra={"event": "FFPROBE_EXCEPTION", "file": file_path},
            )

        # Fallback: try to get duration using ffmpeg with better error handling
        try:
            cmd = ["ffmpeg", "-i", file_path, "-f", "null", "-"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            # Parse duration from ffmpeg output
            import re

            for line in result.stderr.split("\n"):
                if "Duration:" in line:
                    # Extract duration from line like "Duration: 00:03:45.00, start: 0.000000, bitrate: 128 kb/s"
                    duration_match = re.search(
                        r"Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})", line
                    )
                    if duration_match:
                        hours = int(duration_match.group(1))
                        minutes = int(duration_match.group(2))
                        seconds = int(duration_match.group(3))
                        centiseconds = int(duration_match.group(4))
                        total_seconds = (
                            hours * 3600 + minutes * 60 + seconds + centiseconds / 100
                        )
                        if total_seconds > 0:
                            logger.debug(
                                f"Got duration via ffmpeg fallback for {file_path}: {total_seconds}s",
                                extra={
                                    "event": "FFMPEG_DURATION_SUCCESS",
                                    "file": file_path,
                                    "duration": total_seconds,
                                },
                            )
                            return total_seconds
                        else:
                            logger.warning(
                                f"ffmpeg fallback returned zero duration for {file_path}",
                                extra={
                                    "event": "FFMPEG_ZERO_DURATION",
                                    "file": file_path,
                                },
                            )
        except subprocess.TimeoutExpired:
            logger.warning(
                f"ffmpeg duration fallback timeout for {file_path}",
                extra={"event": "FFMPEG_DURATION_TIMEOUT", "file": file_path},
            )
        except Exception as e:
            logger.debug(
                f"ffmpeg duration fallback exception for {file_path}: {e}",
                extra={"event": "FFMPEG_DURATION_EXCEPTION", "file": file_path},
            )

        # Final fallback: estimate based on file size (rough approximation)
        try:
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                logger.error(
                    f"Cannot estimate duration for empty file: {file_path}",
                    extra={"event": "ESTIMATE_EMPTY_FILE", "file": file_path},
                )
                return None

            # Rough estimate: 1 MB ≈ 1 minute for typical MP3 quality (128kbps)
            # More accurate estimation based on typical MP3 bitrates
            estimated_duration = file_size / (
                128 * 1024 / 8
            )  # bytes / (bits per second / 8)
            if estimated_duration > 0:
                logger.info(
                    f"Using estimated duration for {file_path}: {estimated_duration:.1f} seconds (file size: {file_size/1024/1024:.1f}MB)",
                    extra={
                        "event": "ESTIMATED_DURATION",
                        "file": file_path,
                        "duration": estimated_duration,
                        "file_size_mb": file_size / 1024 / 1024,
                    },
                )
                return estimated_duration
            else:
                logger.error(
                    f"Estimated duration is zero for {file_path}",
                    extra={"event": "ESTIMATE_ZERO_DURATION", "file": file_path},
                )
                return None
        except Exception as e:
            logger.warning(
                f"Could not estimate duration for {file_path}: {e}",
                extra={"event": "DURATION_ESTIMATE_FAILED", "file": file_path},
            )
            return None

    def validate_audio_file(self, file_path):
        """Validate audio file integrity and format."""
        if not os.path.exists(file_path):
            logger.error(
                f"Audio file not found during validation: {file_path}",
                extra={"event": "VALIDATION_FILE_NOT_FOUND", "file": file_path},
            )
            return False

        try:
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                logger.error(
                    f"Audio file is empty during validation: {file_path}",
                    extra={"event": "VALIDATION_EMPTY_FILE", "file": file_path},
                )
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
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0 and result.stdout.strip():
                codec = result.stdout.strip()
                logger.debug(
                    f"Audio file validation successful for {file_path}: codec={codec}, size={file_size/1024/1024:.1f}MB",
                    extra={
                        "event": "VALIDATION_SUCCESS",
                        "file": file_path,
                        "codec": codec,
                        "size_mb": file_size / 1024 / 1024,
                    },
                )
                return True
            else:
                logger.error(
                    f"Audio file validation failed for {file_path}: {result.stderr}",
                    extra={
                        "event": "VALIDATION_FAILED",
                        "file": file_path,
                        "stderr": result.stderr,
                    },
                )
                return False

        except subprocess.TimeoutExpired:
            logger.error(
                f"Audio file validation timeout for {file_path}",
                extra={"event": "VALIDATION_TIMEOUT", "file": file_path},
            )
            return False
        except Exception as e:
            logger.error(
                f"Audio file validation exception for {file_path}: {e}",
                extra={"event": "VALIDATION_EXCEPTION", "file": file_path},
            )
            return False

    async def play_surah_with_retries(self, voice_client, mp3_file, max_retries=2):
        """Play a surah with retries and robust FFmpeg error handling. Also updates dynamic presence timer."""
        file_name = os.path.basename(mp3_file)
        surah_info = get_surah_from_filename(file_name)
        surah_display = get_surah_display_name(surah_info["number"])

        # Validate audio file before attempting playback
        if not self.validate_audio_file(mp3_file):
            logger.error(
                f"Skipping invalid audio file: {mp3_file}",
                extra={"event": "INVALID_AUDIO_FILE", "file": file_name},
            )
            return False

        total_duration = self.get_audio_duration(mp3_file)
        if not total_duration:
            logger.error(
                f"Could not determine duration for {mp3_file}, skipping",
                extra={"event": "NO_DURATION", "file": file_name},
            )
            return False

        logger.info(
            f"Starting playback of {surah_display} ({file_name}) - Duration: {total_duration:.1f}s",
            extra={
                "event": "PLAYBACK_START",
                "file": file_name,
                "duration": total_duration,
            },
        )

        for attempt in range(max_retries + 1):
            try:
                # Ensure previous audio is stopped with better error handling
                if voice_client.is_playing():
                    logger.debug(
                        f"Stopping previous audio before playing {file_name}",
                        extra={"event": "STOP_PREVIOUS", "file": file_name},
                    )
                    voice_client.stop()
                    # Wait up to 5 seconds for audio to stop
                    for _ in range(5):
                        if not voice_client.is_playing():
                            break
                        await asyncio.sleep(1)
                    if voice_client.is_playing():
                        logger.warning(
                            f"Previous audio did not stop in time, skipping {file_name}",
                            extra={"event": "STOP_TIMEOUT", "file": file_name},
                        )
                        return False

                # Create FFmpeg source with error handling
                try:
                    source = discord.FFmpegPCMAudio(mp3_file)
                    logger.debug(
                        f"Created FFmpeg source for {file_name}",
                        extra={"event": "FFMPEG_SOURCE_CREATED", "file": file_name},
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to create FFmpeg source for {file_name}: {e}",
                        extra={
                            "event": "FFMPEG_SOURCE_FAILED",
                            "file": file_name,
                            "attempt": attempt + 1,
                        },
                    )
                    raise

                # Start playback
                voice_client.play(source)
                logger.debug(
                    f"Started playback of {file_name}",
                    extra={"event": "PLAYBACK_STARTED", "file": file_name},
                )

                wait_count = 0
                max_wait = int(total_duration) if total_duration else 900
                start_time = time.time()

                # Dynamic presence update loop with better error handling
                while (
                    voice_client.is_playing()
                    and voice_client.is_connected()
                    and wait_count < max_wait
                ):
                    try:
                        elapsed = int(time.time() - start_time)
                        # Format elapsed and total
                        elapsed_str = f"{elapsed//60}:{elapsed%60:02d}"
                        total_str = (
                            f"{int(total_duration)//60}:{int(total_duration)%60:02d}"
                            if total_duration
                            else "?"
                        )
                        emoji = get_surah_emoji(surah_info["number"])
                        presence_str = f"{emoji} {surah_info['english_name']} — {elapsed_str} / {total_str}"
                        activity = discord.Activity(
                            type=discord.ActivityType.listening, name=presence_str
                        )
                        await self.change_presence(activity=activity)

                        # Save playback position every 30 seconds
                        if (
                            wait_count % 6 == 0
                        ):  # Every 30 seconds (6 * 5 second intervals)
                            current_time = time.time()
                            self.state_manager.save_playback_position(current_time)

                        # Wait 5 seconds or until playback ends
                        for _ in range(5):
                            if (
                                not voice_client.is_playing()
                                or not voice_client.is_connected()
                            ):
                                break
                            await asyncio.sleep(1)
                            wait_count += 1

                    except Exception as e:
                        logger.warning(
                            f"Error during presence update for {file_name}: {e}",
                            extra={"event": "PRESENCE_UPDATE_ERROR", "file": file_name},
                        )
                        # Continue playback even if presence update fails
                        await asyncio.sleep(5)
                        wait_count += 1

                # Wait for playback to actually finish (FFmpeg might have terminated but audio could still be buffered)
                if voice_client.is_connected():
                    # Give a small buffer for any remaining audio
                    await asyncio.sleep(2)

                # Final update to show full duration
                try:
                    if total_duration:
                        emoji = get_surah_emoji(surah_info["number"])
                        presence_str = f"{emoji} {surah_info['english_name']} — {int(total_duration)//60}:{int(total_duration)%60:02d} / {int(total_duration)//60}:{int(total_duration)%60:02d}"
                        await self.change_presence(
                            activity=discord.Activity(
                                type=discord.ActivityType.listening, name=presence_str
                            )
                        )
                except Exception as e:
                    logger.warning(
                        f"Error in final presence update for {file_name}: {e}",
                        extra={"event": "FINAL_PRESENCE_ERROR", "file": file_name},
                    )

                # Clear playback position when surah finishes
                self.state_manager.clear_playback_position()
                # Reset the playback start time for the next surah
                self.playback_start_time = time.time()
                self.state_manager.set_playback_start_time(self.playback_start_time)

                # Additional buffer
                await asyncio.sleep(3)

                logger.info(
                    f"Successfully completed playback of {surah_display} ({file_name})",
                    extra={
                        "event": "PLAYBACK_SUCCESS",
                        "file": file_name,
                        "duration": total_duration,
                    },
                )
                return True  # Success

            except discord.errors.ConnectionClosed as e:
                if "4006" in str(e) or "session expired" in str(e).lower():
                    # Handle session expired error
                    guild_id = voice_client.guild.id if voice_client.guild else None
                    logger.warning(
                        f"Voice session expired for {file_name}, guild_id: {guild_id}",
                        extra={
                            "event": "SESSION_EXPIRED",
                            "file": file_name,
                            "guild_id": guild_id,
                        },
                    )
                    await self.handle_voice_session_expired(guild_id)
                    return False
                else:
                    logger.error(
                        f"Voice connection closed for {file_name}: {e}",
                        extra={
                            "event": "VOICE_CONNECTION_CLOSED",
                            "file": file_name,
                            "attempt": attempt + 1,
                        },
                    )
                    log_error(
                        e,
                        f"voice_connection_{file_name}",
                        additional_data={"attempt": attempt + 1},
                    )
                    self.health_monitor.record_error(e, f"voice_connection_{file_name}")

            except discord.errors.ClientException as e:
                logger.error(
                    f"Discord client exception for {file_name}: {e}",
                    extra={
                        "event": "DISCORD_CLIENT_ERROR",
                        "file": file_name,
                        "attempt": attempt + 1,
                    },
                )
                log_error(
                    e,
                    f"discord_client_{file_name}",
                    additional_data={"attempt": attempt + 1},
                )
                self.health_monitor.record_error(e, f"discord_client_{file_name}")

            except Exception as e:
                logger.error(
                    f"FFmpeg playback error for {file_name}: {e}",
                    extra={
                        "event": "FFMPEG_PLAYBACK_ERROR",
                        "file": file_name,
                        "attempt": attempt + 1,
                    },
                )
                log_error(
                    e,
                    f"ffmpeg_playback_{file_name}",
                    additional_data={"attempt": attempt + 1},
                )
                self.health_monitor.record_error(e, f"ffmpeg_playback_{file_name}")

                # Try to forcibly stop playback if stuck
                try:
                    if voice_client.is_playing():
                        voice_client.stop()
                        logger.debug(
                            f"Force stopped playback for {file_name}",
                            extra={"event": "FORCE_STOP", "file": file_name},
                        )
                        for _ in range(5):
                            if not voice_client.is_playing():
                                break
                            await asyncio.sleep(1)
                except Exception as stop_error:
                    logger.warning(
                        f"Error while force stopping {file_name}: {stop_error}",
                        extra={"event": "FORCE_STOP_ERROR", "file": file_name},
                    )

                await asyncio.sleep(2)  # Short delay before retry

        logger.error(
            f"FFmpeg failed for {file_name} after {max_retries+1} attempts. Skipping.",
            extra={
                "event": "FFMPEG_FINAL_FAILURE",
                "file": file_name,
                "attempts": max_retries + 1,
            },
        )
        return False

    async def play_quran_files(
        self, voice_client: discord.VoiceClient, channel: discord.VoiceChannel
    ):
        """Play Quran MP3 files in a continuous loop with robust FFmpeg handling."""
        t0 = time.time()
        try:
            logger.info(
                f"Starting Quran playback in channel: {channel.name} with reciter: {self.current_reciter}",
                extra={
                    "event": "playback_start",
                    "channel": channel.name,
                    "reciter": self.current_reciter,
                },
            )

            # Get playlist based on shuffle setting
            mp3_files = self.get_shuffled_playlist()

            t1 = time.time()
            log_performance("audio_file_scan", t1 - t0)
            if not mp3_files:
                log_error(
                    Exception("No MP3 files found"),
                    "play_quran_files",
                    additional_data={
                        "folder": Config.AUDIO_FOLDER,
                        "reciter": self.current_reciter,
                    },
                )
                return
            logger.info(
                f"Found {len(mp3_files)} audio files from reciter: {self.current_reciter}",
                extra={"event": "AUDIO", "reciter": self.current_reciter},
            )

            current_index = self.state_manager.get_current_song_index()
            last_song = self.state_manager.get_current_song_name()
            if last_song and current_index < len(mp3_files):
                logger.info(
                    f"Resuming from song {current_index}: {last_song} (Reciter: {self.current_reciter})",
                    extra={
                        "event": "resume_playback",
                        "song_index": current_index,
                        "song_name": last_song,
                        "reciter": self.current_reciter,
                    },
                )
            else:
                logger.info(
                    f"Starting from beginning (Reciter: {self.current_reciter})",
                    extra={"event": "start_playback", "reciter": self.current_reciter},
                )
                current_index = 0
            self.is_streaming = True
            self.health_monitor.set_streaming_status(True)

            # Set playback start time for position tracking
            current_time = time.time()

            # Restore playback position if available
            saved_position = self.state_manager.get_playback_position()
            if saved_position > 0:
                logger.info(
                    f"Restoring playback position: {saved_position:.1f} seconds",
                    extra={"event": "restore_position", "position": saved_position},
                )
                # Adjust the start time to account for the saved position
                # This makes the timer show the correct elapsed time
                self.playback_start_time = current_time - saved_position
                self.state_manager.set_playback_start_time(self.playback_start_time)
            else:
                # No saved position, start from beginning
                self.playback_start_time = current_time
                self.state_manager.set_playback_start_time(current_time)

            t2 = time.time()
            log_performance("playback_init", t2 - t1)
            consecutive_failures = 0

            while self.is_streaming and voice_client.is_connected():
                # Handle loop mode - if enabled, play current surah repeatedly
                if self.loop_enabled and self.current_audio_file:
                    # Dedicated loop for continuous surah repetition
                    while (
                        self.loop_enabled
                        and self.is_streaming
                        and voice_client.is_connected()
                        and self.current_audio_file
                    ):
                        if (
                            self.current_audio_file is None
                            or self.current_reciter is None
                        ):
                            break
                        mp3_file = os.path.join(
                            Config.AUDIO_FOLDER,
                            str(self.current_reciter),
                            str(self.current_audio_file),
                        )
                        if os.path.exists(mp3_file):
                            file_name = os.path.basename(mp3_file)
                            try:
                                surah_info = get_surah_from_filename(file_name)
                                surah_display = get_surah_display_name(
                                    surah_info["number"]
                                )
                                log_audio_playback(
                                    f"{surah_display} ({file_name}) - Reciter: {self.current_reciter} [LOOP]"
                                )
                                self.state_manager.increment_songs_played()
                                self.health_monitor.update_current_song(file_name)
                                await self.update_presence_for_surah(surah_info)
                                success = await self.play_surah_with_retries(
                                    voice_client, mp3_file
                                )
                                if not success:
                                    consecutive_failures += 1
                                    if consecutive_failures >= 3:
                                        logger.error(
                                            f"Multiple consecutive FFmpeg failures with reciter {self.current_reciter}. Check your audio files and FFmpeg installation.",
                                            extra={
                                                "event": "FFMPEG",
                                                "reciter": self.current_reciter,
                                            },
                                        )
                                        consecutive_failures = 0
                                        # Wait before retrying
                                        await asyncio.sleep(5)
                                    continue
                                else:
                                    consecutive_failures = 0
                                # Small gap between loops for smooth transition
                                if (
                                    self.is_streaming
                                    and voice_client.is_connected()
                                    and self.loop_enabled
                                ):
                                    await asyncio.sleep(1)
                            except Exception as e:
                                log_error(e, f"playing {mp3_file}")
                                self.health_monitor.record_error(
                                    e, f"audio_playback_{file_name}"
                                )
                                # Wait before retrying on error
                                await asyncio.sleep(2)
                                continue
                        else:
                            logger.warning(
                                f"Loop file not found: {mp3_file}. Disabling loop mode.",
                                extra={"event": "AUDIO", "file": mp3_file},
                            )
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
                        surah_display = get_surah_display_name(surah_info["number"])
                        log_audio_playback(
                            f"{surah_display} ({file_name}) - Reciter: {self.current_reciter}"
                        )
                        self.state_manager.set_current_song_index(i)
                        self.state_manager.set_current_song_name(file_name)
                        self.state_manager.increment_songs_played()
                        self.health_monitor.update_current_song(file_name)
                        self.current_audio_file = file_name
                        await self.update_presence_for_surah(surah_info)
                        success = await self.play_surah_with_retries(
                            voice_client, mp3_file
                        )
                        if not success:
                            consecutive_failures += 1
                            if consecutive_failures >= 3:
                                logger.error(
                                    f"Multiple consecutive FFmpeg failures with reciter {self.current_reciter}. Check your audio files and FFmpeg installation.",
                                    extra={
                                        "event": "FFMPEG",
                                        "reciter": self.current_reciter,
                                    },
                                )
                                consecutive_failures = 0
                            continue
                        else:
                            consecutive_failures = 0
                        # Small gap between surahs for smooth transition
                        if self.is_streaming and voice_client.is_connected():
                            await asyncio.sleep(1)
                    except Exception as e:
                        log_error(e, f"playing {mp3_file}")
                        self.health_monitor.record_error(
                            e, f"audio_playback_{file_name}"
                        )
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
        log_performance("play_quran_files_total", t3 - t0)

    async def close(self):
        """Cleanup when bot is shutting down."""
        if self.health_reporter:
            await self.health_reporter.stop()
        if self.backup_task:
            self.backup_task.cancel()
            try:
                await self.backup_task
            except asyncio.CancelledError:
                pass
        await super().close()

    async def update_presence_for_surah(self, surah_info):
        """Update the bot's presence to show the currently playing surah."""
        try:
            emoji = get_surah_emoji(surah_info["number"])
            activity_type = discord.ActivityType.listening
            message = f"{emoji} {surah_info['english_name']}"

            await self.change_presence(
                activity=discord.Activity(type=activity_type, name=message)
            )
            logger.debug(f"Updated presence to: {message}")
        except Exception as e:
            log_error(e, "update_presence_for_surah")

    async def cycle_presence(self):
        """Cycle through different rich presences every 2 minutes."""
        while True:
            # Check if we're currently playing a surah
            if hasattr(self, "current_audio_file") and self.current_audio_file:
                surah_info = get_surah_from_filename(self.current_audio_file)
                await self.update_presence_for_surah(surah_info)
            else:
                # Fallback to cycling through general messages
                activity_type, message = next(self.presence_cycle)
                await self.change_presence(
                    activity=discord.Activity(type=activity_type, name=message)
                )

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
            if hasattr(self, "discord_logger"):
                await self.discord_logger.cleanup_sessions()

            # Stop presence cycling
            if (
                hasattr(self, "presence_task")
                and self.presence_task
                and not self.presence_task.done()
            ):
                self.presence_task.cancel()
                try:
                    await self.presence_task
                except asyncio.CancelledError:
                    pass
                logger.info("Presence cycling stopped")

            # Stop log cleanup scheduler
            if (
                hasattr(self, "cleanup_scheduler_task")
                and self.cleanup_scheduler_task
                and not self.cleanup_scheduler_task.done()
            ):
                self.cleanup_scheduler_task.cancel()
                try:
                    await self.cleanup_scheduler_task
                except asyncio.CancelledError:
                    pass
                logger.info("Log cleanup scheduler stopped")

            # Disconnect from all voice channels
            for guild_id, voice_client in self._voice_clients.items():
                try:
                    if voice_client.is_connected():
                        await voice_client.disconnect()
                        logger.info(
                            f"Disconnected from voice channel in guild {guild_id}"
                        )
                except Exception as e:
                    log_error(e, f"disconnect_voice_guild_{guild_id}")

            # Save final state and position
            if hasattr(self, "current_audio_file") and self.current_audio_file:
                self.state_manager.set_current_song_name(self.current_audio_file)
                logger.info(f"Saved final state: {self.current_audio_file}")

            # Save final playback position if currently playing
            if (
                self.is_streaming
                and hasattr(self, "playback_start_time")
                and self.playback_start_time
            ):
                current_time = time.time()
                self.state_manager.save_playback_position(current_time)
                logger.info("Saved final playback position")

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
            await self.change_presence(
                activity=discord.Activity(type=activity_type, name=message)
            )
            logger.debug(f"Set initial presence to: {message}")
        except Exception as e:
            log_error(e, "set_presence")

    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available and working."""
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    async def play_audio(self):
        """Restart audio playback - wrapper for control panel compatibility."""
        try:
            # Find the current voice client
            voice_client = None
            channel = None

            for guild in self.guilds:
                if guild.voice_client:
                    voice_client = guild.voice_client
                    channel = voice_client.channel
                    break

            if (
                voice_client
                and channel
                and hasattr(voice_client, "is_connected")
                and getattr(voice_client, "is_connected", lambda: False)()
            ):
                # Stop current playback
                self.is_streaming = False
                await asyncio.sleep(1)  # Give time for current playback to stop

                # Restart playback
                self.is_streaming = True
                # Type cast to ensure compatibility
                if isinstance(voice_client, discord.VoiceClient) and isinstance(
                    channel, discord.VoiceChannel
                ):
                    asyncio.create_task(self.play_quran_files(voice_client, channel))
                    logger.info("Audio playback restarted via control panel")
                else:
                    logger.warning("Invalid voice client or channel type")
            else:
                logger.warning("No voice client found for audio restart")
        except Exception as e:
            logger.error(f"Error restarting audio playback: {e}")
            log_error(e, "play_audio")

    def get_current_playback_time(self):
        if self.playback_start_time:
            return time.time() - self.playback_start_time
        return 0


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
    logger.info("Starting Quran Bot...", extra={"event": "startup"})
    try:
        bot.run(Config.DISCORD_TOKEN)
    except Exception as e:
        log_error(e, "main")
        logger.critical(f"❌ Failed to start bot: {e}")


if __name__ == "__main__":
    main()
