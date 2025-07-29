# =============================================================================
# QuranBot - Modern Webhook Logger
# =============================================================================
# A modern, async-first webhook logger that integrates with the DI container
# and provides reliable Discord notifications for monitoring and debugging.
#
# Key Features:
# - Modern async/await patterns
# - Dependency injection integration
# - Proper error handling and fallbacks
# - Memory-efficient rate limiting
# - Type safety with comprehensive validation
# - Structured logging integration
# - Configuration-driven setup
# - Comprehensive testing support
# =============================================================================

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import time
from typing import Any
import weakref

import aiohttp
import pytz

from .exceptions import QuranBotError
from .structured_logger import StructuredLogger


class LogLevel(Enum):
    """Log levels for webhook messages."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    SUCCESS = "SUCCESS"
    SYSTEM = "SYSTEM"
    USER = "USER"


class WebhookLoggerError(QuranBotError):
    """Raised when webhook logger encounters an error."""

    pass


@dataclass
class WebhookConfig:
    """Configuration for webhook logger."""

    webhook_url: str
    owner_user_id: int | None = None
    max_logs_per_minute: int = 10
    max_embed_fields: int = 25
    max_field_length: int = 1024
    max_description_length: int = 4096
    request_timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0
    rate_limit_window: int = 60
    enable_pings: bool = True
    timezone: str = "US/Eastern"

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.webhook_url:
            raise ValueError("webhook_url is required")
        if self.max_logs_per_minute <= 0:
            raise ValueError("max_logs_per_minute must be positive")
        if self.request_timeout <= 0:
            raise ValueError("request_timeout must be positive")


@dataclass
class EmbedField:
    """Represents a Discord embed field."""

    name: str
    value: str
    inline: bool = False

    def __post_init__(self):
        """Validate field data."""
        if len(self.name) > 256:
            self.name = self.name[:253] + "..."
        if len(self.value) > 1024:
            self.value = self.value[:1021] + "..."


@dataclass
class WebhookMessage:
    """Represents a complete webhook message."""

    title: str
    description: str
    level: LogLevel = LogLevel.INFO
    fields: list[EmbedField] = field(default_factory=list)
    footer: str | None = None
    content: str | None = None
    timestamp: datetime | None = None
    author_name: str | None = None
    author_icon_url: str | None = None
    author_url: str | None = None
    thumbnail_url: str | None = None
    image_url: str | None = None

    def __post_init__(self):
        """Set default timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class RateLimitTracker:
    """Memory-efficient rate limit tracker using sliding window."""

    def __init__(self, max_requests: int, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: list[float] = []
        self._lock = asyncio.Lock()

    async def can_proceed(self) -> bool:
        """Check if request can proceed without hitting rate limit."""
        async with self._lock:
            now = time.time()
            # Remove old requests outside the window
            cutoff = now - self.window_seconds
            self._requests = [
                req_time for req_time in self._requests if req_time > cutoff
            ]

            if len(self._requests) < self.max_requests:
                self._requests.append(now)
                return True
            return False

    async def get_retry_after(self) -> float:
        """Get seconds to wait before next request."""
        if not self._requests:
            return 0.0

        oldest_request = min(self._requests)
        retry_after = self.window_seconds - (time.time() - oldest_request)
        return max(0.0, retry_after)


class WebhookFormatter:
    """Formats webhook messages for Discord."""

    # Color mapping for log levels
    LEVEL_COLORS = {
        LogLevel.DEBUG: 0x95A5A6,  # Gray
        LogLevel.INFO: 0x3498DB,  # Blue
        LogLevel.WARNING: 0xF39C12,  # Orange
        LogLevel.ERROR: 0xE74C3C,  # Red
        LogLevel.CRITICAL: 0x8B0000,  # Dark Red
        LogLevel.SUCCESS: 0x27AE60,  # Green
        LogLevel.SYSTEM: 0x9B59B6,  # Purple
        LogLevel.USER: 0x1ABC9C,  # Teal
    }

    # Emoji mapping for log levels
    LEVEL_EMOJIS = {
        LogLevel.DEBUG: "🔍",
        LogLevel.INFO: "ℹ️",
        LogLevel.WARNING: "⚠️",
        LogLevel.ERROR: "❌",
        LogLevel.CRITICAL: "🚨",
        LogLevel.SUCCESS: "✅",
        LogLevel.SYSTEM: "🔧",
        LogLevel.USER: "👤",
    }

    def __init__(self, config: WebhookConfig, bot: Any | None = None):
        self.config = config
        self.bot = bot
        self.timezone = pytz.timezone(config.timezone)

    def format_message(self, message: WebhookMessage) -> dict[str, Any]:
        """Format webhook message for Discord API."""
        # Create embed
        embed = {
            "title": f"{self.LEVEL_EMOJIS.get(message.level, '📝')} {message.title}",
            "description": self._truncate_text(
                message.description, self.config.max_description_length
            ),
            "color": self.LEVEL_COLORS.get(
                message.level, self.LEVEL_COLORS[LogLevel.INFO]
            ),
            "timestamp": message.timestamp.isoformat(),
            "footer": {
                "text": message.footer or f"QuranBot • {self._get_formatted_time()}"
            },
        }

        # Add author info (user avatar and name)
        if message.author_name or message.author_icon_url:
            embed["author"] = {}
            if message.author_name:
                embed["author"]["name"] = message.author_name
            if message.author_icon_url:
                embed["author"]["icon_url"] = message.author_icon_url
            if message.author_url:
                embed["author"]["url"] = message.author_url

        # Add thumbnail (small image in top-right)
        if message.thumbnail_url:
            embed["thumbnail"] = {"url": message.thumbnail_url}

        # Add image (large image at bottom)
        if message.image_url:
            embed["image"] = {"url": message.image_url}

        # Add fields (limited to prevent embed size issues)
        if message.fields:
            embed["fields"] = []
            for field in message.fields[: self.config.max_embed_fields]:
                embed["fields"].append(
                    {"name": field.name, "value": field.value, "inline": field.inline}
                )

        # Prepare payload
        # Don't override username/avatar - let Discord use the webhook's configured settings
        payload = {
            "embeds": [embed],
        }
        
        # Only add username/avatar if explicitly requested (for backward compatibility)
        # This allows each webhook to use its own configured name and avatar
        if hasattr(self, '_override_webhook_identity') and self._override_webhook_identity:
            bot_avatar_url = "https://cdn.discordapp.com/attachments/1044035927281262673/1044036084692160512/PFP_Cropped_-_Animated.gif"
            if self.bot and hasattr(self.bot, 'user') and self.bot.user and self.bot.user.avatar:
                bot_avatar_url = self.bot.user.avatar.url
            payload["username"] = "QuranBot"
            payload["avatar_url"] = bot_avatar_url

        # Add content for pings if specified
        if message.content:
            payload["content"] = message.content

        return payload

    def _get_formatted_time(self) -> str:
        """Get formatted timestamp in configured timezone."""
        try:
            now_tz = datetime.now(self.timezone)
            return now_tz.strftime("%m/%d %I:%M %p %Z")
        except Exception:
            return datetime.now().strftime("%m/%d %I:%M %p UTC")

    def _truncate_text(self, text: str, max_length: int) -> str:
        """Safely truncate text to fit Discord limits."""
        if len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."


class WebhookSender:
    """Handles sending webhook requests with retries and error handling."""

    def __init__(self, config: WebhookConfig, logger: StructuredLogger):
        self.config = config
        self.logger = logger
        self.session: aiohttp.ClientSession | None = None
        self._closed = False

    async def initialize(self) -> None:
        """Initialize the webhook sender."""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=self.config.request_timeout)
            self.session = aiohttp.ClientSession(
                timeout=timeout, headers={"User-Agent": "QuranBot-WebhookLogger/2.0"}
            )

    async def close(self) -> None:
        """Close the webhook sender and cleanup resources."""
        self._closed = True
        if self.session:
            await self.session.close()
            self.session = None

    async def send_webhook(self, payload: dict[str, Any]) -> bool:
        """Send webhook with retries and proper error handling."""
        if self._closed or not self.session:
            await self.logger.warning("Webhook sender not initialized or closed")
            return False

        for attempt in range(self.config.retry_attempts):
            try:
                async with self.session.post(
                    self.config.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if response.status in (200, 204):
                        # Discord webhooks return 204 No Content on success
                        return True
                    elif response.status == 429:
                        # Rate limited by Discord
                        retry_after = int(response.headers.get("Retry-After", 60))
                        await self.logger.warning(
                            "Discord webhook rate limited",
                            {"retry_after": retry_after, "attempt": attempt + 1},
                        )
                        if attempt < self.config.retry_attempts - 1:
                            await asyncio.sleep(retry_after)
                        continue
                    else:
                        error_text = await response.text()
                        await self.logger.error(
                            "Webhook request failed",
                            {
                                "status": response.status,
                                "response": error_text[:500],
                                "attempt": attempt + 1,
                            },
                        )

            except TimeoutError:
                await self.logger.warning(
                    "Webhook request timed out",
                    {"attempt": attempt + 1, "timeout": self.config.request_timeout},
                )
            except Exception as e:
                await self.logger.error(
                    "Webhook request error", {"error": str(e), "attempt": attempt + 1}
                )

            # Wait before retry (except on last attempt)
            if attempt < self.config.retry_attempts - 1:
                await asyncio.sleep(
                    self.config.retry_delay * (2**attempt)
                )  # Exponential backoff

        return False


class ModernWebhookLogger:
    """
    Modern, async-first webhook logger for Discord notifications.

    This class provides a clean, reliable interface for sending structured
    log messages to Discord via webhooks. It's designed to integrate seamlessly
    with the QuranBot's modernized architecture.

    Features:
    - Async/await support with proper error handling
    - Memory-efficient rate limiting
    - Automatic retries with exponential backoff
    - Type-safe configuration and validation
    - Integration with structured logging
    - Graceful degradation on errors
    - Resource cleanup and lifecycle management
    """

    def __init__(
        self,
        config: WebhookConfig,
        logger: StructuredLogger,
        container: Any | None = None,
        bot: Any | None = None,
    ):
        self.config = config
        self.logger = logger
        self.container = container
        self.bot = bot

        # Initialize components
        self.rate_limiter = RateLimitTracker(
            config.max_logs_per_minute, config.rate_limit_window
        )
        self.formatter = WebhookFormatter(config, bot)
        self.sender = WebhookSender(config, logger)

        # State tracking
        self.initialized = False
        self._closed = False

        # Weak reference to prevent circular dependencies
        if container:
            self._container_ref = weakref.ref(container)
        else:
            self._container_ref = None

    async def initialize(self) -> bool:
        """Initialize the webhook logger."""
        try:
            await self.sender.initialize()

            self.initialized = True
            await self.logger.info(
                "Modern webhook logger initialized",
                {
                    "webhook_url": self.config.webhook_url[:50] + "...",
                    "rate_limit": f"{self.config.max_logs_per_minute}/min",
                    "timezone": self.config.timezone,
                },
            )
            return True

        except Exception as e:
            await self.logger.error(
                "Failed to initialize webhook logger", {"error": str(e)}
            )
            return False

    async def shutdown(self) -> None:
        """Shutdown the webhook logger gracefully."""
        if self._closed:
            return

        self._closed = True

        try:
            # Send shutdown notification
            if self.initialized:
                await self.log_system(
                    "Webhook Logger Shutdown", "Webhook logger is shutting down"
                )

            # Cleanup resources
            await self.sender.close()

            await self.logger.info("Webhook logger shutdown completed")

        except Exception as e:
            await self.logger.error(
                "Error during webhook logger shutdown", {"error": str(e)}
            )

    async def _send_message(self, message: WebhookMessage, force: bool = False) -> bool:
        """Send a webhook message with rate limiting."""
        if self._closed or not self.initialized:
            return False

        # Check rate limiting (unless forced)
        if not force and not await self.rate_limiter.can_proceed():
            retry_after = await self.rate_limiter.get_retry_after()
            await self.logger.debug(
                "Webhook message rate limited",
                {"retry_after": retry_after, "level": message.level.value},
            )
            return False

        try:
            # Format and send message
            payload = self.formatter.format_message(message)
            success = await self.sender.send_webhook(payload)

            if success:
                await self.logger.debug(
                    "Webhook message sent successfully",
                    {"level": message.level.value, "title": message.title},
                )
            else:
                await self.logger.warning(
                    "Failed to send webhook message",
                    {"level": message.level.value, "title": message.title},
                )

            return success

        except Exception as e:
            await self.logger.error(
                "Error sending webhook message",
                {"error": str(e), "level": message.level.value, "title": message.title},
            )
            return False

    # Public logging methods

    async def log_error(
        self,
        title: str,
        description: str,
        exception: Exception | None = None,
        context: dict[str, Any] | None = None,
        ping_owner: bool = True,
    ) -> bool:
        """Log an error with optional owner ping."""
        fields = []
        content = None

        if exception:
            fields.extend(
                [
                    EmbedField("Exception Type", type(exception).__name__, True),
                    EmbedField("Exception Message", str(exception)[:1024], False),
                ]
            )

        if context:
            for key, value in context.items():
                fields.append(
                    EmbedField(key.replace("_", " ").title(), str(value), True)
                )

        if ping_owner and self.config.enable_pings and self.config.owner_user_id:
            content = f"🚨 <@{self.config.owner_user_id}> **ERROR DETECTED** 🚨"

        message = WebhookMessage(
            title=title,
            description=description,
            level=LogLevel.ERROR,
            fields=fields,
            content=content,
        )

        return await self._send_message(message)

    async def log_critical(
        self,
        title: str,
        description: str,
        exception: Exception | None = None,
        context: dict[str, Any] | None = None,
        ping_owner: bool = True,
    ) -> bool:
        """Log a critical error with owner ping."""
        fields = []
        content = None

        if exception:
            fields.extend(
                [
                    EmbedField("Exception Type", type(exception).__name__, True),
                    EmbedField("Exception Message", str(exception)[:1024], False),
                ]
            )

        if context:
            for key, value in context.items():
                fields.append(
                    EmbedField(key.replace("_", " ").title(), str(value), True)
                )

        if ping_owner and self.config.enable_pings and self.config.owner_user_id:
            content = f"🆘 <@{self.config.owner_user_id}> **CRITICAL ERROR** 🆘"

        message = WebhookMessage(
            title=title,
            description=f"🚨 **CRITICAL ERROR** 🚨\n\n{description}",
            level=LogLevel.CRITICAL,
            fields=fields,
            content=content,
        )

        return await self._send_message(message)

    async def log_warning(
        self, title: str, description: str, context: dict[str, Any] | None = None
    ) -> bool:
        """Log a warning message."""
        fields = []

        if context:
            for key, value in context.items():
                fields.append(
                    EmbedField(key.replace("_", " ").title(), str(value), True)
                )

        message = WebhookMessage(
            title=title, description=description, level=LogLevel.WARNING, fields=fields
        )

        return await self._send_message(message)

    async def log_info(
        self, title: str, description: str, context: dict[str, Any] | None = None
    ) -> bool:
        """Log an info message."""
        fields = []

        if context:
            for key, value in context.items():
                fields.append(
                    EmbedField(key.replace("_", " ").title(), str(value), True)
                )

        message = WebhookMessage(
            title=title, description=description, level=LogLevel.INFO, fields=fields
        )

        return await self._send_message(message)

    async def log_success(
        self, title: str, description: str, context: dict[str, Any] | None = None
    ) -> bool:
        """Log a success message."""
        fields = []

        if context:
            for key, value in context.items():
                fields.append(
                    EmbedField(key.replace("_", " ").title(), str(value), True)
                )

        message = WebhookMessage(
            title=title, description=description, level=LogLevel.SUCCESS, fields=fields
        )

        return await self._send_message(message)

    async def log_system(
        self, title: str, description: str, context: dict[str, Any] | None = None
    ) -> bool:
        """Log a system event."""
        fields = []

        if context:
            for key, value in context.items():
                fields.append(
                    EmbedField(key.replace("_", " ").title(), str(value), True)
                )

        message = WebhookMessage(
            title=title, description=description, level=LogLevel.SYSTEM, fields=fields
        )

        return await self._send_message(message)

    async def log_user_activity(
        self,
        title: str,
        description: str,
        context: dict[str, Any] | None = None,
        user_name: str | None = None,
        user_avatar_url: str | None = None,
        user_profile_url: str | None = None,
    ) -> bool:
        """Log user activity with optional user avatar and info."""
        fields = []

        if context:
            for key, value in context.items():
                fields.append(
                    EmbedField(key.replace("_", " ").title(), str(value), True)
                )

        message = WebhookMessage(
            title=title,
            description=description,
            level=LogLevel.USER,
            fields=fields,
            author_name=user_name,
            author_icon_url=user_avatar_url,
            author_url=user_profile_url,
        )

        return await self._send_message(message)

    async def log_quran_command_usage(
        self,
        command_name: str,
        user_name: str,
        user_id: int,
        user_avatar_url: str | None = None,
        command_details: dict[str, Any] | None = None,
    ) -> bool:
        """
        Log QuranBot command usage (verse, quiz, credits, etc.).

        Args:
            command_name: Name of the QuranBot command used
            user_name: User's display name
            user_id: User's Discord ID
            user_avatar_url: User's avatar URL
            command_details: Command-specific details
        """
        # QuranBot command emojis
        command_emojis = {
            "verse": "📖",
            "quiz": "🧠",
            "credits": "ℹ️",
            "interval": "⏰",
            "leaderboard": "🏆",
            "default": "💬",
        }

        emoji = command_emojis.get(command_name, command_emojis["default"])

        fields = [
            EmbedField("Command", f"!{command_name}", True),
            EmbedField("User ID", str(user_id), True),
            EmbedField("Time", f"<t:{int(time.time())}:R>", True),
        ]

        if command_details:
            for key, value in command_details.items():
                fields.append(
                    EmbedField(key.replace("_", " ").title(), str(value)[:1024], True)
                )

        message = WebhookMessage(
            title=f"{emoji} QuranBot Command Used",
            description=f"**{user_name}** used `!{command_name}` command",
            level=LogLevel.USER,
            fields=fields,
            author_name=user_name,
            author_icon_url=user_avatar_url,
            author_url=f"https://discord.com/users/{user_id}",
        )

        return await self._send_message(message)

    async def log_voice_channel_activity(
        self,
        activity_type: str,
        user_name: str,
        user_id: int,
        channel_name: str,
        user_avatar_url: str | None = None,
        additional_info: dict[str, Any] | None = None,
    ) -> bool:
        """
        Log QuranBot voice channel activity (join/leave during audio playback).

        Args:
            activity_type: Type of voice activity (join, leave)
            user_name: User's display name
            user_id: User's Discord ID
            channel_name: Name of the voice channel
            user_avatar_url: User's avatar URL
            additional_info: Additional context
        """
        activity_emojis = {"join": "🎤", "leave": "🔇", "default": "🔊"}

        emoji = activity_emojis.get(activity_type, activity_emojis["default"])
        action_text = "joined" if activity_type == "join" else "left"

        fields = [
            EmbedField("Activity", action_text.title(), True),
            EmbedField("Channel", channel_name, True),
            EmbedField("Time", f"<t:{int(time.time())}:R>", True),
        ]

        if additional_info:
            for key, value in additional_info.items():
                fields.append(
                    EmbedField(key.replace("_", " ").title(), str(value)[:1024], True)
                )

        message = WebhookMessage(
            title=f"{emoji} Voice Channel Activity",
            description=f"**{user_name}** {action_text} QuranBot voice channel",
            level=LogLevel.USER,
            fields=fields,
            author_name=user_name,
            author_icon_url=user_avatar_url,
            author_url=f"https://discord.com/users/{user_id}",
        )

        return await self._send_message(message)

    async def log_control_panel_interaction(
        self,
        interaction_type: str,
        user_name: str,
        user_id: int,
        action_performed: str,
        user_avatar_url: str | None = None,
        panel_details: dict[str, Any] | None = None,
    ) -> bool:
        """
        Log QuranBot control panel interactions (button clicks, controls).

        Args:
            interaction_type: Type of panel interaction (button_click, control_change)
            user_name: User's display name
            user_id: User's Discord ID
            action_performed: What action was performed
            user_avatar_url: User's avatar URL
            panel_details: Panel-specific details
        """
        # Control panel interaction emojis
        panel_emojis = {
            "play_pause": "⏯️",
            "skip_next": "⏭️",
            "skip_previous": "⏮️",
            "surah_select": "📖",
            "reciter_change": "🎙️",
            "volume_change": "🔊",
            "shuffle_toggle": "🔀",
            "loop_toggle": "🔁",
            "default": "🎛️",
        }

        # Try to match the action to get appropriate emoji
        emoji = panel_emojis.get(
            action_performed.lower().replace(" ", "_"), panel_emojis["default"]
        )

        fields = [
            EmbedField("Action", action_performed, True),
            EmbedField("User ID", str(user_id), True),
            EmbedField("Time", f"<t:{int(time.time())}:R>", True),
        ]

        if panel_details:
            for key, value in panel_details.items():
                fields.append(
                    EmbedField(key.replace("_", " ").title(), str(value)[:1024], True)
                )

        message = WebhookMessage(
            title=f"{emoji} Control Panel Interaction",
            description=f"**{user_name}** {action_performed.lower()} via control panel",
            level=LogLevel.USER,
            fields=fields,
            author_name=user_name,
            author_icon_url=user_avatar_url,
            author_url=f"https://discord.com/users/{user_id}",
        )

        return await self._send_message(message)

    async def log_quran_quiz_activity(
        self,
        user_name: str,
        user_id: int,
        question_text: str,
        user_answer: str,
        correct_answer: str,
        is_correct: bool,
        user_avatar_url: str | None = None,
        quiz_stats: dict[str, Any] | None = None,
    ) -> bool:
        """
        Log QuranBot quiz activity with user avatar and stats.

        Args:
            user_name: User's display name
            user_id: User's Discord ID
            question_text: The Quran quiz question
            user_answer: User's answer
            correct_answer: The correct answer
            is_correct: Whether the answer was correct
            user_avatar_url: User's avatar URL
            quiz_stats: Quiz-specific stats (streak, score, etc.)
        """
        emoji = "✅" if is_correct else "❌"
        result_text = "Correct!" if is_correct else "Incorrect"

        fields = [
            EmbedField("Result", f"{emoji} {result_text}", True),
            EmbedField("User ID", str(user_id), True),
            EmbedField("Time", f"<t:{int(time.time())}:R>", True),
            EmbedField("Question", question_text[:1000], False),
            EmbedField("User Answer", user_answer, True),
            EmbedField("Correct Answer", correct_answer, True),
        ]

        if quiz_stats:
            for key, value in quiz_stats.items():
                fields.append(
                    EmbedField(key.replace("_", " ").title(), str(value), True)
                )

        message = WebhookMessage(
            title=f"🧠 Quran Quiz - {result_text}",
            description=f"**{user_name}** answered a Quran quiz question",
            level=LogLevel.USER,
            fields=fields,
            author_name=user_name,
            author_icon_url=user_avatar_url,
            author_url=f"https://discord.com/users/{user_id}",
        )

        return await self._send_message(message)

    async def log_audio_event(
        self,
        event_type: str,
        error_message: str | None = None,
        event_description: str | None = None,
        audio_details: dict[str, Any] | None = None,
        ping_owner: bool = False,
    ) -> bool:
        """
        Log QuranBot audio events (surah changes, reciter changes, failures, recoveries).

        Args:
            event_type: Type of audio event
            error_message: Error message (for failures) or event description
            event_description: Additional event description (deprecated, use error_message)
            audio_details: Audio-specific details
            ping_owner: Whether to ping the owner for critical events
        """
        # Use error_message if provided, otherwise fall back to event_description
        description = error_message or event_description or f"Audio event: {event_type}"
        
        # Audio event emojis
        audio_emojis = {
            "surah_start": "▶️",
            "surah_end": "⏹️",
            "surah_change": "🔄",
            "reciter_change": "🎙️",
            "audio_start": "🎵",
            "audio_stop": "⏸️",
            "audio_pause": "⏸️",
            "audio_resume": "▶️",
            "voice_connect": "🔗",
            "voice_disconnect": "🔌",
            "voice_reconnect": "🔄",
            "playlist_shuffle": "🔀",
            "playlist_loop": "🔁",
            "playback_failure": "❌",
            "playback_timeout": "🔇",
            "playback_recovery": "✅",
            "connection_failure": "🔌",
            "connection_recovery": "✅",
            "critical_failure_escalation": "🚨",
            "emergency_failure_escalation": "🆘",
            "extended_silence_emergency": "🔇",
            "default": "🎵",
        }

        emoji = audio_emojis.get(event_type, audio_emojis["default"])
        
        # Determine log level based on event type
        if event_type in ["playback_failure", "playback_timeout", "connection_failure", "critical_failure_escalation", "emergency_failure_escalation", "extended_silence_emergency"]:
            level = LogLevel.CRITICAL
        elif event_type in ["playback_recovery", "connection_recovery"]:
            level = LogLevel.SUCCESS
        else:
            level = LogLevel.SYSTEM

        fields = [
            EmbedField("Event Type", event_type.replace("_", " ").title(), True),
            EmbedField("Time", f"<t:{int(time.time())}:R>", True),
        ]

        if audio_details:
            for key, value in audio_details.items():
                fields.append(
                    EmbedField(key.replace("_", " ").title(), str(value)[:1024], True)
                )

        # Add owner ping for critical events
        content = None
        if ping_owner and self.config.enable_pings and self.config.owner_user_id:
            if event_type in ["playback_failure", "playback_timeout", "connection_failure"]:
                content = f"🚨 <@{self.config.owner_user_id}> **AUDIO SYSTEM ALERT** 🚨"
            elif event_type in ["critical_failure_escalation", "emergency_failure_escalation"]:
                content = f"🆘 <@{self.config.owner_user_id}> **CRITICAL SYSTEM FAILURE** 🆘"
            elif event_type == "extended_silence_emergency":
                content = f"🔇 <@{self.config.owner_user_id}> **EXTENDED SILENCE EMERGENCY** 🔇"

        message = WebhookMessage(
            title=f"{emoji} QuranBot Audio Event",
            description=description,
            level=level,
            fields=fields,
            content=content,
        )

        return await self._send_message(message)

    # Bot lifecycle event methods
    async def log_bot_startup(
        self,
        version: str,
        startup_duration: float,
        services_loaded: int,
        guild_count: int = 0,
    ) -> bool:
        """
        Log QuranBot startup event.

        Args:
            version: Bot version
            startup_duration: Time taken to start up
            services_loaded: Number of services initialized
            guild_count: Number of connected guilds
        """
        message = WebhookMessage(
            title="🚀 QuranBot Started",
            description=f"**QuranBot v{version}** has started successfully and is ready for 24/7 Quran recitation",
            level=LogLevel.SUCCESS,
            fields=[
                EmbedField("Version", version, True),
                EmbedField("Startup Time", f"{startup_duration:.1f}s", True),
                EmbedField("Services Loaded", str(services_loaded), True),
                EmbedField("Connected Guilds", str(guild_count), True),
                EmbedField("Mode", "100% Automated Continuous Recitation", True),
                EmbedField("Started", f"<t:{int(time.time())}:R>", True),
            ],
        )

        return await self._send_message(
            message, force=True
        )  # Force send startup message

    async def log_bot_shutdown(
        self,
        reason: str = "Graceful shutdown",
        uptime: str | None = None,
        final_stats: dict[str, Any] | None = None,
    ) -> bool:
        """
        Log QuranBot shutdown event.

        Args:
            reason: Reason for shutdown
            uptime: Bot uptime duration
            final_stats: Final statistics before shutdown
        """
        fields = [
            EmbedField("Shutdown Reason", reason, True),
            EmbedField("Shutdown Time", f"<t:{int(time.time())}:R>", True),
        ]

        if uptime:
            fields.append(EmbedField("Uptime", uptime, True))

        if final_stats:
            for key, value in final_stats.items():
                fields.append(
                    EmbedField(key.replace("_", " ").title(), str(value), True)
                )

        message = WebhookMessage(
            title="⏹️ QuranBot Shutdown",
            description=f"**QuranBot is shutting down**\n\n{reason}",
            level=LogLevel.SYSTEM,
            fields=fields,
        )

        return await self._send_message(
            message, force=True
        )  # Force send shutdown message

    async def log_bot_crash(
        self,
        error_message: str,
        exception: Exception | None = None,
        crash_context: dict[str, Any] | None = None,
        ping_owner: bool = True,
    ) -> bool:
        """
        Log QuranBot crash with owner notification.

        Args:
            error_message: Description of the crash
            exception: Exception that caused the crash
            crash_context: Additional crash context
            ping_owner: Whether to ping the owner
        """
        fields = [
            EmbedField("Crash Time", f"<t:{int(time.time())}:R>", True),
            EmbedField("Impact", "🚨 QuranBot is down", True),
        ]

        if exception:
            fields.extend(
                [
                    EmbedField("Exception Type", type(exception).__name__, True),
                    EmbedField("Exception Message", str(exception)[:1024], False),
                ]
            )

        if crash_context:
            for key, value in crash_context.items():
                fields.append(
                    EmbedField(key.replace("_", " ").title(), str(value)[:1024], True)
                )

        content = None
        if ping_owner and self.config.enable_pings and self.config.owner_user_id:
            content = f"🆘 <@{self.config.owner_user_id}> **QURANBOT CRASHED** 🆘"

        message = WebhookMessage(
            title="💥 QuranBot Crashed",
            description=f"🚨 **CRITICAL ERROR** 🚨\n\n**QuranBot has crashed and is no longer running**\n\n{error_message}",
            level=LogLevel.CRITICAL,
            fields=fields,
            content=content,
        )

        return await self._send_message(message, force=True)

    async def log_discord_disconnect(
        self,
        disconnect_reason: str,
        reconnect_attempts: int = 0,
        downtime_duration: float | None = None,
    ) -> bool:
        """
        Log Discord connection issues.

        Args:
            disconnect_reason: Reason for disconnection
            reconnect_attempts: Number of reconnection attempts
            downtime_duration: Duration of disconnection
        """
        fields = [
            EmbedField("Disconnect Reason", disconnect_reason, True),
            EmbedField("Disconnect Time", f"<t:{int(time.time())}:R>", True),
            EmbedField("Reconnect Attempts", str(reconnect_attempts), True),
        ]

        if downtime_duration:
            fields.append(EmbedField("Downtime", f"{downtime_duration:.1f}s", True))

        message = WebhookMessage(
            title="🔌 Discord Disconnection",
            description=f"**QuranBot lost connection to Discord**\n\n{disconnect_reason}",
            level=LogLevel.WARNING,
            fields=fields,
        )

        return await self._send_message(message)

    async def log_discord_reconnect(
        self,
        reconnect_duration: float,
        was_successful: bool = True,
        attempts_made: int = 1,
    ) -> bool:
        """
        Log successful Discord reconnection.

        Args:
            reconnect_duration: Time taken to reconnect
            was_successful: Whether reconnection was successful
            attempts_made: Number of attempts needed
        """
        if was_successful:
            emoji = "✅"
            title = "Discord Reconnected"
            description = "**QuranBot successfully reconnected to Discord**\n\nQuran recitation service restored"
            level = LogLevel.SUCCESS
        else:
            emoji = "❌"
            title = "Discord Reconnection Failed"
            description = "**QuranBot failed to reconnect to Discord**\n\nQuran recitation service is still down"
            level = LogLevel.ERROR

        fields = [
            EmbedField("Reconnect Time", f"<t:{int(time.time())}:R>", True),
            EmbedField("Duration", f"{reconnect_duration:.1f}s", True),
            EmbedField("Attempts", str(attempts_made), True),
            EmbedField("Status", "✅ Online" if was_successful else "❌ Offline", True),
        ]

        message = WebhookMessage(
            title=f"{emoji} {title}",
            description=description,
            level=level,
            fields=fields,
        )

        return await self._send_message(message)

    async def log_voice_connection_issue(
        self,
        issue_type: str,
        error_details: str,
        channel_name: str,
        recovery_action: str | None = None,
        additional_info: dict[str, Any] | None = None,
        ping_owner: bool = False,
    ) -> bool:
        """
        Log voice channel connection issues.

        Args:
            issue_type: Type of voice issue (connection_failed, disconnected, timeout, connection_recovery)
            error_details: Details about the error or recovery
            channel_name: Name of the voice channel
            recovery_action: Action taken to recover
            additional_info: Additional context information
            ping_owner: Whether to ping the owner for critical issues
        """
        issue_emojis = {
            "connection_failed": "🔴",
            "disconnected": "🔌",
            "timeout": "⏱️",
            "connection_recovery": "✅",
            "recovery_success": "✅",
            "default": "⚠️",
        }

        emoji = issue_emojis.get(issue_type, issue_emojis["default"])
        
        # Determine log level and title based on issue type
        if issue_type in ["connection_recovery", "recovery_success"]:
            level = LogLevel.SUCCESS
            title = "Voice Connection Recovered"
        elif issue_type in ["connection_failed", "disconnected", "timeout"]:
            level = LogLevel.ERROR
            title = "Voice Connection Issue"
        else:
            level = LogLevel.WARNING
            title = "Voice Channel Issue"

        fields = [
            EmbedField("Issue Type", issue_type.replace("_", " ").title(), True),
            EmbedField("Channel", channel_name, True),
            EmbedField("Time", f"<t:{int(time.time())}:R>", True),
            EmbedField("Error Details", error_details[:1024], False),
        ]

        if recovery_action:
            fields.append(EmbedField("Recovery Action", recovery_action, False))
            
        if additional_info:
            for key, value in additional_info.items():
                fields.append(
                    EmbedField(key.replace("_", " ").title(), str(value)[:1024], True)
                )

        # Add owner ping for critical connection issues
        content = None
        if ping_owner and self.config.enable_pings and self.config.owner_user_id:
            if issue_type in ["connection_failed", "disconnected", "timeout"]:
                content = f"🔌 <@{self.config.owner_user_id}> **VOICE CONNECTION ALERT** 🔌"

        message = WebhookMessage(
            title=f"{emoji} {title}",
            description=f"**Voice channel connection issue detected**\n\n{error_details}",
            level=level,
            fields=fields,
            content=content,
        )

        return await self._send_message(message)
