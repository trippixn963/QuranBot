# =============================================================================
# QuranBot - Security Validators
# =============================================================================
# Secure input validation utilities to prevent injection attacks and
# ensure data integrity throughout the application.
# =============================================================================

import ipaddress
import re
from re import Pattern
from urllib.parse import urlparse


class SecurityError(Exception):
    """Custom security-related exception."""

    pass


class SecureValidator:
    """Secure input validation utilities."""

    # Compile regex patterns once for performance
    DISCORD_TOKEN_PATTERN: Pattern = re.compile(r"^[A-Za-z0-9._-]{59,}$")
    USER_ID_PATTERN: Pattern = re.compile(r"^\d{17,19}$")
    GUILD_ID_PATTERN: Pattern = re.compile(r"^\d{17,19}$")
    CHANNEL_ID_PATTERN: Pattern = re.compile(r"^\d{17,19}$")
    WEBHOOK_PATTERN: Pattern = re.compile(
        r"^https://discord\.com/api/webhooks/\d{17,19}/[A-Za-z0-9_-]{68}$"
    )
    OPENAI_KEY_PATTERN: Pattern = re.compile(r"^sk-[A-Za-z0-9]{48}$")

    # Dangerous characters and patterns
    DANGEROUS_CHARS = {"<", ">", '"', "'", "&", "\x00", "\n", "\r", "\t"}
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
        r"(--|#|/\*|\*/)",
        r"(\bOR\b.*=.*\bOR\b)",
        r"(\bAND\b.*=.*\bAND\b)",
    ]

    @classmethod
    def validate_discord_token(cls, token: str) -> str:
        """Securely validate Discord bot token format."""
        if not token:
            raise SecurityError("Discord token is required")

        # Remove common prefixes
        clean_token = token
        if token.startswith(("Bot ", "Bearer ")):
            clean_token = token.split(" ", 1)[1]

        # Check for dangerous characters
        if any(char in clean_token for char in cls.DANGEROUS_CHARS):
            raise SecurityError("Discord token contains invalid characters")

        # Validate format
        if not cls.DISCORD_TOKEN_PATTERN.match(clean_token):
            raise SecurityError("Invalid Discord token format")

        # Validate length (Discord tokens are typically 59+ chars)
        if len(clean_token) < 59:
            raise SecurityError("Discord token too short")

        return token

    @classmethod
    def validate_user_id(cls, user_id: str | int) -> int:
        """Securely validate Discord user ID."""
        user_id_str = str(user_id)

        if not cls.USER_ID_PATTERN.match(user_id_str):
            raise SecurityError("Invalid Discord user ID format")

        try:
            uid = int(user_id_str)
            # Discord snowflakes are 64-bit integers with specific range
            if not (4194304 <= uid < 2**63):  # Minimum Discord snowflake
                raise SecurityError("User ID out of valid range")
            return uid
        except ValueError:
            raise SecurityError("Invalid user ID format")

    @classmethod
    def validate_guild_id(cls, guild_id: str | int) -> int:
        """Securely validate Discord guild ID."""
        guild_id_str = str(guild_id)

        if not cls.GUILD_ID_PATTERN.match(guild_id_str):
            raise SecurityError("Invalid Discord guild ID format")

        try:
            gid = int(guild_id_str)
            if not (4194304 <= gid < 2**63):
                raise SecurityError("Guild ID out of valid range")
            return gid
        except ValueError:
            raise SecurityError("Invalid guild ID format")

    @classmethod
    def validate_channel_id(cls, channel_id: str | int) -> int:
        """Securely validate Discord channel ID."""
        channel_id_str = str(channel_id)

        if not cls.CHANNEL_ID_PATTERN.match(channel_id_str):
            raise SecurityError("Invalid Discord channel ID format")

        try:
            cid = int(channel_id_str)
            if not (4194304 <= cid < 2**63):
                raise SecurityError("Channel ID out of valid range")
            return cid
        except ValueError:
            raise SecurityError("Invalid channel ID format")

    @classmethod
    def validate_webhook_url(cls, url: str) -> str:
        """Securely validate Discord webhook URL."""
        if not url:
            raise SecurityError("Webhook URL is required")

        # Must use HTTPS
        if not url.startswith("https://"):
            raise SecurityError("Webhook URLs must use HTTPS")

        # Must be Discord webhook
        if not url.startswith("https://discord.com/api/webhooks/"):
            raise SecurityError("Invalid Discord webhook URL")

        # Validate full format
        if not cls.WEBHOOK_PATTERN.match(url):
            raise SecurityError("Invalid webhook URL format")

        # Additional URL parsing validation
        try:
            parsed = urlparse(url)
            if not parsed.netloc or not parsed.path:
                raise SecurityError("Malformed webhook URL")
        except Exception:
            raise SecurityError("Invalid webhook URL structure")

        return url

    @classmethod
    def validate_openai_key(cls, api_key: str) -> str:
        """Securely validate OpenAI API key format."""
        if not api_key:
            raise SecurityError("OpenAI API key is required")

        # Check format
        if not cls.OPENAI_KEY_PATTERN.match(api_key):
            raise SecurityError("Invalid OpenAI API key format")

        return api_key

    @classmethod
    def validate_surah_number(cls, surah: str | int) -> int:
        """Validate Quran surah number."""
        try:
            surah_num = int(surah)
            if not (1 <= surah_num <= 114):
                raise SecurityError("Surah number must be between 1 and 114")
            return surah_num
        except ValueError:
            raise SecurityError("Invalid surah number format")

    @classmethod
    def validate_text_input(
        cls, text: str, max_length: int = 1000, allow_html: bool = False
    ) -> str:
        """Validate and sanitize text input."""
        if not isinstance(text, str):
            raise SecurityError("Input must be a string")

        # Check length
        if len(text) > max_length:
            raise SecurityError(f"Input too long (max {max_length} characters)")

        # Check for dangerous characters
        if not allow_html:
            if any(char in text for char in cls.DANGEROUS_CHARS):
                raise SecurityError("Input contains dangerous characters")

        # Check for SQL injection patterns
        text_upper = text.upper()
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text_upper, re.IGNORECASE):
                raise SecurityError("Input contains potentially dangerous patterns")

        # Check for script injection
        script_patterns = [
            r"<script",
            r"javascript:",
            r"vbscript:",
            r"onload=",
            r"onerror=",
        ]
        for pattern in script_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                raise SecurityError("Input contains script injection patterns")

        return text.strip()

    @classmethod
    def validate_file_path(cls, path: str, allowed_extensions: list[str] = None) -> str:
        """Validate file path for security."""
        if not path:
            raise SecurityError("File path is required")

        # Check for path traversal
        if ".." in path or path.startswith("/") or ":" in path:
            raise SecurityError("Invalid file path - path traversal detected")

        # Check for null bytes
        if "\x00" in path:
            raise SecurityError("Null byte in file path")

        # Validate extension if specified
        if allowed_extensions:
            path_lower = path.lower()
            if not any(path_lower.endswith(ext.lower()) for ext in allowed_extensions):
                raise SecurityError(
                    f"File extension not allowed. Allowed: {allowed_extensions}"
                )

        return path

    @classmethod
    def validate_ip_address(cls, ip: str) -> str:
        """Validate IP address format."""
        try:
            # This will raise ValueError for invalid IPs
            ipaddress.ip_address(ip)
            return ip
        except ValueError:
            raise SecurityError("Invalid IP address format")

    @classmethod
    def sanitize_log_data(cls, data: dict) -> dict:
        """Sanitize data for safe logging."""
        sensitive_keys = {
            "token",
            "password",
            "secret",
            "key",
            "auth",
            "api_key",
            "discord_token",
            "openai_api_key",
            "webhook_url",
            "private",
        }

        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()

            # Redact sensitive keys
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            # Truncate long strings
            elif isinstance(value, str) and len(value) > 200:
                sanitized[key] = value[:200] + "...[TRUNCATED]"
            # Recursively sanitize nested dicts
            elif isinstance(value, dict):
                sanitized[key] = cls.sanitize_log_data(value)
            # Keep other values as-is
            else:
                sanitized[key] = value

        return sanitized

    @classmethod
    def validate_admin_user_ids(cls, user_ids_str: str) -> list[int]:
        """Validate comma-separated admin user IDs."""
        if not user_ids_str.strip():
            return []

        user_ids = []
        for uid_str in user_ids_str.split(","):
            uid_str = uid_str.strip()
            if uid_str:
                user_ids.append(cls.validate_user_id(uid_str))

        # Check for duplicates
        if len(user_ids) != len(set(user_ids)):
            raise SecurityError("Duplicate user IDs found")

        # Reasonable limit on admin users
        if len(user_ids) > 50:
            raise SecurityError("Too many admin users (max 50)")

        return user_ids
