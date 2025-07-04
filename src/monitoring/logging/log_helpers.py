import time
import traceback
import psutil
import gc
from datetime import datetime
from typing import Optional, Dict, Any, Callable
import functools

try:
    from zoneinfo import ZoneInfo
    eastern = ZoneInfo("America/New_York")
except ImportError:
    import pytz
    eastern = pytz.timezone("America/New_York")

# Use the main logger from logger_fixed
from src.monitoring.logging.tree_log import tree_log

def get_system_metrics():
    process = psutil.Process()
    memory_info = process.memory_info()
    cpu_percent = process.cpu_percent()
    gc_stats = gc.get_stats()
    return {
        "memory_rss_mb": memory_info.rss / 1024 / 1024,
        "memory_vms_mb": memory_info.vms / 1024 / 1024,
        "cpu_percent": cpu_percent,
        "gc_collections": len(gc_stats),
        "gc_objects": sum(stat['collections'] for stat in gc_stats),
        "gc_time": sum(stat['collections'] for stat in gc_stats)
    }

def get_discord_context(interaction) -> Dict[str, Any]:
    user = getattr(interaction, 'user', None)
    guild = getattr(interaction, 'guild', None)
    channel = getattr(interaction, 'channel', None)
    context = {
        "user_id": getattr(user, 'id', None),
        "user_name": getattr(user, 'name', None),
        "user_display_name": getattr(user, 'display_name', None),
        "guild_id": getattr(guild, 'id', None),
        "guild_name": getattr(guild, 'name', None),
        "channel_id": getattr(channel, 'id', None),
        "channel_name": getattr(channel, 'name', None),
        "interaction_id": getattr(interaction, 'id', None),
        "interaction_type": str(getattr(interaction, 'type', None)),
        "created_at": getattr(interaction, 'created_at', None),
    }
    return context

def get_bot_state(bot) -> Dict[str, Any]:
    try:
        return {
            "bot_user_id": bot.user.id if bot.user else None,
            "bot_user_name": bot.user.name if bot.user else None,
            "bot_guild_count": len(bot.guilds),
            "bot_user_count": len(bot.users),
            "bot_latency": round(bot.latency * 1000, 2),
            "bot_is_ready": bot.is_ready(),
            "current_reciter": getattr(bot, 'current_reciter', None),
            "is_streaming": getattr(bot, 'is_streaming', None),
            "loop_enabled": getattr(bot, 'loop_enabled', None),
            "shuffle_enabled": getattr(bot, 'shuffle_enabled', None),
            "current_audio_file": getattr(bot, 'current_audio_file', None),
            "current_song_index": bot.state_manager.get_current_song_index() if hasattr(bot, 'state_manager') else None,
            "current_song_name": bot.state_manager.get_current_song_name() if hasattr(bot, 'state_manager') else None,
        }
    except Exception as e:
        return {"bot_state_error": str(e)}

def get_eastern_now():
    try:
        return datetime.now(eastern)
    except Exception:
        # fallback to naive now
        return datetime.now()

def log_operation(operation: str, level: str = "INFO", extra: Optional[Dict[str, Any]] = None, error: Optional[Exception] = None):
    """Enhanced logging with operation tracking and structured data using tree_log."""
    try:
        current_time = get_eastern_now()
        timestamp = current_time.strftime('%m-%d | %I:%M:%S %p')
        log_data = {
            "operation": operation,
            "timestamp": timestamp,
            "component": "log_helpers",
            "timezone": "US/Eastern"
        }
        if extra:
            log_data.update(extra)
        if error:
            log_data["error"] = str(error)
            log_data["error_type"] = type(error).__name__
            log_data["traceback"] = traceback.format_exc()
            level = "ERROR"
        tree_log(level.lower(), f"Log Helpers - {operation.upper()}", log_data)
    except Exception as e:
        tree_log('error', 'log_operation failed', {'operation': operation, 'error': str(e), 'traceback': traceback.format_exc()})

def log_function_call(func: Callable):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        system_metrics_before = get_system_metrics()
        try:
            result = func(*args, **kwargs)
            response_time = (time.time() - start_time) * 1000
            system_metrics_after = get_system_metrics()
            now = get_eastern_now()
            tree_log('info', f'FUNC_CALL | {func.__name__}', {
                'ResponseTime': f'{response_time:.2f}ms',
                'MemoryChange': f"{system_metrics_after['memory_rss_mb'] - system_metrics_before['memory_rss_mb']:+.1f}MB",
                'CPUChange': f"{system_metrics_after['cpu_percent'] - system_metrics_before['cpu_percent']:+.1f}%"
            })
            return result
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            system_metrics_after = get_system_metrics()
            now = get_eastern_now()
            tree_log('error', f'FUNC_ERROR | {func.__name__}', {
                'ResponseTime': f'{response_time:.2f}ms',
                'Error': str(e),
                'Traceback': traceback.format_exc()
            })
            raise
    return wrapper

def log_async_function_call(func: Callable):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        system_metrics_before = get_system_metrics()
        try:
            result = await func(*args, **kwargs)
            response_time = (time.time() - start_time) * 1000
            system_metrics_after = get_system_metrics()
            now = get_eastern_now()
            tree_log('info', f"ASYNC_FUNC_CALL | {func.__name__}", extra={"extra": {
                "ResponseTime": f"{response_time:.2f}ms",
                "MemoryChange": f"{system_metrics_after['memory_rss_mb'] - system_metrics_before['memory_rss_mb']:+.1f}MB",
                "CPUChange": f"{system_metrics_after['cpu_percent'] - system_metrics_before['cpu_percent']:+.1f}%"
            }})
            return result
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            system_metrics_after = get_system_metrics()
            now = get_eastern_now()
            tree_log('error', f"ASYNC_FUNC_ERROR | {func.__name__}", extra={"extra": {
                "ResponseTime": f"{response_time:.2f}ms",
                "Error": str(e),
                "Traceback": traceback.format_exc()
            }})
            raise
    return wrapper 