# =============================================================================
# QuranBot - Discord Webhook Logger (Enhanced VPS Monitoring)
# =============================================================================
# This module provides Discord webhook logging for 24/7 VPS monitoring.
# It sends important logs, errors, and system events to Discord via webhooks
# instead of using the bot connection, making it more reliable and efficient.
#
# Key Features:
# - Webhook-based logging (no bot dependency)
# - Real-time error logging to Discord
# - System event notifications
# - Rate limiting and spam prevention
# - Rich embed formatting with color coding
# - Automatic log level filtering
# - VPS status monitoring
# - Graceful fallback when webhook is unavailable
# - Better performance and reliability than bot-based logging
# =============================================================================

import asyncio
import json
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import aiohttp
import pytz

from .tree_log import log_error_with_traceback, log_perfect_tree_section


class DiscordWebhookLogger:
    """
    Discord webhook logger for VPS monitoring and real-time debugging.
    
    This class provides comprehensive Discord logging capabilities for
    monitoring QuranBot when running 24/7 on a VPS. It sends formatted
    log messages to Discord via webhooks, which is more reliable than
    using the bot connection.
    
    Features:
    - Webhook-based logging (independent of bot status)
    - Real-time error and warning notifications
    - System event logging (startup, shutdown, connections)
    - Rich embed formatting with color coding
    - Rate limiting to prevent spam
    - Automatic log level filtering
    - Better performance than bot-based logging
    - No dependency on Discord bot connection
    """
    
    def __init__(self, webhook_url: str, owner_user_id: int = None):
        """
        Initialize the Discord webhook logger.
        
        Args:
            webhook_url: Discord webhook URL
            owner_user_id: Discord user ID to ping for critical errors
        """
        self.webhook_url = webhook_url
        self.owner_user_id = owner_user_id or 155149108183695360  # John's Discord ID
        self.rate_limit_cache = {}
        self.max_logs_per_minute = 10
        self.enabled = True
        self.session = None
        
        # Color coding for different log levels
        self.level_colors = {
            "INFO": 0x3498db,      # Blue
            "WARNING": 0xf39c12,   # Orange
            "ERROR": 0xe74c3c,     # Red
            "CRITICAL": 0x8b0000,  # Dark Red
            "SUCCESS": 0x27ae60,   # Green
            "SYSTEM": 0x9b59b6,    # Purple
            "USER": 0x1abc9c,      # Teal
        }
        
        # Emojis for different log types
        self.level_emojis = {
            "INFO": "ℹ️",
            "WARNING": "⚠️", 
            "ERROR": "❌",
            "CRITICAL": "🚨",
            "SUCCESS": "✅",
            "SYSTEM": "🔧",
            "USER": "👤",
        }
    
    async def initialize(self):
        """Initialize the webhook logger by creating HTTP session."""
        try:
            if not self.webhook_url:
                log_error_with_traceback("No webhook URL provided", None)
                self.enabled = False
                return False
            
            # Create aiohttp session for webhook requests
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={'User-Agent': 'QuranBot-WebhookLogger/1.0'}
            )
            
            # Test webhook with initial heartbeat
            await self._send_initial_heartbeat()
            
            log_perfect_tree_section(
                "Discord Webhook Logger - Initialized",
                [
                    ("status", "✅ Webhook logger initialized"),
                    ("method", "Discord Webhook (no bot dependency)"),
                    ("rate_limit", f"{self.max_logs_per_minute} logs/minute"),
                    ("reliability", "✅ Independent of bot connection"),
                ],
                "🔗",
            )
            
            return True
                
        except Exception as e:
            log_error_with_traceback("Failed to initialize Discord webhook logger", e)
            self.enabled = False
            return False
    
    async def close(self):
        """Close the webhook logger and cleanup resources."""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _send_initial_heartbeat(self):
        """Send initial heartbeat to test webhook."""
        try:
            await self._send_webhook_embed(
                title="🚀 QuranBot Webhook Logger Started",
                description="**Webhook-based Discord logging is now active**\n\n"
                           "This provides more reliable logging than bot-based messaging, "
                           "as it works independently of the bot's Discord connection status.",
                level="SYSTEM",
                fields=[
                    {"name": "Logging Method", "value": "Discord Webhook", "inline": True},
                    {"name": "Rate Limit", "value": f"{self.max_logs_per_minute} logs/minute", "inline": True},
                    {"name": "Reliability", "value": "✅ Independent of bot status", "inline": True},
                    {"name": "Started", "value": f"<t:{int(time.time())}:R>", "inline": True},
                ]
            )
        except Exception as e:
            log_error_with_traceback("Error sending initial webhook heartbeat", e)
    
    def _check_rate_limit(self, log_type: str) -> bool:
        """
        Check if we're within rate limits for a specific log type.
        
        Args:
            log_type: Type of log to check
            
        Returns:
            bool: True if within rate limits, False if rate limited
        """
        now = datetime.now()
        minute_key = now.strftime("%Y-%m-%d-%H-%M")
        
        if log_type not in self.rate_limit_cache:
            self.rate_limit_cache[log_type] = {}
        
        if minute_key not in self.rate_limit_cache[log_type]:
            self.rate_limit_cache[log_type][minute_key] = 0
        
        # Clean old entries (older than 2 minutes)
        keys_to_remove = []
        for key in self.rate_limit_cache[log_type].keys():
            try:
                key_time = datetime.strptime(key, "%Y-%m-%d-%H-%M")
                if (now - key_time).total_seconds() > 120:
                    keys_to_remove.append(key)
            except:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.rate_limit_cache[log_type][key]
        
        # Check current minute's count
        current_count = self.rate_limit_cache[log_type][minute_key]
        if current_count >= self.max_logs_per_minute:
            return False
        
        self.rate_limit_cache[log_type][minute_key] += 1
        return True
    
    def _get_timestamp(self) -> str:
        """Get formatted timestamp in EST timezone."""
        try:
            est = pytz.timezone("US/Eastern")
            now_est = datetime.now(est)
            return now_est.strftime("%m/%d %I:%M %p EST")
        except:
            return datetime.now().strftime("%m/%d %I:%M %p")
    
    async def _send_webhook_embed(
        self, 
        title: str, 
        description: str, 
        level: str = "INFO",
        fields: Optional[List[Dict[str, str]]] = None,
        footer: Optional[str] = None,
        content: Optional[str] = None
    ):
        """
        Send a formatted embed to Discord via webhook.
        
        Args:
            title: Embed title
            description: Embed description
            level: Log level (INFO, WARNING, ERROR, etc.)
            fields: List of embed fields
            footer: Optional footer text
            content: Optional message content (for pings)
        """
        if not self.enabled or not self.session:
            return
        
        # Check rate limiting
        if not self._check_rate_limit(level):
            return
        
        try:
            embed = {
                "title": f"{self.level_emojis.get(level, '📝')} {title}",
                "description": description,
                "color": self.level_colors.get(level, 0x95a5a6),
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {
                    "text": footer or f"QuranBot VPS Webhook • {self._get_timestamp()}"
                }
            }
            
            # Add fields if provided
            if fields:
                embed["fields"] = []
                for field in fields[:25]:  # Discord limit is 25 fields
                    embed["fields"].append({
                        "name": field.get("name", "Field"),
                        "value": field.get("value", "No value"),
                        "inline": field.get("inline", False)
                    })
            
            # Prepare webhook payload
            payload = {
                "embeds": [embed],
                "username": "QuranBot Logger",
                "avatar_url": "https://cdn.discordapp.com/attachments/1044035927281262673/1044036084692160512/PFP_Cropped_-_Animated.gif"
            }
            
            # Add content for pings if specified
            if content:
                payload["content"] = content
            
            # Send webhook request
            async with self.session.post(
                self.webhook_url, 
                json=payload,
                headers={'Content-Type': 'application/json'}
            ) as response:
                if response.status == 429:  # Rate limited
                    retry_after = int(response.headers.get('Retry-After', 60))
                    log_perfect_tree_section(
                        "Discord Webhook - Rate Limited",
                        [
                            ("status", "🚨 Webhook rate limited"),
                            ("retry_after", f"{retry_after}s"),
                            ("impact", "Discord notifications paused"),
                            ("local_logging", "✅ Still active"),
                        ],
                        "⏳",
                    )
                elif response.status >= 400:
                    error_text = await response.text()
                    log_error_with_traceback(f"Webhook error {response.status}: {error_text}", None)
            
        except asyncio.TimeoutError:
            log_error_with_traceback("Webhook request timed out", None)
        except Exception as e:
            log_error_with_traceback("Error sending webhook log", e)
    
    async def log_error(
        self, 
        error_message: str, 
        exception: Optional[Exception] = None,
        context: Optional[Dict[str, str]] = None
    ):
        """
        Log an error to Discord with full traceback and ping owner.
        
        Args:
            error_message: Error description
            exception: Exception object (if available)
            context: Additional context information
        """
        if not self.enabled:
            return
        
        # Send ping message first
        try:
            ping_content = f"🚨 <@{self.owner_user_id}> **ERROR DETECTED** 🚨"
            description = f"**Error:** {error_message}"
            
            fields = []
            
            if exception:
                fields.append({
                    "name": "Exception Type",
                    "value": f"`{type(exception).__name__}`",
                    "inline": True
                })
                fields.append({
                    "name": "Exception Message", 
                    "value": f"```\n{str(exception)[:1000]}\n```",
                    "inline": False
                })
                
                # Add traceback (limited to prevent embed size issues)
                if hasattr(exception, '__traceback__') and exception.__traceback__:
                    tb_lines = traceback.format_tb(exception.__traceback__)
                    tb_text = ''.join(tb_lines)[:1000]
                    fields.append({
                        "name": "Traceback",
                        "value": f"```python\n{tb_text}\n```",
                        "inline": False
                    })
            
            if context:
                for key, value in context.items():
                    fields.append({
                        "name": key,
                        "value": str(value)[:1000],
                        "inline": True
                    })
            
            await self._send_webhook_embed(
                title="Critical Error",
                description=description,
                level="ERROR",
                fields=fields,
                content=ping_content
            )
            
        except Exception as e:
            log_error_with_traceback("Failed to send error webhook", e)
    
    async def log_critical_error(
        self, 
        error_message: str, 
        exception: Optional[Exception] = None,
        context: Optional[Dict[str, str]] = None
    ):
        """
        Log a critical error to Discord with owner ping.
        
        Args:
            error_message: Error description
            exception: Exception object (if available)
            context: Additional context information
        """
        if not self.enabled:
            return
        
        ping_content = f"🆘 <@{self.owner_user_id}> **CRITICAL ERROR** 🆘"
        description = f"**🚨 CRITICAL ERROR 🚨**\n\n{error_message}"
        
        fields = []
        
        if exception:
            fields.append({
                "name": "Exception Type",
                "value": f"`{type(exception).__name__}`",
                "inline": True
            })
            fields.append({
                "name": "Exception Message", 
                "value": f"```\n{str(exception)[:1000]}\n```",
                "inline": False
            })
        
        if context:
            for key, value in context.items():
                fields.append({
                    "name": key,
                    "value": str(value)[:1000],
                    "inline": True
                })
        
        await self._send_webhook_embed(
            title="CRITICAL SYSTEM ERROR",
            description=description,
            level="CRITICAL",
            fields=fields,
            content=ping_content
        )
    
    async def log_warning(
        self, 
        warning_message: str, 
        context: Optional[Dict[str, str]] = None
    ):
        """
        Log a warning message.
        
        Args:
            warning_message: Warning description
            context: Additional context information
        """
        if not self.enabled:
            return
        
        description = f"**Warning:** {warning_message}"
        
        fields = []
        if context:
            for key, value in context.items():
                fields.append({
                    "name": key,
                    "value": str(value)[:1000],
                    "inline": True
                })
        
        await self._send_webhook_embed(
            title="Warning",
            description=description,
            level="WARNING",
            fields=fields
        )
    
    async def log_system_event(
        self, 
        event_name: str, 
        event_description: str,
        context: Optional[Dict[str, str]] = None
    ):
        """
        Log a system event (startup, shutdown, connections, etc.).
        
        Args:
            event_name: Name of the system event
            event_description: Description of the event
            context: Additional context information
        """
        if not self.enabled:
            return
        
        fields = []
        if context:
            for key, value in context.items():
                fields.append({
                    "name": key,
                    "value": str(value)[:1000],
                    "inline": True
                })
        
        await self._send_webhook_embed(
            title=event_name,
            description=event_description,
            level="SYSTEM",
            fields=fields
        )
    
    async def log_user_activity(
        self, 
        activity_type: str, 
        user_name: str,
        activity_description: str,
        context: Optional[Dict[str, str]] = None
    ):
        """
        Log important user activities.
        
        Args:
            activity_type: Type of user activity
            user_name: Name of the user
            activity_description: Description of the activity
            context: Additional context information
        """
        if not self.enabled:
            return
        
        description = f"**User:** {user_name}\n**Activity:** {activity_description}"
        
        fields = []
        if context:
            for key, value in context.items():
                fields.append({
                    "name": key,
                    "value": str(value)[:1000],
                    "inline": True
                })
        
        await self._send_webhook_embed(
            title=f"User Activity - {activity_type}",
            description=description,
            level="USER",
            fields=fields
        )
    
    async def log_user_interaction(
        self, 
        interaction_type: str, 
        user_name: str, 
        user_id: int,
        action_description: str, 
        details: Optional[Dict[str, str]] = None, 
        user_avatar_url: Optional[str] = None
    ):
        """
        Log user interactions (commands, button clicks, etc.)
        
        Args:
            interaction_type: Type of interaction
            user_name: User's display name
            user_id: User's Discord ID
            action_description: Description of what the user did
            details: Additional interaction details
            user_avatar_url: User's avatar URL (optional)
        """
        if not self.enabled:
            return
        
        # Create interaction emoji mapping
        interaction_emojis = {
            "button_click": "🔘",
            "command_use": "💬",
            "slash_command": "⚡",
            "voice_join": "🎤",
            "voice_leave": "🔇",
            "voice_move": "🔄",
            "quiz_answer": "🧠",
            "default": "👤"
        }
        
        emoji = interaction_emojis.get(interaction_type, interaction_emojis["default"])
        
        fields = [
            {"name": "Interaction Type", "value": interaction_type.replace("_", " ").title(), "inline": True},
            {"name": "User ID", "value": str(user_id), "inline": True},
            {"name": "Time", "value": f"<t:{int(time.time())}:R>", "inline": True}
        ]
        
        if details:
            for key, value in details.items():
                field_value = str(value)
                if len(field_value) > 1024:
                    field_value = field_value[:1021] + "..."
                fields.append({
                    "name": key.replace("_", " ").title(),
                    "value": field_value,
                    "inline": True
                })
        
        await self._send_webhook_embed(
            title=f"{emoji} User Interaction",
            description=f"**{user_name}** {action_description}",
            level="USER",
            fields=fields
        )
    
    async def log_bot_activity(
        self, 
        activity_type: str, 
        activity_description: str, 
        details: Optional[Dict[str, str]] = None
    ):
        """
        Log bot activities like automatic surah switching, audio management, etc.
        
        Args:
            activity_type: Type of bot activity (surah_switch, audio_start, etc.)
            activity_description: Description of what the bot did
            details: Additional details about the activity
        """
        if not self.enabled:
            return
        
        # Create bot activity emoji mapping
        activity_emojis = {
            "surah_switch": "🔄",
            "surah_start": "▶️",
            "surah_end": "⏹️",
            "audio_start": "🎵",
            "audio_stop": "⏸️",
            "audio_pause": "⏸️",
            "audio_resume": "▶️",
            "reciter_switch": "🎙️",
            "playlist_shuffle": "🔀",
            "playlist_loop": "🔁",
            "voice_connect": "🔗",
            "voice_disconnect": "🔌",
            "voice_reconnect": "🔄",
            "enhanced_auto_recovery": "🔧",
            "auto_recovery": "🔧",
            "daily_verse": "📖",
            "scheduled_verse": "⏰",
            "quiz_start": "🧠",
            "quiz_end": "🏁",
            "backup_create": "💾",
            "backup_restore": "📥",
            "system_restart": "🔄",
            "system_shutdown": "⏹️",
            "error_recovery": "🔧",
            "default": "🤖"
        }
        
        emoji = activity_emojis.get(activity_type, activity_emojis["default"])
        
        fields = []
        if details:
            for key, value in details.items():
                fields.append({
                    "name": key,
                    "value": str(value)[:1000],
                    "inline": True
                })
        
        await self._send_webhook_embed(
            title=f"{emoji} Bot Activity",
            description=f"**QuranBot** {activity_description}",
            level="SYSTEM",
            fields=fields
        )
    
    async def log_success(
        self, 
        success_message: str, 
        context: Optional[Dict[str, str]] = None
    ):
        """
        Log a success message.
        
        Args:
            success_message: Success description
            context: Additional context information
        """
        if not self.enabled:
            return
        
        fields = []
        if context:
            for key, value in context.items():
                fields.append({
                    "name": key,
                    "value": str(value)[:1000],
                    "inline": True
                })
        
        await self._send_webhook_embed(
            title="Success",
            description=success_message,
            level="SUCCESS",
            fields=fields
        )
    
    async def log_vps_status(
        self, 
        status_type: str,
        status_data: Dict[str, str]
    ):
        """
        Log VPS status information.
        
        Args:
            status_type: Type of status (startup, periodic, shutdown)
            status_data: Dictionary of status information
        """
        if not self.enabled:
            return
        
        description = f"**VPS Status Update:** {status_type}"
        
        fields = []
        for key, value in status_data.items():
            fields.append({
                "name": key.replace("_", " ").title(),
                "value": str(value)[:1000],
                "inline": True
            })
        
        await self._send_webhook_embed(
            title=f"VPS Status - {status_type}",
            description=description,
            level="SYSTEM",
            fields=fields
        )
    
    async def log_rate_limit(
        self,
        event: str,
        retry_after: float,
        context: Optional[Dict[str, str]] = None
    ):
        """
        Log a rate limit event.
        
        Args:
            event: Event that was rate limited
            retry_after: Time to wait before retrying
            context: Additional context information
        """
        if not self.enabled:
            return
        
        description = f"**Rate Limited:** {event}\n\nRetry after: {retry_after} seconds"
        
        fields = [
            {"name": "Retry After", "value": f"{retry_after} seconds", "inline": True}
        ]
        
        if context:
            for key, value in context.items():
                fields.append({
                    "name": key,
                    "value": str(value)[:1000],
                    "inline": True
                })
        
        await self._send_webhook_embed(
            title="Rate Limit",
            description=description,
            level="WARNING",
            fields=fields
        )
    
    def disable(self):
        """Disable Discord webhook logging."""
        self.enabled = False
        log_perfect_tree_section(
            "Discord Webhook Logger Disabled",
            [
                ("status", "❌ Discord webhook logging disabled"),
                ("reason", "Error or configuration issue"),
            ],
            "🔇"
        )
    
    def enable(self):
        """Enable Discord webhook logging."""
        self.enabled = True
        log_perfect_tree_section(
            "Discord Webhook Logger Enabled",
            [
                ("status", "✅ Discord webhook logging enabled"),
                ("method", "Webhook-based (independent)"),
            ],
            "🔔"
        )


# Global Discord webhook logger instance
_discord_webhook_logger: Optional[DiscordWebhookLogger] = None


def setup_discord_webhook_logger(webhook_url: str, owner_user_id: int = None) -> DiscordWebhookLogger:
    """
    Set up the global Discord webhook logger instance.
    
    Args:
        webhook_url: Discord webhook URL
        owner_user_id: Discord user ID to ping for critical errors
        
    Returns:
        DiscordWebhookLogger: The initialized Discord webhook logger
    """
    global _discord_webhook_logger
    _discord_webhook_logger = DiscordWebhookLogger(webhook_url, owner_user_id)
    return _discord_webhook_logger


def get_discord_webhook_logger() -> Optional[DiscordWebhookLogger]:
    """
    Get the global Discord webhook logger instance.
    
    Returns:
        Optional[DiscordWebhookLogger]: The Discord webhook logger instance if available
    """
    return _discord_webhook_logger


# Convenience functions for webhook logging
async def webhook_log_error(
    error_message: str, 
    exception: Optional[Exception] = None,
    context: Optional[Dict[str, str]] = None
):
    """Log an error via webhook."""
    if _discord_webhook_logger:
        await _discord_webhook_logger.log_error(error_message, exception, context)


async def webhook_log_critical(
    error_message: str, 
    exception: Optional[Exception] = None,
    context: Optional[Dict[str, str]] = None
):
    """Log a critical error via webhook."""
    if _discord_webhook_logger:
        await _discord_webhook_logger.log_critical_error(error_message, exception, context)


async def webhook_log_warning(
    warning_message: str, 
    context: Optional[Dict[str, str]] = None
):
    """Log a warning via webhook."""
    if _discord_webhook_logger:
        await _discord_webhook_logger.log_warning(warning_message, context)


async def webhook_log_system(
    event_name: str, 
    event_description: str,
    context: Optional[Dict[str, str]] = None
):
    """Log a system event via webhook."""
    if _discord_webhook_logger:
        await _discord_webhook_logger.log_system_event(event_name, event_description, context)


async def webhook_log_user(
    activity_type: str, 
    user_name: str,
    activity_description: str,
    context: Optional[Dict[str, str]] = None
):
    """Log user activity via webhook."""
    if _discord_webhook_logger:
        await _discord_webhook_logger.log_user_activity(activity_type, user_name, activity_description, context)


async def webhook_log_user_interaction(
    interaction_type: str, 
    user_name: str, 
    user_id: int,
    action_description: str, 
    details: Optional[Dict[str, str]] = None, 
    user_avatar_url: Optional[str] = None
):
    """Log user interaction via webhook."""
    if _discord_webhook_logger:
        await _discord_webhook_logger.log_user_interaction(interaction_type, user_name, user_id, action_description, details, user_avatar_url)


async def webhook_log_bot_activity(
    activity_type: str, 
    activity_description: str, 
    details: Optional[Dict[str, str]] = None
):
    """Log bot activity via webhook."""
    if _discord_webhook_logger:
        await _discord_webhook_logger.log_bot_activity(activity_type, activity_description, details)


async def webhook_log_success(
    success_message: str, 
    context: Optional[Dict[str, str]] = None
):
    """Log a success message via webhook."""
    if _discord_webhook_logger:
        await _discord_webhook_logger.log_success(success_message, context)


async def webhook_log_vps_status(
    status_type: str,
    status_data: Dict[str, str]
):
    """Log VPS status via webhook."""
    if _discord_webhook_logger:
        await _discord_webhook_logger.log_vps_status(status_type, status_data) 