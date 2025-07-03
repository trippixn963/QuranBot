"""
Backup Management System for QuranBot VPS
"""

import os
import json
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

class BackupManager:
    """Handles backup creation and management"""
    
    def __init__(self, vps_manager):
        """Initialize with VPS manager instance"""
        self.vps = vps_manager
        self.config = vps_manager.config
    
    def create_backup(self, name: Optional[str] = None, include_logs: bool = False) -> bool:
        """Create a new backup"""
        if name is None:
            name = f"backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        print(f"💾 Creating backup: {name}")
        
        backup_path = self.config['bot']['backup_path']
        install_path = self.config['bot']['install_path']
        data_path = self.config['bot']['data_path']
        
        # Create backup directory
        code, out, err = self.vps._run_ssh_command(f"mkdir -p {backup_path}/{name}")
        if code != 0:
            print(f"❌ Failed to create backup directory: {err}")
            return False
        
        # Build backup command
        backup_items = [
            f"{data_path}/*",
            f"{install_path}/*.json",
            f"{install_path}/*.yml"
        ]
        
        if include_logs:
            backup_items.append(f"{self.config['bot']['log_path']}/*.log")
        
        # Copy files to backup directory
        for item in backup_items:
            code, out, err = self.vps._run_ssh_command(
                f"cp -r {item} {backup_path}/{name}/ 2>/dev/null || true"
            )
        
        # Create archive
        code, out, err = self.vps._run_ssh_command(
            f"cd {backup_path} && tar -czf {name}.tar.gz {name} && rm -rf {name}"
        )
        
        if code == 0:
            print("✅ Backup created successfully!")
            return True
        else:
            print(f"❌ Failed to create backup archive: {err}")
            return False
    
    def list_backups(self) -> List[Dict[str, str]]:
        """List all available backups"""
        print("📋 Available backups:")
        
        backup_path = self.config['bot']['backup_path']
        code, out, err = self.vps._run_ssh_command(f"ls -lh {backup_path}/*.tar.gz 2>/dev/null")
        
        backups = []
        if code == 0 and out:
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 9:
                    backup = {
                        'name': parts[-1].split('/')[-1],
                        'size': parts[4],
                        'date': f"{parts[5]} {parts[6]} {parts[7]}"
                    }
                    backups.append(backup)
                    print(f"  📦 {backup['name']:<30} {backup['size']:>8} {backup['date']}")
        
        if not backups:
            print("  No backups found")
        
        return backups
    
    def restore_backup(self, backup_name: str) -> bool:
        """Restore from a backup"""
        print(f"📥 Restoring from backup: {backup_name}")
        
        backup_path = self.config['bot']['backup_path']
        install_path = self.config['bot']['install_path']
        data_path = self.config['bot']['data_path']
        temp_dir = f"{backup_path}/temp_restore_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Stop the bot first
        print("⏹️ Stopping bot for restore...")
        self.vps._run_ssh_command(f"systemctl stop {self.config['bot']['service_name']}")
        
        # Create temp directory and extract backup
        commands = [
            f"mkdir -p {temp_dir}",
            f"cd {temp_dir} && tar -xzf {backup_path}/{backup_name}",
            f"rm -rf {data_path}/*",  # Clear existing data
            f"cp -r {temp_dir}/*/* {data_path}/",  # Restore data
            f"rm -rf {temp_dir}"  # Cleanup
        ]
        
        success = True
        for cmd in commands:
            code, out, err = self.vps._run_ssh_command(cmd)
            if code != 0:
                print(f"❌ Restore failed: {err}")
                success = False
                break
        
        # Start the bot back up
        print("🚀 Starting bot...")
        self.vps._run_ssh_command(f"systemctl start {self.config['bot']['service_name']}")
        
        if success:
            print("✅ Backup restored successfully!")
        return success
    
    def download_backup(self, backup_name: str) -> Optional[str]:
        """Download a backup file locally"""
        print(f"📥 Downloading backup: {backup_name}")
        
        backup_path = self.config['bot']['backup_path']
        local_dir = Path("backups/vps")
        local_dir.mkdir(parents=True, exist_ok=True)
        local_path = local_dir / backup_name
        
        cmd = [
            'scp',
            '-i', self.config['vps']['ssh_key'],
            f"{self.config['vps']['user']}@{self.config['vps']['host']}:{backup_path}/{backup_name}",
            str(local_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Backup downloaded to: {local_path}")
            return str(local_path)
        else:
            print(f"❌ Failed to download backup: {result.stderr}")
            return None
    
    def cleanup_old_backups(self, days: int = 30) -> bool:
        """Remove backups older than specified days"""
        print(f"🧹 Cleaning up backups older than {days} days...")
        
        backup_path = self.config['bot']['backup_path']
        cmd = f"find {backup_path} -name '*.tar.gz' -type f -mtime +{days} -delete"
        
        code, out, err = self.vps._run_ssh_command(cmd)
        if code == 0:
            print("✅ Old backups cleaned up successfully")
            return True
        else:
            print(f"❌ Failed to clean up backups: {err}")
            return False
    
    def get_backup_stats(self) -> Dict[str, Any]:
        """Get statistics about backups"""
        backup_path = self.config['bot']['backup_path']
        cmd = f"du -sh {backup_path} && ls -lh {backup_path}/*.tar.gz 2>/dev/null"
        
        code, out, err = self.vps._run_ssh_command(cmd)
        if code != 0:
            return {}
        
        stats = {
            'total_size': '0B',
            'backup_count': 0,
            'newest_backup': None,
            'oldest_backup': None,
            'backups': []
        }
        
        lines = out.splitlines()
        if lines:
            # First line is total size
            stats['total_size'] = lines[0].split()[0]
            
            # Rest are backup files
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 9:
                    backup = {
                        'name': parts[-1].split('/')[-1],
                        'size': parts[4],
                        'date': f"{parts[5]} {parts[6]} {parts[7]}"
                    }
                    stats['backups'].append(backup)
                    stats['backup_count'] += 1
                    
                    # Track newest/oldest
                    if not stats['newest_backup'] or parts[5:8] > stats['newest_backup']['date'].split():
                        stats['newest_backup'] = backup
                    if not stats['oldest_backup'] or parts[5:8] < stats['oldest_backup']['date'].split():
                        stats['oldest_backup'] = backup
        
        return stats 