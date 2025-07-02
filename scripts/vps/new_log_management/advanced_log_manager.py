#!/usr/bin/env python3
"""
Advanced Log Manager for QuranBot VPS
Comprehensive log analysis, monitoring, and management
"""

import os
import sys
import re
import json
import subprocess
import datetime
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Any

class AdvancedLogManager:
    def __init__(self):
        self.config = {
            "vps": {
                "host": "159.89.90.90",
                "user": "root",
                "ssh_key": "C:/Users/hanna/.ssh/id_rsa"
            },
            "bot": {
                "log_path": "/opt/quranbot/logs"
            },
            "local": {
                "log_dir": "logs/vps",
                "analysis_dir": "logs/analysis"
            }
        }
        
        # Create local directories
        Path(self.config['local']['log_dir']).mkdir(parents=True, exist_ok=True)
        Path(self.config['local']['analysis_dir']).mkdir(parents=True, exist_ok=True)
    
    def ssh_cmd(self, command: str) -> Tuple[int, str, str]:
        """Execute SSH command and return exit code, stdout, stderr"""
        cmd = [
            'ssh', '-i', self.config['vps']['ssh_key'],
            f"{self.config['vps']['user']}@{self.config['vps']['host']}",
            command
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return 1, "", "Command timed out"
        except Exception as e:
            return 1, "", f"Error: {e}"
    
    def list_available_logs(self) -> List[str]:
        """List all available log files on VPS"""
        print("📋 Listing available log files...")
        
        exit_code, output, error = self.ssh_cmd(f"ls -la {self.config['bot']['log_path']}/*.log 2>/dev/null")
        
        if exit_code == 0:
            log_files = []
            for line in output.split('\n'):
                if '.log' in line:
                    parts = line.split()
                    if len(parts) >= 9:
                        filename = parts[8].split('/')[-1]
                        size = parts[4]
                        date = f"{parts[5]} {parts[6]} {parts[7]}"
                        log_files.append({
                            'filename': filename,
                            'size': size,
                            'date': date,
                            'full_line': line
                        })
                        print(f"  📄 {filename:<20} {size:<10} {date}")
            return log_files
        else:
            print(f"❌ Failed to list logs: {error}")
            return []
    
    def download_log(self, date: str = None) -> str:
        """Download log file for specific date"""
        if date is None:
            date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        remote_file = f"{self.config['bot']['log_path']}/{date}.log"
        local_file = Path(self.config['local']['log_dir']) / f"quranbot_{date}.log"
        
        print(f"📥 Downloading log for {date}...")
        
        # Download using scp
        cmd = [
            'scp', '-i', self.config['vps']['ssh_key'],
            f"{self.config['vps']['user']}@{self.config['vps']['host']}:{remote_file}",
            str(local_file)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            size = local_file.stat().st_size
            print(f"✅ Downloaded to: {local_file} ({size:,} bytes)")
            return str(local_file)
        else:
            print(f"❌ Failed to download: {result.stderr}")
            return None
    
    def analyze_log_file(self, log_file: str) -> Dict[str, Any]:
        """Analyze a log file for patterns, errors, and statistics"""
        print(f"🔍 Analyzing log file: {log_file}")
        
        if not os.path.exists(log_file):
            print(f"❌ Log file not found: {log_file}")
            return {}
        
        analysis = {
            'file_info': {
                'filename': os.path.basename(log_file),
                'size': os.path.getsize(log_file),
                'lines': 0
            },
            'log_levels': Counter(),
            'components': Counter(),
            'operations': Counter(),
            'errors': [],
            'warnings': [],
            'timeline': [],
            'performance': [],
            'user_activity': [],
            'bot_events': []
        }
        
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                analysis['file_info']['lines'] = line_num
                
                # Extract timestamp
                timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                timestamp = timestamp_match.group(1) if timestamp_match else None
                
                # Extract log level
                level_match = re.search(r'\| (DEBUG|INFO|WARNING|ERROR|CRITICAL) \|', line)
                if level_match:
                    level = level_match.group(1)
                    analysis['log_levels'][level] += 1
                
                # Extract component
                component_match = re.search(r'\| ([^|]+) - ([^|]+) \|', line)
                if component_match:
                    component = component_match.group(1).strip()
                    operation = component_match.group(2).strip()
                    analysis['components'][component] += 1
                    analysis['operations'][operation] += 1
                
                # Collect errors and warnings
                if 'ERROR' in line:
                    analysis['errors'].append({
                        'line': line_num,
                        'timestamp': timestamp,
                        'content': line.strip()[:200]  # Truncate long lines
                    })
                elif 'WARNING' in line:
                    analysis['warnings'].append({
                        'line': line_num,
                        'timestamp': timestamp,
                        'content': line.strip()[:200]
                    })
                
                # Track performance logs
                if 'Performance:' in line:
                    analysis['performance'].append({
                        'line': line_num,
                        'timestamp': timestamp,
                        'content': line.strip()
                    })
                
                # Track user activity
                if '👤' in line or 'user_id' in line.lower():
                    analysis['user_activity'].append({
                        'line': line_num,
                        'timestamp': timestamp,
                        'content': line.strip()[:200]
                    })
                
                # Track bot events
                if any(keyword in line.lower() for keyword in ['bot', 'connect', 'disconnect', 'start', 'stop']):
                    analysis['bot_events'].append({
                        'line': line_num,
                        'timestamp': timestamp,
                        'content': line.strip()[:200]
                    })
        
        return analysis
    
    def generate_report(self, analysis: Dict[str, Any]) -> str:
        """Generate a comprehensive analysis report"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = Path(self.config['local']['analysis_dir']) / f"log_analysis_{timestamp}.txt"
        
        with open(report_file, 'w') as f:
            f.write("="*60 + "\n")
            f.write("QuranBot Log Analysis Report\n")
            f.write("="*60 + "\n")
            f.write(f"Generated: {datetime.datetime.now()}\n")
            f.write(f"Log File: {analysis['file_info']['filename']}\n\n")
            
            # File information
            f.write("📊 FILE INFORMATION\n")
            f.write("-" * 20 + "\n")
            f.write(f"Size: {analysis['file_info']['size']:,} bytes\n")
            f.write(f"Lines: {analysis['file_info']['lines']:,}\n\n")
            
            # Log levels summary
            f.write("📈 LOG LEVELS SUMMARY\n")
            f.write("-" * 20 + "\n")
            for level, count in analysis['log_levels'].most_common():
                f.write(f"{level}: {count:,}\n")
            f.write("\n")
            
            # Top components
            f.write("🔧 TOP COMPONENTS\n")
            f.write("-" * 20 + "\n")
            for component, count in analysis['components'].most_common(10):
                f.write(f"{component}: {count:,}\n")
            f.write("\n")
            
            # Top operations
            f.write("⚙️ TOP OPERATIONS\n")
            f.write("-" * 20 + "\n")
            for operation, count in analysis['operations'].most_common(10):
                f.write(f"{operation}: {count:,}\n")
            f.write("\n")
            
            # Errors
            if analysis['errors']:
                f.write("❌ ERRORS\n")
                f.write("-" * 20 + "\n")
                for error in analysis['errors'][-10:]:  # Last 10 errors
                    f.write(f"Line {error['line']}: {error['content']}\n\n")
            
            # Warnings
            if analysis['warnings']:
                f.write("⚠️ WARNINGS\n")
                f.write("-" * 20 + "\n")
                for warning in analysis['warnings'][-10:]:  # Last 10 warnings
                    f.write(f"Line {warning['line']}: {warning['content']}\n\n")
            
            # Performance insights
            if analysis['performance']:
                f.write("🚀 PERFORMANCE INSIGHTS\n")
                f.write("-" * 20 + "\n")
                for perf in analysis['performance'][-5:]:  # Last 5 performance logs
                    f.write(f"{perf['content']}\n")
                f.write("\n")
            
            # User activity summary
            f.write(f"👥 USER ACTIVITY: {len(analysis['user_activity'])} events\n\n")
            
            # Bot events summary
            f.write(f"🤖 BOT EVENTS: {len(analysis['bot_events'])} events\n\n")
        
        return str(report_file)
    
    def real_time_monitor(self, duration: int = 300):
        """Monitor logs in real-time with analysis"""
        print(f"📡 Starting real-time log monitoring for {duration} seconds...")
        print("Press Ctrl+C to stop early")
        
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        log_file = f"{self.config['bot']['log_path']}/{today}.log"
        
        # Use SSH to tail the log with analysis
        cmd = [
            'ssh', '-i', self.config['vps']['ssh_key'],
            f"{self.config['vps']['user']}@{self.config['vps']['host']}",
            f"timeout {duration} tail -f {log_file}"
        ]
        
        try:
            subprocess.run(cmd)
        except KeyboardInterrupt:
            print("\n📊 Monitoring stopped by user")
    
    def cleanup_old_logs(self, days: int = 30):
        """Clean up old log files"""
        print(f"🧹 Cleaning up logs older than {days} days...")
        
        cmd = f"find {self.config['bot']['log_path']} -name '*.log' -type f -mtime +{days} -exec ls -la {{}} +"
        exit_code, output, error = self.ssh_cmd(cmd)
        
        if exit_code == 0 and output:
            print("📋 Files to be deleted:")
            print(output)
            
            confirm = input("\n⚠️ Delete these files? (y/N): ").strip().lower()
            if confirm == 'y':
                delete_cmd = f"find {self.config['bot']['log_path']} -name '*.log' -type f -mtime +{days} -delete"
                exit_code, output, error = self.ssh_cmd(delete_cmd)
                if exit_code == 0:
                    print("✅ Old logs cleaned up successfully")
                else:
                    print(f"❌ Failed to clean up: {error}")
            else:
                print("ℹ️ Cleanup cancelled")
        else:
            print("ℹ️ No old logs found to clean up")
    
    def interactive_menu(self):
        """Interactive menu for log management"""
        while True:
            print("\n" + "="*50)
            print("  Advanced QuranBot Log Manager")
            print("="*50)
            print("1. 📋 List Available Logs")
            print("2. 📥 Download Log")
            print("3. 🔍 Analyze Log")
            print("4. 📊 Generate Report")
            print("5. 📡 Real-time Monitor")
            print("6. 🧹 Cleanup Old Logs")
            print("0. ❌ Exit")
            print("="*50)
            
            choice = input("Enter choice: ").strip()
            
            if choice == '1':
                self.list_available_logs()
            elif choice == '2':
                date = input("Enter date (YYYY-MM-DD) or press Enter for today: ").strip()
                if not date:
                    date = None
                self.download_log(date)
            elif choice == '3':
                date = input("Enter date (YYYY-MM-DD) or press Enter for today: ").strip()
                if not date:
                    date = datetime.datetime.now().strftime("%Y-%m-%d")
                
                log_file = self.download_log(date)
                if log_file:
                    analysis = self.analyze_log_file(log_file)
                    print(f"\n📊 Analysis Summary:")
                    print(f"  Lines: {analysis['file_info']['lines']:,}")
                    print(f"  Errors: {len(analysis['errors'])}")
                    print(f"  Warnings: {len(analysis['warnings'])}")
                    print(f"  Components: {len(analysis['components'])}")
            elif choice == '4':
                date = input("Enter date (YYYY-MM-DD) or press Enter for today: ").strip()
                if not date:
                    date = datetime.datetime.now().strftime("%Y-%m-%d")
                
                log_file = self.download_log(date)
                if log_file:
                    analysis = self.analyze_log_file(log_file)
                    report_file = self.generate_report(analysis)
                    print(f"📋 Report generated: {report_file}")
            elif choice == '5':
                duration = input("Monitor duration in seconds (default 300): ").strip()
                try:
                    duration = int(duration) if duration else 300
                    self.real_time_monitor(duration)
                except ValueError:
                    print("❌ Invalid duration")
            elif choice == '6':
                days = input("Delete logs older than how many days? (default 30): ").strip()
                try:
                    days = int(days) if days else 30
                    self.cleanup_old_logs(days)
                except ValueError:
                    print("❌ Invalid number of days")
            elif choice == '0':
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice")
            
            if choice != '0':
                input("\nPress Enter to continue...")

def main():
    """Main entry point"""
    try:
        manager = AdvancedLogManager()
        
        if len(sys.argv) > 1:
            action = sys.argv[1].lower()
            if action == 'list':
                manager.list_available_logs()
            elif action == 'download':
                date = sys.argv[2] if len(sys.argv) > 2 else None
                manager.download_log(date)
            elif action == 'analyze':
                date = sys.argv[2] if len(sys.argv) > 2 else datetime.datetime.now().strftime("%Y-%m-%d")
                log_file = manager.download_log(date)
                if log_file:
                    analysis = manager.analyze_log_file(log_file)
                    report_file = manager.generate_report(analysis)
                    print(f"Report: {report_file}")
            elif action == 'monitor':
                duration = int(sys.argv[2]) if len(sys.argv) > 2 else 300
                manager.real_time_monitor(duration)
            elif action == 'cleanup':
                days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
                manager.cleanup_old_logs(days)
            else:
                print(f"Unknown action: {action}")
        else:
            manager.interactive_menu()
            
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main() 