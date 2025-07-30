# =============================================================================
# QuranBot - Bottleneck Analyzer
# =============================================================================
# Comprehensive performance bottleneck analysis tool.
# Analyzes system performance, identifies bottlenecks, and provides
# optimization recommendations for the QuranBot system.
# =============================================================================

import asyncio
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
import time
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_config
from src.core.performance_profiler import (
    PerformanceProfiler,
    ProfilerMode,
    profile_operation,
    set_profiler,
)
from src.core.structured_logger import StructuredLogger


class BottleneckAnalyzer:
    """
    Comprehensive bottleneck analysis tool for QuranBot.

    Features:
    - System-wide performance analysis
    - Operation-specific bottleneck detection
    - Memory leak identification
    - CPU usage analysis
    - I/O performance monitoring
    - Database performance analysis
    - Network latency detection
    - Optimization recommendations
    """

    def __init__(self, logger: StructuredLogger | None = None):
        """Initialize the bottleneck analyzer"""
        self.logger = logger or StructuredLogger("bottleneck_analyzer")
        self.profiler = None
        self.config = get_config()
        self.analysis_results = {}

    async def initialize(self) -> None:
        """Initialize the analyzer"""
        await self.logger.info("Initializing bottleneck analyzer")

        # Initialize profiler with detailed mode
        self.profiler = PerformanceProfiler(
            logger=self.logger,
            mode=ProfilerMode.DETAILED,
            enable_memory_tracking=True,
            enable_cpu_profiling=True,
            enable_line_profiling=False,  # Disable for production
            bottleneck_thresholds={
                "cpu_threshold": 70.0,  # Lower threshold for analysis
                "memory_threshold": 80.0,
                "operation_time_threshold": 0.5,  # 500ms threshold
                "memory_growth_threshold": 5.0,  # 5MB per minute
                "io_wait_threshold": 15.0,
            },
        )

        await self.profiler.initialize()
        set_profiler(self.profiler)

        await self.logger.info("Bottleneck analyzer initialized")

    async def shutdown(self) -> None:
        """Shutdown the analyzer"""
        if self.profiler:
            await self.profiler.shutdown()
        await self.logger.info("Bottleneck analyzer shutdown complete")

    @profile_operation("bottleneck_analysis")
    async def run_comprehensive_analysis(self) -> dict[str, Any]:
        """Run comprehensive bottleneck analysis"""
        await self.logger.info("Starting comprehensive bottleneck analysis")

        start_time = time.time()

        # Run all analysis components
        results = {
            "timestamp": datetime.now(UTC).isoformat(),
            "system_analysis": await self._analyze_system_performance(),
            "operation_analysis": await self._analyze_operations(),
            "memory_analysis": await self._analyze_memory_usage(),
            "database_analysis": await self._analyze_database_performance(),
            "network_analysis": await self._analyze_network_performance(),
            "cache_analysis": await self._analyze_cache_performance(),
            "audio_analysis": await self._analyze_audio_performance(),
            "webhook_analysis": await self._analyze_webhook_performance(),
            "overall_score": 0.0,
            "critical_issues": [],
            "recommendations": [],
        }

        # Calculate overall performance score
        results["overall_score"] = await self._calculate_performance_score(results)

        # Identify critical issues
        results["critical_issues"] = await self._identify_critical_issues(results)

        # Generate recommendations
        results["recommendations"] = await self._generate_recommendations(results)

        analysis_time = time.time() - start_time
        await self.logger.info(
            "Comprehensive analysis completed",
            {
                "analysis_time": f"{analysis_time:.2f}s",
                "overall_score": results["overall_score"],
                "critical_issues_count": len(results["critical_issues"]),
            },
        )

        return results

    async def _analyze_system_performance(self) -> dict[str, Any]:
        """Analyze overall system performance"""
        await self.logger.info("Analyzing system performance")

        # Get system metrics
        summary = await self.profiler.get_profiling_summary()
        system_metrics = summary["system_metrics"]

        # Analyze CPU usage
        cpu_score = 100.0 - system_metrics["cpu_percent"]
        cpu_status = (
            "excellent" if cpu_score > 80 else "good" if cpu_score > 60 else "poor"
        )

        # Analyze memory usage
        memory_score = 100.0 - system_metrics["memory_percent"]
        memory_status = (
            "excellent"
            if memory_score > 80
            else "good"
            if memory_score > 60
            else "poor"
        )

        # Analyze thread count
        thread_count = system_metrics["num_threads"]
        thread_status = (
            "good"
            if thread_count < 50
            else "warning"
            if thread_count < 100
            else "critical"
        )

        # Analyze open files
        open_files = system_metrics["open_files"]
        file_status = (
            "good"
            if open_files < 100
            else "warning"
            if open_files < 500
            else "critical"
        )

        return {
            "cpu": {
                "usage_percent": system_metrics["cpu_percent"],
                "score": cpu_score,
                "status": cpu_status,
                "issues": [] if cpu_score > 60 else ["High CPU usage detected"],
            },
            "memory": {
                "usage_percent": system_metrics["memory_percent"],
                "usage_mb": system_metrics["memory_rss_mb"],
                "score": memory_score,
                "status": memory_status,
                "issues": [] if memory_score > 60 else ["High memory usage detected"],
            },
            "threads": {
                "count": thread_count,
                "status": thread_status,
                "issues": [] if thread_count < 50 else ["High thread count detected"],
            },
            "files": {
                "count": open_files,
                "status": file_status,
                "issues": [] if open_files < 100 else ["High file descriptor count"],
            },
            "overall_score": (cpu_score + memory_score) / 2,
        }

    async def _analyze_operations(self) -> dict[str, Any]:
        """Analyze operation performance"""
        await self.logger.info("Analyzing operation performance")

        summary = await self.profiler.get_profiling_summary()
        top_operations = summary["top_operations"]

        # Analyze slow operations
        slow_operations = []
        for op in top_operations:
            if op["avg_time_ms"] > 100:  # Operations taking > 100ms
                slow_operations.append(
                    {
                        "name": op["name"],
                        "avg_time_ms": op["avg_time_ms"],
                        "max_time_ms": op["max_time_ms"],
                        "call_frequency": op["call_frequency"],
                        "severity": (
                            "critical"
                            if op["avg_time_ms"] > 1000
                            else "high"
                            if op["avg_time_ms"] > 500
                            else "medium"
                        ),
                    }
                )

        # Analyze frequent operations
        frequent_operations = []
        for op in top_operations:
            if op["call_frequency"] > 10:  # More than 10 calls per minute
                frequent_operations.append(
                    {
                        "name": op["name"],
                        "call_frequency": op["call_frequency"],
                        "avg_time_ms": op["avg_time_ms"],
                        "total_calls": op["total_calls"],
                    }
                )

        return {
            "total_operations": len(top_operations),
            "slow_operations": slow_operations,
            "frequent_operations": frequent_operations,
            "bottlenecks": summary["recent_bottlenecks"],
            "issues": (
                [
                    f"{len(slow_operations)} slow operations detected",
                    f"{len(frequent_operations)} high-frequency operations detected",
                ]
                if slow_operations or frequent_operations
                else []
            ),
        }

    async def _analyze_memory_usage(self) -> dict[str, Any]:
        """Analyze memory usage and leaks"""
        await self.logger.info("Analyzing memory usage")

        summary = await self.profiler.get_profiling_summary()
        memory_leaks = summary["memory_leaks"]

        # Get memory growth trends
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

        return {
            "memory_leaks_count": memory_leaks,
            "memory_growth_mb": memory_growth,
            "growth_rate_mb_per_minute": memory_growth
            / max(len(self.profiler.memory_snapshots), 1),
            "issues": (
                [
                    f"{memory_leaks} memory leaks detected",
                    f"Memory growth: {memory_growth:.2f}MB",
                ]
                if memory_leaks > 0 or memory_growth > 10
                else []
            ),
        }

    async def _analyze_database_performance(self) -> dict[str, Any]:
        """Analyze database performance"""
        await self.logger.info("Analyzing database performance")

        # This would analyze database connection pool, query performance, etc.
        # For now, return placeholder analysis
        return {
            "connection_pool_size": 0,
            "active_connections": 0,
            "query_performance": "unknown",
            "issues": ["Database analysis not implemented"],
        }

    async def _analyze_network_performance(self) -> dict[str, Any]:
        """Analyze network performance"""
        await self.logger.info("Analyzing network performance")

        # Analyze Discord API latency
        discord_latency = 0.0  # Would get from actual metrics

        return {
            "discord_api_latency_ms": discord_latency,
            "latency_status": "good" if discord_latency < 100 else "poor",
            "issues": [] if discord_latency < 100 else ["High Discord API latency"],
        }

    async def _analyze_cache_performance(self) -> dict[str, Any]:
        """Analyze cache performance"""
        await self.logger.info("Analyzing cache performance")

        # This would analyze cache hit rates, eviction rates, etc.
        return {
            "hit_rate": 0.0,
            "miss_rate": 0.0,
            "eviction_rate": 0.0,
            "issues": ["Cache analysis not implemented"],
        }

    async def _analyze_audio_performance(self) -> dict[str, Any]:
        """Analyze audio system performance"""
        await self.logger.info("Analyzing audio performance")

        # This would analyze audio processing, streaming performance, etc.
        return {
            "audio_processing_time_ms": 0.0,
            "streaming_latency_ms": 0.0,
            "buffer_underruns": 0,
            "issues": ["Audio analysis not implemented"],
        }

    async def _analyze_webhook_performance(self) -> dict[str, Any]:
        """Analyze webhook performance"""
        await self.logger.info("Analyzing webhook performance")

        # This would analyze webhook delivery times, failure rates, etc.
        return {
            "delivery_time_ms": 0.0,
            "failure_rate": 0.0,
            "queue_size": 0,
            "issues": ["Webhook analysis not implemented"],
        }

    async def _calculate_performance_score(self, results: dict[str, Any]) -> float:
        """Calculate overall performance score (0-100)"""
        scores = []

        # System performance score
        if "system_analysis" in results:
            scores.append(results["system_analysis"]["overall_score"])

        # Operation performance score (based on slow operations)
        if "operation_analysis" in results:
            slow_ops = len(results["operation_analysis"]["slow_operations"])
            op_score = max(0, 100 - (slow_ops * 10))  # -10 points per slow operation
            scores.append(op_score)

        # Memory score
        if "memory_analysis" in results:
            memory_leaks = results["memory_analysis"]["memory_leaks_count"]
            memory_score = max(0, 100 - (memory_leaks * 5))  # -5 points per memory leak
            scores.append(memory_score)

        return sum(scores) / len(scores) if scores else 0.0

    async def _identify_critical_issues(
        self, results: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Identify critical performance issues"""
        critical_issues = []

        # Check system issues
        if "system_analysis" in results:
            system = results["system_analysis"]
            if system["cpu"]["status"] == "poor":
                critical_issues.append(
                    {
                        "type": "system",
                        "component": "cpu",
                        "severity": "critical",
                        "description": f"High CPU usage: {system['cpu']['usage_percent']:.1f}%",
                        "impact": "System may become unresponsive",
                    }
                )

            if system["memory"]["status"] == "poor":
                critical_issues.append(
                    {
                        "type": "system",
                        "component": "memory",
                        "severity": "critical",
                        "description": f"High memory usage: {system['memory']['usage_percent']:.1f}%",
                        "impact": "Risk of out-of-memory errors",
                    }
                )

        # Check operation issues
        if "operation_analysis" in results:
            for op in results["operation_analysis"]["slow_operations"]:
                if op["severity"] == "critical":
                    critical_issues.append(
                        {
                            "type": "operation",
                            "component": op["name"],
                            "severity": "critical",
                            "description": f"Slow operation: {op['avg_time_ms']:.1f}ms average",
                            "impact": "User experience degradation",
                        }
                    )

        # Check memory issues
        if "memory_analysis" in results:
            memory = results["memory_analysis"]
            if memory["memory_leaks_count"] > 5:
                critical_issues.append(
                    {
                        "type": "memory",
                        "component": "leaks",
                        "severity": "critical",
                        "description": f"{memory['memory_leaks_count']} memory leaks detected",
                        "impact": "Memory usage will grow over time",
                    }
                )

        return critical_issues

    async def _generate_recommendations(
        self, results: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Generate optimization recommendations"""
        recommendations = []

        # System recommendations
        if "system_analysis" in results:
            system = results["system_analysis"]
            if system["cpu"]["status"] == "poor":
                recommendations.append(
                    {
                        "priority": "high",
                        "category": "system",
                        "title": "Optimize CPU usage",
                        "description": "High CPU usage detected. Consider optimizing algorithms and using async processing.",
                        "actions": [
                            "Profile CPU-intensive operations",
                            "Implement caching for expensive computations",
                            "Use async/await for I/O operations",
                            "Consider reducing polling frequencies",
                        ],
                    }
                )

            if system["memory"]["status"] == "poor":
                recommendations.append(
                    {
                        "priority": "high",
                        "category": "system",
                        "title": "Optimize memory usage",
                        "description": "High memory usage detected. Consider implementing memory cleanup.",
                        "actions": [
                            "Review object lifecycle management",
                            "Implement proper cleanup in long-running operations",
                            "Use weak references where appropriate",
                            "Monitor memory growth patterns",
                        ],
                    }
                )

        # Operation recommendations
        if "operation_analysis" in results:
            slow_ops = results["operation_analysis"]["slow_operations"]
            if slow_ops:
                recommendations.append(
                    {
                        "priority": "medium",
                        "category": "operations",
                        "title": "Optimize slow operations",
                        "description": f"{len(slow_ops)} slow operations detected. Consider optimization.",
                        "actions": [
                            "Profile each slow operation",
                            "Implement caching where appropriate",
                            "Consider async alternatives",
                            "Review algorithm efficiency",
                        ],
                    }
                )

        # Memory recommendations
        if "memory_analysis" in results:
            memory = results["memory_analysis"]
            if memory["memory_leaks_count"] > 0:
                recommendations.append(
                    {
                        "priority": "high",
                        "category": "memory",
                        "title": "Fix memory leaks",
                        "description": f"{memory['memory_leaks_count']} memory leaks detected.",
                        "actions": [
                            "Review object lifecycle management",
                            "Implement proper cleanup",
                            "Use context managers for resources",
                            "Monitor memory growth",
                        ],
                    }
                )

        return recommendations

    async def generate_report(self, results: dict[str, Any]) -> str:
        """Generate a human-readable performance report"""
        report = []
        report.append("=" * 60)
        report.append("QURANBOT PERFORMANCE ANALYSIS REPORT")
        report.append("=" * 60)
        report.append(f"Generated: {results['timestamp']}")
        report.append(f"Overall Score: {results['overall_score']:.1f}/100")
        report.append("")

        # Critical Issues
        if results["critical_issues"]:
            report.append("🚨 CRITICAL ISSUES:")
            report.append("-" * 30)
            for issue in results["critical_issues"]:
                report.append(f"• {issue['description']}")
                report.append(f"  Impact: {issue['impact']}")
                report.append("")
        else:
            report.append("✅ No critical issues detected")
            report.append("")

        # System Performance
        if "system_analysis" in results:
            system = results["system_analysis"]
            report.append("💻 SYSTEM PERFORMANCE:")
            report.append("-" * 30)
            report.append(
                f"CPU Usage: {system['cpu']['usage_percent']:.1f}% ({system['cpu']['status']})"
            )
            report.append(
                f"Memory Usage: {system['memory']['usage_percent']:.1f}% ({system['memory']['status']})"
            )
            report.append(
                f"Threads: {system['threads']['count']} ({system['threads']['status']})"
            )
            report.append(
                f"Open Files: {system['files']['count']} ({system['files']['status']})"
            )
            report.append("")

        # Operation Performance
        if "operation_analysis" in results:
            ops = results["operation_analysis"]
            report.append("⚡ OPERATION PERFORMANCE:")
            report.append("-" * 30)
            report.append(f"Total Operations: {ops['total_operations']}")
            report.append(f"Slow Operations: {len(ops['slow_operations'])}")
            report.append(f"Frequent Operations: {len(ops['frequent_operations'])}")
            report.append("")

        # Memory Analysis
        if "memory_analysis" in results:
            memory = results["memory_analysis"]
            report.append("🧠 MEMORY ANALYSIS:")
            report.append("-" * 30)
            report.append(f"Memory Leaks: {memory['memory_leaks_count']}")
            report.append(f"Memory Growth: {memory['memory_growth_mb']:.2f}MB")
            report.append("")

        # Recommendations
        if results["recommendations"]:
            report.append("💡 RECOMMENDATIONS:")
            report.append("-" * 30)
            for rec in results["recommendations"]:
                report.append(f"Priority: {rec['priority'].upper()}")
                report.append(f"Title: {rec['title']}")
                report.append(f"Description: {rec['description']}")
                report.append("Actions:")
                for action in rec["actions"]:
                    report.append(f"  • {action}")
                report.append("")

        report.append("=" * 60)
        report.append("End of Report")
        report.append("=" * 60)

        return "\n".join(report)

    async def export_results(
        self, results: dict[str, Any], filename: str = None
    ) -> str:
        """Export analysis results to JSON file"""
        if not filename:
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            filename = f"bottleneck_analysis_{timestamp}.json"

        export_path = Path("performance_data") / filename
        export_path.parent.mkdir(exist_ok=True)

        with open(export_path, "w") as f:
            json.dump(results, f, indent=2, default=str)

        await self.logger.info(f"Analysis results exported to {export_path}")
        return str(export_path)


async def main():
    """Main function for running bottleneck analysis"""
    logger = StructuredLogger("bottleneck_analyzer")

    try:
        # Initialize analyzer
        analyzer = BottleneckAnalyzer(logger)
        await analyzer.initialize()

        # Run comprehensive analysis
        results = await analyzer.run_comprehensive_analysis()

        # Generate and print report
        report = await analyzer.generate_report(results)
        print(report)

        # Export results
        export_path = await analyzer.export_results(results)
        print(f"\nResults exported to: {export_path}")

        # Shutdown
        await analyzer.shutdown()

    except Exception as e:
        await logger.error("Bottleneck analysis failed", {"error": str(e)})
        raise


if __name__ == "__main__":
    asyncio.run(main())
