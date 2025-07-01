"""
Professional logging configuration for the Discord Quran Bot.
Provides structured logging with file rotation and console output.
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

# Initialize colorama for Windows
colorama.init()

LOG_DIR = 'logs'
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Emoji and color mappings for different log levels and events
LOG_EMOJIS = {
    'DEBUG': '🔍',
    'INFO': 'ℹ️',
    'WARNING': '⚠️',
    'ERROR': '❌',
    'CRITICAL': '🔥',
    'SUCCESS': '✅',
    'STARTUP': '🚀',
    'SHUTDOWN': '🛑',
    'CONNECTION': '🔗',
    'DISCONNECTION': '🔌',
    'AUDIO': '🎵',
    'HEALTH': '💚',
    'STATE': '💾',
    'CROSSFADE': '🎚️',
    'RETRY': '🔄',
    'PERFORMANCE': '⚡',
    'SECURITY': '🔒',
    'DISCORD': '🤖',
    'FFMPEG': '🎬'
}

LOG_COLORS = {
    'DEBUG': Fore.CYAN,
    'INFO': Fore.GREEN,
    'WARNING': Fore.YELLOW,
    'ERROR': Fore.RED,
    'CRITICAL': Fore.RED + Style.BRIGHT,
    'SUCCESS': Fore.GREEN + Style.BRIGHT,
    'RESET': Style.RESET_ALL
}

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors and emojis for console output."""
    
    def format(self, record):
        # Add emoji based on log level or custom event
        emoji = LOG_EMOJIS.get(record.levelname, '📝')
        if hasattr(record, 'event') and hasattr(record.event, '__str__') and str(record.event) in LOG_EMOJIS:
            emoji = LOG_EMOJIS[str(record.event)]
            
        # Add color
        color = LOG_COLORS.get(record.levelname, Fore.WHITE)
        
        # Format the message
        formatted = super().format(record)
        
        # Add emoji and color
        colored_message = f"{color}{emoji} {formatted}{LOG_COLORS['RESET']}"
        
        return colored_message

class DateNamedTimedRotatingFileHandler(TimedRotatingFileHandler):
    """Custom handler to name log files as logs/YYYY-MM-DD.log"""
    def __init__(self, when='midnight', interval=1, backupCount=30, encoding=None, delay=False, utc=False):
        # Create the date-based filename immediately
        date_str = datetime.now().strftime('%Y-%m-%d')
        log_filename = os.path.join(LOG_DIR, f'{date_str}.log')
        
        # Initialize with the actual date-named file
        super().__init__(log_filename, when, interval, backupCount, encoding, delay, utc)
        
        # Store the current date for rotation checking
        self.current_date = date_str

    def emit(self, record):
        """Override emit to check for date changes and rotate if needed."""
        # Check if the date has changed
        current_date = datetime.now().strftime('%Y-%m-%d')
        if current_date != self.current_date:
            # Date changed, rotate the log
            self.doRollover()
            self.current_date = current_date
            
        super().emit(record)

    def doRollover(self):
        """Rotate to a new date-based filename."""
        # Close the current file
        if self.stream:
            self.stream.close()
            self.stream = None
            
        # Create new filename with current date
        date_str = datetime.now().strftime('%Y-%m-%d')
        new_log = os.path.join(LOG_DIR, f'{date_str}.log')
        
        # Update the base filename
        self.baseFilename = new_log
        
        # Open the new file
        if not self.delay:
            self.stream = self._open()

class PerformanceTracker:
    """Track performance metrics for operations."""
    
    def __init__(self):
        self.metrics: Dict[str, list] = {}
        
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

# Global performance tracker
performance_tracker = PerformanceTracker()

# Set up logger
logger = logging.getLogger('QuranBot')
logger.setLevel(logging.DEBUG)  # Capture all levels

# Clear existing handlers
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# File formatter (no colors for file logs)
file_formatter = logging.Formatter(
    '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    datefmt='%m-%d | %I:%M:%S %p'
)

# Console formatter (with colors and emojis)
console_formatter = ColoredFormatter(
    '%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%m-%d | %I:%M:%S %p'
)

# File handler with daily rotation and date-named logs
file_handler = DateNamedTimedRotatingFileHandler(when='midnight', backupCount=30, encoding='utf-8')
file_handler.setFormatter(file_formatter)
file_handler.setLevel(logging.DEBUG)
logger.addHandler(file_handler)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(console_formatter)
console_handler.setLevel(logging.INFO)
logger.addHandler(console_handler)

def log_bot_startup(bot_name: str, bot_id: int):
    """Log bot startup with enhanced formatting."""
    logger.info(f"Bot '{bot_name}' (ID: {bot_id}) started successfully", 
                extra={'event': 'STARTUP'})

def log_audio_playback(file_name: str, duration: Optional[float] = None):
    """Log audio playback with performance metrics."""
    if duration:
        logger.info(f"Playing audio file: {file_name} (Duration: {duration:.2f}s)", 
                    extra={'event': 'AUDIO'})
    else:
        logger.info(f"Playing audio file: {file_name}", 
                    extra={'event': 'AUDIO'})

def log_crossfade_generation(file1: str, file2: str, duration: float):
    """Log crossfade generation with performance metrics."""
    logger.info(f"Generated crossfade: {os.path.basename(file1)} → {os.path.basename(file2)} (Duration: {duration:.2f}s)", 
                extra={'event': 'CROSSFADE'})

def log_connection_attempt(channel_name: str, attempt: int, max_attempts: int):
    """Log connection attempts with retry information."""
    logger.info(f"Connecting to voice channel: {channel_name} (Attempt {attempt}/{max_attempts})", 
                extra={'event': 'CONNECTION', 'attempt': str(attempt), 'max_attempts': str(max_attempts)})

def log_connection_success(channel_name: str, guild_name: str):
    """Log successful connection."""
    logger.info(f"Successfully connected to {channel_name} in {guild_name}", 
                extra={'event': 'CONNECTION'})

def log_connection_failure(channel_name: str, error: Exception, attempt: int):
    """Log connection failure with detailed error information."""
    logger.error(f"Failed to connect to {channel_name} (Attempt {attempt}): {str(error)}", 
                extra={'event': 'CONNECTION', 'error_type': type(error).__name__, 'attempt': attempt})

def log_health_report(sent: bool, channel_id: int):
    """Log health report status."""
    status = "sent" if sent else "failed to send"
    logger.info(f"Health report {status} to channel {channel_id}", 
                extra={'event': 'HEALTH'})

def log_state_save(operation: str, data: Dict[str, Any]):
    """Log state save operations."""
    logger.info(f"State saved: {operation}", 
                extra={'event': 'STATE'})

def log_state_load(operation: str, data: Dict[str, Any]):
    """Log state load operations."""
    logger.info(f"State loaded: {operation}", 
                extra={'event': 'STATE'})

def log_performance(operation: str, duration: float, success: bool = True):
    """Log performance metrics."""
    status = "completed" if success else "failed"
    logger.info(f"Performance: {operation} {status} in {duration:.2f}s", 
                extra={'event': 'PERFORMANCE'})

def log_error(error: Exception, context: str, retry_attempt: Optional[int] = None, 
             additional_data: Optional[Dict[str, Any]] = None):
    """Log errors with context and retry information."""
    error_msg = f"Error in {context}: {str(error)}"
    if retry_attempt is not None:
        error_msg += f" (Retry attempt: {retry_attempt})"
    
    extra_data = {'event': 'ERROR', 'context': context}
    if retry_attempt is not None:
        extra_data['retry_attempt'] = str(retry_attempt)
    if additional_data:
        extra_data.update(additional_data)
    
    logger.error(error_msg, extra=extra_data)

def log_discord_event(event_type: str, details: Dict[str, Any]):
    """Log Discord events."""
    logger.info(f"Discord event: {event_type}", 
                extra={'event': 'DISCORD'})

def log_ffmpeg_operation(operation: str, input_files: list, output_file: str, duration: float):
    """Log FFmpeg operations."""
    logger.info(f"FFmpeg {operation}: {len(input_files)} files → {output_file} ({duration:.2f}s)", 
                extra={'event': 'FFMPEG'})

def log_security_event(event_type: str, details: Dict[str, Any]):
    """Log security events."""
    logger.warning(f"Security event: {event_type}", 
                   extra={'event': 'SECURITY'})

def log_retry_operation(operation: str, attempt: int, max_attempts: int, delay: float):
    """Log retry operations."""
    logger.info(f"Retrying {operation} (Attempt {attempt}/{max_attempts}, delay: {delay:.2f}s)", 
                extra={'event': 'RETRY', 'attempt': str(attempt), 'max_attempts': str(max_attempts)})

def log_shutdown(reason: str):
    """Log bot shutdown."""
    logger.info(f"Bot shutdown: {reason}", 
                extra={'event': 'SHUTDOWN'})

def log_disconnection(channel_name: str, reason: str):
    """Log disconnection events."""
    logger.info(f"Disconnected from {channel_name}: {reason}", 
                extra={'event': 'DISCONNECTION'})

# Performance tracking decorator
def track_performance(operation_name: str):
    """Decorator to track performance of functions."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            performance_tracker.start_timer(operation_name)
            try:
                result = func(*args, **kwargs)
                duration = performance_tracker.end_timer(operation_name)
                log_performance(operation_name, duration, success=True)
                return result
            except Exception as e:
                duration = performance_tracker.end_timer(operation_name)
                log_performance(operation_name, duration, success=False)
                raise
        return wrapper
    return decorator 