#!/usr/bin/env python3
# =============================================================================
# QuranBot - Modernized Main Entry Point
# =============================================================================
# This is the modernized main entry point that uses the modern architecture
# with dependency injection, proper service management, and error handling.
# The bot is 100% automated for continuous Quran recitation while also
# providing optional commands for interaction.
# =============================================================================

import asyncio
import os
from pathlib import Path
import signal
import sys
import time
import traceback
from typing import Optional

import psutil

# Add src to Python path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# Import Discord bot
import discord
from discord.ext import commands

# Import utilities
from src.commands import load_commands

# Import configuration management
from src.config import BotConfig, ConfigService
from src.core.cache_service import CacheService

# Import core modernized services
from src.core.di_container import DIContainer
from src.core.performance_monitor import PerformanceMonitor
from src.core.resource_manager import ResourceManager
from src.core.security import RateLimiter, SecurityService
from src.core.structured_logger import StructuredLogger
from src.core.webhook_logger import ModernWebhookLogger

# Import data models
from src.data.models import PlaybackMode

# Import modern services
from src.services.audio_service import AudioService
from src.services.metadata_cache import MetadataCache
from src.services.state_service import StateService
from src.utils.control_panel import setup_control_panel
from src.utils.daily_verses import setup_daily_verses
from src.utils.rich_presence import RichPresenceManager
from src.utils.surah_mapper import get_surah_info

# Import tree logging for compatibility
from src.utils.tree_log import (
    log_critical_error,
    log_error_with_traceback,
    log_perfect_tree_section,
    log_run_end,
    log_run_header,
    log_run_separator,
    log_spacing,
    log_status,
)

# Import version information
from src.version import BOT_NAME, BOT_VERSION


class AudioServiceAdapter:
    """
    Adapter to make AudioService compatible with the control panel's expectations.

    The control panel was designed for the old AudioManager, but we're using the new AudioService.
    This adapter bridges the gap by providing the expected interface.
    """

    def __init__(self, audio_service: AudioService):
        self.audio_service = audio_service

    def get_playback_status(self) -> dict:
        """Get playback status in the format expected by the control panel."""
        try:
            print("[DEBUG] AudioServiceAdapter.get_playback_status called")

            # Can't use asyncio.run() within Discord's event loop, so access internal state directly
            # but make sure we get the most recent state
            state = self.audio_service._current_state

            # Force refresh the state by calling the internal update method if available
            try:
                if hasattr(self.audio_service, "_update_playback_state"):
                    self.audio_service._update_playback_state()
                elif hasattr(self.audio_service, "update_position"):
                    self.audio_service.update_position()
            except:
                pass  # Continue with existing state if update fails

            print(f"[DEBUG] Got state: {state}")

            if not state:
                print("[DEBUG] No state found, returning defaults")
                return self._get_default_status()

            # Get available reciters from the audio service
            available_reciters = []
            try:
                reciters_info = self.audio_service._available_reciters
                available_reciters = (
                    [r.name for r in reciters_info]
                    if reciters_info
                    else ["Saad Al Ghamdi"]
                )
                print(f"[DEBUG] Found reciters: {available_reciters}")
            except:
                available_reciters = ["Saad Al Ghamdi"]

            # Get current time and total time
            current_time = (
                getattr(getattr(state, "current_position", None), "position_seconds", 0)
                if hasattr(state, "current_position")
                else 0
            )
            total_time = (
                getattr(
                    getattr(state, "current_position", None), "total_duration", None
                )
                or 0
                if hasattr(state, "current_position")
                else 0
            )

            # If total_time is 0, try to get from cache
            if total_time == 0:
                print("[DEBUG] Total time is 0, trying to get from cache...")
                try:
                    current_surah = getattr(
                        getattr(state, "current_position", None), "surah_number", 1
                    )
                    current_reciter = getattr(
                        state, "current_reciter", "Saad Al Ghamdi"
                    )

                    # Build file path
                    file_path = f"audio/{current_reciter}/{current_surah:03d}.mp3"
                    print(f"[DEBUG] Looking for file: {file_path}")

                    # Try to access cache directly from the audio service
                    cache_service = getattr(self.audio_service, "_cache", None)

                    if cache_service and hasattr(cache_service, "get"):
                        cache_key = f"duration_{file_path}"
                        try:
                            cached_duration = cache_service.get(cache_key)
                            if cached_duration:
                                total_time = cached_duration
                                print(f"[DEBUG] Got duration from cache: {total_time}s")
                        except:
                            pass

                    # If no cache hit, try to read MP3 metadata directly
                    if total_time == 0:
                        from pathlib import Path

                        full_path = Path(file_path)
                        if full_path.exists():
                            try:
                                from mutagen.mp3 import MP3

                                audio_file = MP3(str(full_path))
                                total_time = audio_file.info.length
                                print(f"[DEBUG] Got duration from MP3: {total_time}s")
                            except Exception as e:
                                print(f"[DEBUG] Error reading MP3: {e}")
                                # Fallback: use some known durations for testing
                                if current_surah == 1:
                                    total_time = 47.0625  # Al-Fatiha
                                elif current_surah == 2:
                                    total_time = 7054.331125  # Al-Baqarah
                                else:
                                    total_time = 300  # Default 5 minutes
                                print(f"[DEBUG] Using fallback duration: {total_time}s")
                        else:
                            print(f"[DEBUG] File not found: {full_path}")

                except Exception as e:
                    print(f"[DEBUG] Error getting duration: {e}")

            # Convert AudioService state to control panel format
            result = {
                "is_playing": getattr(state, "is_playing", False),
                "is_paused": getattr(state, "is_paused", False),
                "current_surah": getattr(
                    getattr(state, "current_position", None), "surah_number", 1
                ),
                "current_reciter": getattr(state, "current_reciter", "Saad Al Ghamdi"),
                "is_loop_enabled": getattr(state, "mode", None) == "loop",
                "is_shuffle_enabled": getattr(state, "mode", None) == "shuffle",
                "current_track": getattr(
                    getattr(state, "current_position", None), "surah_number", 1
                ),
                "total_tracks": 114,
                "available_reciters": available_reciters,
                "current_time": current_time,
                "total_time": total_time,
            }

            print(f"[DEBUG] Returning result: {result}")
            return result

        except Exception as e:
            print(f"[DEBUG] Error in get_playback_status: {e}")
            traceback.print_exc()
            return self._get_default_status()

    def _get_default_status(self) -> dict:
        """Return safe default status when AudioService is unavailable."""
        return {
            "is_playing": False,
            "is_paused": False,
            "current_surah": 1,
            "current_reciter": "Saad Al Ghamdi",
            "is_loop_enabled": False,
            "is_shuffle_enabled": False,
            "current_track": 1,
            "total_tracks": 114,
            "available_reciters": ["Saad Al Ghamdi"],
            "current_time": 0,
            "total_time": 0,
        }

    # Control methods expected by the control panel
    async def jump_to_surah(self, surah_number: int):
        """Jump to a specific surah."""
        try:
            print(f"[DEBUG] AudioServiceAdapter.jump_to_surah({surah_number}) called")
            await self.audio_service.set_surah(surah_number)
            print(f"[DEBUG] Successfully jumped to surah {surah_number}")
        except Exception as e:
            print(f"[DEBUG] Error jumping to surah {surah_number}: {e}")
            traceback.print_exc()

    async def switch_reciter(self, reciter_name: str):
        """Switch to a different reciter."""
        try:
            print(f"[DEBUG] AudioServiceAdapter.switch_reciter({reciter_name}) called")
            await self.audio_service.set_reciter(reciter_name)
            print(f"[DEBUG] Successfully switched to reciter {reciter_name}")
        except Exception as e:
            print(f"[DEBUG] Error switching to reciter {reciter_name}: {e}")
            traceback.print_exc()

    async def skip_to_next(self):
        """Skip to the next surah."""
        try:
            print("[DEBUG] AudioServiceAdapter.skip_to_next() called")
            current_state = self.audio_service._current_state
            current_surah = getattr(
                getattr(current_state, "current_position", None), "surah_number", 1
            )
            next_surah = current_surah + 1 if current_surah < 114 else 1
            await self.audio_service.set_surah(next_surah)
            print(f"[DEBUG] Successfully skipped to next surah {next_surah}")
        except Exception as e:
            print(f"[DEBUG] Error skipping to next: {e}")
            traceback.print_exc()

    async def skip_to_previous(self):
        """Skip to the previous surah."""
        try:
            print("[DEBUG] AudioServiceAdapter.skip_to_previous() called")
            current_state = self.audio_service._current_state
            current_surah = getattr(
                getattr(current_state, "current_position", None), "surah_number", 1
            )
            previous_surah = current_surah - 1 if current_surah > 1 else 114
            await self.audio_service.set_surah(previous_surah)
            print(f"[DEBUG] Successfully skipped to previous surah {previous_surah}")
        except Exception as e:
            print(f"[DEBUG] Error skipping to previous: {e}")
            traceback.print_exc()

    def toggle_loop(self):
        """Toggle loop mode."""
        try:
            print("[DEBUG] AudioServiceAdapter.toggle_loop() called")
            current_state = self.audio_service._current_state
            if current_state and hasattr(current_state, "mode"):
                current_mode = getattr(current_state, "mode", "normal")
                if current_mode == PlaybackMode.LOOP_TRACK:
                    asyncio.create_task(
                        self.audio_service.set_playback_mode(PlaybackMode.NORMAL)
                    )
                else:
                    asyncio.create_task(
                        self.audio_service.set_playback_mode(PlaybackMode.LOOP_TRACK)
                    )
            print("[DEBUG] Successfully toggled loop mode")
        except Exception as e:
            print(f"[DEBUG] Error toggling loop: {e}")
            traceback.print_exc()

    def toggle_shuffle(self):
        """Toggle shuffle mode."""
        try:
            print("[DEBUG] AudioServiceAdapter.toggle_shuffle() called")
            current_state = self.audio_service._current_state
            if current_state and hasattr(current_state, "mode"):
                current_mode = getattr(current_state, "mode", "normal")
                if current_mode == PlaybackMode.SHUFFLE:
                    asyncio.create_task(
                        self.audio_service.set_playback_mode(PlaybackMode.NORMAL)
                    )
                else:
                    asyncio.create_task(
                        self.audio_service.set_playback_mode(PlaybackMode.SHUFFLE)
                    )
            print("[DEBUG] Successfully toggled shuffle mode")
        except Exception as e:
            print(f"[DEBUG] Error toggling shuffle: {e}")
            traceback.print_exc()

    async def pause_playback(self):
        """Pause audio playback."""
        try:
            print("[DEBUG] AudioServiceAdapter.pause_playback() called")
            success = await self.audio_service.pause_playback()
            if success:
                print("[DEBUG] Successfully paused playback")
            else:
                print("[DEBUG] Nothing to pause")
        except Exception as e:
            print(f"[DEBUG] Error pausing playback: {e}")
            traceback.print_exc()

    async def resume_playback(self):
        """Resume audio playback."""
        try:
            print("[DEBUG] AudioServiceAdapter.resume_playback() called")
            success = await self.audio_service.resume_playback()
            if success:
                print("[DEBUG] Successfully resumed playback")
            else:
                print("[DEBUG] Nothing to resume")
        except Exception as e:
            print(f"[DEBUG] Error resuming playback: {e}")
            traceback.print_exc()

    async def toggle_playback(self):
        """Toggle play/pause state."""
        try:
            print("[DEBUG] AudioServiceAdapter.toggle_playback() called")
            state = self.audio_service._current_state
            if state.is_playing:
                await self.pause_playback()
            elif state.is_paused:
                await self.resume_playback()
            else:
                print("[DEBUG] Starting playback from stopped state")
                await self.audio_service.start_playback(resume_position=True)
                print("[DEBUG] Successfully started playback")
        except Exception as e:
            print(f"[DEBUG] Error toggling playback: {e}")
            traceback.print_exc()


class ModernizedQuranBot:
    """Modernized QuranBot with dependency injection and 100% automated audio playback."""

    def __init__(self):
        self.container: DIContainer | None = None
        self.bot: commands.Bot | None = None
        self.logger: StructuredLogger | None = None
        self.config: BotConfig | None = None
        self.config_service: ConfigService | None = None
        self.is_running = False
        self._startup_start_time = time.time()

    async def initialize(self) -> bool:
        """Initialize the modernized bot with all services."""
        try:
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
                self.config_service = ConfigService()
                self.config = self.config_service.config
                log_status("Configuration loaded successfully", "✅")
            except Exception as e:
                log_critical_error(f"Configuration failed: {e}")
                return False

            # 2. Initialize DI container
            log_status("Setting up Dependency Injection", "🔧")
            self.container = DIContainer()

            # Register configuration services
            self.container.register_singleton(BotConfig, self.config)
            self.container.register_singleton(ConfigService, self.config_service)

            # 3. Initialize core services
            log_status("Initializing core services", "🛠️")

            # Structured Logger
            logger_factory = lambda: StructuredLogger(
                name="quranbot",
                level="INFO",
                log_file=project_root / "logs" / "quranbot.log",
                console_output=True,
            )
            self.container.register_singleton(StructuredLogger, logger_factory)
            self.logger = self.container.get(StructuredLogger)
            await self.logger.info("Structured logger initialized")

            # JSON services removed - now using SQLite for all data storage

            # Health Monitor - Comprehensive health monitoring with webhooks
            log_status("Initializing health monitoring system", "💚")
            from .health_monitor import HealthMonitor
            
            # Get webhook logger if available
            webhook_logger = None
            try:
                webhook_logger = self.container.get(ModernWebhookLogger)
            except:
                pass  # Webhook logger not available
            
            health_monitor = HealthMonitor(
                logger=self.logger,
                webhook_logger=webhook_logger,
                data_dir=project_root / "data",
                check_interval_minutes=60,  # Health reports every hour
                alert_interval_minutes=5    # Critical alerts every 5 minutes
            )
            
            # Start health monitoring
            await health_monitor.start_monitoring()
            self.container.register_singleton(HealthMonitor, health_monitor)
            
            # Set health monitor on services that need it
            try:
                metadata_cache = self.container.get(MetadataCache)
                metadata_cache.set_health_monitor(health_monitor)
            except:
                pass  # MetadataCache not available yet

            # Cache Service
            cache_config = self.config_service.create_cache_service_config()
            cache_factory = lambda: CacheService(
                container=self.container, config=cache_config, logger=self.logger
            )
            self.container.register_singleton(CacheService, cache_factory)

            # Performance Monitor
            perf_monitor_factory = lambda: PerformanceMonitor(
                container=self.container,
                logger=self.logger,
                collection_interval=30,
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

            # Webhook Logger (if enabled)
            try:
                if self.config_service.config.USE_WEBHOOK_LOGGING:
                    webhook_config = self.config_service.create_webhook_config()
                    webhook_factory = lambda: ModernWebhookLogger(
                        config=webhook_config,
                        logger=self.logger,
                        container=self.container,
                        bot=self,
                    )
                    self.container.register_singleton(
                        ModernWebhookLogger, webhook_factory
                    )
                    log_status("Webhook logger configured", "🔗")
                else:
                    log_status("Webhook logging disabled", "ℹ️")
            except Exception as e:
                await self.logger.warning(
                    "Failed to setup webhook logger",
                    {"error": str(e), "fallback": "Continuing without webhook logging"},
                )

            # Initialize all core services
            await self.container.get(CacheService).initialize()
            await self.container.get(PerformanceMonitor).initialize()
            await self.container.get(ResourceManager).initialize()
            # SecurityService initializes in constructor, no separate initialize() method

            # Initialize webhook logger if available
            try:
                webhook_logger = self.container.get(ModernWebhookLogger)
                if webhook_logger:
                    await webhook_logger.initialize()
                    log_status("Webhook logger initialized", "✅")
            except Exception as e:
                await self.logger.warning(
                    "Webhook logger initialization failed", {"error": str(e)}
                )

            log_status("Core services initialized", "✅")

            # 4. Initialize modern services
            log_status("Initializing modern services", "🎵")

            # Create Discord bot first (needed for audio service)
            intents = discord.Intents.default()
            intents.message_content = True
            intents.voice_states = True
            intents.guilds = True

            self.bot = commands.Bot(
                command_prefix="!", intents=intents, help_command=None
            )
            self.container.register_singleton(commands.Bot, self.bot)

            # Create metadata cache
            metadata_cache = MetadataCache(
                logger=self.logger, max_size=1000, enable_persistence=True
            )
            self.container.register_singleton(MetadataCache, metadata_cache)

            # Audio Service
            audio_config = self.config_service.create_audio_service_config()

            audio_factory = lambda: AudioService(
                container=self.container,
                bot=self.bot,
                config=audio_config,
                logger=self.logger,
                metadata_cache=metadata_cache,
            )
            self.container.register_singleton(AudioService, audio_factory)

            # SQLite State Service - Modern SQLite-based state management
            from ..services.sqlite_state_service import SQLiteStateService
            
            # Get webhook logger if available
            webhook_logger = None
            try:
                webhook_logger = self.container.get(ModernWebhookLogger)
            except:
                pass  # Webhook logger not available yet
            
            sqlite_state_service = SQLiteStateService(
                logger=self.logger,
                db_path=project_root / "data" / "quranbot.db"
            )
            
            # Set webhook logger on the database service
            if webhook_logger and hasattr(sqlite_state_service, 'db_service'):
                sqlite_state_service.db_service.webhook_logger = webhook_logger
            self.container.register_singleton(SQLiteStateService, sqlite_state_service)

            # State Service (legacy JSON support, backups disabled)
            state_config = self.config_service.create_state_service_config(project_root)

            state_factory = lambda: StateService(
                container=self.container, config=state_config, logger=self.logger
            )
            self.container.register_singleton(StateService, state_factory)

            # Initialize modern services
            await self.container.get(AudioService).initialize()
            await self.container.get(SQLiteStateService).initialize()
            await self.container.get(StateService).initialize()

            log_status("Modern services initialized", "✅")

            # 5. Initialize Rich Presence Manager
            log_status("Setting up Rich Presence", "🎮")

            rich_presence_factory = lambda: RichPresenceManager(
                client=self.bot, data_dir=project_root / "data"
            )
            self.container.register_singleton(
                RichPresenceManager, rich_presence_factory
            )

            log_status("Rich Presence initialized", "✅")

            # 6. All services initialized
            log_status("All services initialized", "✅")

            # 7. Initialize Discord bot
            log_status("Setting up Discord bot", "🤖")

            # Set up bot events
            await self._setup_bot_events()

            # Load commands
            await self._load_commands()

            log_status("Discord bot configured", "✅")

            await self.logger.info(
                "Modernized QuranBot initialized successfully",
                {
                    "version": BOT_VERSION,
                    "guild_id": self.config_service.get_guild_id(),
                    "services": "All modern services operational",
                },
            )

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

    async def _setup_bot_events(self):
        """Set up Discord bot events with modern service integration."""

        @self.bot.event
        async def on_ready():
            """Bot ready event - start automated audio playback immediately."""
            startup_end_time = time.time()
            startup_duration = startup_end_time - getattr(
                self, "_startup_start_time", startup_end_time
            )

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

            # Send startup webhook notification
            try:
                webhook_logger = self.container.get(ModernWebhookLogger)
                if webhook_logger and webhook_logger.initialized:
                    await webhook_logger.log_bot_startup(
                        version=BOT_VERSION,
                        startup_duration=startup_duration,
                        services_loaded=(
                            len(self.container._singletons)
                            if hasattr(self.container, "_singletons")
                            else 0
                        ),
                        guild_count=len(self.bot.guilds),
                    )
            except Exception as e:
                await self.logger.warning(
                    "Failed to send startup webhook", {"error": str(e)}
                )

            # **START AUTOMATED AUDIO PLAYBACK IMMEDIATELY**
            await self._start_automated_continuous_playback()

            # Initialize daily verses system
            try:
                daily_verse_channel_id = self.config.DAILY_VERSE_CHANNEL_ID
                if daily_verse_channel_id:
                    await setup_daily_verses(self.bot, daily_verse_channel_id)
                    await self.logger.info(
                        "Daily verses system initialized",
                        {"channel_id": daily_verse_channel_id},
                    )
                else:
                    await self.logger.warning(
                        "Daily verses system not initialized - channel ID not configured"
                    )
            except Exception as e:
                await self.logger.error(
                    "Failed to initialize daily verses system", {"error": str(e)}
                )

            # Initialize quiz system
            try:
                daily_verse_channel_id = self.config.DAILY_VERSE_CHANNEL_ID
                if daily_verse_channel_id:
                    from src.utils.quiz_manager import setup_quiz_system
                    await setup_quiz_system(self.bot, daily_verse_channel_id)
                    await self.logger.info(
                        "Quiz system initialized",
                        {"channel_id": daily_verse_channel_id},
                    )
                else:
                    await self.logger.warning(
                        "Quiz system not initialized - channel ID not configured"
                    )
            except Exception as e:
                await self.logger.error(
                    "Failed to initialize quiz system", {"error": str(e)}
                )

            # Initialize Mecca prayer notifications
            try:
                from src.utils.mecca_prayer_times import (
                    setup_mecca_prayer_notifications,
                )
                await setup_mecca_prayer_notifications(self.bot)
                await self.logger.info(
                    "Mecca prayer notification system initialized",
                    {"monitoring": "5 daily prayers in Holy City"},
                )
            except Exception as e:
                await self.logger.error(
                    "Failed to initialize Mecca prayer notifications", {"error": str(e)}
                )

            # Initialize Islamic AI mention listener
            try:
                from src.utils.islamic_ai_listener import setup_islamic_ai_listener
                await setup_islamic_ai_listener(self.bot, self.container)
                await self.logger.info(
                    "Islamic AI mention listener initialized",
                    {"trigger": "bot mentions", "model": "GPT-3.5 Turbo", "languages": "English + Arabic input", "rate_limit": "1 question/hour per user"},
                )
            except Exception as e:
                await self.logger.error(
                    "Failed to initialize Islamic AI listener", {"error": str(e)}
                )

        @self.bot.event
        async def on_error(event, *args, **kwargs):
            """Global error handler with modern logging."""
            await self.logger.error(
                "Discord event error",
                {"event": event, "args": str(args)[:500], "kwargs": str(kwargs)[:500]},
            )

            # Send error webhook for critical Discord events
            try:
                webhook_logger = self.container.get(ModernWebhookLogger)
                if webhook_logger and webhook_logger.initialized:
                    await webhook_logger.log_error(
                        title="Discord Event Error",
                        description=f"Error in Discord event: {event}",
                        context={
                            "event": event,
                            "args": str(args)[:500],
                            "kwargs": str(kwargs)[:500],
                        },
                        ping_owner=False,  # Don't ping for every Discord error
                    )
            except:
                pass  # Don't fail if webhook fails

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

            # Send user-friendly error message
            await ctx.send("❌ An error occurred while processing your command.")

        @self.bot.event
        async def on_voice_state_update(member, before, after):
            """Handle voice state changes for QuranBot voice channel activity and role management."""
            try:
                # Get services
                webhook_logger = self.container.get(ModernWebhookLogger)
                if not webhook_logger or not webhook_logger.initialized:
                    return

                audio_service = self.container.get(AudioService)
                target_channel_id = self.config_service.get_target_channel_id()

                # Only track activity for the QuranBot voice channel
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

                # Handle role management for Quran voice channel
                await self._handle_voice_channel_roles(member, before, after, target_channel_id)

                if joined_quran_vc:
                    # User joined QuranBot voice channel
                    try:
                        # Get current audio state for context
                        audio_state = await audio_service.get_playback_state()
                        current_surah = (
                            getattr(
                                audio_state.current_position, "surah_number", "Unknown"
                            )
                            if audio_state.current_position
                            else "Unknown"
                        )

                        await webhook_logger.log_voice_channel_activity(
                            activity_type="join",
                            user_name=member.display_name,
                            user_id=member.id,
                            channel_name=after.channel.name,
                            user_avatar_url=member.display_avatar.url,
                            additional_info={
                                "current_listeners": len(after.channel.members),
                                "current_surah": f"Surah {current_surah}",
                                "current_reciter": (
                                    audio_state.current_reciter
                                    if audio_state
                                    else "Unknown"
                                ),
                                "is_playing": (
                                    audio_state.is_playing if audio_state else False
                                ),
                            },
                        )
                    except Exception as e:
                        await self.logger.warning(
                            "Failed to send voice join webhook",
                            {"user_id": member.id, "error": str(e)},
                        )

                elif left_quran_vc:
                    # User left QuranBot voice channel
                    try:
                        remaining_members = (
                            len(before.channel.members) - 1
                        )  # Subtract the leaving member

                        await webhook_logger.log_voice_channel_activity(
                            activity_type="leave",
                            user_name=member.display_name,
                            user_id=member.id,
                            channel_name=before.channel.name,
                            user_avatar_url=member.display_avatar.url,
                            additional_info={
                                "remaining_listeners": remaining_members,
                                "left_at": f"<t:{int(time.time())}:T>",
                            },
                        )
                    except Exception as e:
                        await self.logger.warning(
                            "Failed to send voice leave webhook",
                            {"user_id": member.id, "error": str(e)},
                        )

            except Exception as e:
                await self.logger.error(
                    "Error in voice state update handler",
                    {"member_id": member.id if member else "unknown", "error": str(e)},
                )

    async def _handle_voice_channel_roles(self, member, before, after, target_channel_id):
        """Handle role assignment/removal for voice channel activity."""
        try:
            # Skip role management for bots
            if member.bot:
                return

            # Get panel access role ID from config
            panel_access_role_id = self.config.PANEL_ACCESS_ROLE_ID
            if not panel_access_role_id:
                return  # Role management disabled

            # Get the guild and role
            guild = member.guild
            if not guild:
                return

            panel_role = guild.get_role(panel_access_role_id)
            if not panel_role:
                await self.logger.warning(
                    "Panel access role not found",
                    {"role_id": panel_access_role_id, "guild_id": guild.id}
                )
                return

            # Check if user joined a voice channel (wasn't in VC, now is)
            if not before.channel and after.channel:
                # Only assign role if they joined the Quran voice channel specifically
                if after.channel.id == target_channel_id:
                    await self._assign_panel_access_role(member, panel_role, after.channel)

            # Check if user left all voice channels (was in VC, now isn't)
            elif before.channel and not after.channel:
                # Only remove role if they left the Quran voice channel
                if before.channel.id == target_channel_id:
                    await self._remove_panel_access_role(member, panel_role, before.channel)

            # Check if user moved between voice channels
            elif before.channel and after.channel and before.channel != after.channel:
                # If they left the Quran voice channel, remove role
                if before.channel.id == target_channel_id:
                    await self._remove_panel_access_role(member, panel_role, before.channel)

                # If they joined the Quran voice channel, assign role
                if after.channel.id == target_channel_id:
                    await self._assign_panel_access_role(member, panel_role, after.channel)

        except Exception as e:
            await self.logger.error(
                "Error in voice channel role management",
                {"member_id": member.id, "error": str(e)},
            )

    async def _assign_panel_access_role(self, member, panel_role, channel):
        """Assign the panel access role to a user who joined the Quran voice channel."""
        try:
            # Check if user already has the role
            if panel_role in member.roles:
                await self.logger.debug(
                    "User already has panel access role",
                    {"user": member.display_name, "role": panel_role.name}
                )
                return

            # Assign the role
            await member.add_roles(panel_role, reason="Joined Quran voice channel")

            await self.logger.info(
                "Panel access role assigned",
                {
                    "user": member.display_name,
                    "user_id": member.id,
                    "role": panel_role.name,
                    "role_id": panel_role.id,
                    "channel": channel.name,
                }
            )

        except discord.Forbidden:
            await self.logger.error(
                "No permission to assign panel access role",
                {
                    "user": member.display_name,
                    "role": panel_role.name,
                    "role_id": panel_role.id,
                }
            )
        except discord.HTTPException as e:
            await self.logger.error(
                "HTTP error while assigning panel access role",
                {
                    "user": member.display_name,
                    "error": str(e),
                    "role_id": panel_role.id,
                }
            )
        except Exception as e:
            await self.logger.error(
                "Unexpected error while assigning panel access role",
                {
                    "user": member.display_name,
                    "error": str(e),
                    "role_id": panel_role.id,
                }
            )

    async def _remove_panel_access_role(self, member, panel_role, channel):
        """Remove the panel access role from a user who left the Quran voice channel."""
        try:
            # Check if user has the role
            if panel_role not in member.roles:
                await self.logger.debug(
                    "User doesn't have panel access role to remove",
                    {"user": member.display_name, "role": panel_role.name}
                )
                return

            # Remove the role
            await member.remove_roles(panel_role, reason="Left Quran voice channel")

            await self.logger.info(
                "Panel access role removed",
                {
                    "user": member.display_name,
                    "user_id": member.id,
                    "role": panel_role.name,
                    "role_id": panel_role.id,
                    "channel": channel.name,
                }
            )

        except discord.Forbidden:
            await self.logger.error(
                "No permission to remove panel access role",
                {
                    "user": member.display_name,
                    "role": panel_role.name,
                    "role_id": panel_role.id,
                }
            )
        except discord.HTTPException as e:
            await self.logger.error(
                "HTTP error while removing panel access role",
                {
                    "user": member.display_name,
                    "error": str(e),
                    "role_id": panel_role.id,
                }
            )
        except Exception as e:
            await self.logger.error(
                "Unexpected error while removing panel access role",
                {
                    "user": member.display_name,
                    "error": str(e),
                    "role_id": panel_role.id,
                }
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
                        f"Auto-connecting to {self.config_service.get_target_channel_id()}",
                    ),
                    ("Playback", "Automatic progression through all 114 surahs"),
                ],
            )

            # Get services
            audio_service = self.container.get(AudioService)
            rich_presence = self.container.get(RichPresenceManager)

            # Connect Rich Presence to Audio Service
            log_status("Connecting Rich Presence to Audio Service", "🔗")

            # Start a task to monitor AudioService and update Rich Presence
            asyncio.create_task(
                self._monitor_audio_for_rich_presence(audio_service, rich_presence)
            )

            # Connect to voice channel automatically
            voice_channel_id = self.config_service.get_target_channel_id()
            guild_id = self.config_service.get_guild_id()
            connected = await audio_service.connect_to_voice_channel(
                voice_channel_id, guild_id
            )

            if not connected:
                await self.logger.error(
                    "Failed to connect to voice channel for automation",
                    {"channel_id": voice_channel_id},
                )
                return

            # Start continuous 24/7 playback with resume
            await audio_service.start_playback(resume_position=True)

            # Set up Control Panel after successful voice connection
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
        """Monitors the AudioService state and updates Rich Presence accordingly."""
        while True:
            try:
                # Get current playback state from AudioService
                playback_state = await audio_service.get_playback_state()

                if playback_state.is_playing:
                    # Get surah information for rich presence
                    surah_info = get_surah_info(
                        playback_state.current_position.surah_number
                    )

                    if surah_info:
                        # Update rich presence with current playback info using template
                        rich_presence.update_presence_with_template(
                            "listening",
                            {
                                "emoji": surah_info.emoji,  # Use specific surah emoji from control panel
                                "surah": surah_info.name_transliteration,
                                "verse": "1",  # Could be made dynamic if verse position is available
                                "total": str(surah_info.verses),
                                "reciter": playback_state.current_reciter,
                            },
                            silent=False,  # Enable logging to see what's happening
                        )
                    else:
                        # Fallback if surah info not found - try to get emoji by surah number
                        surah_number = playback_state.current_position.surah_number
                        fallback_surah_info = get_surah_info(surah_number)
                        emoji = (
                            fallback_surah_info.emoji if fallback_surah_info else "🎵"
                        )

                        rich_presence.update_presence(
                            status=f"{emoji} Surah {surah_number}",
                            details=f"Recited by {playback_state.current_reciter}",
                            state="Quran Recitation",
                            activity_type="listening",
                            silent=False,
                        )
                else:
                    # Update rich presence to show paused/stopped state
                    rich_presence.update_presence(
                        status="QuranBot",
                        details="Paused",
                        state="Ready to resume",
                        activity_type="playing",
                        silent=False,  # Enable logging
                    )

                # Wait before next update
                await asyncio.sleep(30)  # Update every 30 seconds

            except Exception as e:
                await self.logger.error(
                    "Error monitoring audio for rich presence", {"error": str(e)}
                )
                await asyncio.sleep(60)  # Wait longer on error

    async def _setup_control_panel(self, voice_channel_id: int, guild_id: int):
        """Set up the control panel with AudioService adapter."""
        try:
            log_status("Setting up Control Panel", "🎛️")

            # Get the audio service
            audio_service = self.container.get(AudioService)

            # Create adapter for compatibility with control panel
            audio_adapter = AudioServiceAdapter(audio_service)

            # Set up control panel with the adapter
            await setup_control_panel(
                bot=self.bot,
                channel_id=self.config_service.get_panel_channel_id(),
                audio_manager=audio_adapter,  # Use adapter instead of direct service
            )

            log_status("Control Panel configured", "✅")

        except Exception as e:
            await self.logger.error("Failed to set up control panel", {"error": str(e)})
            log_error_with_traceback("Control panel setup error", e)

    async def _load_commands(self):
        """Load Discord commands."""
        try:
            log_status("Loading Discord commands", "⚡")

            # Load commands
            await load_commands(self.bot, self.container)

            log_status("Discord commands loaded", "✅")

        except Exception as e:
            await self.logger.error("Failed to load commands", {"error": str(e)})
            log_error_with_traceback("Command loading error", e)

    async def run(self):
        """Start the modernized bot."""
        try:
            self.is_running = True

            # Initialize everything
            if not await self.initialize():
                log_critical_error("Failed to initialize bot")
                return False

            # Start the Discord bot
            log_status("Starting Discord bot", "🚀")
            await self.bot.start(self.config_service.get_discord_token())

        except KeyboardInterrupt:
            log_status("Received shutdown signal", "⏹️")
        except Exception as e:
            log_critical_error(f"Bot runtime error: {e}")

            # Send crash webhook notification
            try:
                if hasattr(self, "container") and self.container:
                    webhook_logger = self.container.get(ModernWebhookLogger)
                    if webhook_logger and webhook_logger.initialized:
                        await webhook_logger.log_bot_crash(
                            error_message="Bot encountered a critical runtime error",
                            exception=e,
                            crash_context={
                                "error_type": type(e).__name__,
                                "module": getattr(e, "__module__", "unknown"),
                                "uptime_seconds": int(
                                    time.time() - self._startup_start_time
                                ),
                            },
                            ping_owner=True,
                        )
            except:
                pass  # Don't fail if webhook fails during crash

            if self.logger:
                await self.logger.error(
                    "Bot runtime error",
                    {"error": str(e), "error_type": type(e).__name__},
                )
        finally:
            await self.shutdown()

    async def shutdown(self):
        """Gracefully shutdown all services."""
        if not self.is_running:
            return

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

            # Send shutdown webhook notification
            try:
                webhook_logger = self.container.get(ModernWebhookLogger)
                if webhook_logger and webhook_logger.initialized:
                    uptime_seconds = time.time() - self._startup_start_time
                    uptime_str = (
                        f"{uptime_seconds/3600:.1f} hours"
                        if uptime_seconds > 3600
                        else f"{uptime_seconds/60:.1f} minutes"
                    )

                    await webhook_logger.log_bot_shutdown(
                        reason="Graceful shutdown requested",
                        uptime=uptime_str,
                        final_stats={
                            "guilds_connected": len(self.bot.guilds) if self.bot else 0,
                            "uptime_seconds": int(uptime_seconds),
                        },
                    )
            except Exception as e:
                if self.logger:
                    await self.logger.warning(
                        "Failed to send shutdown webhook", {"error": str(e)}
                    )

            # Stop Discord bot
            if self.bot and not self.bot.is_closed():
                log_status("Disconnecting from Discord", "📡")
                await self.bot.close()

            # Shutdown services in reverse order
            if self.container:
                log_status("Shutting down services", "🛠️")

                try:
                    state_service = self.container.get(StateService)
                    await state_service.shutdown()
                except:
                    pass

                try:
                    audio_service = self.container.get(AudioService)
                    await audio_service.shutdown()
                except:
                    pass

                try:
                    performance_monitor = self.container.get(PerformanceMonitor)
                    await performance_monitor.shutdown()
                except:
                    pass

                try:
                    resource_manager = self.container.get(ResourceManager)
                    await resource_manager.shutdown()
                except:
                    pass

                try:
                    cache_service = self.container.get(CacheService)
                    await cache_service.shutdown()
                except:
                    pass

                try:
                    webhook_logger = self.container.get(ModernWebhookLogger)
                    if webhook_logger:
                        await webhook_logger.shutdown()
                except:
                    pass

            log_status("All services stopped", "✅")

            if self.logger:
                await self.logger.info("Graceful shutdown completed")

        except Exception as e:
            log_critical_error(f"Shutdown error: {e}")
        finally:
            self.is_running = False


# =============================================================================
# Instance Detection and Management
# =============================================================================
# This section handles multiple bot instance detection and management.
# It's crucial for preventing conflicts and ensuring clean bot operation.
#
# Key Capabilities:
# - Detects other running QuranBot instances
# - Automatically terminates conflicting instances
# - Provides detailed logging of instance management
# - Ensures only one bot instance runs per directory
# =============================================================================


def check_existing_instances():
    """
    Detect and automatically terminate existing bot instances.

    Scans running processes to find other QuranBot instances and stops them
    to prevent conflicts. Uses PID matching and working directory verification.

    Returns:
        bool: True if safe to proceed, False if critical error occurred
    """

    current_pid = os.getpid()
    bot_processes = []

    try:
        # Scan all running processes for QuranBot instances
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                # Skip current process
                if proc.info["pid"] == current_pid:
                    continue

                # Check for Python processes that might be running QuranBot
                if proc.info["name"] and "python" in proc.info["name"].lower():
                    cmdline = proc.info["cmdline"]
                    if cmdline:
                        cmdline_str = " ".join(cmdline)

                        # Look for main.py in command line
                        if "main.py" in cmdline_str:
                            try:
                                # Verify it's actually QuranBot by checking working directory
                                proc_cwd = proc.cwd()
                                current_cwd = os.getcwd()

                                if "QuranBot" in proc_cwd:
                                    # Check if it's the same project directory
                                    if os.path.normpath(proc_cwd) == os.path.normpath(
                                        current_cwd
                                    ):
                                        bot_processes.append(proc)
                                    elif "QuranBot" in proc_cwd:
                                        bot_processes.append(proc)

                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                # Process ended or access denied - skip for safety
                                continue

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Process might have ended or we don't have access - continue scanning
                continue

    except Exception as e:
        log_error_with_traceback("Process scanning failed during instance detection", e)
        log_perfect_tree_section(
            "Instance Detection - Warning",
            [
                ("detection_result", "⚠️ Proceeding without complete instance check"),
            ],
            "⚠️",
        )
        return True

    # Process detection results
    if not bot_processes:
        log_perfect_tree_section(
            "Instance Detection",
            [
                ("existing_instances", "None detected"),
                ("detection_result", "✅ Safe to proceed"),
            ],
            "🔍",
        )
        return True

    # Found existing instances - prepare to stop them
    instance_items = [
        ("existing_instances", f"{len(bot_processes)} found"),
    ]

    for i, proc in enumerate(bot_processes, 1):
        try:
            cmdline_display = (
                " ".join(proc.cmdline()[:3]) + "..."
                if len(proc.cmdline()) > 3
                else " ".join(proc.cmdline())
            )
            instance_items.append(
                (f"instance_{i}", f"PID {proc.pid} - {cmdline_display}")
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            instance_items.append(
                (f"instance_{i}", f"PID {proc.pid} - (process ended)")
            )

    instance_items.append(
        ("detection_result", "🤖 Automatically stopping existing instances")
    )

    log_perfect_tree_section(
        "Instance Detection",
        instance_items,
        "🔍",
    )
    log_spacing()

    # Automatically terminate existing instances
    return stop_existing_instances(bot_processes)


def stop_existing_instances(bot_processes):
    """
    Terminate existing bot instances gracefully with fallback to force kill.

    Attempts graceful shutdown first, then force kills if necessary.
    Tracks success/failure rates and provides detailed logging.

    Args:
        bot_processes: List of psutil.Process objects to terminate

    Returns:
        bool: True if termination completed (regardless of individual failures)
    """

    stopped_count = 0
    failed_count = 0
    termination_items = []

    for i, proc in enumerate(bot_processes, 1):
        try:
            termination_items.append((f"terminating_{i}", f"PID {proc.pid}"))

            # Attempt graceful termination first
            proc.terminate()

            # Wait for graceful shutdown with timeout
            try:
                proc.wait(timeout=5)
                termination_items.append(
                    (f"result_{i}", f"PID {proc.pid} - Graceful shutdown")
                )
                stopped_count += 1

            except psutil.TimeoutExpired:
                # Graceful shutdown failed - force kill
                termination_items.append(
                    (f"forcing_{i}", f"PID {proc.pid} - Timeout, force killing")
                )
                proc.kill()
                proc.wait(timeout=3)
                termination_items.append(
                    (f"result_{i}", f"PID {proc.pid} - Force killed")
                )
                stopped_count += 1

        except psutil.NoSuchProcess:
            termination_items.append(
                (f"result_{i}", f"PID {proc.pid} - Already terminated")
            )
            stopped_count += 1

        except psutil.AccessDenied:
            termination_items.append((f"result_{i}", f"PID {proc.pid} - Access denied"))
            failed_count += 1

        except Exception as e:
            log_error_with_traceback(f"Failed to terminate process PID {proc.pid}", e)
            termination_items.append(
                (f"result_{i}", f"PID {proc.pid} - Error occurred")
            )
            failed_count += 1

    # Allow time for processes to fully terminate
    if bot_processes:
        termination_items.append(
            ("cleanup_wait", "Waiting for processes to terminate...")
        )
        time.sleep(2)

    # Report final termination results
    if failed_count == 0:
        termination_items.append(
            ("termination_result", f"✅ All {stopped_count} instances terminated")
        )
        log_perfect_tree_section(
            "Instance Termination",
            termination_items,
            "🛑",
        )
    else:
        termination_items.append(
            ("termination_result", f"⚠️ {stopped_count} stopped, {failed_count} failed")
        )
        log_perfect_tree_section(
            "Instance Termination",
            termination_items,
            "🛑",
        )

    return True  # Continue execution regardless of individual failures


# =============================================================================
# Bot Initialization and Startup
# =============================================================================
# This section manages the bot's lifecycle from startup to shutdown.
#
# Implementation Details:
# - Initializes core bot systems and dependencies
# - Handles Discord connection management
# - Provides comprehensive error handling
# - Manages graceful shutdowns (both user-triggered and automatic)
# - Maintains state persistence across sessions
#
# Error Handling:
# - Catches and logs all runtime errors
# - Handles Discord-specific connection issues
# - Provides detailed crash reports for debugging
# - Ensures clean shutdown even during errors
# =============================================================================


# =============================================================================
# Main Entry Point
# =============================================================================
# Primary execution entry point for QuranBot using modernized architecture
#
# Startup Flow:
# 1. Initialize logging system with unique run ID
# 2. Perform instance detection and conflict resolution
# 3. Initialize modernized bot with dependency injection
# 4. Start automated continuous playback
# 5. Monitor for shutdown triggers or errors
# 6. Perform graceful shutdown and cleanup
#
# Usage:
# - Run directly: python main.py
# - Environment Setup: Ensure DISCORD_TOKEN is set in config/.env
# - Dependencies: See pyproject.toml for necessary packages
# - Logs: Check logs/ directory for detailed operation logs
# =============================================================================


async def main():
    """Main entry point for the modernized bot."""

    # Set up signal handlers for graceful shutdown
    bot_instance = None

    def signal_handler(signum, frame):
        """Handle shutdown signals."""
        print(f"\nReceived signal {signum}, initiating graceful shutdown...")
        if bot_instance:
            # Create a task to shutdown the bot and then stop the event loop
            async def shutdown_and_exit():
                await bot_instance.shutdown()
                # Get the current event loop and stop it
                loop = asyncio.get_running_loop()
                loop.stop()

            asyncio.create_task(shutdown_and_exit())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Initialize logging session
    log_run_separator()
    run_id = log_run_header(BOT_NAME, BOT_VERSION)

    try:
        # Phase 1: Instance Detection and Management
        if not check_existing_instances():
            log_critical_error("Instance detection failed", "Cannot proceed safely")
            log_run_end(run_id, "Instance detection failure")
            sys.exit(1)

        # Phase 2: Create and run the modernized bot
        bot_instance = ModernizedQuranBot()
        await bot_instance.run()

        # Phase 3: Clean Exit
        log_run_end(run_id, "Normal shutdown")

    except KeyboardInterrupt:
        log_spacing()
        log_perfect_tree_section(
            "User Shutdown",
            [
                ("shutdown_reason", "User interrupt (Ctrl+C)"),
                ("shutdown_status", "✅ Graceful shutdown completed"),
            ],
            "👋",
        )
        log_run_end(run_id, "User shutdown")
    except Exception as e:
        # Critical error in main entry point
        log_spacing()
        log_critical_error("Fatal error in main entry point", e)
        log_perfect_tree_section(
            "Critical Error",
            [
                ("critical_status", "💥 Application failed to start"),
            ],
            "💥",
        )
        log_run_end(run_id, f"Critical failure: {e!s}")
        sys.exit(1)


if __name__ == "__main__":
    # Ensure we're in the right directory
    os.chdir(project_root)

    # Run the modernized bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot shutdown requested by user")
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        sys.exit(1)
