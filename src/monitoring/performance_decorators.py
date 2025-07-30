# =============================================================================
# QuranBot - Performance Monitoring Decorators
# =============================================================================
# Decorators for automatically tracking command and database performance
# =============================================================================

import asyncio
from functools import wraps
import hashlib
import time
from typing import Any, Callable

from ..core.di_container import get_container


def track_command_performance(command_name: str = None):
    """Decorator to automatically track command response times.
    
    Args:
        command_name: Optional custom command name (defaults to function name)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get command name
            cmd_name = command_name or func.__name__
            
            # Extract user ID from interaction if available
            user_id = None
            if args and hasattr(args[0], 'user'):
                user_id = args[0].user.id
            elif 'interaction' in kwargs and hasattr(kwargs['interaction'], 'user'):
                user_id = kwargs['interaction'].user.id
            
            # Record start time
            start_time = time.time()
            success = True
            error_message = None
            
            try:
                # Execute the command
                result = await func(*args, **kwargs)
                return result
                
            except Exception as e:
                success = False
                error_message = str(e)
                raise
                
            finally:
                # Record metrics
                end_time = time.time()
                
                try:
                    container = get_container()
                    if container:
                        performance_monitor = container.get("performance_monitor")
                        if performance_monitor:
                            await performance_monitor.record_command_metric(
                                command_name=cmd_name,
                                user_id=user_id or 0,
                                start_time=start_time,
                                end_time=end_time,
                                success=success,
                                error_message=error_message
                            )
                except Exception:
                    pass  # Don't let monitoring failures affect the command
        
        return wrapper
    return decorator


def track_database_performance(query_type: str = None):
    """Decorator to automatically track database query performance.
    
    Args:
        query_type: Type of database operation (SELECT, INSERT, UPDATE, etc.)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Determine query type
            q_type = query_type or func.__name__
            
            # Create query hash for privacy (hash the query string if available)
            query_hash = "unknown"
            if args and isinstance(args[0], str):
                query_hash = hashlib.md5(args[0].encode()).hexdigest()[:16]
            
            start_time = time.time()
            success = True
            error_message = None
            rows_affected = 0
            
            try:
                # Execute the database operation
                result = await func(*args, **kwargs)
                
                # Try to extract rows affected from result
                if hasattr(result, 'rowcount'):
                    rows_affected = result.rowcount
                elif isinstance(result, (list, tuple)):
                    rows_affected = len(result)
                
                return result
                
            except Exception as e:
                success = False
                error_message = str(e)
                raise
                
            finally:
                # Record metrics
                execution_time = time.time() - start_time
                
                try:
                    container = get_container()
                    if container:
                        performance_monitor = container.get("performance_monitor")
                        if performance_monitor:
                            await performance_monitor.record_database_metric(
                                query_type=q_type,
                                query_hash=query_hash,
                                execution_time=execution_time,
                                success=success,
                                error_message=error_message,
                                rows_affected=rows_affected
                            )
                except Exception:
                    pass  # Don't let monitoring failures affect the query
        
        return wrapper
    return decorator


class PerformanceContext:
    """Context manager for tracking custom performance metrics."""
    
    def __init__(self, operation_name: str, operation_type: str = "custom"):
        self.operation_name = operation_name
        self.operation_type = operation_type
        self.start_time = None
        
    async def __aenter__(self):
        self.start_time = time.time()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            execution_time = time.time() - self.start_time
            success = exc_type is None
            error_message = str(exc_val) if exc_val else None
            
            try:
                container = get_container()
                if container:
                    performance_monitor = container.get("performance_monitor")
                    if performance_monitor:
                        # Record as database metric for now (could be extended)
                        await performance_monitor.record_database_metric(
                            query_type=f"{self.operation_type}_{self.operation_name}",
                            query_hash=hashlib.md5(self.operation_name.encode()).hexdigest()[:16],
                            execution_time=execution_time,
                            success=success,
                            error_message=error_message
                        )
            except Exception:
                pass  # Don't let monitoring failures affect the operation


# Convenience function for manual performance tracking
async def track_performance(operation_name: str, operation_type: str = "custom"):
    """Create a performance tracking context manager.
    
    Usage:
        async with track_performance("audio_processing", "media"):
            # Your code here
            pass
    """
    return PerformanceContext(operation_name, operation_type)