# =============================================================================
# QuranBot - Performance Metrics Monitor
# =============================================================================
# Monitors bot performance metrics including response times, memory usage,
# database query performance, and Discord API rate limits
# =============================================================================

import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import psutil
import time
from typing import Any, Dict, List, Optional

from ..core.logger import StructuredLogger
from ..core.webhook_logger import LogLevel


@dataclass
class CommandMetric:
    """Metrics for a single command execution."""
    command_name: str
    user_id: int
    start_time: float
    end_time: float
    response_time: float
    success: bool
    error_message: Optional[str] = None
    memory_before: float = 0.0
    memory_after: float = 0.0


@dataclass
class DatabaseMetric:
    """Metrics for a database query."""
    query_type: str
    query_hash: str  # Hash of query for privacy
    execution_time: float
    timestamp: float
    success: bool
    error_message: Optional[str] = None
    rows_affected: int = 0


@dataclass
class MemorySnapshot:
    """Memory usage snapshot."""
    timestamp: float
    rss_mb: float  # Resident Set Size
    vms_mb: float  # Virtual Memory Size
    percent: float
    available_mb: float


@dataclass
class APIRateLimit:
    """Discord API rate limit information."""
    endpoint: str
    remaining: int
    limit: int
    reset_after: float
    timestamp: float
    usage_percent: float


class PerformanceMonitor:
    """Monitor bot performance metrics and send webhook alerts."""
    
    def __init__(self, logger: StructuredLogger, webhook_router=None):
        self.logger = logger
        self.webhook_router = webhook_router
        self.monitoring = False
        self.monitor_task = None
        
        # Metrics storage (using deques for memory efficiency)
        self.command_metrics: deque[CommandMetric] = deque(maxlen=1000)
        self.database_metrics: deque[DatabaseMetric] = deque(maxlen=1000)
        self.memory_snapshots: deque[MemorySnapshot] = deque(maxlen=500)
        self.api_rate_limits: deque[APIRateLimit] = deque(maxlen=200)
        
        # Performance thresholds
        self.slow_command_threshold = 5.0  # seconds
        self.slow_query_threshold = 1.0    # seconds
        self.memory_leak_threshold = 50.0  # MB increase over 10 minutes
        self.high_api_usage_threshold = 80.0  # percentage
        
        # Alert cooldowns
        self.last_slow_command_alert = 0
        self.last_slow_query_alert = 0
        self.last_memory_leak_alert = 0
        self.last_api_usage_alert = 0
        self.alert_cooldown = 300  # 5 minutes
        
        # Process reference for memory monitoring
        self.process = psutil.Process()
    
    async def start_monitoring(self, interval_seconds: int = 30):
        """Start performance monitoring."""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.monitor_task = asyncio.create_task(self._monitor_loop(interval_seconds))
        await self.logger.info("Performance monitoring started")
    
    async def stop_monitoring(self):
        """Stop performance monitoring."""
        self.monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        await self.logger.info("Performance monitoring stopped")
    
    async def _monitor_loop(self, interval_seconds: int):
        """Main performance monitoring loop."""
        while self.monitoring:
            try:
                await self._take_memory_snapshot()
                await self._check_performance_alerts()
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                await self.logger.error("Error in performance monitoring loop", {"error": str(e)})
                await asyncio.sleep(interval_seconds)
    
    async def _take_memory_snapshot(self):
        """Take a memory usage snapshot."""
        try:
            memory_info = self.process.memory_info()
            system_memory = psutil.virtual_memory()
            
            snapshot = MemorySnapshot(
                timestamp=time.time(),
                rss_mb=memory_info.rss / (1024 * 1024),
                vms_mb=memory_info.vms / (1024 * 1024),
                percent=self.process.memory_percent(),
                available_mb=system_memory.available / (1024 * 1024)
            )
            
            self.memory_snapshots.append(snapshot)
            
        except Exception as e:
            await self.logger.error("Failed to take memory snapshot", {"error": str(e)})
    
    async def _check_performance_alerts(self):
        """Check for performance issues and send alerts."""
        current_time = time.time()
        
        # Check for memory leaks
        await self._check_memory_leak_alert(current_time)
        
        # Check for slow commands
        await self._check_slow_commands_alert(current_time)
        
        # Check for slow database queries
        await self._check_slow_queries_alert(current_time)
        
        # Check API rate limit usage
        await self._check_api_usage_alert(current_time)
    
    async def _check_memory_leak_alert(self, current_time: float):
        """Check for potential memory leaks."""
        if current_time - self.last_memory_leak_alert < self.alert_cooldown:
            return
            
        if len(self.memory_snapshots) < 20:  # Need enough data points
            return
        
        # Compare memory usage over last 10 minutes
        ten_minutes_ago = current_time - 600
        recent_snapshots = [s for s in self.memory_snapshots if s.timestamp > ten_minutes_ago]
        
        if len(recent_snapshots) < 10:
            return
        
        # Calculate memory trend
        oldest_memory = recent_snapshots[0].rss_mb
        newest_memory = recent_snapshots[-1].rss_mb
        memory_increase = newest_memory - oldest_memory
        
        if memory_increase > self.memory_leak_threshold:
            await self._send_memory_leak_alert(memory_increase, oldest_memory, newest_memory)
            self.last_memory_leak_alert = current_time
    
    async def _check_slow_commands_alert(self, current_time: float):
        """Check for slow command responses."""
        if current_time - self.last_slow_command_alert < self.alert_cooldown:
            return
        
        # Check last 10 commands for slow responses
        recent_commands = list(self.command_metrics)[-10:]
        slow_commands = [cmd for cmd in recent_commands if cmd.response_time > self.slow_command_threshold]
        
        if len(slow_commands) >= 3:  # 3 or more slow commands recently
            await self._send_slow_commands_alert(slow_commands)
            self.last_slow_command_alert = current_time
    
    async def _check_slow_queries_alert(self, current_time: float):
        """Check for slow database queries."""
        if current_time - self.last_slow_query_alert < self.alert_cooldown:
            return
        
        # Check last 20 queries for slow execution
        recent_queries = list(self.database_metrics)[-20:]
        slow_queries = [q for q in recent_queries if q.execution_time > self.slow_query_threshold]
        
        if len(slow_queries) >= 5:  # 5 or more slow queries recently
            await self._send_slow_queries_alert(slow_queries)
            self.last_slow_query_alert = current_time
    
    async def _check_api_usage_alert(self, current_time: float):
        """Check for high Discord API usage."""
        if current_time - self.last_api_usage_alert < self.alert_cooldown:
            return
        
        if not self.api_rate_limits:
            return
        
        # Check recent API usage
        recent_limits = [limit for limit in self.api_rate_limits if current_time - limit.timestamp < 60]
        if not recent_limits:
            return
        
        # Find highest usage percentage
        max_usage = max(limit.usage_percent for limit in recent_limits)
        
        if max_usage > self.high_api_usage_threshold:
            high_usage_limits = [limit for limit in recent_limits if limit.usage_percent > self.high_api_usage_threshold]
            await self._send_api_usage_alert(high_usage_limits, max_usage)
            self.last_api_usage_alert = current_time    # Ale
rt sending methods
    async def _send_memory_leak_alert(self, increase_mb: float, old_mb: float, new_mb: float):
        """Send memory leak alert."""
        if not self.webhook_router:
            return
        
        try:
            from ..core.webhook_logger import LogLevel
            
            context = {
                "Memory Increase": f"{increase_mb:.1f} MB",
                "Previous Memory": f"{old_mb:.1f} MB",
                "Current Memory": f"{new_mb:.1f} MB",
                "Time Period": "10 minutes",
                "Severity": "HIGH" if increase_mb > 100 else "MEDIUM",
                "Action Required": "Monitor for continued growth",
            }
            
            await self.webhook_router.route_event(
                event_type="memory_leak_detected",
                title="⚠️ Potential Memory Leak Detected",
                description=f"Memory usage increased by {increase_mb:.1f} MB in 10 minutes",
                level=LogLevel.WARNING,
                context=context
            )
            
        except Exception as e:
            await self.logger.error("Failed to send memory leak alert", {"error": str(e)})
    
    async def _send_slow_commands_alert(self, slow_commands: List[CommandMetric]):
        """Send slow commands alert."""
        if not self.webhook_router:
            return
        
        try:
            from ..core.webhook_logger import LogLevel
            
            avg_response_time = sum(cmd.response_time for cmd in slow_commands) / len(slow_commands)
            slowest_command = max(slow_commands, key=lambda x: x.response_time)
            
            context = {
                "Slow Commands Count": f"{len(slow_commands)} commands",
                "Average Response Time": f"{avg_response_time:.2f}s",
                "Slowest Command": slowest_command.command_name,
                "Slowest Time": f"{slowest_command.response_time:.2f}s",
                "Threshold": f"{self.slow_command_threshold}s",
                "Impact": "User experience degraded",
            }
            
            await self.webhook_router.route_event(
                event_type="slow_commands_detected",
                title="🐌 Slow Command Response Times",
                description=f"Multiple commands responding slowly (avg: {avg_response_time:.2f}s)",
                level=LogLevel.WARNING,
                context=context
            )
            
        except Exception as e:
            await self.logger.error("Failed to send slow commands alert", {"error": str(e)})
    
    async def _send_slow_queries_alert(self, slow_queries: List[DatabaseMetric]):
        """Send slow database queries alert."""
        if not self.webhook_router:
            return
        
        try:
            from ..core.webhook_logger import LogLevel
            
            avg_query_time = sum(q.execution_time for q in slow_queries) / len(slow_queries)
            slowest_query = max(slow_queries, key=lambda x: x.execution_time)
            
            context = {
                "Slow Queries Count": f"{len(slow_queries)} queries",
                "Average Query Time": f"{avg_query_time:.3f}s",
                "Slowest Query Type": slowest_query.query_type,
                "Slowest Time": f"{slowest_query.execution_time:.3f}s",
                "Threshold": f"{self.slow_query_threshold}s",
                "Impact": "Database performance degraded",
            }
            
            await self.webhook_router.route_event(
                event_type="slow_database_queries",
                title="🗄️ Slow Database Queries Detected",
                description=f"Multiple database queries executing slowly (avg: {avg_query_time:.3f}s)",
                level=LogLevel.WARNING,
                context=context
            )
            
        except Exception as e:
            await self.logger.error("Failed to send slow queries alert", {"error": str(e)})
    
    async def _send_api_usage_alert(self, high_usage_limits: List[APIRateLimit], max_usage: float):
        """Send Discord API high usage alert."""
        if not self.webhook_router:
            return
        
        try:
            from ..core.webhook_logger import LogLevel
            
            # Group by endpoint
            endpoint_usage = {}
            for limit in high_usage_limits:
                if limit.endpoint not in endpoint_usage:
                    endpoint_usage[limit.endpoint] = []
                endpoint_usage[limit.endpoint].append(limit)
            
            # Find most used endpoint
            most_used_endpoint = max(endpoint_usage.keys(), 
                                   key=lambda ep: max(l.usage_percent for l in endpoint_usage[ep]))
            
            context = {
                "Max API Usage": f"{max_usage:.1f}%",
                "High Usage Endpoints": f"{len(endpoint_usage)} endpoints",
                "Most Used Endpoint": most_used_endpoint,
                "Threshold": f"{self.high_api_usage_threshold}%",
                "Risk Level": "HIGH" if max_usage > 90 else "MEDIUM",
                "Action": "Monitor for rate limiting",
            }
            
            level = LogLevel.WARNING if max_usage < 90 else LogLevel.ERROR
            
            await self.webhook_router.route_event(
                event_type="high_api_usage",
                title="📡 High Discord API Usage",
                description=f"Discord API usage at {max_usage:.1f}% - approaching rate limits",
                level=level,
                context=context
            )
            
        except Exception as e:
            await self.logger.error("Failed to send API usage alert", {"error": str(e)})   
 # Public methods for recording metrics
    async def record_command_metric(self, command_name: str, user_id: int, start_time: float, 
                                   end_time: float, success: bool, error_message: str = None):
        """Record a command execution metric."""
        try:
            memory_info = self.process.memory_info()
            
            metric = CommandMetric(
                command_name=command_name,
                user_id=user_id,
                start_time=start_time,
                end_time=end_time,
                response_time=end_time - start_time,
                success=success,
                error_message=error_message,
                memory_after=memory_info.rss / (1024 * 1024)
            )
            
            self.command_metrics.append(metric)
            
            # Log slow commands immediately
            if metric.response_time > self.slow_command_threshold:
                await self.logger.warning(
                    f"Slow command detected: {command_name}",
                    {
                        "response_time": f"{metric.response_time:.2f}s",
                        "user_id": user_id,
                        "threshold": f"{self.slow_command_threshold}s"
                    }
                )
                
        except Exception as e:
            await self.logger.error("Failed to record command metric", {"error": str(e)})
    
    async def record_database_metric(self, query_type: str, query_hash: str, 
                                   execution_time: float, success: bool, 
                                   error_message: str = None, rows_affected: int = 0):
        """Record a database query metric."""
        try:
            metric = DatabaseMetric(
                query_type=query_type,
                query_hash=query_hash,
                execution_time=execution_time,
                timestamp=time.time(),
                success=success,
                error_message=error_message,
                rows_affected=rows_affected
            )
            
            self.database_metrics.append(metric)
            
            # Log slow queries immediately
            if execution_time > self.slow_query_threshold:
                await self.logger.warning(
                    f"Slow database query: {query_type}",
                    {
                        "execution_time": f"{execution_time:.3f}s",
                        "query_hash": query_hash[:16],
                        "threshold": f"{self.slow_query_threshold}s"
                    }
                )
                
        except Exception as e:
            await self.logger.error("Failed to record database metric", {"error": str(e)})
    
    async def record_api_rate_limit(self, endpoint: str, remaining: int, limit: int, reset_after: float):
        """Record Discord API rate limit information."""
        try:
            usage_percent = ((limit - remaining) / limit) * 100 if limit > 0 else 0
            
            rate_limit = APIRateLimit(
                endpoint=endpoint,
                remaining=remaining,
                limit=limit,
                reset_after=reset_after,
                timestamp=time.time(),
                usage_percent=usage_percent
            )
            
            self.api_rate_limits.append(rate_limit)
            
            # Log high API usage immediately
            if usage_percent > self.high_api_usage_threshold:
                await self.logger.warning(
                    f"High API usage: {endpoint}",
                    {
                        "usage_percent": f"{usage_percent:.1f}%",
                        "remaining": remaining,
                        "limit": limit,
                        "threshold": f"{self.high_api_usage_threshold}%"
                    }
                )
                
        except Exception as e:
            await self.logger.error("Failed to record API rate limit", {"error": str(e)})
    
    async def get_performance_summary(self) -> Dict[str, Any]:
        """Get current performance summary."""
        try:
            current_time = time.time()
            
            # Command performance (last hour)
            hour_ago = current_time - 3600
            recent_commands = [cmd for cmd in self.command_metrics if cmd.start_time > hour_ago]
            
            # Database performance (last hour)
            recent_queries = [q for q in self.database_metrics if q.timestamp > hour_ago]
            
            # Memory trend (last 30 minutes)
            thirty_min_ago = current_time - 1800
            recent_memory = [m for m in self.memory_snapshots if m.timestamp > thirty_min_ago]
            
            # API usage (last 10 minutes)
            ten_min_ago = current_time - 600
            recent_api = [api for api in self.api_rate_limits if api.timestamp > ten_min_ago]
            
            return {
                "commands": {
                    "total_count": len(recent_commands),
                    "avg_response_time": sum(cmd.response_time for cmd in recent_commands) / len(recent_commands) if recent_commands else 0,
                    "slow_commands": len([cmd for cmd in recent_commands if cmd.response_time > self.slow_command_threshold]),
                    "success_rate": (len([cmd for cmd in recent_commands if cmd.success]) / len(recent_commands) * 100) if recent_commands else 100,
                },
                "database": {
                    "total_queries": len(recent_queries),
                    "avg_query_time": sum(q.execution_time for q in recent_queries) / len(recent_queries) if recent_queries else 0,
                    "slow_queries": len([q for q in recent_queries if q.execution_time > self.slow_query_threshold]),
                    "success_rate": (len([q for q in recent_queries if q.success]) / len(recent_queries) * 100) if recent_queries else 100,
                },
                "memory": {
                    "current_mb": recent_memory[-1].rss_mb if recent_memory else 0,
                    "trend_mb": (recent_memory[-1].rss_mb - recent_memory[0].rss_mb) if len(recent_memory) > 1 else 0,
                    "percent_used": recent_memory[-1].percent if recent_memory else 0,
                },
                "api": {
                    "max_usage_percent": max(api.usage_percent for api in recent_api) if recent_api else 0,
                    "high_usage_endpoints": len([api for api in recent_api if api.usage_percent > self.high_api_usage_threshold]),
                    "total_requests": len(recent_api),
                }
            }
            
        except Exception as e:
            await self.logger.error("Failed to get performance summary", {"error": str(e)})
            return {}