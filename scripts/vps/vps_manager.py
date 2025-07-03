#!/usr/bin/env python3
"""
VPS Manager for QuranBot
Manages the QuranBot deployment on the VPS with specific configuration.
"""

import os
import sys
import subprocess
import json
import time
import argparse
import psutil
import requests
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta

# VPS Configuration
VPS_CONFIG = {
    "ip": "159.89.90.90",
    "user": "root",
    "ssh_key": "quranbot_key",
    "ssh_key_path": "C:\\Users\\hanna\\Documents\\QuranBot\\quranbot_key",
    "bot_directory": "/home/QuranAudioBot",
    "local_project": "C:/Users/hanna/Documents/QuranBot",
    "repo_url": "https://github.com/yourusername/QuranBot.git",  # Update with your actual repo URL
    "venv_name": "venv",
    "log_file": "bot.log",
    "service_name": "quranbot",
    "discord_webhook": "https://discord.com/api/webhooks/1390306713999249438/GtYAxLATdciVSo9X43zFoTmu3P-XHB0h5MP2v7JlZZeWxvk9LKmzLRiqWPEEkZcHhq7F",  # Discord webhook for VPS notifications
    "backup_retention_days": 7,
    "auto_restart_on_failure": True,
    "monitoring_interval": 300  # 5 minutes
}

class VPSManager:
    def __init__(self):
        self.config = VPS_CONFIG
        self.ssh_base_cmd = f"ssh -i {self.config['ssh_key_path']} {self.config['user']}@{self.config['ip']}"
        
    def run_ssh_command(self, command: str, capture_output: bool = True) -> subprocess.CompletedProcess:
        """Run a command on the VPS via SSH."""
        # Escape the command properly for SSH
        escaped_command = command.replace("'", "'\"'\"'")
        full_command = f"{self.ssh_base_cmd} \"{escaped_command}\""
        print(f"Running: {full_command}")
        
        try:
            if capture_output:
                result = subprocess.run(full_command, shell=True, capture_output=True, text=True)
            else:
                result = subprocess.run(full_command, shell=True)
            return result
        except Exception as e:
            print(f"Error running SSH command: {e}")
            return subprocess.CompletedProcess(full_command, 1, "", str(e))

    def check_connection(self) -> bool:
        """Test SSH connection to VPS."""
        print("Testing SSH connection...")
        result = self.run_ssh_command("echo 'Connection successful'")
        if result.returncode == 0:
            print("SUCCESS: SSH connection successful!")
            return True
        else:
            print("ERROR: SSH connection failed!")
            print(f"Error: {result.stderr}")
            return False

    def get_system_info(self) -> Dict:
        """Get comprehensive system information."""
        print("Getting system information...")
        
        info = {}
        
        # CPU and Memory
        cpu_result = self.run_ssh_command("top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1")
        mem_result = self.run_ssh_command("free | grep Mem | awk '{printf \"%.1f\", $3/$2 * 100.0}'")
        disk_result = self.run_ssh_command("df -h / | tail -1 | awk '{print $5}' | sed 's/%//'")
        
        info['cpu_usage'] = cpu_result.stdout.strip() if cpu_result.returncode == 0 else "Unknown"
        info['memory_usage'] = mem_result.stdout.strip() if mem_result.returncode == 0 else "Unknown"
        info['disk_usage'] = disk_result.stdout.strip() if disk_result.returncode == 0 else "Unknown"
        
        # System uptime
        uptime_result = self.run_ssh_command("uptime -p")
        info['uptime'] = uptime_result.stdout.strip() if uptime_result.returncode == 0 else "Unknown"
        
        # Load average
        load_result = self.run_ssh_command("cat /proc/loadavg | awk '{print $1, $2, $3}'")
        info['load_average'] = load_result.stdout.strip() if load_result.returncode == 0 else "Unknown"
        
        # Network connections
        net_result = self.run_ssh_command("netstat -an | grep ESTABLISHED | wc -l")
        info['active_connections'] = net_result.stdout.strip() if net_result.returncode == 0 else "Unknown"
        
        return info

    def get_bot_status(self) -> Dict:
        """Get current bot status."""
        print("Getting bot status...")
        
        # Check if bot process is running
        result = self.run_ssh_command(f"ps aux | grep 'python run.py' | grep -v grep")
        is_running = result.returncode == 0 and result.stdout.strip()
        
        # Get recent logs
        log_result = self.run_ssh_command(f"tail -10 {self.config['bot_directory']}/{self.config['log_file']}")
        recent_logs = log_result.stdout if log_result.returncode == 0 else "No logs available"
        
        # Get disk usage
        disk_result = self.run_ssh_command(f"df -h {self.config['bot_directory']}")
        disk_usage = disk_result.stdout if disk_result.returncode == 0 else "Unknown"
        
        # Get memory usage
        mem_result = self.run_ssh_command("free -h")
        memory_usage = mem_result.stdout if disk_result.returncode == 0 else "Unknown"
        
        # Get bot uptime
        if is_running:
            uptime_result = self.run_ssh_command("ps -eo pid,etime,cmd | grep 'python run.py' | grep -v grep | awk '{print $2}'")
            bot_uptime = uptime_result.stdout.strip() if uptime_result.returncode == 0 else "Unknown"
        else:
            bot_uptime = "Not running"
        
        return {
            "is_running": bool(is_running),
            "recent_logs": recent_logs,
            "disk_usage": disk_usage,
            "memory_usage": memory_usage,
            "bot_uptime": bot_uptime
        }

    def start_bot(self) -> bool:
        """Start the QuranBot on VPS."""
        print("Starting QuranBot...")
        
        # Kill any existing processes
        self.run_ssh_command(f"pkill -f 'python run.py'", capture_output=False)
        time.sleep(2)
        
        # Start the bot
        start_cmd = f"cd {self.config['bot_directory']} && source {self.config['venv_name']}/bin/activate && nohup python run.py &"
        result = self.run_ssh_command(start_cmd, capture_output=False)
        
        if result.returncode == 0:
            print("SUCCESS: Bot started successfully!")
            self.send_discord_notification("Bot started successfully!")
            time.sleep(3)
            # Verify it's running
            status = self.get_bot_status()
            if status["is_running"]:
                print("SUCCESS: Bot is confirmed running!")
                return True
            else:
                print("WARNING: Bot may not have started properly. Check logs.")
                self.send_discord_notification("Bot may not have started properly. Check logs.")
                return False
        else:
            print("ERROR: Failed to start bot!")
            self.send_discord_notification("Failed to start bot!")
            return False

    def stop_bot(self) -> bool:
        """Stop the QuranBot on VPS."""
        print("Stopping QuranBot...")
        result = self.run_ssh_command(f"pkill -f 'python run.py'", capture_output=False)
        
        if result.returncode == 0:
            print("SUCCESS: Bot stopped successfully!")
            self.send_discord_notification("Bot stopped successfully!")
            return True
        else:
            print("WARNING: Bot may not have been running or failed to stop.")
            self.send_discord_notification("Bot may not have been running or failed to stop.")
            return False

    def restart_bot(self) -> bool:
        """Restart the QuranBot on VPS."""
        print("Restarting QuranBot...")
        self.send_discord_notification("Restarting bot...")
        
        # Step 1: Stop the bot
        print("Step 1: Stopping bot...")
        stop_result = self.run_ssh_command(f"pkill -f 'python run.py'", capture_output=False)
        time.sleep(3)  # Wait for process to fully stop
        
        # Step 2: Start the bot
        print("Step 2: Starting bot...")
        start_cmd = f"cd {self.config['bot_directory']} && source {self.config['venv_name']}/bin/activate && nohup python run.py &"
        start_result = self.run_ssh_command(start_cmd, capture_output=False)
        
        if start_result.returncode == 0:
            print("SUCCESS: Bot restart command sent!")
            time.sleep(3)  # Wait for bot to start
            
            # Step 3: Verify bot is running
            print("Step 3: Verifying bot is running...")
            status = self.get_bot_status()
            if status["is_running"]:
                print("SUCCESS: Bot restarted successfully!")
                self.send_discord_notification("Bot restarted successfully!")
                return True
            else:
                print("ERROR: Bot restart failed! Bot is not running.")
                self.send_discord_notification("Bot restart failed! Bot is not running.")
                return False
        else:
            print("ERROR: Failed to start bot during restart!")
            self.send_discord_notification("Failed to start bot during restart!")
            return False

    def deploy_bot(self) -> bool:
        """Deploy the bot to VPS (pull latest changes and restart)."""
        print("Deploying QuranBot...")
        self.send_discord_notification("Starting bot deployment...")
        
        # Pull latest changes
        pull_cmd = f"cd {self.config['bot_directory']} && git pull origin master"
        result = self.run_ssh_command(pull_cmd)
        
        if result.returncode != 0:
            print("ERROR: Failed to pull latest changes!")
            print(f"Error: {result.stderr}")
            self.send_discord_notification("Failed to pull latest changes!")
            return False
        
        print("SUCCESS: Code updated successfully!")
        self.send_discord_notification("Code updated successfully!")
        
        # Install/update dependencies
        install_cmd = f"cd {self.config['bot_directory']} && source {self.config['venv_name']}/bin/activate && pip install -r requirements.txt"
        result = self.run_ssh_command(install_cmd)
        
        if result.returncode != 0:
            print("WARNING: Some dependencies may not have installed properly.")
            self.send_discord_notification("Warning: Some dependencies may not have installed properly.")
        
        # Restart the bot
        return self.restart_bot()

    def view_logs(self, lines: int = 50) -> None:
        """View bot logs."""
        print(f"Showing last {lines} lines of bot logs...")
        result = self.run_ssh_command(f"tail -{lines} {self.config['bot_directory']}/{self.config['log_file']}")
        
        if result.returncode == 0:
            print("\n" + "="*80)
            print("BOT LOGS:")
            print("="*80)
            print(result.stdout)
            print("="*80)
        else:
            print("ERROR: Failed to retrieve logs!")

    def search_logs(self, search_term: str, lines: int = 100) -> None:
        """Search bot logs for specific terms."""
        print(f"Searching logs for '{search_term}'...")
        result = self.run_ssh_command(f"grep -n '{search_term}' {self.config['bot_directory']}/{self.config['log_file']} | tail -{lines}")
        
        if result.returncode == 0 and result.stdout.strip():
            print("\n" + "="*80)
            print(f"LOG SEARCH RESULTS FOR '{search_term}':")
            print("="*80)
            print(result.stdout)
            print("="*80)
        else:
            print(f"ERROR: No results found for '{search_term}'")

    def clear_logs(self) -> bool:
        """Clear old log files."""
        print("Clearing old log files...")
        result = self.run_ssh_command(f"cd {self.config['bot_directory']} && find . -name '*.log*' -mtime +7 -delete")
        
        if result.returncode == 0:
            print("SUCCESS: Old log files cleared successfully!")
            return True
        else:
            print("ERROR: Failed to clear log files!")
            return False

    def upload_audio_files(self, local_audio_path: str) -> bool:
        """Upload audio files to VPS."""
        print("Uploading audio files...")
        
        if not os.path.exists(local_audio_path):
            print(f"ERROR: Local audio path not found: {local_audio_path}")
            return False
        
        # Create remote audio directory
        self.run_ssh_command(f"mkdir -p {self.config['bot_directory']}/audio")
        
        # Upload using scp
        scp_cmd = f"scp -i {self.config['ssh_key_path']} -r {local_audio_path}/* {self.config['user']}@{self.config['ip']}:{self.config['bot_directory']}/audio/"
        
        print(f"Running: {scp_cmd}")
        result = subprocess.run(scp_cmd, shell=True)
        
        if result.returncode == 0:
            print("SUCCESS: Audio files uploaded successfully!")
            return True
        else:
            print("ERROR: Failed to upload audio files!")
            return False

    def backup_bot(self) -> bool:
        """Create a backup of the bot."""
        print("Creating backup...")
        self.send_discord_notification("Creating backup...")
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_cmd = f"cd {self.config['bot_directory']} && tar -czf backup_{timestamp}.tar.gz --exclude=venv --exclude=*.log --exclude=__pycache__ ."
        result = self.run_ssh_command(backup_cmd)
        
        if result.returncode == 0:
            print(f"SUCCESS: Backup created: backup_{timestamp}.tar.gz")
            self.send_discord_notification(f"Backup created: `backup_{timestamp}.tar.gz`")
            return True
        else:
            print("ERROR: Failed to create backup!")
            self.send_discord_notification("Failed to create backup!")
            return False

    def list_backups(self) -> None:
        """List available backups."""
        print("Listing available backups...")
        result = self.run_ssh_command(f"cd {self.config['bot_directory']} && ls -la *.tar.gz 2>/dev/null || echo 'No backup files found'")
        
        if result.returncode == 0:
            print("\n" + "="*80)
            print("AVAILABLE BACKUPS:")
            print("="*80)
            print(result.stdout)
            print("="*80)

    def restore_backup(self, backup_name: str) -> bool:
        """Restore from a backup."""
        print(f"Restoring from backup: {backup_name}")
        self.send_discord_notification(f"Restoring from backup: `{backup_name}`")
        
        # Stop bot first
        self.stop_bot()
        
        # Restore backup
        restore_cmd = f"cd {self.config['bot_directory']} && tar -xzf {backup_name} --strip-components=0"
        result = self.run_ssh_command(restore_cmd)
        
        if result.returncode == 0:
            print("SUCCESS: Backup restored successfully!")
            self.send_discord_notification("Backup restored successfully!")
            # Restart bot
            return self.start_bot()
        else:
            print("ERROR: Failed to restore backup!")
            self.send_discord_notification("Failed to restore backup!")
            return False

    def cleanup_old_backups(self) -> bool:
        """Clean up old backup files."""
        print("Cleaning up old backups...")
        days = self.config.get('backup_retention_days', 7)
        cleanup_cmd = f"cd {self.config['bot_directory']} && find . -name '*.tar.gz' -mtime +{days} -delete"
        result = self.run_ssh_command(cleanup_cmd)
        
        if result.returncode == 0:
            print(f"SUCCESS: Old backups (older than {days} days) cleaned up!")
            return True
        else:
            print("ERROR: Failed to cleanup old backups!")
            return False

    def setup_environment(self) -> bool:
        """Initial setup of the bot environment on VPS."""
        print("Setting up bot environment...")
        
        # Clone repository if it doesn't exist
        clone_cmd = f"if [ ! -d '{self.config['bot_directory']}' ]; then git clone {self.config['repo_url']} {self.config['bot_directory']}; fi"
        result = self.run_ssh_command(clone_cmd)
        
        if result.returncode != 0:
            print("ERROR: Failed to clone repository!")
            return False
        
        # Create virtual environment
        venv_cmd = f"cd {self.config['bot_directory']} && python3 -m venv {self.config['venv_name']}"
        result = self.run_ssh_command(venv_cmd)
        
        if result.returncode != 0:
            print("ERROR: Failed to create virtual environment!")
            return False
        
        # Install dependencies
        install_cmd = f"cd {self.config['bot_directory']} && source {self.config['venv_name']}/bin/activate && pip install -r requirements.txt"
        result = self.run_ssh_command(install_cmd)
        
        if result.returncode != 0:
            print("WARNING: Some dependencies may not have installed properly.")
        
        # Create necessary directories
        mkdir_cmd = f"cd {self.config['bot_directory']} && mkdir -p logs audio"
        self.run_ssh_command(mkdir_cmd)
        
        print("SUCCESS: Environment setup completed!")
        return True

    def monitor_bot(self, duration_minutes: int = 60) -> None:
        """Monitor bot continuously for specified duration."""
        print(f"Monitoring bot for {duration_minutes} minutes...")
        self.send_discord_notification(f"Starting bot monitoring for {duration_minutes} minutes...")
        end_time = time.time() + (duration_minutes * 60)
        
        while time.time() < end_time:
            status = self.get_bot_status()
            system_info = self.get_system_info()
            
            print(f"\n{'='*60}")
            print(f"Status Check - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*60}")
            print(f"Bot Running: {'YES' if status['is_running'] else 'NO'}")
            print(f"Bot Uptime: {status['bot_uptime']}")
            print(f"CPU Usage: {system_info['cpu_usage']}%")
            print(f"Memory Usage: {system_info['memory_usage']}%")
            print(f"Disk Usage: {system_info['disk_usage']}%")
            print(f"Load Average: {system_info['load_average']}")
            
            # Check for critical issues
            cpu_usage = float(system_info['cpu_usage']) if system_info['cpu_usage'] != "Unknown" else 0
            mem_usage = float(system_info['memory_usage']) if system_info['memory_usage'] != "Unknown" else 0
            disk_usage = float(system_info['disk_usage']) if system_info['disk_usage'] != "Unknown" else 0
            
            if cpu_usage > 90:
                self.send_discord_notification(f"WARNING: High CPU usage: {cpu_usage}%")
            if mem_usage > 90:
                self.send_discord_notification(f"WARNING: High memory usage: {mem_usage}%")
            if disk_usage > 90:
                self.send_discord_notification(f"WARNING: High disk usage: {disk_usage}%")
            
            if not status['is_running'] and self.config.get('auto_restart_on_failure', False):
                print("Bot is down, attempting auto-restart...")
                self.send_discord_notification("Bot is down, attempting auto-restart...")
                self.start_bot()
            
            time.sleep(self.config.get('monitoring_interval', 300))  # 5 minutes default
        
        self.send_discord_notification("Bot monitoring completed!")

    def send_discord_notification(self, message: str) -> bool:
        """Send notification to Discord webhook."""
        if not self.config.get('discord_webhook'):
            return False
        
        try:
            payload = {"content": f"**QuranBot VPS**: {message}"}
            response = requests.post(self.config['discord_webhook'], json=payload, timeout=10)
            return response.status_code == 204
        except Exception as e:
            print(f"Failed to send Discord notification: {e}")
            return False

    def emergency_restart(self) -> bool:
        """Emergency restart - force kill and restart everything."""
        print("EMERGENCY: Emergency restart initiated...")
        self.send_discord_notification("EMERGENCY: Emergency restart initiated...")
        
        # Force kill all Python processes
        self.run_ssh_command("pkill -9 -f python", capture_output=False)
        time.sleep(5)
        
        # Clean up any zombie processes
        self.run_ssh_command("killall -9 python", capture_output=False)
        time.sleep(2)
        
        # Restart bot
        result = self.start_bot()
        if result:
            self.send_discord_notification("SUCCESS: Emergency restart completed successfully!")
        else:
            self.send_discord_notification("ERROR: Emergency restart failed!")
        return result

    def check_disk_space(self) -> Dict:
        """Check disk space on VPS."""
        print("Checking disk space...")
        print()
        print("Main Disk Usage:")
        result = self.run_ssh_command("df -h /")
        if result.returncode == 0:
            print(result.stdout.strip())
        else:
            print("ERROR: Failed to get disk usage!")
        
        print()
        print("All Mounted Disks:")
        result = self.run_ssh_command("df -h | grep -E '^/dev/'")
        if result.returncode == 0:
            print(result.stdout.strip())
        else:
            print("ERROR: Failed to get disk information!")
        
        return {}

    def check_network_status(self) -> Dict:
        """Check network connectivity and status."""
        print("Checking network status...")
        
        # Check internet connectivity
        ping_result = self.run_ssh_command("ping -c 3 8.8.8.8")
        # Check DNS
        dns_result = self.run_ssh_command("nslookup google.com")
        # Check open ports
        ports_result = self.run_ssh_command("netstat -tlnp | grep LISTEN")
        
        print("\n" + "="*80)
        print("NETWORK STATUS:")
        print("="*80)
        print("Internet Connectivity:")
        print(ping_result.stdout if ping_result.returncode == 0 else "ERROR: No internet connection")
        print("\nDNS Resolution:")
        print(dns_result.stdout if dns_result.returncode == 0 else "ERROR: DNS issues")
        print("\nOpen Ports:")
        print(ports_result.stdout if ports_result.returncode == 0 else "No listening ports found")
        print("="*80)
        
        return {
            "internet": ping_result.returncode == 0,
            "dns": dns_result.returncode == 0,
            "ports": ports_result.stdout if ports_result.returncode == 0 else ""
        }

    def update_system(self) -> bool:
        """Update system packages."""
        print("Updating system packages...")
        
        update_cmd = "apt update && apt upgrade -y"
        result = self.run_ssh_command(update_cmd)
        
        if result.returncode == 0:
            print("SUCCESS: System updated successfully!")
            return True
        else:
            print("ERROR: Failed to update system!")
            return False

    def interactive_menu(self):
        """Interactive menu for VPS management."""
        while True:
            print("\n" + "="*80)
            print("                    QuranBot VPS Manager")
            print("="*80)
            print()
            print("BOT CONTROL:")
            print("1.  Check Connection          - Test SSH connection to VPS")
            print("2.  Get Bot Status           - Check if bot is running and get uptime")
            print("3.  Start Bot                - Start the QuranBot on VPS")
            print("4.  Stop Bot                 - Stop the QuranBot on VPS")
            print("5.  Restart Bot              - Stop and restart the bot")
            print("6.  Deploy Bot               - Pull latest code and restart")
            print()
            print("LOGS & MONITORING:")
            print("7.  View Logs                - Show recent bot log entries")
            print("8.  Search Logs              - Search logs for specific terms")
            print("9.  Download All Logs        - Download all log files to local logs folder")
            print("10. Clear Old Logs           - Remove log files older than 7 days")
            print()
            print("BACKUP & RESTORE:")
            print("11. Create Backup            - Create timestamped backup of bot")
            print("12. List Backups             - Show all available backup files")
            print("13. Restore Backup           - Restore bot from backup file")
            print("14. Cleanup Old Backups      - Remove backups older than 7 days")
            print()
            print("SYSTEM MANAGEMENT:")
            print("15. Setup Environment        - Initial bot setup (first time only)")
            print("16. Monitor Bot              - Continuous monitoring with alerts")
            print("17. System Information       - CPU, memory, disk usage, uptime")
            print("18. Check Disk Space         - Show disk space on VPS")
            print("19. Check Network Status     - Test internet, DNS, open ports")
            print()
            print("UTILITIES:")
            print("20. Upload Audio Files       - Upload audio files to VPS")
            print("21. Update System            - Update system packages on VPS")
            print("22. Emergency Restart        - Force kill and restart everything")
            print("23. Exit                     - Close the VPS manager")
            print("="*80)
            
            choice = input("Enter your choice (1-23): ").strip()
            
            if choice == "1":
                self.check_connection()
            elif choice == "2":
                status = self.get_bot_status()
                print(f"\nBot Status: {'RUNNING' if status['is_running'] else 'STOPPED'}")
                print(f"Bot Uptime: {status['bot_uptime']}")
            elif choice == "3":
                self.start_bot()
            elif choice == "4":
                self.stop_bot()
            elif choice == "5":
                self.restart_bot()
            elif choice == "6":
                self.deploy_bot()
            elif choice == "7":
                lines = input("Number of log lines to show (default 50): ").strip()
                lines = int(lines) if lines.isdigit() else 50
                self.view_logs(lines)
            elif choice == "8":
                search_term = input("Enter search term: ").strip()
                if search_term:
                    lines = input("Number of lines to search (default 100): ").strip()
                    lines = int(lines) if lines.isdigit() else 100
                    self.search_logs(search_term, lines)
                else:
                    print("ERROR: No search term provided!")
            elif choice == "9":
                self.download_all_logs()
            elif choice == "10":
                self.clear_logs()
            elif choice == "11":
                self.backup_bot()
            elif choice == "12":
                self.list_backups()
            elif choice == "13":
                backup_name = input("Enter backup filename: ").strip()
                if backup_name:
                    self.restore_backup(backup_name)
                else:
                    print("ERROR: No backup name provided!")
            elif choice == "14":
                self.cleanup_old_backups()
            elif choice == "15":
                self.setup_environment()
            elif choice == "16":
                duration = input("Monitoring duration in minutes (default 60): ").strip()
                duration = int(duration) if duration.isdigit() else 60
                self.monitor_bot(duration)
            elif choice == "17":
                info = self.get_system_info()
                print(f"\nSystem Information:")
                print(f"CPU Usage: {info['cpu_usage']}%")
                print(f"Memory Usage: {info['memory_usage']}%")
                print(f"Disk Usage: {info['disk_usage']}%")
                print(f"Uptime: {info['uptime']}")
                print(f"Load Average: {info['load_average']}")
                print(f"Active Connections: {info['active_connections']}")
            elif choice == "18":
                self.check_disk_space()
            elif choice == "19":
                self.check_network_status()
            elif choice == "20":
                audio_path = input("Enter local audio files path: ").strip()
                if audio_path:
                    self.upload_audio_files(audio_path)
                else:
                    print("ERROR: No path provided!")
            elif choice == "21":
                self.update_system()
            elif choice == "22":
                self.emergency_restart()
            elif choice == "23":
                print("Goodbye!")
                break
            else:
                print("ERROR: Invalid choice!")
            
            input("\nPress Enter to continue...")

    def download_all_logs(self) -> bool:
        """Download all log files from VPS to local logs folder."""
        print("Downloading all log files from VPS...")
        
        # Create local logs directory if it doesn't exist
        local_logs_dir = os.path.join(self.config['local_project'], 'logs')
        os.makedirs(local_logs_dir, exist_ok=True)
        
        # Get timestamp for the download
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # Create a tar.gz of all logs on VPS
        remote_logs_archive = f"logs_backup_{timestamp}.tar.gz"
        create_archive_cmd = f"cd {self.config['bot_directory']} && tar -czf {remote_logs_archive} logs/ *.log 2>/dev/null || echo 'No logs found'"
        
        print("Step 1: Creating log archive on VPS...")
        result = self.run_ssh_command(create_archive_cmd)
        
        if result.returncode != 0:
            print("ERROR: Failed to create log archive on VPS!")
            return False
        
        # Download the archive
        print("Step 2: Downloading log archive...")
        local_archive_path = os.path.join(local_logs_dir, remote_logs_archive)
        
        # Use proper path formatting for Windows
        scp_cmd = f"scp -i {self.config['ssh_key_path']} {self.config['user']}@{self.config['ip']}:{self.config['bot_directory']}/{remote_logs_archive} \"{local_logs_dir}\""
        
        print(f"Running: {scp_cmd}")
        result = subprocess.run(scp_cmd, shell=True)
        
        if result.returncode == 0:
            print(f"SUCCESS: Log archive downloaded to: {local_archive_path}")
            
            # Extract the archive
            print("Step 3: Extracting logs...")
            extract_cmd = f"cd \"{local_logs_dir}\" && tar -xzf {remote_logs_archive}"
            result = subprocess.run(extract_cmd, shell=True)
            
            if result.returncode == 0:
                print(f"SUCCESS: Logs extracted to: {local_logs_dir}")
                
                # Clean up the archive
                os.remove(local_archive_path)
                print("SUCCESS: Temporary archive removed")
                
                # List downloaded files
                log_files = [f for f in os.listdir(local_logs_dir) if f.endswith('.log')]
                if log_files:
                    print(f"\nDownloaded log files:")
                    for log_file in log_files:
                        print(f"  - {log_file}")
                else:
                    print("No log files found on VPS")
                
                # Clean up remote archive
                cleanup_cmd = f"cd {self.config['bot_directory']} && rm -f {remote_logs_archive}"
                self.run_ssh_command(cleanup_cmd)
                
                return True
            else:
                print("ERROR: Failed to extract log archive!")
                return False
        else:
            print("ERROR: Failed to download log archive!")
            return False

def main():
    parser = argparse.ArgumentParser(description="QuranBot VPS Manager - Complete VPS management tool for QuranBot")
    parser.add_argument("action", nargs="?", choices=[
        "status", "start", "stop", "restart", "deploy", "logs", "search-logs", "clear-logs", "download-logs",
        "upload", "backup", "list-backups", "restore", "cleanup-backups", "setup", "monitor",
        "system-info", "disk-space", "network", "update", "emergency-restart", "check", "menu"
    ], help="Action to perform")
    parser.add_argument("--lines", "-l", type=int, default=50, help="Number of log lines to show")
    parser.add_argument("--audio-path", "-a", help="Path to audio files for upload")
    parser.add_argument("--search-term", "-s", help="Search term for logs")
    parser.add_argument("--backup-name", "-b", help="Backup filename for restore")
    parser.add_argument("--duration", "-d", type=int, default=60, help="Monitoring duration in minutes")
    
    # Add detailed help for each action
    parser.add_argument_group("Available Actions", description="""
    status              - Check if bot is running and get uptime
    start               - Start the QuranBot on VPS
    stop                - Stop the QuranBot on VPS
    restart             - Stop and restart the bot
    deploy              - Pull latest code and restart
    logs                - Show recent bot log entries
    search-logs         - Search logs for specific terms
    clear-logs          - Remove log files older than 7 days
    upload              - Upload audio files to VPS
    backup              - Create timestamped backup of bot
    list-backups        - Show all available backup files
    restore             - Restore bot from backup file
    cleanup-backups     - Remove backups older than 7 days
    setup               - Initial bot setup (first time only)
    monitor             - Continuous monitoring with alerts
    system-info         - CPU, memory, disk usage, uptime
    disk-space          - Show disk space on VPS
    network             - Test internet, DNS, open ports
    update              - Update system packages on VPS
    emergency-restart   - Force kill and restart everything
    check               - Test SSH connection to VPS
    menu                - Interactive menu (default)
    """)
    
    args = parser.parse_args()
    
    manager = VPSManager()
    
    if args.action == "status":
        status = manager.get_bot_status()
        print(f"Bot Status: {'RUNNING' if status['is_running'] else 'STOPPED'}")
        print(f"Bot Uptime: {status['bot_uptime']}")
    elif args.action == "start":
        manager.start_bot()
    elif args.action == "stop":
        manager.stop_bot()
    elif args.action == "restart":
        manager.restart_bot()
    elif args.action == "deploy":
        manager.deploy_bot()
    elif args.action == "logs":
        manager.view_logs(args.lines)
    elif args.action == "search-logs":
        if args.search_term:
            manager.search_logs(args.search_term, args.lines)
        else:
            print("ERROR: Please provide search term with --search-term")
    elif args.action == "clear-logs":
        manager.clear_logs()
    elif args.action == "download-logs":
        manager.download_all_logs()
    elif args.action == "upload":
        if args.audio_path:
            manager.upload_audio_files(args.audio_path)
        else:
            print("ERROR: Please provide audio path with --audio-path")
    elif args.action == "backup":
        manager.backup_bot()
    elif args.action == "list-backups":
        manager.list_backups()
    elif args.action == "restore":
        if args.backup_name:
            manager.restore_backup(args.backup_name)
        else:
            print("ERROR: Please provide backup name with --backup-name")
    elif args.action == "cleanup-backups":
        manager.cleanup_old_backups()
    elif args.action == "setup":
        manager.setup_environment()
    elif args.action == "monitor":
        manager.monitor_bot(args.duration)
    elif args.action == "system-info":
        info = manager.get_system_info()
        print(f"\nSystem Information:")
        print(f"CPU Usage: {info['cpu_usage']}%")
        print(f"Memory Usage: {info['memory_usage']}%")
        print(f"Disk Usage: {info['disk_usage']}%")
        print(f"Uptime: {info['uptime']}")
        print(f"Load Average: {info['load_average']}")
        print(f"Active Connections: {info['active_connections']}")
    elif args.action == "disk-space":
        manager.check_disk_space()
    elif args.action == "network":
        manager.check_network_status()
    elif args.action == "update":
        manager.update_system()
    elif args.action == "emergency-restart":
        manager.emergency_restart()
    elif args.action == "check":
        manager.check_connection()
    elif args.action == "menu" or not args.action:
        manager.interactive_menu()
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 