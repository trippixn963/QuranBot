#!/usr/bin/env python3
"""
QuranBot VPS Web Dashboard
==========================
Real-time monitoring and control dashboard for QuranBot VPS deployment.

Features:
- Live bot status monitoring
- Real-time log viewing
- System resource tracking
- Bot control (start/stop/restart)
- Audio playback status
- Error tracking and alerts

Port: 8080 (configurable)
Access: http://your-vps-ip:8080
"""

import json
import os
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import psutil
from flask import Flask, jsonify, render_template, request

# Flask app configuration
app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config['SECRET_KEY'] = 'your-secret-key-change-this'

# Bot configuration
BOT_DIR = "/opt/DiscordBots/QuranBot"
BOT_SERVICE = "quranbot.service"
LOG_DIR = Path(BOT_DIR) / "logs"

class BotMonitor:
    """Monitor bot status and system resources."""
    
    def __init__(self):
        self.bot_dir = Path(BOT_DIR)
        self.log_dir = LOG_DIR
    
    def get_bot_status(self) -> Dict:
        """Get comprehensive bot status - works even when bot is offline."""
        try:
            # Check systemd service status
            service_status = self._get_service_status()
            
            # Check if bot process is running
            bot_process = self._find_bot_process()
            
            # Get bot stats from state file
            bot_stats = self._get_bot_stats()
            
            # Get last activity info
            last_activity = self._get_last_activity()
            
            # Determine overall status
            if service_status['active'] and bot_process:
                overall_status = 'running'
                status_message = 'Bot is running normally'
            elif service_status['active'] and not bot_process:
                overall_status = 'starting'
                status_message = 'Bot service is active but process not found'
            elif not service_status['active'] and service_status['failed']:
                overall_status = 'failed'
                status_message = f"Bot service failed: {service_status['error']}"
            else:
                overall_status = 'stopped'
                status_message = 'Bot is stopped'
            
            return {
                'service_active': service_status['active'],
                'service_enabled': service_status['enabled'],
                'service_failed': service_status['failed'],
                'service_error': service_status['error'],
                'process_running': bot_process is not None,
                'process_id': bot_process.pid if bot_process else None,
                'uptime': self._get_uptime(bot_process),
                'memory_usage': self._get_memory_usage(bot_process),
                'cpu_usage': self._get_cpu_usage(bot_process),
                'status': overall_status,
                'status_message': status_message,
                'bot_stats': bot_stats,
                'last_activity': last_activity,
                'last_updated': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'error': f"Dashboard error: {str(e)}",
                'status': 'dashboard_error',
                'status_message': f"Dashboard cannot determine bot status: {str(e)}",
                'service_active': False,
                'process_running': False,
                'last_updated': datetime.now().isoformat()
            }
    
    def _find_bot_process(self) -> Optional[psutil.Process]:
        """Find the bot process."""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if proc.info['cmdline']:
                    cmdline = ' '.join(proc.info['cmdline'])
                    if 'main.py' in cmdline and 'QuranBot' in cmdline:
                        return proc
        except:
            pass
        return None
    
    def _get_uptime(self, process: Optional[psutil.Process]) -> str:
        """Get process uptime."""
        if not process:
            return "Not running"
        
        try:
            create_time = process.create_time()
            uptime_seconds = time.time() - create_time
            uptime_hours = int(uptime_seconds // 3600)
            uptime_minutes = int((uptime_seconds % 3600) // 60)
            return f"{uptime_hours}h {uptime_minutes}m"
        except:
            return "Unknown"
    
    def _get_memory_usage(self, process: Optional[psutil.Process]) -> str:
        """Get memory usage."""
        if not process:
            return "0 MB"
        
        try:
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            return f"{memory_mb:.1f} MB"
        except:
            return "Unknown"
    
    def _get_cpu_usage(self, process: Optional[psutil.Process]) -> str:
        """Get CPU usage."""
        if not process:
            return "0%"
        
        try:
            cpu_percent = process.cpu_percent(interval=1)
            return f"{cpu_percent:.1f}%"
        except:
            return "Unknown"
    
    def _get_service_status(self) -> Dict:
        """Get detailed systemd service status."""
        try:
            # Check if service is active
            result_active = subprocess.run(
                ['/usr/bin/systemctl', 'is-active', BOT_SERVICE],
                capture_output=True,
                text=True
            )
            is_active = result_active.stdout.strip() == 'active'
            
            # Check if service is enabled
            result_enabled = subprocess.run(
                ['/usr/bin/systemctl', 'is-enabled', BOT_SERVICE],
                capture_output=True,
                text=True
            )
            is_enabled = result_enabled.stdout.strip() == 'enabled'
            
            # Check if service has failed
            result_failed = subprocess.run(
                ['/usr/bin/systemctl', 'is-failed', BOT_SERVICE],
                capture_output=True,
                text=True
            )
            has_failed = result_failed.stdout.strip() == 'failed'
            
            # Get service error if failed
            error_message = None
            if has_failed:
                result_status = subprocess.run(
                    ['/usr/bin/systemctl', 'status', BOT_SERVICE, '--no-pager', '-l'],
                    capture_output=True,
                    text=True
                )
                error_message = result_status.stdout.strip()
            
            return {
                'active': is_active,
                'enabled': is_enabled,
                'failed': has_failed,
                'error': error_message
            }
        except Exception as e:
            return {
                'active': False,
                'enabled': False,
                'failed': True,
                'error': f"Cannot check service status: {str(e)}"
            }
    
    def _get_last_activity(self) -> Dict:
        """Get last bot activity information."""
        try:
            # Check for recent log activity
            today = datetime.now().strftime("%Y-%m-%d")
            log_file = self.log_dir / today / "logs.log"
            
            if log_file.exists():
                # Get file modification time
                mod_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                time_diff = datetime.now() - mod_time
                
                # Read last few lines for activity
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        last_line = lines[-1].strip()
                        return {
                            'last_log_time': mod_time.isoformat(),
                            'minutes_ago': int(time_diff.total_seconds() / 60),
                            'last_log_entry': last_line[:100] + '...' if len(last_line) > 100 else last_line,
                            'has_recent_activity': time_diff.total_seconds() < 300  # 5 minutes
                        }
            
            return {
                'last_log_time': 'Unknown',
                'minutes_ago': 999,
                'last_log_entry': 'No recent logs found',
                'has_recent_activity': False
            }
        except Exception as e:
            return {
                'last_log_time': 'Error',
                'minutes_ago': 999,
                'last_log_entry': f'Error reading logs: {str(e)}',
                'has_recent_activity': False
            }
    
    def _get_bot_stats(self) -> Dict:
        """Get bot statistics from state files."""
        try:
            # Try to read bot stats
            stats_file = self.bot_dir / "data" / "bot_stats.json"
            if stats_file.exists():
                with open(stats_file, 'r') as f:
                    stats = json.load(f)
                return {
                    'total_sessions': stats.get('total_sessions', 0),
                    'total_runtime': stats.get('total_runtime_hours', 0),
                    'last_session': stats.get('last_session_start', 'Unknown')
                }
        except:
            pass
        
        return {
            'total_sessions': 0,
            'total_runtime': 0,
            'last_session': 'Unknown'
        }
    
    def get_recent_logs(self, lines: int = 50) -> List[str]:
        """Get recent log entries."""
        try:
            # Get today's log file
            today = datetime.now().strftime("%Y-%m-%d")
            log_file = self.log_dir / today / "logs.log"
            
            if not log_file.exists():
                return ["No logs found for today"]
            
            # Read last N lines
            with open(log_file, 'r') as f:
                all_lines = f.readlines()
                recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                return [line.strip() for line in recent_lines if line.strip()]
        except Exception as e:
            return [f"Error reading logs: {str(e)}"]
    
    def get_error_logs(self, lines: int = 20) -> List[str]:
        """Get recent error logs."""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            error_file = self.log_dir / today / "errors.log"
            
            if not error_file.exists():
                return ["No errors found for today"]
            
            with open(error_file, 'r') as f:
                all_lines = f.readlines()
                recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                return [line.strip() for line in recent_lines if line.strip()]
        except Exception as e:
            return [f"Error reading error logs: {str(e)}"]
    
    def get_system_info(self) -> Dict:
        """Get system resource information."""
        try:
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent,
                'load_average': os.getloadavg()[0] if hasattr(os, 'getloadavg') else 0,
                'uptime': self._get_system_uptime()
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _get_system_uptime(self) -> str:
        """Get system uptime."""
        try:
            boot_time = psutil.boot_time()
            uptime_seconds = time.time() - boot_time
            uptime_hours = int(uptime_seconds // 3600)
            uptime_days = uptime_hours // 24
            uptime_hours = uptime_hours % 24
            return f"{uptime_days}d {uptime_hours}h"
        except:
            return "Unknown"
    
    def get_audio_status(self) -> Dict:
        """Get audio playback status and information."""
        try:
            # Check current playback state
            state_file = self.bot_dir / "data" / "playback_state.json"
            audio_info = {
                'playback_active': False,
                'current_surah': 'None',
                'current_reciter': 'None',
                'current_position': 0,
                'total_duration': 0,
                'loop_enabled': False,
                'shuffle_enabled': False,
                'last_updated': 'Unknown'
            }
            
            if state_file.exists():
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    audio_info.update({
                        'playback_active': state.get('is_playing', False),
                        'current_surah': f"Surah {state.get('current_surah', 'Unknown')}",
                        'current_reciter': state.get('current_reciter', 'Unknown'),
                        'current_position': state.get('current_position', 0),
                        'total_duration': state.get('total_duration', 0),
                        'loop_enabled': state.get('loop_enabled', False),
                        'shuffle_enabled': state.get('shuffle_enabled', False),
                        'last_updated': state.get('last_updated', 'Unknown')
                    })
            
            # Check audio files availability
            audio_dir = self.bot_dir / "audio"
            if audio_dir.exists():
                reciters = [d.name for d in audio_dir.iterdir() if d.is_dir()]
                audio_info['available_reciters'] = len(reciters)
                audio_info['reciter_list'] = reciters[:5]  # Top 5 for display
            else:
                audio_info['available_reciters'] = 0
                audio_info['reciter_list'] = []
            
            return audio_info
        except Exception as e:
            return {'error': f"Error getting audio status: {str(e)}"}
    
    def get_discord_status(self) -> Dict:
        """Get Discord connection and server information."""
        try:
            # Check environment configuration
            env_file = self.bot_dir / "config" / ".env"
            discord_info = {
                'configured': False,
                'guild_id': 'Not configured',
                'voice_channel': 'Not configured',
                'panel_channel': 'Not configured',
                'logs_channel': 'Not configured',
                'connection_status': 'Unknown'
            }
            
            if env_file.exists():
                with open(env_file, 'r') as f:
                    env_content = f.read()
                    
                    # Check for required configuration
                    if 'DISCORD_TOKEN=' in env_content and 'your_discord_bot_token' not in env_content:
                        discord_info['configured'] = True
                        
                        # Extract configuration details (safely)
                        lines = env_content.split('\n')
                        for line in lines:
                            if line.startswith('GUILD_ID=') and not line.endswith('your_discord_server_id'):
                                discord_info['guild_id'] = 'Configured'
                            elif line.startswith('TARGET_CHANNEL_ID=') and not line.endswith('voice_channel_id_for_audio'):
                                discord_info['voice_channel'] = 'Configured'
                            elif line.startswith('PANEL_CHANNEL_ID=') and not line.endswith('text_channel_id_for_control_panel'):
                                discord_info['panel_channel'] = 'Configured'
                            elif line.startswith('LOGS_CHANNEL_ID=') and not line.endswith('text_channel_id_for_logs'):
                                discord_info['logs_channel'] = 'Configured'
            
            # Try to determine connection status from logs
            if discord_info['configured']:
                recent_logs = self.get_recent_logs(20)
                connection_indicators = [
                    'Discord connection established',
                    'Bot connected to Discord',
                    'Ready event received',
                    'Connected to Discord'
                ]
                
                disconnect_indicators = [
                    'Discord connection lost',
                    'Connection error',
                    'Disconnected from Discord'
                ]
                
                # Check recent logs for connection status
                for log in reversed(recent_logs):
                    if any(indicator in log for indicator in connection_indicators):
                        discord_info['connection_status'] = 'Connected'
                        break
                    elif any(indicator in log for indicator in disconnect_indicators):
                        discord_info['connection_status'] = 'Disconnected'
                        break
            
            return discord_info
        except Exception as e:
            return {'error': f"Error getting Discord status: {str(e)}"}
    
    def get_user_activity(self) -> Dict:
        """Get user activity and statistics."""
        try:
            # Check listening stats
            stats_file = self.bot_dir / "data" / "listening_stats.json"
            user_info = {
                'active_users': 0,
                'total_users': 0,
                'top_users': [],
                'recent_activity': []
            }
            
            if stats_file.exists():
                with open(stats_file, 'r') as f:
                    stats = json.load(f)
                    
                    users = stats.get('users', {})
                    user_info['total_users'] = len(users)
                    
                    # Get top users by listening time
                    user_list = []
                    for user_id, user_data in users.items():
                        user_list.append({
                            'user_id': user_id,
                            'total_time': user_data.get('total_time', 0),
                            'sessions': user_data.get('sessions', 0),
                            'last_seen': user_data.get('last_seen', 'Unknown')
                        })
                    
                    # Sort by total time and get top 5
                    user_list.sort(key=lambda x: x['total_time'], reverse=True)
                    user_info['top_users'] = user_list[:5]
                    
                    # Count active users (activity in last 24 hours)
                    active_count = 0
                    current_time = datetime.now()
                    for user_data in user_list:
                        try:
                            last_seen = datetime.fromisoformat(user_data['last_seen'].replace('Z', '+00:00'))
                            if (current_time - last_seen).total_seconds() < 86400:  # 24 hours
                                active_count += 1
                        except:
                            pass
                    
                    user_info['active_users'] = active_count
            
            return user_info
        except Exception as e:
            return {'error': f"Error getting user activity: {str(e)}"}
    
    def get_config_status(self) -> Dict:
        """Get bot configuration status."""
        try:
            config_info = {
                'env_file_exists': False,
                'required_vars_set': 0,
                'total_required_vars': 6,
                'ffmpeg_available': False,
                'audio_directory': False,
                'data_directory': False,
                'logs_directory': False
            }
            
            # Check environment file
            env_file = self.bot_dir / "config" / ".env"
            if env_file.exists():
                config_info['env_file_exists'] = True
                
                with open(env_file, 'r') as f:
                    env_content = f.read()
                    
                    required_vars = [
                        ('DISCORD_TOKEN', 'your_discord_bot_token'),
                        ('GUILD_ID', 'your_discord_server_id'),
                        ('TARGET_CHANNEL_ID', 'voice_channel_id'),
                        ('PANEL_CHANNEL_ID', 'text_channel_id'),
                        ('LOGS_CHANNEL_ID', 'text_channel_id'),
                        ('DEVELOPER_ID', 'your_discord_user_id')
                    ]
                    
                    for var_name, default_value in required_vars:
                        if f"{var_name}=" in env_content and default_value not in env_content:
                            config_info['required_vars_set'] += 1
            
            # Check FFmpeg
            try:
                result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
                config_info['ffmpeg_available'] = result.returncode == 0
            except:
                config_info['ffmpeg_available'] = False
            
            # Check directories
            config_info['audio_directory'] = (self.bot_dir / "audio").exists()
            config_info['data_directory'] = (self.bot_dir / "data").exists()
            config_info['logs_directory'] = (self.bot_dir / "logs").exists()
            
            return config_info
        except Exception as e:
            return {'error': f"Error getting config status: {str(e)}"}
    
    def get_performance_metrics(self) -> Dict:
        """Get detailed performance metrics."""
        try:
            # Get bot process for detailed metrics
            bot_process = self._find_bot_process()
            
            metrics = {
                'cpu_times': {},
                'memory_info': {},
                'io_stats': {},
                'connections': 0,
                'threads': 0
            }
            
            if bot_process:
                try:
                    # CPU times
                    cpu_times = bot_process.cpu_times()
                    metrics['cpu_times'] = {
                        'user': cpu_times.user,
                        'system': cpu_times.system
                    }
                    
                    # Memory info
                    memory_info = bot_process.memory_info()
                    metrics['memory_info'] = {
                        'rss': memory_info.rss,
                        'vms': memory_info.vms,
                        'rss_mb': round(memory_info.rss / 1024 / 1024, 2),
                        'vms_mb': round(memory_info.vms / 1024 / 1024, 2)
                    }
                    
                    # IO stats
                    try:
                        io_stats = bot_process.io_counters()
                        metrics['io_stats'] = {
                            'read_bytes': io_stats.read_bytes,
                            'write_bytes': io_stats.write_bytes,
                            'read_mb': round(io_stats.read_bytes / 1024 / 1024, 2),
                            'write_mb': round(io_stats.write_bytes / 1024 / 1024, 2)
                        }
                    except:
                        metrics['io_stats'] = {'error': 'IO stats not available'}
                    
                    # Connections and threads
                    try:
                        metrics['connections'] = len(bot_process.connections())
                        metrics['threads'] = bot_process.num_threads()
                    except:
                        pass
                        
                except psutil.NoSuchProcess:
                    metrics['error'] = 'Bot process not found'
            else:
                metrics['error'] = 'Bot not running'
            
            return metrics
        except Exception as e:
            return {'error': f"Error getting performance metrics: {str(e)}"}
    
    def search_logs(self, query: str, date: str, lines: int = 100) -> Dict:
        """Search logs for specific content."""
        try:
            log_file = self.log_dir / date / "logs.log"
            
            if not log_file.exists():
                return {'results': [], 'total_matches': 0, 'error': f'No logs found for {date}'}
            
            matches = []
            with open(log_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    if query.lower() in line.lower():
                        matches.append({
                            'line_number': line_num,
                            'content': line.strip(),
                            'timestamp': line.split(']')[0].strip('[') if ']' in line else 'Unknown'
                        })
                        
                        if len(matches) >= lines:
                            break
            
            return {
                'results': matches,
                'total_matches': len(matches),
                'query': query,
                'date': date
            }
        except Exception as e:
            return {'error': f"Error searching logs: {str(e)}"}
    
    def get_available_log_dates(self) -> List[str]:
        """Get list of available log dates."""
        try:
            if not self.log_dir.exists():
                return []
            
            dates = []
            for item in self.log_dir.iterdir():
                if item.is_dir() and item.name.match(r'\d{4}-\d{2}-\d{2}'):
                    dates.append(item.name)
            
            return sorted(dates, reverse=True)
        except Exception as e:
            return []
    
    def get_backup_status(self) -> Dict:
        """Get backup status information."""
        try:
            backup_dir = self.bot_dir / "backup"
            backup_info = {
                'backup_directory_exists': backup_dir.exists(),
                'recent_backups': [],
                'total_backups': 0,
                'last_backup': 'Unknown'
            }
            
            if backup_dir.exists():
                # Get backup files
                backup_files = []
                for backup_file in backup_dir.rglob('*.zip'):
                    stat = backup_file.stat()
                    backup_files.append({
                        'name': backup_file.name,
                        'size': stat.st_size,
                        'size_mb': round(stat.st_size / 1024 / 1024, 2),
                        'created': datetime.fromtimestamp(stat.st_ctime).isoformat()
                    })
                
                # Sort by creation time
                backup_files.sort(key=lambda x: x['created'], reverse=True)
                
                backup_info['recent_backups'] = backup_files[:5]
                backup_info['total_backups'] = len(backup_files)
                
                if backup_files:
                    backup_info['last_backup'] = backup_files[0]['created']
            
            return backup_info
        except Exception as e:
            return {'error': f"Error getting backup status: {str(e)}"}
    
    def get_network_stats(self) -> Dict:
        """Get network statistics."""
        try:
            # Get network IO stats
            net_io = psutil.net_io_counters()
            
            network_info = {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv,
                'bytes_sent_mb': round(net_io.bytes_sent / 1024 / 1024, 2),
                'bytes_recv_mb': round(net_io.bytes_recv / 1024 / 1024, 2)
            }
            
            # Get network connections
            try:
                connections = psutil.net_connections()
                network_info['total_connections'] = len(connections)
                network_info['established_connections'] = len([c for c in connections if c.status == 'ESTABLISHED'])
            except:
                network_info['total_connections'] = 0
                network_info['established_connections'] = 0
            
            return network_info
        except Exception as e:
            return {'error': f"Error getting network stats: {str(e)}"}
    
    def control_bot(self, action: str) -> Dict:
        """Control bot service with detailed feedback."""
        try:
            if action not in ['start', 'stop', 'restart', 'status']:
                return {'error': 'Invalid action'}
            
            result = subprocess.run(
                ['/usr/bin/systemctl', action, BOT_SERVICE],
                capture_output=True,
                text=True
            )
            
            return {
                'action': action,
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr if result.stderr else None,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {'error': f"Error controlling bot: {str(e)}"}
    
    def get_quick_stats(self) -> Dict:
        """Get quick statistics for dashboard overview."""
        try:
            stats = {
                'bot_online': False,
                'discord_connected': False,
                'users_active': 0,
                'audio_playing': False,
                'system_healthy': True,
                'last_error': None
            }
            
            # Check bot status
            bot_status = self.get_bot_status()
            stats['bot_online'] = bot_status.get('status') == 'running'
            
            # Check Discord connection
            discord_status = self.get_discord_status()
            stats['discord_connected'] = discord_status.get('connection_status') == 'Connected'
            
            # Check user activity
            user_activity = self.get_user_activity()
            stats['users_active'] = user_activity.get('active_users', 0)
            
            # Check audio status
            audio_status = self.get_audio_status()
            stats['audio_playing'] = audio_status.get('playback_active', False)
            
            # Check system health
            system_info = self.get_system_info()
            if not system_info.get('error'):
                cpu_high = system_info.get('cpu_percent', 0) > 80
                memory_high = system_info.get('memory_percent', 0) > 90
                disk_high = system_info.get('disk_percent', 0) > 95
                stats['system_healthy'] = not (cpu_high or memory_high or disk_high)
            
            # Get last error
            error_logs = self.get_error_logs(1)
            if error_logs and error_logs[0] != "No errors found for today":
                stats['last_error'] = error_logs[0][:100]
            
            return stats
        except Exception as e:
            return {'error': f"Error getting quick stats: {str(e)}"}
    
    def get_dashboard_info(self) -> Dict:
        """Get dashboard-specific information."""
        try:
            return {
                'version': '2.0',
                'uptime': self._get_dashboard_uptime(),
                'features': [
                    'Real-time Bot Monitoring',
                    'System Resource Tracking',
                    'Audio Status Monitoring',
                    'Discord Connection Status',
                    'User Activity Tracking',
                    'Log Search & Analysis',
                    'Performance Metrics',
                    'Backup Status',
                    'Network Statistics',
                    'Remote Bot Control'
                ],
                'endpoints': len([
                    '/api/status', '/api/logs', '/api/errors', '/api/system',
                    '/api/control', '/api/audio', '/api/discord', '/api/users',
                    '/api/config', '/api/performance', '/api/logs/search',
                    '/api/backup', '/api/network'
                ])
            }
        except Exception as e:
            return {'error': f"Error getting dashboard info: {str(e)}"}
    
    def _get_dashboard_uptime(self) -> str:
        """Get dashboard uptime."""
        try:
            # This is a simplified version - in a real implementation,
            # you'd track when the dashboard started
            return "Since VPS boot"
        except:
            return "Unknown"

# Initialize monitor
monitor = BotMonitor()

@app.route('/')
def dashboard():
    """Main dashboard page."""
    return render_template('dashboard.html')

@app.route('/api/status')
def api_status():
    """API endpoint for bot status."""
    return jsonify(monitor.get_bot_status())

@app.route('/api/logs')
def api_logs():
    """API endpoint for recent logs."""
    lines = request.args.get('lines', 50, type=int)
    return jsonify({
        'logs': monitor.get_recent_logs(lines),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/errors')
def api_errors():
    """API endpoint for error logs."""
    lines = request.args.get('lines', 20, type=int)
    return jsonify({
        'errors': monitor.get_error_logs(lines),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/system')
def api_system():
    """API endpoint for system information."""
    return jsonify(monitor.get_system_info())

@app.route('/api/control/<action>')
def api_control(action):
    """API endpoint for bot control actions."""
    if action not in ['start', 'stop', 'restart', 'status']:
        return jsonify({'error': 'Invalid action'}), 400
    
    try:
        if action == 'status':
            result = subprocess.run(
                ['/usr/bin/systemctl', 'status', BOT_SERVICE],
                capture_output=True,
                text=True
            )
        else:
            result = subprocess.run(
                ['/usr/bin/systemctl', action, BOT_SERVICE],
                capture_output=True,
                text=True
            )
        
        return jsonify({
            'action': action,
            'success': result.returncode == 0,
            'output': result.stdout,
            'error': result.stderr if result.stderr else None
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/audio')
def api_audio():
    """API endpoint for audio status information."""
    try:
        audio_info = monitor.get_audio_status()
        return jsonify(audio_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/discord')
def api_discord():
    """API endpoint for Discord connection status."""
    try:
        discord_info = monitor.get_discord_status()
        return jsonify(discord_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users')
def api_users():
    """API endpoint for user activity information."""
    try:
        user_info = monitor.get_user_activity()
        return jsonify(user_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/config')
def api_config():
    """API endpoint for bot configuration information."""
    try:
        config_info = monitor.get_config_status()
        return jsonify(config_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/performance')
def api_performance():
    """API endpoint for detailed performance metrics."""
    try:
        perf_info = monitor.get_performance_metrics()
        return jsonify(perf_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs/search')
def api_logs_search():
    """API endpoint for searching logs."""
    try:
        query = request.args.get('query', '')
        date = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
        lines = request.args.get('lines', 100, type=int)
        
        if not query:
            return jsonify({'error': 'Query parameter required'}), 400
        
        results = monitor.search_logs(query, date, lines)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs/dates')
def api_logs_dates():
    """API endpoint for available log dates."""
    try:
        dates = monitor.get_available_log_dates()
        return jsonify({'dates': dates})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/backup')
def api_backup():
    """API endpoint for backup status."""
    try:
        backup_info = monitor.get_backup_status()
        return jsonify(backup_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/network')
def api_network():
    """API endpoint for network statistics."""
    try:
        network_info = monitor.get_network_stats()
        return jsonify(network_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/quick-stats')
def api_quick_stats():
    """API endpoint for quick dashboard overview stats."""
    try:
        stats = monitor.get_quick_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard-info')
def api_dashboard_info():
    """API endpoint for dashboard information."""
    try:
        info = monitor.get_dashboard_info()
        return jsonify(info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def api_health():
    """API endpoint for overall system health check."""
    try:
        health = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'components': {}
        }
        
        # Check bot status
        bot_status = monitor.get_bot_status()
        health['components']['bot'] = {
            'status': 'healthy' if bot_status.get('status') == 'running' else 'unhealthy',
            'details': bot_status.get('status_message', 'Unknown')
        }
        
        # Check system resources
        system_info = monitor.get_system_info()
        if not system_info.get('error'):
            cpu_ok = system_info.get('cpu_percent', 0) < 80
            memory_ok = system_info.get('memory_percent', 0) < 90
            disk_ok = system_info.get('disk_percent', 0) < 95
            
            health['components']['system'] = {
                'status': 'healthy' if (cpu_ok and memory_ok and disk_ok) else 'degraded',
                'details': f"CPU: {system_info.get('cpu_percent', 0):.1f}%, Memory: {system_info.get('memory_percent', 0):.1f}%, Disk: {system_info.get('disk_percent', 0):.1f}%"
            }
        else:
            health['components']['system'] = {
                'status': 'unhealthy',
                'details': system_info.get('error', 'Unknown error')
            }
        
        # Check Discord connection
        discord_status = monitor.get_discord_status()
        health['components']['discord'] = {
            'status': 'healthy' if discord_status.get('connection_status') == 'Connected' else 'unhealthy',
            'details': discord_status.get('connection_status', 'Unknown')
        }
        
        # Overall health
        unhealthy_components = [comp for comp in health['components'].values() if comp['status'] == 'unhealthy']
        if unhealthy_components:
            health['status'] = 'unhealthy'
        elif any(comp['status'] == 'degraded' for comp in health['components'].values()):
            health['status'] = 'degraded'
        
        return jsonify(health)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs/download/<date>')
def api_logs_download(date):
    """API endpoint for downloading log files."""
    try:
        from flask import send_file
        import tempfile
        import zipfile
        
        # Validate date format
        datetime.strptime(date, '%Y-%m-%d')
        
        log_dir = monitor.log_dir / date
        if not log_dir.exists():
            return jsonify({'error': f'No logs found for {date}'}), 404
        
        # Create temporary zip file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        
        with zipfile.ZipFile(temp_file.name, 'w') as zipf:
            for log_file in log_dir.glob('*.log'):
                zipf.write(log_file, log_file.name)
            for log_file in log_dir.glob('*.json'):
                zipf.write(log_file, log_file.name)
        
        return send_file(
            temp_file.name,
            as_attachment=True,
            download_name=f'quranbot-logs-{date}.zip',
            mimetype='application/zip'
        )
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    # Run the Flask app
    app.run(
        host='0.0.0.0',
        port=8080,
        debug=False,
        threaded=True
    ) 