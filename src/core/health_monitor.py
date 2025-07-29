# =============================================================================
# QuranBot - Health Monitor System
# =============================================================================
# Comprehensive health monitoring with Discord webhook notifications
# Monitors audio, JSON files, performance, and sends regular status updates
# =============================================================================

import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

from .structured_logger import StructuredLogger
from .webhook_logger import ModernWebhookLogger
from .json_validator import JSONValidator
from ..utils.tree_log import log_perfect_tree_section, log_error_with_traceback


class HealthStatus:
    """Health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning" 
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class HealthCheck:
    """Individual health check result"""
    def __init__(
        self, 
        name: str, 
        status: str, 
        message: str, 
        details: Dict[str, Any] = None
    ):
        self.name = name
        self.status = status
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now(timezone.utc)


class HealthMonitor:
    """
    Comprehensive health monitoring system for QuranBot.
    
    Features:
    - Regular health status webhooks (hourly)
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
        webhook_logger: ModernWebhookLogger = None,
        data_dir: Path = None,
        check_interval_minutes: int = 60,
        alert_interval_minutes: int = 5
    ):
        """
        Initialize health monitor.
        
        Args:
            logger: Structured logger instance
            webhook_logger: Webhook logger for notifications
            data_dir: Data directory to monitor
            check_interval_minutes: Regular health check interval (default: 60 min)
            alert_interval_minutes: Critical alert check interval (default: 5 min)
        """
        self.logger = logger
        self.webhook_logger = webhook_logger
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
        
        # JSON validator for file checks
        self.json_validator = JSONValidator(logger)
        
        # Critical files to monitor
        self.critical_files = [
            "playback_state.json",
            "bot_stats.json", 
            "quiz_state.json",
            "quiz_stats.json",
            "metadata_cache.json"
        ]
        
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
                "webhook_enabled": self.webhook_logger is not None
            }
        )
        
        log_perfect_tree_section(
            "Health Monitor - Started",
            [
                ("status", "🟢 Monitoring active"),
                ("health_checks", f"⏰ Every {self.check_interval_minutes} minutes"),
                ("critical_alerts", f"🚨 Every {self.alert_interval_minutes} minutes"),
                ("webhook_logging", "✅ Enabled" if self.webhook_logger else "❌ Disabled")
            ],
            "💚"
        )
        
        # Send startup notification
        if self.webhook_logger:
            await self._send_startup_notification()
            
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
                    "Error in health monitor loop", 
                    {"error": str(e)}
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
                    "Error in alert monitor loop", 
                    {"error": str(e)}
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
            
            # JSON file integrity check
            json_check = await self._check_json_integrity()
            health_checks.append(json_check)
            
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
            
            # Send webhook report
            if self.webhook_logger:
                await self._send_health_report(overall_status, health_checks)
                
            self.last_health_report = datetime.now(timezone.utc)
            
            await self.logger.info(
                "Health check completed",
                {
                    "overall_status": overall_status,
                    "checks_performed": len(health_checks),
                    "webhook_sent": self.webhook_logger is not None
                }
            )
            
        except Exception as e:
            await self.logger.error(
                "Error performing health check", 
                {"error": str(e)}
            )
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
            await self.logger.error(
                "Error checking critical alerts", 
                {"error": str(e)}
            )
            
    async def _check_audio_health(self) -> HealthCheck:
        """Check audio playback health"""
        try:
            # This would integrate with your AudioService
            # For now, we'll check if FFmpeg processes are running
            import psutil
            
            ffmpeg_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] == 'ffmpeg':
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
                        "last_check": datetime.now(timezone.utc).isoformat()
                    }
                )
            else:
                return HealthCheck(
                    name="Audio Playback", 
                    status=HealthStatus.CRITICAL,
                    message="❌ No audio processes detected",
                    details={"ffmpeg_processes": 0}
                )
                
        except Exception as e:
            return HealthCheck(
                name="Audio Playback",
                status=HealthStatus.WARNING,
                message=f"⚠️ Could not check audio status: {e}",
                details={"error": str(e)}
            )
            
    async def _check_json_integrity(self) -> HealthCheck:
        """Check JSON file integrity"""
        try:
            results = {}
            corrupted_files = []
            
            for filename in self.critical_files:
                file_path = self.data_dir / filename
                validation_result = self.json_validator.validate_json_file(file_path)
                results[filename] = validation_result
                
                if not validation_result["valid"]:
                    corrupted_files.append(filename)
                    
            if not corrupted_files:
                return HealthCheck(
                    name="JSON Integrity",
                    status=HealthStatus.HEALTHY,
                    message=f"✅ All {len(self.critical_files)} JSON files valid",
                    details={
                        "files_checked": len(self.critical_files),
                        "corrupted_files": 0,
                        "details": results
                    }
                )
            else:
                return HealthCheck(
                    name="JSON Integrity",
                    status=HealthStatus.CRITICAL,
                    message=f"❌ {len(corrupted_files)} corrupted JSON files detected",
                    details={
                        "files_checked": len(self.critical_files),
                        "corrupted_files": corrupted_files,
                        "details": results
                    }
                )
                
        except Exception as e:
            return HealthCheck(
                name="JSON Integrity",
                status=HealthStatus.WARNING,
                message=f"⚠️ Could not check JSON files: {e}",
                details={"error": str(e)}
            )
            
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
                    "system_memory_available_gb": round(system_memory.available / 1024 / 1024 / 1024, 1)
                }
            )
            
        except Exception as e:
            return HealthCheck(
                name="Performance",
                status=HealthStatus.WARNING,
                message=f"⚠️ Could not check performance: {e}",
                details={"error": str(e)}
            )
            
    async def _check_system_uptime(self) -> HealthCheck:
        """Check system uptime"""
        try:
            import psutil
            
            # Bot process uptime
            process = psutil.Process()
            create_time = datetime.fromtimestamp(process.create_time(), timezone.utc)
            uptime = datetime.now(timezone.utc) - create_time
            
            uptime_hours = uptime.total_seconds() / 3600
            
            # System uptime
            boot_time = datetime.fromtimestamp(psutil.boot_time(), timezone.utc)
            system_uptime = datetime.now(timezone.utc) - boot_time
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
                    "system_boot": boot_time.isoformat()
                }
            )
            
        except Exception as e:
            return HealthCheck(
                name="System Uptime",
                status=HealthStatus.WARNING,
                message=f"⚠️ Could not check uptime: {e}",
                details={"error": str(e)}
            )
            
    async def _check_backup_status(self) -> HealthCheck:
        """Check backup system status"""
        try:
            backup_file = Path("backup/data_backup.tar.gz")
            
            if backup_file.exists():
                stat = backup_file.stat()
                backup_age = datetime.now(timezone.utc) - datetime.fromtimestamp(stat.st_mtime, timezone.utc)
                backup_age_hours = backup_age.total_seconds() / 3600
                size_mb = stat.st_size / 1024 / 1024
                
                if backup_age_hours > 24:  # More than 24 hours old
                    status = HealthStatus.WARNING
                    message = f"⚠️ Backup is {backup_age_hours:.1f}h old"
                else:
                    status = HealthStatus.HEALTHY
                    message = f"✅ Recent backup: {backup_age_hours:.1f}h ago ({size_mb:.1f}MB)"
                    
                return HealthCheck(
                    name="Data Backup",
                    status=status,
                    message=message,
                    details={
                        "backup_age_hours": round(backup_age_hours, 1),
                        "backup_size_mb": round(size_mb, 1),
                        "last_backup": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
                    }
                )
            else:
                return HealthCheck(
                    name="Data Backup",
                    status=HealthStatus.WARNING,
                    message="⚠️ No backup file found",
                    details={"backup_exists": False}
                )
                
        except Exception as e:
            return HealthCheck(
                name="Data Backup",
                status=HealthStatus.WARNING,
                message=f"⚠️ Could not check backup: {e}",
                details={"error": str(e)}
            )
            
    def _assess_overall_health(self, health_checks: List[HealthCheck]) -> str:
        """Assess overall system health from individual checks"""
        critical_count = sum(1 for check in health_checks if check.status == HealthStatus.CRITICAL)
        warning_count = sum(1 for check in health_checks if check.status == HealthStatus.WARNING)
        
        if critical_count > 0:
            return HealthStatus.CRITICAL
        elif warning_count > 0:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY
            
    async def _send_health_report(self, overall_status: str, health_checks: List[HealthCheck]) -> None:
        """Send comprehensive health report via webhook"""
        try:
            # Choose emoji and color based on status
            if overall_status == HealthStatus.HEALTHY:
                emoji = "💚"
                color = 0x00ff00  # Green
                title = "🟢 Bot Health Report - All Systems Operational"
            elif overall_status == HealthStatus.WARNING:
                emoji = "⚠️"
                color = 0xffaa00  # Orange
                title = "🟠 Bot Health Report - Warnings Detected"
            else:  # CRITICAL
                emoji = "🚨"
                color = 0xff0000  # Red
                title = "🔴 Bot Health Report - Critical Issues"
                
            # Build description
            description = f"{emoji} **Overall Status: {overall_status.title()}**\n\n"
            
            # Add summary of each check
            for check in health_checks:
                status_emoji = {
                    HealthStatus.HEALTHY: "✅",
                    HealthStatus.WARNING: "⚠️", 
                    HealthStatus.CRITICAL: "❌"
                }.get(check.status, "❓")
                
                description += f"{status_emoji} **{check.name}**: {check.message}\n"
                
            # Add timestamp
            description += f"\n🕒 **Report Time**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
            
            # Create embed
            embed = {
                "title": title,
                "description": description,
                "color": color,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "thumbnail": {
                    "url": "https://cdn.discordapp.com/icons/1120508636436373667/a_9421c0e06a4c1b90fe4527ad2095e7de.gif"
                },
                "footer": {
                    "text": "QuranBot Health Monitor • Automated System Status",
                    "icon_url": "https://cdn.discordapp.com/icons/1120508636436373667/a_9421c0e06a4c1b90fe4527ad2095e7de.gif"
                },
                "fields": []
            }
            
            # Add detailed fields for critical/warning items
            for check in health_checks:
                if check.status in [HealthStatus.CRITICAL, HealthStatus.WARNING] and check.details:
                    details_text = []
                    for key, value in check.details.items():
                        if key != "error":  # Skip error details in public report
                            details_text.append(f"**{key.replace('_', ' ').title()}**: {value}")
                    
                    if details_text:
                        embed["fields"].append({
                            "name": f"{check.name} Details",
                            "value": "\n".join(details_text[:5]),  # Limit to 5 details
                            "inline": True
                        })
            
            await self.webhook_logger.send_embed(embed)
            
        except Exception as e:
            await self.logger.error(
                "Failed to send health report webhook", 
                {"error": str(e)}
            )
            
    async def _send_startup_notification(self) -> None:
        """Send bot startup notification"""
        try:
            embed = {
                "title": "🚀 QuranBot Health Monitor Started",
                "description": "✅ **Health monitoring system is now active**\n\n"
                             f"🔍 **Regular health checks**: Every {self.check_interval_minutes} minutes\n"
                             f"🚨 **Critical alerts**: Every {self.alert_interval_minutes} minutes\n"
                             f"📊 **Monitoring**: Audio, JSON integrity, performance, backups\n\n"
                             f"🕒 **Started**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
                "color": 0x00ff00,  # Green
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "thumbnail": {
                    "url": "https://cdn.discordapp.com/icons/1120508636436373667/a_9421c0e06a4c1b90fe4527ad2095e7de.gif"
                },
                "footer": {
                    "text": "QuranBot Health Monitor • System Online",
                    "icon_url": "https://cdn.discordapp.com/icons/1120508636436373667/a_9421c0e06a4c1b90fe4527ad2095e7de.gif"
                }
            }
            
            await self.webhook_logger.send_embed(embed)
            
        except Exception as e:
            await self.logger.error(
                "Failed to send startup notification", 
                {"error": str(e)}
            )
            
    async def _send_shutdown_notification(self) -> None:
        """Send bot shutdown notification"""
        try:
            embed = {
                "title": "🛑 QuranBot Health Monitor Stopped",
                "description": "⚠️ **Health monitoring system has been stopped**\n\n"
                             f"🕒 **Stopped**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
                "color": 0xffaa00,  # Orange
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "thumbnail": {
                    "url": "https://cdn.discordapp.com/icons/1120508636436373667/a_9421c0e06a4c1b90fe4527ad2095e7de.gif"
                },
                "footer": {
                    "text": "QuranBot Health Monitor • System Offline",
                    "icon_url": "https://cdn.discordapp.com/icons/1120508636436373667/a_9421c0e06a4c1b90fe4527ad2095e7de.gif"
                }
            }
            
            await self.webhook_logger.send_embed(embed)
            
        except Exception as e:
            await self.logger.error(
                "Failed to send shutdown notification", 
                {"error": str(e)}
            )
            
    async def _check_audio_stuck(self) -> Optional[HealthCheck]:
        """Check if audio has been stuck for too long"""
        # This would integrate with your audio service to check last activity
        # For now, return None (no alert)
        return None
        
    async def _check_json_errors(self) -> Optional[HealthCheck]:
        """Check for repeated JSON errors"""
        # This would check recent logs for JSON serialization errors
        # For now, return None (no alert)
        return None
        
    async def _check_memory_usage(self) -> Optional[HealthCheck]:
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
                    details={"memory_mb": round(memory_mb, 1)}
                )
                
        except Exception:
            pass
            
        return None
        
    async def _send_critical_alert(self, alert: HealthCheck) -> None:
        """Send critical alert webhook"""
        try:
            embed = {
                "title": f"🚨 CRITICAL ALERT: {alert.name}",
                "description": f"**{alert.message}**\n\n"
                             f"🕒 **Alert Time**: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                             f"⚠️ **Immediate attention required**",
                "color": 0xff0000,  # Red
                "timestamp": alert.timestamp.isoformat(),
                "thumbnail": {
                    "url": "https://cdn.discordapp.com/icons/1120508636436373667/a_9421c0e06a4c1b90fe4527ad2095e7de.gif"
                },
                "footer": {
                    "text": "QuranBot Critical Alert System • Urgent Action Required",
                    "icon_url": "https://cdn.discordapp.com/icons/1120508636436373667/a_9421c0e06a4c1b90fe4527ad2095e7de.gif"
                }
            }
            
            await self.webhook_logger.send_embed(embed)
            
        except Exception as e:
            await self.logger.error(
                "Failed to send critical alert", 
                {"error": str(e)}
            )
            
    async def _send_audio_stuck_alert(self, details: Dict[str, Any]) -> None:
        """Send immediate audio stuck alert webhook"""
        try:
            minutes_stuck = details.get("minutes_since_playback", 0)
            current_surah = details.get("current_surah", "Unknown")
            is_connected = details.get("is_connected", False)
            is_playing = details.get("is_playing", False)
            
            # Create status indicators
            connection_status = "🟢 Connected" if is_connected else "🔴 Disconnected" 
            playback_status = "🎵 Playing" if is_playing else "⏸️ Stopped"
            
            embed = {
                 "title": "🚨 AUDIO ALERT: Playback Stuck",
                 "description": f"**Audio playback has been stuck for {minutes_stuck:.1f} minutes**\n\n"
                              f"📖 **Current Surah**: {current_surah}\n"
                              f"🔗 **Voice Connection**: {connection_status}\n"
                              f"🎶 **Playback Status**: {playback_status}\n\n"
                              f"🕒 **Alert Time**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                              f"⚠️ **Bot may need restart**",
                 "color": 0xff6600,  # Orange-red
                 "timestamp": datetime.now(timezone.utc).isoformat(),
                 "thumbnail": {
                     "url": "https://cdn.discordapp.com/icons/1120508636436373667/a_9421c0e06a4c1b90fe4527ad2095e7de.gif"
                 },
                 "footer": {
                     "text": "QuranBot Audio Monitor • Immediate Attention Required",
                     "icon_url": "https://cdn.discordapp.com/icons/1120508636436373667/a_9421c0e06a4c1b90fe4527ad2095e7de.gif"
                 }
             }
            
            await self.webhook_logger.send_embed(embed)
            
        except Exception as e:
            await self.logger.error(
                "Failed to send audio stuck alert", 
                {"error": str(e)}
            )
            
    # Public methods for external integrations
    async def report_audio_activity(self, activity_type: str, details: Dict[str, Any] = None) -> None:
        """Report audio activity for monitoring"""
        self.last_audio_activity = {
            "timestamp": datetime.now(timezone.utc),
            "activity_type": activity_type,
            "details": details or {}
        }
        
        # Send immediate webhook alert for critical audio events
        if activity_type == "audio_stuck" and self.webhook_logger:
            await self._send_audio_stuck_alert(details or {})
        
    async def report_json_save(self, filename: str, success: bool, error: str = None) -> None:
        """Report JSON file save operation"""
        self.last_successful_save[filename] = {
            "timestamp": datetime.now(timezone.utc),
            "success": success,
            "error": error
        }
        
    async def get_health_status(self) -> Dict[str, Any]:
        """Get current health status"""
        return {
            "is_monitoring": self.is_monitoring,
            "last_health_report": self.last_health_report.isoformat() if self.last_health_report else None,
            "last_audio_activity": self.last_audio_activity,
            "webhook_enabled": self.webhook_logger is not None,
            "check_interval_minutes": self.check_interval_minutes,
            "alert_interval_minutes": self.alert_interval_minutes
        } 