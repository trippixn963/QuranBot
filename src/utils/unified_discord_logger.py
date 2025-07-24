# =============================================================================
# QuranBot - Unified Discord Logger
# =============================================================================
# This module provides a unified interface for Discord logging that can
# automatically switch between bot-based and webhook-based logging based
# on configuration. This allows for easy migration from bot to webhook logging.
# =============================================================================

import os
from typing import Dict, List, Optional, Union
from discord.ext import commands

from .discord_logger import DiscordLogger, setup_discord_logger
from .discord_webhook_logger import DiscordWebhookLogger, setup_discord_webhook_logger
from .tree_log import log_error_with_traceback, log_perfect_tree_section


class UnifiedDiscordLogger:
    """
    Unified Discord logger that can use either bot-based or webhook-based logging.
    
    This class provides a single interface for Discord logging while supporting
    both the old bot-based method and the new webhook-based method. It automatically
    chooses the appropriate method based on configuration.
    """
    
    def __init__(self):
        self.bot_logger: Optional[DiscordLogger] = None
        self.webhook_logger: Optional[DiscordWebhookLogger] = None
        self.use_webhook = False
        self.enabled = False
    
    async def initialize(self, bot: Optional[commands.Bot] = None):
        """
        Initialize the unified logger based on environment configuration.
        
        Args:
            bot: Discord bot instance (required for bot-based logging)
        """
        try:
            # Check configuration
            use_webhook_logging = os.getenv("USE_WEBHOOK_LOGGING", "false").lower() == "true"
            webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "")
            log_channel_id = int(os.getenv("LOG_CHANNEL_ID", "0"))
            
            if use_webhook_logging and webhook_url:
                # Use webhook-based logging
                self.use_webhook = True
                self.webhook_logger = setup_discord_webhook_logger(webhook_url)
                success = await self.webhook_logger.initialize()
                
                if success:
                    self.enabled = True
                    log_perfect_tree_section(
                        "Unified Discord Logger - Webhook Mode",
                        [
                            ("status", "✅ Webhook-based logging active"),
                            ("method", "Discord Webhook"),
                            ("reliability", "✅ Independent of bot connection"),
                            ("performance", "✅ Better than bot-based logging"),
                        ],
                        "🔗",
                    )
                else:
                    log_error_with_traceback("Failed to initialize webhook logging", None)
                    
            elif bot and log_channel_id:
                # Fall back to bot-based logging
                self.use_webhook = False
                self.bot_logger = setup_discord_logger(bot, log_channel_id)
                success = await self.bot_logger.initialize()
                
                if success:
                    self.enabled = True
                    log_perfect_tree_section(
                        "Unified Discord Logger - Bot Mode",
                        [
                            ("status", "✅ Bot-based logging active"),
                            ("method", "Discord Bot Messages"),
                            ("note", "⚠️ Depends on bot connection"),
                            ("recommendation", "Consider switching to webhook logging"),
                        ],
                        "🤖",
                    )
                else:
                    log_error_with_traceback("Failed to initialize bot logging", None)
            else:
                log_perfect_tree_section(
                    "Unified Discord Logger - Disabled",
                    [
                        ("status", "❌ Discord logging disabled"),
                        ("reason", "Missing webhook URL or bot configuration"),
                        ("webhook_url_set", "✅" if webhook_url else "❌"),
                        ("log_channel_id_set", "✅" if log_channel_id else "❌"),
                        ("use_webhook_logging", str(use_webhook_logging)),
                    ],
                    "🔇",
                )
                self.enabled = False
                
            return self.enabled
            
        except Exception as e:
            log_error_with_traceback("Error initializing unified Discord logger", e)
            self.enabled = False
            return False
    
    async def close(self):
        """Close the unified logger and cleanup resources."""
        if self.webhook_logger:
            await self.webhook_logger.close()
        # Bot logger doesn't need explicit closing
    
    def get_active_logger(self):
        """Get the currently active logger instance."""
        if self.use_webhook and self.webhook_logger:
            return self.webhook_logger
        elif not self.use_webhook and self.bot_logger:
            return self.bot_logger
        return None
    
    def get_logger_type(self) -> str:
        """Get the type of logger currently in use."""
        if not self.enabled:
            return "disabled"
        return "webhook" if self.use_webhook else "bot"
    
    # Unified logging methods that delegate to the appropriate logger
    
    async def log_error(
        self, 
        error_message: str, 
        exception: Optional[Exception] = None,
        context: Optional[Dict[str, str]] = None
    ):
        """Log an error to Discord."""
        if not self.enabled:
            return
        
        logger = self.get_active_logger()
        if logger:
            await logger.log_error(error_message, exception, context)
    
    async def log_critical_error(
        self, 
        error_message: str, 
        exception: Optional[Exception] = None,
        context: Optional[Dict[str, str]] = None
    ):
        """Log a critical error to Discord."""
        if not self.enabled:
            return
        
        logger = self.get_active_logger()
        if logger:
            if hasattr(logger, 'log_critical_error'):
                await logger.log_critical_error(error_message, exception, context)
            else:
                # Fallback for bot logger which doesn't have log_critical_error
                await logger.log_error(f"CRITICAL: {error_message}", exception, context)
    
    async def log_warning(
        self, 
        warning_message: str, 
        context: Optional[Dict[str, str]] = None
    ):
        """Log a warning message."""
        if not self.enabled:
            return
        
        logger = self.get_active_logger()
        if logger:
            await logger.log_warning(warning_message, context)
    
    async def log_system_event(
        self, 
        event_name: str, 
        event_description: str,
        context: Optional[Dict[str, str]] = None
    ):
        """Log a system event."""
        if not self.enabled:
            return
        
        logger = self.get_active_logger()
        if logger:
            await logger.log_system_event(event_name, event_description, context)
    
    async def log_user_activity(
        self, 
        activity_type: str, 
        user_name: str,
        activity_description: str,
        context: Optional[Dict[str, str]] = None
    ):
        """Log user activity."""
        if not self.enabled:
            return
        
        logger = self.get_active_logger()
        if logger:
            await logger.log_user_activity(activity_type, user_name, activity_description, context)
    
    async def log_user_interaction(
        self, 
        interaction_type: str, 
        user_name: str, 
        user_id: int,
        action_description: str, 
        details: Optional[Dict[str, str]] = None, 
        user_avatar_url: Optional[str] = None
    ):
        """Log user interaction."""
        if not self.enabled:
            return
        
        logger = self.get_active_logger()
        if logger:
            await logger.log_user_interaction(interaction_type, user_name, user_id, action_description, details, user_avatar_url)
    
    async def log_bot_activity(
        self, 
        activity_type: str, 
        activity_description: str, 
        details: Optional[Dict[str, str]] = None
    ):
        """Log bot activity."""
        if not self.enabled:
            return
        
        logger = self.get_active_logger()
        if logger:
            await logger.log_bot_activity(activity_type, activity_description, details)
    
    async def log_success(
        self, 
        success_message: str, 
        context: Optional[Dict[str, str]] = None
    ):
        """Log a success message."""
        if not self.enabled:
            return
        
        logger = self.get_active_logger()
        if logger:
            await logger.log_success(success_message, context)
    
    async def log_vps_status(
        self, 
        status_type: str,
        status_data: Dict[str, str]
    ):
        """Log VPS status."""
        if not self.enabled:
            return
        
        logger = self.get_active_logger()
        if logger:
            await logger.log_vps_status(status_type, status_data)
    
    async def log_rate_limit(
        self,
        event: str,
        retry_after: float,
        context: Optional[Dict[str, str]] = None
    ):
        """Log a rate limit event."""
        if not self.enabled:
            return
        
        logger = self.get_active_logger()
        if logger:
            await logger.log_rate_limit(event, retry_after, context)


# Global unified logger instance
_unified_discord_logger: Optional[UnifiedDiscordLogger] = None


def setup_unified_discord_logger() -> UnifiedDiscordLogger:
    """
    Set up the global unified Discord logger instance.
    
    Returns:
        UnifiedDiscordLogger: The unified Discord logger
    """
    global _unified_discord_logger
    _unified_discord_logger = UnifiedDiscordLogger()
    return _unified_discord_logger


def get_unified_discord_logger() -> Optional[UnifiedDiscordLogger]:
    """
    Get the global unified Discord logger instance.
    
    Returns:
        Optional[UnifiedDiscordLogger]: The unified Discord logger instance if available
    """
    return _unified_discord_logger


# Convenience functions that use the unified logger
async def unified_log_error(
    error_message: str, 
    exception: Optional[Exception] = None,
    context: Optional[Dict[str, str]] = None
):
    """Log an error via unified logger."""
    if _unified_discord_logger:
        await _unified_discord_logger.log_error(error_message, exception, context)


async def unified_log_critical(
    error_message: str, 
    exception: Optional[Exception] = None,
    context: Optional[Dict[str, str]] = None
):
    """Log a critical error via unified logger."""
    if _unified_discord_logger:
        await _unified_discord_logger.log_critical_error(error_message, exception, context)


async def unified_log_warning(
    warning_message: str, 
    context: Optional[Dict[str, str]] = None
):
    """Log a warning via unified logger."""
    if _unified_discord_logger:
        await _unified_discord_logger.log_warning(warning_message, context)


async def unified_log_system(
    event_name: str, 
    event_description: str,
    context: Optional[Dict[str, str]] = None
):
    """Log a system event via unified logger."""
    if _unified_discord_logger:
        await _unified_discord_logger.log_system_event(event_name, event_description, context)


async def unified_log_user(
    activity_type: str, 
    user_name: str,
    activity_description: str,
    context: Optional[Dict[str, str]] = None
):
    """Log user activity via unified logger."""
    if _unified_discord_logger:
        await _unified_discord_logger.log_user_activity(activity_type, user_name, activity_description, context)


async def unified_log_user_interaction(
    interaction_type: str, 
    user_name: str, 
    user_id: int,
    action_description: str, 
    details: Optional[Dict[str, str]] = None, 
    user_avatar_url: Optional[str] = None
):
    """Log user interaction via unified logger."""
    if _unified_discord_logger:
        await _unified_discord_logger.log_user_interaction(interaction_type, user_name, user_id, action_description, details, user_avatar_url)


async def unified_log_bot_activity(
    activity_type: str, 
    activity_description: str, 
    details: Optional[Dict[str, str]] = None
):
    """Log bot activity via unified logger."""
    if _unified_discord_logger:
        await _unified_discord_logger.log_bot_activity(activity_type, activity_description, details) 