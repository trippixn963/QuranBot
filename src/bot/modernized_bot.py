# =============================================================================
# QuranBot - Modernized Bot Implementation
# =============================================================================
# Main bot class with dependency injection and modern architecture patterns.
# This module contains the core bot implementation that orchestrates all
# QuranBot functionality using modern software architecture patterns.
# =============================================================================

import asyncio
from pathlib import Path
import time

import discord
from discord.ext import commands

from src.adapters.audio_service_adapter import AudioServiceAdapter
from src.commands import load_commands
from src.config import (
    QuranBotConfig,
    get_config,
    get_discord_token,
    get_guild_id,
    get_target_channel_id,
)
from src.core.cache_service import CacheService
from src.core.di_container import DIContainer, set_global_container
from src.core.health_monitor import HealthMonitor
from src.core.logger import StructuredLogger
from src.core.performance_monitor import PerformanceMonitor
from src.core.resource_manager import ResourceManager
from src.core.database import DatabaseManager
from src.services.database_service import QuranBotDatabaseService
from src.monitoring.bot_status_monitor import BotStatusMonitor
from src.core.security import RateLimiter, SecurityService


from src.services.audio_service import AudioService
from src.services.metadata_cache import MetadataCache
from src.services.state_service import SQLiteStateService
from src.utils.control_panel import setup_control_panel
from src.utils.presence import RichPresenceManager
from src.utils.surah_utils import get_surah_info
from src.utils.tree_log import (
    log_critical_error,
    log_error_with_traceback,
    log_perfect_tree_section,
    log_status,
)
from src.utils.verses import setup_daily_verses
from src.version import BOT_NAME, BOT_VERSION


class ModernizedQuranBot:
    """
    Modernized QuranBot with dependency injection and 100% automated audio playback.

    This is the main bot class that orchestrates all QuranBot functionality using modern
    software architecture patterns. It provides:

    Architecture Features:
    - Dependency injection container for service management
    - Comprehensive error handling and recovery mechanisms
    - Structured logging with comprehensive monitoring
    - Health monitoring and automatic reconnection
    - Graceful shutdown with resource cleanup

    Core Functionality:
    - 24/7 continuous Quran audio playback
    - Interactive Discord control panel
    - Voice channel activity tracking
    - Quiz system and daily verse delivery
    - Islamic AI question answering
    - Prayer time notifications for Mecca

    The bot is designed for fully automated operation with minimal manual intervention
    while providing rich interactive features for users who want to engage actively.
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.container: DIContainer | None = None
        self.bot: commands.Bot | None = None
        self.logger: StructuredLogger | None = None
        self.config: QuranBotConfig | None = None
        self.is_running = False
        self._startup_start_time = time.time()
        self._shutdown_in_progress = False

    async def initialize(self) -> bool:
        """Initialize the modernized bot with all services."""
        try:
            from src.utils.tree_log import log_run_header

            log_run_header(BOT_NAME, BOT_VERSION)
            log_perfect_tree_section(
                "🏗️ Initializing Modernized Architecture",
                [
                    ("Mode", "100% Automated + Optional Commands"),
                    ("DI Container", "Setting up dependency injection"),
                    ("Core Services", "Cache, Performance, Security"),
                    ("Modern Services", "Audio, State Management"),
                    ("Discord Bot", "Integration and commands"),
                ],
            )

            # 1. Initialize configuration
            log_status("Loading configuration", "⚙️")
            try:
                self.config = get_config()
                log_status("Configuration loaded successfully", "✅")
            except Exception as e:
                log_critical_error(f"Configuration failed: {e}")
                return False

            # 2. Initialize DI container
            log_status("Setting up Dependency Injection", "🔧")
            self.container = DIContainer()
            set_global_container(self.container)

            # Register configuration services
            self.container.register_singleton(QuranBotConfig, self.config)

            # 3. Initialize core services
            await self._initialize_core_services()

            # 4. Initialize modern services
            await self._initialize_modern_services()

            # 5. Initialize Discord bot
            await self._initialize_discord_bot()

            log_perfect_tree_section(
                "🎯 ✅ Modernized Architecture Ready",
                [
                    ("Mode", "100% Automated + Optional Commands"),
                    ("Services", "All services initialized successfully"),
                    ("Discord Bot", "Configured and ready for connection"),
                    ("Architecture", "Modern architecture fully operational"),
                ],
            )
            return True

        except Exception as e:
            log_critical_error(f"Initialization failed: {e}")
            log_error_with_traceback("Detailed error", e)
            return False

    async def _initialize_core_services(self):
        """Initialize core services like logging, caching, monitoring."""
        log_status("Initializing core services", "🛠️")

        # Structured Logger
        logger_factory = lambda: StructuredLogger(
            name="quranbot",
            level="INFO",
            log_file=self.project_root / "logs" / "quranbot.log",
            console_output=True,
        )
        self.container.register_singleton(StructuredLogger, logger_factory)
        self.logger = self.container.get(StructuredLogger)
        await self.logger.info("Structured logger initialized")

        # Health Monitor
        log_status("Initializing health monitoring system", "💚")
        health_monitor = HealthMonitor(
            logger=self.logger,

            data_dir=self.project_root / "data",
            check_interval_minutes=60,
            alert_interval_minutes=5,
        )
        self.container.register_singleton(HealthMonitor, health_monitor)

        # Cache Service
        from src.core.cache_service import CacheConfig

        cache_config = CacheConfig(
            max_memory_mb=self.config.cache_max_memory_mb,
            max_entries=self.config.cache_max_entries,
            default_ttl_seconds=self.config.cache_default_ttl_seconds,
            strategy=self.config.cache_strategy,
            level=self.config.cache_level,
            enable_compression=self.config.cache_enable_compression,
            compression_threshold_bytes=self.config.cache_compression_threshold_bytes,
            disk_cache_directory=self.config.cache_disk_directory,
            cleanup_interval_seconds=self.config.cache_cleanup_interval_seconds,
            enable_statistics=self.config.cache_enable_statistics,
            enable_persistence=self.config.cache_enable_persistence,
        )
        cache_factory = lambda: CacheService(
            container=self.container, config=cache_config, logger=self.logger
        )
        self.container.register_singleton(CacheService, cache_factory)

        # Performance Monitor
        perf_monitor_factory = lambda: PerformanceMonitor(
            container=self.container,
            logger=self.logger,
            collection_interval=300,
            enable_detailed_profiling=False,
        )
        self.container.register_singleton(PerformanceMonitor, perf_monitor_factory)

        # Resource Manager
        resource_manager_factory = lambda: ResourceManager(
            container=self.container, logger=self.logger
        )
        self.container.register_singleton(ResourceManager, resource_manager_factory)

        # Security Service
        rate_limiter = RateLimiter(logger=self.logger)
        security_factory = lambda: SecurityService(
            rate_limiter=rate_limiter, logger=self.logger
        )
        self.container.register_singleton(SecurityService, security_factory)

        # Database Services
        log_status("Initializing database services", "🗄️")
        data_dir = Path(self.config.data_directory or "data")
        data_dir.mkdir(exist_ok=True)
        
        db_manager = DatabaseManager(
            db_path=data_dir / "quranbot.db",
            logger=self.logger,
            max_pool_size=10
        )
        await db_manager.initialize()
        self.container.register_singleton(DatabaseManager, db_manager)
        
        db_service = QuranBotDatabaseService(
            db_manager=db_manager,
            logger=self.logger
        )
        self.container.register_singleton(QuranBotDatabaseService, db_service)



        # Initialize all core services
        await self.container.get(CacheService).initialize()
        await self.container.get(PerformanceMonitor).initialize()
        await self.container.get(ResourceManager).initialize()

        log_status("Core services initialized", "✅")



    async def _initialize_modern_services(self):
        """Initialize modern services like audio and state management."""
        log_status("Initializing modern services", "🎵")

        # Create Discord bot first (needed for audio service)
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        intents.guilds = True

        self.bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
        self.container.register_singleton(commands.Bot, self.bot)

        # Create metadata cache
        metadata_cache = MetadataCache(
            logger=self.logger, max_size=1000, enable_persistence=True
        )
        self.container.register_singleton(MetadataCache, metadata_cache)

        # Audio Service
        audio_config = self.config
        audio_factory = lambda: AudioService(
            container=self.container,
            bot=self.bot,
            config=audio_config,
            logger=self.logger,
            metadata_cache=metadata_cache,
        )
        self.container.register_singleton(AudioService, audio_factory)

        # State Service
        state_factory = lambda: SQLiteStateService(
            logger=self.logger, db_path=self.project_root / "data" / "quranbot.db"
        )
        self.container.register_singleton(SQLiteStateService, state_factory)

        # Initialize modern services
        await self.container.get(AudioService).initialize()
        await self.container.get(SQLiteStateService).initialize()

        # Rich Presence Manager
        log_status("Setting up Rich Presence", "🎮")
        rich_presence_factory = lambda: RichPresenceManager(
            client=self.bot, data_dir=self.project_root / "data"
        )
        self.container.register_singleton(RichPresenceManager, rich_presence_factory)

        # Bot Status Monitor
        log_status("Setting up Bot Status Monitor", "📊")
        db_service = self.container.get(QuranBotDatabaseService)
        self.status_monitor = BotStatusMonitor(
            bot=self.bot,
            db_service=db_service,
            data_dir=self.project_root / "data"
        )
        self.container.register_singleton(BotStatusMonitor, self.status_monitor)

        log_status("Modern services initialized", "✅")

    async def _initialize_discord_bot(self):
        """Initialize Discord bot with event handlers and commands."""
        log_status("Setting up Discord bot", "🤖")

        # Set up bot events
        await self._setup_bot_events()

        # Load commands
        await self._load_commands()

        log_status("Discord bot configured", "✅")

    async def _setup_bot_events(self):
        """Set up Discord bot events with modern service integration."""

        @self.bot.event
        async def on_ready():
            """Bot ready event - start automated audio playback immediately."""
            startup_end_time = time.time()
            startup_duration = startup_end_time - self._startup_start_time

            await self.logger.info(
                "Bot connected to Discord",
                {
                    "bot_name": self.bot.user.name,
                    "bot_id": self.bot.user.id,
                    "guild_count": len(self.bot.guilds),
                },
            )

            log_perfect_tree_section(
                "🎯 🎵 QuranBot Online",
                [
                    ("Bot Name", self.bot.user.name),
                    ("Bot ID", self.bot.user.id),
                    ("Guilds", f"{len(self.bot.guilds)} connected"),
                    ("Mode", "Starting 100% automated continuous recitation"),
                ],
            )





            # Start bot status monitor
            try:
                status_monitor = self.container.get(BotStatusMonitor)
                await status_monitor.start()
                await self.logger.info("Bot status monitor started successfully")
            except Exception as e:
                await self.logger.error(f"Failed to start status monitor: {e}")

            # Start automated audio playback
            await self._start_automated_continuous_playback()

            # Start periodic role cleanup task
            asyncio.create_task(self._periodic_role_cleanup())

            # Start health monitor for hourly status reports
            try:
                health_monitor = self.container.get(HealthMonitor)
                if health_monitor:
                    await health_monitor.start_monitoring()
                    await self.logger.info(
                        "Health monitor started",
                        {
                            "check_interval": f"{health_monitor.check_interval_minutes} minutes"
                        },
                    )
                else:
                    await self.logger.warning(
                        "Health monitor not available in container"
                    )
            except Exception as e:
                await self.logger.error(
                    "Failed to start health monitor", {"error": str(e)}
                )

            # Initialize additional systems
            await self._initialize_additional_systems()

        @self.bot.event
        async def on_error(event, *args, **kwargs):
            """Global error handler with modern logging."""
            await self.logger.error(
                "Discord event error",
                {"event": event, "args": str(args)[:500], "kwargs": str(kwargs)[:500]},
            )
            


        @self.bot.event
        async def on_command_error(ctx, error):
            """Command error handler with modern error management."""
            if isinstance(error, commands.CommandNotFound):
                return

            await self.logger.error(
                "Command error",
                {
                    "command": ctx.command.name if ctx.command else "unknown",
                    "user_id": ctx.author.id,
                    "guild_id": ctx.guild.id if ctx.guild else None,
                    "error": str(error),
                },
            )
            


            await ctx.send("❌ An error occurred while processing your command.")

        @self.bot.event
        async def on_voice_state_update(member, before, after):
            """Handle voice state changes for role management."""
            await self._handle_voice_state_update(member, before, after)



    async def _initialize_additional_systems(self):
        """Initialize additional systems like daily verses, quiz, etc."""
        # Initialize daily verses system
        try:
            daily_verse_channel_id = self.config.daily_verse_channel_id
            if daily_verse_channel_id:
                await setup_daily_verses(self.bot, daily_verse_channel_id)
                await self.logger.info(
                    "Daily verses system initialized",
                    {"channel_id": daily_verse_channel_id},
                )
        except Exception as e:
            await self.logger.error(
                "Failed to initialize daily verses system", {"error": str(e)}
            )

        # Initialize quiz system
        try:
            daily_verse_channel_id = self.config.daily_verse_channel_id
            if daily_verse_channel_id:
                from src.utils.quiz_manager import setup_quiz_system

                await setup_quiz_system(self.bot, daily_verse_channel_id)
                await self.logger.info(
                    "Quiz system initialized",
                    {"channel_id": daily_verse_channel_id},
                )
        except Exception as e:
            await self.logger.error(
                "Failed to initialize quiz system", {"error": str(e)}
            )

        # Initialize other systems...
        await self._initialize_prayer_notifications()
        await self._initialize_islamic_ai()

    async def _initialize_prayer_notifications(self):
        """Initialize Mecca prayer notifications."""
        try:
            from src.utils.prayer_times import setup_mecca_prayer_notifications

            await setup_mecca_prayer_notifications(self.bot)
            await self.logger.info(
                "Mecca prayer notification system initialized",
                {"monitoring": "5 daily prayers in Holy City"},
            )
        except Exception as e:
            await self.logger.error(
                "Failed to initialize Mecca prayer notifications", {"error": str(e)}
            )

    async def _initialize_islamic_ai(self):
        """Initialize Islamic AI mention listener."""
        try:
            from src.services.islamic_ai_listener import setup_islamic_ai_listener

            await setup_islamic_ai_listener(self.bot, self.container)
            await self.logger.info(
                "Islamic AI mention listener initialized",
                {
                    "trigger": "bot mentions",
                    "model": "GPT-3.5 Turbo",
                    "languages": "English + Arabic input",
                    "rate_limit": "1 question/hour per user",
                },
            )
        except Exception as e:
            await self.logger.error(
                "Failed to initialize Islamic AI listener", {"error": str(e)}
            )

    async def _handle_voice_state_update(self, member, before, after):
        """Handle voice state changes for QuranBot voice channel activity and role management."""
        try:
            audio_service = self.container.get(AudioService)
            target_channel_id = get_target_channel_id()

            # Handle role management
            await self._handle_voice_channel_roles(
                member, before, after, target_channel_id
            )

        except Exception as e:
            await self.logger.error(
                "Error in voice state update handler",
                {"member_id": member.id if member else "unknown", "error": str(e)},
            )

    async def _handle_voice_channel_roles(
        self, member, before, after, target_channel_id
    ):
        """Handle role assignment/removal for voice channel activity."""
        # Skip role management for bots
        if member.bot:
            return

        panel_access_role_id = self.config.panel_access_role_id
        if not panel_access_role_id:
            return

        guild = member.guild
        if not guild:
            return

        panel_role = guild.get_role(panel_access_role_id)
        if not panel_role:
            return

        # Handle role logic based on voice state changes
        if (
            not before.channel
            and after.channel
            and after.channel.id == target_channel_id
        ):
            # User joined Quran voice channel
            await self._assign_panel_access_role(member, panel_role, after.channel)
        elif (
            before.channel
            and before.channel.id == target_channel_id
            and (not after.channel or after.channel.id != target_channel_id)
        ):
            # User left Quran voice channel
            await self._remove_panel_access_role(member, panel_role, before.channel)

    async def _assign_panel_access_role(self, member, panel_role, channel):
        """Assign the panel access role to a user."""
        try:
            if panel_role in member.roles:
                return

            await member.add_roles(panel_role, reason="Joined Quran voice channel")
            await self.logger.info(
                "Panel access role assigned",
                {
                    "user": member.display_name,
                    "user_id": member.id,
                    "role": panel_role.name,
                    "channel": channel.name,
                },
            )
        except Exception as e:
            await self.logger.error(
                "Error assigning panel access role",
                {"user": member.display_name, "error": str(e)},
            )

    async def _remove_panel_access_role(self, member, panel_role, channel, force=False):
        """Remove the panel access role from a user."""
        try:
            if not force and panel_role not in member.roles:
                return

            await member.remove_roles(panel_role, reason="Left Quran voice channel")
            await self.logger.info(
                "Panel access role removed",
                {
                    "user": member.display_name,
                    "user_id": member.id,
                    "role": panel_role.name,
                    "channel": channel.name if channel else "None",
                },
            )
        except Exception as e:
            await self.logger.error(
                "Error removing panel access role",
                {"user": member.display_name, "error": str(e)},
            )

    async def _log_voice_activity(
        self, member, before, after, target_channel_id, audio_service
    ):
        """Log voice channel activity."""
        joined_quran_vc = (
            before.channel is None
            and after.channel is not None
            and after.channel.id == target_channel_id
        )

        left_quran_vc = (
            before.channel is not None
            and before.channel.id == target_channel_id
            and (after.channel is None or after.channel.id != target_channel_id)
        )

        if joined_quran_vc:
            try:
                from src.utils.stats import get_listening_stats_manager

                listening_manager = get_listening_stats_manager()
                if listening_manager:
                    listening_manager.user_joined_voice(member.id)

                await self.logger.info(
                    "User joined QuranBot voice channel",
                    {
                        "user_name": member.display_name,
                        "user_id": member.id,
                        "channel_name": after.channel.name,
                        "current_listeners": len(after.channel.members),
                    },
                )
            except Exception as e:
                await self.logger.warning(
                    "Failed to log voice join activity",
                    {"user_id": member.id, "error": str(e)},
                )

        elif left_quran_vc:
            try:
                from src.utils.stats import get_listening_stats_manager

                listening_manager = get_listening_stats_manager()
                if listening_manager:
                    listening_manager.user_left_voice(member.id)

                remaining_members = len(before.channel.members) - 1

                await self.logger.info(
                    "User left QuranBot voice channel",
                    {
                        "user_name": member.display_name,
                        "user_id": member.id,
                        "channel_name": before.channel.name,
                        "remaining_listeners": remaining_members,
                    },
                )
            except Exception as e:
                await self.logger.warning(
                    "Failed to log voice leave activity",
                    {"user_id": member.id, "error": str(e)},
                )

    async def _start_automated_continuous_playback(self):
        """Start 100% automated continuous Quran playback (24/7)."""
        try:
            log_perfect_tree_section(
                "🎵 Starting 100% Automated Playback",
                [
                    ("Mode", "24/7 Continuous Quran Recitation"),
                    ("Automation", "No manual intervention required"),
                    (
                        "Voice Channel",
                        f"Auto-connecting to {get_target_channel_id()}",
                    ),
                    ("Playback", "Automatic progression through all 114 surahs"),
                ],
            )

            # Get services
            audio_service = self.container.get(AudioService)
            rich_presence = self.container.get(RichPresenceManager)

            # Start monitoring task for rich presence
            asyncio.create_task(
                self._monitor_audio_for_rich_presence(audio_service, rich_presence)
            )

            # Connect to voice channel
            voice_channel_id = get_target_channel_id()
            guild_id = get_guild_id()
            connected = await audio_service.connect_to_voice_channel(
                voice_channel_id, guild_id
            )

            if not connected:
                await self.logger.error(
                    "Failed to connect to voice channel for automation",
                    {"channel_id": voice_channel_id},
                )
                return

            # Start continuous playback
            await audio_service.start_playback(resume_position=True)

            # Set up control panel
            await self._setup_control_panel(voice_channel_id, guild_id)

            log_perfect_tree_section(
                "🎵 ✅ 100% Automated Playback Active",
                [
                    ("Status", "Successfully started automated continuous recitation"),
                    ("Voice Channel", f"Connected to {voice_channel_id}"),
                    ("Playback Mode", "24/7 continuous - automatic progression"),
                    ("Control Panel", "Interactive panel created"),
                    ("Rich Presence", "Connected and updating"),
                    ("Manual Commands", "Available but not required for operation"),
                ],
            )

        except Exception as e:
            await self.logger.error(
                "Failed to start automated continuous playback", {"error": str(e)}
            )
            log_error_with_traceback("Automated playback error", e)

    async def _monitor_audio_for_rich_presence(
        self, audio_service: AudioService, rich_presence: RichPresenceManager
    ):
        """Monitor audio service and update rich presence."""
        while True:
            try:
                playback_state = await audio_service.get_playback_state()

                if playback_state.is_playing:
                    surah_info = get_surah_info(
                        playback_state.current_position.surah_number
                    )
                    if surah_info:
                        rich_presence.update_presence_with_template(
                            "listening",
                            {
                                "emoji": surah_info.emoji,
                                "surah": surah_info.name_transliteration,
                                "verse": "1",
                                "total": str(surah_info.verses),
                                "reciter": playback_state.current_reciter,
                            },
                            silent=False,
                        )
                    else:
                        rich_presence.update_presence(
                            status=f"🎵 Surah {playback_state.current_position.surah_number}",
                            details=f"Recited by {playback_state.current_reciter}",
                            state="Quran Recitation",
                            activity_type="listening",
                            silent=False,
                        )
                else:
                    rich_presence.update_presence(
                        status="QuranBot",
                        details="Connecting",
                        state="Continuous Quran Recitation",
                        activity_type="playing",
                        silent=False,
                    )

                await asyncio.sleep(30)

            except Exception as e:
                await self.logger.error(
                    "Error monitoring audio for rich presence", {"error": str(e)}
                )
                await asyncio.sleep(60)

    async def _setup_control_panel(self, voice_channel_id: int, guild_id: int):
        """Set up the control panel with AudioService adapter."""
        try:
            log_status("Setting up Control Panel", "🎛️")

            audio_service = self.container.get(AudioService)
            audio_adapter = AudioServiceAdapter(audio_service)

            await setup_control_panel(
                bot=self.bot,
                channel_id=self.config.panel_channel_id,
                audio_manager=audio_adapter,
            )

            log_status("Control Panel configured", "✅")

        except Exception as e:
            await self.logger.error("Failed to set up control panel", {"error": str(e)})
            log_error_with_traceback("Control panel setup error", e)

    async def _load_commands(self):
        """Load Discord commands."""
        try:
            log_status("Loading Discord commands", "⚡")
            await load_commands(self.bot, self.container)
            log_status("Discord commands loaded", "✅")
        except Exception as e:
            await self.logger.error("Failed to load commands", {"error": str(e)})
            log_error_with_traceback("Command loading error", e)

    async def _periodic_role_cleanup(self):
        """Periodic role cleanup task."""
        cleanup_interval = 3600  # 1 hour

        while True:
            try:
                await self.logger.info("Starting hourly role audit")

                total_checked = 0
                total_roles_removed = 0

                for guild in self.bot.guilds:
                    try:
                        target_channel_id = get_target_channel_id()
                        if not target_channel_id:
                            continue

                        panel_access_role_id = self.config.panel_access_role_id
                        if not panel_access_role_id:
                            continue

                        panel_role = guild.get_role(panel_access_role_id)
                        if not panel_role:
                            continue

                        target_channel = guild.get_channel(target_channel_id)
                        if not target_channel:
                            continue

                        users_in_quran_vc = {
                            member.id
                            for member in target_channel.members
                            if not member.bot
                        }

                        for member in guild.members:
                            if member.bot:
                                continue

                            total_checked += 1

                            if (
                                panel_role in member.roles
                                and member.id not in users_in_quran_vc
                            ):
                                try:
                                    await member.remove_roles(
                                        panel_role,
                                        reason="Hourly audit: Not in Quran voice channel",
                                    )
                                    total_roles_removed += 1
                                    await asyncio.sleep(0.5)  # Rate limit protection
                                except Exception as e:
                                    await self.logger.error(
                                        "Error removing role during audit",
                                        {"user": member.display_name, "error": str(e)},
                                    )

                    except Exception as e:
                        await self.logger.error(
                            "Error processing guild during role audit",
                            {"guild_id": guild.id, "error": str(e)},
                        )

                await self.logger.info(
                    "Hourly role audit completed",
                    {
                        "total_members_checked": total_checked,
                        "total_roles_removed": total_roles_removed,
                    },
                )

                await asyncio.sleep(cleanup_interval)

            except Exception as e:
                await self.logger.error(
                    "Critical error in hourly role audit", {"error": str(e)}
                )
                await asyncio.sleep(600)  # Wait 10 minutes on error

    async def run(self):
        """Start the modernized bot."""
        try:
            self.is_running = True

            if not await self.initialize():
                log_critical_error("Failed to initialize bot")
                return False

            log_status("Starting Discord bot", "🚀")
            await self.bot.start(get_discord_token())

        except KeyboardInterrupt:
            log_status("Received shutdown signal", "⏹️")
        except Exception as e:
            log_critical_error(f"Bot runtime error: {e}")

        finally:
            await self.shutdown()



    async def shutdown(self):
        """Gracefully shutdown all services."""
        if not self.is_running or self._shutdown_in_progress:
            return

        self._shutdown_in_progress = True

        log_perfect_tree_section(
            "🔄 Graceful Shutdown",
            [
                ("Discord Bot", "Stopping connection"),
                ("Services", "Shutting down all services"),
                ("Resources", "Cleaning up and releasing"),
            ],
        )

        try:
            if self.logger:
                await self.logger.info("Starting graceful shutdown")



            # Stop Discord bot
            if self.bot and not self.bot.is_closed():
                log_status("Disconnecting from Discord", "📡")
                await self.bot.close()

            # Shutdown services
            await self._shutdown_services()

            log_status("All services stopped", "✅")

            if self.logger:
                await self.logger.info("Graceful shutdown completed")

        except Exception as e:
            log_critical_error(f"Shutdown error: {e}")
        finally:
            self.is_running = False



    async def _shutdown_services(self):
        """Shutdown all services in reverse order."""
        if not self.container:
            return

        log_status("Shutting down services", "🛠️")

        services_to_shutdown = [
            SQLiteStateService,
            AudioService,
            PerformanceMonitor,
            ResourceManager,
            CacheService,
        ]

        for service_type in services_to_shutdown:
            try:
                service = self.container.get(service_type)
                if service and hasattr(service, "shutdown"):
                    await service.shutdown()
            except:
                pass  # Continue shutting down other services
