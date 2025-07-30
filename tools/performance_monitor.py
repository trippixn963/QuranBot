# =============================================================================
# QuranBot - Performance Monitor
# =============================================================================
# Real-time performance monitoring and bottleneck detection tool.
# Integrates with existing performance systems to provide comprehensive
# monitoring, alerting, and optimization recommendations.
# =============================================================================

import asyncio
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import sys
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_config
from src.core.performance_profiler import (
    PerformanceProfiler,
    ProfilerMode,
    set_profiler,
)
from src.core.structured_logger import StructuredLogger


class QuranBotPerformanceMonitor:
    """
    Comprehensive performance monitoring system for QuranBot.

    Features:
    - Real-time system monitoring
    - Operation profiling
    - Bottleneck detection
    - Performance alerts
    - Historical trend analysis
    - Optimization recommendations
    """

    def __init__(self, logger: StructuredLogger | None = None):
        """Initialize the performance monitor"""
        self.logger = logger or StructuredLogger("performance_monitor")
        self.config = get_config()
        self.profiler = None
        self.performance_monitor = None
        self.monitoring_task = None
        self.shutdown_event = asyncio.Event()

        # Monitoring configuration
        self.monitoring_interval = 30  # seconds
        self.alert_thresholds = {
            "cpu_usage": 80.0,
            "memory_usage": 85.0,
            "operation_time": 1.0,  # seconds
            "memory_growth": 10.0,  # MB per minute
        }

        # Performance history
        self.performance_history = []
        self.max_history_size = 1000

    async def initialize(self) -> None:
        """Initialize the performance monitoring system"""
        await self.logger.info("Initializing QuranBot performance monitor")

        # Initialize profiler
        self.profiler = PerformanceProfiler(
            logger=self.logger,
            mode=ProfilerMode.DETAILED,
            enable_memory_tracking=True,
            enable_cpu_profiling=True,
            enable_line_profiling=False,
            bottleneck_thresholds={
                "cpu_threshold": self.alert_thresholds["cpu_usage"],
                "memory_threshold": self.alert_thresholds["memory_usage"],
                "operation_time_threshold": self.alert_thresholds["operation_time"],
                "memory_growth_threshold": self.alert_thresholds["memory_growth"],
                "io_wait_threshold": 20.0,
            },
        )

        await self.profiler.initialize()
        set_profiler(self.profiler)

        # Start monitoring task
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())

        await self.logger.info("Performance monitor initialized successfully")

    async def shutdown(self) -> None:
        """Shutdown the performance monitoring system"""
        await self.logger.info("Shutting down performance monitor")

        # Signal shutdown
        self.shutdown_event.set()

        # Cancel monitoring task
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

        # Shutdown profiler
        if self.profiler:
            await self.profiler.shutdown()

        await self.logger.info("Performance monitor shutdown complete")

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        await self.logger.info("Starting performance monitoring loop")

        while not self.shutdown_event.is_set():
            try:
                # Collect performance data
                performance_data = await self._collect_performance_data()

                # Store in history
                self.performance_history.append(performance_data)
                if len(self.performance_history) > self.max_history_size:
                    self.performance_history.pop(0)

                # Check for alerts
                alerts = await self._check_alerts(performance_data)
                if alerts:
                    await self._send_alerts(alerts)

                # Generate periodic report
                if len(self.performance_history) % 20 == 0:  # Every 20 cycles
                    await self._generate_periodic_report()

                # Export data periodically
                if len(self.performance_history) % 100 == 0:  # Every 100 cycles
                    await self._export_performance_data()

                # Wait for next cycle
                await asyncio.sleep(self.monitoring_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                await self.logger.error(
                    "Performance monitoring error", {"error": str(e)}
                )
                await asyncio.sleep(5)  # Brief pause before retry

    async def _collect_performance_data(self) -> dict[str, Any]:
        """Collect comprehensive performance data"""
        timestamp = datetime.now(UTC)

        # Get profiler summary
        profiler_summary = await self.profiler.get_profiling_summary()

        # Get system metrics
        system_metrics = profiler_summary["system_metrics"]

        # Calculate performance scores
        cpu_score = 100.0 - system_metrics["cpu_percent"]
        memory_score = 100.0 - system_metrics["memory_percent"]

        # Analyze operation performance
        operation_analysis = await self._analyze_operations(profiler_summary)

        # Memory analysis
        memory_analysis = await self._analyze_memory_usage()

        return {
            "timestamp": timestamp.isoformat(),
            "system_metrics": system_metrics,
            "performance_scores": {
                "cpu_score": cpu_score,
                "memory_score": memory_score,
                "overall_score": (cpu_score + memory_score) / 2,
            },
            "operation_analysis": operation_analysis,
            "memory_analysis": memory_analysis,
            "bottlenecks": profiler_summary["recent_bottlenecks"],
            "alerts": [],
        }

    async def _analyze_operations(
        self, profiler_summary: dict[str, Any]
    ) -> dict[str, Any]:
        """Analyze operation performance"""
        top_operations = profiler_summary["top_operations"]

        # Find slow operations
        slow_operations = [
            op
            for op in top_operations
            if op["avg_time_ms"] > 100  # > 100ms
        ]

        # Find frequent operations
        frequent_operations = [
            op
            for op in top_operations
            if op["call_frequency"] > 10  # > 10 calls per minute
        ]

        # Calculate operation health score
        total_ops = len(top_operations)
        slow_ops = len(slow_operations)
        operation_score = max(0, 100 - (slow_ops * 10))  # -10 points per slow operation

        return {
            "total_operations": total_ops,
            "slow_operations": slow_operations,
            "frequent_operations": frequent_operations,
            "operation_score": operation_score,
            "issues": (
                [
                    f"{slow_ops} slow operations detected",
                    f"{len(frequent_operations)} high-frequency operations detected",
                ]
                if slow_operations or frequent_operations
                else []
            ),
        }

    async def _analyze_memory_usage(self) -> dict[str, Any]:
        """Analyze memory usage patterns"""
        memory_leaks = len(self.profiler.memory_leaks)

        # Calculate memory growth rate
        memory_growth = 0.0
        if len(self.profiler.memory_snapshots) > 1:
            first_snapshot = self.profiler.memory_snapshots[0]
            last_snapshot = self.profiler.memory_snapshots[-1]
            memory_growth = (
                (
                    last_snapshot.statistics("filename")[0].size
                    - first_snapshot.statistics("filename")[0].size
                )
                / 1024
                / 1024
            )

        memory_score = max(0, 100 - (memory_leaks * 5) - (memory_growth * 2))

        return {
            "memory_leaks": memory_leaks,
            "memory_growth_mb": memory_growth,
            "memory_score": memory_score,
            "issues": (
                [
                    f"{memory_leaks} memory leaks detected",
                    f"Memory growth: {memory_growth:.2f}MB",
                ]
                if memory_leaks > 0 or memory_growth > 10
                else []
            ),
        }

    async def _check_alerts(
        self, performance_data: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Check for performance alerts"""
        alerts = []

        # System alerts
        system_metrics = performance_data["system_metrics"]

        # CPU alert
        if system_metrics["cpu_percent"] > self.alert_thresholds["cpu_usage"]:
            alerts.append(
                {
                    "type": "system",
                    "severity": (
                        "warning" if system_metrics["cpu_percent"] < 90 else "critical"
                    ),
                    "component": "cpu",
                    "message": f"High CPU usage: {system_metrics['cpu_percent']:.1f}%",
                    "value": system_metrics["cpu_percent"],
                    "threshold": self.alert_thresholds["cpu_usage"],
                }
            )

        # Memory alert
        if system_metrics["memory_percent"] > self.alert_thresholds["memory_usage"]:
            alerts.append(
                {
                    "type": "system",
                    "severity": (
                        "warning"
                        if system_metrics["memory_percent"] < 95
                        else "critical"
                    ),
                    "component": "memory",
                    "message": f"High memory usage: {system_metrics['memory_percent']:.1f}%",
                    "value": system_metrics["memory_percent"],
                    "threshold": self.alert_thresholds["memory_usage"],
                }
            )

        # Operation alerts
        operation_analysis = performance_data["operation_analysis"]
        for op in operation_analysis["slow_operations"]:
            if op["avg_time_ms"] > self.alert_thresholds["operation_time"] * 1000:
                alerts.append(
                    {
                        "type": "operation",
                        "severity": (
                            "warning" if op["avg_time_ms"] < 5000 else "critical"
                        ),
                        "component": op["name"],
                        "message": f"Slow operation: {op['avg_time_ms']:.1f}ms average",
                        "value": op["avg_time_ms"],
                        "threshold": self.alert_thresholds["operation_time"] * 1000,
                    }
                )

        # Memory leak alerts
        memory_analysis = performance_data["memory_analysis"]
        if memory_analysis["memory_leaks"] > 5:
            alerts.append(
                {
                    "type": "memory",
                    "severity": "critical",
                    "component": "leaks",
                    "message": f"{memory_analysis['memory_leaks']} memory leaks detected",
                    "value": memory_analysis["memory_leaks"],
                    "threshold": 5,
                }
            )

        return alerts

    async def _send_alerts(self, alerts: list[dict[str, Any]]) -> None:
        """Send performance alerts"""
        for alert in alerts:
            await self.logger.warning(
                f"Performance alert: {alert['message']}",
                {
                    "type": alert["type"],
                    "severity": alert["severity"],
                    "component": alert["component"],
                    "value": alert["value"],
                    "threshold": alert["threshold"],
                },
            )

    async def _generate_periodic_report(self) -> None:
        """Generate periodic performance report"""
        if not self.performance_history:
            return

        # Calculate trends
        recent_data = self.performance_history[-20:]  # Last 20 data points

        # Calculate average scores
        avg_cpu_score = sum(
            d["performance_scores"]["cpu_score"] for d in recent_data
        ) / len(recent_data)
        avg_memory_score = sum(
            d["performance_scores"]["memory_score"] for d in recent_data
        ) / len(recent_data)
        avg_overall_score = sum(
            d["performance_scores"]["overall_score"] for d in recent_data
        ) / len(recent_data)

        # Count alerts
        total_alerts = sum(len(d.get("alerts", [])) for d in recent_data)

        await self.logger.info(
            "Periodic performance report",
            {
                "avg_cpu_score": f"{avg_cpu_score:.1f}",
                "avg_memory_score": f"{avg_memory_score:.1f}",
                "avg_overall_score": f"{avg_overall_score:.1f}",
                "total_alerts": total_alerts,
                "data_points": len(recent_data),
            },
        )

    async def _export_performance_data(self) -> None:
        """Export performance data to file"""
        try:
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            export_path = (
                Path("performance_data") / f"performance_monitor_{timestamp}.json"
            )
            export_path.parent.mkdir(exist_ok=True)

            export_data = {
                "timestamp": datetime.now(UTC).isoformat(),
                "monitoring_config": {
                    "interval": self.monitoring_interval,
                    "alert_thresholds": self.alert_thresholds,
                },
                "performance_history": self.performance_history[
                    -100:
                ],  # Last 100 data points
                "summary": {
                    "total_data_points": len(self.performance_history),
                    "avg_overall_score": (
                        sum(
                            d["performance_scores"]["overall_score"]
                            for d in self.performance_history
                        )
                        / len(self.performance_history)
                        if self.performance_history
                        else 0
                    ),
                    "total_alerts": sum(
                        len(d.get("alerts", [])) for d in self.performance_history
                    ),
                },
            }

            with open(export_path, "w") as f:
                json.dump(export_data, f, indent=2, default=str)

            await self.logger.info(
                "Performance data exported", {"file": str(export_path)}
            )

        except Exception as e:
            await self.logger.warning(
                "Failed to export performance data", {"error": str(e)}
            )

    async def get_current_status(self) -> dict[str, Any]:
        """Get current performance status"""
        if not self.performance_history:
            return {"status": "no_data"}

        latest_data = self.performance_history[-1]

        # Determine overall status
        overall_score = latest_data["performance_scores"]["overall_score"]
        if overall_score >= 80:
            status = "excellent"
        elif overall_score >= 60:
            status = "good"
        elif overall_score >= 40:
            status = "fair"
        else:
            status = "poor"

        return {
            "status": status,
            "overall_score": overall_score,
            "cpu_score": latest_data["performance_scores"]["cpu_score"],
            "memory_score": latest_data["performance_scores"]["memory_score"],
            "system_metrics": latest_data["system_metrics"],
            "operation_analysis": latest_data["operation_analysis"],
            "memory_analysis": latest_data["memory_analysis"],
            "recent_alerts": len(latest_data.get("alerts", [])),
            "data_points": len(self.performance_history),
        }

    async def get_performance_trends(self, hours: int = 24) -> dict[str, Any]:
        """Get performance trends over time"""
        if not self.performance_history:
            return {"status": "no_data"}

        # Filter data for the specified time period
        cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
        recent_data = [
            d
            for d in self.performance_history
            if datetime.fromisoformat(d["timestamp"]) > cutoff_time
        ]

        if not recent_data:
            return {"status": "no_data_for_period"}

        # Calculate trends
        cpu_scores = [d["performance_scores"]["cpu_score"] for d in recent_data]
        memory_scores = [d["performance_scores"]["memory_score"] for d in recent_data]
        overall_scores = [d["performance_scores"]["overall_score"] for d in recent_data]

        return {
            "period_hours": hours,
            "data_points": len(recent_data),
            "trends": {
                "cpu_score": {
                    "min": min(cpu_scores),
                    "max": max(cpu_scores),
                    "avg": sum(cpu_scores) / len(cpu_scores),
                    "trend": (
                        "improving" if cpu_scores[-1] > cpu_scores[0] else "declining"
                    ),
                },
                "memory_score": {
                    "min": min(memory_scores),
                    "max": max(memory_scores),
                    "avg": sum(memory_scores) / len(memory_scores),
                    "trend": (
                        "improving"
                        if memory_scores[-1] > memory_scores[0]
                        else "declining"
                    ),
                },
                "overall_score": {
                    "min": min(overall_scores),
                    "max": max(overall_scores),
                    "avg": sum(overall_scores) / len(overall_scores),
                    "trend": (
                        "improving"
                        if overall_scores[-1] > overall_scores[0]
                        else "declining"
                    ),
                },
            },
            "alerts_count": sum(len(d.get("alerts", [])) for d in recent_data),
        }


async def main():
    """Main function for running the performance monitor"""
    logger = StructuredLogger("performance_monitor")

    try:
        # Initialize monitor
        monitor = QuranBotPerformanceMonitor(logger)
        await monitor.initialize()

        print("🚀 QuranBot Performance Monitor Started")
        print("Press Ctrl+C to stop monitoring")
        print("-" * 50)

        # Main monitoring loop
        while True:
            try:
                # Get current status
                status = await monitor.get_current_status()

                # Print status
                print(f"\n📊 Performance Status: {status['status'].upper()}")
                print(f"Overall Score: {status['overall_score']:.1f}/100")
                print(f"CPU Score: {status['cpu_score']:.1f}/100")
                print(f"Memory Score: {status['memory_score']:.1f}/100")
                print(f"Recent Alerts: {status['recent_alerts']}")

                # Print trends every 10 cycles
                if len(monitor.performance_history) % 10 == 0:
                    trends = await monitor.get_performance_trends(hours=1)
                    if trends["status"] == "no_data":
                        print("No trend data available")
                    else:
                        print("\n📈 1-Hour Trends:")
                        print(f"CPU: {trends['trends']['cpu_score']['trend']}")
                        print(f"Memory: {trends['trends']['memory_score']['trend']}")
                        print(f"Overall: {trends['trends']['overall_score']['trend']}")

                await asyncio.sleep(30)  # Update every 30 seconds

            except KeyboardInterrupt:
                print("\n🛑 Stopping performance monitor...")
                break
            except Exception as e:
                await logger.error("Performance monitor error", {"error": str(e)})
                await asyncio.sleep(5)

        # Shutdown
        await monitor.shutdown()
        print("✅ Performance monitor stopped")

    except Exception as e:
        await logger.error("Performance monitor failed", {"error": str(e)})
        raise


if __name__ == "__main__":
    asyncio.run(main())
