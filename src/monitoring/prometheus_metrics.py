# =============================================================================
# QuranBot - Prometheus Metrics Collection and Exposition
# =============================================================================
# This module provides comprehensive Prometheus metrics for monitoring QuranBot
# performance, usage patterns, and system health in production environments.
# =============================================================================

"""
"""

import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import logging
from collections import defaultdict, deque

try:
    from prometheus_client import (
        Counter, Histogram, Gauge, Summary, Info,
        CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST,
        multiprocess, values
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

from ..core.logger import StructuredLogger


class MetricType(Enum):
    """Types of metrics collected by the monitoring system."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"
    INFO = "info"


@dataclass
class MetricDefinition:
    """Definition of a Prometheus metric with metadata."""
    name: str
    metric_type: MetricType
    description: str
    labels: List[str] = field(default_factory=list)
    buckets: Optional[List[float]] = None
    quantiles: Optional[Dict[float, float]] = None


class QuranBotMetrics:
    """
    Comprehensive Prometheus metrics collector for QuranBot.
    
    Provides monitoring capabilities for:
    - Audio playback statistics
    - User interaction patterns
    - System performance metrics
    - Discord API usage
    - Database operations
    - Cache performance
    - Error tracking
    """
    
    def __init__(self, logger: Optional[StructuredLogger] = None):
        """
        Initialize Prometheus metrics collector.
        
        Args:
            logger: Optional structured logger instance
            
        Raises:
            ImportError: If prometheus_client is not installed
        """
        if not PROMETHEUS_AVAILABLE:
            raise ImportError(
                "prometheus_client not installed. Run: pip install prometheus-client"
            )
        
        self._logger = logger or StructuredLogger("prometheus_metrics")
        self._registry = CollectorRegistry()
        self._metrics: Dict[str, Any] = {}
        self._start_time = time.time()
        
        # Initialize all metrics
        self._initialize_metrics()
        
        # Track metric updates
        self._last_update = {}
        self._update_intervals = defaultdict(lambda: deque(maxlen=100))
        
    def _initialize_metrics(self) -> None:
        """Initialize all Prometheus metrics with proper labels and types."""
        
        # === Bot Lifecycle Metrics ===
        self._metrics["bot_start_time"] = Gauge(
            "quranbot_start_time_seconds",
            "Unix timestamp when the bot started",
            registry=self._registry
        )
        self._metrics["bot_start_time"].set(self._start_time)
        
        self._metrics["bot_uptime"] = Gauge(
            "quranbot_uptime_seconds",
            "Bot uptime in seconds",
            registry=self._registry
        )
        
        self._metrics["bot_info"] = Info(
            "quranbot_info",
            "Bot version and configuration information",
            registry=self._registry
        )
        
        # === Audio Playback Metrics ===
        self._metrics["audio_sessions_total"] = Counter(
            "quranbot_audio_sessions_total",
            "Total number of audio playback sessions",
            ["reciter", "surah", "status"],
            registry=self._registry
        )
        
        self._metrics["audio_playback_duration"] = Histogram(
            "quranbot_audio_playback_duration_seconds",
            "Duration of audio playback sessions",
            ["reciter", "surah"],
            buckets=[30, 60, 300, 900, 1800, 3600, 7200, float("inf")],
            registry=self._registry
        )
        
        self._metrics["audio_listeners_current"] = Gauge(
            "quranbot_audio_listeners_current",
            "Current number of active listeners",
            ["guild_id"],
            registry=self._registry
        )
        
        self._metrics["audio_skip_events"] = Counter(
            "quranbot_audio_skip_events_total",
            "Total number of skip events",
            ["direction", "user_id", "guild_id"],
            registry=self._registry
        )
        
        # === User Interaction Metrics ===
        self._metrics["commands_total"] = Counter(
            "quranbot_commands_total",
            "Total number of commands executed",
            ["command", "user_id", "guild_id", "status"],
            registry=self._registry
        )
        
        self._metrics["command_duration"] = Histogram(
            "quranbot_command_duration_seconds",
            "Time taken to execute commands",
            ["command"],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, float("inf")],
            registry=self._registry
        )
        
        self._metrics["user_sessions"] = Counter(
            "quranbot_user_sessions_total",
            "Total user sessions by type",
            ["user_id", "guild_id", "session_type"],
            registry=self._registry
        )
        
        # === Quiz System Metrics ===
        self._metrics["quiz_questions_total"] = Counter(
            "quranbot_quiz_questions_total",
            "Total quiz questions asked",
            ["category", "difficulty"],
            registry=self._registry
        )
        
        self._metrics["quiz_answers"] = Counter(
            "quranbot_quiz_answers_total",
            "Quiz answers by correctness",
            ["user_id", "correct", "difficulty"],
            registry=self._registry
        )
        
        self._metrics["quiz_response_time"] = Histogram(
            "quranbot_quiz_response_time_seconds",
            "Time taken to answer quiz questions",
            ["difficulty"],
            buckets=[1, 5, 10, 15, 30, 60, float("inf")],
            registry=self._registry
        )
        
        # === System Performance Metrics ===
        self._metrics["system_cpu_usage"] = Gauge(
            "quranbot_system_cpu_usage_percent",
            "CPU usage percentage",
            registry=self._registry
        )
        
        self._metrics["system_memory_usage"] = Gauge(
            "quranbot_system_memory_usage_bytes",
            "Memory usage in bytes",
            ["type"],  # rss, vms, shared
            registry=self._registry
        )
        
        self._metrics["system_disk_usage"] = Gauge(
            "quranbot_system_disk_usage_bytes",
            "Disk usage in bytes",
            ["path", "type"],  # used, free, total
            registry=self._registry
        )
        
        # === Database Metrics ===
        self._metrics["database_queries_total"] = Counter(
            "quranbot_database_queries_total",
            "Total database queries executed",
            ["operation", "table", "status"],
            registry=self._registry
        )
        
        self._metrics["database_query_duration"] = Histogram(
            "quranbot_database_query_duration_seconds",
            "Database query execution time",
            ["operation", "table"],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, float("inf")],
            registry=self._registry
        )
        
        self._metrics["database_connections"] = Gauge(
            "quranbot_database_connections_current",
            "Current number of database connections",
            ["state"],  # active, idle
            registry=self._registry
        )
        
        # === Cache Performance ===
        self._metrics["cache_operations_total"] = Counter(
            "quranbot_cache_operations_total",
            "Total cache operations",
            ["operation", "cache_type", "result"],  # hit, miss, set, delete
            registry=self._registry
        )
        
        self._metrics["cache_size"] = Gauge(
            "quranbot_cache_size_entries",
            "Number of entries in cache",
            ["cache_type"],
            registry=self._registry
        )
        
        self._metrics["cache_memory_usage"] = Gauge(
            "quranbot_cache_memory_usage_bytes",
            "Memory used by cache",
            ["cache_type"],
            registry=self._registry
        )
        
        # === Discord API Metrics ===
        self._metrics["discord_api_requests"] = Counter(
            "quranbot_discord_api_requests_total",
            "Discord API requests made",
            ["endpoint", "method", "status_code"],
            registry=self._registry
        )
        
        self._metrics["discord_api_latency"] = Histogram(
            "quranbot_discord_api_latency_seconds",
            "Discord API request latency",
            ["endpoint"],
            buckets=[0.1, 0.2, 0.5, 1.0, 2.0, 5.0, float("inf")],
            registry=self._registry
        )
        
        self._metrics["discord_events"] = Counter(
            "quranbot_discord_events_total",
            "Discord events received",
            ["event_type"],
            registry=self._registry
        )
        
        # === Webhook Metrics ===
        self._metrics["webhook_messages_sent"] = Counter(
            "quranbot_webhook_messages_sent_total",
            "Webhook messages sent",
            ["channel", "level", "status"],
            registry=self._registry
        )
        
        self._metrics["webhook_send_duration"] = Histogram(
            "quranbot_webhook_send_duration_seconds",
            "Time to send webhook messages",
            ["channel"],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, float("inf")],
            registry=self._registry
        )
        
        # === Error Tracking ===
        self._metrics["errors_total"] = Counter(
            "quranbot_errors_total",
            "Total errors encountered",
            ["error_type", "module", "severity"],
            registry=self._registry
        )
        
        self._metrics["exceptions_total"] = Counter(
            "quranbot_exceptions_total",
            "Total exceptions raised",
            ["exception_type", "module"],
            registry=self._registry
        )
        
        await self._logger.info("Prometheus metrics initialized", context={
            "total_metrics": len(self._metrics),
            "registry": "custom"
        })
    
    # === Metric Update Methods ===
    
    def record_audio_session_start(
        self, 
        reciter: str, 
        surah: str, 
        guild_id: str,
        listeners: int = 1
    ) -> None:
        """Record the start of an audio playback session."""
        self._metrics["audio_sessions_total"].labels(
            reciter=reciter, surah=surah, status="started"
        ).inc()
        
        self._metrics["audio_listeners_current"].labels(
            guild_id=guild_id
        ).set(listeners)
    
    def record_audio_session_end(
        self, 
        reciter: str, 
        surah: str, 
        duration: float,
        reason: str = "completed"
    ) -> None:
        """Record the end of an audio playback session."""
        self._metrics["audio_sessions_total"].labels(
            reciter=reciter, surah=surah, status=reason
        ).inc()
        
        self._metrics["audio_playback_duration"].labels(
            reciter=reciter, surah=surah
        ).observe(duration)
    
    def record_command_execution(
        self, 
        command: str, 
        user_id: str, 
        guild_id: str,
        duration: float,
        success: bool = True
    ) -> None:
        """Record command execution metrics."""
        status = "success" if success else "error"
        
        self._metrics["commands_total"].labels(
            command=command, user_id=user_id, guild_id=guild_id, status=status
        ).inc()
        
        self._metrics["command_duration"].labels(command=command).observe(duration)
    
    def record_quiz_question(
        self, 
        category: str, 
        difficulty: str,
        user_id: str,
        correct: bool,
        response_time: float
    ) -> None:
        """Record quiz interaction metrics."""
        self._metrics["quiz_questions_total"].labels(
            category=category, difficulty=difficulty
        ).inc()
        
        self._metrics["quiz_answers"].labels(
            user_id=user_id, correct=str(correct).lower(), difficulty=difficulty
        ).inc()
        
        self._metrics["quiz_response_time"].labels(difficulty=difficulty).observe(response_time)
    
    def record_database_query(
        self, 
        operation: str, 
        table: str, 
        duration: float,
        success: bool = True
    ) -> None:
        """Record database operation metrics."""
        status = "success" if success else "error"
        
        self._metrics["database_queries_total"].labels(
            operation=operation, table=table, status=status
        ).inc()
        
        self._metrics["database_query_duration"].labels(
            operation=operation, table=table
        ).observe(duration)
    
    def record_cache_operation(
        self, 
        operation: str, 
        cache_type: str, 
        hit: Optional[bool] = None
    ) -> None:
        """Record cache operation metrics."""
        if hit is not None:
            result = "hit" if hit else "miss"
        else:
            result = operation
        
        self._metrics["cache_operations_total"].labels(
            operation=operation, cache_type=cache_type, result=result
        ).inc()
    
    def update_cache_stats(self, cache_type: str, size: int, memory_bytes: int) -> None:
        """Update cache size and memory usage."""
        self._metrics["cache_size"].labels(cache_type=cache_type).set(size)
        self._metrics["cache_memory_usage"].labels(cache_type=cache_type).set(memory_bytes)
    
    def record_discord_api_request(
        self, 
        endpoint: str, 
        method: str, 
        status_code: int,
        latency: float
    ) -> None:
        """Record Discord API request metrics."""
        self._metrics["discord_api_requests"].labels(
            endpoint=endpoint, method=method, status_code=str(status_code)
        ).inc()
        
        self._metrics["discord_api_latency"].labels(endpoint=endpoint).observe(latency)
    
    def record_discord_event(self, event_type: str) -> None:
        """Record Discord event reception."""
        self._metrics["discord_events"].labels(event_type=event_type).inc()
    
    def record_webhook_message(
        self, 
        channel: str, 
        level: str, 
        duration: float,
        success: bool = True
    ) -> None:
        """Record webhook message sending metrics."""
        status = "success" if success else "error"
        
        self._metrics["webhook_messages_sent"].labels(
            channel=channel, level=level, status=status
        ).inc()
        
        self._metrics["webhook_send_duration"].labels(channel=channel).observe(duration)
    
    def record_error(
        self, 
        error_type: str, 
        module: str, 
        severity: str = "error"
    ) -> None:
        """Record error occurrence."""
        self._metrics["errors_total"].labels(
            error_type=error_type, module=module, severity=severity
        ).inc()
    
    def record_exception(self, exception_type: str, module: str) -> None:
        """Record exception occurrence."""
        self._metrics["exceptions_total"].labels(
            exception_type=exception_type, module=module
        ).inc()
    
    def update_system_metrics(
        self, 
        cpu_percent: float,
        memory_rss: int,
        memory_vms: int,
        disk_stats: Dict[str, Dict[str, int]]
    ) -> None:
        """Update system performance metrics."""
        self._metrics["system_cpu_usage"].set(cpu_percent)
        self._metrics["system_memory_usage"].labels(type="rss").set(memory_rss)
        self._metrics["system_memory_usage"].labels(type="vms").set(memory_vms)
        
        for path, stats in disk_stats.items():
            for stat_type, value in stats.items():
                self._metrics["system_disk_usage"].labels(
                    path=path, type=stat_type
                ).set(value)
    
    def update_bot_info(self, version: str, environment: str, **kwargs) -> None:
        """Update bot information metrics."""
        info_dict = {
            "version": version,
            "environment": environment,
            **kwargs
        }
        self._metrics["bot_info"].info(info_dict)
    
    def update_uptime(self) -> None:
        """Update bot uptime metric."""
        uptime = time.time() - self._start_time
        self._metrics["bot_uptime"].set(uptime)
    
    def get_metrics_text(self) -> str:
        """
        Generate Prometheus metrics in text format.
        
        Returns:
            Prometheus metrics formatted as text
        """
        self.update_uptime()
        return generate_latest(self._registry).decode("utf-8")
    
    def get_metrics_content_type(self) -> str:
        """
        Get the content type for Prometheus metrics.
        
        Returns:
            Content type string for HTTP responses
        """
        return CONTENT_TYPE_LATEST
    
    async def collect_and_expose_metrics(self) -> Dict[str, Any]:
        """
        Collect current metrics for JSON API exposure.
        
        Returns:
            Dictionary containing current metric values
        """
        current_time = time.time()
        uptime = current_time - self._start_time
        
        metrics_summary = {
            "timestamp": current_time,
            "uptime_seconds": uptime,
            "metrics_count": len(self._metrics),
            "collection_interval": 15.0,  # Default collection interval
        }
        
        # Add sample values for key metrics
        try:
            # Note: Getting current values from Prometheus metrics requires
            # accessing internal state which varies by metric type
            await self._logger.debug("Metrics collection completed", context={
                "metrics_count": len(self._metrics),
                "uptime_seconds": uptime
            })
        except Exception as e:
            await self._logger.error("Error collecting metrics", context={
                "error": str(e)
            })
        
        return metrics_summary


class MetricsServer:
    """
    HTTP server for exposing Prometheus metrics.
    
    Provides endpoints for:
    - /metrics - Prometheus format metrics
    - /health - Health check endpoint
    - /metrics/json - JSON format metrics summary
    """
    
    def __init__(self, metrics: QuranBotMetrics, port: int = 8000):
        """
        Initialize metrics HTTP server.
        
        Args:
            metrics: QuranBotMetrics instance
            port: Port to bind the server to
        """
        self.metrics = metrics
        self.port = port
        self._server = None
        self._logger = StructuredLogger("metrics_server")
    
    async def start_server(self) -> None:
        """Start the metrics HTTP server."""
        try:
            from aiohttp import web, web_runner
            
            app = web.Application()
            app.router.add_get("/metrics", self._metrics_handler)
            app.router.add_get("/health", self._health_handler)
            app.router.add_get("/metrics/json", self._json_metrics_handler)
            
            runner = web_runner.AppRunner(app)
            await runner.setup()
            
            site = web_runner.TCPSite(runner, "0.0.0.0", self.port)
            await site.start()
            
            await self._logger.info("Metrics server started", context={
                "port": self.port,
                "endpoints": ["/metrics", "/health", "/metrics/json"]
            })
            
        except ImportError:
            await self._logger.error("aiohttp not available for metrics server")
            raise
        except Exception as e:
            await self._logger.error("Error starting metrics server", context={
                "error": str(e),
                "port": self.port
            })
            raise
    
    async def _metrics_handler(self, request) -> "web.Response":
        """Handle /metrics endpoint requests."""
        from aiohttp import web
        
        try:
            metrics_text = self.metrics.get_metrics_text()
            return web.Response(
                text=metrics_text,
                content_type=self.metrics.get_metrics_content_type()
            )
        except Exception as e:
            await self._logger.error("Error serving metrics", context={"error": str(e)})
            return web.Response(text="Error generating metrics", status=500)
    
    async def _health_handler(self, request) -> "web.Response":
        """Handle /health endpoint requests."""
        from aiohttp import web
        
        health_data = {
            "status": "healthy",
            "timestamp": time.time(),
            "uptime_seconds": time.time() - self.metrics._start_time,
            "version": "1.0.0"
        }
        
        return web.json_response(health_data)
    
    async def _json_metrics_handler(self, request) -> "web.Response":
        """Handle /metrics/json endpoint requests."""
        from aiohttp import web
        
        try:
            metrics_data = await self.metrics.collect_and_expose_metrics()
            return web.json_response(metrics_data)
        except Exception as e:
            await self._logger.error("Error serving JSON metrics", context={"error": str(e)})
            return web.json_response({"error": "Failed to collect metrics"}, status=500)


# Convenience function for easy integration
def create_metrics_collector(logger: Optional[StructuredLogger] = None) -> QuranBotMetrics:
    """
    Create a QuranBotMetrics instance with error handling.
    
    Args:
        logger: Optional structured logger instance
        
    Returns:
        QuranBotMetrics instance or None if Prometheus is not available
    """
    try:
        return QuranBotMetrics(logger)
    except ImportError:
        if logger:
            asyncio.create_task(logger.warning(
                "Prometheus metrics disabled - prometheus_client not installed"
            ))
        return None