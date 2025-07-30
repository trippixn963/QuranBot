# =============================================================================
# QuranBot - Performance Monitor
# =============================================================================
# Comprehensive performance monitoring and metrics collection service with
# real-time monitoring, alerting, performance analysis, and optimization recommendations.
# =============================================================================

import asyncio
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
import gc
import json
from pathlib import Path
import statistics
import threading
import time
import tracemalloc
from typing import Any

import psutil

from .di_container import DIContainer
from .structured_logger import StructuredLogger

# Try to import optional performance libraries
try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import matplotlib.pyplot as plt

    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


class MetricType(str, Enum):
    """Types of performance metrics"""

    COUNTER = "counter"  # Incrementing values
    GAUGE = "gauge"  # Point-in-time values
    HISTOGRAM = "histogram"  # Distribution of values
    TIMER = "timer"  # Duration measurements
    RATE = "rate"  # Rate of change


class AlertSeverity(str, Enum):
    """Alert severity levels"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MetricValue:
    """Represents a single metric measurement"""

    value: int | float
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    tags: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricSeries:
    """Time series of metric values"""

    name: str
    metric_type: MetricType
    values: deque = field(default_factory=lambda: deque(maxlen=1000))
    unit: str = field(default="")
    description: str = field(default="")

    def add_value(self, value: int | float, tags: dict[str, str] | None = None) -> None:
        """Add a value to the time series"""
        metric_value = MetricValue(value=value, tags=tags or {})
        self.values.append(metric_value)

    def get_latest(self) -> MetricValue | None:
        """Get the most recent value"""
        return self.values[-1] if self.values else None

    def get_average(self, window_seconds: int = 300) -> float:
        """Get average value over a time window"""
        cutoff_time = datetime.now(UTC) - timedelta(seconds=window_seconds)
        recent_values = [mv.value for mv in self.values if mv.timestamp > cutoff_time]
        return statistics.mean(recent_values) if recent_values else 0.0

    def get_percentile(self, percentile: float, window_seconds: int = 300) -> float:
        """Get percentile value over a time window"""
        cutoff_time = datetime.now(UTC) - timedelta(seconds=window_seconds)
        recent_values = [mv.value for mv in self.values if mv.timestamp > cutoff_time]
        if not recent_values:
            return 0.0

        if HAS_NUMPY:
            return np.percentile(recent_values, percentile)
        else:
            # Fallback implementation
            sorted_values = sorted(recent_values)
            k = (len(sorted_values) - 1) * percentile / 100
            f = int(k)
            c = k - f
            if f == len(sorted_values) - 1:
                return sorted_values[f]
            return sorted_values[f] * (1 - c) + sorted_values[f + 1] * c


@dataclass
class PerformanceAlert:
    """Performance alert configuration and state"""

    name: str
    metric_name: str
    condition: str  # e.g., "> 100", "< 0.5"
    severity: AlertSeverity
    description: str = field(default="")
    enabled: bool = field(default=True)
    cooldown_seconds: int = field(default=300)  # 5 minutes
    last_triggered: datetime | None = field(default=None)
    trigger_count: int = field(default=0)

    def should_trigger(self, value: float) -> bool:
        """Check if alert should trigger for given value"""
        if not self.enabled:
            return False

        # Check cooldown
        if (
            self.last_triggered
            and (datetime.now(UTC) - self.last_triggered).total_seconds()
            < self.cooldown_seconds
        ):
            return False

        # Evaluate condition
        try:
            return eval(f"{value} {self.condition}")
        except (ValueError, TypeError, NameError, SyntaxError):
            # Invalid condition or value, treat as not triggered
            return False

    def trigger(self) -> None:
        """Mark alert as triggered"""
        self.last_triggered = datetime.now(UTC)
        self.trigger_count += 1


@dataclass
class SystemMetrics:
    """System-level performance metrics"""

    cpu_percent: float = field(default=0.0)
    memory_percent: float = field(default=0.0)
    memory_rss_mb: float = field(default=0.0)
    memory_vms_mb: float = field(default=0.0)
    disk_io_read_mb: float = field(default=0.0)
    disk_io_write_mb: float = field(default=0.0)
    network_sent_mb: float = field(default=0.0)
    network_recv_mb: float = field(default=0.0)
    open_file_descriptors: int = field(default=0)
    thread_count: int = field(default=0)
    gc_collections: int = field(default=0)
    gc_collected: int = field(default=0)
    gc_uncollectable: int = field(default=0)


@dataclass
class ApplicationMetrics:
    """Application-specific performance metrics"""

    discord_api_latency_ms: float = field(default=0.0)
    audio_processing_time_ms: float = field(default=0.0)
    cache_hit_rate: float = field(default=0.0)
    active_connections: int = field(default=0)
    pending_tasks: int = field(default=0)
    error_rate: float = field(default=0.0)
    commands_per_minute: float = field(default=0.0)
    memory_leaks_detected: int = field(default=0)


class PerformanceMonitor:
    """
    Comprehensive performance monitoring service with real-time metrics,
    alerting, and performance analysis.

    Features:
    - System and application metrics collection
    - Real-time performance monitoring
    - Configurable alerting system
    - Performance trend analysis
    - Memory leak detection
    - Bottleneck identification
    - Performance optimization recommendations
    """

    def __init__(
        self,
        container: DIContainer,
        logger: StructuredLogger | None = None,
        collection_interval: int = 300,  # 5 minutes instead of 30 seconds
        enable_detailed_profiling: bool = False,
    ):
        """Initialize performance monitor"""
        self._container = container
        self._logger = logger or StructuredLogger()
        self._collection_interval = collection_interval
        self._enable_detailed_profiling = enable_detailed_profiling

        # Metrics storage
        self._metrics: dict[str, MetricSeries] = {}
        self._custom_metrics: dict[str, MetricSeries] = {}

        # System monitoring
        self._process = psutil.Process()
        self._system_metrics = SystemMetrics()
        self._app_metrics = ApplicationMetrics()

        # Performance tracking
        self._operation_timers: dict[str, list[float]] = defaultdict(list)
        self._performance_baseline: dict[str, float] = {}

        # Alerting
        self._alerts: dict[str, PerformanceAlert] = {}
        self._triggered_alerts: list[tuple[PerformanceAlert, float, datetime]] = []

        # Background tasks
        self._collection_task: asyncio.Task | None = None
        self._analysis_task: asyncio.Task | None = None

        # Memory tracking
        self._memory_snapshots: list[tracemalloc.Snapshot] = []
        self._memory_baseline: tracemalloc.Snapshot | None = None

        # Shutdown management
        self._shutdown_event = asyncio.Event()

        # Performance data export
        self._export_enabled = True
        self._export_directory = Path("performance_data")

        # Thread safety
        self._lock = threading.RLock()

    async def initialize(self) -> None:
        """Initialize the performance monitor"""
        await self._logger.info(
            "Initializing performance monitor",
            {
                "collection_interval": self._collection_interval,
                "detailed_profiling": self._enable_detailed_profiling,
            },
        )

        # Create export directory
        if self._export_enabled:
            self._export_directory.mkdir(parents=True, exist_ok=True)

        # Start memory tracking
        if self._enable_detailed_profiling:
            tracemalloc.start()
            self._memory_baseline = tracemalloc.take_snapshot()

        # Initialize default metrics
        await self._initialize_default_metrics()

        # Setup default alerts
        await self._setup_default_alerts()

        # Start background tasks
        self._collection_task = asyncio.create_task(self._collection_loop())
        self._analysis_task = asyncio.create_task(self._analysis_loop())

        await self._logger.info("Performance monitor initialized successfully")

    async def shutdown(self) -> None:
        """Shutdown the performance monitor"""
        await self._logger.info("Shutting down performance monitor")

        # Signal shutdown
        self._shutdown_event.set()

        # Cancel background tasks
        for task in [self._collection_task, self._analysis_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Export final performance data
        if self._export_enabled:
            await self._export_performance_data()

        # Stop memory tracking
        if self._enable_detailed_profiling and tracemalloc.is_tracing():
            tracemalloc.stop()

        await self._logger.info("Performance monitor shutdown complete")

    async def record_metric(
        self,
        name: str,
        value: int | float,
        metric_type: MetricType = MetricType.GAUGE,
        unit: str = "",
        tags: dict[str, str] | None = None,
    ) -> None:
        """Record a custom metric value"""
        with self._lock:
            if name not in self._custom_metrics:
                self._custom_metrics[name] = MetricSeries(
                    name=name, metric_type=metric_type, unit=unit
                )

            self._custom_metrics[name].add_value(value, tags)

        await self._logger.debug(
            "Metric recorded",
            {
                "name": name,
                "value": value,
                "type": metric_type.value,
                "tags": tags or {},
            },
        )

    async def start_timer(self, operation_name: str) -> str:
        """Start timing an operation"""
        timer_id = f"{operation_name}_{time.time()}_{id(asyncio.current_task())}"

        # Store start time
        if not hasattr(self, "_active_timers"):
            self._active_timers = {}

        self._active_timers[timer_id] = time.time()

        return timer_id

    async def end_timer(self, timer_id: str) -> float:
        """End timing an operation and record the duration"""
        if not hasattr(self, "_active_timers") or timer_id not in self._active_timers:
            return 0.0

        start_time = self._active_timers.pop(timer_id)
        duration = time.time() - start_time

        # Extract operation name
        operation_name = timer_id.split("_")[0]

        # Record duration
        with self._lock:
            self._operation_timers[operation_name].append(duration)
            # Keep only last 1000 measurements
            if len(self._operation_timers[operation_name]) > 1000:
                self._operation_timers[operation_name].pop(0)

        # Record as metric
        await self.record_metric(
            f"{operation_name}_duration_ms", duration * 1000, MetricType.TIMER, "ms"
        )

        return duration

    async def time_operation(self, operation_name: str):
        """Context manager for timing operations"""

        class TimerContext:
            def __init__(self, monitor, name):
                self.monitor = monitor
                self.name = name
                self.timer_id = None

            async def __aenter__(self):
                self.timer_id = await self.monitor.start_timer(self.name)
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                if self.timer_id:
                    await self.monitor.end_timer(self.timer_id)

        return TimerContext(self, operation_name)

    async def add_alert(
        self,
        name: str,
        metric_name: str,
        condition: str,
        severity: AlertSeverity,
        description: str = "",
        cooldown_seconds: int = 300,
    ) -> None:
        """Add a performance alert"""
        alert = PerformanceAlert(
            name=name,
            metric_name=metric_name,
            condition=condition,
            severity=severity,
            description=description,
            cooldown_seconds=cooldown_seconds,
        )

        self._alerts[name] = alert

        await self._logger.info(
            "Performance alert added",
            {
                "name": name,
                "metric": metric_name,
                "condition": condition,
                "severity": severity.value,
            },
        )

    async def get_system_metrics(self) -> SystemMetrics:
        """Get current system metrics"""
        return self._system_metrics

    async def get_application_metrics(self) -> ApplicationMetrics:
        """Get current application metrics"""
        return self._app_metrics

    async def get_metric_series(self, name: str) -> MetricSeries | None:
        """Get metric time series by name"""
        return self._metrics.get(name) or self._custom_metrics.get(name)

    async def get_operation_stats(self, operation_name: str) -> dict[str, float]:
        """Get statistics for an operation"""
        with self._lock:
            durations = self._operation_timers.get(operation_name, [])

        if not durations:
            return {}

        return {
            "count": len(durations),
            "average_ms": statistics.mean(durations) * 1000,
            "median_ms": statistics.median(durations) * 1000,
            "min_ms": min(durations) * 1000,
            "max_ms": max(durations) * 1000,
            "stddev_ms": (
                statistics.stdev(durations) * 1000 if len(durations) > 1 else 0.0
            ),
            "p95_ms": self._percentile(durations, 95) * 1000,
            "p99_ms": self._percentile(durations, 99) * 1000,
        }

    async def get_performance_summary(self) -> dict[str, Any]:
        """Get comprehensive performance summary"""
        # Collect current metrics
        await self._collect_system_metrics()
        await self._collect_application_metrics()

        # Get top operations by duration
        top_operations = {}
        with self._lock:
            for op_name, durations in self._operation_timers.items():
                if durations:
                    avg_duration = statistics.mean(durations) * 1000
                    top_operations[op_name] = avg_duration

        # Sort by average duration
        top_operations = dict(
            sorted(top_operations.items(), key=lambda x: x[1], reverse=True)[:10]
        )

        # Get active alerts
        active_alerts = [
            {
                "name": alert.name,
                "severity": alert.severity.value,
                "description": alert.description,
                "trigger_count": alert.trigger_count,
            }
            for alert in self._alerts.values()
            if alert.last_triggered
            and (datetime.now(UTC) - alert.last_triggered).total_seconds() < 3600
        ]

        # Memory leak detection
        memory_leaks = (
            await self._detect_memory_leaks() if self._enable_detailed_profiling else []
        )

        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "system_metrics": {
                "cpu_percent": self._system_metrics.cpu_percent,
                "memory_percent": self._system_metrics.memory_percent,
                "memory_rss_mb": self._system_metrics.memory_rss_mb,
                "open_file_descriptors": self._system_metrics.open_file_descriptors,
                "thread_count": self._system_metrics.thread_count,
            },
            "application_metrics": {
                "discord_api_latency_ms": self._app_metrics.discord_api_latency_ms,
                "cache_hit_rate": self._app_metrics.cache_hit_rate,
                "active_connections": self._app_metrics.active_connections,
                "error_rate": self._app_metrics.error_rate,
                "commands_per_minute": self._app_metrics.commands_per_minute,
            },
            "top_operations": top_operations,
            "active_alerts": active_alerts,
            "memory_leaks": len(memory_leaks),
            "performance_recommendations": await self._get_performance_recommendations(),
        }

    async def generate_performance_report(self) -> str:
        """Generate detailed performance report"""
        summary = await self.get_performance_summary()

        report_lines = [
            "QuranBot Performance Report",
            "=" * 50,
            f"Generated: {summary['timestamp']}",
            "",
            "System Metrics:",
            f"  CPU Usage: {summary['system_metrics']['cpu_percent']:.1f}%",
            f"  Memory Usage: {summary['system_metrics']['memory_percent']:.1f}%",
            f"  Memory RSS: {summary['system_metrics']['memory_rss_mb']:.1f} MB",
            f"  Open Files: {summary['system_metrics']['open_file_descriptors']}",
            f"  Threads: {summary['system_metrics']['thread_count']}",
            "",
            "Application Metrics:",
            f"  Discord API Latency: {summary['application_metrics']['discord_api_latency_ms']:.1f} ms",
            f"  Cache Hit Rate: {summary['application_metrics']['cache_hit_rate']:.1f}%",
            f"  Active Connections: {summary['application_metrics']['active_connections']}",
            f"  Error Rate: {summary['application_metrics']['error_rate']:.2f}%",
            f"  Commands/Minute: {summary['application_metrics']['commands_per_minute']:.1f}",
            "",
            "Top Operations by Duration:",
        ]

        for op_name, avg_duration in summary["top_operations"].items():
            report_lines.append(f"  {op_name}: {avg_duration:.1f} ms")

        if summary["active_alerts"]:
            report_lines.extend(
                [
                    "",
                    "Active Alerts:",
                ]
            )
            for alert in summary["active_alerts"]:
                report_lines.append(
                    f"  [{alert['severity'].upper()}] {alert['name']}: {alert['description']}"
                )

        if summary["performance_recommendations"]:
            report_lines.extend(
                [
                    "",
                    "Performance Recommendations:",
                ]
            )
            for rec in summary["performance_recommendations"]:
                report_lines.append(f"  - {rec}")

        return "\n".join(report_lines)

    # =============================================================================
    # Private Methods
    # =============================================================================

    async def _initialize_default_metrics(self) -> None:
        """Initialize default metric series"""
        default_metrics = [
            ("cpu_percent", MetricType.GAUGE, "%"),
            ("memory_percent", MetricType.GAUGE, "%"),
            ("memory_rss_mb", MetricType.GAUGE, "MB"),
            ("open_file_descriptors", MetricType.GAUGE, "count"),
            ("thread_count", MetricType.GAUGE, "count"),
            ("discord_api_latency_ms", MetricType.GAUGE, "ms"),
            ("cache_hit_rate", MetricType.GAUGE, "%"),
            ("active_connections", MetricType.GAUGE, "count"),
            ("error_rate", MetricType.GAUGE, "%"),
            ("commands_per_minute", MetricType.RATE, "rate"),
        ]

        for name, metric_type, unit in default_metrics:
            self._metrics[name] = MetricSeries(
                name=name, metric_type=metric_type, unit=unit
            )

    async def _setup_default_alerts(self) -> None:
        """Setup default performance alerts"""
        default_alerts = [
            (
                "high_cpu",
                "cpu_percent",
                "> 80",
                AlertSeverity.WARNING,
                "High CPU usage detected",
            ),
            (
                "critical_cpu",
                "cpu_percent",
                "> 95",
                AlertSeverity.CRITICAL,
                "Critical CPU usage",
            ),
            (
                "high_memory",
                "memory_percent",
                "> 85",
                AlertSeverity.WARNING,
                "High memory usage",
            ),
            (
                "critical_memory",
                "memory_percent",
                "> 95",
                AlertSeverity.CRITICAL,
                "Critical memory usage",
            ),
            (
                "high_api_latency",
                "discord_api_latency_ms",
                "> 1000",
                AlertSeverity.WARNING,
                "High Discord API latency",
            ),
            (
                "low_cache_hit_rate",
                "cache_hit_rate",
                "< 70",
                AlertSeverity.WARNING,
                "Low cache hit rate",
            ),
            (
                "high_error_rate",
                "error_rate",
                "> 5",
                AlertSeverity.ERROR,
                "High error rate detected",
            ),
        ]

        for name, metric, condition, severity, description in default_alerts:
            await self.add_alert(name, metric, condition, severity, description)

    async def _collection_loop(self) -> None:
        """Background metrics collection loop"""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(3600)  # 60 minutes

                # Collect system metrics
                await self._collect_system_metrics()

                # Collect application metrics
                await self._collect_application_metrics()

                # Check alerts
                await self._check_alerts()

                # Update metric series
                await self._update_metric_series()

                # Send performance metrics to webhook (every hour)
                await self._send_performance_webhook()

            except asyncio.CancelledError:
                break
            except Exception as e:
                await self._logger.error("Metrics collection error", {"error": str(e)})

    async def _analysis_loop(self) -> None:
        """Background performance analysis loop"""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(3600)  # Run every hour

                # Analyze performance trends
                await self._analyze_performance_trends()

                # Detect memory leaks
                if self._enable_detailed_profiling:
                    leaks = await self._detect_memory_leaks()
                    if leaks:
                        await self._logger.warning(
                            "Memory leaks detected", {"leak_count": len(leaks)}
                        )

                # Cleanup old data
                await self._cleanup_old_data()

            except asyncio.CancelledError:
                break
            except Exception as e:
                await self._logger.error(
                    "Performance analysis error", {"error": str(e)}
                )

    async def _collect_system_metrics(self) -> None:
        """Collect system performance metrics"""
        try:
            # CPU and memory
            self._system_metrics.cpu_percent = self._process.cpu_percent()
            memory_info = self._process.memory_info()
            self._system_metrics.memory_rss_mb = memory_info.rss / (1024 * 1024)
            self._system_metrics.memory_vms_mb = memory_info.vms / (1024 * 1024)
            self._system_metrics.memory_percent = self._process.memory_percent()

            # I/O statistics
            try:
                io_counters = self._process.io_counters()
                self._system_metrics.disk_io_read_mb = io_counters.read_bytes / (
                    1024 * 1024
                )
                self._system_metrics.disk_io_write_mb = io_counters.write_bytes / (
                    1024 * 1024
                )
            except AttributeError:
                pass  # I/O counters not available on all platforms

            # Process information
            try:
                self._system_metrics.open_file_descriptors = len(
                    self._process.open_files()
                )
            except Exception:
                self._system_metrics.open_file_descriptors = 0

            self._system_metrics.thread_count = self._process.num_threads()

            # Garbage collection stats
            gc_stats = gc.get_stats()
            if gc_stats:
                total_collections = sum(stat["collections"] for stat in gc_stats)
                total_collected = sum(stat["collected"] for stat in gc_stats)
                total_uncollectable = sum(stat["uncollectable"] for stat in gc_stats)

                self._system_metrics.gc_collections = total_collections
                self._system_metrics.gc_collected = total_collected
                self._system_metrics.gc_uncollectable = total_uncollectable

        except Exception as e:
            await self._logger.warning(
                "Failed to collect system metrics", {"error": str(e)}
            )

    async def _collect_application_metrics(self) -> None:
        """Collect application-specific metrics"""
        try:
            # These would be populated by the actual application components
            # For now, we'll use placeholders or try to get from DI container

            # Try to get cache service metrics
            try:
                from .cache_service import get_cache_service

                cache_service = await get_cache_service()
                cache_stats = await cache_service.get_statistics()
                self._app_metrics.cache_hit_rate = cache_stats.hit_rate * 100
            except Exception:
                pass

            # Try to get connection pool metrics
            try:
                from .connection_pool import get_pool_manager

                pool_manager = await get_pool_manager()
                # Would get metrics from pool manager
            except Exception:
                pass

            # Calculate commands per minute from operation timers
            command_operations = [
                name
                for name in self._operation_timers.keys()
                if "command" in name.lower()
            ]
            if command_operations:
                recent_commands = 0
                with self._lock:
                    for op_name in command_operations:
                        recent_commands += len(
                            [
                                t
                                for t in self._operation_timers[op_name]
                                if time.time() - t < 60  # Last minute
                            ]
                        )
                self._app_metrics.commands_per_minute = recent_commands

        except Exception as e:
            await self._logger.warning(
                "Failed to collect application metrics", {"error": str(e)}
            )

    async def _update_metric_series(self) -> None:
        """Update metric time series with current values"""
        # System metrics
        system_values = [
            ("cpu_percent", self._system_metrics.cpu_percent),
            ("memory_percent", self._system_metrics.memory_percent),
            ("memory_rss_mb", self._system_metrics.memory_rss_mb),
            ("open_file_descriptors", self._system_metrics.open_file_descriptors),
            ("thread_count", self._system_metrics.thread_count),
        ]

        # Application metrics
        app_values = [
            ("discord_api_latency_ms", self._app_metrics.discord_api_latency_ms),
            ("cache_hit_rate", self._app_metrics.cache_hit_rate),
            ("active_connections", self._app_metrics.active_connections),
            ("error_rate", self._app_metrics.error_rate),
            ("commands_per_minute", self._app_metrics.commands_per_minute),
        ]

        with self._lock:
            for name, value in system_values + app_values:
                if name in self._metrics:
                    self._metrics[name].add_value(value)

    async def _check_alerts(self) -> None:
        """Check all alerts against current metrics"""
        current_values = {
            "cpu_percent": self._system_metrics.cpu_percent,
            "memory_percent": self._system_metrics.memory_percent,
            "discord_api_latency_ms": self._app_metrics.discord_api_latency_ms,
            "cache_hit_rate": self._app_metrics.cache_hit_rate,
            "error_rate": self._app_metrics.error_rate,
        }

        for alert in self._alerts.values():
            if alert.metric_name in current_values:
                value = current_values[alert.metric_name]

                if alert.should_trigger(value):
                    alert.trigger()

                    # Log alert
                    await self._logger.warning(
                        "Performance alert triggered",
                        {
                            "alert_name": alert.name,
                            "metric": alert.metric_name,
                            "value": value,
                            "condition": alert.condition,
                            "severity": alert.severity.value,
                        },
                    )

                    # Store triggered alert
                    self._triggered_alerts.append((alert, value, datetime.now(UTC)))

                    # Keep only last 100 triggered alerts
                    if len(self._triggered_alerts) > 100:
                        self._triggered_alerts.pop(0)

    async def _analyze_performance_trends(self) -> None:
        """Analyze performance trends and patterns"""
        try:
            # Analyze CPU trends
            cpu_series = self._metrics.get("cpu_percent")
            if cpu_series and len(cpu_series.values) > 10:
                recent_cpu = [mv.value for mv in list(cpu_series.values)[-10:]]
                avg_cpu = statistics.mean(recent_cpu)

                if avg_cpu > 70:
                    await self._logger.info(
                        "High CPU usage trend detected",
                        {
                            "average_cpu": avg_cpu,
                            "recommendation": "Consider optimizing CPU-intensive operations",
                        },
                    )

            # Analyze memory trends
            memory_series = self._metrics.get("memory_percent")
            if memory_series and len(memory_series.values) > 10:
                recent_memory = [mv.value for mv in list(memory_series.values)[-10:]]

                # Check for memory leak (consistently increasing memory)
                if len(recent_memory) >= 5:
                    slope = self._calculate_trend_slope(recent_memory)
                    if slope > 1:  # Increasing by more than 1% per measurement
                        await self._logger.warning(
                            "Potential memory leak detected",
                            {
                                "memory_trend_slope": slope,
                                "recommendation": "Check for memory leaks in application code",
                            },
                        )

        except Exception as e:
            await self._logger.warning(
                "Performance trend analysis failed", {"error": str(e)}
            )

    async def _detect_memory_leaks(self) -> list[dict[str, Any]]:
        """Detect memory leaks using tracemalloc"""
        if not tracemalloc.is_tracing() or not self._memory_baseline:
            return []

        try:
            current_snapshot = tracemalloc.take_snapshot()
            top_stats = current_snapshot.compare_to(self._memory_baseline, "lineno")

            leaks = []
            for stat in top_stats[:10]:  # Top 10 memory consumers
                if stat.size_diff > 1024 * 1024:  # More than 1MB difference
                    leaks.append(
                        {
                            "file": stat.traceback.format()[0],
                            "size_diff_mb": stat.size_diff / (1024 * 1024),
                            "count_diff": stat.count_diff,
                        }
                    )

            # Store snapshot for next comparison
            self._memory_snapshots.append(current_snapshot)
            if len(self._memory_snapshots) > 5:  # Keep only last 5 snapshots
                self._memory_snapshots.pop(0)

            return leaks

        except Exception as e:
            await self._logger.warning(
                "Memory leak detection failed", {"error": str(e)}
            )
            return []

    async def _get_performance_recommendations(self) -> list[str]:
        """Generate performance optimization recommendations"""
        recommendations = []

        # CPU recommendations
        if self._system_metrics.cpu_percent > 80:
            recommendations.append(
                "High CPU usage detected. Consider optimizing computational operations or using async processing."
            )

        # Memory recommendations
        if self._system_metrics.memory_percent > 85:
            recommendations.append(
                "High memory usage detected. Consider implementing memory cleanup or increasing system memory."
            )

        # Cache recommendations
        if self._app_metrics.cache_hit_rate < 70:
            recommendations.append(
                "Low cache hit rate. Consider reviewing cache configuration and key strategies."
            )

        # Error rate recommendations
        if self._app_metrics.error_rate > 2:
            recommendations.append(
                "High error rate detected. Review error logs and implement better error handling."
            )

        # Operation performance recommendations
        with self._lock:
            slow_operations = []
            for op_name, durations in self._operation_timers.items():
                if durations:
                    avg_duration = statistics.mean(durations)
                    if avg_duration > 1.0:  # Slower than 1 second
                        slow_operations.append((op_name, avg_duration))

        if slow_operations:
            slowest_op = max(slow_operations, key=lambda x: x[1])
            recommendations.append(
                f"Operation '{slowest_op[0]}' is slow ({slowest_op[1]:.2f}s avg). Consider optimization."
            )

        return recommendations

    async def _cleanup_old_data(self) -> None:
        """Clean up old performance data"""
        cutoff_time = datetime.now(UTC) - timedelta(hours=24)

        # Clean up triggered alerts older than 24 hours
        self._triggered_alerts = [
            (alert, value, timestamp)
            for alert, value, timestamp in self._triggered_alerts
            if timestamp > cutoff_time
        ]

        # Clean up old operation timers
        with self._lock:
            for op_name in list(self._operation_timers.keys()):
                if len(self._operation_timers[op_name]) > 1000:
                    # Keep only the most recent 1000 measurements
                    self._operation_timers[op_name] = self._operation_timers[op_name][
                        -1000:
                    ]

    async def _send_performance_webhook(self) -> None:
        """Send performance metrics to webhook system"""
        try:
            # Get webhook router from container
            webhook_router = self._container.get("enhanced_webhook_router")
            if not webhook_router or not hasattr(
                webhook_router, "log_performance_visual"
            ):
                return

            # Get current metrics
            cpu_percent = self._system_metrics.cpu_percent
            memory_percent = self._system_metrics.memory_percent
            latency_ms = self._app_metrics.discord_api_latency_ms
            cache_hit_rate = self._app_metrics.cache_hit_rate

            # Get historical data for trends
            cpu_series = self._metrics.get("cpu_percent")
            memory_series = self._metrics.get("memory_percent")

            cpu_history = None
            memory_history = None

            if cpu_series:
                cpu_history = [mv.value for mv in list(cpu_series.values)[-20:]]
            if memory_series:
                memory_history = [mv.value for mv in list(memory_series.values)[-20:]]

            # Get bot's profile picture URL
            bot_avatar_url = None
            try:
                bot = self._container.get("bot")
                if bot and bot.user and bot.user.avatar:
                    bot_avatar_url = str(bot.user.avatar.url)
            except Exception as e:
                await self._logger.debug("Could not get bot avatar", {"error": str(e)})

            # Send to webhook with bot avatar as thumbnail
            await webhook_router.log_performance_visual(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                latency_ms=latency_ms,
                cache_hit_rate=cache_hit_rate,
                cpu_history=cpu_history,
                memory_history=memory_history,
                bot_avatar_url=bot_avatar_url,
            )

            await self._logger.debug(
                "Performance metrics sent to webhook",
                {
                    "cpu": f"{cpu_percent:.1f}%",
                    "memory": f"{memory_percent:.1f}%",
                    "latency": f"{latency_ms:.1f}ms",
                    "cache_hits": f"{cache_hit_rate:.1f}%",
                    "bot_avatar": bot_avatar_url is not None,
                },
            )

        except Exception as e:
            await self._logger.warning(
                "Failed to send performance webhook", {"error": str(e)}
            )

    async def _export_performance_data(self) -> None:
        """Export performance data to files"""
        try:
            export_time = datetime.now(UTC)
            export_file = (
                self._export_directory
                / f"performance_{export_time.strftime('%Y%m%d_%H%M%S')}.json"
            )

            # Prepare export data
            export_data = {
                "timestamp": export_time.isoformat(),
                "system_metrics": {
                    "cpu_percent": self._system_metrics.cpu_percent,
                    "memory_percent": self._system_metrics.memory_percent,
                    "memory_rss_mb": self._system_metrics.memory_rss_mb,
                    "open_file_descriptors": self._system_metrics.open_file_descriptors,
                    "thread_count": self._system_metrics.thread_count,
                },
                "application_metrics": {
                    "discord_api_latency_ms": self._app_metrics.discord_api_latency_ms,
                    "cache_hit_rate": self._app_metrics.cache_hit_rate,
                    "active_connections": self._app_metrics.active_connections,
                    "error_rate": self._app_metrics.error_rate,
                    "commands_per_minute": self._app_metrics.commands_per_minute,
                },
                "operation_stats": {},
                "triggered_alerts": len(self._triggered_alerts),
            }

            # Add operation statistics
            with self._lock:
                for op_name, durations in self._operation_timers.items():
                    if durations:
                        export_data["operation_stats"][op_name] = {
                            "count": len(durations),
                            "average_ms": statistics.mean(durations) * 1000,
                            "max_ms": max(durations) * 1000,
                            "min_ms": min(durations) * 1000,
                        }

            # Write to file
            with open(export_file, "w") as f:
                json.dump(export_data, f, indent=2, default=str)

            await self._logger.info(
                "Performance data exported", {"file": str(export_file)}
            )

        except Exception as e:
            await self._logger.warning(
                "Failed to export performance data", {"error": str(e)}
            )

    def _percentile(self, values: list[float], percentile: float) -> float:
        """Calculate percentile of values"""
        if not values:
            return 0.0

        sorted_values = sorted(values)
        k = (len(sorted_values) - 1) * percentile / 100
        f = int(k)
        c = k - f

        if f == len(sorted_values) - 1:
            return sorted_values[f]

        return sorted_values[f] * (1 - c) + sorted_values[f + 1] * c

    def _calculate_trend_slope(self, values: list[float]) -> float:
        """Calculate trend slope using simple linear regression"""
        if len(values) < 2:
            return 0.0

        n = len(values)
        x_values = list(range(n))

        # Calculate slope using least squares method
        sum_x = sum(x_values)
        sum_y = sum(values)
        sum_xy = sum(x * y for x, y in zip(x_values, values, strict=False))
        sum_x_squared = sum(x * x for x in x_values)

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x_squared - sum_x * sum_x)
        return slope


# =============================================================================
# Decorator for Performance Monitoring
# =============================================================================


def monitor_performance(operation_name: str = None):
    """Decorator for automatic performance monitoring"""

    def decorator(func: Callable) -> Callable:
        nonlocal operation_name
        if operation_name is None:
            operation_name = func.__name__

        if asyncio.iscoroutinefunction(func):

            async def async_wrapper(*args, **kwargs):
                try:
                    from .di_container import get_container

                    container = get_container()
                    monitor = container.get(PerformanceMonitor)

                    async with monitor.time_operation(operation_name):
                        return await func(*args, **kwargs)
                except Exception:
                    # Fallback if monitoring not available
                    return await func(*args, **kwargs)

            return async_wrapper
        else:

            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    # Could log duration here for sync functions
                    pass

            return sync_wrapper

    return decorator


# =============================================================================
# Global Performance Monitor
# =============================================================================

_global_performance_monitor: PerformanceMonitor | None = None


async def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance"""
    global _global_performance_monitor

    if _global_performance_monitor is None:
        from .di_container import get_container

        container = get_container()
        _global_performance_monitor = PerformanceMonitor(container)
        await _global_performance_monitor.initialize()

    return _global_performance_monitor
