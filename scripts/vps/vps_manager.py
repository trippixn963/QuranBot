#!/usr/bin/env python3
"""
QuranBot VPS Manager
Handles all VPS management actions via SSH.
"""

import argparse
import json
import os
import sys
import time
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import paramiko
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VPSManager:
    def __init__(self):
        self.config = self.load_config()
        self.ssh_client = None
        
    def load_config(self):
        """Load VPS configuration from JSON file."""
        config_path = Path(__file__).parent / "vps_config.json"
        if not config_path.exists():
            print("❌ VPS config file not found!")
            print(f"Please copy vps_config.json.template to vps_config.json and fill in your VPS details.")
            print(f"Expected location: {config_path}")
            sys.exit(1)
            
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in config file: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            sys.exit(1)
    
    def connect_ssh(self):
        """Establish SSH connection to VPS."""
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Try key-based authentication first, then password
            try:
                if self.config.get('vps_key_path') and os.path.exists(self.config['vps_key_path']):
                    self.ssh_client.connect(
                        hostname=self.config['vps_host'],
                        port=self.config['vps_port'],
                        username=self.config['vps_username'],
                        key_filename=self.config['vps_key_path'],
                        timeout=self.config['ssh_timeout']
                    )
                else:
                    self.ssh_client.connect(
                        hostname=self.config['vps_host'],
                        port=self.config['vps_port'],
                        username=self.config['vps_username'],
                        password=self.config['vps_password'],
                        timeout=self.config['ssh_timeout']
                    )
                return True
            except Exception as e:
                print(f"❌ SSH connection failed: {e}")
                return False
                
        except Exception as e:
            print(f"❌ SSH setup failed: {e}")
            return False
    
    def execute_command(self, command, timeout=None):
        """Execute command on VPS and return result."""
        if not self.ssh_client:
            if not self.connect_ssh():
                return None, None, False
                
        try:
            timeout = timeout or self.config['command_timeout']
            if self.ssh_client:  # Type check for linter
                stdin, stdout, stderr = self.ssh_client.exec_command(command, timeout=timeout)
                
                output = stdout.read().decode('utf-8').strip()
                error = stderr.read().decode('utf-8').strip()
                exit_code = stdout.channel.recv_exit_status()
                
                return output, error, exit_code == 0
            else:
                return None, None, False
            
        except Exception as e:
            print(f"❌ Command execution failed: {e}")
            return None, None, False
    
    def disconnect(self):
        """Close SSH connection."""
        if self.ssh_client:
            self.ssh_client.close()
            self.ssh_client = None
    
    def check_connection(self):
        """Test SSH connection to VPS."""
        print("🔍 Testing SSH connection to VPS...")
        
        if self.connect_ssh():
            print("✅ SSH connection successful!")
            
            # Test basic command execution
            output, error, success = self.execute_command("echo 'Connection test successful'")
            if success:
                print("✅ Command execution test passed!")
            else:
                print("❌ Command execution test failed!")
                
            self.disconnect()
            return True
        else:
            print("❌ SSH connection failed!")
            return False
    
    def get_bot_status(self):
        """Check if bot is running and get uptime."""
        print("🔍 Checking bot status...")
        
        if not self.connect_ssh():
            return False
            
        try:
            # Check if bot process is running
            output, error, success = self.execute_command(
                "ps aux | grep 'python3.*run.py' | grep -v grep"
            )
            
            if output:
                print("✅ Bot is running!")
                print(f"📊 Process info:\n{output}")
                
                # Get uptime
                uptime_output, _, _ = self.execute_command("uptime")
                if uptime_output:
                    print(f"🕒 System uptime: {uptime_output}")
                    
                # Get bot directory info
                dir_output, _, _ = self.execute_command(f"ls -la {self.config['bot_directory']}")
                if dir_output:
                    print(f"📁 Bot directory contents:\n{dir_output}")
            else:
                print("❌ Bot is not running!")
                
        finally:
            self.disconnect()
    
    def start_bot(self):
        """Start the QuranBot on VPS."""
        print("🚀 Starting QuranBot...")
        
        if not self.connect_ssh():
            return False
            
        try:
            # Change to bot directory and start
            command = f"cd {self.config['bot_directory']} && nohup python3 run.py > logs/bot.log 2>&1 &"
            output, error, success = self.execute_command(command)
            
            if success:
                print("✅ Bot start command executed!")
                time.sleep(2)  # Wait a moment
                self.get_bot_status()  # Check if it's actually running
            else:
                print(f"❌ Failed to start bot: {error}")
                
        finally:
            self.disconnect()
    
    def stop_bot(self):
        """Stop the QuranBot on VPS."""
        print("🛑 Stopping QuranBot...")
        
        if not self.connect_ssh():
            return False
            
        try:
            # Find and kill bot processes
            command = "pkill -f 'python3.*run.py'"
            output, error, success = self.execute_command(command)
            
            if success:
                print("✅ Bot stop command executed!")
                time.sleep(1)
                self.get_bot_status()  # Verify it's stopped
            else:
                print(f"❌ Failed to stop bot: {error}")
                
        finally:
            self.disconnect()
    
    def restart_bot(self):
        """Stop and restart the bot."""
        print("🔄 Restarting QuranBot...")
        self.stop_bot()
        time.sleep(2)
        self.start_bot()
    
    def deploy_bot(self):
        """Pull latest code and restart, NEVER touching the data directory."""
        print("🚀 Deploying latest bot code...")
        print("🌲 [SAFE] The data directory will NEVER be touched, overwritten, or deleted during deploy.")
        
        if not self.connect_ssh():
            return False
            
        try:
            # Stop bot first
            self.execute_command("pkill -f 'python3.*run.py'")
            time.sleep(2)
            
            # Only pull latest code, do not touch data directory
            command = f"cd {self.config['bot_directory']} && git pull"
            output, error, success = self.execute_command(command)
            
            if success:
                print("✅ Code updated successfully!")
                print(f"📝 Git output:\n{output}")
                print("🌲 [SAFE] The data directory was NOT modified.")
                
                # Install any new dependencies
                install_cmd = f"cd {self.config['bot_directory']} && pip install -r requirements.txt"
                install_output, install_error, install_success = self.execute_command(install_cmd)
                
                if install_success:
                    print("✅ Dependencies updated!")
                else:
                    print(f"⚠️ Dependency update had issues: {install_error}")
                
                # Start bot
                self.start_bot()
            else:
                print(f"❌ Failed to update code: {error}")
                
        finally:
            self.disconnect()
    
    def view_logs(self):
        """Show recent bot log entries."""
        print("📋 Viewing recent bot logs...")
        
        if not self.connect_ssh():
            return False
            
        try:
            # Get recent log entries
            command = f"tail -n 50 {self.config['logs_directory']}/bot.log"
            output, error, success = self.execute_command(command)
            
            if success and output:
                print("📋 Recent log entries:")
                print("=" * 50)
                print(output)
                print("=" * 50)
            else:
                print("❌ No logs found or error occurred!")
                
        finally:
            self.disconnect()
    
    def search_logs(self):
        """Search logs for specific terms."""
        print("🔍 Searching logs...")
        
        search_term = input("Enter search term: ").strip()
        if not search_term:
            print("❌ No search term provided!")
            return
            
        if not self.connect_ssh():
            return False
            
        try:
            # Search logs for the term
            command = f"grep -i '{search_term}' {self.config['logs_directory']}/*.log | tail -n 20"
            output, error, success = self.execute_command(command)
            
            if success and output:
                print(f"🔍 Search results for '{search_term}':")
                print("=" * 50)
                print(output)
                print("=" * 50)
            else:
                print(f"❌ No matches found for '{search_term}'!")
                
        finally:
            self.disconnect()
    
    def download_logs(self):
        """Download all log files to local logs folder."""
        print("📥 Downloading logs from VPS...")
        
        local_logs_dir = Path(self.config['local_logs_dir'])
        local_logs_dir.mkdir(exist_ok=True)
        
        if not self.connect_ssh():
            return False
            
        try:
            # Create SFTP session
            if self.ssh_client:  # Type check for linter
                sftp = self.ssh_client.open_sftp()
                
                # List log files on VPS
                try:
                    log_files = sftp.listdir(self.config['logs_directory'])
                    log_files = [f for f in log_files if f.endswith('.log')]
                    
                    if not log_files:
                        print("❌ No log files found on VPS!")
                        return
                        
                    print(f"📁 Found {len(log_files)} log files")
                    
                    # Download each log file
                    for log_file in log_files:
                        remote_path = f"{self.config['logs_directory']}/{log_file}"
                        local_path = local_logs_dir / log_file
                        
                        print(f"📥 Downloading {log_file}...")
                        sftp.get(remote_path, str(local_path))
                        print(f"✅ Downloaded {log_file}")
                        
                    print(f"✅ All logs downloaded to {local_logs_dir}")
                    
                except Exception as e:
                    print(f"❌ Error downloading logs: {e}")
                finally:
                    sftp.close()
            else:
                print("❌ SSH client not available!")
                
        finally:
            self.disconnect()
    
    def clear_old_logs(self):
        """Remove log files older than 7 days."""
        print("🧹 Clearing old logs (older than 7 days)...")
        
        if not self.connect_ssh():
            return False
            
        try:
            # Find and remove old log files
            command = f"find {self.config['logs_directory']} -name '*.log' -mtime +7 -delete"
            output, error, success = self.execute_command(command)
            
            if success:
                print("✅ Old logs cleared successfully!")
                
                # Show remaining log files
                list_cmd = f"ls -la {self.config['logs_directory']}/*.log"
                list_output, _, _ = self.execute_command(list_cmd)
                if list_output:
                    print("📁 Remaining log files:")
                    print(list_output)
            else:
                print(f"❌ Failed to clear old logs: {error}")
                
        finally:
            self.disconnect()
    
    def create_backup(self):
        """Create timestamped backup of bot."""
        print("💾 Creating backup...")
        
        if not self.connect_ssh():
            return False
            
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"QuranBot_Backup_{timestamp}.tar.gz"
            backup_path = f"{self.config['backup_directory']}/{backup_name}"
            
            # Create backup
            command = f"cd {self.config['bot_directory']} && tar -czf {backup_path} --exclude=audio --exclude=logs --exclude=backups ."
            output, error, success = self.execute_command(command)
            
            if success:
                print(f"✅ Backup created: {backup_name}")
                
                # Get backup size
                size_cmd = f"ls -lh {backup_path}"
                size_output, _, _ = self.execute_command(size_cmd)
                if size_output:
                    print(f"📊 Backup size: {size_output}")
            else:
                print(f"❌ Failed to create backup: {error}")
                
        finally:
            self.disconnect()
    
    def list_backups(self):
        """Show all available backup files."""
        print("📋 Listing available backups...")
        
        if not self.connect_ssh():
            return False
            
        try:
            # List backup files
            command = f"ls -lah {self.config['backup_directory']}/*.tar.gz"
            output, error, success = self.execute_command(command)
            
            if success and output:
                print("📁 Available backups:")
                print("=" * 50)
                print(output)
                print("=" * 50)
            else:
                print("❌ No backups found!")
                
        finally:
            self.disconnect()
    
    def restore_backup(self):
        """Restore bot from backup file."""
        print("🔄 Restoring from backup...")
        
        if not self.connect_ssh():
            return False
            
        try:
            # List available backups
            list_cmd = f"ls {self.config['backup_directory']}/*.tar.gz"
            list_output, _, _ = self.execute_command(list_cmd)
            
            if not list_output:
                print("❌ No backups found!")
                return
                
            print("📁 Available backups:")
            backups = list_output.strip().split('\n')
            for i, backup in enumerate(backups, 1):
                print(f"{i}. {backup.split('/')[-1]}")
            
            # Get user choice
            try:
                choice = int(input("Enter backup number to restore: ")) - 1
                if 0 <= choice < len(backups):
                    selected_backup = backups[choice]
                    print(f"🔄 Restoring from: {selected_backup.split('/')[-1]}")
                    
                    # Stop bot first
                    self.execute_command("pkill -f 'python.*run.py'")
                    time.sleep(2)
                    
                    # Restore backup
                    restore_cmd = f"cd {self.config['bot_directory']} && tar -xzf {selected_backup}"
                    output, error, success = self.execute_command(restore_cmd)
                    
                    if success:
                        print("✅ Backup restored successfully!")
                        self.start_bot()
                    else:
                        print(f"❌ Failed to restore backup: {error}")
                else:
                    print("❌ Invalid choice!")
            except ValueError:
                print("❌ Invalid input!")
                
        finally:
            self.disconnect()
    
    def cleanup_old_backups(self):
        """Remove backups older than 7 days."""
        print("🧹 Cleaning up old backups (older than 7 days)...")
        
        if not self.connect_ssh():
            return False
            
        try:
            # Find and remove old backups
            command = f"find {self.config['backup_directory']} -name '*.tar.gz' -mtime +7 -delete"
            output, error, success = self.execute_command(command)
            
            if success:
                print("✅ Old backups cleaned up!")
                
                # Show remaining backups
                self.list_backups()
            else:
                print(f"❌ Failed to cleanup old backups: {error}")
                
        finally:
            self.disconnect()
    
    def setup_environment(self):
        """Initial bot setup (first time only)."""
        print("🔧 Setting up bot environment...")
        
        if not self.connect_ssh():
            return False
            
        try:
            print("📦 Installing system dependencies...")
            
            # Update system packages
            update_cmd = "sudo apt update && sudo apt upgrade -y"
            output, error, success = self.execute_command(update_cmd)
            
            if success:
                print("✅ System packages updated!")
                
                # Install Python and pip
                python_cmd = "sudo apt install -y python3 python3-pip python3-venv"
                output, error, success = self.execute_command(python_cmd)
                
                if success:
                    print("✅ Python environment installed!")
                    
                    # Install bot dependencies using system packages
                    print("📦 Installing Python dependencies...")
                    
                    # Install required packages via apt
                    packages = ["python3-psutil", "python3-discord", "python3-dotenv", "python3-pynacl", "python3-pytz"]
                    for package in packages:
                        install_cmd = f"sudo apt install -y {package}"
                        output, error, success = self.execute_command(install_cmd)
                        if success:
                            print(f"✅ Installed {package}")
                        else:
                            print(f"⚠️ Failed to install {package}: {error}")
                    
                    # Create necessary directories
                    dirs_cmd = f"cd {self.config['bot_directory']} && mkdir -p logs backups audio"
                    self.execute_command(dirs_cmd)
                    print("✅ Directories created!")
                    
                    print("✅ Environment setup complete!")
                else:
                    print(f"❌ Failed to install Python: {error}")
            else:
                print(f"❌ Failed to update system: {error}")
                
        finally:
            self.disconnect()
    
    def monitor_bot(self):
        """Continuous monitoring with alerts."""
        print("📊 Starting bot monitoring (Ctrl+C to stop)...")
        
        if not self.connect_ssh():
            return False
            
        try:
            while True:
                # Check bot status
                output, error, success = self.execute_command(
                    "ps aux | grep 'python3.*run.py' | grep -v grep"
                )
                
                if output:
                    print(f"✅ Bot running - {datetime.now().strftime('%H:%M:%S')}")
                else:
                    print(f"❌ Bot stopped - {datetime.now().strftime('%H:%M:%S')}")
                    
                time.sleep(30)  # Check every 30 seconds
                
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped.")
        finally:
            self.disconnect()
    
    def system_info(self):
        """Get CPU, memory, disk usage, uptime."""
        print("💻 Getting system information...")
        
        if not self.connect_ssh():
            return False
            
        try:
            # System uptime
            uptime_output, _, _ = self.execute_command("uptime")
            if uptime_output:
                print(f"🕒 Uptime: {uptime_output}")
            
            # CPU and memory usage
            top_output, _, _ = self.execute_command("top -bn1 | head -20")
            if top_output:
                print(f"💻 CPU/Memory:\n{top_output}")
            
            # Disk usage
            df_output, _, _ = self.execute_command("df -h")
            if df_output:
                print(f"💾 Disk usage:\n{df_output}")
            
            # Memory details
            mem_output, _, _ = self.execute_command("free -h")
            if mem_output:
                print(f"🧠 Memory details:\n{mem_output}")
                
        finally:
            self.disconnect()
    
    def check_disk_space(self):
        """Show disk space on VPS."""
        print("💾 Checking disk space...")
        
        if not self.connect_ssh():
            return False
            
        try:
            # Get disk usage
            command = "df -h"
            output, error, success = self.execute_command(command)
            
            if success and output:
                print("💾 Disk space usage:")
                print("=" * 50)
                print(output)
                print("=" * 50)
                
                # Check specific directories
                bot_dir_size, _, _ = self.execute_command(f"du -sh {self.config['bot_directory']}")
                if bot_dir_size:
                    print(f"📁 Bot directory size: {bot_dir_size}")
                    
            else:
                print("❌ Failed to get disk space info!")
                
        finally:
            self.disconnect()
    
    def check_network_status(self):
        """Test internet, DNS, open ports."""
        print("🌐 Checking network status...")
        
        if not self.connect_ssh():
            return False
            
        try:
            # Test internet connectivity
            ping_output, _, ping_success = self.execute_command("ping -c 3 8.8.8.8")
            if ping_success:
                print("✅ Internet connectivity: OK")
            else:
                print("❌ Internet connectivity: FAILED")
            
            # Test DNS resolution
            nslookup_output, _, dns_success = self.execute_command("nslookup google.com")
            if dns_success:
                print("✅ DNS resolution: OK")
            else:
                print("❌ DNS resolution: FAILED")
            
            # Check open ports
            netstat_output, _, _ = self.execute_command("netstat -tlnp | grep LISTEN")
            if netstat_output:
                print("🔌 Open ports:")
                print(netstat_output)
            
            # Network interfaces
            ifconfig_output, _, _ = self.execute_command("ip addr show")
            if ifconfig_output:
                print("🌐 Network interfaces:")
                print(ifconfig_output)
                
        finally:
            self.disconnect()
    
    def upload_audio(self):
        """Upload audio files to VPS."""
        print("📤 Uploading audio files to VPS...")
        
        local_audio_dir = Path(self.config['local_audio_dir'])
        if not local_audio_dir.exists():
            print("❌ Local audio directory not found!")
            return
            
        if not self.connect_ssh():
            return False
            
        try:
            # Create SFTP session
            if self.ssh_client:  # Type check for linter
                sftp = self.ssh_client.open_sftp()
                
                # List local audio files
                audio_files = list(local_audio_dir.glob("*.mp3"))
                
                if not audio_files:
                    print("❌ No audio files found in local directory!")
                    return
                    
                print(f"📁 Found {len(audio_files)} audio files")
                
                # Upload each file
                for audio_file in audio_files:
                    remote_path = f"{self.config['audio_directory']}/{audio_file.name}"
                    local_path = str(audio_file)
                    
                    print(f"📤 Uploading {audio_file.name}...")
                    try:
                        sftp.put(local_path, remote_path)
                        print(f"✅ Uploaded {audio_file.name}")
                    except Exception as e:
                        print(f"❌ Failed to upload {audio_file.name}: {e}")
                        
                print("✅ Audio upload complete!")
                
            else:
                print("❌ SSH client not available!")
                
        except Exception as e:
            print(f"❌ Error during upload: {e}")
        finally:
            if self.ssh_client and 'sftp' in locals():
                sftp.close()
            self.disconnect()
    
    def update_system(self):
        """Update system packages on VPS."""
        print("🔄 Updating system packages...")
        
        if not self.connect_ssh():
            return False
            
        try:
            # Update package lists
            update_cmd = "sudo apt update"
            output, error, success = self.execute_command(update_cmd)
            
            if success:
                print("✅ Package lists updated!")
                
                # Upgrade packages
                upgrade_cmd = "sudo apt upgrade -y"
                output, error, success = self.execute_command(upgrade_cmd)
                
                if success:
                    print("✅ System packages upgraded!")
                    
                    # Clean up
                    cleanup_cmd = "sudo apt autoremove -y && sudo apt autoclean"
                    self.execute_command(cleanup_cmd)
                    print("✅ System cleanup completed!")
                else:
                    print(f"❌ Failed to upgrade packages: {error}")
            else:
                print(f"❌ Failed to update package lists: {error}")
                
        finally:
            self.disconnect()
    
    def kill_all_python(self):
        """Force kill all Python processes."""
        print("💀 Force killing all Python processes...")
        
        if not self.connect_ssh():
            return False
            
        try:
            # Kill all Python processes
            command = "sudo pkill -9 python"
            output, error, success = self.execute_command(command)
            
            if success:
                print("✅ All Python processes killed!")
                
                # Verify no Python processes remain
                check_cmd = "ps aux | grep python | grep -v grep"
                check_output, _, _ = self.execute_command(check_cmd)
                
                if not check_output:
                    print("✅ No Python processes remaining!")
                else:
                    print("⚠️ Some Python processes may still be running:")
                    print(check_output)
            else:
                print(f"❌ Failed to kill Python processes: {error}")
                
        finally:
            self.disconnect()
    
    def download_data(self):
        """Download data directory from VPS for editing."""
        print("📥 Downloading data directory from VPS...")
        
        local_data_dir = Path("data_vps")
        local_data_dir.mkdir(exist_ok=True)
        
        if not self.connect_ssh():
            return False
            
        try:
            # Create SFTP session
            if self.ssh_client:  # Type check for linter
                sftp = self.ssh_client.open_sftp()
                
                # List data files on VPS
                try:
                    data_files = sftp.listdir(f"{self.config['bot_directory']}/data")
                    
                    if not data_files:
                        print("❌ No data files found on VPS!")
                        return
                        
                    print(f"📁 Found {len(data_files)} data files")
                    
                    # Download each data file
                    for data_file in data_files:
                        remote_path = f"{self.config['bot_directory']}/data/{data_file}"
                        local_path = local_data_dir / data_file
                        
                        print(f"📥 Downloading {data_file}...")
                        sftp.get(remote_path, str(local_path))
                        print(f"✅ Downloaded {data_file}")
                        
                    print(f"✅ All data files downloaded to {local_data_dir}")
                    print("📝 You can now edit the files in the 'data_vps' directory")
                    print("📤 Use 'Upload Data' option to send changes back to VPS")
                    
                except Exception as e:
                    print(f"❌ Error downloading data: {e}")
                finally:
                    sftp.close()
            else:
                print("❌ SSH client not available!")
                
        finally:
            self.disconnect()
    
    def upload_data(self):
        """Upload edited data directory back to VPS."""
        print("📤 Uploading data directory to VPS...")
        
        local_data_dir = Path("data_vps")
        if not local_data_dir.exists():
            print("❌ Local data_vps directory not found!")
            print("📥 Please download data first using 'Download Data' option")
            return
            
        if not self.connect_ssh():
            return False
            
        try:
            # Create SFTP session
            if self.ssh_client:  # Type check for linter
                sftp = self.ssh_client.open_sftp()
                
                # List local data files
                data_files = list(local_data_dir.glob("*"))
                
                if not data_files:
                    print("❌ No data files found in local data_vps directory!")
                    return
                    
                print(f"📁 Found {len(data_files)} data files to upload")
                
                # Upload each file
                for data_file in data_files:
                    remote_path = f"{self.config['bot_directory']}/data/{data_file.name}"
                    local_path = str(data_file)
                    
                    print(f"📤 Uploading {data_file.name}...")
                    try:
                        sftp.put(local_path, remote_path)
                        print(f"✅ Uploaded {data_file.name}")
                    except Exception as e:
                        print(f"❌ Failed to upload {data_file.name}: {e}")
                        
                print("✅ Data upload complete!")
                print("🔄 Consider restarting the bot to load new data")
                
            else:
                print("❌ SSH client not available!")
                
        except Exception as e:
            print(f"❌ Error during upload: {e}")
        finally:
            sftp.close()
            self.disconnect()
    
    def emergency_restart(self):
        """Force kill and restart everything."""
        print("🚨 Emergency restart initiated...")
        
        if not self.connect_ssh():
            return False
            
        try:
            # Kill all Python processes
            self.execute_command("sudo pkill -9 python")
            time.sleep(2)
            
            # Kill any remaining bot processes
            self.execute_command("pkill -f 'python3.*run.py'")
            time.sleep(2)
            
            # Clear any lock files
            self.execute_command(f"rm -f {self.config['bot_directory']}/*.lock")
            
            # Restart bot
            print("🔄 Restarting bot after emergency cleanup...")
            self.start_bot()
            
        finally:
            self.disconnect()

def main():
    parser = argparse.ArgumentParser(description='QuranBot VPS Manager')
    parser.add_argument('--check-connection', action='store_true', help='Test SSH connection to VPS')
    parser.add_argument('--get-bot-status', action='store_true', help='Check if bot is running and get uptime')
    parser.add_argument('--start-bot', action='store_true', help='Start the QuranBot on VPS')
    parser.add_argument('--stop-bot', action='store_true', help='Stop the QuranBot on VPS')
    parser.add_argument('--restart-bot', action='store_true', help='Stop and restart the bot')
    parser.add_argument('--deploy-bot', action='store_true', help='Pull latest code and restart')
    parser.add_argument('--view-logs', action='store_true', help='Show recent bot log entries')
    parser.add_argument('--search-logs', action='store_true', help='Search logs for specific terms')
    parser.add_argument('--download-logs', action='store_true', help='Download all log files to local logs folder')
    parser.add_argument('--clear-old-logs', action='store_true', help='Remove log files older than 7 days')
    parser.add_argument('--create-backup', action='store_true', help='Create timestamped backup of bot')
    parser.add_argument('--list-backups', action='store_true', help='Show all available backup files')
    parser.add_argument('--restore-backup', action='store_true', help='Restore bot from backup file')
    parser.add_argument('--cleanup-old-backups', action='store_true', help='Remove backups older than 7 days')
    parser.add_argument('--setup-environment', action='store_true', help='Initial bot setup (first time only)')
    parser.add_argument('--monitor-bot', action='store_true', help='Continuous monitoring with alerts')
    parser.add_argument('--system-info', action='store_true', help='CPU, memory, disk usage, uptime')
    parser.add_argument('--check-disk-space', action='store_true', help='Show disk space on VPS')
    parser.add_argument('--check-network-status', action='store_true', help='Test internet, DNS, open ports')
    parser.add_argument('--upload-audio', action='store_true', help='Upload audio files to VPS')
    parser.add_argument('--update-system', action='store_true', help='Update system packages on VPS')
    parser.add_argument('--kill-all-python', action='store_true', help='Force kill all Python processes')
    parser.add_argument('--download-data', action='store_true', help='Download data directory from VPS for editing')
    parser.add_argument('--upload-data', action='store_true', help='Upload edited data directory back to VPS')
    parser.add_argument('--emergency-restart', action='store_true', help='Force kill and restart everything')
    
    args = parser.parse_args()
    
    # Create VPS manager instance
    vps_manager = VPSManager()
    
    try:
        # Execute requested action
        if args.check_connection:
            vps_manager.check_connection()
        elif args.get_bot_status:
            vps_manager.get_bot_status()
        elif args.start_bot:
            vps_manager.start_bot()
        elif args.stop_bot:
            vps_manager.stop_bot()
        elif args.restart_bot:
            vps_manager.restart_bot()
        elif args.deploy_bot:
            vps_manager.deploy_bot()
        elif args.view_logs:
            vps_manager.view_logs()
        elif args.search_logs:
            vps_manager.search_logs()
        elif args.download_logs:
            vps_manager.download_logs()
        elif args.clear_old_logs:
            vps_manager.clear_old_logs()
        elif args.create_backup:
            vps_manager.create_backup()
        elif args.list_backups:
            vps_manager.list_backups()
        elif args.restore_backup:
            vps_manager.restore_backup()
        elif args.cleanup_old_backups:
            vps_manager.cleanup_old_backups()
        elif args.setup_environment:
            vps_manager.setup_environment()
        elif args.monitor_bot:
            vps_manager.monitor_bot()
        elif args.system_info:
            vps_manager.system_info()
        elif args.check_disk_space:
            vps_manager.check_disk_space()
        elif args.check_network_status:
            vps_manager.check_network_status()
        elif args.upload_audio:
            vps_manager.upload_audio()
        elif args.update_system:
            vps_manager.update_system()
        elif args.kill_all_python:
            vps_manager.kill_all_python()
        elif args.download_data:
            vps_manager.download_data()
        elif args.upload_data:
            vps_manager.upload_data()
        elif args.emergency_restart:
            vps_manager.emergency_restart()
        else:
            print("❌ No action specified. Use --help for available options.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled by user.")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
    finally:
        vps_manager.disconnect()

if __name__ == "__main__":
    main() 