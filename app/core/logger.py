# =============================================================================
# QuranBot - Tree Logger with Long-Term Management
# =============================================================================
# Ultimate logging system designed for single-server 24/7 Discord bot operation.
# Features beautiful tree-style console output with automatic file management,
# compression, retention, performance tracking, and service-specific logging.
#
# Structure: logs/YYYY-MM-DD/1AM/[log.log, log.json, error.log, performance.json, debug.log]
# Auto-compression after 7 days, auto-deletion after 30 days, correlation tracking.
# =============================================================================

from datetime import datetime, timedelta
import json
import logging
import os
from pathlib import Path
import shutil
import sys
import threading
import time
from typing import Any
import uuid

# Import centralized timezone configuration
from ..config.timezone import APP_TIMEZONE

# =============================================================================
# Configuration Constants
# =============================================================================


DEFAULT_RETENTION_DAYS = 30
DEFAULT_COMPRESSION_DAYS = 7
DEFAULT_LOG_LEVEL = "INFO"

# Performance thresholds for warnings
PERFORMANCE_THRESHOLDS = {
    "slow_operation_ms": 1000,  # Warn if operation takes > 1s
    "memory_usage_mb": 512,  # Warn if memory usage > 512MB
    "disk_usage_percent": 85,  # Warn if disk usage > 85%
    "error_rate_per_hour": 10,  # Warn if > 10 errors per hour
}

# =============================================================================
# JSON Encoder for Complex Objects
# =============================================================================


class JSONEncoder(json.JSONEncoder):
    """JSON encoder for logging complex objects."""

    def default(self, obj):
        """Convert complex objects to JSON-serializable format."""
        if isinstance(obj, Path):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Exception):
            return {"type": type(obj).__name__, "message": str(obj), "args": obj.args}
        elif hasattr(obj, "value"):  # Handle enums
            return obj.value
        elif hasattr(obj, "__class__") and hasattr(obj.__class__, "__bases__"):
            # Check if it's an enum
            for base in obj.__class__.__bases__:
                if base.__name__ == "Enum":
                    return obj.value
        elif hasattr(obj, "__dict__"):
            return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
        elif hasattr(obj, "__iter__") and not isinstance(obj, (str, bytes, bytearray)):
            try:
                return list(obj)
            except TypeError:
                return str(obj)
        else:
            return str(obj)


# =============================================================================
# Log Retention and Compression Manager
# =============================================================================


class LogRetentionManager:
    """Manages log file retention, compression, and cleanup."""

    def __init__(
        self,
        base_log_folder: Path,
        retention_days: int = DEFAULT_RETENTION_DAYS,
        compression_days: int = DEFAULT_COMPRESSION_DAYS,
    ):
        self.base_log_folder = base_log_folder
        self.retention_days = retention_days
        self.compression_days = compression_days
        self.retention_file = base_log_folder / "retention.json"
        self._lock = threading.Lock()

    def cleanup_old_logs(self) -> dict[str, Any]:
        """Clean up old logs with compression and deletion."""
        with self._lock:
            cleanup_stats = {
                "compressed_folders": 0,
                "deleted_files": 0,
                "freed_bytes": 0,
                "errors": [],
            }

            try:
                now = datetime.now(APP_TIMEZONE)
                cutoff_delete = now - timedelta(days=self.retention_days)
                cutoff_compress = now - timedelta(days=self.compression_days)

                # Process each date folder
                for date_folder in self.base_log_folder.iterdir():
                    if not date_folder.is_dir() or not self._is_date_folder(
                        date_folder.name
                    ):
                        continue

                    try:
                        folder_date = datetime.strptime(date_folder.name, "%Y-%m-%d")
                        folder_date = folder_date.replace(tzinfo=APP_TIMEZONE)

                        # Delete old folders
                        if folder_date < cutoff_delete:
                            folder_size = self._get_folder_size(date_folder)
                            shutil.rmtree(date_folder)
                            cleanup_stats["deleted_files"] += 1
                            cleanup_stats["freed_bytes"] += folder_size

                        # Compress folders older than compression days but newer than deletion
                        elif folder_date < cutoff_compress:
                            zip_file = date_folder.with_suffix(".zip")
                            if not zip_file.exists():
                                original_size = self._get_folder_size(date_folder)
                                shutil.make_archive(
                                    str(date_folder), "zip", date_folder
                                )
                                shutil.rmtree(date_folder)
                                compressed_size = zip_file.stat().st_size
                                cleanup_stats["compressed_folders"] += 1
                                cleanup_stats["freed_bytes"] += (
                                    original_size - compressed_size
                                )

                    except Exception as e:
                        cleanup_stats["errors"].append(
                            f"Error processing {date_folder.name}: {e}"
                        )

                # Update retention metadata
                self._update_retention_metadata(cleanup_stats)

            except Exception as e:
                cleanup_stats["errors"].append(f"General cleanup error: {e}")

            return cleanup_stats

    def _is_date_folder(self, folder_name: str) -> bool:
        """Check if folder name is a valid date format."""
        try:
            datetime.strptime(folder_name, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def _get_folder_size(self, folder: Path) -> int:
        """Get total size of folder in bytes."""
        total_size = 0
        try:
            for file_path in folder.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception:
            pass
        return total_size

    def _update_retention_metadata(self, cleanup_stats: dict[str, Any]) -> None:
        """Update retention metadata file."""
        try:
            metadata = {
                "last_cleanup": datetime.now(APP_TIMEZONE).isoformat(),
                "retention_days": self.retention_days,
                "compression_days": self.compression_days,
                "last_cleanup_stats": cleanup_stats,
            }

            with open(self.retention_file, "w") as f:
                json.dump(metadata, f, indent=2, cls=JSONEncoder)

        except Exception as e:
            cleanup_stats["errors"].append(f"Failed to update retention metadata: {e}")


# =============================================================================
# Performance Metrics Tracker
# =============================================================================


class PerformanceTracker:
    """Tracks performance metrics for logging and monitoring."""

    def __init__(self):
        self.metrics = {
            "operations": [],
            "errors_per_hour": {},
            "service_health": {},
            "system_metrics": {},
        }
        self._lock = threading.Lock()

    def track_operation(
        self,
        operation: str,
        duration_ms: float,
        success: bool = True,
        service: str = "system",
        context: dict[str, Any] | None = None,
    ) -> None:
        """Track operation performance."""
        with self._lock:
            metric = {
                "timestamp": datetime.now(APP_TIMEZONE).isoformat(),
                "operation": operation,
                "service": service,
                "duration_ms": duration_ms,
                "success": success,
                "context": context or {},
            }

            self.metrics["operations"].append(metric)

            # Keep only last 1000 operations to prevent memory growth
            if len(self.metrics["operations"]) > 1000:
                self.metrics["operations"] = self.metrics["operations"][-1000:]

    def track_error(self, service: str = "system") -> None:
        """Track error occurrence by hour."""
        with self._lock:
            now = datetime.now(APP_TIMEZONE)
            hour_key = now.strftime("%Y-%m-%d_%H")

            if hour_key not in self.metrics["errors_per_hour"]:
                self.metrics["errors_per_hour"][hour_key] = 0

            self.metrics["errors_per_hour"][hour_key] += 1

            # Clean old error tracking (keep only last 48 hours)
            cutoff = now - timedelta(hours=48)
            self.metrics["errors_per_hour"] = {
                k: v
                for k, v in self.metrics["errors_per_hour"].items()
                if datetime.strptime(k, "%Y-%m-%d_%H").replace(tzinfo=APP_TIMEZONE)
                > cutoff
            }

    def update_service_health(self, service: str, health_data: dict[str, Any]) -> None:
        """Update service health metrics."""
        with self._lock:
            self.metrics["service_health"][service] = {
                "timestamp": datetime.now(APP_TIMEZONE).isoformat(),
                **health_data,
            }

    def get_performance_summary(self) -> dict[str, Any]:
        """Get performance summary for logging."""
        with self._lock:
            now = datetime.now(APP_TIMEZONE)
            recent_ops = [
                op
                for op in self.metrics["operations"]
                if datetime.fromisoformat(op["timestamp"]) > now - timedelta(minutes=5)
            ]

            successful_ops = [op for op in recent_ops if op["success"]]
            failed_ops = [op for op in recent_ops if not op["success"]]

            current_hour = now.strftime("%Y-%m-%d_%H")
            errors_this_hour = self.metrics["errors_per_hour"].get(current_hour, 0)

            avg_duration = 0
            if successful_ops:
                avg_duration = sum(op["duration_ms"] for op in successful_ops) / len(
                    successful_ops
                )

            return {
                "recent_operations_count": len(recent_ops),
                "successful_operations": len(successful_ops),
                "failed_operations": len(failed_ops),
                "average_duration_ms": round(avg_duration, 2),
                "errors_this_hour": errors_this_hour,
                "service_health_count": len(self.metrics["service_health"]),
                "performance_warnings": self._check_performance_warnings(
                    avg_duration, errors_this_hour
                ),
            }

    def _check_performance_warnings(
        self, avg_duration: float, errors_this_hour: int
    ) -> list[str]:
        """Check for performance warnings."""
        warnings = []

        if avg_duration > PERFORMANCE_THRESHOLDS["slow_operation_ms"]:
            warnings.append(f"Slow operations detected: {avg_duration:.1f}ms average")

        if errors_this_hour > PERFORMANCE_THRESHOLDS["error_rate_per_hour"]:
            warnings.append(f"High error rate: {errors_this_hour} errors this hour")

        return warnings


# =============================================================================
# File Handler Manager
# =============================================================================


class LogFileManager:
    """file manager with multiple output formats and performance tracking."""

    def __init__(
        self,
        base_log_folder: Path = Path("logs"),
        retention_days: int = DEFAULT_RETENTION_DAYS,
        compression_days: int = DEFAULT_COMPRESSION_DAYS,
    ):
        self.base_log_folder = base_log_folder
        self.retention_manager = LogRetentionManager(
            base_log_folder, retention_days, compression_days
        )
        self.performance_tracker = PerformanceTracker()

        # Current handlers
        self.current_date = None
        self.current_hour = None
        self.handlers = {}

        # Clean up existing logs before initializing
        self._cleanup_existing_logs()

        # Initialize handlers
        self._setup_handlers()

        # Schedule cleanup task
        self._last_cleanup = datetime.now(APP_TIMEZONE)

    def _cleanup_existing_logs(self) -> None:
        """
        Clean up ALL existing logs on startup for completely fresh logging.

        This ensures fresh logs every time the bot starts, deleting ALL
        previous log files and folders (including current day) to start
        with a completely clean slate.
        """
        try:
            print(f"🧹 Starting log cleanup in: {self.base_log_folder}")

            if not self.base_log_folder.exists():
                print("📁 Log folder doesn't exist, nothing to clean")
                return

            # Track cleanup statistics
            cleanup_stats = {
                "deleted_folders": 0,
                "deleted_files": 0,
                "freed_bytes": 0,
                "errors": [],
            }

            # Delete ALL log folders for completely fresh start
            for item in self.base_log_folder.iterdir():
                if not item.is_dir():
                    # Skip non-directory items (like .DS_Store)
                    continue

                # Check if this is a date folder (YYYY-MM-DD format)
                if not self._is_date_folder(item.name):
                    continue

                print(f"🗑️  Deleting log folder: {item.name}")

                # Delete the entire date folder and all its contents
                try:
                    # Count files before deleting
                    file_count = 0
                    for root, dirs, files in os.walk(str(item)):
                        file_count += len(files)

                    folder_size = self._get_folder_size(item)
                    shutil.rmtree(item)

                    cleanup_stats["deleted_folders"] += 1
                    cleanup_stats["deleted_files"] += file_count
                    cleanup_stats["freed_bytes"] += folder_size

                    print(f"✅ Deleted folder: {item.name} ({file_count} files)")

                except Exception as e:
                    error_msg = f"Failed to delete {item}: {e}"
                    cleanup_stats["errors"].append(error_msg)
                    print(f"❌ {error_msg}")

            # Log the cleanup results
            if cleanup_stats["deleted_folders"] > 0:
                print(
                    f"🧹 Cleaned up {cleanup_stats['deleted_folders']} log folders "
                    f"({cleanup_stats['deleted_files']} files, "
                    f"{cleanup_stats['freed_bytes'] / 1024 / 1024:.2f} MB freed)"
                )

                if cleanup_stats["errors"]:
                    print(f"⚠️  Cleanup errors: {len(cleanup_stats['errors'])}")
            else:
                print("📁 No log folders found to clean")

        except Exception as e:
            print(f"❌ Log cleanup failed: {e}")

    def _is_date_folder(self, folder_name: str) -> bool:
        """Check if folder name matches date format (YYYY-MM-DD)."""
        try:
            # Validate date format
            datetime.strptime(folder_name, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def _get_folder_size(self, folder: Path) -> int:
        """Get total size of folder in bytes."""
        total_size = 0
        try:
            for root, dirs, files in os.walk(str(folder)):
                for file in files:
                    file_path = Path(root) / file
                    if file_path.exists():
                        total_size += file_path.stat().st_size
        except Exception:
            pass
        return total_size

    def _get_log_folder(self) -> tuple[Path, str, str]:
        """Get current log folder based on date and hour."""
        now = datetime.now(APP_TIMEZONE)
        date_str = now.strftime("%Y-%m-%d")
        hour = now.hour

        # Format hour with AM/PM
        if hour == 0:
            hour_str = "12AM"
        elif hour == 12:
            hour_str = "12PM"
        elif hour > 12:
            hour_str = f"{hour-12}PM"
        else:
            hour_str = f"{hour}AM"

        folder = self.base_log_folder / date_str / hour_str
        folder.mkdir(parents=True, exist_ok=True)

        return folder, date_str, hour_str

    def _setup_handlers(self) -> None:
        """Setup file handlers for current hour."""
        folder, date_str, hour_str = self._get_log_folder()

        # Check if we need to rotate
        if (self.current_date, self.current_hour) == (date_str, hour_str):
            return

        # Close old handlers
        for handler in self.handlers.values():
            if handler:
                handler.close()

        # Update current time
        self.current_date, self.current_hour = date_str, hour_str

        # Create new handlers
        self.handlers = {
            "log": logging.FileHandler(folder / "log.log", mode="a", encoding="utf-8"),
            "json": logging.FileHandler(
                folder / "log.json", mode="a", encoding="utf-8"
            ),
            "error": logging.FileHandler(
                folder / "error.log", mode="a", encoding="utf-8"
            ),
            "performance": logging.FileHandler(
                folder / "performance.json", mode="a", encoding="utf-8"
            ),
            "debug": logging.FileHandler(
                folder / "debug.log", mode="a", encoding="utf-8"
            ),
        }

        # Set formatter for all handlers
        formatter = logging.Formatter("%(message)s")
        for handler in self.handlers.values():
            handler.setFormatter(formatter)
            handler.setLevel(logging.DEBUG)

    def _rotate_if_needed(self) -> None:
        """Rotate handlers if hour has changed."""
        self._setup_handlers()

        # Perform cleanup if it's been more than 24 hours
        now = datetime.now(APP_TIMEZONE)
        if now.replace(tzinfo=None) - self._last_cleanup.replace(
            tzinfo=None
        ) > timedelta(hours=24):
            try:
                cleanup_stats = self.retention_manager.cleanup_old_logs()
                if (
                    cleanup_stats["compressed_folders"] > 0
                    or cleanup_stats["deleted_files"] > 0
                ):
                    self._write_to_handler(
                        "log", f"📦 Log cleanup completed: {cleanup_stats}"
                    )
                self._last_cleanup = now
            except Exception as e:
                self._write_to_handler("error", f"❌ Log cleanup failed: {e}")

    def _write_to_handler(self, handler_name: str, message: str) -> None:
        """Write message to specific handler."""
        self._rotate_if_needed()

        if handler_name in self.handlers:
            try:
                record = logging.LogRecord(
                    name="TreeLogger",
                    level=logging.INFO,
                    pathname="",
                    lineno=0,
                    msg=message,
                    args=(),
                    exc_info=None,
                )
                self.handlers[handler_name].emit(record)
            except Exception:
                pass  # Silent fail to prevent logging loops

    def write_log(
        self,
        message: str,
        level: str = "INFO",
        context: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        service: str = "system",
    ) -> None:
        """Write log message to appropriate files."""
        timestamp = datetime.now(APP_TIMEZONE).isoformat()

        # Write to human-readable log
        self._write_to_handler("log", message)

        # Sanitize context keys for JSON serialization
        sanitized_context = {}
        if context:
            for key, value in context.items():
                # Convert enum keys to strings
                if hasattr(key, "value"):
                    sanitized_key = str(key.value)
                else:
                    sanitized_key = str(key)
                sanitized_context[sanitized_key] = value

        # Write to JSON log
        json_data = {
            "timestamp": timestamp,
            "level": level.upper(),
            "message": message.split("\n")[0],  # First line only for JSON
            "service": service,
            "correlation_id": correlation_id,
            "context": sanitized_context,
        }
        self._write_to_handler("json", json.dumps(json_data, cls=JSONEncoder))

        # Write to error log if error level
        if level.upper() in ["ERROR", "CRITICAL"]:
            self._write_to_handler("error", message)
            self.performance_tracker.track_error(service)

        # Write to debug log if debug level
        if level.upper() == "DEBUG":
            self._write_to_handler("debug", message)

    def write_performance(
        self,
        operation: str,
        duration_ms: float,
        success: bool = True,
        service: str = "system",
        context: dict[str, Any] | None = None,
    ) -> None:
        """Write performance metrics."""
        self.performance_tracker.track_operation(
            operation, duration_ms, success, service, context
        )

        # Sanitize context keys for JSON serialization
        sanitized_context = {}
        if context:
            for key, value in context.items():
                # Convert enum keys to strings
                if hasattr(key, "value"):
                    sanitized_key = str(key.value)
                else:
                    sanitized_key = str(key)
                sanitized_context[sanitized_key] = value

        performance_data = {
            "timestamp": datetime.now(APP_TIMEZONE).isoformat(),
            "operation": operation,
            "service": service,
            "duration_ms": duration_ms,
            "success": success,
            "context": sanitized_context,
        }

        self._write_to_handler(
            "performance", json.dumps(performance_data, cls=JSONEncoder)
        )

    def get_performance_summary(self) -> dict[str, Any]:
        """Get current performance summary."""
        return self.performance_tracker.get_performance_summary()


# =============================================================================
# TreeLogger Class
# =============================================================================


class TreeLogger:
    """tree logger with visual formatting, service context, and performance tracking."""

    # Tree drawing characters
    TREE_BRANCH = "├─"
    TREE_LAST = "└─"
    TREE_CONTINUE = "│ "
    TREE_SPACE = "  "

    # Color codes for console output
    COLORS = {
        "INFO": "\033[36m",  # Cyan
        "SUCCESS": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[91m",  # Bright Red
        "DEBUG": "\033[35m",  # Magenta
        "PERFORMANCE": "\033[34m",  # Blue
        "RESET": "\033[0m",
    }

    # Level icons with emojis
    LEVEL_ICONS = {
        "INFO": "📍",
        "SUCCESS": "✅",
        "WARNING": "⚠️",
        "ERROR": "❌",
        "CRITICAL": "🚨",
        "DEBUG": "🔍",
        "PERFORMANCE": "📊",
        "SECTION": "📦",
        "SERVICE": "⚙️",
        "HEALTH": "💚",
    }

    # Service icons
    SERVICE_ICONS = {
        "QuranBot": "🕌",
        "AudioService": "🎵",
        "DatabaseService": "💾",
        "StateService": "📊",
        "DiscordAPI": "🤖",
        "WebhookService": "🔗",
        "system": "⚙️",
    }

    @classmethod
    def _format_timestamp(cls) -> str:
        """Format current timestamp for logging."""
        now = datetime.now(APP_TIMEZONE)
        return now.strftime("[%m/%d %I:%M:%S %p EST]")

    @classmethod
    def _get_service_icon(cls, service: str) -> str:
        """Get appropriate icon for service."""
        return cls.SERVICE_ICONS.get(service, cls.SERVICE_ICONS["system"])

    @classmethod
    def _format_value(cls, key: str, value: Any) -> str:
        """Format value for display, with special handling for timestamps."""
        # Check if this looks like a timestamp
        if isinstance(value, str) and (
            "time" in key.lower() or "timestamp" in key.lower()
        ):
            try:
                # Try to parse ISO format timestamp
                if "T" in value and (
                    "+" in value or "Z" in value or value.endswith("-04:00")
                ):
                    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                    # Convert to EST/EDT
                    est_dt = dt.astimezone(APP_TIMEZONE)
                    return est_dt.strftime("%m/%d %I:%M:%S %p EST")
            except (ValueError, TypeError):
                pass

        return str(value)

    @classmethod
    def _format_context_tree(cls, context: dict[str, Any], timestamp: str) -> list[str]:
        """Format context as tree structure."""
        lines = []
        items = list(context.items())

        for i, (key, value) in enumerate(items):
            is_last = i == len(items) - 1
            branch = cls.TREE_LAST if is_last else cls.TREE_BRANCH

            # Format value based on type
            if isinstance(value, dict):
                lines.append(f"{timestamp} {branch} {key}:")
                # Handle nested dict
                nested_items = list(value.items())
                for j, (nested_key, nested_value) in enumerate(nested_items):
                    is_nested_last = j == len(nested_items) - 1
                    nested_prefix = cls.TREE_SPACE if is_last else cls.TREE_CONTINUE
                    nested_branch = cls.TREE_LAST if is_nested_last else cls.TREE_BRANCH
                    formatted_value = cls._format_value(nested_key, nested_value)
                    lines.append(
                        f"{timestamp} {nested_prefix}{nested_branch} {nested_key}: {formatted_value}"
                    )
            else:
                formatted_value = cls._format_value(key, value)
                lines.append(f"{timestamp} {branch} {key}: {formatted_value}")

        return lines

    @classmethod
    def section(
        cls,
        title: str,
        context: dict[str, Any] | None = None,
        service: str = "system",
        correlation_id: str | None = None,
    ) -> str:
        """Log a section header with context."""
        timestamp = cls._format_timestamp()
        service_icon = cls._get_service_icon(service)
        section_icon = cls.LEVEL_ICONS["SECTION"]

        # Main section line
        main_line = f"{timestamp} {section_icon} {service_icon} {title}"
        print(main_line)
        lines = [main_line]

        # Add correlation ID if provided
        if correlation_id:
            corr_line = (
                f"{timestamp} {cls.TREE_BRANCH} correlation_id: {correlation_id}"
            )
            print(corr_line)
            lines.append(corr_line)

        # Add context if provided
        if context:
            context_lines = cls._format_context_tree(context, timestamp)
            for line in context_lines:
                print(line)
                lines.append(line)

        # Add spacing after the section (blank line)
        print("")  # Add blank line to console
        lines.append("")  # Add blank line to file output

        # Write to file
        full_message = "\n".join(lines)
        _file_manager.write_log(full_message, "INFO", context, correlation_id, service)

        return correlation_id or str(uuid.uuid4())[:8]

    @classmethod
    def info(
        cls,
        message: str,
        context: dict[str, Any] | None = None,
        service: str = "system",
        correlation_id: str | None = None,
    ) -> None:
        """Log info message."""
        cls._log_message(message, "INFO", context, service, correlation_id)

    @classmethod
    def success(
        cls,
        message: str,
        context: dict[str, Any] | None = None,
        service: str = "system",
        correlation_id: str | None = None,
    ) -> None:
        """Log success message."""
        cls._log_message(message, "SUCCESS", context, service, correlation_id)

    @classmethod
    def warning(
        cls,
        message: str,
        context: dict[str, Any] | None = None,
        service: str = "system",
        correlation_id: str | None = None,
    ) -> None:
        """Log warning message."""
        cls._log_message(message, "WARNING", context, service, correlation_id)

    @classmethod
    def error(
        cls,
        message: str,
        error: Exception | None = None,
        context: dict[str, Any] | None = None,
        service: str = "system",
        correlation_id: str | None = None,
    ) -> None:
        """Log error message with optional exception."""
        # Add error details to context
        if error:
            error_context = context.copy() if context else {}
            error_context.update(
                {
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "error_args": (
                        getattr(error, "args", ()) if hasattr(error, "args") else ()
                    ),
                }
            )
            context = error_context

        cls._log_message(message, "ERROR", context, service, correlation_id)

    @classmethod
    def critical(
        cls,
        message: str,
        error: Exception | None = None,
        context: dict[str, Any] | None = None,
        service: str = "system",
        correlation_id: str | None = None,
    ) -> None:
        """Log critical message."""
        if error:
            error_context = context.copy() if context else {}
            error_context.update(
                {
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "error_args": (
                        getattr(error, "args", ()) if hasattr(error, "args") else ()
                    ),
                }
            )
            context = error_context

        cls._log_message(message, "CRITICAL", context, service, correlation_id)

    @classmethod
    def debug(
        cls,
        message: str,
        context: dict[str, Any] | None = None,
        service: str = "system",
        correlation_id: str | None = None,
    ) -> None:
        """Log debug message."""
        cls._log_message(message, "DEBUG", context, service, correlation_id)

    @classmethod
    def performance(
        cls,
        operation: str,
        duration_ms: float,
        success: bool = True,
        context: dict[str, Any] | None = None,
        service: str = "system",
        correlation_id: str | None = None,
    ) -> None:
        """Log performance metrics."""
        perf_context = context.copy() if context else {}
        perf_context.update(
            {
                "duration_ms": duration_ms,
                "success": success,
                "slow_operation": duration_ms
                > PERFORMANCE_THRESHOLDS["slow_operation_ms"],
            }
        )

        level = (
            "WARNING"
            if duration_ms > PERFORMANCE_THRESHOLDS["slow_operation_ms"]
            else "PERFORMANCE"
        )
        message = f"Operation '{operation}' completed in {duration_ms:.1f}ms"

        cls._log_message(message, level, perf_context, service, correlation_id)
        _file_manager.write_performance(
            operation, duration_ms, success, service, context
        )

    @classmethod
    def health(
        cls,
        service_name: str,
        health_data: dict[str, Any],
        correlation_id: str | None = None,
    ) -> None:
        """Log service health status."""
        is_healthy = health_data.get("is_healthy", True)
        level = "SUCCESS" if is_healthy else "WARNING"
        message = f"Service '{service_name}' health check: {'✅ Healthy' if is_healthy else '⚠️ Unhealthy'}"

        cls._log_message(message, level, health_data, service_name, correlation_id)
        _file_manager.performance_tracker.update_service_health(
            service_name, health_data
        )

    @classmethod
    def _log_message(
        cls,
        message: str,
        level: str,
        context: dict[str, Any] | None = None,
        service: str = "system",
        correlation_id: str | None = None,
    ) -> None:
        """Internal method to log formatted message."""
        timestamp = cls._format_timestamp()
        service_icon = cls._get_service_icon(service)
        level_icon = cls.LEVEL_ICONS.get(level.upper(), cls.LEVEL_ICONS["INFO"])
        color = cls.COLORS.get(level.upper(), cls.COLORS["INFO"])
        reset = cls.COLORS["RESET"]

        # Main message line
        main_line = f"{timestamp} {color}{level_icon}{reset} {service_icon} {color}{message}{reset}"
        print(main_line)
        lines = [
            f"{timestamp} {level_icon} {service_icon} {message}"
        ]  # Clean version for file

        # Add correlation ID if provided
        if correlation_id:
            corr_line = (
                f"{timestamp} {cls.TREE_BRANCH} correlation_id: {correlation_id}"
            )
            print(corr_line)
            lines.append(corr_line)

        # Add context if provided
        if context:
            context_lines = cls._format_context_tree(context, timestamp)
            for line in context_lines:
                print(line)
                lines.append(line)

        # Add spacing after the log entry (blank line)
        print("")  # Add blank line to console
        lines.append("")  # Add blank line to file output

        # Write to file
        full_message = "\n".join(lines)
        _file_manager.write_log(full_message, level, context, correlation_id, service)


# =============================================================================
# Performance Monitoring Utilities
# =============================================================================


class PerformanceTimer:
    """Context manager for timing operations."""

    def __init__(
        self,
        operation: str,
        service: str = "system",
        correlation_id: str | None = None,
        log_result: bool = True,
    ):
        self.operation = operation
        self.service = service
        self.correlation_id = correlation_id
        self.log_result = log_result
        self.start_time = None
        self.duration_ms = 0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration_ms = (time.time() - self.start_time) * 1000
        success = exc_type is None

        if self.log_result:
            TreeLogger.performance(
                self.operation,
                self.duration_ms,
                success,
                service=self.service,
                correlation_id=self.correlation_id,
            )

        return False  # Don't suppress exceptions


# =============================================================================
# Global Instance and Convenience Functions
# =============================================================================

# Global file manager instance
_file_manager = LogFileManager()


def get_logger():
    """Get TreeLogger instance for compatibility."""
    return TreeLogger


def get_performance_summary() -> dict[str, Any]:
    """Get current performance summary."""
    return _file_manager.get_performance_summary()


def log_event(
    level: str,
    message: str,
    context: dict[str, Any] | None = None,
    service: str = "system",
    correlation_id: str | None = None,
) -> None:
    """Convenience function for backward compatibility."""
    method = getattr(TreeLogger, level.lower(), TreeLogger.info)
    method(message, context=context, service=service, correlation_id=correlation_id)


def setup_logging(
    log_level: str = DEFAULT_LOG_LEVEL,
    base_log_folder: Path | None = None,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    compression_days: int = DEFAULT_COMPRESSION_DAYS,
) -> None:
    """Setup logging system with automatic log cleanup on startup."""
    global _file_manager

    print("🔧 Setting up logging system...")

    # Perform startup cleanup on existing file manager
    print("🧹 Performing startup log cleanup...")
    _file_manager._cleanup_existing_logs()

    # Create new file manager if different folder specified
    if base_log_folder and str(base_log_folder) != str(_file_manager.base_log_folder):
        _file_manager = LogFileManager(
            base_log_folder, retention_days, compression_days
        )
        _file_manager._cleanup_existing_logs()

    # Setup basic Python logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Configure Discord.py logging levels
    if log_level.upper() in ["INFO", "WARNING", "ERROR", "CRITICAL"]:
        logging.getLogger("discord").setLevel(logging.WARNING)
        logging.getLogger("discord.http").setLevel(logging.WARNING)
        logging.getLogger("discord.gateway").setLevel(logging.INFO)
    else:  # DEBUG
        logging.getLogger("discord").setLevel(logging.DEBUG)

    TreeLogger.info(
        "logging system initialized with fresh logs",
        {
            "log_level": log_level.upper(),
            "base_folder": str(_file_manager.base_log_folder),
            "retention_days": retention_days,
            "compression_days": compression_days,
            "startup_cleanup": "enabled",
        },
        "TreeLogger",
    )
