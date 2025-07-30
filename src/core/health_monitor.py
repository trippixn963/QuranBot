# =============================================================================
# QuranBot - Health Monitor System
# =============================================================================
# Comprehensive health monitoring with structured logging
# Monitors audio, JSON files, performance, and sends regular status updates
# =============================================================================

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..utils.tree_log import log_error_with_traceback, log_perfect_tree_section
from .logger import StructuredLogger



class HealthStatus:
    """Health status levels"""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class HealthCheck:
    """Individual health check result"""

    def __init__(
        self, name: str, status: str, message: str, details: dict[str, Any] = None
    ):
        self.name = name
        self.status = status
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now(UTC)


class HealthMonitor:
    """
    Comprehensive health monitoring system for QuranBot.

    Features:
    - Regular health status logging (hourly)
    - Audio playback monitoring with alerts
    - JSON file integrity monitoring
    - Performance and memory monitoring
    - System resource monitoring
    - Critical alert notifications
    - Daily summary reports
    """

    def __init__(
        self,
        logger: StructuredLogger,
        data_dir: Path = None,
        check_interval_minutes: int = 60,
        alert_interval_minutes: int = 60,
    ):
        """
        Initialize health monitor.

        Args:
            logger: Structured logger instance
            data_dir: Data directory to monitor
            check_interval_minutes: Regular health check interval (default: 60 min)
            alert_interval_minutes: Critical alert check interval (default: 5 min)
        """
        self.logger = logger
        self.data_dir = data_dir or Path("data")
        self.check_interval_minutes = check_interval_minutes
        self.alert_interval_minutes = alert_interval_minutes

        # Health tracking
        self.last_health_report = None
        self.last_audio_activity = None
        self.last_successful_save = {}
        self.consecutive_warnings = {}
        self.alert_history = []

        # Background tasks
        self.monitor_task = None
        self.alert_task = None
        self.is_monitoring = False

        # SQLite database health monitoring
        self.database_health_stats = {
            "last_check": None,
            "size_mb": 0.0,
            "table_count": 0,
            "record_count": 0,
            "last_backup": None,
            "integrity_status": "unknown",
            "wal_status": "unknown",
            "connection_test": False,
        }

    async def start_monitoring(self) -> None:
        """Start the health monitoring system"""
        if self.is_monitoring:
            await self.logger.warning("Health monitor already running")
            return

        self.is_monitoring = True

        # Start background tasks
        self.monitor_task = asyncio.create_task(self._health_monitor_loop())
        self.alert_task = asyncio.create_task(self._alert_monitor_loop())

        await self.logger.info(
            "Health monitor started",
            {
                "check_interval": f"{self.check_interval_minutes} minutes",
                "alert_interval": f"{self.alert_interval_minutes} minutes",
                "logging_enabled": True,
            },
        )

        log_perfect_tree_section(
            "Health Monitor - Started",
            [
                ("status", "🟢 Monitoring active"),
                ("health_checks", f"⏰ Every {self.check_interval_minutes} minutes"),
                ("critical_alerts", f"🚨 Every {self.alert_interval_minutes} minutes"),
                (
                    "logging",
                    "✅ Enabled",
                ),
            ],
            "💚",
        )



    async def stop_monitoring(self) -> None:
        """Stop the health monitoring system"""
        if not self.is_monitoring:
            return

        self.is_monitoring = False

        # Cancel tasks
        if self.monitor_task and not self.monitor_task.done():
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass

        if self.alert_task and not self.alert_task.done():
            self.alert_task.cancel()
            try:
                await self.alert_task
            except asyncio.CancelledError:
                pass

        await self.logger.info("Health monitor stopped")

        # Send shutdown notification
        if self.webhook_logger:
            await self._send_shutdown_notification()

    async def _health_monitor_loop(self) -> None:
        """Main health monitoring loop"""
        while self.is_monitoring:
            try:
                # Wait for interval
                await asyncio.sleep(self.check_interval_minutes * 60)

                if not self.is_monitoring:
                    break

                # Perform comprehensive health check
                await self._perform_health_check()

            except asyncio.CancelledError:
                break
            except Exception as e:
                await self.logger.error(
                    "Error in health monitor loop", {"error": str(e)}
                )
                log_error_with_traceback("Health monitor loop error", e)
                # Wait before retrying
                await asyncio.sleep(300)  # 5 minutes

    async def _alert_monitor_loop(self) -> None:
        """Critical alert monitoring loop"""
        while self.is_monitoring:
            try:
                # Wait for alert interval
                await asyncio.sleep(self.alert_interval_minutes * 60)

                if not self.is_monitoring:
                    break

                # Check for critical issues
                await self._check_critical_alerts()

            except asyncio.CancelledError:
                break
            except Exception as e:
                await self.logger.error(
                    "Error in alert monitor loop", {"error": str(e)}
                )
                log_error_with_traceback("Alert monitor loop error", e)
                await asyncio.sleep(60)  # 1 minute

    async def _perform_health_check(self) -> None:
        """Perform comprehensive health check and send webhook report"""
        try:
            health_checks = []

            # Audio health check
            audio_check = await self._check_audio_health()
            health_checks.append(audio_check)

            # SQLite database health check
            database_check = await self._check_database_health()
            health_checks.append(database_check)

            # Memory and performance check
            performance_check = await self._check_performance()
            health_checks.append(performance_check)

            # System uptime check
            uptime_check = await self._check_system_uptime()
            health_checks.append(uptime_check)

            # Data backup check
            backup_check = await self._check_backup_status()
            health_checks.append(backup_check)

            # Overall health assessment
            overall_status = self._assess_overall_health(health_checks)

            

            self.last_health_report = datetime.now(UTC)

            await self.logger.info(
                "Health check completed",
                {
                    "overall_status": overall_status,
                    "checks_performed": len(health_checks),
                    "logging_enabled": True,
                },
            )

        except Exception as e:
            await self.logger.error("Error performing health check", {"error": str(e)})
            log_error_with_traceback("Health check error", e)

    async def _check_critical_alerts(self) -> None:
        """Check for critical issues that need immediate alerts"""
        try:
            alerts = []

            # Check if audio has been stuck for too long
            audio_stuck_alert = await self._check_audio_stuck()
            if audio_stuck_alert:
                alerts.append(audio_stuck_alert)

            # Check for repeated JSON errors
            json_error_alert = await self._check_json_errors()
            if json_error_alert:
                alerts.append(json_error_alert)

            # Check memory usage
            memory_alert = await self._check_memory_usage()
            if memory_alert:
                alerts.append(memory_alert)

            # Send critical alerts
            for alert in alerts:
                if self.webhook_logger:
                    await self._send_critical_alert(alert)

        except Exception as e:
            await self.logger.error("Error checking critical alerts", {"error": str(e)})

    async def _check_audio_health(self) -> HealthCheck:
        """Check audio playback health"""
        try:
            # This would integrate with your AudioService
            # For now, we'll check if FFmpeg processes are running
            import psutil

            ffmpeg_processes = []
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    if proc.info["name"] == "ffmpeg":
                        ffmpeg_processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if ffmpeg_processes:
                return HealthCheck(
                    name="Audio Playback",
                    status=HealthStatus.HEALTHY,
                    message=f"✅ Audio active ({len(ffmpeg_processes)} FFmpeg processes)",
                    details={
                        "ffmpeg_processes": len(ffmpeg_processes),
                        "last_check": datetime.now(UTC).isoformat(),
                    },
                )
            else:
                return HealthCheck(
                    name="Audio Playback",
                    status=HealthStatus.CRITICAL,
                    message="❌ No audio processes detected",
                    details={"ffmpeg_processes": 0},
                )

        except Exception as e:
            return HealthCheck(
                name="Audio Playback",
                status=HealthStatus.WARNING,
                message=f"⚠️ Could not check audio status: {e}",
                details={"error": str(e)},
            )

    # JSON integrity check removed - replaced with SQLite database health monitoring

    async def _check_performance(self) -> HealthCheck:
        """Check system performance metrics"""
        try:
            import psutil

            # Get current process info
            process = psutil.Process()
            memory_info = process.memory_info()
            cpu_percent = process.cpu_percent()

            # System info
            system_memory = psutil.virtual_memory()

            memory_mb = memory_info.rss / 1024 / 1024
            memory_percent = (memory_info.rss / system_memory.total) * 100

            # Determine status based on usage
            if memory_mb > 500:  # More than 500MB
                status = HealthStatus.WARNING
                message = f"⚠️ High memory usage: {memory_mb:.1f}MB"
            elif cpu_percent > 80:  # More than 80% CPU
                status = HealthStatus.WARNING
                message = f"⚠️ High CPU usage: {cpu_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"✅ Performance normal: {memory_mb:.1f}MB RAM, {cpu_percent:.1f}% CPU"

            return HealthCheck(
                name="Performance",
                status=status,
                message=message,
                details={
                    "memory_mb": round(memory_mb, 1),
                    "memory_percent": round(memory_percent, 1),
                    "cpu_percent": round(cpu_percent, 1),
                    "system_memory_available_gb": round(
                        system_memory.available / 1024 / 1024 / 1024, 1
                    ),
                },
            )

        except Exception as e:
            return HealthCheck(
                name="Performance",
                status=HealthStatus.WARNING,
                message=f"⚠️ Could not check performance: {e}",
                details={"error": str(e)},
            )

    async def _check_database_health(self) -> HealthCheck:
        """Comprehensive SQLite database health check"""
        try:
            from datetime import datetime
            import os
            from pathlib import Path
            import sqlite3

            db_path = Path("data/quranbot.db")

            if not db_path.exists():
                return HealthCheck(
                    name="Database",
                    status=HealthStatus.CRITICAL,
                    message="❌ SQLite database file not found!",
                    details={"db_path": str(db_path), "exists": False},
                )

            # Get database file size
            file_size_bytes = os.path.getsize(db_path)
            file_size_mb = file_size_bytes / 1024 / 1024

            # Test database connection and integrity
            conn = sqlite3.connect(db_path)
            try:
                # Check database integrity
                integrity_result = conn.execute("PRAGMA integrity_check").fetchone()
                integrity_ok = integrity_result[0] == "ok"

                # Check WAL mode status
                journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
                wal_enabled = journal_mode.lower() == "wal"

                # Count tables
                tables_result = conn.execute(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
                ).fetchone()
                table_count = tables_result[0] if tables_result else 0

                # Count total records across main tables
                record_counts = {}
                main_tables = [
                    "daily_verses",
                    "hadith",
                    "duas",
                    "quiz_questions",
                    "conversations",
                    "playback_state",
                    "bot_statistics",
                ]

                total_records = 0
                for table in main_tables:
                    try:
                        count_result = conn.execute(
                            f"SELECT COUNT(*) FROM {table}"
                        ).fetchone()
                        count = count_result[0] if count_result else 0
                        record_counts[table] = count
                        total_records += count
                    except sqlite3.OperationalError:
                        # Table doesn't exist, skip
                        pass

                # Check recent activity (last insert/update)
                try:
                    last_activity = conn.execute(
                        "SELECT MAX(created_at) FROM ("
                        "SELECT created_at FROM quiz_questions UNION ALL "
                        "SELECT created_at FROM daily_verses UNION ALL "
                        "SELECT created_at FROM conversations"
                        ")"
                    ).fetchone()
                    last_activity_time = (
                        last_activity[0]
                        if last_activity and last_activity[0]
                        else "unknown"
                    )
                except sqlite3.OperationalError:
                    last_activity_time = "unknown"

                # Update health stats
                self.database_health_stats.update(
                    {
                        "last_check": datetime.now(UTC).isoformat(),
                        "size_mb": round(file_size_mb, 2),
                        "table_count": table_count,
                        "record_count": total_records,
                        "integrity_status": "ok" if integrity_ok else "corrupt",
                        "wal_status": "enabled" if wal_enabled else "disabled",
                        "connection_test": True,
                        "last_activity": last_activity_time,
                    }
                )

                # Determine health status
                if not integrity_ok:
                    status = HealthStatus.CRITICAL
                    message = "❌ Database integrity check failed!"
                elif file_size_mb > 100:  # Database larger than 100MB
                    status = HealthStatus.WARNING
                    message = f"⚠️ Large database size: {file_size_mb:.1f}MB"
                elif total_records == 0:
                    status = HealthStatus.WARNING
                    message = "⚠️ No data in database tables"
                else:
                    status = HealthStatus.HEALTHY
                    message = f"✅ Database healthy: {total_records} records, {file_size_mb:.1f}MB"

                return HealthCheck(
                    name="Database",
                    status=status,
                    message=message,
                    details={
                        "file_size_mb": round(file_size_mb, 2),
                        "table_count": table_count,
                        "total_records": total_records,
                        "integrity_ok": integrity_ok,
                        "wal_enabled": wal_enabled,
                        "record_counts": record_counts,
                        "last_activity": last_activity_time,
                        "db_path": str(db_path),
                    },
                )

            finally:
                conn.close()

        except Exception as e:
            self.database_health_stats["connection_test"] = False
            return HealthCheck(
                name="Database",
                status=HealthStatus.CRITICAL,
                message=f"❌ Database check failed: {e}",
                details={"error": str(e)},
            )

    async def _check_system_uptime(self) -> HealthCheck:
        """Check system uptime"""
        try:
            import psutil

            # Bot process uptime
            process = psutil.Process()
            create_time = datetime.fromtimestamp(process.create_time(), UTC)
            uptime = datetime.now(UTC) - create_time

            uptime_hours = uptime.total_seconds() / 3600

            # System uptime
            boot_time = datetime.fromtimestamp(psutil.boot_time(), UTC)
            system_uptime = datetime.now(UTC) - boot_time
            system_uptime_hours = system_uptime.total_seconds() / 3600

            if uptime_hours < 1:
                status = HealthStatus.WARNING
                message = f"⚠️ Recent restart: {uptime_hours:.1f}h uptime"
            else:
                status = HealthStatus.HEALTHY
                message = f"✅ Stable: {uptime_hours:.1f}h uptime"

            return HealthCheck(
                name="System Uptime",
                status=status,
                message=message,
                details={
                    "bot_uptime_hours": round(uptime_hours, 1),
                    "system_uptime_hours": round(system_uptime_hours, 1),
                    "bot_started": create_time.isoformat(),
                    "system_boot": boot_time.isoformat(),
                },
            )

        except Exception as e:
            return HealthCheck(
                name="System Uptime",
                status=HealthStatus.WARNING,
                message=f"⚠️ Could not check uptime: {e}",
                details={"error": str(e)},
            )

    async def _check_backup_status(self) -> HealthCheck:
        """Check SQLite database backup status"""
        try:
            # Check for SQLite database backup
            backup_dir = Path("backup")
            db_backup_files = (
                list(backup_dir.glob("quranbot_backup_*.db"))
                if backup_dir.exists()
                else []
            )

            if db_backup_files:
                # Get the most recent backup
                latest_backup = max(db_backup_files, key=lambda f: f.stat().st_mtime)
                stat = latest_backup.stat()
                backup_age = datetime.now(UTC) - datetime.fromtimestamp(
                    stat.st_mtime, UTC
                )
                backup_age_hours = backup_age.total_seconds() / 3600
                size_mb = stat.st_size / 1024 / 1024

                if backup_age_hours > 48:  # More than 48 hours old for SQLite
                    status = HealthStatus.WARNING
                    message = f"⚠️ Database backup is {backup_age_hours:.1f}h old"
                elif size_mb < 0.1:  # Less than 100KB
                    status = HealthStatus.WARNING
                    message = f"⚠️ Database backup seems too small: {size_mb:.1f}MB"
                else:
                    status = HealthStatus.HEALTHY
                    message = f"✅ Recent DB backup: {backup_age_hours:.1f}h ago ({size_mb:.1f}MB)"

                return HealthCheck(
                    name="Database Backup",
                    status=status,
                    message=message,
                    details={
                        "backup_age_hours": round(backup_age_hours, 1),
                        "backup_size_mb": round(size_mb, 1),
                        "backup_file": latest_backup.name,
                        "last_backup": datetime.fromtimestamp(
                            stat.st_mtime, UTC
                        ).isoformat(),
                        "total_backups": len(db_backup_files),
                    },
                )
            else:
                # Check if the main database exists (backup might not be critical)
                main_db = Path("data/quranbot.db")
                if main_db.exists():
                    return HealthCheck(
                        name="Database Backup",
                        status=HealthStatus.WARNING,
                        message="⚠️ No database backup found (main DB exists)",
                        details={"backup_exists": False, "main_db_exists": True},
                    )
                else:
                    return HealthCheck(
                        name="Database Backup",
                        status=HealthStatus.CRITICAL,
                        message="❌ No database or backup found!",
                        details={"backup_exists": False, "main_db_exists": False},
                    )

        except Exception as e:
            return HealthCheck(
                name="Data Backup",
                status=HealthStatus.WARNING,
                message=f"⚠️ Could not check backup: {e}",
                details={"error": str(e)},
            )

    def _assess_overall_health(self, health_checks: list[HealthCheck]) -> str:
        """Assess overall system health from individual checks"""
        critical_count = sum(
            1 for check in health_checks if check.status == HealthStatus.CRITICAL
        )
        warning_count = sum(
            1 for check in health_checks if check.status == HealthStatus.WARNING
        )

        if critical_count > 0:
            return HealthStatus.CRITICAL
        elif warning_count > 0:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY

    async def _send_health_report(
        self, overall_status: str, health_checks: list[HealthCheck]
    ) -> None:
        """Log comprehensive health report"""
        await self.logger.info(
            f"Health report - {overall_status}",
            {
                "overall_status": overall_status,
                "checks_count": len(health_checks),
                "checks": [{"name": check.name, "status": check.status, "message": check.message} for check in health_checks]
            }
        )

    async def _send_startup_notification(self) -> None:
        """Log startup notification"""
        await self.logger.info(
            "Health monitor started",
            {
                "check_interval": self.check_interval_minutes,
                "alert_interval": self.alert_interval_minutes,
            }
        )

    async def _send_shutdown_notification(self) -> None:
        """Log shutdown notification"""
        await self.logger.info(
            "Health monitor stopped",
            {"shutdown_time": datetime.now(UTC).isoformat()}
        )

    async def _check_audio_stuck(self) -> HealthCheck | None:
        """Check if audio has been stuck for too long"""
        # This would integrate with your audio service to check last activity
        # For now, return None (no alert)
        return None

    async def _check_json_errors(self) -> HealthCheck | None:
        """Check for repeated JSON errors"""
        # This would check recent logs for JSON serialization errors
        # For now, return None (no alert)
        return None

    async def _check_memory_usage(self) -> HealthCheck | None:
        """Check for critical memory usage"""
        try:
            import psutil

            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024

            # Alert if using more than 1GB
            if memory_mb > 1024:
                return HealthCheck(
                    name="Memory Usage Critical",
                    status=HealthStatus.CRITICAL,
                    message=f"🚨 Critical memory usage: {memory_mb:.1f}MB",
                    details={"memory_mb": round(memory_mb, 1)},
                )

        except Exception:
            pass

        return None

    async def _send_critical_alert(self, alert: HealthCheck) -> None:
        """Log critical alert"""
        await self.logger.critical(
            f"Critical alert: {alert.name}",
            {
                "status": alert.status,
                "message": alert.message,
                "details": alert.details
            }
        )

    async def _send_audio_stuck_alert(self, details: dict[str, Any]) -> None:
        """Log audio stuck alert"""
        await self.logger.warning(
            "Audio playback stuck",
            {
                "minutes_stuck": details.get("minutes_since_playback", 0),
                "current_surah": details.get("current_surah", "Unknown"),
                "is_connected": details.get("is_connected", False),
                "is_playing": details.get("is_playing", False)
            }
        )

    # Public methods for external integrations
    async def report_audio_activity(
        self, activity_type: str, details: dict[str, Any] = None
    ) -> None:
        """Report audio activity for monitoring"""
        self.last_audio_activity = {
            "timestamp": datetime.now(UTC),
            "activity_type": activity_type,
            "details": details or {},
        }



    async def report_json_save(
        self, filename: str, success: bool, error: str = None
    ) -> None:
        """Report JSON file save operation"""
        self.last_successful_save[filename] = {
            "timestamp": datetime.now(UTC),
            "success": success,
            "error": error,
        }

    async def get_health_status(self) -> dict[str, Any]:
        """Get current health status"""
        return {
            "is_monitoring": self.is_monitoring,
            "last_health_report": (
                self.last_health_report.isoformat() if self.last_health_report else None
            ),
            "last_audio_activity": self.last_audio_activity,
            "logging_enabled": True,
            "check_interval_minutes": self.check_interval_minutes,
            "alert_interval_minutes": self.alert_interval_minutes,
        }
