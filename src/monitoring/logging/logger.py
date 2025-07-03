"""
Professional logging configuration for the Discord Quran Bot.
Provides structured logging with file rotation and console output.
Enhanced with comprehensive monitoring for latency, disconnections, and bugs.
No emojis for clean, professional logs with consistent pipe alignment.
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

# Initialize colorama for Windows
colorama.init()

LOG_DIR = 'logs'
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Color mappings for different log levels (no emojis)
LOG_COLORS = {
    'DEBUG': Fore.CYAN,
    'INFO': Fore.GREEN,
    'WARNING': Fore.YELLOW,
    'ERROR': Fore.RED,
    'CRITICAL': Fore.RED + Style.BRIGHT,
    'SUCCESS': Fore.GREEN + Style.BRIGHT,
    'LATENCY': Fore.MAGENTA,
    'DISCONNECTION': Fore.RED + Style.BRIGHT,
    'CONNECTION': Fore.BLUE,
    'PERFORMANCE': Fore.YELLOW,
    'RESET': Style.RESET_ALL
}

class EnhancedFormatter(logging.Formatter):
    """Custom formatter with colors but no emojis for console output."""
    
    def format(self, record):
        # Add color based on log level
        color = LOG_COLORS.get(record.levelname, Fore.WHITE)
        
        # Format the message
        formatted = super().format(record)
        
        # Add color only
        colored_message = f"{color}{formatted}{LOG_COLORS['RESET']}"
        
        return colored_message

class DateNamedTimedRotatingFileHandler(TimedRotatingFileHandler):
    """Custom handler to name log files as logs/YYYY-MM-DD.log"""
    def __init__(self, when='midnight', backupCount=30, encoding=None):
        # Use absolute path to the project root directory
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        log_dir = os.path.join(project_root, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        date_str = datetime.now().strftime('%Y-%m-%d')
        log_file = os.path.join(log_dir, f"{date_str}.log")
        super().__init__(log_file, when=when, backupCount=backupCount, encoding=encoding)

class PerformanceTracker:
    """Track performance metrics for operations."""
    
    def __init__(self):
        self.metrics: Dict[str, list] = {}
        self.latency_thresholds = {
            'interaction_response': 1000,  # 1 second
            'audio_playback': 5000,        # 5 seconds
            'voice_connection': 3000,      # 3 seconds
            'discord_api': 2000,           # 2 seconds
            'file_operations': 1000        # 1 second
        }
        
    def start_timer(self, operation: str):
        """Start timing an operation."""
        if operation not in self.metrics:
            self.metrics[operation] = []
        self.metrics[operation].append(time.time())
        
    def end_timer(self, operation: str) -> float:
        """End timing an operation and return duration."""
        if operation in self.metrics and self.metrics[operation]:
            start_time = self.metrics[operation].pop()
            duration = time.time() - start_time
            return duration
        return 0.0
    
    def check_latency(self, operation: str, duration: float) -> bool:
        """Check if operation exceeded latency threshold."""
        threshold = self.latency_thresholds.get(operation, 5000)
        return duration > threshold

class SystemMonitor:
    """Monitor system resources and bot health."""
    
    def __init__(self):
        self.start_time = time.time()
        self.disconnection_count = 0
        self.error_count = 0
        self.latency_issues = 0
        self.last_health_check = time.time()
        
    def get_system_stats(self) -> Dict[str, Any]:
        """Get current system statistics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available': memory.available,
                'disk_percent': disk.percent,
                'disk_free': disk.free,
                'uptime': time.time() - self.start_time
            }
        except Exception as e:
            return {'error': str(e)}
    
    def record_disconnection(self, reason: str, duration: float = 0):
        """Record a disconnection event."""
        self.disconnection_count += 1
        return {
            'count': self.disconnection_count,
            'reason': reason,
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        }
    
    def record_error(self, error_type: str, error_msg: str):
        """Record an error event."""
        self.error_count += 1
        return {
            'count': self.error_count,
            'type': error_type,
            'message': error_msg,
            'timestamp': datetime.now().isoformat()
        }
    
    def record_latency_issue(self, operation: str, duration: float, threshold: float):
        """Record a latency issue."""
        self.latency_issues += 1
        return {
            'count': self.latency_issues,
            'operation': operation,
            'duration': duration,
            'threshold': threshold,
            'timestamp': datetime.now().isoformat()
        }

# Global instances
performance_tracker = PerformanceTracker()
system_monitor = SystemMonitor()

# Set up logger
logger = logging.getLogger('QuranBot')
logger.setLevel(logging.DEBUG)  # Capture all levels

# Clear existing handlers
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Professional log format, no emojis - use defaults when extra is missing
class SafeFormatter(logging.Formatter):
    def format(self, record):
        # Ensure extra field exists
        extra_value = getattr(record, 'extra', None)
        if extra_value is None:
            setattr(record, 'extra', '')
        else:
            # If extra is a dict, convert to string
            if isinstance(extra_value, dict):
                setattr(record, 'extra', str(extra_value))
        return super().format(record)

file_formatter = SafeFormatter(
    '%(asctime)s | %(name)s | %(levelname)s | %(message)s | %(extra)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
console_formatter = SafeFormatter(
    '%(asctime)s | %(levelname)s | %(message)s | %(extra)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# File handler with daily rotation and date-named logs
file_handler = DateNamedTimedRotatingFileHandler(when='midnight', backupCount=30, encoding='utf-8')
file_handler.setFormatter(file_formatter)
file_handler.setLevel(logging.DEBUG)
logger.addHandler(file_handler)

# Console handler - only enable in development
# Disable console handler in production to avoid conflicts with shell redirection
if os.getenv('ENVIRONMENT', 'production') == 'development':
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)

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
    logger.info(f"Connecting to voice channel: {channel_name} (Attempt {attempt}/{max_attempts})")

def log_connection_success(channel_name: str, guild_name: str):
    """Log successful connection."""
    logger.info(f"Successfully connected to {channel_name} in {guild_name}")

def log_connection_failure(channel_name: str, error: Exception, attempt: int):
    """Log connection failure with detailed error information."""
    disconnection_data = system_monitor.record_disconnection(f"Connection failed: {str(error)}")
    logger.error(f"Failed to connect to {channel_name} (Attempt {attempt}): {str(error)}")
    logger.debug(f"Disconnection data: {disconnection_data}")

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
    """Log performance metrics with latency monitoring."""
    status = "SUCCESS" if success else "FAILED"
    
    # Check for latency issues
    if performance_tracker.check_latency(operation, duration * 1000):
        latency_data = system_monitor.record_latency_issue(operation, duration * 1000, 
                                                         performance_tracker.latency_thresholds.get(operation, 5000))
        logger.warning(f"LATENCY ISSUE: {operation} took {duration:.3f}s (threshold exceeded)")
        logger.debug(f"Latency data: {latency_data}")
    
    logger.info(f"Performance: {operation} completed in {duration:.3f}s [{status}]")

def log_error(error: Exception, context: str, retry_attempt: Optional[int] = None, 
             additional_data: Optional[Dict[str, Any]] = None):
    """Log errors with comprehensive error tracking."""
    error_data = system_monitor.record_error(type(error).__name__, str(error))
    
    # Get system stats for context
    system_stats = system_monitor.get_system_stats()
    
    error_msg = f"ERROR in {context}: {str(error)}"
    if retry_attempt:
        error_msg += f" (Retry attempt: {retry_attempt})"
    
    logger.error(error_msg)
    logger.debug(f"Error data: {error_data}")
    logger.debug(f"System stats: {system_stats}")
    
    if additional_data:
        logger.debug(f"Additional error data: {additional_data}")

def log_discord_event(event_type: str, details: Dict[str, Any]):
    """Log Discord events with performance tracking."""
    logger.info(f"Discord event: {event_type} - {details}")

def log_ffmpeg_operation(operation: str, input_files: list, output_file: str, duration: float):
    """Log FFmpeg operations with performance metrics."""
    logger.info(f"FFmpeg {operation}: {len(input_files)} files -> {output_file} (Duration: {duration:.3f}s)")

def log_security_event(event_type: str, details: Dict[str, Any]):
    """Log security events."""
    logger.warning(f"Security event: {event_type} - {details}")

def log_retry_operation(operation: str, attempt: int, max_attempts: int, delay: float):
    """Log retry operations."""
    logger.info(f"Retry {operation}: Attempt {attempt}/{max_attempts} (Delay: {delay:.2f}s)")

def log_shutdown(reason: str):
    """Log bot shutdown."""
    logger.info(f"Bot shutdown: {reason}")

def log_disconnection(channel_name: str, reason: str):
    """Log disconnection events with monitoring."""
    disconnection_data = system_monitor.record_disconnection(reason)
    logger.warning(f"Disconnected from {channel_name}: {reason}")
    logger.debug(f"Disconnection data: {disconnection_data}")

def log_latency_monitoring(operation: str, duration: float, threshold: float):
    """Log latency monitoring specifically."""
    if duration > threshold:
        latency_data = system_monitor.record_latency_issue(operation, duration, threshold)
        logger.warning(f"LATENCY ALERT: {operation} took {duration:.2f}ms (threshold: {threshold}ms)")
        logger.debug(f"Latency data: {latency_data}")
    else:
        logger.debug(f"Latency OK: {operation} took {duration:.2f}ms (threshold: {threshold}ms)")

def log_system_health():
    """Log comprehensive system health information."""
    stats = system_monitor.get_system_stats()
    logger.info(f"System health check: CPU {stats.get('cpu_percent', 'N/A')}%, "
                f"Memory {stats.get('memory_percent', 'N/A')}%, "
                f"Uptime {stats.get('uptime', 0):.0f}s, "
                f"Disconnections: {system_monitor.disconnection_count}, "
                f"Errors: {system_monitor.error_count}, "
                f"Latency issues: {system_monitor.latency_issues}")

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