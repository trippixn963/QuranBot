#!/usr/bin/env python3
"""
QuranBot Advanced VPS Manager
Modern, feature-rich VPS management system with colorful interface
"""

import os
import sys
import json
import time
import datetime
import subprocess
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import argparse

# Try to import colorama, fallback to no colors if not available
try:
    import colorama
    from colorama import Fore, Back, Style, init
    init(autoreset=True)
    COLORS_AVAILABLE = True
except ImportError:
    COLORS_AVAILABLE = False
    # Create dummy color objects
    class DummyColor:
        def __getattr__(self, name): return ""
    Fore = Back = Style = DummyColor()

class VPSManager:
    """Advanced VPS management system for QuranBot"""
    
    def __init__(self, config_path: str = "scripts/vps/config/vps_config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.session_start = datetime.datetime.now()
        self.verbose = False
        
    def _load_config(self) -> Dict[str, Any]:
        """Load VPS configuration from JSON file"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"{Fore.RED}❌ Config file not found: {self.config_path}")
            return self._create_default_config()
        except json.JSONDecodeError as e:
            print(f"{Fore.RED}❌ Invalid JSON in config: {e}")
            sys.exit(1)
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration"""
        config = {
            "vps": {
                "host": "159.89.90.90",
                "user": "root",
                "ssh_key": "C:/Users/hanna/.ssh/id_rsa",
                "port": 22,
                "connection_timeout": 30,
                "command_timeout": 60
            },
            "bot": {
                "service_name": "quranbot",
                "install_path": "/opt/quranbot",
                "log_path": "/opt/quranbot/logs",
                "data_path": "/opt/quranbot/data",
                "backup_path": "/opt/quranbot/backups"
            },
            "local": {
                "log_download_path": "./logs/vps",
                "backup_download_path": "./backups/vps"
            }
        }
        
        # Create config directory
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        # Save default config
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"{Fore.GREEN}✅ Created default config: {self.config_path}")
        return config
    
    def _print_header(self, title: str, width: int = 60):
        """Print formatted header"""
        print(f"\n{Fore.CYAN}{'='*width}")
        print(f"{Fore.CYAN}{title:^{width}}")
        print(f"{Fore.CYAN}{'='*width}")
    
    def _print_success(self, message: str):
        """Print success message"""
        print(f"{Fore.GREEN}✅ {message}")
    
    def _print_error(self, message: str):
        """Print error message"""
        print(f"{Fore.RED}❌ {message}")
    
    def _print_warning(self, message: str):
        """Print warning message"""
        print(f"{Fore.YELLOW}⚠️  {message}")
    
    def _print_info(self, message: str):
        """Print info message"""
        print(f"{Fore.BLUE}ℹ️  {message}")
    
    def _run_ssh_command(self, command: str, timeout: int = None) -> Tuple[int, str, str]:
        """Execute SSH command and return exit code, stdout, stderr"""
        if timeout is None:
            timeout = self.config['vps']['command_timeout']
        
        vps_config = self.config['vps']
        ssh_cmd = [
            'ssh', '-i', vps_config['ssh_key'],
            f"{vps_config['user']}@{vps_config['host']}",
            '-o', 'ConnectTimeout=10',
            '-o', 'StrictHostKeyChecking=no',
            command
        ]
        
        if self.verbose:
            self._print_info(f"Executing: {command}")
        
        try:
            result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return 1, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return 1, "", f"SSH error: {e}"
    
    def test_connection(self) -> bool:
        """Test SSH connection to VPS"""
        self._print_info("Testing SSH connection...")
        exit_code, output, error = self._run_ssh_command("echo 'Connection successful'")
        
        if exit_code == 0:
            self._print_success("SSH connection successful")
            return True
        else:
            self._print_error(f"SSH connection failed: {error}")
            return False
    
    def get_bot_status(self) -> Dict[str, Any]:
        """Get comprehensive bot status"""
        service_name = self.config['bot']['service_name']
        status = {}
        
        # Check if service exists
        exit_code, output, error = self._run_ssh_command(f"systemctl list-unit-files | grep {service_name}")
        status['service_exists'] = exit_code == 0
        
        if not status['service_exists']:
            status['running'] = False
            status['error'] = f"Service {service_name} not found"
            return status
        
        # Get service status
        exit_code, output, error = self._run_ssh_command(f"systemctl is-active {service_name}")
        status['running'] = exit_code == 0 and "active" in output
        status['service_status'] = output
        
        # Get detailed status
        exit_code, output, error = self._run_ssh_command(f"systemctl status {service_name} --no-pager -l")
        status['detailed_status'] = output if exit_code == 0 else error
        
        # Get process info if running
        if status['running']:
            exit_code, output, error = self._run_ssh_command(f"pgrep -f {service_name}")
            if exit_code == 0:
                pids = [int(pid) for pid in output.split() if pid.strip()]
                status['pids'] = pids
                
                # Get CPU and memory usage
                if pids:
                    pid = pids[0]
                    exit_code, output, error = self._run_ssh_command(
                        f"ps -p {pid} -o %cpu,%mem,etime --no-headers"
                    )
                    if exit_code == 0:
                        parts = output.split()
                        if len(parts) >= 3:
                            status['cpu_percent'] = parts[0]
                            status['memory_percent'] = parts[1]
                            status['uptime'] = parts[2]
        
        return status
    
    def start_bot(self) -> bool:
        """Start the bot service"""
        self._print_header("Starting QuranBot")
        service_name = self.config['bot']['service_name']
        
        # Check if already running
        status = self.get_bot_status()
        if status.get('running', False):
            self._print_warning(f"{service_name} is already running")
            return True
        
        exit_code, output, error = self._run_ssh_command(f"systemctl start {service_name}")
        
        if exit_code == 0:
            self._print_success(f"Start command executed successfully")
            
            # Wait and verify
            time.sleep(3)
            status = self.get_bot_status()
            
            if status.get('running', False):
                self._print_success(f"{service_name} is now running")
                if 'uptime' in status:
                    self._print_info(f"Uptime: {status['uptime']}")
                return True
            else:
                self._print_error(f"{service_name} failed to start properly")
                return False
        else:
            self._print_error(f"Failed to start {service_name}: {error}")
            return False
    
    def stop_bot(self) -> bool:
        """Stop the bot service"""
        self._print_header("Stopping QuranBot")
        service_name = self.config['bot']['service_name']
        
        # Check if already stopped
        status = self.get_bot_status()
        if not status.get('running', False):
            self._print_warning(f"{service_name} is already stopped")
            return True
        
        exit_code, output, error = self._run_ssh_command(f"systemctl stop {service_name}")
        
        if exit_code == 0:
            self._print_success(f"Stop command executed successfully")
            
            # Wait and verify
            time.sleep(3)
            status = self.get_bot_status()
            
            if not status.get('running', False):
                self._print_success(f"{service_name} is now stopped")
                return True
            else:
                self._print_warning(f"{service_name} may still be running")
                return False
        else:
            self._print_error(f"Failed to stop {service_name}: {error}")
            return False
    
    def restart_bot(self) -> bool:
        """Restart the bot service"""
        self._print_header("Restarting QuranBot")
        service_name = self.config['bot']['service_name']
        
        exit_code, output, error = self._run_ssh_command(f"systemctl restart {service_name}")
        
        if exit_code == 0:
            self._print_success(f"Restart command executed successfully")
            
            # Wait for service to start
            time.sleep(5)
            status = self.get_bot_status()
            
            if status.get('running', False):
                self._print_success(f"{service_name} restarted successfully")
                if 'uptime' in status:
                    self._print_info(f"New uptime: {status['uptime']}")
                return True
            else:
                self._print_error(f"{service_name} failed to restart properly")
                return False
        else:
            self._print_error(f"Failed to restart {service_name}: {error}")
            return False
    
    def show_status(self):
        """Show comprehensive bot status"""
        self._print_header("QuranBot Status")
        
        status = self.get_bot_status()
        
        if not status.get('service_exists', True):
            self._print_error("Service does not exist on the system")
            return
        
        # Basic status
        if status.get('running', False):
            self._print_success(f"Service is RUNNING")
            if 'cpu_percent' in status:
                self._print_info(f"CPU: {status['cpu_percent']}% | Memory: {status['memory_percent']}% | Uptime: {status['uptime']}")
            if 'pids' in status:
                self._print_info(f"Process IDs: {', '.join(map(str, status['pids']))}")
        else:
            self._print_error("Service is STOPPED")
        
        # Show detailed status
        if status.get('detailed_status'):
            print(f"\n{Fore.BLUE}📊 Detailed Status:")
            lines = status['detailed_status'].split('\n')
            for line in lines[:15]:  # Show first 15 lines
                print(f"  {line}")
            if len(lines) > 15:
                print(f"  ... ({len(lines) - 15} more lines)")
    
    def stream_logs(self):
        """Stream logs in real-time"""
        self._print_header("Live Log Stream")
        print(f"{Fore.YELLOW}📡 Press Ctrl+C to stop streaming")
        
        log_path = self.config['bot']['log_path']
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        log_file = f"{log_path}/{today}.log"
        
        try:
            vps_config = self.config['vps']
            ssh_cmd = [
                'ssh', '-i', vps_config['ssh_key'],
                f"{vps_config['user']}@{vps_config['host']}",
                f"tail -f {log_file}"
            ]
            
            self._print_info(f"Streaming from: {log_file}")
            subprocess.run(ssh_cmd)
            
        except KeyboardInterrupt:
            print(f"\n{Fore.BLUE}ℹ️  Log streaming stopped")
        except Exception as e:
            self._print_error(f"Failed to stream logs: {e}")
    
    def download_logs(self, date: str = None):
        """Download logs for a specific date"""
        self._print_header("Download Logs")
        
        if date is None:
            date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        log_path = self.config['bot']['log_path']
        remote_file = f"{log_path}/{date}.log"
        
        # Create local directory
        local_dir = Path(self.config['local']['log_download_path'])
        local_dir.mkdir(parents=True, exist_ok=True)
        
        local_file = local_dir / f"quranbot_{date}.log"
        
        # Download using scp
        vps_config = self.config['vps']
        scp_cmd = [
            'scp', '-i', vps_config['ssh_key'],
            f"{vps_config['user']}@{vps_config['host']}:{remote_file}",
            str(local_file)
        ]
        
        try:
            self._print_info(f"Downloading logs for {date}...")
            result = subprocess.run(scp_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self._print_success(f"Logs downloaded to: {local_file}")
                
                # Show file size
                size = local_file.stat().st_size
                size_mb = size / (1024 * 1024)
                self._print_info(f"File size: {size_mb:.2f} MB ({size:,} bytes)")
                
                # Ask to open
                try:
                    response = input(f"\n{Fore.CYAN}Open log file? (y/n): ").strip().lower()
                    if response == 'y':
                        if os.name == 'nt':  # Windows
                            os.startfile(str(local_file))
                        else:  # Unix-like
                            subprocess.run(['xdg-open', str(local_file)])
                except KeyboardInterrupt:
                    print()
                    
            else:
                self._print_error(f"Failed to download logs: {result.stderr}")
                
        except Exception as e:
            self._print_error(f"Error downloading logs: {e}")
    
    def system_info(self):
        """Get comprehensive system information"""
        self._print_header("System Information")
        
        commands = {
            "🖥️  Operating System": "cat /etc/os-release | head -3",
            "⏰ System Uptime": "uptime",
            "💾 Memory Usage": "free -h",
            "💿 Disk Usage": "df -h /",
            "⚡ CPU Load": "cat /proc/loadavg",
            "🌐 Network Interface": "ip route get 1 | awk '{print $7}' | head -1",
            "🐍 Python Version": "python3 --version",
            "📦 Pip Packages": "pip3 list | wc -l"
        }
        
        for title, command in commands.items():
            print(f"\n{Fore.BLUE}{title}:")
            exit_code, output, error = self._run_ssh_command(command)
            if exit_code == 0:
                for line in output.split('\n'):
                    print(f"  {line}")
            else:
                print(f"  {Fore.RED}Error: {error}")
    
    def create_backup(self, name: str = None):
        """Create a backup of bot data"""
        self._print_header("Create Backup")
        
        if name is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            name = f"backup_{timestamp}"
        
        bot_path = self.config['bot']['install_path']
        backup_path = self.config['bot']['backup_path']
        
        # Create backup directory
        exit_code, output, error = self._run_ssh_command(f"mkdir -p {backup_path}")
        if exit_code != 0:
            self._print_error(f"Failed to create backup directory: {error}")
            return False
        
        # Create backup
        backup_file = f"{backup_path}/{name}.tar.gz"
        backup_cmd = f"cd {bot_path} && tar -czf {backup_file} data/ *.json *.yml 2>/dev/null"
        
        self._print_info(f"Creating backup: {name}")
        exit_code, output, error = self._run_ssh_command(backup_cmd, timeout=120)
        
        if exit_code == 0:
            # Get backup size
            exit_code, output, error = self._run_ssh_command(f"ls -lh {backup_file}")
            if exit_code == 0:
                size_info = output.split()[4] if len(output.split()) > 4 else "unknown"
                self._print_success(f"Backup created: {name}.tar.gz ({size_info})")
            else:
                self._print_success(f"Backup created: {name}.tar.gz")
            return True
        else:
            self._print_error(f"Failed to create backup: {error}")
            return False
    
    def list_backups(self):
        """List available backups"""
        self._print_header("Available Backups")
        
        backup_path = self.config['bot']['backup_path']
        exit_code, output, error = self._run_ssh_command(f"ls -lht {backup_path}/*.tar.gz 2>/dev/null")
        
        if exit_code == 0 and output:
            print(f"{Fore.BLUE}📦 Backup files:")
            for line in output.split('\n'):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 9:
                        size = parts[4]
                        date = f"{parts[5]} {parts[6]} {parts[7]}"
                        filename = parts[8].split('/')[-1]
                        print(f"  {Fore.GREEN}{filename:<30} {Fore.BLUE}{size:<8} {Fore.YELLOW}{date}")
        else:
            self._print_info("No backups found")
    
    def emergency_stop(self):
        """Emergency stop - kill all Python processes"""
        self._print_header("Emergency Stop")
        self._print_warning("⚠️  This will forcefully terminate ALL Python processes!")
        
        try:
            confirm = input(f"\n{Fore.RED}Type 'EMERGENCY' to confirm: ").strip()
            if confirm == 'EMERGENCY':
                exit_code, output, error = self._run_ssh_command("pkill -f python")
                if exit_code == 0:
                    self._print_success("All Python processes terminated")
                else:
                    self._print_error(f"Failed to kill processes: {error}")
            else:
                self._print_info("Operation cancelled")
        except KeyboardInterrupt:
            print(f"\n{Fore.BLUE}ℹ️  Operation cancelled")
    
    def interactive_menu(self):
        """Interactive menu system"""
        while True:
            self._print_header("QuranBot VPS Manager", 70)
            
            print(f"{Fore.GREEN}🤖 Bot Control:")
            print(f"  {Fore.WHITE}1. {Fore.GREEN}🚀 Start Bot")
            print(f"  {Fore.WHITE}2. {Fore.RED}🛑 Stop Bot")
            print(f"  {Fore.WHITE}3. {Fore.BLUE}🔄 Restart Bot")
            print(f"  {Fore.WHITE}4. {Fore.CYAN}📊 Bot Status")
            
            print(f"\n{Fore.BLUE}📋 Log Management:")
            print(f"  {Fore.WHITE}5. {Fore.YELLOW}🔄 Stream Logs")
            print(f"  {Fore.WHITE}6. {Fore.GREEN}📥 Download Today's Logs")
            print(f"  {Fore.WHITE}7. {Fore.MAGENTA}📅 Download Logs by Date")
            
            print(f"\n{Fore.MAGENTA}🛠️  System & Maintenance:")
            print(f"  {Fore.WHITE}8. {Fore.CYAN}🖥️  System Info")
            print(f"  {Fore.WHITE}9. {Fore.GREEN}💾 Create Backup")
            print(f"  {Fore.WHITE}10. {Fore.BLUE}📦 List Backups")
            print(f"  {Fore.WHITE}11. {Fore.YELLOW}🧪 Test Connection")
            print(f"  {Fore.WHITE}12. {Fore.RED}💀 Emergency Stop")
            
            print(f"\n  {Fore.WHITE}0. {Fore.RED}❌ Exit")
            
            print(f"\n{Fore.CYAN}{'='*70}")
            print(f"{Fore.YELLOW}VPS: {self.config['vps']['host']} | Service: {self.config['bot']['service_name']}")
            
            try:
                choice = input(f"\n{Fore.WHITE}Enter choice (0-12): ").strip()
                
                if choice == '1':
                    self.start_bot()
                elif choice == '2':
                    self.stop_bot()
                elif choice == '3':
                    self.restart_bot()
                elif choice == '4':
                    self.show_status()
                elif choice == '5':
                    self.stream_logs()
                elif choice == '6':
                    self.download_logs()
                elif choice == '7':
                    date = input(f"{Fore.CYAN}Enter date (YYYY-MM-DD): ").strip()
                    if date:
                        self.download_logs(date)
                elif choice == '8':
                    self.system_info()
                elif choice == '9':
                    name = input(f"{Fore.CYAN}Backup name (optional): ").strip()
                    self.create_backup(name if name else None)
                elif choice == '10':
                    self.list_backups()
                elif choice == '11':
                    self.test_connection()
                elif choice == '12':
                    self.emergency_stop()
                elif choice == '0':
                    print(f"\n{Fore.GREEN}👋 Goodbye!")
                    break
                else:
                    self._print_error("Invalid choice")
                
                if choice != '0' and choice in ['1', '2', '3', '4', '8', '9', '10', '11', '12']:
                    input(f"\n{Fore.BLUE}Press Enter to continue...")
                    
            except KeyboardInterrupt:
                print(f"\n\n{Fore.GREEN}👋 Goodbye!")
                break
            except Exception as e:
                self._print_error(f"Error: {e}")
                input(f"\n{Fore.BLUE}Press Enter to continue...")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="QuranBot Advanced VPS Manager")
    parser.add_argument("action", nargs='?', choices=[
        'status', 'start', 'stop', 'restart', 'logs', 'stream', 
        'backup', 'list-backups', 'system', 'test', 'emergency'
    ], help="Action to perform")
    parser.add_argument('--date', help='Date for log download (YYYY-MM-DD)')
    parser.add_argument('--name', help='Name for backup')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    try:
        manager = VPSManager()
        manager.verbose = args.verbose
        
        if args.action:
            if args.action == 'status':
                manager.show_status()
            elif args.action == 'start':
                manager.start_bot()
            elif args.action == 'stop':
                manager.stop_bot()
            elif args.action == 'restart':
                manager.restart_bot()
            elif args.action == 'logs':
                manager.download_logs(args.date)
            elif args.action == 'stream':
                manager.stream_logs()
            elif args.action == 'backup':
                manager.create_backup(args.name)
            elif args.action == 'list-backups':
                manager.list_backups()
            elif args.action == 'system':
                manager.system_info()
            elif args.action == 'test':
                manager.test_connection()
            elif args.action == 'emergency':
                manager.emergency_stop()
        else:
            # Interactive mode
            manager.interactive_menu()
            
    except KeyboardInterrupt:
        print(f"\n{Fore.GREEN}👋 Goodbye!")
    except Exception as e:
        print(f"{Fore.RED}❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 