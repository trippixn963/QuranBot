# =============================================================================
# QuranBot - Daily Health Reporter
# =============================================================================
# Generates and sends daily health reports via webhook for VPS monitoring
# =============================================================================

import asyncio
from datetime import datetime, timedelta
import time
from typing import Any

from ..core.logger import StructuredLogger


class DailyHealthReporter:
    """Generate and send daily health reports for 24/7 VPS monitoring."""

    def __init__(
        self, logger: StructuredLogger, webhook_router=None, system_monitor=None, performance_monitor=None
    ):
        self.logger = logger
        self.webhook_router = webhook_router
        self.system_monitor = system_monitor
        self.performance_monitor = performance_monitor
        self.reporting_active = False
        self.report_task = None
        self.last_report_time = 0

        # Statistics tracking
        self.daily_stats = {
            "audio_sessions": 0,
            "user_interactions": 0,
            "voice_joins": 0,
            "voice_leaves": 0,
            "errors": 0,
            "warnings": 0,
            "database_operations": 0,
            "api_calls": 0,
        }

    async def start_daily_reporting(self, report_hour: int = 9):
        """Start daily health reporting at specified hour (24h format)."""
        if self.reporting_active:
            return

        self.reporting_active = True
        self.report_task = asyncio.create_task(self._daily_report_loop(report_hour))
        await self.logger.info(
            f"Daily health reporting started - reports at {report_hour}:00"
        )

    async def stop_daily_reporting(self):
        """Stop daily health reporting."""
        self.reporting_active = False
        if self.report_task:
            self.report_task.cancel()
            try:
                await self.report_task
            except asyncio.CancelledError:
                pass
        await self.logger.info("Daily health reporting stopped")

    async def _daily_report_loop(self, report_hour: int):
        """Main daily reporting loop."""
        while self.reporting_active:
            try:
                now = datetime.now()

                # Calculate next report time
                next_report = now.replace(
                    hour=report_hour, minute=0, second=0, microsecond=0
                )
                if now >= next_report:
                    next_report += timedelta(days=1)

                # Wait until report time
                wait_seconds = (next_report - now).total_seconds()
                await asyncio.sleep(wait_seconds)

                if self.reporting_active:
                    await self._generate_and_send_daily_report()

            except asyncio.CancelledError:
                break
            except Exception as e:
                await self.logger.error("Error in daily report loop", {"error": str(e)})
                await asyncio.sleep(3600)  # Wait 1 hour before retry

    async def _generate_and_send_daily_report(self):
        """Generate and send the daily health report."""
        try:
            report_data = await self._collect_daily_metrics()
            await self._send_daily_report(report_data)
            self.last_report_time = time.time()

            # Reset daily stats
            self.daily_stats = {key: 0 for key in self.daily_stats}

        except Exception as e:
            await self.logger.error(
                "Failed to generate daily report", {"error": str(e)}
            )

    async def _collect_daily_metrics(self) -> dict[str, Any]:
        """Collect metrics for the daily report."""
        now = datetime.now()

        # Get system status
        system_status = {}
        if self.system_monitor:
            system_status = await self.system_monitor.get_system_status()

        # Calculate uptime
        uptime_hours = system_status.get("uptime_hours", 0)

        # Get Discord API health if available
        api_health = {}
        try:
            from ..utils.api_monitor import get_discord_monitor

            monitor = get_discord_monitor()
            if monitor:
                api_health = monitor.get_current_health()
        except Exception:
            pass

        # Get performance metrics if available
        performance_metrics = {}
        if self.performance_monitor:
            try:
                performance_metrics = await self.performance_monitor.get_performance_summary()
            except Exception:
                pass

        return {
            "report_date": now.strftime("%Y-%m-%d"),
            "report_time": now.strftime("%H:%M:%S UTC"),
            "system_status": system_status,
            "api_health": api_health,
            "performance_metrics": performance_metrics,
            "daily_stats": self.daily_stats.copy(),
            "uptime_hours": uptime_hours,
            "overall_health": self._calculate_overall_health(system_status, api_health),
        }

    async def _send_daily_report(self, report_data: dict[str, Any]):
        """Send the daily health report via webhook."""
        if not self.webhook_router:
            return

        try:
            from ..core.webhook_logger import LogLevel

            # Determine report level based on health
            overall_health = report_data.get("overall_health", "unknown")
            if overall_health == "critical":
                level = LogLevel.CRITICAL
                emoji = "🚨"
            elif overall_health == "warning":
                level = LogLevel.WARNING
                emoji = "⚠️"
            else:
                level = LogLevel.INFO
                emoji = "📊"

            # Format system status
            system_status = report_data.get("system_status", {})
            cpu_status = system_status.get("cpu", {})
            memory_status = system_status.get("memory", {})
            disk_status = system_status.get("disk", {})

            # Format daily stats
            stats = report_data.get("daily_stats", {})
            performance = report_data.get("performance_metrics", {})

            # Create enhanced context with better field names and formatting
            context = {
                "Report Date": report_data.get("report_date"),
                "System Uptime": f"{report_data.get('uptime_hours', 0):.1f} hours",
                "Overall Health": overall_health.upper(),
                "CPU Usage": f"{cpu_status.get('usage_percent', 0):.1f}%",
                "Memory Usage": f"{memory_status.get('usage_percent', 0):.1f}%",
                "Disk Usage": f"{disk_status.get('usage_percent', 0):.1f}%",
                "Audio Sessions": f"{stats.get('audio_sessions', 0)} sessions",
                "User Interactions": f"{stats.get('user_interactions', 0)} interactions",
                "Voice Activity": f"{stats.get('voice_joins', 0)} joins, {stats.get('voice_leaves', 0)} leaves",
                "Errors Today": f"{stats.get('errors', 0)} errors",
                "Warnings Today": f"{stats.get('warnings', 0)} warnings",
                "System Status": overall_health.upper(),
            }
            
            # Add performance metrics if available
            if performance:
                commands = performance.get("commands", {})
                database = performance.get("database", {})
                memory = performance.get("memory", {})
                api = performance.get("api", {})
                
                context.update({
                    "Avg Command Time": f"{commands.get('avg_response_time', 0):.2f}s",
                    "Slow Commands": f"{commands.get('slow_commands', 0)} commands",
                    "Command Success Rate": f"{commands.get('success_rate', 100):.1f}%",
                    "Avg Query Time": f"{database.get('avg_query_time', 0):.3f}s",
                    "Slow Queries": f"{database.get('slow_queries', 0)} queries",
                    "Memory Trend": f"{memory.get('trend_mb', 0):+.1f} MB",
                    "Max API Usage": f"{api.get('max_usage_percent', 0):.1f}%",
                })

            # Build description with performance metrics
            description_parts = [
                f"**24/7 VPS Health Report**",
                f"",
                f"System Status: **{overall_health.upper()}**",
                f"Uptime: {report_data.get('uptime_hours', 0):.1f} hours",
                f"",
                f"**Resource Usage:**",
                f"• CPU: {cpu_status.get('usage_percent', 0):.1f}%",
                f"• Memory: {memory_status.get('usage_percent', 0):.1f}%",
                f"• Disk: {disk_status.get('usage_percent', 0):.1f}%",
                f"",
                f"**Bot Activity:**",
                f"• Audio Sessions: {stats.get('audio_sessions', 0)}",
                f"• User Interactions: {stats.get('user_interactions', 0)}",
                f"• Voice Channel Activity: {stats.get('voice_joins', 0)} joins, {stats.get('voice_leaves', 0)} leaves",
            ]
            
            # Add performance metrics if available
            if performance:
                commands = performance.get("commands", {})
                database = performance.get("database", {})
                api = performance.get("api", {})
                
                description_parts.extend([
                    f"",
                    f"**Performance Metrics:**",
                    f"• Avg Command Response: {commands.get('avg_response_time', 0):.2f}s",
                    f"• Slow Commands: {commands.get('slow_commands', 0)}",
                    f"• Avg Database Query: {database.get('avg_query_time', 0):.3f}s",
                    f"• Max API Usage: {api.get('max_usage_percent', 0):.1f}%",
                ])
            
            description_parts.extend([
                f"",
                f"**Issues:**",
                f"• Errors: {stats.get('errors', 0)}",
                f"• Warnings: {stats.get('warnings', 0)}",
            ])
            
            description = "\n".join(description_parts)

            await self.webhook_router.route_event(
                event_type="daily_health_report",
                title=f"{emoji} Daily Health Report - {report_data.get('report_date')}",
                description=description,
                level=level,
                context=context,
                force_channel=None,  # Let router decide channel
            )

        except Exception as e:
            await self.logger.error("Failed to send daily report", {"error": str(e)})

    def _calculate_overall_health(self, system_status: dict, api_health: dict) -> str:
        """Calculate overall system health."""
        # Check system resources
        if system_status:
            cpu_status = system_status.get("cpu", {}).get("status", "healthy")
            memory_status = system_status.get("memory", {}).get("status", "healthy")
            disk_status = system_status.get("disk", {}).get("status", "healthy")

            if any(
                status == "critical"
                for status in [cpu_status, memory_status, disk_status]
            ):
                return "critical"
            elif any(
                status == "warning"
                for status in [cpu_status, memory_status, disk_status]
            ):
                return "warning"

        # Check API health
        if api_health:
            api_status = api_health.get("status", "healthy")
            if api_status in ["critical", "warning"]:
                return api_status

        return "healthy"

    def increment_stat(self, stat_name: str, amount: int = 1):
        """Increment a daily statistic."""
        if stat_name in self.daily_stats:
            self.daily_stats[stat_name] += amount
