#!/usr/bin/env python3
"""
QuranBot Enhanced VPS Manager
Modern Python-based VPS management system
"""

import os
import sys
import json
import time
import datetime
import subprocess
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import colorama
from colorama import Fore, Style, init

# Initialize colorama for Windows
init(autoreset=True)

class VPSManager:
    def __init__(self):
        self.config = {
            "vps": {
                "host": "159.89.90.90",
                "user": "root",
                "ssh_key": "C:/Users/hanna/.ssh/id_rsa"
            },
            "bot": {
                "service_name": "quranbot",
                "log_path": "/opt/quranbot/logs"
            }
        }
    
    def ssh_cmd(self, command):
        """Execute SSH command"""
        cmd = [
            'ssh', '-i', self.config['vps']['ssh_key'],
            f"{self.config['vps']['user']}@{self.config['vps']['host']}",
            command
        ]
        return subprocess.run(cmd, capture_output=True, text=True)
    
    def start_bot(self):
        """Start the bot"""
        print("🚀 Starting QuranBot...")
        result = self.ssh_cmd(f"systemctl start {self.config['bot']['service_name']}")
        if result.returncode == 0:
            print("✅ Bot started successfully!")
        else:
            print(f"❌ Failed to start bot: {result.stderr}")
    
    def stop_bot(self):
        """Stop the bot"""
        print("🛑 Stopping QuranBot...")
        result = self.ssh_cmd(f"systemctl stop {self.config['bot']['service_name']}")
        if result.returncode == 0:
            print("✅ Bot stopped successfully!")
        else:
            print(f"❌ Failed to stop bot: {result.stderr}")
    
    def restart_bot(self):
        """Restart the bot"""
        print("🔄 Restarting QuranBot...")
        result = self.ssh_cmd(f"systemctl restart {self.config['bot']['service_name']}")
        if result.returncode == 0:
            print("✅ Bot restarted successfully!")
        else:
            print(f"❌ Failed to restart bot: {result.stderr}")
    
    def bot_status(self):
        """Get bot status"""
        print("📊 Checking QuranBot status...")
        result = self.ssh_cmd(f"systemctl status {self.config['bot']['service_name']} --no-pager")
        print(result.stdout)
    
    def stream_logs(self):
        """Stream logs in real-time"""
        print("📡 Streaming logs (Press Ctrl+C to stop)...")
        today = time.strftime("%Y-%m-%d")
        cmd = [
            'ssh', '-i', self.config['vps']['ssh_key'],
            f"{self.config['vps']['user']}@{self.config['vps']['host']}",
            f"tail -f {self.config['bot']['log_path']}/{today}.log"
        ]
        subprocess.run(cmd)
    
    def download_logs(self):
        """Download today's logs"""
        print("📥 Downloading today's logs...")
        today = time.strftime("%Y-%m-%d")
        local_dir = Path("logs/vps")
        local_dir.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            'scp', '-i', self.config['vps']['ssh_key'],
            f"{self.config['vps']['user']}@{self.config['vps']['host']}:{self.config['bot']['log_path']}/{today}.log",
            f"logs/vps/quranbot_{today}.log"
        ]
        
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode == 0:
            print(f"✅ Logs downloaded to logs/vps/quranbot_{today}.log")
        else:
            print("❌ Failed to download logs")
    
    def menu(self):
        """Interactive menu"""
        while True:
            print("\n" + "="*50)
            print("     QuranBot VPS Manager")
            print("="*50)
            print("1. 🚀 Start Bot")
            print("2. 🛑 Stop Bot")
            print("3. 🔄 Restart Bot")
            print("4. 📊 Status")
            print("5. 📡 Stream Logs")
            print("6. 📥 Download Logs")
            print("0. ❌ Exit")
            print("="*50)
            
            choice = input("Enter choice: ").strip()
            
            if choice == '1':
                self.start_bot()
            elif choice == '2':
                self.stop_bot()
            elif choice == '3':
                self.restart_bot()
            elif choice == '4':
                self.bot_status()
            elif choice == '5':
                self.stream_logs()
            elif choice == '6':
                self.download_logs()
            elif choice == '0':
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice")
            
            if choice != '0':
                input("\nPress Enter to continue...")

if __name__ == "__main__":
    manager = VPSManager()
    if len(sys.argv) > 1:
        action = sys.argv[1]
        if action == 'start':
            manager.start_bot()
        elif action == 'stop':
            manager.stop_bot()
        elif action == 'restart':
            manager.restart_bot()
        elif action == 'status':
            manager.bot_status()
        elif action == 'logs':
            manager.download_logs()
        elif action == 'stream':
            manager.stream_logs()
    else:
        manager.menu() 