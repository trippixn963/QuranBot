#!/usr/bin/env python3
"""
Enhanced QuranBot VPS Manager
Advanced VPS management system with comprehensive features
"""

import json
import os
import sys
import time
import datetime
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import paramiko
from paramiko import SSHClient, AutoAddPolicy
import colorama
from colorama import Fore, Back, Style
import psutil

class VPSManager:
    """Advanced VPS management system for QuranBot"""
    
    def __init__(self, config_path: str = "scripts/vps/config/vps_config.json"):
        """Initialize VPS Manager with configuration"""
        colorama.init(autoreset=True)
        self.config_path = config_path
        self.config = self._load_config()
        self.ssh_client = None
        self.connected = False
        self.logger = self._setup_logging()
        self.session_start = datetime.datetime.now()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load VPS configuration from JSON file"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            self._print_error(f"Config file not found: {self.config_path}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            self._print_error(f"Invalid JSON in config file: {e}")
            sys.exit(1)
    
    def _setup_logging(self) -> logging.Logger:
        """Setup local logging for VPS operations"""
        log_dir = Path("logs/vps")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d")
        log_file = log_dir / f"vps_manager_{timestamp}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)
    
    def _print_header(self, title: str):
        """Print formatted header"""
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}{title:^60}")
        print(f"{Fore.CYAN}{'='*60}\n")
    
    def _print_success(self, message: str):
        """Print success message"""
        print(f"{Fore.GREEN}✅ {message}")
        self.logger.info(message)
    
    def _print_error(self, message: str):
        """Print error message"""
        print(f"{Fore.RED}❌ {message}")
        self.logger.error(message)
    
    def _print_warning(self, message: str):
        """Print warning message"""
        print(f"{Fore.YELLOW}⚠️  {message}")
        self.logger.warning(message)
    
    def _print_info(self, message: str):
        """Print info message"""
        print(f"{Fore.BLUE}ℹ️  {message}")
        self.logger.info(message)
    
    def connect(self) -> bool:
        """Establish SSH connection to VPS"""
        if self.connected:
            return True
            
        try:
            self.ssh_client = SSHClient()
            self.ssh_client.set_missing_host_key_policy(AutoAddPolicy())
            
            vps_config = self.config['vps']
            self._print_info(f"Connecting to {vps_config['host']}...")
            
            self.ssh_client.connect(
                hostname=vps_config['host'],
                username=vps_config['user'],
                key_filename=vps_config['ssh_key'],
                port=vps_config['port'],
                timeout=vps_config['connection_timeout']
            )
            
            self.connected = True
            self._print_success(f"Connected to VPS: {vps_config['host']}")
            return True
            
        except Exception as e:
            self._print_error(f"Failed to connect to VPS: {e}")
            return False
    
    def disconnect(self):
        """Close SSH connection"""
        if self.ssh_client:
            self.ssh_client.close()
            self.connected = False
            self._print_info("Disconnected from VPS")
    
    def execute_command(self, command: str, timeout: int = None) -> Tuple[int, str, str]:
        """Execute command on VPS and return exit code, stdout, stderr"""
        if not self.connected:
            if not self.connect():
                return 1, "", "Not connected to VPS"
        
        try:
            if timeout is None:
                timeout = self.config['vps']['command_timeout']
            
            self._print_info(f"Executing: {command}")
            stdin, stdout, stderr = self.ssh_client.exec_command(command, timeout=timeout)
            
            exit_code = stdout.channel.recv_exit_status()
            stdout_text = stdout.read().decode('utf-8').strip()
            stderr_text = stderr.read().decode('utf-8').strip()
            
            if exit_code == 0:
                self._print_success(f"Command executed successfully")
            else:
                self._print_error(f"Command failed with exit code {exit_code}")
                
            return exit_code, stdout_text, stderr_text
            
        except Exception as e:
            self._print_error(f"Failed to execute command: {e}")
            return 1, "", str(e)
    
    def get_bot_status(self) -> Dict[str, Any]:
        """Get comprehensive bot status"""
        service_name = self.config['bot']['service_name']
        
        # Get systemd status
        exit_code, stdout, stderr = self.execute_command(f"systemctl status {service_name}")
        service_status = {
            'running': exit_code == 0,
            'status_output': stdout,
            'error': stderr if exit_code != 0 else None
        }
        
        # Get process information
        exit_code, stdout, stderr = self.execute_command(f"pgrep -f {service_name}")
        if exit_code == 0:
            pids = stdout.strip().split('\n') if stdout.strip() else []
            service_status['pids'] = [int(pid) for pid in pids if pid]
        else:
            service_status['pids'] = []
        
        # Get memory and CPU usage
        if service_status['pids']:
            pid = service_status['pids'][0]
            exit_code, stdout, stderr = self.execute_command(f"ps -p {pid} -o %cpu,%mem,etime --no-headers")
            if exit_code == 0:
                parts = stdout.strip().split()
                if len(parts) >= 3:
                    service_status['cpu_percent'] = float(parts[0])
                    service_status['memory_percent'] = float(parts[1])
                    service_status['uptime'] = parts[2]
        
        # Get recent logs
        log_path = self.config['bot']['log_path']
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        exit_code, stdout, stderr = self.execute_command(f"tail -20 {log_path}/{today}.log")
        if exit_code == 0:
            service_status['recent_logs'] = stdout.split('\n')[-10:]  # Last 10 lines
        
        return service_status
    
    def start_bot(self) -> bool:
        """Start the bot service"""
        service_name = self.config['bot']['service_name']
        self._print_info(f"Starting {service_name} service...")
        
        exit_code, stdout, stderr = self.execute_command(f"systemctl start {service_name}")
        if exit_code == 0:
            # Wait a moment for service to start
            time.sleep(3)
            
            # Verify it's running
            status = self.get_bot_status()
            if status['running']:
                self._print_success(f"{service_name} started successfully")
                return True
            else:
                self._print_error(f"{service_name} failed to start properly")
                return False
        else:
            self._print_error(f"Failed to start {service_name}: {stderr}")
            return False
    
    def stop_bot(self) -> bool:
        """Stop the bot service"""
        service_name = self.config['bot']['service_name']
        self._print_info(f"Stopping {service_name} service...")
        
        exit_code, stdout, stderr = self.execute_command(f"systemctl stop {service_name}")
        if exit_code == 0:
            # Wait a moment for service to stop
            time.sleep(3)
            
            # Verify it's stopped
            status = self.get_bot_status()
            if not status['running']:
                self._print_success(f"{service_name} stopped successfully")
                return True
            else:
                self._print_warning(f"{service_name} may still be running")
                return False
        else:
            self._print_error(f"Failed to stop {service_name}: {stderr}")
            return False
    
    def restart_bot(self) -> bool:
        """Restart the bot service"""
        service_name = self.config['bot']['service_name']
        self._print_info(f"Restarting {service_name} service...")
        
        exit_code, stdout, stderr = self.execute_command(f"systemctl restart {service_name}")
        if exit_code == 0:
            # Wait a moment for service to restart
            time.sleep(5)
            
            # Verify it's running
            status = self.get_bot_status()
            if status['running']:
                self._print_success(f"{service_name} restarted successfully")
                return True
            else:
                self._print_error(f"{service_name} failed to restart properly")
                return False
        else:
            self._print_error(f"Failed to restart {service_name}: {stderr}")
            return False
    
    def update_bot(self, auto_restart: bool = True) -> bool:
        """Update bot from repository"""
        install_path = self.config['bot']['install_path']
        branch = self.config['bot']['branch']
        
        self._print_info("Updating bot from repository...")
        
        # Create backup if enabled
        if self.config['deployment']['backup_before_deploy']:
            if not self.create_backup(f"pre_update_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"):
                self._print_warning("Backup failed, continuing with update...")
        
        # Navigate to bot directory and pull latest changes
        commands = [
            f"cd {install_path}",
            f"git fetch origin {branch}",
            f"git reset --hard origin/{branch}",
            "pip install -r requirements.txt",
        ]
        
        for cmd in commands:
            exit_code, stdout, stderr = self.execute_command(cmd)
            if exit_code != 0:
                self._print_error(f"Update failed at step: {cmd}")
                if self.config['deployment']['rollback_on_failure']:
                    self._print_info("Rolling back to previous version...")
                    # Implement rollback logic here
                return False
        
        self._print_success("Bot updated successfully")
        
        # Restart if auto-restart is enabled
        if auto_restart and self.config['deployment']['auto_restart_on_update']:
            return self.restart_bot()
        
        return True
    
    def create_backup(self, backup_name: str = None) -> bool:
        """Create backup of bot data and configuration"""
        if not self.config['backup']['enabled']:
            self._print_warning("Backup is disabled in configuration")
            return False
        
        if backup_name is None:
            backup_name = f"backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        backup_path = self.config['bot']['backup_path']
        install_path = self.config['bot']['install_path']
        data_path = self.config['bot']['data_path']
        
        self._print_info(f"Creating backup: {backup_name}")
        
        # Create backup directory
        exit_code, stdout, stderr = self.execute_command(f"mkdir -p {backup_path}/{backup_name}")
        if exit_code != 0:
            self._print_error(f"Failed to create backup directory: {stderr}")
            return False
        
        # Backup configuration and data
        backup_commands = [
            f"cp -r {data_path} {backup_path}/{backup_name}/",
            f"cp {install_path}/*.json {backup_path}/{backup_name}/ 2>/dev/null || true",
            f"cp {install_path}/*.yml {backup_path}/{backup_name}/ 2>/dev/null || true",
        ]
        
        if self.config['backup']['include_logs']:
            log_path = self.config['bot']['log_path']
            backup_commands.append(f"cp -r {log_path} {backup_path}/{backup_name}/")
        
        for cmd in backup_commands:
            exit_code, stdout, stderr = self.execute_command(cmd)
            if exit_code != 0 and "No such file" not in stderr:
                self._print_warning(f"Backup warning: {stderr}")
        
        # Compress backup
        exit_code, stdout, stderr = self.execute_command(
            f"cd {backup_path} && tar -czf {backup_name}.tar.gz {backup_name} && rm -rf {backup_name}"
        )
        
        if exit_code == 0:
            self._print_success(f"Backup created: {backup_name}.tar.gz")
            return True
        else:
            self._print_error(f"Failed to compress backup: {stderr}")
            return False
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information"""
        info = {}
        
        # System information
        commands = {
            'os_info': 'cat /etc/os-release | head -3',
            'uptime': 'uptime',
            'disk_usage': f"df -h {self.config['bot']['install_path']}",
            'memory_usage': 'free -h',
            'cpu_info': 'nproc && cat /proc/loadavg',
            'network_info': 'ip route get 1 | awk \'{print $7}\' | head -1',
            'python_version': f"{self.config['bot']['python_path']} --version",
            'git_status': f"cd {self.config['bot']['install_path']} && git status --porcelain && git log -1 --oneline",
        }
        
        for key, cmd in commands.items():
            exit_code, stdout, stderr = self.execute_command(cmd)
            info[key] = {
                'success': exit_code == 0,
                'output': stdout if exit_code == 0 else stderr,
                'exit_code': exit_code
            }
        
        return info
    
    def cleanup_logs(self, days: int = None) -> bool:
        """Clean up old log files"""
        if days is None:
            days = self.config['monitoring']['log_retention_days']
        
        log_path = self.config['bot']['log_path']
        self._print_info(f"Cleaning up logs older than {days} days...")
        
        exit_code, stdout, stderr = self.execute_command(
            f"find {log_path} -name '*.log' -type f -mtime +{days} -delete"
        )
        
        if exit_code == 0:
            # Count remaining logs
            exit_code, stdout, stderr = self.execute_command(f"ls -1 {log_path}/*.log | wc -l")
            log_count = stdout.strip() if exit_code == 0 else "unknown"
            self._print_success(f"Log cleanup completed. {log_count} logs remaining.")
            return True
        else:
            self._print_error(f"Log cleanup failed: {stderr}")
            return False
    
    def monitor_performance(self, duration: int = 60) -> Dict[str, Any]:
        """Monitor bot performance for specified duration"""
        self._print_info(f"Monitoring performance for {duration} seconds...")
        
        service_name = self.config['bot']['service_name']
        status = self.get_bot_status()
        
        if not status['running']:
            self._print_error("Bot is not running - cannot monitor performance")
            return {}
        
        pid = status['pids'][0]
        performance_data = {
            'start_time': datetime.datetime.now().isoformat(),
            'duration': duration,
            'samples': []
        }
        
        for i in range(duration // 5):  # Sample every 5 seconds
            exit_code, stdout, stderr = self.execute_command(
                f"ps -p {pid} -o %cpu,%mem --no-headers"
            )
            
            if exit_code == 0:
                parts = stdout.strip().split()
                if len(parts) >= 2:
                    sample = {
                        'timestamp': datetime.datetime.now().isoformat(),
                        'cpu_percent': float(parts[0]),
                        'memory_percent': float(parts[1])
                    }
                    performance_data['samples'].append(sample)
                    print(f"Sample {i+1}: CPU {parts[0]}%, Memory {parts[1]}%")
            
            if i < (duration // 5) - 1:  # Don't sleep on last iteration
                time.sleep(5)
        
        # Calculate averages
        if performance_data['samples']:
            cpu_avg = sum(s['cpu_percent'] for s in performance_data['samples']) / len(performance_data['samples'])
            mem_avg = sum(s['memory_percent'] for s in performance_data['samples']) / len(performance_data['samples'])
            
            performance_data['average_cpu'] = round(cpu_avg, 2)
            performance_data['average_memory'] = round(mem_avg, 2)
            
            self._print_success(f"Performance monitoring completed")
            self._print_info(f"Average CPU: {cpu_avg:.2f}%, Average Memory: {mem_avg:.2f}%")
        
        return performance_data
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


if __name__ == "__main__":
    # Command line interface for direct usage
    import argparse
    
    parser = argparse.ArgumentParser(description="QuranBot VPS Manager")
    parser.add_argument("action", choices=[
        "status", "start", "stop", "restart", "update", 
        "backup", "system", "monitor", "cleanup"
    ])
    parser.add_argument("--duration", type=int, default=60, help="Duration for monitoring")
    parser.add_argument("--days", type=int, help="Days for cleanup")
    
    args = parser.parse_args()
    
    with VPSManager() as vps:
        if args.action == "status":
            status = vps.get_bot_status()
            print(json.dumps(status, indent=2))
        elif args.action == "start":
            vps.start_bot()
        elif args.action == "stop":
            vps.stop_bot()
        elif args.action == "restart":
            vps.restart_bot()
        elif args.action == "update":
            vps.update_bot()
        elif args.action == "backup":
            vps.create_backup()
        elif args.action == "system":
            info = vps.get_system_info()
            print(json.dumps(info, indent=2))
        elif args.action == "monitor":
            perf = vps.monitor_performance(args.duration)
            print(json.dumps(perf, indent=2))
        elif args.action == "cleanup":
            vps.cleanup_logs(args.days) 