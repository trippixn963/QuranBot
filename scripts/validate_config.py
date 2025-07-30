#!/usr/bin/env python3
"""
Configuration Validation Script for QuranBot

Validates configuration files for completeness, security, and correctness.
Ensures all required settings are present and properly formatted.

"And it is He who created all things in due proportion." - Quran 25:2
"""

from pathlib import Path
import re
import sys
import tomllib
from typing import Any

# Required configuration keys for different environments
REQUIRED_CONFIG_KEYS = {
    "development": {
        "DISCORD_TOKEN",
        "GUILD_ID",
        "TARGET_CHANNEL_ID",
        "ADMIN_USER_ID",
        "AUDIO_FOLDER",
        "FFMPEG_PATH",
    },
    "production": {
        "DISCORD_TOKEN",
        "GUILD_ID",
        "TARGET_CHANNEL_ID",
        "PANEL_CHANNEL_ID",
        "LOGS_CHANNEL_ID",
        "ADMIN_USER_ID",
        "DEVELOPER_ID",
        "AUDIO_FOLDER",
        "FFMPEG_PATH",
        "USE_WEBHOOK_LOGGING",
        "DISCORD_WEBHOOK_URL",
        "RATE_LIMIT_PER_MINUTE",
        "LOG_LEVEL",
    },
}

# Optional configuration keys with defaults
OPTIONAL_CONFIG_KEYS = {
    "DAILY_VERSE_CHANNEL_ID": "Daily verse channel ID",
    "OPENAI_API_KEY": "OpenAI API key for AI features",
    "DEFAULT_RECITER": "Default Quranic reciter",
    "DEFAULT_VOLUME": "Default audio volume",
    "CACHE_TTL": "Cache time-to-live in seconds",
    "BACKUP_INTERVAL_HOURS": "Backup interval in hours",
    "ENVIRONMENT": "Environment (development/production)",
    "TIMEZONE": "Bot timezone",
}

# Security-sensitive keys that should never be hardcoded
SENSITIVE_KEYS = {
    "DISCORD_TOKEN",
    "OPENAI_API_KEY",
    "DISCORD_WEBHOOK_URL",
    "DATABASE_URL",
    "REDIS_URL",
    "SECRET_KEY",
}

# Pattern validators for specific config values
VALIDATORS = {
    "DISCORD_TOKEN": re.compile(
        r"^[A-Za-z0-9_-]{24}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{27}$|^Bot [A-Za-z0-9_-]{24}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{27}$"
    ),
    "GUILD_ID": re.compile(r"^\d{17,19}$"),
    "TARGET_CHANNEL_ID": re.compile(r"^\d{17,19}$"),
    "PANEL_CHANNEL_ID": re.compile(r"^\d{17,19}$"),
    "LOGS_CHANNEL_ID": re.compile(r"^\d{17,19}$"),
    "DAILY_VERSE_CHANNEL_ID": re.compile(r"^\d{17,19}$"),
    "ADMIN_USER_ID": re.compile(r"^\d{17,19}$"),
    "DEVELOPER_ID": re.compile(r"^\d{17,19}$"),
    "DISCORD_WEBHOOK_URL": re.compile(
        r"^https://discord\.com/api/webhooks/\d+/[A-Za-z0-9_-]+$"
    ),
    "LOG_LEVEL": re.compile(r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$"),
    "ENVIRONMENT": re.compile(r"^(development|staging|production)$"),
    "USE_WEBHOOK_LOGGING": re.compile(r"^(true|false|True|False|1|0)$"),
    "RATE_LIMIT_PER_MINUTE": re.compile(r"^\d+$"),
    "DEFAULT_VOLUME": re.compile(r"^(0(\.\d+)?|1(\.0+)?)$"),  # 0.0 to 1.0
    "CACHE_TTL": re.compile(r"^\d+$"),
    "BACKUP_INTERVAL_HOURS": re.compile(r"^\d+$"),
}


class ConfigValidator:
    """Validates QuranBot configuration files."""

    def __init__(self):
        self.errors: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []
        self.validated_files: set[Path] = set()

    def validate_file(self, file_path: Path) -> bool:
        """Validate a configuration file."""
        try:
            if file_path.suffix == ".env":
                return self._validate_env_file(file_path)
            elif file_path.suffix == ".toml":
                return self._validate_toml_file(file_path)
            elif file_path.suffix == ".py" and "config" in file_path.name:
                return self._validate_python_config(file_path)
            else:
                self._add_warning(file_path, "Unknown configuration file type")
                return True

        except Exception as e:
            self._add_error(file_path, f"Configuration validation error: {e}")
            return False

    def _validate_env_file(self, file_path: Path) -> bool:
        """Validate .env configuration file."""
        try:
            config = {}
            with open(file_path, encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        if "=" in line:
                            key, value = line.split("=", 1)
                            config[key.strip()] = value.strip()
                        else:
                            self._add_warning(
                                file_path,
                                f"Line {line_num}: Invalid format, expected KEY=VALUE",
                            )

            return self._validate_config_dict(file_path, config)

        except UnicodeDecodeError as e:
            self._add_error(file_path, f"Encoding error: {e}")
            return False

    def _validate_toml_file(self, file_path: Path) -> bool:
        """Validate TOML configuration file."""
        try:
            with open(file_path, "rb") as f:
                config_data = tomllib.load(f)

            # Extract bot configuration section if it exists
            if "tool" in config_data and "quranbot" in config_data["tool"]:
                config = config_data["tool"]["quranbot"]
            elif "quranbot" in config_data:
                config = config_data["quranbot"]
            else:
                # For pyproject.toml, check poetry section too
                if "tool" in config_data and "poetry" in config_data["tool"]:
                    poetry_config = config_data["tool"]["poetry"]
                    if poetry_config.get("name") == "quranbot":
                        return True  # Valid poetry config

                self._add_warning(file_path, "No QuranBot configuration section found")
                return True

            return self._validate_config_dict(file_path, config)

        except tomllib.TOMLDecodeError as e:
            self._add_error(file_path, f"Invalid TOML: {e}")
            return False

    def _validate_python_config(self, file_path: Path) -> bool:
        """Validate Python configuration file."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Check for hardcoded secrets
            for sensitive_key in SENSITIVE_KEYS:
                if (
                    f'{sensitive_key} = "' in content
                    or f"{sensitive_key} = '" in content
                ):
                    self._add_error(
                        file_path,
                        f"Hardcoded sensitive value detected: {sensitive_key}",
                    )

            # Check for proper environment variable usage
            if "os.getenv" not in content and "os.environ" not in content:
                self._add_warning(
                    file_path, "Configuration should use environment variables"
                )

            return len(self.errors) == 0

        except UnicodeDecodeError as e:
            self._add_error(file_path, f"Encoding error: {e}")
            return False

    def _validate_config_dict(self, file_path: Path, config: dict[str, Any]) -> bool:
        """Validate configuration dictionary."""
        valid = True

        # Determine environment
        environment = config.get("ENVIRONMENT", "development").lower()
        if environment not in REQUIRED_CONFIG_KEYS:
            environment = "development"

        # Check required keys
        required_keys = REQUIRED_CONFIG_KEYS[environment]
        missing_keys = required_keys - set(config.keys())

        if missing_keys:
            self._add_error(
                file_path,
                f"Missing required configuration keys for {environment}: {sorted(missing_keys)}",
            )
            valid = False

        # Validate individual config values
        for key, value in config.items():
            if not self._validate_config_value(file_path, key, value):
                valid = False

        # Check for security issues
        if not self._validate_security(file_path, config):
            valid = False

        # Check for Islamic content configuration
        if not self._validate_islamic_config(file_path, config):
            # This is warning-level, doesn't fail validation
            pass

        return valid

    def _validate_config_value(self, file_path: Path, key: str, value: Any) -> bool:
        """Validate individual configuration value."""
        valid = True

        # Skip validation for empty values
        if not value:
            return True

        # Convert to string for pattern matching
        str_value = str(value).strip()

        # Check if value looks like a placeholder
        if str_value.startswith("YOUR_") or str_value in [
            "your_token_here",
            "your_key_here",
        ]:
            self._add_warning(
                file_path, f"{key} appears to be a placeholder value: {str_value}"
            )
            return True

        # Validate using specific patterns
        if key in VALIDATORS:
            if not VALIDATORS[key].match(str_value):
                self._add_error(file_path, f"Invalid format for {key}: {str_value}")
                valid = False

        # Additional validations
        if key == "FFMPEG_PATH":
            if not self._validate_ffmpeg_path(file_path, str_value):
                valid = False
        elif key == "AUDIO_FOLDER":
            if not self._validate_audio_folder(file_path, str_value):
                valid = False
        elif key.endswith("_CHANNEL_ID") or key.endswith("_USER_ID"):
            if not self._validate_discord_id(file_path, key, str_value):
                valid = False

        return valid

    def _validate_ffmpeg_path(self, file_path: Path, ffmpeg_path: str) -> bool:
        """Validate FFmpeg path."""
        if not ffmpeg_path:
            return True

        path = Path(ffmpeg_path)
        if not path.exists():
            self._add_warning(file_path, f"FFmpeg path does not exist: {ffmpeg_path}")
        elif not path.is_file():
            self._add_error(file_path, f"FFmpeg path is not a file: {ffmpeg_path}")
            return False

        return True

    def _validate_audio_folder(self, file_path: Path, audio_folder: str) -> bool:
        """Validate audio folder path."""
        if not audio_folder:
            return True

        path = Path(audio_folder)
        if not path.exists():
            self._add_warning(file_path, f"Audio folder does not exist: {audio_folder}")
        elif not path.is_dir():
            self._add_error(
                file_path, f"Audio folder is not a directory: {audio_folder}"
            )
            return False

        return True

    def _validate_discord_id(self, file_path: Path, key: str, discord_id: str) -> bool:
        """Validate Discord ID format."""
        if not discord_id.isdigit():
            self._add_error(
                file_path, f"{key} must be a numeric Discord ID: {discord_id}"
            )
            return False

        if len(discord_id) < 17 or len(discord_id) > 19:
            self._add_error(
                file_path,
                f"{key} has invalid length (should be 17-19 digits): {discord_id}",
            )
            return False

        return True

    def _validate_security(self, file_path: Path, config: dict[str, Any]) -> bool:
        """Validate security aspects of configuration."""
        valid = True

        # Check for weak or default tokens
        discord_token = config.get("DISCORD_TOKEN", "")
        if discord_token:
            if len(discord_token) < 50:
                self._add_warning(
                    file_path, "Discord token appears to be too short or invalid"
                )
            elif discord_token in ["your_token_here", "test_token"]:
                self._add_error(file_path, "Discord token is set to default/test value")
                valid = False

        # Check webhook URL security
        webhook_url = config.get("DISCORD_WEBHOOK_URL", "")
        if webhook_url and not webhook_url.startswith("https://"):
            self._add_error(file_path, "Discord webhook URL must use HTTPS")
            valid = False

        # Check rate limiting
        rate_limit = config.get("RATE_LIMIT_PER_MINUTE")
        if rate_limit and int(rate_limit) > 100:
            self._add_warning(
                file_path, f"Rate limit seems high: {rate_limit} requests/minute"
            )

        return valid

    def _validate_islamic_config(self, file_path: Path, config: dict[str, Any]) -> bool:
        """Validate Islamic-specific configuration."""
        valid = True

        # Check for default reciter
        reciter = config.get("DEFAULT_RECITER", "")
        if reciter:
            known_reciters = [
                "Abdul Basit Abdul Samad",
                "Saad Al Ghamdi",
                "Mishary Rashid",
                "Maher Al Muaiqly",
                "Abdul Rahman As-Sudais",
                "Yasser Al Dosari",
            ]
            if reciter not in known_reciters:
                self._add_warning(
                    file_path, f"Unknown reciter: {reciter}. Please verify spelling."
                )

        # Check timezone for prayer times
        timezone = config.get("TIMEZONE", "")
        if not timezone:
            self._add_warning(
                file_path, "TIMEZONE not set. This may affect prayer time calculations."
            )

        return valid

    def _add_error(self, file_path: Path, message: str, details: dict | None = None):
        """Add a validation error."""
        self.errors.append(
            {
                "file": str(file_path),
                "message": message,
                "details": details or {},
                "type": "error",
            }
        )

    def _add_warning(self, file_path: Path, message: str, details: dict | None = None):
        """Add a validation warning."""
        self.warnings.append(
            {
                "file": str(file_path),
                "message": message,
                "details": details or {},
                "type": "warning",
            }
        )

    def get_report(self) -> dict[str, Any]:
        """Get validation report."""
        return {
            "files_validated": len(self.validated_files),
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "error_details": self.errors,
            "warning_details": self.warnings,
            "status": "PASS" if len(self.errors) == 0 else "FAIL",
        }


def main():
    """Main validation function."""
    if len(sys.argv) < 2:
        print("Usage: python validate_config.py <config_file1> [config_file2] ...")
        sys.exit(1)

    validator = ConfigValidator()
    all_valid = True

    for file_arg in sys.argv[1:]:
        file_path = Path(file_arg)
        if file_path.exists():
            valid = validator.validate_file(file_path)
            validator.validated_files.add(file_path)
            all_valid &= valid
        else:
            validator._add_error(file_path, "File not found")
            all_valid = False

    # Generate report
    report = validator.get_report()

    # Print summary
    print("\n⚙️  Configuration Validation Report")
    print(f"{'='*50}")
    print(f"Files validated: {report['files_validated']}")
    print(f"Errors: {report['errors']}")
    print(f"Warnings: {report['warnings']}")
    print(f"Status: {report['status']}")

    # Print details if there are issues
    if report["errors"] > 0:
        print("\n❌ Errors:")
        for error in report["error_details"]:
            print(f"  {error['file']}: {error['message']}")

    if report["warnings"] > 0:
        print("\n⚠️  Warnings:")
        for warning in report["warning_details"]:
            print(f"  {warning['file']}: {warning['message']}")

    if all_valid:
        print("\n✅ All configuration files are valid!")
        print("بارك الله فيك (May Allah bless you)")
    else:
        print("\n❌ Configuration validation failed!")
        print("Please review and correct the issues above.")

    sys.exit(0 if all_valid else 1)


if __name__ == "__main__":
    main()
