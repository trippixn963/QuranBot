# =============================================================================
# QuranBot - Security Module
# =============================================================================
# Comprehensive security utilities including rate limiting, input validation,
# and permission checking for Discord bot commands and interactions.
# =============================================================================

import asyncio
from collections import defaultdict, deque
from collections.abc import Callable
from functools import wraps
import hashlib
import re
import time
from typing import Any

import discord

from .exceptions import RateLimitError, SecurityError, ValidationError
from .structured_logger import StructuredLogger

# =============================================================================
# Rate Limiting System
# =============================================================================


class RateLimiter:
    """
    Advanced rate limiting system for Discord commands and interactions.

    Supports multiple rate limiting strategies:
    - Per-user rate limiting
    - Per-guild rate limiting
    - Per-command rate limiting
    - Global rate limiting
    - Sliding window and token bucket algorithms
    """

    def __init__(self, logger: StructuredLogger | None = None):
        self.logger = logger

        # Rate limit storage: {scope: {identifier: deque of timestamps}}
        self._user_requests: dict[str, dict[int, deque]] = defaultdict(
            lambda: defaultdict(deque)
        )
        self._guild_requests: dict[str, dict[int, deque]] = defaultdict(
            lambda: defaultdict(deque)
        )
        self._command_requests: dict[str, deque] = defaultdict(deque)
        self._global_requests: deque = deque()

        # Token bucket storage: {scope: {identifier: (tokens, last_refill)}}
        self._token_buckets: dict[str, dict[int, tuple]] = defaultdict(dict)

        # Cleanup task
        self._cleanup_task: asyncio.Task | None = None
        self._start_cleanup_task()

    def _start_cleanup_task(self):
        """Start background cleanup task"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_old_requests())

    async def _cleanup_old_requests(self):
        """Clean up old request timestamps periodically"""
        while True:
            try:
                await asyncio.sleep(300)  # Clean up every 5 minutes
                current_time = time.time()

                # Clean up user requests (older than 1 hour)
                for command_requests in self._user_requests.values():
                    for user_id, timestamps in list(command_requests.items()):
                        while timestamps and current_time - timestamps[0] > 3600:
                            timestamps.popleft()
                        if not timestamps:
                            del command_requests[user_id]

                # Clean up guild requests (older than 1 hour)
                for command_requests in self._guild_requests.values():
                    for guild_id, timestamps in list(command_requests.items()):
                        while timestamps and current_time - timestamps[0] > 3600:
                            timestamps.popleft()
                        if not timestamps:
                            del command_requests[guild_id]

                # Clean up command requests (older than 1 hour)
                for command, timestamps in self._command_requests.items():
                    while timestamps and current_time - timestamps[0] > 3600:
                        timestamps.popleft()

                # Clean up global requests (older than 1 hour)
                while (
                    self._global_requests
                    and current_time - self._global_requests[0] > 3600
                ):
                    self._global_requests.popleft()

            except asyncio.CancelledError:
                break
            except Exception as e:
                if self.logger:
                    await self.logger.error(
                        "Rate limiter cleanup error", {"error": str(e)}
                    )

    async def check_rate_limit(
        self,
        user_id: int,
        guild_id: int | None,
        command_name: str,
        user_limit: int = 5,
        user_window: int = 60,
        guild_limit: int = 20,
        guild_window: int = 60,
        command_limit: int = 100,
        command_window: int = 60,
        global_limit: int = 1000,
        global_window: int = 60,
    ) -> bool:
        """
        Check if a request should be rate limited.

        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID (None for DMs)
            command_name: Name of the command being executed
            user_limit: Max requests per user per window
            user_window: User rate limit window in seconds
            guild_limit: Max requests per guild per window
            guild_window: Guild rate limit window in seconds
            command_limit: Max requests per command per window
            command_window: Command rate limit window in seconds
            global_limit: Max global requests per window
            global_window: Global rate limit window in seconds

        Returns:
            True if request should proceed, False if rate limited

        Raises:
            RateLimitError: If rate limit is exceeded
        """
        current_time = time.time()

        # Check user rate limit
        user_requests = self._user_requests[command_name][user_id]
        self._clean_window(user_requests, current_time, user_window)

        if len(user_requests) >= user_limit:
            if self.logger:
                await self.logger.warning(
                    "User rate limit exceeded",
                    {
                        "user_id": user_id,
                        "command": command_name,
                        "limit": user_limit,
                        "window": user_window,
                        "current_requests": len(user_requests),
                    },
                )
            raise RateLimitError(
                f"User rate limit exceeded: {user_limit} requests per {user_window} seconds",
                limit_type="user",
                limit=user_limit,
                window=user_window,
                current_count=len(user_requests),
            )

        # Check guild rate limit (if in a guild)
        if guild_id:
            guild_requests = self._guild_requests[command_name][guild_id]
            self._clean_window(guild_requests, current_time, guild_window)

            if len(guild_requests) >= guild_limit:
                if self.logger:
                    await self.logger.warning(
                        "Guild rate limit exceeded",
                        {
                            "guild_id": guild_id,
                            "command": command_name,
                            "limit": guild_limit,
                            "window": guild_window,
                            "current_requests": len(guild_requests),
                        },
                    )
                raise RateLimitError(
                    f"Guild rate limit exceeded: {guild_limit} requests per {guild_window} seconds",
                    limit_type="guild",
                    limit=guild_limit,
                    window=guild_window,
                    current_count=len(guild_requests),
                )

        # Check command rate limit
        command_requests = self._command_requests[command_name]
        self._clean_window(command_requests, current_time, command_window)

        if len(command_requests) >= command_limit:
            if self.logger:
                await self.logger.warning(
                    "Command rate limit exceeded",
                    {
                        "command": command_name,
                        "limit": command_limit,
                        "window": command_window,
                        "current_requests": len(command_requests),
                    },
                )
            raise RateLimitError(
                f"Command rate limit exceeded: {command_limit} requests per {command_window} seconds",
                limit_type="command",
                limit=command_limit,
                window=command_window,
                current_count=len(command_requests),
            )

        # Check global rate limit
        self._clean_window(self._global_requests, current_time, global_window)

        if len(self._global_requests) >= global_limit:
            if self.logger:
                await self.logger.warning(
                    "Global rate limit exceeded",
                    {
                        "limit": global_limit,
                        "window": global_window,
                        "current_requests": len(self._global_requests),
                    },
                )
            raise RateLimitError(
                f"Global rate limit exceeded: {global_limit} requests per {global_window} seconds",
                limit_type="global",
                limit=global_limit,
                window=global_window,
                current_count=len(self._global_requests),
            )

        # Record the request
        user_requests.append(current_time)
        if guild_id:
            guild_requests.append(current_time)
        command_requests.append(current_time)
        self._global_requests.append(current_time)

        return True

    def _clean_window(self, timestamps: deque, current_time: float, window: int):
        """Remove timestamps outside the current window"""
        while timestamps and current_time - timestamps[0] > window:
            timestamps.popleft()

    async def check_token_bucket(
        self,
        user_id: int,
        command_name: str,
        bucket_size: int = 10,
        refill_rate: float = 1.0,
    ) -> bool:
        """
        Check token bucket rate limit.

        Args:
            user_id: Discord user ID
            command_name: Command name
            bucket_size: Maximum tokens in bucket
            refill_rate: Tokens refilled per second

        Returns:
            True if request should proceed, False if no tokens available
        """
        current_time = time.time()
        key = f"{command_name}:{user_id}"

        if key not in self._token_buckets:
            # Initialize new bucket
            self._token_buckets[key] = (bucket_size - 1, current_time)
            return True

        tokens, last_refill = self._token_buckets[key]

        # Calculate tokens to add
        time_passed = current_time - last_refill
        tokens_to_add = time_passed * refill_rate
        new_tokens = min(bucket_size, tokens + tokens_to_add)

        if new_tokens >= 1:
            # Consume one token
            self._token_buckets[key] = (new_tokens - 1, current_time)
            return True
        else:
            # No tokens available
            if self.logger:
                await self.logger.warning(
                    "Token bucket rate limit exceeded",
                    {
                        "user_id": user_id,
                        "command": command_name,
                        "tokens": new_tokens,
                        "bucket_size": bucket_size,
                    },
                )
            return False

    async def get_rate_limit_status(
        self, user_id: int, command_name: str
    ) -> dict[str, Any]:
        """Get current rate limit status for a user and command"""
        current_time = time.time()

        user_requests = self._user_requests[command_name][user_id]
        self._clean_window(user_requests, current_time, 60)  # Default 60s window

        token_bucket_key = f"{command_name}:{user_id}"
        tokens = 0
        if token_bucket_key in self._token_buckets:
            tokens, last_refill = self._token_buckets[token_bucket_key]
            time_passed = current_time - last_refill
            tokens = min(
                10, tokens + time_passed * 1.0
            )  # Default bucket size and refill rate

        return {
            "user_requests_last_minute": len(user_requests),
            "available_tokens": tokens,
            "next_token_in": max(0, 1.0 - tokens) if tokens < 1 else 0,
        }


# =============================================================================
# Rate Limiting Decorators
# =============================================================================


def rate_limit(
    user_limit: int = 5,
    user_window: int = 60,
    guild_limit: int = 20,
    guild_window: int = 60,
    command_limit: int = 100,
    command_window: int = 60,
    global_limit: int = 1000,
    global_window: int = 60,
):
    """
    Rate limiting decorator for Discord commands.

    Args:
        user_limit: Max requests per user per window
        user_window: User rate limit window in seconds
        guild_limit: Max requests per guild per window
        guild_window: Guild rate limit window in seconds
        command_limit: Max requests per command per window
        command_window: Command rate limit window in seconds
        global_limit: Max global requests per window
        global_window: Global rate limit window in seconds
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract interaction from arguments
            interaction = None
            for arg in args:
                if isinstance(arg, discord.Interaction):
                    interaction = arg
                    break

            if not interaction:
                # If no interaction found, proceed without rate limiting
                return await func(*args, **kwargs)

            # Get rate limiter instance (should be injected or available globally)
            from .di_container import DIContainer

            try:
                container = DIContainer.get_instance()
                rate_limiter = container.get(RateLimiter)
            except:
                # If no rate limiter available, proceed without limiting
                return await func(*args, **kwargs)

            try:
                await rate_limiter.check_rate_limit(
                    user_id=interaction.user.id,
                    guild_id=interaction.guild.id if interaction.guild else None,
                    command_name=func.__name__,
                    user_limit=user_limit,
                    user_window=user_window,
                    guild_limit=guild_limit,
                    guild_window=guild_window,
                    command_limit=command_limit,
                    command_window=command_window,
                    global_limit=global_limit,
                    global_window=global_window,
                )

                return await func(*args, **kwargs)

            except RateLimitError as e:
                # Create rate limit response
                embed = discord.Embed(
                    title="⏰ Rate Limit Exceeded",
                    description=f"You're doing that too quickly! {e!s}",
                    color=0xFF6B6B,
                )
                embed.add_field(
                    name="🔄 Try Again",
                    value=f"Please wait {e.window} seconds before trying again.",
                    inline=False,
                )
                embed.set_footer(
                    text="Rate limiting helps keep the bot responsive for everyone"
                )

                try:
                    if interaction.response.is_done():
                        await interaction.followup.send(embed=embed, ephemeral=True)
                    else:
                        await interaction.response.send_message(
                            embed=embed, ephemeral=True
                        )
                except:
                    # If we can't send the rate limit message, just log it
                    pass

                return None

        return wrapper

    return decorator


# =============================================================================
# Input Validation and Sanitization
# =============================================================================


class InputValidator:
    """
    Comprehensive input validation and sanitization for user inputs.
    """

    # Dangerous patterns that should be blocked
    DANGEROUS_PATTERNS = [
        r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>",  # Script tags
        r"javascript:",  # JavaScript URLs
        r"on\w+\s*=",  # Event handlers
        r"@everyone",  # Mass mentions
        r"@here",  # Mass mentions
        r"(?:https?:\/\/)?(?:www\.)?(?:discord\.gg|discord\.com\/invite)\/\w+",  # Discord invites
    ]

    # Compiled regex patterns for performance
    _compiled_patterns = [
        re.compile(pattern, re.IGNORECASE) for pattern in DANGEROUS_PATTERNS
    ]

    @classmethod
    def sanitize_string(
        cls,
        text: str,
        max_length: int = 2000,
        allow_newlines: bool = True,
        allow_mentions: bool = False,
        allow_links: bool = False,
    ) -> str:
        """
        Sanitize user input string.

        Args:
            text: Input text to sanitize
            max_length: Maximum allowed length
            allow_newlines: Whether to allow newline characters
            allow_mentions: Whether to allow user mentions
            allow_links: Whether to allow URLs

        Returns:
            Sanitized text

        Raises:
            ValidationError: If input fails validation
        """
        if not isinstance(text, str):
            raise ValidationError(
                "Input must be a string",
                input_type=type(text).__name__,
                expected_type="str",
            )

        # Check length
        if len(text) > max_length:
            raise ValidationError(
                f"Input too long: {len(text)} characters (max: {max_length})",
                input_length=len(text),
                max_length=max_length,
            )

        # Remove null bytes and control characters
        text = "".join(char for char in text if ord(char) >= 32 or char in "\n\r\t")

        # Check for dangerous patterns
        for pattern in cls._compiled_patterns:
            if pattern.search(text):
                raise ValidationError(
                    "Input contains potentially dangerous content",
                    pattern=pattern.pattern,
                )

        # Handle newlines
        if not allow_newlines:
            text = text.replace("\n", " ").replace("\r", " ")

        # Handle mentions
        if not allow_mentions:
            text = re.sub(r"<@[!&]?\d+>", "[mention removed]", text)

        # Handle links
        if not allow_links:
            text = re.sub(r"https?://\S+", "[link removed]", text)

        return text.strip()

    @classmethod
    def validate_surah_number(cls, surah: int | str) -> int:
        """
        Validate and convert surah number.

        Args:
            surah: Surah number to validate

        Returns:
            Validated surah number as integer

        Raises:
            ValidationError: If surah number is invalid
        """
        try:
            surah_int = int(surah)
        except (ValueError, TypeError):
            raise ValidationError(
                f"Invalid surah number format: {surah}",
                input_value=surah,
                expected_type="integer",
            )

        if not (1 <= surah_int <= 114):
            raise ValidationError(
                f"Surah number must be between 1 and 114, got {surah_int}",
                input_value=surah_int,
                valid_range="1-114",
            )

        return surah_int

    @classmethod
    def validate_ayah_number(cls, ayah: int | str, surah: int) -> int:
        """
        Validate ayah number for a given surah.

        Args:
            ayah: Ayah number to validate
            surah: Surah number for context

        Returns:
            Validated ayah number as integer

        Raises:
            ValidationError: If ayah number is invalid
        """
        try:
            ayah_int = int(ayah)
        except (ValueError, TypeError):
            raise ValidationError(
                f"Invalid ayah number format: {ayah}",
                input_value=ayah,
                expected_type="integer",
            )

        if ayah_int < 1:
            raise ValidationError(
                f"Ayah number must be positive, got {ayah_int}", input_value=ayah_int
            )

        # Note: We don't validate max ayah number here as it requires
        # Quran data which should be handled by the domain layer

        return ayah_int

    @classmethod
    def validate_time_interval(cls, interval: str) -> float:
        """
        Validate and parse time interval string.

        Args:
            interval: Time interval string (e.g., "30m", "2h", "1h30m")

        Returns:
            Time interval in hours as float

        Raises:
            ValidationError: If interval format is invalid
        """
        if not isinstance(interval, str):
            raise ValidationError(
                "Time interval must be a string",
                input_type=type(interval).__name__,
                expected_type="str",
            )

        interval = interval.strip().lower()

        # Pattern for flexible time format
        pattern = r"^(?:(\d+(?:\.\d+)?)h)?(?:(\d+)m)?$"
        match = re.match(pattern, interval)

        if not match:
            # Try simple number format
            try:
                num = float(interval)
                if num <= 24:  # Assume hours if <= 24
                    hours = num
                else:  # Assume minutes if > 24
                    hours = num / 60
            except ValueError:
                raise ValidationError(
                    f"Invalid time interval format: {interval}",
                    input_value=interval,
                    expected_format="30m, 2h, 1h30m, or number",
                )
        else:
            hours_str, minutes_str = match.groups()
            hours = float(hours_str) if hours_str else 0
            minutes = int(minutes_str) if minutes_str else 0
            hours += minutes / 60

        # Validate range (1 minute to 24 hours)
        if not (1 / 60 <= hours <= 24):
            raise ValidationError(
                f"Time interval must be between 1 minute and 24 hours, got {hours:.2f}h",
                input_value=hours,
                valid_range="1 minute to 24 hours",
            )

        return hours

    @classmethod
    def validate_user_id(cls, user_id: int | str) -> int:
        """
        Validate Discord user ID.

        Args:
            user_id: User ID to validate

        Returns:
            Validated user ID as integer

        Raises:
            ValidationError: If user ID is invalid
        """
        try:
            user_id_int = int(user_id)
        except (ValueError, TypeError):
            raise ValidationError(
                f"Invalid user ID format: {user_id}",
                input_value=user_id,
                expected_type="integer",
            )

        # Discord snowflake IDs are 64-bit integers
        if not (17 <= len(str(user_id_int)) <= 20):
            raise ValidationError(
                f"Invalid Discord user ID length: {len(str(user_id_int))}",
                input_value=user_id_int,
                expected_length="17-20 digits",
            )

        return user_id_int


# =============================================================================
# Permission and Security Service
# =============================================================================


class SecurityService:
    """
    Centralized security service for permission checking and security operations.
    """

    def __init__(self, rate_limiter: RateLimiter, logger: StructuredLogger):
        self.rate_limiter = rate_limiter
        self.logger = logger

        # Security configuration
        self.admin_users: set[int] = set()
        self.trusted_guilds: set[int] = set()
        self.blocked_users: set[int] = set()
        self.blocked_guilds: set[int] = set()

        # Load configuration from environment
        self._load_security_config()

    def _load_security_config(self):
        """Load security configuration from environment variables"""
        from src.config import get_config_service

        try:
            config = get_config_service().config

            # Load admin users
            self.admin_users.add(config.DEVELOPER_ID)
            for admin_id in config.admin_user_ids:
                self.admin_users.add(admin_id)

            # Load trusted guilds (if configured)
            if hasattr(config, "TRUSTED_GUILDS") and config.TRUSTED_GUILDS:
                for guild_id in config.TRUSTED_GUILDS.split(","):
                    if guild_id.strip():
                        try:
                            self.trusted_guilds.add(int(guild_id.strip()))
                        except ValueError:
                            pass

            # Load blocked users (if configured)
            if hasattr(config, "BLOCKED_USERS") and config.BLOCKED_USERS:
                blocked_users = config.BLOCKED_USERS
                for user_id in blocked_users.split(","):
                    if user_id.strip():
                        try:
                            self.blocked_users.add(int(user_id.strip()))
                        except ValueError:
                            pass
        except Exception:
            # If config loading fails, continue with empty admin set
            pass

    async def is_admin(self, user_id: int) -> bool:
        """Check if user is an administrator"""
        return user_id in self.admin_users

    async def is_blocked(self, user_id: int, guild_id: int | None = None) -> bool:
        """Check if user or guild is blocked"""
        if user_id in self.blocked_users:
            return True

        if guild_id and guild_id in self.blocked_guilds:
            return True

        return False

    async def is_trusted_guild(self, guild_id: int) -> bool:
        """Check if guild is in trusted list"""
        return guild_id in self.trusted_guilds

    async def check_command_permission(
        self,
        user_id: int,
        guild_id: int | None,
        command_name: str,
        require_admin: bool = False,
    ) -> bool:
        """
        Check if user has permission to execute a command.

        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID (None for DMs)
            command_name: Name of the command
            require_admin: Whether command requires admin privileges

        Returns:
            True if user has permission, False otherwise

        Raises:
            SecurityError: If user/guild is blocked
        """
        # Check if user/guild is blocked
        if await self.is_blocked(user_id, guild_id):
            await self.logger.warning(
                "Blocked user/guild attempted command",
                {"user_id": user_id, "guild_id": guild_id, "command": command_name},
            )
            raise SecurityError(
                "Access denied: User or guild is blocked",
                user_id=user_id,
                guild_id=guild_id,
                reason="blocked",
            )

        # Check admin requirement
        if require_admin and not await self.is_admin(user_id):
            await self.logger.warning(
                "Non-admin user attempted admin command",
                {"user_id": user_id, "guild_id": guild_id, "command": command_name},
            )
            return False

        return True

    async def log_security_event(
        self,
        event_type: str,
        user_id: int,
        guild_id: int | None,
        details: dict[str, Any],
    ):
        """Log security-related events"""
        await self.logger.info(
            f"Security event: {event_type}",
            {
                "event_type": event_type,
                "user_id": user_id,
                "guild_id": guild_id,
                **details,
            },
        )

    async def hash_sensitive_data(self, data: str) -> str:
        """Hash sensitive data for secure storage"""
        salt = "quranbot_security_salt"  # In production, use random salt from env
        return hashlib.sha256((data + salt).encode()).hexdigest()

    async def validate_discord_token(self, token: str) -> bool:
        """Validate Discord bot token format"""
        if not isinstance(token, str):
            return False

        # Remove common prefixes
        clean_token = token
        for prefix in ["Bot ", "Bearer "]:
            if clean_token.startswith(prefix):
                clean_token = clean_token[len(prefix) :]

        # Discord bot tokens are typically 59+ characters
        if len(clean_token) < 50:
            return False

        # Check basic format (letters, numbers, dots, underscores, dashes)
        if not re.match(r"^[A-Za-z0-9._-]+$", clean_token):
            return False

        return True

    async def sanitize_for_logging(self, data: Any) -> Any:
        """Sanitize data for safe logging (remove sensitive information)"""
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if any(
                    sensitive in key.lower()
                    for sensitive in ["token", "password", "secret", "key"]
                ):
                    sanitized[key] = "[REDACTED]"
                else:
                    sanitized[key] = await self.sanitize_for_logging(value)
            return sanitized
        elif isinstance(data, list):
            return [await self.sanitize_for_logging(item) for item in data]
        elif isinstance(data, str) and len(data) > 50:
            # Potentially sensitive long strings
            return f"[STRING:{len(data)} chars]"
        else:
            return data


# =============================================================================
# Security Decorators
# =============================================================================


def require_admin(func: Callable) -> Callable:
    """Decorator to require admin privileges for command execution"""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract interaction from arguments
        interaction = None
        for arg in args:
            if isinstance(arg, discord.Interaction):
                interaction = arg
                break

        if not interaction:
            return await func(*args, **kwargs)

        # Get security service
        from .di_container import DIContainer

        try:
            container = DIContainer.get_instance()
            security_service = container.get(SecurityService)
        except:
            # If no security service, proceed (development mode)
            return await func(*args, **kwargs)

        try:
            has_permission = await security_service.check_command_permission(
                user_id=interaction.user.id,
                guild_id=interaction.guild.id if interaction.guild else None,
                command_name=func.__name__,
                require_admin=True,
            )

            if not has_permission:
                embed = discord.Embed(
                    title="🔒 Access Denied",
                    description="This command is only available to bot administrators.",
                    color=0xFF6B6B,
                )
                embed.set_footer(
                    text="Contact the bot administrator if you believe this is an error"
                )

                try:
                    if interaction.response.is_done():
                        await interaction.followup.send(embed=embed, ephemeral=True)
                    else:
                        await interaction.response.send_message(
                            embed=embed, ephemeral=True
                        )
                except:
                    pass

                return None

            return await func(*args, **kwargs)

        except SecurityError as e:
            embed = discord.Embed(
                title="🚫 Security Error", description=str(e), color=0xFF6B6B
            )

            try:
                if interaction.response.is_done():
                    await interaction.followup.send(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                pass

            return None

    return wrapper


def validate_input(**validation_params):
    """
    Decorator to validate command inputs.

    Args:
        **validation_params: Validation parameters for specific arguments
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # Validate kwargs based on validation_params
                for param_name, validation_config in validation_params.items():
                    if param_name in kwargs:
                        value = kwargs[param_name]

                        if validation_config.get("type") == "surah":
                            kwargs[param_name] = InputValidator.validate_surah_number(
                                value
                            )
                        elif validation_config.get("type") == "ayah":
                            surah = kwargs.get("surah", 1)
                            kwargs[param_name] = InputValidator.validate_ayah_number(
                                value, surah
                            )
                        elif validation_config.get("type") == "string":
                            kwargs[param_name] = InputValidator.sanitize_string(
                                value,
                                max_length=validation_config.get("max_length", 2000),
                                allow_newlines=validation_config.get(
                                    "allow_newlines", True
                                ),
                                allow_mentions=validation_config.get(
                                    "allow_mentions", False
                                ),
                                allow_links=validation_config.get("allow_links", False),
                            )
                        elif validation_config.get("type") == "time_interval":
                            kwargs[param_name] = InputValidator.validate_time_interval(
                                value
                            )

                return await func(*args, **kwargs)

            except ValidationError as e:
                # Extract interaction from arguments
                interaction = None
                for arg in args:
                    if isinstance(arg, discord.Interaction):
                        interaction = arg
                        break

                if interaction:
                    embed = discord.Embed(
                        title="❌ Invalid Input", description=str(e), color=0xFF6B6B
                    )
                    embed.set_footer(text="Please check your input and try again")

                    try:
                        if interaction.response.is_done():
                            await interaction.followup.send(embed=embed, ephemeral=True)
                        else:
                            await interaction.response.send_message(
                                embed=embed, ephemeral=True
                            )
                    except:
                        pass

                return None

        return wrapper

    return decorator
