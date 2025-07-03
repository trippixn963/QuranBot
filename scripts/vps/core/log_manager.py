"""
Log Management System for QuranBot VPS
"""

import os
import re
import json
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import Counter

class LogManager:
    """Handles log management and analysis"""
    
    def __init__(self, vps_manager):
        """Initialize with VPS manager instance"""
        self.vps = vps_manager
        self.config = vps_manager.config
    
    def analyze_logs(self, date: Optional[str] = None, lines: int = 1000) -> Dict[str, Any]:
        """Analyze logs for patterns and statistics"""
        if date is None:
            date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        print(f"🔍 Analyzing logs for {date}...")
        
        log_path = self.config['bot']['log_path']
        cmd = f"tail -n {lines} {log_path}/{date}.log"
        
        code, out, err = self.vps._run_ssh_command(cmd)
        if code != 0:
            print(f"❌ Failed to read logs: {err}")
            return {}
        
        analysis = {
            'date': date,
            'lines_analyzed': 0,
            'log_levels': Counter(),
            'errors': [],
            'warnings': [],
            'user_actions': [],
            'bot_events': [],
            'performance': []
        }
        
        for line in out.splitlines():
            analysis['lines_analyzed'] += 1
            
            # Extract log level
            if 'ERROR' in line:
                analysis['log_levels']['ERROR'] += 1
                analysis['errors'].append(self._parse_log_line(line))
            elif 'WARNING' in line:
                analysis['log_levels']['WARNING'] += 1
                analysis['warnings'].append(self._parse_log_line(line))
            elif 'INFO' in line:
                analysis['log_levels']['INFO'] += 1
            elif 'DEBUG' in line:
                analysis['log_levels']['DEBUG'] += 1
            
            # Track user actions
            if any(term in line.lower() for term in ['user', 'command', 'action']):
                analysis['user_actions'].append(self._parse_log_line(line))
            
            # Track bot events
            if any(term in line.lower() for term in ['connected', 'disconnected', 'started', 'stopped']):
                analysis['bot_events'].append(self._parse_log_line(line))
            
            # Track performance
            if any(term in line.lower() for term in ['latency', 'performance', 'memory']):
                analysis['performance'].append(self._parse_log_line(line))
        
        return analysis
    
    def _parse_log_line(self, line: str) -> Dict[str, str]:
        """Parse a log line into components"""
        # Extract timestamp
        timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
        timestamp = timestamp_match.group(1) if timestamp_match else None
        
        # Extract log level
        level_match = re.search(r'\b(ERROR|WARNING|INFO|DEBUG)\b', line)
        level = level_match.group(1) if level_match else None
        
        return {
            'timestamp': timestamp,
            'level': level,
            'message': line.strip()
        }
    
    def generate_report(self, analysis: Dict[str, Any]) -> str:
        """Generate a human-readable report from log analysis"""
        report_dir = Path("logs/analysis")
        report_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = report_dir / f"log_analysis_{timestamp}.txt"
        
        with open(report_file, 'w') as f:
            f.write("="*60 + "\n")
            f.write("QuranBot Log Analysis Report\n")
            f.write("="*60 + "\n\n")
            
            f.write(f"Date: {analysis['date']}\n")
            f.write(f"Lines Analyzed: {analysis['lines_analyzed']}\n\n")
            
            # Log levels summary
            f.write("Log Levels:\n")
            f.write("-"*20 + "\n")
            for level, count in analysis['log_levels'].items():
                f.write(f"{level}: {count}\n")
            f.write("\n")
            
            # Errors
            if analysis['errors']:
                f.write("Recent Errors:\n")
                f.write("-"*20 + "\n")
                for error in analysis['errors'][-5:]:
                    f.write(f"[{error['timestamp']}] {error['message']}\n")
                f.write("\n")
            
            # Warnings
            if analysis['warnings']:
                f.write("Recent Warnings:\n")
                f.write("-"*20 + "\n")
                for warning in analysis['warnings'][-5:]:
                    f.write(f"[{warning['timestamp']}] {warning['message']}\n")
                f.write("\n")
            
            # Bot events
            if analysis['bot_events']:
                f.write("Bot Events:\n")
                f.write("-"*20 + "\n")
                for event in analysis['bot_events'][-5:]:
                    f.write(f"[{event['timestamp']}] {event['message']}\n")
                f.write("\n")
            
            # Performance
            if analysis['performance']:
                f.write("Performance Metrics:\n")
                f.write("-"*20 + "\n")
                for perf in analysis['performance'][-5:]:
                    f.write(f"[{perf['timestamp']}] {perf['message']}\n")
                f.write("\n")
        
        return str(report_file)
    
    def cleanup_old_logs(self, days: int = 30) -> bool:
        """Clean up logs older than specified days"""
        print(f"🧹 Cleaning up logs older than {days} days...")
        
        log_path = self.config['bot']['log_path']
        cmd = f"find {log_path} -name '*.log' -type f -mtime +{days} -delete"
        
        code, out, err = self.vps._run_ssh_command(cmd)
        if code == 0:
            print("✅ Old logs cleaned up successfully")
            return True
        else:
            print(f"❌ Failed to clean up logs: {err}")
            return False
    
    def get_log_stats(self) -> Dict[str, Any]:
        """Get statistics about log files"""
        log_path = self.config['bot']['log_path']
        cmd = f"ls -lh {log_path}/*.log 2>/dev/null"
        
        code, out, err = self.vps._run_ssh_command(cmd)
        if code != 0:
            return {}
        
        stats = {
            'total_size': 0,
            'file_count': 0,
            'newest_file': None,
            'oldest_file': None,
            'files': []
        }
        
        for line in out.splitlines():
            if '.log' not in line:
                continue
            
            parts = line.split()
            if len(parts) >= 9:
                file_info = {
                    'name': parts[-1].split('/')[-1],
                    'size': parts[4],
                    'date': f"{parts[5]} {parts[6]} {parts[7]}"
                }
                stats['files'].append(file_info)
                stats['file_count'] += 1
                
                # Update newest/oldest
                if not stats['newest_file'] or parts[5:8] > stats['newest_file']['date'].split():
                    stats['newest_file'] = file_info
                if not stats['oldest_file'] or parts[5:8] < stats['oldest_file']['date'].split():
                    stats['oldest_file'] = file_info
        
        return stats 