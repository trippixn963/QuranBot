#!/usr/bin/env python3
"""
QuranBot - Automated Log Sync Daemon
===================================
Fully automated log syncing daemon that runs independently of the main bot.
This ensures logs are always syncing without any manual intervention.

Features:
- Runs as a background daemon
- Auto-restarts on failure
- Configurable sync intervals
- Health monitoring
- Graceful shutdown
- Process management
- System service integration

Usage:
    python tools/log_sync_daemon.py start     # Start daemon
    python tools/log_sync_daemon.py stop      # Stop daemon
    python tools/log_sync_daemon.py restart   # Restart daemon
    python tools/log_sync_daemon.py status    # Check status
    python tools/log_sync_daemon.py install   # Install as system service
"""

import asyncio
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import pytz

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from dotenv import load_dotenv

# Load environment variables
env_path = project_root / "config" / ".env"
load_dotenv(env_path)

# Import the logging system to use the same structure
from utils.tree_log import write_to_log_files, log_perfect_tree_section


class LogSyncDaemon:
    """Automated log sync daemon that runs 24/7"""

    def __init__(self):
        self.vps_host = os.getenv("VPS_HOST", "root@159.89.90.90")
        self.sync_interval = int(os.getenv("LOG_SYNC_INTERVAL", "30"))  # seconds
        self.local_logs_dir = project_root / "logs"
        self.vps_logs_path = "/opt/DiscordBots/QuranBot/logs/"
        
        # EST timezone to match bot's timezone
        self.est_tz = pytz.timezone("US/Eastern")
        
        # Daemon state
        self.is_running = False
        self.sync_count = 0
        self.last_sync_time = None
        self.last_error = None
        self.start_time = None
        
        # Process management
        self.pid_file = project_root / "tools" / "log_sync_daemon.pid"
        self.status_file = project_root / "tools" / "log_sync_status.json"
        
        # Create required directories
        self.local_logs_dir.mkdir(exist_ok=True)
        (project_root / "tools").mkdir(exist_ok=True)

    def log_tree_section(self, title: str, items: list, emoji: str = "🤖"):
        """Log a tree section using the standard tree logging format"""
        log_perfect_tree_section(title, items, emoji)

    def log_message(self, message: str, level: str = "INFO"):
        """Log a message using the standard logging system"""
        # Print to console for immediate feedback
        timestamp = datetime.now(self.est_tz).strftime("%Y-%m-%d %H:%M:%S EST")
        print(f"[{timestamp}] [{level}] {message}")
        
        # Use the standard logging system to maintain structure
        write_to_log_files(f"🤖 Log Sync Daemon - {message}", level, "log_sync_daemon")

    def save_status(self):
        """Save current status to file"""
        try:
            status = {
                "is_running": self.is_running,
                "sync_count": self.sync_count,
                "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
                "last_error": self.last_error,
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "vps_host": self.vps_host,
                "sync_interval": self.sync_interval,
                "pid": os.getpid()
            }
            
            with open(self.status_file, 'w') as f:
                json.dump(status, f, indent=2)
                
        except Exception as e:
            self.log_message(f"Failed to save status: {e}", "ERROR")

    def load_status(self) -> dict:
        """Load status from file"""
        try:
            if self.status_file.exists():
                with open(self.status_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            self.log_message(f"Failed to load status: {e}", "WARNING")
        return {}

    async def test_vps_connection(self) -> bool:
        """Test VPS connection"""
        try:
            cmd = f"ssh -o ConnectTimeout=10 -o BatchMode=yes {self.vps_host} 'echo test'"
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await process.wait()
            return process.returncode == 0
        except Exception:
            return False

    async def sync_logs(self) -> bool:
        """Perform log sync operation"""
        try:
            # Get current and previous day
            today = datetime.now(self.est_tz).strftime("%Y-%m-%d")
            yesterday = datetime.fromtimestamp(
                datetime.now(self.est_tz).timestamp() - 86400
            ).strftime("%Y-%m-%d")
            
            dates_to_sync = [today, yesterday]
            synced_count = 0

            for date_str in dates_to_sync:
                try:
                    # Check if VPS directory exists
                    vps_date_path = f"{self.vps_logs_path}{date_str}/"
                    check_cmd = f"ssh {self.vps_host} 'test -d {vps_date_path}'"
                    
                    process = await asyncio.create_subprocess_shell(
                        check_cmd,
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL
                    )
                    await process.wait()
                    
                    if process.returncode != 0:
                        continue  # Directory doesn't exist
                    
                    # Create local directory
                    local_date_dir = self.local_logs_dir / date_str
                    local_date_dir.mkdir(exist_ok=True)
                    
                    # Sync with rsync
                    rsync_cmd = f"rsync -az --timeout=30 {self.vps_host}:{vps_date_path} {local_date_dir}/"
                    
                    process = await asyncio.create_subprocess_shell(
                        rsync_cmd,
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    _, stderr = await process.communicate()
                    
                    if process.returncode == 0:
                        synced_count += 1
                    else:
                        error_msg = stderr.decode() if stderr else "Unknown error"
                        self.log_tree_section(
                            "Log Sync - Rsync Error",
                            [
                                ("date", date_str),
                                ("error", error_msg),
                                ("command", rsync_cmd),
                            ],
                            "❌"
                        )

                except Exception as e:
                    self.log_tree_section(
                        "Log Sync - Date Sync Error",
                        [
                            ("date", date_str),
                            ("error", str(e)),
                            ("action", "Continuing with other dates"),
                        ],
                        "⚠️"
                    )

            # Update stats
            self.sync_count += 1
            self.last_sync_time = datetime.now(self.est_tz)
            self.last_error = None
            
            # Log success with tree format (every 10th sync to reduce noise)
            if self.sync_count % 10 == 1 or synced_count == 0:
                self.log_tree_section(
                    "Log Sync - Completed",
                    [
                        ("sync_number", f"#{self.sync_count}"),
                        ("dates_synced", f"{synced_count} dates"),
                        ("dates_checked", f"{len(dates_to_sync)} dates ({', '.join(dates_to_sync)})"),
                        ("next_sync", f"in {self.sync_interval}s"),
                    ],
                    "📡"
                )
            
            return True

        except Exception as e:
            self.last_error = str(e)
            self.log_tree_section(
                "Log Sync - Failed",
                [
                    ("sync_number", f"#{self.sync_count + 1}"),
                    ("error", str(e)),
                    ("action", "Will retry next cycle"),
                ],
                "❌"
            )
            return False

    async def daemon_loop(self):
        """Main daemon loop"""
        self.log_tree_section(
            "Log Sync Daemon Starting",
            [
                ("vps_host", self.vps_host),
                ("sync_interval", f"{self.sync_interval}s"),
                ("local_logs", str(self.local_logs_dir)),
                ("vps_logs", self.vps_logs_path),
            ],
            "🚀"
        )
        
        # Test VPS connection
        if not await self.test_vps_connection():
            self.log_tree_section(
                "Log Sync Daemon - Connection Failed",
                [
                    ("status", "❌ Cannot connect to VPS"),
                    ("vps_host", self.vps_host),
                    ("action", "Daemon startup aborted"),
                ],
                "❌"
            )
            return False
        
        self.log_tree_section(
            "Log Sync Daemon - VPS Connection",
            [
                ("status", "✅ Connected successfully"),
                ("vps_host", self.vps_host),
                ("connection_test", "✅ Passed"),
            ],
            "🌐"
        )
        
        # Set daemon state
        self.is_running = True
        self.start_time = datetime.now(self.est_tz)
        self.save_status()
        
        self.log_tree_section(
            "Log Sync Daemon - Active",
            [
                ("status", "✅ Daemon running"),
                ("sync_interval", f"{self.sync_interval}s"),
                ("timezone", "EST (US/Eastern)"),
                ("start_time", self.start_time.strftime("%Y-%m-%d %H:%M:%S EST")),
            ],
            "🔄"
        )
        
        # Initial sync
        await self.sync_logs()
        
        # Main loop
        while self.is_running:
            try:
                await asyncio.sleep(self.sync_interval)
                if self.is_running:  # Check again after sleep
                    await self.sync_logs()
                    self.save_status()
                    
            except asyncio.CancelledError:
                self.log_tree_section(
                    "Log Sync Daemon - Cancelled",
                    [
                        ("status", "🛑 Daemon cancelled"),
                        ("reason", "CancelledError received"),
                    ],
                    "🛑"
                )
                break
            except Exception as e:
                self.log_tree_section(
                    "Log Sync Daemon - Error",
                    [
                        ("status", "❌ Error in daemon loop"),
                        ("error", str(e)),
                        ("action", "Retrying in 60s"),
                    ],
                    "❌"
                )
                self.last_error = str(e)
                self.save_status()
                # Wait before retrying
                await asyncio.sleep(60)

        self.is_running = False
        self.save_status()
        
        self.log_tree_section(
            "Log Sync Daemon - Stopped",
            [
                ("status", "🛑 Daemon stopped"),
                ("total_syncs", str(self.sync_count)),
                ("uptime", str(datetime.now(self.est_tz) - self.start_time) if self.start_time else "Unknown"),
            ],
            "🏁"
        )
        return True

    def start_daemon(self):
        """Start the daemon"""
        # Check if already running
        if self.is_daemon_running():
            print("Daemon is already running")
            return False
        
        # Write PID file
        with open(self.pid_file, 'w') as f:
            f.write(str(os.getpid()))
        
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        try:
            # Run the daemon
            asyncio.run(self.daemon_loop())
        finally:
            # Clean up
            if self.pid_file.exists():
                self.pid_file.unlink()
            self.is_running = False
            self.save_status()

    def stop_daemon(self):
        """Stop the daemon"""
        if not self.pid_file.exists():
            print("Daemon is not running (no PID file)")
            return False
        
        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Send SIGTERM
            os.kill(pid, signal.SIGTERM)
            
            # Wait for process to stop
            for _ in range(30):  # Wait up to 30 seconds
                try:
                    os.kill(pid, 0)  # Check if process exists
                    time.sleep(1)
                except ProcessLookupError:
                    break
            else:
                # Force kill if still running
                try:
                    os.kill(pid, signal.SIGKILL)
                    print("Daemon force-killed")
                except ProcessLookupError:
                    pass
            
            # Clean up PID file
            if self.pid_file.exists():
                self.pid_file.unlink()
            
            print("Daemon stopped")
            return True
            
        except Exception as e:
            print(f"Error stopping daemon: {e}")
            return False

    def is_daemon_running(self) -> bool:
        """Check if daemon is running"""
        if not self.pid_file.exists():
            return False
        
        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Check if process exists
            os.kill(pid, 0)
            return True
            
        except (ProcessLookupError, ValueError, OSError):
            # Clean up stale PID file
            if self.pid_file.exists():
                self.pid_file.unlink()
            return False

    def get_status(self) -> dict:
        """Get daemon status"""
        status = self.load_status()
        status["daemon_running"] = self.is_daemon_running()
        return status

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.log_message(f"Received signal {signum}, shutting down...")
        self.is_running = False

    def install_systemd_service(self):
        """Install as systemd service (Linux only)"""
        if os.name != 'posix':
            print("Systemd services are only available on Linux")
            return False
        
        service_content = f"""[Unit]
Description=QuranBot Log Sync Daemon
After=network.target

[Service]
Type=simple
User={os.getenv('USER', 'root')}
WorkingDirectory={project_root}
ExecStart={sys.executable} {__file__} start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
        
        service_file = "/etc/systemd/system/quranbot-logsync.service"
        
        try:
            # Write service file
            subprocess.run(['sudo', 'tee', service_file], input=service_content, text=True, check=True)
            
            # Reload systemd and enable service
            subprocess.run(['sudo', 'systemctl', 'daemon-reload'], check=True)
            subprocess.run(['sudo', 'systemctl', 'enable', 'quranbot-logsync.service'], check=True)
            
            print(f"Systemd service installed: {service_file}")
            print("Start with: sudo systemctl start quranbot-logsync")
            print("Check status: sudo systemctl status quranbot-logsync")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Failed to install systemd service: {e}")
            return False


def main():
    """Main CLI interface"""
    daemon = LogSyncDaemon()
    
    if len(sys.argv) < 2:
        print("Usage: python log_sync_daemon.py {start|stop|restart|status|install}")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "start":
        print("Starting log sync daemon...")
        daemon.start_daemon()
        
    elif command == "stop":
        print("Stopping log sync daemon...")
        daemon.stop_daemon()
        
    elif command == "restart":
        print("Restarting log sync daemon...")
        daemon.stop_daemon()
        time.sleep(2)
        daemon.start_daemon()
        
    elif command == "status":
        status = daemon.get_status()
        print("\n=== Log Sync Daemon Status ===")
        print(f"Running: {'✅ Yes' if status.get('daemon_running') else '❌ No'}")
        if status.get('start_time'):
            print(f"Started: {status['start_time']}")
        if status.get('last_sync_time'):
            print(f"Last Sync: {status['last_sync_time']}")
        print(f"Sync Count: {status.get('sync_count', 0)}")
        print(f"VPS Host: {status.get('vps_host', 'Not set')}")
        print(f"Interval: {status.get('sync_interval', 30)}s")
        if status.get('last_error'):
            print(f"Last Error: {status['last_error']}")
        
    elif command == "install":
        print("Installing systemd service...")
        daemon.install_systemd_service()
        
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main() 