"""QuranBot - Enhanced Multi-Channel Webhook Router.

This router intelligently categorizes and routes webhook events to different
Discord channels based on event type and content. It provides specialized
formatting and routing for bot-focused events while maintaining backward
compatibility with the existing webhook system.

The Enhanced Webhook Router provides:
- Intelligent event categorization and channel routing
- Multi-channel Discord webhook support for organized logging
- Rich visualization capabilities for analytics and metrics
- Specialized formatting for different event types
- Backward compatibility with legacy single webhook systems
- Performance monitoring and visualization
- Daily report generation with charts and statistics
- Real-time system health monitoring

Classes:
    WebhookChannel: Enumeration of available webhook channels
    EventCategory: Event categories for intelligent routing
    EnhancedWebhookRouter: Main router class with multi-channel support
    
Features:
    - Automatic event categorization based on content analysis
    - Channel-specific formatting and enhancement
    - Rich visualizations with progress bars, gauges, and charts
    - Fallback support for legacy webhook configurations
    - Comprehensive logging methods for all QuranBot events
    - Performance metrics visualization
    - Daily analytics reporting with visual elements
"""

import asyncio
from datetime import datetime
from enum import Enum
import time
from typing import Any, Dict, List, Optional, Union

from .webhook_logger import (
    ModernWebhookLogger,
    WebhookConfig,
    WebhookMessage,
    EmbedField,
    LogLevel,
)
from .structured_logger import StructuredLogger
from src.config.bot_config import BotConfig
from .webhook_visualizations import (
    VisualizationBuilder,
    ChartType,
    ChartColors,
    quick_progress,
    quick_sparkline,
    quick_gauge,
)


class WebhookChannel(Enum):
    """Available webhook channels for different event types.
    
    Defines the available Discord webhook channels for organized event logging.
    Each channel is optimized for specific types of events and information.
    
    Attributes:
        BOT_STATUS: Bot lifecycle, health, and system events
        QURAN_AUDIO: Audio playback, voice channel, and recitation events
        COMMANDS_PANEL: Command usage and control panel interactions
        USER_ACTIVITY: User engagement, quiz activity, and Islamic learning
        DATA_ANALYTICS: Database operations, state management, and metrics
        ERRORS_ALERTS: Error messages, warnings, and system recovery
        DAILY_REPORTS: Daily statistics, analytics summaries, and reports
    """
    
    BOT_STATUS = "bot_status"
    QURAN_AUDIO = "quran_audio"
    COMMANDS_PANEL = "commands_panel"
    USER_ACTIVITY = "user_activity"
    DATA_ANALYTICS = "data_analytics"
    ERRORS_ALERTS = "errors_alerts"
    DAILY_REPORTS = "daily_reports"


class EventCategory(Enum):
    """Event categories for intelligent routing.
    
    Categorizes events based on their type and content for intelligent
    routing to appropriate webhook channels. This enables organized
    and contextual logging across different Discord channels.
    
    Bot Status & Health Categories:
        BOT_LIFECYCLE: Startup, shutdown, restart events
        SYSTEM_HEALTH: Health checks, monitoring alerts
        CONNECTION_STATUS: Discord connection events
    
    Quran Audio & Playback Categories:
        AUDIO_PLAYBACK: Audio streaming and playback events
        VOICE_CHANNEL: Voice channel activity and management
        AUDIO_CONTROL: Audio control and configuration changes
    
    Commands & Panel Categories:
        SLASH_COMMANDS: Discord slash command usage
        CONTROL_PANEL: Interactive control panel usage
        BOT_INTERACTIONS: General bot interaction events
    
    User Activity Categories:
        USER_ENGAGEMENT: User interaction and engagement metrics
        QUIZ_ACTIVITY: Quiz participation and results
        ISLAMIC_LEARNING: Islamic education and learning events
    
    Data & Analytics Categories:
        DATABASE_OPS: Database operations and queries
        STATE_MANAGEMENT: State persistence and management
        PERFORMANCE_METRICS: Performance monitoring and metrics
    
    Error & Alert Categories:
        ERROR_CRITICAL: Critical errors requiring attention
        ERROR_WARNING: Warning messages and non-critical issues
        SYSTEM_RECOVERY: System recovery and restoration events
    
    Report Categories:
        ANALYTICS_SUMMARY: Analytics summaries and insights
        DAILY_STATS: Daily statistics and usage reports
        USAGE_REPORTS: Usage patterns and trend reports
    """
    
    # Bot Status & Health
    BOT_LIFECYCLE = "bot_lifecycle"
    SYSTEM_HEALTH = "system_health"
    CONNECTION_STATUS = "connection_status"
    
    # Quran Audio & Playback
    AUDIO_PLAYBACK = "audio_playback"
    VOICE_CHANNEL = "voice_channel"
    AUDIO_CONTROL = "audio_control"
    
    # Commands & Panel
    SLASH_COMMANDS = "slash_commands"
    CONTROL_PANEL = "control_panel"
    BOT_INTERACTIONS = "bot_interactions"
    
    # User Activity
    USER_ENGAGEMENT = "user_engagement"
    QUIZ_ACTIVITY = "quiz_activity"
    ISLAMIC_LEARNING = "islamic_learning"
    
    # Data & Analytics
    DATABASE_OPS = "database_ops"
    STATE_MANAGEMENT = "state_management"
    PERFORMANCE_METRICS = "performance_metrics"
    
    # Errors & Alerts
    ERROR_CRITICAL = "error_critical"
    ERROR_WARNING = "error_warning"
    SYSTEM_RECOVERY = "system_recovery"
    
    # Daily Reports
    ANALYTICS_SUMMARY = "analytics_summary"
    DAILY_STATS = "daily_stats"
    USAGE_REPORTS = "usage_reports"


class EnhancedWebhookRouter:
    """Enhanced webhook router for multi-channel Discord logging.
    
    This router intelligently categorizes webhook events and routes them to
    appropriate Discord channels while providing specialized formatting for
    different event types. It builds on the existing ModernWebhookLogger
    infrastructure.
    
    The Enhanced Webhook Router provides comprehensive logging capabilities:
    - Automatic event categorization based on content analysis
    - Multi-channel routing for organized Discord notifications
    - Rich visualization support for analytics and metrics
    - Channel-specific formatting and enhancement
    - Fallback support for legacy single webhook configurations
    - Performance monitoring with visual indicators
    - Daily reporting with charts and statistics
    
    Architecture:
        - Uses multiple ModernWebhookLogger instances for different channels
        - Implements intelligent event categorization algorithms
        - Provides specialized methods for different event types
        - Includes rich visualization capabilities
        - Maintains backward compatibility with legacy systems
    
    Attributes:
        config: Bot configuration with webhook URLs
        logger: Structured logger for internal logging
        container: Optional dependency injection container
        bot: Optional Discord bot instance for metadata
        _webhook_loggers: Dictionary of webhook loggers per channel
        _event_routing_map: Mapping of event categories to channels
        _fallback_logger: Legacy webhook logger for backward compatibility
        initialized: Initialization status flag
        _closed: Shutdown status flag
    """
    
    def __init__(
        self,
        config: BotConfig,
        logger: StructuredLogger,
        container: Any = None,
        bot: Any = None,
    ) -> None:
        """Initialize the enhanced webhook router.
        
        Sets up the multi-channel webhook router with intelligent event
        categorization and routing capabilities.
        
        Args:
            config: Bot configuration with webhook URLs for different channels
            logger: Structured logger for internal logging and debugging
            container: Optional dependency injection container
            bot: Optional Discord bot instance for metadata and context
        """
        self.config = config
        self.logger = logger
        self.container = container
        self.bot = bot
        
        # Initialize webhook loggers for each channel
        self._webhook_loggers: Dict[WebhookChannel, Optional[ModernWebhookLogger]] = {}
        self._event_routing_map = self._build_event_routing_map()
        
        # Fallback logger for legacy support
        self._fallback_logger: Optional[ModernWebhookLogger] = None
        
        # State tracking
        self.initialized = False
        self._closed = False
        
    async def initialize(self) -> bool:
        """Initialize all webhook loggers for available channels.
        
        Creates ModernWebhookLogger instances for each configured webhook channel
        and initializes them for use. Also sets up fallback logger for legacy support.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            await self.logger.info("Initializing enhanced webhook router")
            
            # Initialize loggers for each configured webhook channel
            initialized_count = 0
            
            for channel in WebhookChannel:
                webhook_url = self.config.get_webhook_url(channel.value)
                if webhook_url:
                    webhook_config = WebhookConfig(
                        webhook_url=webhook_url,
                        owner_user_id=self.config.DEVELOPER_ID,
                        max_logs_per_minute=15,  # Higher limit for specialized channels
                        timezone="US/Eastern",
                        enable_pings=True,
                    )
                    
                    webhook_logger = ModernWebhookLogger(
                        config=webhook_config,
                        logger=self.logger,
                        container=self.container,
                        bot=self.bot,
                    )
                    
                    if await webhook_logger.initialize():
                        self._webhook_loggers[channel] = webhook_logger
                        initialized_count += 1
                        await self.logger.debug(
                            f"Initialized webhook logger for {channel.value}",
                            {"webhook_url": webhook_url[:50] + "..."}
                        )
                    else:
                        self._webhook_loggers[channel] = None
                        await self.logger.warning(
                            f"Failed to initialize webhook logger for {channel.value}"
                        )
                else:
                    self._webhook_loggers[channel] = None
            
            # Initialize fallback logger if legacy webhook URL is available
            if self.config.DISCORD_WEBHOOK_URL:
                fallback_config = WebhookConfig(
                    webhook_url=self.config.DISCORD_WEBHOOK_URL,
                    owner_user_id=self.config.DEVELOPER_ID,
                    timezone="US/Eastern",
                )
                
                self._fallback_logger = ModernWebhookLogger(
                    config=fallback_config,
                    logger=self.logger,
                    container=self.container,
                    bot=self.bot,
                )
                
                await self._fallback_logger.initialize()
            
            self.initialized = True
            
            await self.logger.info(
                "Enhanced webhook router initialized successfully",
                {
                    "initialized_channels": initialized_count,
                    "total_channels": len(WebhookChannel),
                    "has_fallback": bool(self._fallback_logger),
                }
            )
            
            return True
            
        except Exception as e:
            await self.logger.error(
                "Failed to initialize enhanced webhook router",
                {"error": str(e)}
            )
            return False
    
    async def shutdown(self) -> None:
        """Shutdown all webhook loggers gracefully.
        
        Performs orderly shutdown of all webhook loggers including
        both channel-specific loggers and the fallback logger.
        """
        if self._closed:
            return
            
        self._closed = True
        
        try:
            await self.logger.info("Shutting down enhanced webhook router")
            
            # Shutdown all channel loggers
            for channel, webhook_logger in self._webhook_loggers.items():
                if webhook_logger:
                    try:
                        await webhook_logger.shutdown()
                    except Exception as e:
                        await self.logger.warning(
                            f"Error shutting down {channel.value} webhook logger",
                            {"error": str(e)}
                        )
            
            # Shutdown fallback logger
            if self._fallback_logger:
                try:
                    await self._fallback_logger.shutdown()
                except Exception as e:
                    await self.logger.warning(
                        "Error shutting down fallback webhook logger",
                        {"error": str(e)}
                    )
            
            await self.logger.info("Enhanced webhook router shutdown completed")
            
        except Exception as e:
            await self.logger.error(
                "Error during enhanced webhook router shutdown",
                {"error": str(e)}
            )
    
    def _build_event_routing_map(self) -> Dict[EventCategory, WebhookChannel]:
        """Build the mapping of event categories to webhook channels.
        
        Creates the routing table that maps event categories to their
        appropriate webhook channels for organized logging.
        
        Returns:
            Dict[EventCategory, WebhookChannel]: Mapping of categories to channels
        """
        return {
            # Bot Status & Health -> BOT_STATUS channel
            EventCategory.BOT_LIFECYCLE: WebhookChannel.BOT_STATUS,
            EventCategory.SYSTEM_HEALTH: WebhookChannel.BOT_STATUS,
            EventCategory.CONNECTION_STATUS: WebhookChannel.BOT_STATUS,
            
            # Quran Audio & Playback -> QURAN_AUDIO channel
            EventCategory.AUDIO_PLAYBACK: WebhookChannel.QURAN_AUDIO,
            EventCategory.VOICE_CHANNEL: WebhookChannel.QURAN_AUDIO,
            EventCategory.AUDIO_CONTROL: WebhookChannel.QURAN_AUDIO,
            
            # Commands & Panel -> COMMANDS_PANEL channel
            EventCategory.SLASH_COMMANDS: WebhookChannel.COMMANDS_PANEL,
            EventCategory.CONTROL_PANEL: WebhookChannel.COMMANDS_PANEL,
            EventCategory.BOT_INTERACTIONS: WebhookChannel.COMMANDS_PANEL,
            
            # User Activity -> USER_ACTIVITY channel
            EventCategory.USER_ENGAGEMENT: WebhookChannel.USER_ACTIVITY,
            EventCategory.QUIZ_ACTIVITY: WebhookChannel.USER_ACTIVITY,
            EventCategory.ISLAMIC_LEARNING: WebhookChannel.USER_ACTIVITY,
            
            # Data & Analytics -> DATA_ANALYTICS channel
            EventCategory.DATABASE_OPS: WebhookChannel.DATA_ANALYTICS,
            EventCategory.STATE_MANAGEMENT: WebhookChannel.DATA_ANALYTICS,
            EventCategory.PERFORMANCE_METRICS: WebhookChannel.DATA_ANALYTICS,
            
            # Errors & Alerts -> ERRORS_ALERTS channel
            EventCategory.ERROR_CRITICAL: WebhookChannel.ERRORS_ALERTS,
            EventCategory.ERROR_WARNING: WebhookChannel.ERRORS_ALERTS,
            EventCategory.SYSTEM_RECOVERY: WebhookChannel.ERRORS_ALERTS,
            
            # Daily Reports -> DAILY_REPORTS channel
            EventCategory.ANALYTICS_SUMMARY: WebhookChannel.DAILY_REPORTS,
            EventCategory.DAILY_STATS: WebhookChannel.DAILY_REPORTS,
            EventCategory.USAGE_REPORTS: WebhookChannel.DAILY_REPORTS,
        }
    
    def _categorize_event(self, event_type: str, context: Dict[str, Any] = None) -> EventCategory:
        """Categorize an event based on its type and context.
        
        Uses keyword analysis and context information to intelligently
        categorize events for appropriate channel routing.
        
        Args:
            event_type: String describing the event type
            context: Optional context information for categorization
            
        Returns:
            EventCategory: Determined event category for routing
        """
        event_type_lower = event_type.lower()
        
        # Bot lifecycle events
        if any(keyword in event_type_lower for keyword in ['startup', 'shutdown', 'crash', 'restart']):
            return EventCategory.BOT_LIFECYCLE
        
        # Connection status events
        if any(keyword in event_type_lower for keyword in ['connect', 'disconnect', 'reconnect', 'connection']):
            return EventCategory.CONNECTION_STATUS
        
        # Audio playback events
        if any(keyword in event_type_lower for keyword in ['audio', 'playback', 'surah', 'reciter', 'play', 'pause', 'stop']):
            return EventCategory.AUDIO_PLAYBACK
        
        # Voice channel events
        if any(keyword in event_type_lower for keyword in ['voice', 'channel']):
            return EventCategory.VOICE_CHANNEL
        
        # Command events
        if any(keyword in event_type_lower for keyword in ['command', 'slash', 'interaction']):
            return EventCategory.SLASH_COMMANDS
        
        # Control panel events
        if any(keyword in event_type_lower for keyword in ['panel', 'control', 'button']):
            return EventCategory.CONTROL_PANEL
        
        # Quiz activity
        if any(keyword in event_type_lower for keyword in ['quiz', 'question', 'answer']):
            return EventCategory.QUIZ_ACTIVITY
        
        # User activity
        if any(keyword in event_type_lower for keyword in ['user', 'activity', 'engagement']):
            return EventCategory.USER_ENGAGEMENT
        
        # Database operations
        if any(keyword in event_type_lower for keyword in ['database', 'db', 'save', 'load', 'backup']):
            return EventCategory.DATABASE_OPS
        
        # State management
        if any(keyword in event_type_lower for keyword in ['state', 'session', 'statistics']):
            return EventCategory.STATE_MANAGEMENT
        
        # Error categories
        if any(keyword in event_type_lower for keyword in ['error', 'exception', 'fail', 'critical']):
            return EventCategory.ERROR_CRITICAL
        
        if any(keyword in event_type_lower for keyword in ['warning', 'warn']):
            return EventCategory.ERROR_WARNING
        
        # Recovery events
        if any(keyword in event_type_lower for keyword in ['recovery', 'recover', 'restored']):
            return EventCategory.SYSTEM_RECOVERY
        
        # Performance metrics
        if any(keyword in event_type_lower for keyword in ['performance', 'metrics', 'latency', 'memory']):
            return EventCategory.PERFORMANCE_METRICS
        
        # Daily reports
        if any(keyword in event_type_lower for keyword in ['daily', 'report', 'summary', 'analytics']):
            return EventCategory.ANALYTICS_SUMMARY
        
        # Default to system health for unknown events
        return EventCategory.SYSTEM_HEALTH
    
    def _get_webhook_logger(self, channel: WebhookChannel) -> Optional[ModernWebhookLogger]:
        """Get the webhook logger for a specific channel with fallback.
        
        Retrieves the webhook logger for the specified channel, falling back
        to the legacy single webhook logger if channel-specific logger is unavailable.
        
        Args:
            channel: Target webhook channel
            
        Returns:
            Optional[ModernWebhookLogger]: Webhook logger instance or None
        """
        # Try to get the specific channel logger
        logger = self._webhook_loggers.get(channel)
        if logger:
            return logger
        
        # Fallback to legacy webhook logger
        return self._fallback_logger
    
    async def route_event(
        self,
        event_type: str,
        title: str,
        description: str,
        level: LogLevel = LogLevel.INFO,
        context: Dict[str, Any] = None,
        force_channel: Optional[WebhookChannel] = None,
        **kwargs
    ) -> bool:
        """Route an event to the appropriate webhook channel.
        
        Intelligently categorizes the event and routes it to the most appropriate
        Discord webhook channel. Provides channel-specific formatting and enhancement.
        
        Args:
            event_type: Type of event for categorization (e.g., 'audio_playback', 'user_command')
            title: Event title for the webhook message
            description: Detailed event description
            level: Log level (INFO, WARNING, ERROR, CRITICAL, SUCCESS, SYSTEM)
            context: Additional context information as key-value pairs
            force_channel: Force event to specific channel (overrides intelligent routing)
            **kwargs: Additional arguments for webhook message formatting
            
        Returns:
            bool: True if event was successfully routed and sent, False otherwise
        """
        if not self.initialized or self._closed:
            return False
        
        try:
            # Determine target channel
            if force_channel:
                target_channel = force_channel
            else:
                event_category = self._categorize_event(event_type, context)
                target_channel = self._event_routing_map.get(event_category, WebhookChannel.BOT_STATUS)
            
            # Get the appropriate webhook logger
            webhook_logger = self._get_webhook_logger(target_channel)
            if not webhook_logger:
                await self.logger.warning(
                    f"No webhook logger available for channel {target_channel.value}",
                    {"event_type": event_type, "title": title}
                )
                return False
            
            # Add channel-specific formatting
            enhanced_title = self._enhance_title_for_channel(title, target_channel)
            enhanced_description = self._enhance_description_for_channel(description, target_channel, event_type)
            
            # Create fields from context
            fields = []
            if context:
                for key, value in context.items():
                    fields.append(
                        EmbedField(key.replace("_", " ").title(), str(value)[:1024], True)
                    )
            
            # Create and send webhook message
            message = WebhookMessage(
                title=enhanced_title,
                description=enhanced_description,
                level=level,
                fields=fields,
                **kwargs
            )
            
            # Route to appropriate method based on level
            if level == LogLevel.CRITICAL:
                success = await webhook_logger.log_critical(
                    enhanced_title,
                    enhanced_description,
                    context=context
                )
            elif level == LogLevel.ERROR:
                success = await webhook_logger.log_error(
                    enhanced_title,
                    enhanced_description,
                    context=context
                )
            elif level == LogLevel.WARNING:
                success = await webhook_logger.log_warning(
                    enhanced_title,
                    enhanced_description,
                    context=context
                )
            elif level == LogLevel.SUCCESS:
                success = await webhook_logger.log_success(
                    enhanced_title,
                    enhanced_description,
                    context=context
                )
            elif level == LogLevel.SYSTEM:
                success = await webhook_logger.log_system(
                    enhanced_title,
                    enhanced_description,
                    context=context
                )
            else:  # INFO and others
                success = await webhook_logger.log_info(
                    enhanced_title,
                    enhanced_description,
                    context=context
                )
            
            if success:
                await self.logger.debug(
                    "Event routed successfully",
                    {
                        "event_type": event_type,
                        "target_channel": target_channel.value,
                        "level": level.value,
                        "title": title
                    }
                )
            
            return success
            
        except Exception as e:
            await self.logger.error(
                "Failed to route webhook event",
                {
                    "event_type": event_type,
                    "title": title,
                    "error": str(e)
                }
            )
            return False
    
    def _enhance_title_for_channel(self, title: str, channel: WebhookChannel) -> str:
        """Add channel-specific enhancements to the title.
        
        Adds appropriate emoji prefixes and formatting based on the target channel.
        
        Args:
            title: Original message title
            channel: Target webhook channel
            
        Returns:
            str: Enhanced title with channel-appropriate formatting
        """
        channel_prefixes = {
            WebhookChannel.BOT_STATUS: "🤖",
            WebhookChannel.QURAN_AUDIO: "🎵",
            WebhookChannel.COMMANDS_PANEL: "⚡",
            WebhookChannel.USER_ACTIVITY: "👤",
            WebhookChannel.DATA_ANALYTICS: "📊",
            WebhookChannel.ERRORS_ALERTS: "🚨",
            WebhookChannel.DAILY_REPORTS: "📈",
        }
        
        prefix = channel_prefixes.get(channel, "📝")
        
        # Don't add prefix if title already has an emoji
        if any(ord(char) > 127 for char in title[:5]):  # Basic emoji detection
            return title
        
        return f"{prefix} {title}"
    
    def _enhance_description_for_channel(
        self, 
        description: str, 
        channel: WebhookChannel, 
        event_type: str
    ) -> str:
        """Add channel-specific context to the description.
        
        Enhances the message description with channel-appropriate context
        and formatting to provide better organization and readability.
        
        Args:
            description: Original message description
            channel: Target webhook channel
            event_type: Type of event for additional context
            
        Returns:
            str: Enhanced description with channel-specific context
        """
        
        channel_contexts = {
            WebhookChannel.BOT_STATUS: "**QuranBot System Status**",
            WebhookChannel.QURAN_AUDIO: "**QuranBot Audio System**",
            WebhookChannel.COMMANDS_PANEL: "**QuranBot Commands & Interactions**",
            WebhookChannel.USER_ACTIVITY: "**QuranBot User Engagement**",
            WebhookChannel.DATA_ANALYTICS: "**QuranBot Data & Analytics**",
            WebhookChannel.ERRORS_ALERTS: "**QuranBot Error Alert**",
            WebhookChannel.DAILY_REPORTS: "**QuranBot Daily Report**",
        }
        
        context = channel_contexts.get(channel, "**QuranBot Event**")
        
        # For some channels, add specific context
        if channel == WebhookChannel.QURAN_AUDIO:
            if "surah" in event_type.lower() or "reciter" in event_type.lower():
                context += " - 24/7 Continuous Recitation"
        elif channel == WebhookChannel.USER_ACTIVITY:
            if "quiz" in event_type.lower():
                context += " - Islamic Learning"
            elif "command" in event_type.lower():
                context += " - Bot Interaction"
        
        return f"{context}\n\n{description}"

    # Convenience methods for specific event types
    
    async def log_bot_event(
        self,
        event_type: str,
        title: str,
        description: str,
        level: LogLevel = LogLevel.INFO,
        context: Dict[str, Any] = None
    ) -> bool:
        """Log a bot lifecycle or system event.
        
        Logs events related to bot lifecycle, system health, and status updates
        to the BOT_STATUS channel.
        
        Args:
            event_type: Type of bot event (e.g., 'startup', 'shutdown', 'health_check')
            title: Event title
            description: Event description
            level: Log level
            context: Additional context information
            
        Returns:
            bool: True if logged successfully
        """
        return await self.route_event(
            event_type=event_type,
            title=title,
            description=description,
            level=level,
            context=context,
            force_channel=WebhookChannel.BOT_STATUS
        )
    
    async def log_audio_event(
        self,
        event_type: str,
        title: str,
        description: str,
        level: LogLevel = LogLevel.INFO,
        context: Dict[str, Any] = None
    ) -> bool:
        """Log an audio or playback event.
        
        Logs events related to Quran audio playback, voice channel activity,
        and audio system status to the QURAN_AUDIO channel.
        
        Args:
            event_type: Type of audio event (e.g., 'surah_start', 'voice_connect')
            title: Event title
            description: Event description
            level: Log level
            context: Additional context information
            
        Returns:
            bool: True if logged successfully
        """
        return await self.route_event(
            event_type=event_type,
            title=title,
            description=description,
            level=level,
            context=context,
            force_channel=WebhookChannel.QURAN_AUDIO
        )
    
    async def log_user_event(
        self,
        event_type: str,
        title: str,
        description: str,
        level: LogLevel = LogLevel.INFO,
        context: Dict[str, Any] = None
    ) -> bool:
        """Log a user activity event."""
        return await self.route_event(
            event_type=event_type,
            title=title,
            description=description,
            level=level,
            context=context,
            force_channel=WebhookChannel.USER_ACTIVITY
        )
    
    async def log_command_event(
        self,
        event_type: str,
        title: str,
        description: str,
        level: LogLevel = LogLevel.INFO,
        context: Dict[str, Any] = None
    ) -> bool:
        """Log a command or panel interaction event."""
        return await self.route_event(
            event_type=event_type,
            title=title,
            description=description,
            level=level,
            context=context,
            force_channel=WebhookChannel.COMMANDS_PANEL
        )
    
    async def log_data_event(
        self,
        event_type: str,
        title: str,
        description: str,
        level: LogLevel = LogLevel.INFO,
        context: Dict[str, Any] = None
    ) -> bool:
        """Log a data or analytics event."""
        return await self.route_event(
            event_type=event_type,
            title=title,
            description=description,
            level=level,
            context=context,
            force_channel=WebhookChannel.DATA_ANALYTICS
        )
    
    async def log_error_event(
        self,
        event_type: str,
        title: str,
        description: str,
        level: LogLevel = LogLevel.ERROR,
        context: Dict[str, Any] = None,
        exception: Exception = None
    ) -> bool:
        """Log an error or alert event."""
        if exception:
            if not context:
                context = {}
            context.update({
                "exception_type": type(exception).__name__,
                "exception_message": str(exception)
            })
        
        return await self.route_event(
            event_type=event_type,
            title=title,
            description=description,
            level=level,
            context=context,
            force_channel=WebhookChannel.ERRORS_ALERTS
        )
    
    async def log_daily_report(
        self,
        event_type: str,
        title: str,
        description: str,
        level: LogLevel = LogLevel.INFO,
        context: Dict[str, Any] = None
    ) -> bool:
        """Log a daily report or analytics summary."""
        return await self.route_event(
            event_type=event_type,
            title=title,
            description=description,
            level=level,
            context=context,
            force_channel=WebhookChannel.DAILY_REPORTS
        )

    # Specialized bot-focused logging methods
    
    async def log_quran_command_usage(
        self,
        command_name: str,
        user_name: str,
        user_id: int,
        user_avatar_url: str = None,
        command_details: Dict[str, Any] = None,
    ) -> bool:
        """Log QuranBot command usage (verse, quiz, credits, etc.)."""
        webhook_logger = self._get_webhook_logger(WebhookChannel.COMMANDS_PANEL)
        if webhook_logger:
            return await webhook_logger.log_quran_command_usage(
                command_name=command_name,
                user_name=user_name,
                user_id=user_id,
                user_avatar_url=user_avatar_url,
                command_details=command_details,
            )
        return False
    
    async def log_voice_channel_activity(
        self,
        activity_type: str,
        user_name: str,
        user_id: int,
        channel_name: str,
        user_avatar_url: str = None,
        additional_info: Dict[str, Any] = None,
    ) -> bool:
        """Log QuranBot voice channel activity during audio playback."""
        webhook_logger = self._get_webhook_logger(WebhookChannel.QURAN_AUDIO)
        if webhook_logger:
            return await webhook_logger.log_voice_channel_activity(
                activity_type=activity_type,
                user_name=user_name,
                user_id=user_id,
                channel_name=channel_name,
                user_avatar_url=user_avatar_url,
                additional_info=additional_info,
            )
        return False
    
    async def log_control_panel_interaction(
        self,
        interaction_type: str,
        user_name: str,
        user_id: int,
        action_performed: str,
        user_avatar_url: str = None,
        panel_details: Dict[str, Any] = None,
    ) -> bool:
        """Log QuranBot control panel interactions."""
        webhook_logger = self._get_webhook_logger(WebhookChannel.COMMANDS_PANEL)
        if webhook_logger:
            return await webhook_logger.log_control_panel_interaction(
                interaction_type=interaction_type,
                user_name=user_name,
                user_id=user_id,
                action_performed=action_performed,
                user_avatar_url=user_avatar_url,
                panel_details=panel_details,
            )
        return False
    
    async def log_quran_quiz_activity(
        self,
        user_name: str,
        user_id: int,
        question_text: str,
        user_answer: str,
        correct_answer: str,
        is_correct: bool,
        user_avatar_url: str = None,
        quiz_stats: Dict[str, Any] = None,
    ) -> bool:
        """Log QuranBot quiz activity."""
        webhook_logger = self._get_webhook_logger(WebhookChannel.USER_ACTIVITY)
        if webhook_logger:
            return await webhook_logger.log_quran_quiz_activity(
                user_name=user_name,
                user_id=user_id,
                question_text=question_text,
                user_answer=user_answer,
                correct_answer=correct_answer,
                is_correct=is_correct,
                user_avatar_url=user_avatar_url,
                quiz_stats=quiz_stats,
            )
        return False
    
    async def log_audio_playback_event(
        self,
        event_type: str,
        description: str = None,
        audio_details: Dict[str, Any] = None,
        ping_owner: bool = False,
    ) -> bool:
        """Log QuranBot audio playback events."""
        webhook_logger = self._get_webhook_logger(WebhookChannel.QURAN_AUDIO)
        if webhook_logger:
            return await webhook_logger.log_audio_event(
                event_type=event_type,
                error_message=description,
                audio_details=audio_details,
                ping_owner=ping_owner,
            )
        return False
    
    async def log_bot_startup(
        self,
        version: str,
        startup_duration: float,
        services_loaded: int,
        guild_count: int = 0,
    ) -> bool:
        """Log QuranBot startup event."""
        webhook_logger = self._get_webhook_logger(WebhookChannel.BOT_STATUS)
        if webhook_logger:
            return await webhook_logger.log_bot_startup(
                version=version,
                startup_duration=startup_duration,
                services_loaded=services_loaded,
                guild_count=guild_count,
            )
        return False
    
    async def log_bot_shutdown(
        self,
        reason: str = "Graceful shutdown",
        uptime: str = None,
        final_stats: Dict[str, Any] = None,
    ) -> bool:
        """Log QuranBot shutdown event."""
        webhook_logger = self._get_webhook_logger(WebhookChannel.BOT_STATUS)
        if webhook_logger:
            return await webhook_logger.log_bot_shutdown(
                reason=reason,
                uptime=uptime,
                final_stats=final_stats,
            )
        return False
    
    async def log_bot_crash(
        self,
        error_message: str,
        exception: Exception = None,
        crash_context: Dict[str, Any] = None,
        ping_owner: bool = True,
    ) -> bool:
        """Log QuranBot crash with owner notification."""
        webhook_logger = self._get_webhook_logger(WebhookChannel.ERRORS_ALERTS)
        if webhook_logger:
            return await webhook_logger.log_bot_crash(
                error_message=error_message,
                exception=exception,
                crash_context=crash_context,
                ping_owner=ping_owner,
            )
        return False
    
    async def log_database_operation(
        self,
        operation_type: str,
        table_name: str = None,
        records_affected: int = None,
        duration_ms: float = None,
        success: bool = True,
        error_details: str = None,
    ) -> bool:
        """Log database operations for analytics."""
        context = {}
        
        if table_name:
            context["table"] = table_name
        if records_affected is not None:
            context["records_affected"] = records_affected
        if duration_ms is not None:
            context["duration_ms"] = f"{duration_ms:.2f}ms"
        if error_details:
            context["error_details"] = error_details
        
        level = LogLevel.SUCCESS if success else LogLevel.ERROR
        title = f"Database {operation_type.title()}"
        description = f"Database operation completed {'successfully' if success else 'with errors'}"
        
        if error_details:
            description += f"\n\n**Error:** {error_details}"
        
        return await self.log_data_event(
            event_type=f"database_{operation_type}",
            title=title,
            description=description,
            level=level,
            context=context,
        )
    
    async def log_state_backup_event(
        self,
        backup_type: str,
        backup_id: str = None,
        file_size: int = None,
        success: bool = True,
        error_details: str = None,
    ) -> bool:
        """Log state backup operations."""
        context = {
            "backup_type": backup_type,
            "timestamp": f"<t:{int(time.time())}:R>",
        }
        
        if backup_id:
            context["backup_id"] = backup_id
        if file_size:
            context["file_size"] = f"{file_size // 1024}KB"
        if error_details:
            context["error_details"] = error_details
        
        level = LogLevel.SUCCESS if success else LogLevel.ERROR
        title = f"State Backup {'Completed' if success else 'Failed'}"
        description = f"State backup operation {'completed successfully' if success else 'failed'}"
        
        if error_details:
            description += f"\n\n**Error:** {error_details}"
        
        return await self.log_data_event(
            event_type=f"backup_{backup_type}",
            title=title,
            description=description,
            level=level,
            context=context,
        )
    
    async def log_performance_metrics(
        self,
        metric_type: str,
        value: float,
        unit: str = "",
        threshold_exceeded: bool = False,
        additional_metrics: Dict[str, Any] = None,
    ) -> bool:
        """Log performance metrics and alerts."""
        context = {
            "metric_value": f"{value}{unit}",
            "recorded_at": f"<t:{int(time.time())}:R>",
        }
        
        if additional_metrics:
            context.update(additional_metrics)
        
        level = LogLevel.WARNING if threshold_exceeded else LogLevel.INFO
        title = f"Performance Metric: {metric_type.title()}"
        description = f"Performance metric recorded: **{value}{unit}**"
        
        if threshold_exceeded:
            description += "\n\n⚠️ **Threshold exceeded** - Performance may be impacted"
        
        return await self.log_data_event(
            event_type=f"performance_{metric_type}",
            title=title,
            description=description,
            level=level,
            context=context,
        )
    
    async def log_conversation_memory_event(
        self,
        event_type: str,
        user_id: int = None,
        total_users: int = None,
        total_conversations: int = None,
        popular_topics: List[str] = None,
        success: bool = True,
        error_details: str = None,
    ) -> bool:
        """Log conversation memory service events."""
        context = {}
        
        if user_id:
            context["user_id"] = str(user_id)
        if total_users is not None:
            context["total_users"] = total_users
        if total_conversations is not None:
            context["total_conversations"] = total_conversations
        if popular_topics:
            context["popular_topics"] = ", ".join(popular_topics[:3])
        if error_details:
            context["error_details"] = error_details
        
        level = LogLevel.SUCCESS if success else LogLevel.ERROR
        title = f"Conversation Memory {event_type.title()}"
        description = f"Conversation memory operation {'completed successfully' if success else 'failed'}"
        
        if error_details:
            description += f"\n\n**Error:** {error_details}"
        
        return await self.log_data_event(
            event_type=f"conversation_memory_{event_type}",
            title=title,
            description=description,
            level=level,
            context=context,
        )
    
    # =============================================================================
    # Enhanced Visualization Methods
    # =============================================================================
    
    async def log_audio_playback_visual(
        self,
        surah_number: int,
        surah_name: str,
        reciter: str,
        progress: float,
        duration: float,
        listeners: int = 0,
        surah_progress_in_quran: float = None,
    ) -> bool:
        """Log audio playback with rich visualizations."""
        # Create progress visualizations
        playback_progress = VisualizationBuilder.create_progress_bar(
            progress, duration, length=25, show_percentage=True, show_values=False
        )
        
        # Quran completion progress
        quran_progress = ""
        if surah_progress_in_quran is not None:
            quran_progress = VisualizationBuilder.create_progress_bar(
                surah_progress_in_quran, 100, length=20, show_percentage=True
            )
        
        # Listener gauge
        listener_gauge = VisualizationBuilder.create_gauge(
            listeners, 0, 50,  # Assume 50 is a good max for visualization
            thresholds=[
                (30, "🔥"),  # Very active
                (15, "🟢"),  # Good activity
                (5, "🟡"),   # Some activity
                (1, "🟠"),   # Low activity
                (0, "⚫"),   # No listeners
            ]
        )
        
        description = f"**Now Playing:** Surah {surah_number} - {surah_name}\n"
        description += f"**Reciter:** {reciter}\n\n"
        description += f"**Playback Progress:**\n{playback_progress}\n\n"
        
        if quran_progress:
            description += f"**Quran Completion:**\n{quran_progress}\n\n"
        
        description += f"**Active Listeners:**\n{listener_gauge}"
        
        return await self.log_audio_event(
            event_type="audio_playback_visual",
            title="🎵 Quran Playback Status",
            description=description,
            level=LogLevel.INFO,
            context={
                "surah": f"{surah_number} - {surah_name}",
                "reciter": reciter,
                "duration": f"{int(duration//60)}:{int(duration%60):02d}",
                "progress_seconds": int(progress),
                "listeners": listeners,
            }
        )
    
    async def log_daily_stats_visual(
        self,
        total_playtime_hours: float,
        surahs_played: int,
        unique_listeners: int,
        quiz_participation: int,
        commands_used: int,
        hourly_activity: Dict[int, int] = None,
        top_surahs: List[Dict[str, Any]] = None,
    ) -> bool:
        """Log daily statistics with rich visualizations."""
        # Create main stats with visual indicators
        stats_lines = []
        
        # Playtime with gauge
        playtime_gauge = VisualizationBuilder.create_gauge(
            total_playtime_hours, 0, 24,
            thresholds=[(20, "🏆"), (16, "🟢"), (12, "🟡"), (8, "🟠"), (0, "🔴")]
        )
        stats_lines.append(f"**Total Playtime:**\n{playtime_gauge}")
        
        # Surahs progress
        surah_progress = VisualizationBuilder.create_circular_progress(
            surahs_played, 114, size="medium"
        )
        stats_lines.append(f"**Surahs Played:** {surah_progress}")
        
        # Activity metrics
        activity_bars = VisualizationBuilder.create_multi_progress_bars([
            {"name": "Unique Listeners", "value": unique_listeners, "emoji": "👥"},
            {"name": "Quiz Participants", "value": quiz_participation, "emoji": "🎯"},
            {"name": "Commands Used", "value": commands_used, "emoji": "⚡"},
        ], max_value=max(unique_listeners, quiz_participation, commands_used, 1))
        
        description = "\n\n".join(stats_lines) + "\n\n**Activity Breakdown:**\n" + "\n".join(activity_bars)
        
        # Add hourly heatmap if available
        if hourly_activity:
            heatmap = VisualizationBuilder.create_activity_heatmap(
                hourly_activity, hours=24, show_labels=True
            )
            description += f"\n\n{heatmap}"
        
        # Add top surahs chart if available
        if top_surahs:
            chart_data = [(s["name"][:10], s["plays"]) for s in top_surahs[:5]]
            surah_chart = VisualizationBuilder.create_bar_chart(
                chart_data, max_height=5, horizontal=True
            )
            description += f"\n\n**Top Surahs Today:**\n{surah_chart}"
        
        return await self.log_daily_report(
            event_type="daily_stats_visual",
            title="📊 Daily Statistics Report",
            description=description,
            level=LogLevel.INFO,
            context={
                "report_date": datetime.now().strftime("%Y-%m-%d"),
                "total_metrics": {
                    "playtime": f"{total_playtime_hours:.1f}h",
                    "surahs": surahs_played,
                    "listeners": unique_listeners,
                }
            }
        )
    
    async def log_performance_visual(
        self,
        cpu_percent: float,
        memory_percent: float,
        latency_ms: float,
        cache_hit_rate: float,
        cpu_history: List[float] = None,
        memory_history: List[float] = None,
    ) -> bool:
        """Log performance metrics with visualizations."""
        # Create performance gauges
        cpu_gauge = VisualizationBuilder.create_gauge(
            cpu_percent, 0, 100,
            thresholds=[(80, "🔴"), (60, "🟠"), (40, "🟡"), (20, "🟢"), (0, "⚫")]
        )
        
        memory_gauge = VisualizationBuilder.create_gauge(
            memory_percent, 0, 100,
            thresholds=[(85, "🔴"), (70, "🟠"), (50, "🟡"), (30, "🟢"), (0, "⚫")]
        )
        
        latency_gauge = VisualizationBuilder.create_gauge(
            latency_ms, 0, 1000,
            thresholds=[(800, "🔴"), (500, "🟠"), (300, "🟡"), (150, "🟢"), (0, "⚫")]
        )
        
        cache_gauge = VisualizationBuilder.create_gauge(
            cache_hit_rate, 0, 100,
            thresholds=[(90, "🟢"), (70, "🟡"), (50, "🟠"), (30, "🔴"), (0, "⚫")]
        )
        
        description = "**System Performance Metrics:**\n\n"
        description += f"**CPU Usage:**\n{cpu_gauge}\n\n"
        description += f"**Memory Usage:**\n{memory_gauge}\n\n"
        description += f"**Discord Latency:**\n{latency_gauge}\n\n"
        description += f"**Cache Performance:**\n{cache_gauge}"
        
        # Add sparklines if history is available
        if cpu_history and len(cpu_history) > 1:
            cpu_spark = VisualizationBuilder.create_sparkline(cpu_history[-20:])
            description += f"\n\n**CPU Trend (20 min):** {cpu_spark}"
        
        if memory_history and len(memory_history) > 1:
            memory_spark = VisualizationBuilder.create_sparkline(memory_history[-20:])
            description += f"\n**Memory Trend (20 min):** {memory_spark}"
        
        # Determine alert level
        level = LogLevel.INFO
        if cpu_percent > 80 or memory_percent > 85:
            level = LogLevel.WARNING
        if cpu_percent > 95 or memory_percent > 95:
            level = LogLevel.ERROR
        
        return await self.log_data_event(
            event_type="performance_visual",
            title="📈 Performance Metrics",
            description=description,
            level=level,
            context={
                "cpu": f"{cpu_percent:.1f}%",
                "memory": f"{memory_percent:.1f}%",
                "latency": f"{latency_ms:.0f}ms",
                "cache_hits": f"{cache_hit_rate:.1f}%",
            }
        )
    
    async def log_quiz_stats_visual(
        self,
        total_questions: int,
        correct_answers: int,
        participants: List[Dict[str, Any]],
        difficulty_distribution: Dict[str, int] = None,
        response_times: List[float] = None,
    ) -> bool:
        """Log quiz statistics with visualizations."""
        # Overall accuracy
        accuracy = (correct_answers / total_questions * 100) if total_questions > 0 else 0
        accuracy_bar = VisualizationBuilder.create_progress_bar(
            correct_answers, total_questions, length=20, show_percentage=True
        )
        
        description = f"**Quiz Performance Overview:**\n\n"
        description += f"**Overall Accuracy:**\n{accuracy_bar}\n\n"
        
        # Top participants leaderboard
        if participants:
            leaderboard_items = []
            for i, p in enumerate(participants[:5], 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🏅"
                score = p.get("score", 0)
                accuracy = p.get("accuracy", 0)
                bar = VisualizationBuilder.create_progress_bar(
                    accuracy, 100, length=10, show_percentage=False, include_emoji=False
                )
                leaderboard_items.append(
                    f"{medal} **{p.get('name', 'Unknown')}** - {score} pts {bar} {accuracy:.0f}%"
                )
            
            description += "**Top Participants:**\n" + "\n".join(leaderboard_items) + "\n\n"
        
        # Difficulty distribution
        if difficulty_distribution:
            diff_bars = VisualizationBuilder.create_multi_progress_bars([
                {"name": "Easy", "value": difficulty_distribution.get("easy", 0), "emoji": "🟢"},
                {"name": "Medium", "value": difficulty_distribution.get("medium", 0), "emoji": "🟡"},
                {"name": "Hard", "value": difficulty_distribution.get("hard", 0), "emoji": "🔴"},
            ])
            description += "**Questions by Difficulty:**\n" + "\n".join(diff_bars) + "\n\n"
        
        # Response time analysis
        if response_times and len(response_times) > 0:
            avg_time = sum(response_times) / len(response_times)
            time_sparkline = VisualizationBuilder.create_sparkline(response_times[-10:])
            description += f"**Response Times:** {time_sparkline}\n"
            description += f"**Average:** {avg_time:.1f}s"
        
        return await self.log_user_event(
            event_type="quiz_stats_visual",
            title="🎯 Quiz Statistics",
            description=description,
            level=LogLevel.SUCCESS,
            context={
                "total_questions": total_questions,
                "accuracy": f"{accuracy:.1f}%",
                "participants": len(participants),
            }
        )