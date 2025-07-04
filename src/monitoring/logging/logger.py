"""
Professional logging configuration for the Discord Quran Bot.
Provides structured logging with file rotation and console output.
Enhanced with comprehensive monitoring for latency, disconnections, and bugs.
No emojis for clean, professional logs with consistent pipe alignment.

This module provides a comprehensive logging system for the Quran Bot including:
- Structured logging with file rotation
- Console output with color coding
- Performance tracking and monitoring
- System health monitoring
- Error tracking and reporting
- Discord event logging
- Security event logging

Features:
    - Daily log file rotation with date-based folders
    - Color-coded console output
    - Performance tracking and latency monitoring
    - System resource monitoring
    - Comprehensive error handling
    - Structured log formatting
    - JSON logging support
    - Security event tracking

Author: John (Discord: Trippxin)
Version: 2.0.0
"""

import logging
import logging.handlers
import os
from datetime import datetime
from typing import Optional, Dict, Any
from logging.handlers import TimedRotatingFileHandler
import time
import traceback
import colorama
from colorama import Fore, Back, Style
import psutil
import asyncio
import json
import inspect
from src.monitoring.logging.tree_log import tree_log

# Initialize colorama for Windows
colorama.init()

# Get log directory from environment or default to 'logs'
LOG_DIR = os.getenv(
    "QURANBOT_LOG_DIR",
    os.path.join(
        os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        ),
        "logs",
    ),
)
os.makedirs(LOG_DIR, exist_ok=True)

# Get log level from environment or default to INFO
LOG_LEVEL = os.getenv("QURANBOT_LOG_LEVEL", "INFO").upper()
FILE_LOG_LEVEL = getattr(logging, LOG_LEVEL, logging.INFO)
CONSOLE_LOG_LEVEL = getattr(
    logging, os.getenv("QURANBOT_CONSOLE_LOG_LEVEL", "WARNING").upper(), logging.WARNING
)

# Global flag to prevent multiple initializations
_logger_initialized = False

# Color mappings for different log levels (no emojis)
LOG_COLORS = {
    "DEBUG": Fore.CYAN,
    "INFO": Fore.GREEN,
    "WARNING": Fore.YELLOW,
    "ERROR": Fore.RED,
    "CRITICAL": Fore.RED + Style.BRIGHT,
    "SUCCESS": Fore.GREEN + Style.BRIGHT,
    "LATENCY": Fore.MAGENTA,
    "DISCONNECTION": Fore.RED + Style.BRIGHT,
    "CONNECTION": Fore.BLUE,
    "PERFORMANCE": Fore.YELLOW,
    "RESET": Style.RESET_ALL,
}


class EnhancedFormatter(logging.Formatter):
    """
    Custom formatter with colors and tree-like symbols for console output.

    This formatter provides color-coded console output with tree-like
    symbols for better visual hierarchy and readability.
    """

    def format(self, record):
        """
        Format log record with color coding and tree symbols.

        Args:
            record: LogRecord object to format

        Returns:
            str: Color-coded formatted log message with tree symbols
        """
        try:
            # Add color based on log level
            color = LOG_COLORS.get(record.levelname, Fore.WHITE)

            # Get the base message
            message = record.getMessage()
            
            # Check if this is a tree-like line (contains ├─ or └─)
            is_tree_line = "├─" in message or "└─" in message
            
            # Format the message with tree symbols for console
            if is_tree_line:
                # Tree lines get special formatting with proper indentation
                formatted = f"{color}{message}{LOG_COLORS['RESET']}"
            else:
                # Regular lines get standard formatting
                formatted = f"{color}{message}{LOG_COLORS['RESET']}"

            return formatted
        except Exception as e:
            # Fallback to basic formatting if color formatting fails
            return super().format(record)


class HumanReadableFormatter(logging.Formatter):
    """
    Human-readable formatter with clean, structured output.

    This formatter creates structured, easy-to-read log messages
    with proper indentation and visual hierarchy for log files.
    """

    def format(self, record):
        """
        Format log record with human-readable structure.

        Args:
            record: LogRecord object to format

        Returns:
            str: Formatted log message with visual hierarchy
        """
        try:
            # Base timestamp and level
            timestamp = datetime.now().strftime("%I:%M:%S %p")

            # Level emojis and names (no colors for log files)
            level_styles = {
                "DEBUG": {"emoji": "🔍", "name": "DEBUG"},
                "INFO": {"emoji": "ℹ️", "name": "INFO"},
                "WARNING": {"emoji": "⚠️", "name": "WARN"},
                "ERROR": {"emoji": "❌", "name": "ERROR"},
                "CRITICAL": {"emoji": "🚨", "name": "CRIT"},
            }

            style = level_styles.get(
                record.levelname, {"emoji": "📝", "name": record.levelname}
            )

            # Start with main message line
            formatted = f"{timestamp} | {style['emoji']} {style['name']:8} | {record.getMessage()}"

            # Collect additional info to append
            additional_info = []

            # Add module/function info for errors only
            if record.levelname in ["ERROR", "CRITICAL"]:
                additional_info.append(f"📁 {record.module}:{record.lineno}")

            # Add extra data if present (simplified)
            extra_value = getattr(record, "extra", None)
            if extra_value and isinstance(extra_value, dict):
                # Only show key metrics, not all data
                important_keys = [
                    "operation",
                    "component",
                    "user_id",
                    "error",
                    "ResponseTime",
                    "duration",
                    "attempt",
                ]
                extra_str = []
                for key, value in extra_value.items():
                    if key in important_keys:
                        if isinstance(value, (int, float)):
                            extra_str.append(f"{key}={value}")
                        elif isinstance(value, str) and len(value) < 30:
                            extra_str.append(f"{key}='{value}'")
                if extra_str:
                    additional_info.append(f"📊 {', '.join(extra_str[:3])}")

            # Add exception info if present
            if record.exc_info and record.exc_info[0] is not None:
                exc_type = record.exc_info[0].__name__
                exc_msg = str(record.exc_info[1])
                exc_text = (
                    f"{exc_type}: {exc_msg[:50]}..."
                    if len(exc_msg) > 50
                    else f"{exc_type}: {exc_msg}"
                )
                additional_info.append(f"💥 {exc_text}")

            # If we have additional info, append it with tree symbols
            if additional_info:
                # Use tree symbols for visual hierarchy
                for i, info in enumerate(additional_info):
                    if i == len(additional_info) - 1:  # Last item
                        symbol = "└─"
                    else:
                        symbol = "├─"
                    formatted += f"\n{' ' * 11} {symbol} {info}"  # 11 spaces to align with the message

            # Check if this is a tree-like line (contains ├─ or └─)
            is_tree_line = "├─" in record.getMessage() or "└─" in record.getMessage()

            # Only add extra spacing for main event lines, not tree-like lines
            if is_tree_line:
                return formatted  # No extra spacing for tree lines
            else:
                return formatted + "\n"  # Add extra space between main log lines

        except Exception as e:
            # Fallback to basic formatting if structured formatting fails
            return f"{timestamp} | {record.levelname} | {record.getMessage()}"


class DateNamedTimedRotatingFileHandler(TimedRotatingFileHandler):
    """
    Custom handler to name log files as logs/YYYY-MM-DD/filename.

    This handler creates date-based folder structure for log files
    and automatically rotates logs at midnight with proper cleanup.
    """

    def __init__(
        self, filename_suffix=".log", when="midnight", backupCount=30, encoding=None
    ):
        """
        Initialize the date-based rotating file handler.

        Args:
            filename_suffix (str): Suffix for log files
            when (str): When to rotate logs ('midnight', 'hour', etc.)
            backupCount (int): Number of backup files to keep
            encoding (str): File encoding
        """
        try:
            # Use absolute path to the project root directory
            # __file__ is src/monitoring/logging/logger.py, so we need to go up 4 levels to get to project root
            project_root = os.path.dirname(
                os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                )
            )
            base_log_dir = os.path.join(project_root, "logs")
            os.makedirs(base_log_dir, exist_ok=True)

            # Create date-based folder structure
            date_str = datetime.now().strftime("%Y-%m-%d")
            date_log_dir = os.path.join(base_log_dir, date_str)
            os.makedirs(date_log_dir, exist_ok=True)

            # Create log file inside the date folder
            log_file = os.path.join(date_log_dir, f"quranbot{filename_suffix}")

            # Initialize the parent handler
            super().__init__(
                log_file, when=when, backupCount=backupCount, encoding=encoding
            )

            # Ensure the log file exists by writing a startup message
            try:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                startup_msg = f"{timestamp} ℹ️ INFO     | Bot logging initialized - Daily log file created in {date_str}/"
                with open(log_file, "a", encoding=encoding or "utf-8") as f:
                    f.write(startup_msg + "\n")
            except Exception as e:
                # Silently handle startup message writing errors
                pass

        except Exception as e:
            # Fallback to basic handler if date-based setup fails
            super().__init__(
                "quranbot.log", when=when, backupCount=backupCount, encoding=encoding
            )

    def doRollover(self):
        """
        Override to create new date folder when rolling over.

        This method handles log rotation by creating new date-based
        folders and moving log files appropriately.
        """
        try:
            # Get the new date for the rollover
            new_date_str = datetime.now().strftime("%Y-%m-%d")
            project_root = os.path.dirname(
                os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                )
            )
            base_log_dir = os.path.join(project_root, "logs")
            new_date_log_dir = os.path.join(base_log_dir, new_date_str)

            # Create new date folder if it doesn't exist
            os.makedirs(new_date_log_dir, exist_ok=True)

            # Update the log file path to the new date folder
            filename_suffix = (
                os.path.splitext(self.baseFilename)[1]
                if "." in os.path.basename(self.baseFilename)
                else ".log"
            )
            new_log_file = os.path.join(new_date_log_dir, f"quranbot{filename_suffix}")

            # Update the handler's filename
            self.baseFilename = new_log_file

            # Call parent rollover
            super().doRollover()

            # Write startup message to new log file
            try:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                startup_msg = f"{timestamp} ℹ️ INFO     | Bot logging continued - New daily log file created in {new_date_str}/"
                with open(new_log_file, "a", encoding=self.encoding or "utf-8") as f:
                    f.write(startup_msg + "\n")
            except Exception as e:
                # Silently handle startup message writing errors
                pass

        except Exception as e:
            # Fallback to basic rollover if date-based rollover fails
            super().doRollover()


class PerformanceTracker:
    """
    Track performance metrics for operations.

    This class provides performance tracking capabilities for monitoring
    operation durations, latency issues, and system performance.
    """

    def __init__(self):
        """Initialize the performance tracker."""
        self.timers = {}
        self.performance_data = {}
        self.latency_thresholds = {
            "default": 5.0,  # 5 seconds
            "connection": 10.0,  # 10 seconds
            "audio_playback": 2.0,  # 2 seconds
            "discord_api": 3.0,  # 3 seconds
        }

    def start_timer(self, operation: str) -> None:
        """
        Start timing an operation.

        Args:
            operation (str): Name of the operation to time
        """
        try:
            self.timers[operation] = time.time()
        except Exception as e:
            # Silently handle timer start errors
            pass

    def end_timer(self, operation: str) -> float:
        """
        End timing an operation and return duration.

        Args:
            operation (str): Name of the operation to end timing

        Returns:
            float: Duration of the operation in seconds
        """
        try:
            if operation in self.timers:
                duration = time.time() - self.timers[operation]
                del self.timers[operation]

                # Store performance data
                if operation not in self.performance_data:
                    self.performance_data[operation] = []
                self.performance_data[operation].append(duration)

                return duration
            return 0.0
        except Exception as e:
            return 0.0

    def check_latency(self, operation: str, duration: float) -> bool:
        """
        Check if an operation exceeded latency threshold.

        Args:
            operation (str): Name of the operation
            duration (float): Duration of the operation

        Returns:
            bool: True if latency threshold exceeded, False otherwise
        """
        try:
            threshold = self.latency_thresholds.get(
                operation, self.latency_thresholds["default"]
            )
            return duration > threshold
        except Exception as e:
            return False


class SystemMonitor:
    """
    Monitor system resources and health.

    This class provides system monitoring capabilities including
    CPU usage, memory usage, and disk space monitoring.
    """

    def __init__(self):
        """Initialize the system monitor."""
        self.start_time = time.time()
        self.disconnections = []
        self.errors = []
        self.latency_issues = []

    def get_system_stats(self) -> Dict[str, Any]:
        """
        Get current system statistics.

        Returns:
            Dict[str, Any]: Dictionary containing system statistics
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available": memory.available,
                "disk_percent": disk.percent,
                "disk_free": disk.free,
                "uptime": time.time() - self.start_time,
                "disconnection_count": len(self.disconnections),
                "error_count": len(self.errors),
                "latency_issue_count": len(self.latency_issues),
            }
        except Exception as e:
            return {"error": str(e), "uptime": time.time() - self.start_time}

    def record_disconnection(self, reason: str, duration: float = 0) -> None:
        """
        Record a disconnection event.

        Args:
            reason (str): Reason for disconnection
            duration (float): Duration of disconnection
        """
        try:
            self.disconnections.append(
                {"timestamp": time.time(), "reason": reason, "duration": duration}
            )
        except Exception as e:
            # Silently handle disconnection recording errors
            pass

    def record_error(self, error_type: str, error_msg: str) -> None:
        """
        Record an error event.

        Args:
            error_type (str): Type of error
            error_msg (str): Error message
        """
        try:
            self.errors.append(
                {"timestamp": time.time(), "type": error_type, "message": error_msg}
            )
        except Exception as e:
            # Silently handle error recording errors
            pass

    def record_latency_issue(
        self, operation: str, duration: float, threshold: float
    ) -> None:
        """
        Record a latency issue.

        Args:
            operation (str): Name of the operation
            duration (float): Duration of the operation
            threshold (float): Latency threshold that was exceeded
        """
        try:
            self.latency_issues.append(
                {
                    "timestamp": time.time(),
                    "operation": operation,
                    "duration": duration,
                    "threshold": threshold,
                }
            )
        except Exception as e:
            # Silently handle latency issue recording errors
            pass


# Global instances
performance_tracker = PerformanceTracker()
system_monitor = SystemMonitor()

# Set up logger
logger = logging.getLogger("QuranBot")
logger.setLevel(logging.DEBUG)  # Capture all levels

# Don't clear existing handlers - this prevents multiple log files


# Professional log format, no emojis - use defaults when extra is missing
class SafeFormatter(logging.Formatter):
    def format(self, record):
        # Ensure extra field exists
        extra_value = getattr(record, "extra", None)
        if extra_value is None:
            setattr(record, "extra", "")
        else:
            # If extra is a dict, convert to string
            if isinstance(extra_value, dict):
                setattr(record, "extra", str(extra_value))
        return super().format(record)


class JSONFormatter(logging.Formatter):
    """Formatter for detailed JSON logs."""

    def format(self, record):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        # Add extra fields if they exist
        extra_value = getattr(record, "extra", None)
        if extra_value:
            if isinstance(extra_value, dict):
                log_entry.update(extra_value)
            else:
                log_entry["extra"] = str(extra_value)
        # Add exception info if present
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }
        return json.dumps(log_entry, ensure_ascii=False)


file_formatter = SafeFormatter(
    "%(asctime)s | %(name)s | %(levelname)s | %(message)s | %(extra)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
console_formatter = SafeFormatter(
    "%(asctime)s | %(levelname)s | %(message)s | %(extra)s", datefmt="%Y-%m-%d %H:%M:%S"
)

# Only setup handlers if they haven't been setup already
if not logger.handlers:
    # Human-readable log (INFO+) - creates logs/YYYY-MM-DD/quranbot.log
    human_handler = DateNamedTimedRotatingFileHandler(
        filename_suffix=".log", when="midnight", backupCount=30, encoding="utf-8"
    )
    human_handler.setFormatter(HumanReadableFormatter())
    human_handler.setLevel(logging.INFO)
    logger.addHandler(human_handler)

    # Error-only log (ERROR+) - creates logs/YYYY-MM-DD/quranbot-errors.log
    error_handler = DateNamedTimedRotatingFileHandler(
        filename_suffix="-errors.log", when="midnight", backupCount=30, encoding="utf-8"
    )
    error_handler.setFormatter(HumanReadableFormatter())
    error_handler.setLevel(logging.ERROR)
    logger.addHandler(error_handler)

    # Detailed JSON log (DEBUG+) - creates logs/YYYY-MM-DD/quranbot.json
    json_handler = DateNamedTimedRotatingFileHandler(
        filename_suffix=".json", when="midnight", backupCount=30, encoding="utf-8"
    )
    json_handler.setFormatter(JSONFormatter())
    json_handler.setLevel(logging.DEBUG)
    logger.addHandler(json_handler)

# Console handler - only enable in development
if os.getenv("ENVIRONMENT", "production") == "development":
    console_handlers = [
        h for h in logger.handlers if isinstance(h, logging.StreamHandler)
    ]
    if not console_handlers:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.DEBUG)
        logger.addHandler(console_handler)

# Log startup message (only if not already written)
if not hasattr(logger, "_startup_message_written"):
    tree_log('info', 'QuranBot logging system initialized - Dual log rotation enabled', {'event': 'LOGGER_STARTUP'})
    setattr(logger, "_startup_message_written", True)


def log_bot_startup(bot_name: str, bot_id: int):
    """Log bot startup with enhanced formatting."""
    logger.info(f"Bot '{bot_name}' (ID: {bot_id}) started successfully")


def log_audio_playback(file_name: str, duration: Optional[float] = None):
    """Log audio playback with performance metrics."""
    if duration:
        logger.info(f"Playing audio file: {file_name} (Duration: {duration:.2f}s)")
    else:
        logger.info(f"Playing audio file: {file_name}")


def log_connection_attempt(channel_name: str, attempt: int, max_attempts: int):
    """Log connection attempts with retry information."""
    logger.info(
        f"Connecting to voice channel: {channel_name} (Attempt {attempt}/{max_attempts})"
    )


def log_connection_success(channel_name: str, guild_name: str):
    """Log successful connection."""
    logger.info(f"Successfully connected to {channel_name} in {guild_name}")


def log_connection_failure(channel_name: str, error: Exception, attempt: int):
    """
    Log connection failure with detailed error information.

    Args:
        channel_name (str): Name of the channel connection failed to
        error (Exception): The error that occurred
        attempt (int): Current attempt number
    """
    try:
        system_monitor.record_disconnection(f"Connection failed: {str(error)}")
        logger.error(
            f"Failed to connect to {channel_name} (Attempt {attempt}): {str(error)}"
        )
    except Exception as e:
        from src.monitoring.logging.tree_log import tree_log
        tree_log('error', 'Error logging connection failure', {'error': str(e), 'channel_name': channel_name, 'attempt': attempt})


def log_health_report(sent: bool, channel_id: int):
    """Log health report status."""
    status = "sent" if sent else "failed"
    logger.info(f"Health report {status} to channel {channel_id}")


def log_state_save(operation: str, data: Dict[str, Any]):
    """Log state save operations."""
    logger.debug(f"State saved: {operation} - {data}")


def log_state_load(operation: str, data: Dict[str, Any]):
    """Log state load operations."""
    logger.debug(f"State loaded: {operation} - {data}")


def log_performance(operation: str, duration: float, success: bool = True):
    """
    Log performance metrics with latency monitoring.

    Args:
        operation (str): Name of the operation
        duration (float): Duration of the operation in seconds
        success (bool): Whether the operation was successful
    """
    try:
        status = "SUCCESS" if success else "FAILED"

        # Check for latency issues
        if performance_tracker.check_latency(operation, duration * 1000):
            system_monitor.record_latency_issue(
                operation,
                duration * 1000,
                performance_tracker.latency_thresholds.get(operation, 5000),
            )
            logger.warning(
                f"LATENCY ISSUE: {operation} took {duration:.3f}s (threshold exceeded)"
            )

        logger.info(f"Performance: {operation} completed in {duration:.3f}s [{status}]")
    except Exception as e:
        from src.monitoring.logging.tree_log import tree_log
        tree_log('error', 'Error logging performance', {'error': str(e), 'operation': operation, 'duration': duration})


def log_error(
    error: Exception,
    context: str,
    retry_attempt: Optional[int] = None,
    additional_data: Optional[Dict[str, Any]] = None,
):
    """
    Log errors with comprehensive error tracking.

    Args:
        error (Exception): The error that occurred
        context (str): Context where the error occurred
        retry_attempt (Optional[int]): Current retry attempt number
        additional_data (Optional[Dict[str, Any]]): Additional error data
    """
    try:
        system_monitor.record_error(type(error).__name__, str(error))

        # Get system stats for context
        system_stats = system_monitor.get_system_stats()

        error_msg = f"ERROR in {context}: {str(error)}"
        if retry_attempt:
            error_msg += f" (Retry attempt: {retry_attempt})"

        logger.error(error_msg)
        logger.debug(f"System stats: {system_stats}")

        if additional_data:
            logger.debug(f"Additional error data: {additional_data}")

        log_tree_start("Error Context")
        log_tree_item(f"Context: {context}")
        log_tree_item(f"Type: {type(error).__name__}")
        log_tree_item(f"Message: {str(error)}")
        log_tree_item(f"System stats: {system_stats}")
        if additional_data:
            log_tree_item(f"Additional data: {additional_data}")
        log_tree_item(f"Traceback: {traceback.format_exc()}", is_last=True)
        log_tree_end()

    except Exception as e:
        from src.monitoring.logging.tree_log import tree_log
        tree_log('error', 'Error logging error', {'error': str(e), 'traceback': traceback.format_exc(), 'original_error': error, 'context': context})


def log_discord_event(event_type: str, details: Dict[str, Any]):
    """Log Discord events with performance tracking."""
    logger.info(f"Discord event: {event_type} - {details}")


def log_ffmpeg_operation(
    operation: str, input_files: list, output_file: str, duration: float
):
    """Log FFmpeg operations with performance metrics."""
    logger.info(
        f"FFmpeg {operation}: {len(input_files)} files -> {output_file} (Duration: {duration:.3f}s)"
    )


def log_security_event(event_type: str, details: Dict[str, Any]):
    """Log security events."""
    logger.warning(f"Security event: {event_type} - {details}")


def log_retry_operation(operation: str, attempt: int, max_attempts: int, delay: float):
    """Log retry operations."""
    logger.info(
        f"Retry {operation}: Attempt {attempt}/{max_attempts} (Delay: {delay:.2f}s)"
    )


def log_shutdown(reason: str):
    """Log bot shutdown."""
    logger.info(f"Bot shutdown: {reason}")


def log_disconnection(channel_name: str, reason: str):
    """
    Log disconnection events with monitoring.

    Args:
        channel_name (str): Name of the channel disconnected from
        reason (str): Reason for disconnection
    """
    try:
        system_monitor.record_disconnection(reason)
        logger.warning(f"Disconnected from {channel_name}: {reason}")
    except Exception as e:
        from src.monitoring.logging.tree_log import tree_log
        tree_log('error', 'Error logging disconnection', {'error': str(e), 'channel_name': channel_name, 'reason': reason})


def log_latency_monitoring(operation: str, duration: float, threshold: float):
    """
    Log latency monitoring specifically.

    Args:
        operation (str): Name of the operation
        duration (float): Duration of the operation in milliseconds
        threshold (float): Latency threshold in milliseconds
    """
    try:
        if duration > threshold:
            system_monitor.record_latency_issue(operation, duration, threshold)
            logger.warning(
                f"LATENCY ALERT: {operation} took {duration:.2f}ms (threshold: {threshold}ms)"
            )
        else:
            logger.debug(
                f"Latency OK: {operation} took {duration:.2f}ms (threshold: {threshold}ms)"
            )
    except Exception as e:
        from src.monitoring.logging.tree_log import tree_log
        tree_log('error', 'Error logging latency monitoring', {'error': str(e), 'operation': operation, 'duration': duration, 'threshold': threshold})


def log_system_health():
    """Log comprehensive system health information."""
    stats = system_monitor.get_system_stats()
    tree_log('tree', 'System Health Check', {
        'event': 'SYSTEM_HEALTH_CHECK',
        'memory_percent': stats.get('memory_percent', 'N/A'),
        'cpu_percent': stats.get('cpu_percent', 'N/A'),
        'disk_percent': stats.get('disk_percent', 'N/A'),
        'uptime': stats.get('uptime', 0),
        'disconnection_count': stats.get('disconnection_count', 0),
        'error_count': stats.get('error_count', 0),
        'latency_issue_count': stats.get('latency_issue_count', 0)
    })


def track_performance(operation_name: str):
    """Decorator to track performance of functions."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            performance_tracker.start_timer(operation_name)
            try:
                result = func(*args, **kwargs)
                duration = performance_tracker.end_timer(operation_name)
                log_performance(operation_name, duration, True)
                return result
            except Exception as e:
                duration = performance_tracker.end_timer(operation_name)
                log_performance(operation_name, duration, False)
                log_error(e, operation_name)
                raise

        return wrapper

    return decorator


# Example usage for sync functions:
# @log_function_call
# def some_helper_function():
#     # ... existing code ...

# Apply these decorators to all major functions throughout the file.

# Silence noisy third-party loggers
for noisy_logger in ["discord", "asyncio", "websockets", "urllib3"]:
    logging.getLogger(noisy_logger).setLevel(logging.WARNING)

# Periodic health/status logging (every 10 minutes)
import threading


def log_tree_start(title: str, logger=None):
    """
    Start a tree-like log section with a title.
    
    Args:
        title (str): The title for the tree section
        logger: Logger instance (optional)
    
    Returns:
        str: The formatted start message
    """
    if logger is None:
        logger = logging.getLogger("QuranBot")
    
    message = f"🌳 {title}"
    logger.info(message)
    return message


def log_tree_item(item: str, is_last: bool = False, logger=None):
    """
    Log a tree item with proper tree symbols.
    
    Args:
        item (str): The item to log
        is_last (bool): Whether this is the last item in the branch
        logger: Logger instance (optional)
    
    Returns:
        str: The formatted tree item message
    """
    if logger is None:
        logger = logging.getLogger("QuranBot")
    
    symbol = "└─" if is_last else "├─"
    message = f"{symbol} {item}"
    logger.info(message)
    return message


def log_tree_branch(items: list, logger=None):
    """
    Log a branch of tree items.
    
    Args:
        items (list): List of items to log as a branch
        logger: Logger instance (optional)
    
    Returns:
        list: List of formatted messages
    """
    if logger is None:
        logger = logging.getLogger("QuranBot")
    
    messages = []
    for i, item in enumerate(items):
        is_last = i == len(items) - 1
        message = log_tree_item(item, is_last, logger)
        messages.append(message)
    
    return messages


def log_tree_end(logger=None):
    """
    End a tree-like log section with proper spacing.
    
    Args:
        logger: Logger instance (optional)
    """
    if logger is None:
        logger = logging.getLogger("QuranBot")
    
    # Add a blank line to separate tree sections
    logger.info("")


def log_system_health_periodically():
    stats = system_monitor.get_system_stats()
    tree_log('tree', 'Periodic System Health Check', {
        'event': 'PERIODIC_SYSTEM_HEALTH_CHECK',
        'memory_percent': stats.get('memory_percent', 'N/A'),
        'cpu_percent': stats.get('cpu_percent', 'N/A'),
        'disk_percent': stats.get('disk_percent', 'N/A'),
        'network_sent': stats.get('network_sent', 0),
        'network_recv': stats.get('network_recv', 0)
    })
    threading.Timer(600, log_system_health_periodically).start()  # 10 minutes


log_system_health_periodically()
