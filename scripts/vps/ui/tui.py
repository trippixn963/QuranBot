"""
Terminal User Interface for QuranBot VPS Management
"""

import os
import sys
import time
from typing import Dict, Any, Optional
from ..core import VPSManager, LogManager, BackupManager

class TUI:
    """Terminal User Interface for VPS Management"""
    
    def __init__(self):
        """Initialize TUI"""
        self.vps = VPSManager()
        self.log_mgr = LogManager(self.vps)
        self.backup_mgr = BackupManager(self.vps)
    
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self):
        """Print TUI header"""
        self.clear_screen()
        print("="*60)
        print("           QuranBot VPS Management")
        print("="*60)
        print()
    
    def print_menu(self):
        """Print main menu"""
        print("🤖 Bot Control:")
        print("  1. Start Bot")
        print("  2. Stop Bot")
        print("  3. Restart Bot")
        print("  4. Show Status")
        print()
        print("📋 Log Management:")
        print("  5. View Logs")
        print("  6. Download Logs")
        print("  7. Analyze Logs")
        print("  8. Clean Up Logs")
        print()
        print("💾 Backup Management:")
        print("  9. Create Backup")
        print("  10. List Backups")
        print("  11. Restore Backup")
        print("  12. Download Backup")
        print("  13. Clean Up Backups")
        print()
        print("0. Exit")
        print()
    
    def get_choice(self) -> str:
        """Get user menu choice"""
        return input("Enter choice (0-13): ").strip()
    
    def wait_key(self):
        """Wait for user to press a key"""
        input("\nPress Enter to continue...")
    
    def handle_bot_control(self, choice: str):
        """Handle bot control options"""
        if choice == '1':
            self.vps.start_bot()
        elif choice == '2':
            self.vps.stop_bot()
        elif choice == '3':
            self.vps.restart_bot()
        elif choice == '4':
            status = self.vps.get_status()
            print("\n📊 Bot Status:")
            print(f"Running: {'✅' if status['running'] else '❌'}")
            if status['running']:
                print(f"CPU Usage: {status.get('cpu_usage', 'N/A')}%")
                print(f"Memory Usage: {status.get('memory_usage', 'N/A')}%")
                if status.get('errors'):
                    print("\nRecent Errors:")
                    for error in status['errors'][-3:]:
                        print(f"  ❌ {error}")
    
    def handle_log_management(self, choice: str):
        """Handle log management options"""
        if choice == '5':
            lines = input("Number of lines to show (default 50): ").strip()
            self.vps.stream_logs(int(lines) if lines else 50)
        
        elif choice == '6':
            date = input("Enter date (YYYY-MM-DD) or press Enter for today: ").strip()
            self.log_mgr.download_logs(date if date else None)
        
        elif choice == '7':
            date = input("Enter date (YYYY-MM-DD) or press Enter for today: ").strip()
            lines = input("Number of lines to analyze (default 1000): ").strip()
            
            analysis = self.log_mgr.analyze_logs(
                date if date else None,
                int(lines) if lines else 1000
            )
            report_file = self.log_mgr.generate_report(analysis)
            print(f"\n📋 Analysis report saved to: {report_file}")
        
        elif choice == '8':
            days = input("Delete logs older than days (default 30): ").strip()
            confirm = input("⚠️ Are you sure? (y/N): ").strip().lower()
            if confirm == 'y':
                self.log_mgr.cleanup_old_logs(int(days) if days else 30)
    
    def handle_backup_management(self, choice: str):
        """Handle backup management options"""
        if choice == '9':
            name = input("Backup name (press Enter for auto-generated): ").strip()
            include_logs = input("Include logs? (y/N): ").strip().lower() == 'y'
            self.backup_mgr.create_backup(name if name else None, include_logs)
        
        elif choice == '10':
            self.backup_mgr.list_backups()
        
        elif choice == '11':
            self.backup_mgr.list_backups()
            name = input("\nEnter backup name to restore: ").strip()
            if name:
                confirm = input("⚠️ This will STOP the bot and REPLACE current data. Continue? (y/N): ").strip().lower()
                if confirm == 'y':
                    self.backup_mgr.restore_backup(name)
        
        elif choice == '12':
            self.backup_mgr.list_backups()
            name = input("\nEnter backup name to download: ").strip()
            if name:
                self.backup_mgr.download_backup(name)
        
        elif choice == '13':
            days = input("Delete backups older than days (default 30): ").strip()
            confirm = input("⚠️ Are you sure? (y/N): ").strip().lower()
            if confirm == 'y':
                self.backup_mgr.cleanup_old_backups(int(days) if days else 30)
    
    def run(self):
        """Run the TUI"""
        try:
            while True:
                self.print_header()
                self.print_menu()
                
                choice = self.get_choice()
                print()
                
                if choice == '0':
                    print("👋 Goodbye!")
                    break
                
                elif choice in ['1', '2', '3', '4']:
                    self.handle_bot_control(choice)
                
                elif choice in ['5', '6', '7', '8']:
                    self.handle_log_management(choice)
                
                elif choice in ['9', '10', '11', '12', '13']:
                    self.handle_backup_management(choice)
                
                else:
                    print("❌ Invalid choice")
                
                self.wait_key()
        
        except KeyboardInterrupt:
            print("\n👋 Operation cancelled by user")
        except Exception as e:
            print(f"\n❌ Error: {e}")

def main():
    """Main entry point"""
    tui = TUI()
    tui.run()

if __name__ == '__main__':
    main() 