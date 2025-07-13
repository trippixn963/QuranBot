# =============================================================================
# QuranBot - Discord API Health Monitor
# =============================================================================
# Comprehensive monitoring system for Discord API health and performance
# Tracks response times, rate limits, gateway connection, and error rates
# =============================================================================

import asyncio
import json
import time
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import statistics

import discord
from discord.ext import commands

from .tree_log import log_error_with_traceback, log_perfect_tree_section

# =============================================================================
# Configuration
# =============================================================================

# File paths
DATA_DIR = Path(__file__).parent.parent.parent / "data"
MONITOR_DATA_FILE = DATA_DIR / "discord_api_monitor.json"

# Monitoring settings
MAX_HISTORY_SIZE = 1000  # Maximum number of metrics to keep in memory
SAVE_INTERVAL = 30  # Save metrics to disk every 30 seconds
CLEANUP_INTERVAL = 3600  # Clean old data every hour
MAX_AGE_HOURS = 24  # Keep data for 24 hours

# Rate limit warning thresholds
RATE_LIMIT_WARNING_THRESHOLD = 0.8  # Warn when 80% of rate limit used
RATE_LIMIT_CRITICAL_THRESHOLD = 0.95  # Critical when 95% of rate limit used

# Response time thresholds (in seconds)
RESPONSE_TIME_WARNING = 2.0  # Warn if response time > 2 seconds
RESPONSE_TIME_CRITICAL = 5.0  # Critical if response time > 5 seconds

# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class APICallMetric:
    """Individual API call metric"""
    timestamp: float
    endpoint: str
    method: str
    response_time: float
    status_code: int
    rate_limit_remaining: Optional[int] = None
    rate_limit_limit: Optional[int] = None
    rate_limit_reset_after: Optional[float] = None
    error_message: Optional[str] = None

@dataclass
class GatewayMetric:
    """Gateway connection metric"""
    timestamp: float
    latency: Optional[float]
    is_connected: bool
    reconnect_count: int
    event_type: str  # 'heartbeat', 'connect', 'disconnect', 'reconnect'

@dataclass
class DiscordAPIHealth:
    """Overall Discord API health status"""
    timestamp: float
    is_healthy: bool
    avg_response_time: float
    rate_limit_usage: float  # Percentage of rate limit used
    gateway_latency: Optional[float]
    gateway_connected: bool
    total_api_calls: int
    error_rate: float  # Percentage of failed calls
    status: str  # 'healthy', 'warning', 'critical'

# =============================================================================
# Discord API Monitor
# =============================================================================

class DiscordAPIMonitor:
    """
    Comprehensive Discord API health monitoring system.
    
    Tracks:
    - API response times and success rates
    - Rate limit usage and warnings
    - Gateway connection health and latency
    - Error rates and patterns
    - Overall system health scoring
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.api_metrics: deque[APICallMetric] = deque(maxlen=MAX_HISTORY_SIZE)
        self.gateway_metrics: deque[GatewayMetric] = deque(maxlen=MAX_HISTORY_SIZE)
        self.health_history: deque[DiscordAPIHealth] = deque(maxlen=MAX_HISTORY_SIZE)
        
        # Rate limiting tracking
        self.rate_limit_buckets: Dict[str, Dict] = defaultdict(dict)
        self.last_rate_limit_warning = {}
        
        # Connection tracking
        self.connection_start_time = time.time()
        self.reconnect_count = 0
        self.last_heartbeat = None
        
        # Background tasks
        self.save_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.total_api_calls = 0
        self.total_errors = 0
        
        # Setup data directory
        DATA_DIR.mkdir(exist_ok=True)
        
        # Load existing data
        self._load_data()
        
        # Start background tasks
        self._start_background_tasks()
        
        # Hook into Discord.py events
        self._setup_discord_hooks()
    
    def _setup_discord_hooks(self):
        """Setup hooks into Discord.py for automatic monitoring"""
        
        # Hook into HTTP requests
        original_request = self.bot.http.request
        
        async def monitored_request(route, **kwargs):
            start_time = time.time()
            error_message = None
            status_code = 200
            rate_limit_remaining = None
            rate_limit_limit = None
            rate_limit_reset_after = None
            
            try:
                response = await original_request(route, **kwargs)
                
                # Extract rate limit info from response headers if available
                if hasattr(response, 'headers'):
                    rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
                    rate_limit_limit = response.headers.get('X-RateLimit-Limit')
                    rate_limit_reset_after = response.headers.get('X-RateLimit-Reset-After')
                    
                    if rate_limit_remaining:
                        rate_limit_remaining = int(rate_limit_remaining)
                    if rate_limit_limit:
                        rate_limit_limit = int(rate_limit_limit)
                    if rate_limit_reset_after:
                        rate_limit_reset_after = float(rate_limit_reset_after)
                
                return response
                
            except discord.HTTPException as e:
                status_code = e.status
                error_message = str(e)
                self.total_errors += 1
                raise
            except Exception as e:
                status_code = 500
                error_message = str(e)
                self.total_errors += 1
                raise
            finally:
                response_time = time.time() - start_time
                self.total_api_calls += 1
                
                # Record the API call metric
                metric = APICallMetric(
                    timestamp=time.time(),
                    endpoint=route.path,
                    method=route.method,
                    response_time=response_time,
                    status_code=status_code,
                    rate_limit_remaining=rate_limit_remaining,
                    rate_limit_limit=rate_limit_limit,
                    rate_limit_reset_after=rate_limit_reset_after,
                    error_message=error_message
                )
                
                self.api_metrics.append(metric)
                self._check_rate_limits(metric)
                self._update_health_status()
        
        # Replace the original request method
        self.bot.http.request = monitored_request
        
        # Setup gateway event hooks
        @self.bot.event
        async def on_connect():
            self._record_gateway_event('connect', self.bot.latency, True)
        
        @self.bot.event
        async def on_disconnect():
            self._record_gateway_event('disconnect', None, False)
        
        @self.bot.event
        async def on_resumed():
            self.reconnect_count += 1
            self._record_gateway_event('reconnect', self.bot.latency, True)
    
    def _record_gateway_event(self, event_type: str, latency: Optional[float], connected: bool):
        """Record a gateway event"""
        metric = GatewayMetric(
            timestamp=time.time(),
            latency=latency,
            is_connected=connected,
            reconnect_count=self.reconnect_count,
            event_type=event_type
        )
        
        self.gateway_metrics.append(metric)
        self.last_heartbeat = time.time() if event_type in ['connect', 'heartbeat'] else self.last_heartbeat
        self._update_health_status()
    
    def record_heartbeat(self, latency: float):
        """Record a heartbeat event (call this from bot's heartbeat monitoring)"""
        self._record_gateway_event('heartbeat', latency, True)
    
    def _check_rate_limits(self, metric: APICallMetric):
        """Check for rate limit warnings"""
        if metric.rate_limit_remaining is not None and metric.rate_limit_limit is not None:
            usage = 1.0 - (metric.rate_limit_remaining / metric.rate_limit_limit)
            bucket_key = f"{metric.method}:{metric.endpoint}"
            
            # Update rate limit tracking
            self.rate_limit_buckets[bucket_key] = {
                'remaining': metric.rate_limit_remaining,
                'limit': metric.rate_limit_limit,
                'usage': usage,
                'reset_after': metric.rate_limit_reset_after,
                'last_updated': time.time()
            }
            
            # Check for warnings
            current_time = time.time()
            last_warning = self.last_rate_limit_warning.get(bucket_key, 0)
            
            if usage >= RATE_LIMIT_CRITICAL_THRESHOLD and current_time - last_warning > 300:
                log_perfect_tree_section(
                    "Discord API - Critical Rate Limit",
                    [
                        ("endpoint", bucket_key),
                        ("usage", f"{usage:.1%}"),
                        ("remaining", str(metric.rate_limit_remaining)),
                        ("limit", str(metric.rate_limit_limit)),
                        ("status", "🚨 CRITICAL"),
                    ],
                    "🚨",
                )
                self.last_rate_limit_warning[bucket_key] = current_time
                
            elif usage >= RATE_LIMIT_WARNING_THRESHOLD and current_time - last_warning > 600:
                log_perfect_tree_section(
                    "Discord API - Rate Limit Warning",
                    [
                        ("endpoint", bucket_key),
                        ("usage", f"{usage:.1%}"),
                        ("remaining", str(metric.rate_limit_remaining)),
                        ("limit", str(metric.rate_limit_limit)),
                        ("status", "⚠️ WARNING"),
                    ],
                    "⚠️",
                )
                self.last_rate_limit_warning[bucket_key] = current_time
    
    def _update_health_status(self):
        """Update overall health status"""
        current_time = time.time()
        
        # Calculate metrics from recent data (last 5 minutes)
        recent_cutoff = current_time - 300
        recent_api_calls = [m for m in self.api_metrics if m.timestamp > recent_cutoff]
        recent_gateway_events = [m for m in self.gateway_metrics if m.timestamp > recent_cutoff]
        
        # Calculate average response time
        if recent_api_calls:
            avg_response_time = statistics.mean([m.response_time for m in recent_api_calls])
            error_rate = len([m for m in recent_api_calls if m.status_code >= 400]) / len(recent_api_calls)
        else:
            avg_response_time = 0.0
            error_rate = 0.0
        
        # Calculate rate limit usage
        current_rate_limit_usage = 0.0
        if self.rate_limit_buckets:
            usages = [bucket['usage'] for bucket in self.rate_limit_buckets.values() 
                     if current_time - bucket['last_updated'] < 60]
            if usages:
                current_rate_limit_usage = max(usages)
        
        # Get gateway status
        gateway_connected = self.bot.is_ready()
        gateway_latency = self.bot.latency if gateway_connected else None
        
        # Determine overall status
        is_healthy = True
        status = "healthy"
        
        if (avg_response_time > RESPONSE_TIME_CRITICAL or 
            error_rate > 0.1 or 
            current_rate_limit_usage > RATE_LIMIT_CRITICAL_THRESHOLD or
            not gateway_connected):
            is_healthy = False
            status = "critical"
        elif (avg_response_time > RESPONSE_TIME_WARNING or 
              error_rate > 0.05 or 
              current_rate_limit_usage > RATE_LIMIT_WARNING_THRESHOLD or
              (gateway_latency and gateway_latency > 0.5)):
            status = "warning"
        
        # Create health record
        health = DiscordAPIHealth(
            timestamp=current_time,
            is_healthy=is_healthy,
            avg_response_time=avg_response_time,
            rate_limit_usage=current_rate_limit_usage,
            gateway_latency=gateway_latency,
            gateway_connected=gateway_connected,
            total_api_calls=self.total_api_calls,
            error_rate=error_rate,
            status=status
        )
        
        self.health_history.append(health)
    
    def get_current_health(self) -> Dict[str, Any]:
        """Get current health status"""
        if not self.health_history:
            self._update_health_status()
        
        if self.health_history:
            latest = self.health_history[-1]
            return asdict(latest)
        
        return {
            "timestamp": time.time(),
            "is_healthy": False,
            "avg_response_time": 0.0,
            "rate_limit_usage": 0.0,
            "gateway_latency": None,
            "gateway_connected": False,
            "total_api_calls": 0,
            "error_rate": 0.0,
            "status": "unknown"
        }
    
    def get_health_history(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get health history for the specified number of hours"""
        cutoff = time.time() - (hours * 3600)
        return [asdict(h) for h in self.health_history if h.timestamp > cutoff]
    
    def get_api_metrics_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get API metrics summary"""
        cutoff = time.time() - (hours * 3600)
        recent_metrics = [m for m in self.api_metrics if m.timestamp > cutoff]
        
        if not recent_metrics:
            return {
                "total_calls": 0,
                "avg_response_time": 0.0,
                "error_rate": 0.0,
                "slowest_endpoint": None,
                "most_used_endpoint": None,
                "rate_limit_status": {}
            }
        
        # Calculate statistics
        response_times = [m.response_time for m in recent_metrics]
        error_count = len([m for m in recent_metrics if m.status_code >= 400])
        
        # Find slowest and most used endpoints
        endpoint_times = defaultdict(list)
        endpoint_counts = defaultdict(int)
        
        for metric in recent_metrics:
            endpoint_times[metric.endpoint].append(metric.response_time)
            endpoint_counts[metric.endpoint] += 1
        
        slowest_endpoint = None
        if endpoint_times:
            avg_times = {ep: statistics.mean(times) for ep, times in endpoint_times.items()}
            slowest_endpoint = max(avg_times, key=avg_times.get)
        
        most_used_endpoint = None
        if endpoint_counts:
            most_used_endpoint = max(endpoint_counts, key=endpoint_counts.get)
        
        return {
            "total_calls": len(recent_metrics),
            "avg_response_time": statistics.mean(response_times) if response_times else 0.0,
            "error_rate": error_count / len(recent_metrics) if recent_metrics else 0.0,
            "slowest_endpoint": slowest_endpoint,
            "most_used_endpoint": most_used_endpoint,
            "rate_limit_status": dict(self.rate_limit_buckets)
        }
    
    def get_gateway_status(self) -> Dict[str, Any]:
        """Get gateway connection status"""
        return {
            "connected": self.bot.is_ready(),
            "latency": self.bot.latency if self.bot.is_ready() else None,
            "reconnect_count": self.reconnect_count,
            "uptime_seconds": time.time() - self.connection_start_time,
            "last_heartbeat": self.last_heartbeat
        }
    
    def _start_background_tasks(self):
        """Start background monitoring tasks"""
        self.save_task = asyncio.create_task(self._save_data_loop())
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def _save_data_loop(self):
        """Periodically save data to disk"""
        while True:
            try:
                await asyncio.sleep(SAVE_INTERVAL)
                self._save_data()
            except Exception as e:
                log_error_with_traceback("Error saving Discord API monitor data", e)
    
    async def _cleanup_loop(self):
        """Periodically clean up old data"""
        while True:
            try:
                await asyncio.sleep(CLEANUP_INTERVAL)
                self._cleanup_old_data()
            except Exception as e:
                log_error_with_traceback("Error cleaning up Discord API monitor data", e)
    
    def _save_data(self):
        """Save current data to disk"""
        try:
            data = {
                "health_history": [asdict(h) for h in list(self.health_history)[-100:]],  # Keep last 100
                "api_metrics": [asdict(m) for m in list(self.api_metrics)[-500:]],  # Keep last 500
                "gateway_metrics": [asdict(m) for m in list(self.gateway_metrics)[-100:]],  # Keep last 100
                "rate_limit_buckets": dict(self.rate_limit_buckets),
                "stats": {
                    "total_api_calls": self.total_api_calls,
                    "total_errors": self.total_errors,
                    "reconnect_count": self.reconnect_count,
                    "connection_start_time": self.connection_start_time
                }
            }
            
            # Atomic write
            temp_file = MONITOR_DATA_FILE.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)
            temp_file.replace(MONITOR_DATA_FILE)
            
        except Exception as e:
            log_error_with_traceback("Error saving Discord API monitor data", e)
    
    def _load_data(self):
        """Load existing data from disk"""
        try:
            if MONITOR_DATA_FILE.exists():
                with open(MONITOR_DATA_FILE, 'r') as f:
                    data = json.load(f)
                
                # Load health history
                if 'health_history' in data:
                    for h_data in data['health_history']:
                        health = DiscordAPIHealth(**h_data)
                        self.health_history.append(health)
                
                # Load API metrics
                if 'api_metrics' in data:
                    for m_data in data['api_metrics']:
                        metric = APICallMetric(**m_data)
                        self.api_metrics.append(metric)
                
                # Load gateway metrics
                if 'gateway_metrics' in data:
                    for g_data in data['gateway_metrics']:
                        gateway = GatewayMetric(**g_data)
                        self.gateway_metrics.append(gateway)
                
                # Load rate limit buckets
                if 'rate_limit_buckets' in data:
                    self.rate_limit_buckets.update(data['rate_limit_buckets'])
                
                # Load stats
                if 'stats' in data:
                    stats = data['stats']
                    self.total_api_calls = stats.get('total_api_calls', 0)
                    self.total_errors = stats.get('total_errors', 0)
                    self.reconnect_count = stats.get('reconnect_count', 0)
                    self.connection_start_time = stats.get('connection_start_time', time.time())
                
        except Exception as e:
            log_error_with_traceback("Error loading Discord API monitor data", e)
    
    def _cleanup_old_data(self):
        """Remove old data beyond retention period"""
        cutoff = time.time() - (MAX_AGE_HOURS * 3600)
        
        # Clean health history
        self.health_history = deque(
            [h for h in self.health_history if h.timestamp > cutoff],
            maxlen=MAX_HISTORY_SIZE
        )
        
        # Clean API metrics
        self.api_metrics = deque(
            [m for m in self.api_metrics if m.timestamp > cutoff],
            maxlen=MAX_HISTORY_SIZE
        )
        
        # Clean gateway metrics
        self.gateway_metrics = deque(
            [g for g in self.gateway_metrics if g.timestamp > cutoff],
            maxlen=MAX_HISTORY_SIZE
        )
        
        # Clean rate limit buckets
        current_time = time.time()
        expired_buckets = [
            key for key, bucket in self.rate_limit_buckets.items()
            if current_time - bucket.get('last_updated', 0) > 3600
        ]
        for key in expired_buckets:
            del self.rate_limit_buckets[key]
    
    def stop(self):
        """Stop monitoring and cleanup"""
        if self.save_task:
            self.save_task.cancel()
        if self.cleanup_task:
            self.cleanup_task.cancel()
        
        # Final save
        self._save_data()

# =============================================================================
# Global Monitor Instance
# =============================================================================

_discord_monitor: Optional[DiscordAPIMonitor] = None

def initialize_discord_monitor(bot: commands.Bot) -> DiscordAPIMonitor:
    """Initialize the global Discord API monitor"""
    global _discord_monitor
    _discord_monitor = DiscordAPIMonitor(bot)
    return _discord_monitor

def get_discord_monitor() -> Optional[DiscordAPIMonitor]:
    """Get the global Discord API monitor instance"""
    return _discord_monitor 