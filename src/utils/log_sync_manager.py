# =============================================================================
# QuranBot - Integrated Log Sync Manager
# =============================================================================
# Automatic log syncing from VPS that runs as part of the main bot process
# Starts automatically when bot starts, stops when bot stops
# =============================================================================

import asyncio
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from .tree_log import log_error_with_traceback, log_perfect_tree_section


class LogSyncManager:
    """Integrated log sync manager that runs as part of the bot"""

    def __init__(self, vps_host: Optional[str] = None, sync_interval: int = 30):
        self.vps_host = vps_host or os.getenv("VPS_HOST")
        self.sync_interval = sync_interval
        self.sync_task: Optional[asyncio.Task] = None
        self.is_running = False
        
        # Paths
        self.local_logs_dir = Path("logs")
        self.vps_logs_path = "/opt/DiscordBots/QuranBot/logs/"
        
        # Stats
        self.sync_count = 0
        self.last_sync_time = None
        self.last_error = None

    async def start(self):
        """Start the log sync manager"""
        try:
            if not self.vps_host:
                log_perfect_tree_section(
                    "Log Sync Manager - Disabled",
                    [
                        ("status", "⚠️ VPS_HOST not configured"),
                        ("action", "Log syncing disabled"),
                        ("note", "Set VPS_HOST in .env to enable"),
                    ],
                    "📡",
                )
                return

            # Check if we're running on the VPS itself
            if await self._is_running_on_vps():
                log_perfect_tree_section(
                    "Integrated Log Sync",
                    [
                        ("status", "⚠️ Running on VPS - Integrated sync disabled"),
                        ("reason", "Bot is running on VPS itself"),
                        ("action", "Log syncing disabled"),
                        ("note", "Use standalone daemon on local machine for log sync"),
                        ("vps_host", self.vps_host),
                    ],
                    "📡",
                )
                return

            if self.is_running:
                log_perfect_tree_section(
                    "Log Sync Manager - Already Running",
                    [
                        ("status", "⚠️ Sync manager already started"),
                        ("action", "Skipping duplicate start"),
                    ],
                    "📡",
                )
                return

            # Test VPS connection
            if not await self._test_vps_connection():
                log_perfect_tree_section(
                    "Log Sync Manager - Connection Failed",
                    [
                        ("status", "❌ Cannot connect to VPS"),
                        ("vps_host", self.vps_host),
                        ("action", "Log syncing disabled"),
                    ],
                    "📡",
                )
                return

            # Create local logs directory
            self.local_logs_dir.mkdir(exist_ok=True)

            # Start sync task
            self.sync_task = asyncio.create_task(self._sync_loop())
            self.is_running = True

            log_perfect_tree_section(
                "Log Sync Manager - Started",
                [
                    ("status", "✅ Integrated log sync started"),
                    ("vps_host", self.vps_host),
                    ("sync_interval", f"{self.sync_interval}s"),
                    ("local_path", str(self.local_logs_dir)),
                ],
                "📡",
            )

        except Exception as e:
            log_error_with_traceback("Error starting log sync manager", e)

    async def stop(self):
        """Stop the log sync manager"""
        try:
            if not self.is_running:
                return

            self.is_running = False

            if self.sync_task and not self.sync_task.done():
                self.sync_task.cancel()
                try:
                    await self.sync_task
                except asyncio.CancelledError:
                    pass

            log_perfect_tree_section(
                "Log Sync Manager - Stopped",
                [
                    ("status", "🛑 Log sync stopped"),
                    ("total_syncs", self.sync_count),
                    ("last_sync", self._format_time(self.last_sync_time) if self.last_sync_time else "Never"),
                ],
                "📡",
            )

        except Exception as e:
            log_error_with_traceback("Error stopping log sync manager", e)

    async def _sync_loop(self):
        """Main sync loop that runs continuously"""
        try:
            # Initial sync
            await self._perform_sync()
            
            while self.is_running:
                try:
                    await asyncio.sleep(self.sync_interval)
                    if self.is_running:  # Check again after sleep
                        await self._perform_sync()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.last_error = str(e)
                    log_error_with_traceback("Error in sync loop", e)
                    # Wait a bit before retrying
                    await asyncio.sleep(60)

        except asyncio.CancelledError:
            log_perfect_tree_section(
                "Log Sync Manager - Loop Cancelled",
                [
                    ("status", "🛑 Sync loop cancelled"),
                    ("reason", "Task cancellation"),
                ],
                "📡",
            )
        except Exception as e:
            log_error_with_traceback("Critical error in sync loop", e)

    async def _perform_sync(self):
        """Perform a single sync operation"""
        try:
            # Get current date directories to sync
            today = datetime.now().strftime("%Y-%m-%d")
            yesterday = (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp() - 86400)
            yesterday_str = datetime.fromtimestamp(yesterday).strftime("%Y-%m-%d")
            
            dates_to_sync = [today, yesterday_str]
            synced_dates = []

            for date_str in dates_to_sync:
                try:
                    # Check if VPS directory exists
                    vps_date_path = f"{self.vps_logs_path}{date_str}/"
                    check_cmd = f"ssh {self.vps_host} 'test -d {vps_date_path}'"
                    
                    result = await asyncio.create_subprocess_shell(
                        check_cmd,
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL
                    )
                    await result.wait()
                    
                    if result.returncode != 0:
                        continue  # Directory doesn't exist, skip
                    
                    # Create local directory
                    local_date_dir = self.local_logs_dir / date_str
                    local_date_dir.mkdir(exist_ok=True)
                    
                    # Sync the directory
                    rsync_cmd = f"rsync -az --timeout=30 {self.vps_host}:{vps_date_path} {local_date_dir}/"
                    
                    result = await asyncio.create_subprocess_shell(
                        rsync_cmd,
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    _, stderr = await result.communicate()
                    
                    if result.returncode == 0:
                        synced_dates.append(date_str)
                    else:
                        error_msg = stderr.decode() if stderr else "Unknown rsync error"
                        log_error_with_traceback(f"Rsync failed for {date_str}", Exception(error_msg))

                except Exception as e:
                    log_error_with_traceback(f"Error syncing date {date_str}", e)

            # Update stats
            self.sync_count += 1
            self.last_sync_time = datetime.now()
            self.last_error = None

            # Log success (only every 10th sync to reduce noise)
            if self.sync_count % 10 == 1:  # Log on 1st, 11th, 21st sync, etc.
                log_perfect_tree_section(
                    "Log Sync Manager - Sync Complete",
                    [
                        ("status", "✅ Logs synced successfully"),
                        ("sync_count", f"#{self.sync_count}"),
                        ("dates_synced", len(synced_dates)),
                        ("next_sync", f"{self.sync_interval}s"),
                    ],
                    "📡",
                )

        except Exception as e:
            self.last_error = str(e)
            log_error_with_traceback("Error performing sync", e)

    async def _test_vps_connection(self) -> bool:
        """Test if we can connect to the VPS"""
        try:
            test_cmd = f"ssh -o ConnectTimeout=10 {self.vps_host} 'echo test'"
            
            result = await asyncio.create_subprocess_shell(
                test_cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await result.wait()
            
            return result.returncode == 0

        except Exception:
            return False

    async def _is_running_on_vps(self) -> bool:
        """Check if we're running on the VPS itself"""
        try:
            # If we can access the VPS logs directory locally, we're on the VPS
            vps_logs_path = Path(self.vps_logs_path)
            return vps_logs_path.exists() and vps_logs_path.is_dir()
        except Exception:
            return False

    def _format_time(self, dt: Optional[datetime]) -> str:
        """Format datetime for display"""
        if not dt:
            return "Never"
        return dt.strftime("%I:%M %p EST")

    def get_status(self) -> dict:
        """Get current sync status"""
        return {
            "is_running": self.is_running,
            "vps_host": self.vps_host,
            "sync_count": self.sync_count,
            "sync_interval": self.sync_interval,
            "last_sync": self._format_time(self.last_sync_time),
            "last_error": self.last_error,
        }


# Global instance
_log_sync_manager: Optional[LogSyncManager] = None


def get_log_sync_manager() -> Optional[LogSyncManager]:
    """Get the global log sync manager instance"""
    return _log_sync_manager


async def start_integrated_log_sync(vps_host: Optional[str] = None, sync_interval: int = 30):
    """Start integrated log syncing"""
    global _log_sync_manager
    
    if _log_sync_manager and _log_sync_manager.is_running:
        return _log_sync_manager
    
    _log_sync_manager = LogSyncManager(vps_host, sync_interval)
    await _log_sync_manager.start()
    return _log_sync_manager


async def stop_integrated_log_sync():
    """Stop integrated log syncing"""
    global _log_sync_manager
    
    if _log_sync_manager:
        await _log_sync_manager.stop()
        _log_sync_manager = None 