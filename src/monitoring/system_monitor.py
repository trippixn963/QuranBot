# =============================================================================
# QuranBot - System Resource Monitor
# =============================================================================
# Monitors system resources (CPU, memory, disk) and sends webhook alerts
# for 24/7 VPS monitoring
# =============================================================================

import asyncio
import time
from typing import Any, Dict

import psutil

from ..core.logger import StructuredLogger


class SystemResourceMonitor:
    """Monitor system resources and send webhook alerts for VPS monitoring."""

    def __init__(self, logger: StructuredLogger, webhook_router=None):
        self.logger = logger
        self.webhook_router = webhook_router
        self.monitoring = False
        self.monitor_task = None

        # Thresholds for alerts
        self.cpu_warning_threshold = 80.0  # %
        self.cpu_critical_threshold = 95.0  # %
        self.memory_warning_threshold = 85.0  # %
        self.memory_critical_threshold = 95.0  # %
        self.disk_warning_threshold = 90.0  # %
        self.disk_critical_threshold = 95.0  # %

        # Alert cooldowns (seconds)
        self.last_cpu_alert = 0
        self.last_memory_alert = 0
        self.last_disk_alert = 0
        self.alert_cooldown = 300  # 5 minutes

    async def start_monitoring(self, interval_seconds: int = 60):
        """Start system resource monitoring."""
        if self.monitoring:
            return

        self.monitoring = True
        self.monitor_task = asyncio.create_task(self._monitor_loop(interval_seconds))
        await self.logger.info("System resource monitoring started")

    async def stop_monitoring(self):
        """Stop system resource monitoring."""
        self.monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        await self.logger.info("System resource monitoring stopped")
    
    async def _monitor_loop(self, interval_seconds: int):
        """Main monitoring loop."""
        while self.monitoring:
            try:
                await self._check_system_resources()
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                await self.logger.error("Error in system monitoring loop", {"error": str(e)})
                await asyncio.sleep(interval_seconds)

    async def _check_system_resources(self):
        """Check system resources and send alerts if needed."""
        current_time = time.time()

        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # Check CPU usage
        if cpu_percent >= self.cpu_critical_threshold:
            if current_time - self.last_cpu_alert > self.alert_cooldown:
                await self._send_resource_alert(
                    "cpu", "critical", cpu_percent,
                    f"🚨 CRITICAL: CPU usage at {cpu_percent:.1f}%"
                )
                self.last_cpu_alert = current_time
        elif cpu_percent >= self.cpu_warning_threshold:
            if current_time - self.last_cpu_alert > self.alert_cooldown:
                await self._send_resource_alert(
                    "cpu", "warning", cpu_percent,
                    f"⚠️ WARNING: High CPU usage at {cpu_percent:.1f}%"
                )
                self.last_cpu_alert = current_time

        # Check memory usage
        memory_percent = memory.percent
        if memory_percent >= self.memory_critical_threshold:
            if current_time - self.last_memory_alert > self.alert_cooldown:
                await self._send_resource_alert(
                    "memory", "critical", memory_percent,
                    f"🚨 CRITICAL: Memory usage at {memory_percent:.1f}%"
                )
                self.last_memory_alert = current_time
        elif memory_percent >= self.memory_warning_threshold:
            if current_time - self.last_memory_alert > self.alert_cooldown:
                await self._send_resource_alert(
                    "memory", "warning", memory_percent,
                    f"⚠️ WARNING: High memory usage at {memory_percent:.1f}%"
                )
                self.last_memory_alert = current_time

        # Check disk usage
        disk_percent = disk.percent
        if disk_percent >= self.disk_critical_threshold:
            if current_time - self.last_disk_alert > self.alert_cooldown:
                await self._send_resource_alert(
                    "disk", "critical", disk_percent,
                    f"🚨 CRITICAL: Disk usage at {disk_percent:.1f}%"
                )
                self.last_disk_alert = current_time
        elif disk_percent >= self.disk_warning_threshold:
            if current_time - self.last_disk_alert > self.alert_cooldown:
                await self._send_resource_alert(
                    "disk", "warning", disk_percent,
                    f"⚠️ WARNING: High disk usage at {disk_percent:.1f}%"
                )
                self.last_disk_alert = current_time
 async def _send_resource_alert(self, resource_type: str, severity: str, value: float, title: str):
        """Send resource usage alert via webhook."""
        if not self.webhook_router:
            return

        try:
            from ..core.webhook_logger import LogLevel

            level = LogLevel.CRITICAL if severity == "critical" else LogLevel.WARNING

            # Get additional system info
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            cpu_count = psutil.cpu_count()

            context = {
                "resource_type": resource_type,
                "current_value": f"{value:.1f}%",
                "severity": severity,
                "cpu_usage": f"{psutil.cpu_percent():.1f}%",
                "cpu_cores": cpu_count,
                "memory_usage": f"{memory.percent:.1f}%",
                "memory_available": f"{memory.available / (1024**3):.1f}GB",
                "disk_usage": f"{disk.percent:.1f}%",
                "disk_free": f"{disk.free / (1024**3):.1f}GB",
            }

            await self.webhook_router.route_event(
                event_type=f"system_{resource_type}_{severity}",
                title=title,
                description=f"VPS resource usage alert - immediate attention may be required",
                level=level,
                context=context
            )

        except Exception as e:
            await self.logger.error("Failed to send resource alert", {"error": str(e)})

    async def get_system_status(self) -> Dict[str, Any]:
        """Get current system status."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            boot_time = psutil.boot_time()

            return {
                "cpu": {
                    "usage_percent": cpu_percent,
                    "cores": psutil.cpu_count(),
                    "status": "critical" if cpu_percent >= self.cpu_critical_threshold
                             else "warning" if cpu_percent >= self.cpu_warning_threshold
                             else "healthy"
                },
                "memory": {
                    "usage_percent": memory.percent,
                    "total_gb": memory.total / (1024**3),
                    "available_gb": memory.available / (1024**3),
                    "status": "critical" if memory.percent >= self.memory_critical_threshold
                             else "warning" if memory.percent >= self.memory_warning_threshold
                             else "healthy"
                },
                "disk": {
                    "usage_percent": disk.percent,
                    "total_gb": disk.total / (1024**3),
                    "free_gb": disk.free / (1024**3),
                    "status": "critical" if disk.percent >= self.disk_critical_threshold
                             else "warning" if disk.percent >= self.disk_warning_threshold
                             else "healthy"
                },
                "uptime_hours": (time.time() - boot_time) / 3600,
                "overall_status": self._get_overall_status(cpu_percent, memory.percent, disk.percent)
            }
        except Exception as e:
            await self.logger.error("Failed to get system status", {"error": str(e)})
            return {"error": str(e)}

    def _get_overall_status(self, cpu: float, memory: float, disk: float) -> str:
        """Determine overall system status."""
        if any(x >= 95 for x in [cpu, memory, disk]):
            return "critical"
        elif any(x >= 80 for x in [cpu, memory, disk]):
            return "warning"
        else:
            return "healthy"
