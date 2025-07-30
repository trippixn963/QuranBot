# =============================================================================
# QuranBot - Performance Profiler
# =============================================================================
# Advanced performance profiling and bottleneck identification system.
# Provides detailed analysis of system performance, memory usage,
# operation timing, and resource utilization to identify optimization opportunities.
# =============================================================================

import asyncio
import cProfile
import functools
import gc
import inspect
import os
import pstats
import sys
import time
import tracemalloc
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import threading
import weakref

import psutil

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

try:
    import line_profiler
    HAS_LINE_PROFILER = True
except ImportError:
    HAS_LINE_PROFILER = False

try:
    import memory_profiler
    HAS_MEMORY_PROFILER = True
except ImportError:
    HAS_MEMORY_PROFILER = False

from .structured_logger import StructuredLogger


class ProfilerMode(str, Enum):
    """Profiling modes"""
    DISABLED = "disabled"
    BASIC = "basic"  # Simple timing
    DETAILED = "detailed"  # Line-by-line profiling
    MEMORY = "memory"  # Memory profiling
    CPU = "cpu"  # CPU profiling
    FULL = "full"  # All profiling modes


class BottleneckType(str, Enum):
    """Types of performance bottlenecks"""
    CPU_INTENSIVE = "cpu_intensive"
    MEMORY_LEAK = "memory_leak"
    I_O_BOUND = "io_bound"
    NETWORK_LATENCY = "network_latency"
    DISK_ACCESS = "disk_access"
    CONCURRENCY_ISSUE = "concurrency_issue"
    CACHE_MISS = "cache_miss"
    DATABASE_SLOW = "database_slow"


@dataclass
class BottleneckReport:
    """Report of a detected performance bottleneck"""
    
    bottleneck_type: BottleneckType
    severity: str  # "low", "medium", "high", "critical"
    description: str
    location: str  # File:line or function name
    metrics: Dict[str, Any]
    recommendations: List[str]
    detected_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    impact_score: float = 0.0  # 0.0 to 1.0


@dataclass
class OperationProfile:
    """Profile of a specific operation"""
    
    name: str
    total_calls: int = 0
    total_time: float = 0.0
    avg_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    call_frequency: float = 0.0  # calls per minute
    last_called: Optional[datetime] = None
    bottlenecks: List[BottleneckReport] = field(default_factory=list)


class PerformanceProfiler:
    """
    Advanced performance profiler for identifying bottlenecks and optimization opportunities.
    
    Features:
    - Real-time operation profiling
    - Memory leak detection
    - CPU usage analysis
    - I/O performance monitoring
    - Bottleneck identification and reporting
    - Performance recommendations
    - Historical trend analysis
    """
    
    def __init__(
        self,
        logger: Optional[StructuredLogger] = None,
        mode: ProfilerMode = ProfilerMode.BASIC,
        enable_memory_tracking: bool = True,
        enable_cpu_profiling: bool = False,
        enable_line_profiling: bool = False,
        max_operation_history: int = 1000,
        bottleneck_thresholds: Optional[Dict[str, float]] = None,
    ):
        """Initialize the performance profiler"""
        self.logger = logger or StructuredLogger()
        self.mode = mode
        self.enable_memory_tracking = enable_memory_tracking
        self.enable_cpu_profiling = enable_cpu_profiling
        self.enable_line_profiling = enable_line_profiling
        self.max_operation_history = max_operation_history
        
        # Operation tracking
        self.operations: Dict[str, OperationProfile] = {}
        self.active_operations: Dict[str, Dict[str, Any]] = {}
        self.operation_history: deque = deque(maxlen=max_operation_history)
        
        # Memory tracking
        self.memory_snapshots: List[tracemalloc.Snapshot] = []
        self.memory_baseline: Optional[tracemalloc.Snapshot] = None
        self.memory_leaks: List[Dict[str, Any]] = []
        
        # CPU profiling
        self.cpu_profiler: Optional[cProfile.Profile] = None
        self.line_profiler: Optional[Any] = None  # Will be line_profiler.LineProfiler if available
        
        # Bottleneck detection
        self.bottleneck_thresholds = bottleneck_thresholds or {
            "cpu_threshold": 80.0,  # CPU usage percentage
            "memory_threshold": 85.0,  # Memory usage percentage
            "operation_time_threshold": 1.0,  # seconds
            "memory_growth_threshold": 10.0,  # MB per minute
            "io_wait_threshold": 20.0,  # IO wait percentage
        }
        
        # System monitoring
        self.process = psutil.Process()
        self.system_metrics = {
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "memory_rss_mb": 0.0,
            "io_counters": None,
            "num_threads": 0,
            "open_files": 0,
        }
        
        # Background tasks
        self.monitoring_task: Optional[asyncio.Task] = None
        self.shutdown_event = asyncio.Event()
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Performance data export
        self.export_directory = Path("performance_data")
        self.export_directory.mkdir(exist_ok=True)
        
    async def initialize(self) -> None:
        """Initialize the profiler"""
        await self.logger.info(
            "Initializing performance profiler",
            {
                "mode": self.mode.value,
                "memory_tracking": self.enable_memory_tracking,
                "cpu_profiling": self.enable_cpu_profiling,
                "line_profiling": self.enable_line_profiling,
            }
        )
        
        # Start memory tracking
        if self.enable_memory_tracking:
            tracemalloc.start()
            self.memory_baseline = tracemalloc.take_snapshot()
            await self.logger.info("Memory tracking enabled")
        
        # Initialize CPU profiler
        if self.enable_cpu_profiling:
            self.cpu_profiler = cProfile.Profile()
            await self.logger.info("CPU profiling enabled")
        
        # Initialize line profiler
        if self.enable_line_profiling and HAS_LINE_PROFILER:
            self.line_profiler = line_profiler.LineProfiler()
            await self.logger.info("Line profiling enabled")
        elif self.enable_line_profiling and not HAS_LINE_PROFILER:
            await self.logger.warning("Line profiling requested but line_profiler not available")
        
        # Start monitoring task
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        await self.logger.info("Performance profiler initialized successfully")
    
    async def shutdown(self) -> None:
        """Shutdown the profiler"""
        await self.logger.info("Shutting down performance profiler")
        
        # Signal shutdown
        self.shutdown_event.set()
        
        # Cancel monitoring task
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Stop memory tracking
        if self.enable_memory_tracking and tracemalloc.is_tracing():
            tracemalloc.stop()
        
        # Export final data
        await self._export_profiling_data()
        
        await self.logger.info("Performance profiler shutdown complete")
    
    def profile_operation(self, operation_name: str = None):
        """
        Decorator to profile operations automatically.
        
        Usage:
            @profiler.profile_operation("audio_playback")
            async def play_audio():
                # operation code
        """
        def decorator(func: Callable) -> Callable:
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await self._profile_operation(op_name, func, *args, **kwargs)
            
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                return self._profile_operation_sync(op_name, func, *args, **kwargs)
            
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    async def _profile_operation(
        self, 
        operation_name: str, 
        func: Callable, 
        *args, 
        **kwargs
    ) -> Any:
        """Profile an async operation"""
        start_time = time.time()
        start_memory = self._get_memory_usage()
        start_cpu = self._get_cpu_usage()
        
        # Start CPU profiling if enabled
        if self.enable_cpu_profiling and self.cpu_profiler:
            self.cpu_profiler.enable()
        
        # Start line profiling if enabled
        if self.enable_line_profiling and self.line_profiler and HAS_LINE_PROFILER:
            self.line_profiler.enable_by_count()
        
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            # Stop profiling
            if self.enable_cpu_profiling and self.cpu_profiler:
                self.cpu_profiler.disable()
            
            if self.enable_line_profiling and self.line_profiler and HAS_LINE_PROFILER:
                self.line_profiler.disable_by_count()
            
            # Calculate metrics
            end_time = time.time()
            end_memory = self._get_memory_usage()
            end_cpu = self._get_cpu_usage()
            
            duration = end_time - start_time
            memory_delta = end_memory - start_memory
            cpu_usage = (start_cpu + end_cpu) / 2
            
            # Record operation
            await self._record_operation(
                operation_name, duration, memory_delta, cpu_usage
            )
    
    def _profile_operation_sync(
        self, 
        operation_name: str, 
        func: Callable, 
        *args, 
        **kwargs
    ) -> Any:
        """Profile a sync operation"""
        start_time = time.time()
        start_memory = self._get_memory_usage()
        start_cpu = self._get_cpu_usage()
        
        # Start CPU profiling if enabled
        if self.enable_cpu_profiling and self.cpu_profiler:
            self.cpu_profiler.enable()
        
        # Start line profiling if enabled
        if self.enable_line_profiling and self.line_profiler and HAS_LINE_PROFILER:
            self.line_profiler.enable_by_count()
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            # Stop profiling
            if self.enable_cpu_profiling and self.cpu_profiler:
                self.cpu_profiler.disable()
            
            if self.enable_line_profiling and self.line_profiler and HAS_LINE_PROFILER:
                self.line_profiler.disable_by_count()
            
            # Calculate metrics
            end_time = time.time()
            end_memory = self._get_memory_usage()
            end_cpu = self._get_cpu_usage()
            
            duration = end_time - start_time
            memory_delta = end_memory - start_memory
            cpu_usage = (start_cpu + end_cpu) / 2
            
            # Record operation (sync version)
            asyncio.create_task(
                self._record_operation(operation_name, duration, memory_delta, cpu_usage)
            )
    
    async def _record_operation(
        self, 
        operation_name: str, 
        duration: float, 
        memory_delta: float, 
        cpu_usage: float
    ) -> None:
        """Record operation metrics"""
        with self.lock:
            if operation_name not in self.operations:
                self.operations[operation_name] = OperationProfile(name=operation_name)
            
            op = self.operations[operation_name]
            op.total_calls += 1
            op.total_time += duration
            op.avg_time = op.total_time / op.total_calls
            op.min_time = min(op.min_time, duration)
            op.max_time = max(op.max_time, duration)
            op.memory_usage_mb += memory_delta
            op.cpu_usage_percent = (op.cpu_usage_percent + cpu_usage) / 2
            op.last_called = datetime.now(UTC)
            
            # Calculate call frequency (calls per minute)
            if op.last_called:
                time_diff = (datetime.now(UTC) - op.last_called).total_seconds() / 60
                if time_diff > 0:
                    op.call_frequency = 1 / time_diff
            
            # Record in history
            self.operation_history.append({
                "operation": operation_name,
                "duration": duration,
                "memory_delta": memory_delta,
                "cpu_usage": cpu_usage,
                "timestamp": datetime.now(UTC),
            })
        
        # Check for bottlenecks
        await self._check_operation_bottlenecks(operation_name, duration, memory_delta, cpu_usage)
    
    async def _check_operation_bottlenecks(
        self, 
        operation_name: str, 
        duration: float, 
        memory_delta: float, 
        cpu_usage: float
    ) -> None:
        """Check for bottlenecks in an operation"""
        bottlenecks = []
        
        # Check operation time threshold
        if duration > self.bottleneck_thresholds["operation_time_threshold"]:
            bottlenecks.append(BottleneckReport(
                bottleneck_type=BottleneckType.CPU_INTENSIVE,
                severity="high" if duration > 5.0 else "medium",
                description=f"Operation '{operation_name}' is taking {duration:.2f}s",
                location=operation_name,
                metrics={"duration": duration, "threshold": self.bottleneck_thresholds["operation_time_threshold"]},
                recommendations=[
                    "Consider optimizing the operation algorithm",
                    "Look for unnecessary computations",
                    "Consider caching results",
                    "Check for blocking operations"
                ],
                impact_score=min(duration / 10.0, 1.0)
            ))
        
        # Check memory growth
        if memory_delta > self.bottleneck_thresholds["memory_growth_threshold"]:
            bottlenecks.append(BottleneckReport(
                bottleneck_type=BottleneckType.MEMORY_LEAK,
                severity="critical" if memory_delta > 50.0 else "high",
                description=f"Operation '{operation_name}' allocated {memory_delta:.2f}MB",
                location=operation_name,
                metrics={"memory_delta": memory_delta, "threshold": self.bottleneck_thresholds["memory_growth_threshold"]},
                recommendations=[
                    "Check for memory leaks",
                    "Review object lifecycle management",
                    "Consider using weak references",
                    "Implement proper cleanup"
                ],
                impact_score=min(memory_delta / 100.0, 1.0)
            ))
        
        # Check CPU usage
        if cpu_usage > self.bottleneck_thresholds["cpu_threshold"]:
            bottlenecks.append(BottleneckReport(
                bottleneck_type=BottleneckType.CPU_INTENSIVE,
                severity="high" if cpu_usage > 90.0 else "medium",
                description=f"Operation '{operation_name}' used {cpu_usage:.1f}% CPU",
                location=operation_name,
                metrics={"cpu_usage": cpu_usage, "threshold": self.bottleneck_thresholds["cpu_threshold"]},
                recommendations=[
                    "Consider async/await for I/O operations",
                    "Look for CPU-intensive loops",
                    "Consider caching expensive computations",
                    "Profile the operation for hotspots"
                ],
                impact_score=min(cpu_usage / 100.0, 1.0)
            ))
        
        # Add bottlenecks to operation profile
        with self.lock:
            if operation_name in self.operations:
                self.operations[operation_name].bottlenecks.extend(bottlenecks)
        
        # Log critical bottlenecks
        for bottleneck in bottlenecks:
            if bottleneck.severity in ["high", "critical"]:
                await self.logger.warning(
                    f"Performance bottleneck detected: {bottleneck.description}",
                    {
                        "type": bottleneck.bottleneck_type.value,
                        "severity": bottleneck.severity,
                        "impact_score": bottleneck.impact_score,
                        "recommendations": bottleneck.recommendations
                    }
                )
    
    async def _monitoring_loop(self) -> None:
        """Background monitoring loop"""
        while not self.shutdown_event.is_set():
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                # Update system metrics
                await self._update_system_metrics()
                
                # Check for system-level bottlenecks
                await self._check_system_bottlenecks()
                
                # Detect memory leaks
                if self.enable_memory_tracking:
                    await self._detect_memory_leaks()
                
                # Export profiling data periodically
                if len(self.operation_history) % 100 == 0:  # Every 100 operations
                    await self._export_profiling_data()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                await self.logger.error("Profiling monitoring error", {"error": str(e)})
    
    async def _update_system_metrics(self) -> None:
        """Update system-level metrics"""
        try:
            self.system_metrics["cpu_percent"] = self.process.cpu_percent()
            self.system_metrics["memory_percent"] = self.process.memory_percent()
            self.system_metrics["memory_rss_mb"] = self.process.memory_info().rss / 1024 / 1024
            self.system_metrics["io_counters"] = self.process.io_counters()
            self.system_metrics["num_threads"] = self.process.num_threads()
            self.system_metrics["open_files"] = len(self.process.open_files())
        except Exception as e:
            await self.logger.warning("Failed to update system metrics", {"error": str(e)})
    
    async def _check_system_bottlenecks(self) -> None:
        """Check for system-level bottlenecks"""
        bottlenecks = []
        
        # Check CPU usage
        if self.system_metrics["cpu_percent"] > self.bottleneck_thresholds["cpu_threshold"]:
            bottlenecks.append(BottleneckReport(
                bottleneck_type=BottleneckType.CPU_INTENSIVE,
                severity="critical" if self.system_metrics["cpu_percent"] > 95.0 else "high",
                description=f"High CPU usage: {self.system_metrics['cpu_percent']:.1f}%",
                location="system",
                metrics={"cpu_percent": self.system_metrics["cpu_percent"]},
                recommendations=[
                    "Check for CPU-intensive operations",
                    "Consider optimizing algorithms",
                    "Look for infinite loops",
                    "Consider async processing"
                ],
                impact_score=min(self.system_metrics["cpu_percent"] / 100.0, 1.0)
            ))
        
        # Check memory usage
        if self.system_metrics["memory_percent"] > self.bottleneck_thresholds["memory_threshold"]:
            bottlenecks.append(BottleneckReport(
                bottleneck_type=BottleneckType.MEMORY_LEAK,
                severity="critical" if self.system_metrics["memory_percent"] > 95.0 else "high",
                description=f"High memory usage: {self.system_metrics['memory_percent']:.1f}%",
                location="system",
                metrics={"memory_percent": self.system_metrics["memory_percent"]},
                recommendations=[
                    "Check for memory leaks",
                    "Review object lifecycle",
                    "Consider garbage collection",
                    "Monitor memory growth"
                ],
                impact_score=min(self.system_metrics["memory_percent"] / 100.0, 1.0)
            ))
        
        # Log system bottlenecks
        for bottleneck in bottlenecks:
            await self.logger.warning(
                f"System bottleneck detected: {bottleneck.description}",
                {
                    "type": bottleneck.bottleneck_type.value,
                    "severity": bottleneck.severity,
                    "impact_score": bottleneck.impact_score
                }
            )
    
    async def _detect_memory_leaks(self) -> None:
        """Detect memory leaks using tracemalloc"""
        try:
            current_snapshot = tracemalloc.take_snapshot()
            
            if self.memory_baseline:
                # Compare with baseline
                top_stats = current_snapshot.compare_to(self.memory_baseline, 'lineno')
                
                for stat in top_stats[:10]:  # Top 10 differences
                    if stat.size_diff > 1024 * 1024:  # 1MB threshold
                        self.memory_leaks.append({
                            "file": stat.traceback.format()[-1],
                            "size_diff_mb": stat.size_diff / 1024 / 1024,
                            "count_diff": stat.count_diff,
                            "detected_at": datetime.now(UTC)
                        })
            
            # Update baseline periodically
            if len(self.memory_snapshots) % 10 == 0:  # Every 10 snapshots
                self.memory_baseline = current_snapshot
            
            self.memory_snapshots.append(current_snapshot)
            
        except Exception as e:
            await self.logger.warning("Memory leak detection failed", {"error": str(e)})
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            return self.process.memory_info().rss / 1024 / 1024
        except Exception:
            return 0.0
    
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage"""
        try:
            return self.process.cpu_percent()
        except Exception:
            return 0.0
    
    async def get_profiling_summary(self) -> Dict[str, Any]:
        """Get comprehensive profiling summary"""
        with self.lock:
            # Get top operations by duration
            top_operations = []
            for op_name, op in self.operations.items():
                if op.total_calls > 0:
                    top_operations.append({
                        "name": op_name,
                        "total_calls": op.total_calls,
                        "avg_time_ms": op.avg_time * 1000,
                        "max_time_ms": op.max_time * 1000,
                        "memory_usage_mb": op.memory_usage_mb,
                        "cpu_usage_percent": op.cpu_usage_percent,
                        "call_frequency": op.call_frequency,
                        "bottleneck_count": len(op.bottlenecks)
                    })
            
            # Sort by average time
            top_operations.sort(key=lambda x: x["avg_time_ms"], reverse=True)
            
            # Get recent bottlenecks
            recent_bottlenecks = []
            for op in self.operations.values():
                for bottleneck in op.bottlenecks[-5:]:  # Last 5 bottlenecks per operation
                    recent_bottlenecks.append({
                        "operation": op.name,
                        "type": bottleneck.bottleneck_type.value,
                        "severity": bottleneck.severity,
                        "description": bottleneck.description,
                        "impact_score": bottleneck.impact_score
                    })
            
            # Sort by impact score
            recent_bottlenecks.sort(key=lambda x: x["impact_score"], reverse=True)
            
            return {
                "timestamp": datetime.now(UTC).isoformat(),
                "system_metrics": self.system_metrics,
                "top_operations": top_operations[:10],
                "recent_bottlenecks": recent_bottlenecks[:20],
                "memory_leaks": len(self.memory_leaks),
                "total_operations": len(self.operations),
                "operation_history_size": len(self.operation_history),
                "profiling_mode": self.mode.value
            }
    
    async def get_operation_profile(self, operation_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed profile for a specific operation"""
        with self.lock:
            if operation_name not in self.operations:
                return None
            
            op = self.operations[operation_name]
            
            # Get recent history for this operation
            recent_history = [
                h for h in self.operation_history[-100:]  # Last 100 entries
                if h["operation"] == operation_name
            ]
            
            return {
                "name": op.name,
                "total_calls": op.total_calls,
                "total_time": op.total_time,
                "avg_time_ms": op.avg_time * 1000,
                "min_time_ms": op.min_time * 1000,
                "max_time_ms": op.max_time * 1000,
                "memory_usage_mb": op.memory_usage_mb,
                "cpu_usage_percent": op.cpu_usage_percent,
                "call_frequency": op.call_frequency,
                "last_called": op.last_called.isoformat() if op.last_called else None,
                "bottlenecks": [
                    {
                        "type": b.bottleneck_type.value,
                        "severity": b.severity,
                        "description": b.description,
                        "impact_score": b.impact_score,
                        "detected_at": b.detected_at.isoformat()
                    }
                    for b in op.bottlenecks[-10:]  # Last 10 bottlenecks
                ],
                "recent_history": recent_history[-20:]  # Last 20 calls
            }
    
    async def _export_profiling_data(self) -> None:
        """Export profiling data to file"""
        try:
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            export_file = self.export_directory / f"profiling_data_{timestamp}.json"
            
            summary = await self.get_profiling_summary()
            
            # Add detailed operation data
            detailed_operations = {}
            with self.lock:
                for op_name, op in self.operations.items():
                    detailed_operations[op_name] = {
                        "total_calls": op.total_calls,
                        "total_time": op.total_time,
                        "avg_time": op.avg_time,
                        "memory_usage_mb": op.memory_usage_mb,
                        "cpu_usage_percent": op.cpu_usage_percent,
                        "bottleneck_count": len(op.bottlenecks)
                    }
            
            export_data = {
                "timestamp": datetime.now(UTC).isoformat(),
                "summary": summary,
                "detailed_operations": detailed_operations,
                "memory_leaks": self.memory_leaks[-50:],  # Last 50 memory leaks
                "operation_history_size": len(self.operation_history)
            }
            
            with open(export_file, "w") as f:
                import json
                json.dump(export_data, f, indent=2, default=str)
            
            await self.logger.info(
                "Profiling data exported", {"file": str(export_file)}
            )
            
        except Exception as e:
            await self.logger.warning(
                "Failed to export profiling data", {"error": str(e)}
            )


# Global profiler instance
_profiler: Optional[PerformanceProfiler] = None


def get_profiler() -> Optional[PerformanceProfiler]:
    """Get the global profiler instance"""
    return _profiler


def set_profiler(profiler: PerformanceProfiler) -> None:
    """Set the global profiler instance"""
    global _profiler
    _profiler = profiler


def profile_operation(operation_name: str = None):
    """Global decorator for profiling operations"""
    def decorator(func: Callable) -> Callable:
        profiler = get_profiler()
        if profiler:
            return profiler.profile_operation(operation_name)(func)
        return func
    return decorator 