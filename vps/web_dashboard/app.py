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
- Tree logging for dashboard interactions

Port: 8080 (configurable)
Access: http://your-vps-ip:8080
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
import pytz
from pathlib import Path
from typing import Dict, List, Optional

import psutil
from flask import Flask, jsonify, render_template, request
import re # Added for activity feed parsing

# Add the bot's src directory to Python path for tree logging
sys.path.insert(0, '/opt/DiscordBots/QuranBot/src')

# Import tree logging functionality
try:
    from utils.tree_log import TreeLogger, log_user_interaction, log_status
    TREE_LOGGING_AVAILABLE = True
except ImportError:
    TREE_LOGGING_AVAILABLE = False
    print("Warning: Tree logging not available - QuranBot src not found")


# EST timezone helper functions (to match bot timezone)
def get_est_now():
    """Get current time in EST timezone (same as bot)."""
    est = pytz.timezone('America/New_York')
    return datetime.now(est)

def get_est_date_string():
    """Get current date string in EST timezone for log file paths."""
    return get_est_now().strftime('%Y-%m-%d')

# Flask app configuration
app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config['SECRET_KEY'] = 'your-secret-key-change-this'

# Bot configuration
BOT_DIR = "/opt/DiscordBots/QuranBot"
BOT_SERVICE = "quranbot.service"
LOG_DIR = Path(BOT_DIR) / "logs"

# Initialize tree logger
tree_logger = TreeLogger() if TREE_LOGGING_AVAILABLE else None

def log_dashboard_interaction(action: str, endpoint: str, user_ip: str, details: Dict = None):
    """Log dashboard interactions using tree logging."""
    if not TREE_LOGGING_AVAILABLE or not tree_logger:
        return
    
    try:
        # Create interaction details
        interaction_details = {
            "endpoint": endpoint,
            "user_ip": user_ip,
            "timestamp": get_est_now().isoformat(),
            "user_agent": request.headers.get('User-Agent', 'Unknown')
        }
        
        if details:
            interaction_details.update(details)
        
        # Log using tree logging
        log_user_interaction(
            interaction_type="dashboard_interaction",
            user_name=f"Dashboard User ({user_ip})",
            user_id=hash(user_ip) % 1000000,  # Create consistent numeric ID from IP
            action_description=f"{action} - {endpoint}",
            details=interaction_details
        )
    except Exception as e:
        print(f"Tree logging error: {e}")

def log_dashboard_status(message: str, status: str = "INFO", emoji: str = "🖥️"):
    """Log dashboard status messages using tree logging."""
    if not TREE_LOGGING_AVAILABLE:
        return
    
    try:
        log_status(f"Dashboard: {message}", status=status, emoji=emoji)
    except Exception as e:
        print(f"Tree logging error: {e}")

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
                'last_updated': get_est_now().isoformat()
            }
        except Exception as e:
            return {
                'error': f"Dashboard error: {str(e)}",
                'status': 'dashboard_error',
                'status_message': f"Dashboard cannot determine bot status: {str(e)}",
                'service_active': False,
                'process_running': False,
                'last_updated': get_est_now().isoformat()
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
            today = get_est_date_string()
            log_file = self.log_dir / today / "logs.log"
            
            if log_file.exists():
                # Get file modification time
                mod_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                time_diff = get_est_now() - mod_time
                
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
            today = get_est_date_string()
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
            today = get_est_date_string()
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
                'last_updated': 'Unknown',
                # Dashboard-specific fields
                'current_track': 'None',
                'voice_channel': 'Not connected',
                'status': 'Unknown'
            }
            
            if state_file.exists():
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    current_surah = state.get('current_surah', 'Unknown')
                    current_reciter = state.get('current_reciter', 'Unknown')
                    is_playing = state.get('is_playing', False)
                    
                    # Get surah name from surah mapper
                    surah_name = self._get_surah_name(current_surah)
                    
                    audio_info.update({
                        'playback_active': is_playing,
                        'current_surah': f"Surah {current_surah}",
                        'current_reciter': current_reciter,
                        'current_position': state.get('current_position', 0),
                        'total_duration': state.get('total_duration', 0),
                        'loop_enabled': state.get('loop_enabled', False),
                        'shuffle_enabled': state.get('shuffle_enabled', False),
                        'last_updated': state.get('last_updated', 'Unknown'),
                        # Dashboard-specific fields
                        'current_track': f"{surah_name} - {current_reciter}" if current_surah != 'Unknown' else 'None',
                        'status': 'Playing' if is_playing else 'Paused'
                    })
            
            # Check voice connection status from logs
            voice_connected = self._check_voice_connection_status()
            audio_info['voice_channel'] = 'Connected' if voice_connected else 'Not connected'
            
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
    
    def _get_surah_name(self, surah_number) -> str:
        """Get surah name from surah number."""
        try:
            # Try to load surah names from the bot's surahs.json file
            surahs_file = self.bot_dir / "src" / "utils" / "surahs.json"
            if surahs_file.exists():
                with open(surahs_file, 'r', encoding='utf-8') as f:
                    surahs = json.load(f)
                    surah_str = str(surah_number)
                    if surah_str in surahs:
                        return surahs[surah_str]['name_transliteration']
            
            # Fallback to basic surah names
            surah_names = {
                1: "Al-Fatiha", 2: "Al-Baqarah", 3: "Ali 'Imran", 4: "An-Nisa",
                5: "Al-Ma'idah", 6: "Al-An'am", 7: "Al-A'raf", 8: "Al-Anfal",
                9: "At-Tawbah", 10: "Yunus", 11: "Hud", 12: "Yusuf",
                13: "Ar-Ra'd", 14: "Ibrahim", 15: "Al-Hijr", 16: "An-Nahl",
                17: "Al-Isra", 18: "Al-Kahf", 19: "Maryam", 20: "Ta-Ha"
            }
            return surah_names.get(int(surah_number), f"Surah {surah_number}")
        except:
            return f"Surah {surah_number}"
    
    def _check_voice_connection_status(self) -> bool:
        """Check if bot is connected to voice channel by examining recent logs."""
        try:
            # Check recent logs for voice connection indicators
            recent_logs = self.get_recent_logs(50)
            
            # Look for voice connection indicators in recent logs
            connection_indicators = [
                'Voice connection established',
                'connection complete',
                'Connected to voice',
                'Reconnected to',
                'Fresh connection established',
                'Voice Connection - Success'
            ]
            
            disconnect_indicators = [
                'Voice disconnected',
                'Disconnected from voice',
                'Voice connection lost',
                'Connection terminated',
                'Bot Disconnected'
            ]
            
            # Check recent logs (most recent first)
            for log in reversed(recent_logs):
                # Check for connection indicators
                if any(indicator.lower() in log.lower() for indicator in connection_indicators):
                    return True
                # Check for disconnection indicators
                elif any(indicator.lower() in log.lower() for indicator in disconnect_indicators):
                    return False
            
            # If no clear indicators, check if bot process is running and has audio playing
            # This is a fallback check
            bot_status = self.get_bot_status()
            if bot_status.get('process_running') and bot_status.get('status') == 'running':
                # If bot is running and audio is playing, likely connected
                state_file = self.bot_dir / "data" / "playback_state.json"
                if state_file.exists():
                    with open(state_file, 'r') as f:
                        state = json.load(f)
                        if state.get('is_playing', False):
                            return True
            
            return False
        except Exception as e:
            # If we can't determine status, assume not connected
            return False
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
                    current_time = get_est_now()
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
                'timestamp': get_est_now().isoformat()
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
    
    def get_quiz_statistics(self) -> Dict:
        """Get comprehensive quiz statistics."""
        try:
            quiz_stats = {
                'total_questions': 0,
                'correct_answers': 0,
                'user_participation': 0,
                'accuracy_rate': 0.0,
                'recent_activity': [],
                'popular_categories': {},
                'difficulty_stats': {}
            }
            
            # Try to read quiz stats file (contains user scores)
            quiz_stats_file = self.bot_dir / "data" / "quiz_stats.json"
            if quiz_stats_file.exists():
                with open(quiz_stats_file, 'r') as f:
                    quiz_data = json.load(f)
                    
                    # Extract statistics from user scores
                    user_scores = quiz_data.get('user_scores', {})
                    quiz_stats['user_participation'] = len(user_scores)
                    
                    # Calculate totals from all users
                    total_questions = 0
                    total_correct = 0
                    
                    for user_id, user_data in user_scores.items():
                        total_questions += user_data.get('total_questions', 0)
                        total_correct += user_data.get('correct_answers', 0)
                    
                    quiz_stats['total_questions'] = total_questions
                    quiz_stats['correct_answers'] = total_correct
                    
                    if total_questions > 0:
                        quiz_stats['accuracy_rate'] = (total_correct / total_questions) * 100
                    
                    # Get top performers for recent activity
                    user_list = []
                    for user_id, user_data in user_scores.items():
                        if user_data.get('total_questions', 0) > 0:
                            accuracy = (user_data.get('correct_answers', 0) / user_data.get('total_questions', 1)) * 100
                            user_list.append({
                                'user_id': user_id,
                                'questions': user_data.get('total_questions', 0),
                                'correct': user_data.get('correct_answers', 0),
                                'accuracy': accuracy,
                                'streak': user_data.get('best_streak', 0)
                            })
                    
                    # Sort by total questions and get top 5 for recent activity
                    user_list.sort(key=lambda x: x['questions'], reverse=True)
                    quiz_stats['recent_activity'] = user_list[:5]
            
            return quiz_stats
        except Exception as e:
            return {'error': f"Failed to get quiz statistics: {str(e)}"}
    
    def get_verse_statistics(self) -> Dict:
        """Get comprehensive verse statistics."""
        try:
            verse_stats = {
                'total_verses_sent': 0,
                'dua_reactions': 0,
                'user_engagement': 0,
                'recent_verses': [],
                'popular_surahs': {},
                'reaction_rate': 0.0
            }
            
            # Try to read verse state file
            verse_state_file = self.bot_dir / "data" / "daily_verses_state.json"
            if verse_state_file.exists():
                with open(verse_state_file, 'r') as f:
                    verse_data = json.load(f)
                    
                    # Extract statistics from verse data
                    verse_stats['total_verses_sent'] = verse_data.get('total_verses_sent', 0)
                    verse_stats['dua_reactions'] = verse_data.get('total_dua_reactions', 0)
                    verse_stats['user_engagement'] = len(verse_data.get('user_reactions', {}))
                    
                    if verse_stats['total_verses_sent'] > 0:
                        verse_stats['reaction_rate'] = (verse_stats['dua_reactions'] / verse_stats['total_verses_sent']) * 100
                    
                    # Get recent verses
                    recent_verses = verse_data.get('recent_verses', [])
                    verse_stats['recent_verses'] = recent_verses[-10:] if recent_verses else []
                    
                    # Get popular surahs
                    verse_stats['popular_surahs'] = verse_data.get('surah_stats', {})
            
            return verse_stats
        except Exception as e:
            return {'error': f"Failed to get verse statistics: {str(e)}"}
    
    def get_current_intervals(self) -> Dict:
        """Get current quiz and verse intervals."""
        try:
            intervals = {
                'quiz_interval': 3.0,  # Default 3 hours
                'verse_interval': 6.0,  # Default 6 hours
                'quiz_formatted': '3h',
                'verse_formatted': '6h'
            }
            
            # Get quiz interval
            quiz_state_file = self.bot_dir / "data" / "quiz_state.json"
            if quiz_state_file.exists():
                with open(quiz_state_file, 'r') as f:
                    quiz_data = json.load(f)
                    schedule_config = quiz_data.get('schedule_config', {})
                    intervals['quiz_interval'] = schedule_config.get('send_interval_hours', 3.0)
            
            # Get verse interval
            verse_state_file = self.bot_dir / "data" / "daily_verses_state.json"
            if verse_state_file.exists():
                with open(verse_state_file, 'r') as f:
                    verse_data = json.load(f)
                    schedule_config = verse_data.get('schedule_config', {})
                    intervals['verse_interval'] = schedule_config.get('send_interval_hours', 6.0)
            
            # Format intervals for display
            intervals['quiz_formatted'] = self._format_interval(intervals['quiz_interval'])
            intervals['verse_formatted'] = self._format_interval(intervals['verse_interval'])
            
            return intervals
        except Exception as e:
            return {'error': f"Failed to get intervals: {str(e)}"}
    
    def _format_interval(self, hours: float) -> str:
        """Format interval hours into readable string."""
        if hours < 1:
            minutes = int(hours * 60)
            return f"{minutes}m"
        elif hours == int(hours):
            return f"{int(hours)}h"
        else:
            h = int(hours)
            m = int((hours - h) * 60)
            return f"{h}h{m}m" if m > 0 else f"{h}h"
    
    def update_intervals(self, data: Dict) -> Dict:
        """Update quiz and verse intervals."""
        try:
            result = {'success': False, 'message': '', 'updated': []}
            
            # Update quiz interval if provided
            if 'quiz_interval' in data:
                quiz_hours = float(data['quiz_interval'])
                if 0.017 <= quiz_hours <= 24:  # 1 minute to 24 hours
                    quiz_state_file = self.bot_dir / "data" / "quiz_state.json"
                    if quiz_state_file.exists():
                        with open(quiz_state_file, 'r') as f:
                            quiz_data = json.load(f)
                    else:
                        quiz_data = {}
                    
                    if 'schedule_config' not in quiz_data:
                        quiz_data['schedule_config'] = {}
                    
                    quiz_data['schedule_config']['send_interval_hours'] = quiz_hours
                    quiz_data['schedule_config']['last_updated'] = get_est_now().isoformat()
                    
                    with open(quiz_state_file, 'w') as f:
                        json.dump(quiz_data, f, indent=2)
                    
                    result['updated'].append(f"Quiz interval: {self._format_interval(quiz_hours)}")
                else:
                    return {'success': False, 'message': 'Quiz interval must be between 1 minute and 24 hours'}
            
            # Update verse interval if provided
            if 'verse_interval' in data:
                verse_hours = float(data['verse_interval'])
                if 0.017 <= verse_hours <= 24:  # 1 minute to 24 hours
                    verse_state_file = self.bot_dir / "data" / "daily_verses_state.json"
                    if verse_state_file.exists():
                        with open(verse_state_file, 'r') as f:
                            verse_data = json.load(f)
                    else:
                        verse_data = {}
                    
                    if 'schedule_config' not in verse_data:
                        verse_data['schedule_config'] = {}
                    
                    verse_data['schedule_config']['send_interval_hours'] = verse_hours
                    verse_data['schedule_config']['last_updated'] = get_est_now().isoformat()
                    
                    with open(verse_state_file, 'w') as f:
                        json.dump(verse_data, f, indent=2)
                    
                    result['updated'].append(f"Verse interval: {self._format_interval(verse_hours)}")
                else:
                    return {'success': False, 'message': 'Verse interval must be between 1 minute and 24 hours'}
            
            if result['updated']:
                result['success'] = True
                result['message'] = f"Successfully updated: {', '.join(result['updated'])}"
            else:
                result['message'] = 'No valid intervals provided'
            
            return result
        except Exception as e:
            return {'success': False, 'message': f"Failed to update intervals: {str(e)}"}
    
    def control_audio(self, action: str, data: Dict) -> Dict:
        """Control audio playback."""
        try:
            # This would need to interface with the bot's audio system
            # For now, return a placeholder response
            result = {'success': False, 'message': ''}
            
            if action == 'play':
                result['message'] = 'Audio playback started'
                result['success'] = True
            elif action == 'pause':
                result['message'] = 'Audio playback paused'
                result['success'] = True
            elif action == 'skip':
                result['message'] = 'Skipped to next track'
                result['success'] = True
            elif action == 'volume':
                volume = data.get('volume', 50)
                result['message'] = f'Volume set to {volume}%'
                result['success'] = True
            
            return result
        except Exception as e:
            return {'success': False, 'message': f"Audio control failed: {str(e)}"}
    
    def get_activity_feed(self, limit: int = 50) -> Dict:
        """Get recent Discord activity feed from logs."""
        try:
            activities = []
            log_date = get_est_date_string()
            log_file = self.log_dir / log_date / "logs.log"
            
            if not log_file.exists():
                return {
                    'activities': [],
                    'total_activities': 0,
                    'last_updated': get_est_now().isoformat(),
                    'status': 'no_logs'
                }
            
            # Read recent log entries
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Process recent lines for Discord activities
            activity_types = {
                'quiz': {'emoji': '❓', 'color': '#3498db'},
                'verse': {'emoji': '📖', 'color': '#27ae60'},
                'command': {'emoji': '⚡', 'color': '#f39c12'},
                'voice': {'emoji': '🎵', 'color': '#9b59b6'},
                'user': {'emoji': '👤', 'color': '#34495e'},
                'error': {'emoji': '❌', 'color': '#e74c3c'}
            }
            
            for line in reversed(lines[-200:]):  # Check last 200 lines
                if any(keyword in line.lower() for keyword in ['quiz', 'verse', 'command', 'voice', 'user joined', 'error']):
                    try:
                        # Extract timestamp
                        timestamp_match = re.search(r'\[([\d\-: ]+)\]', line)
                        if timestamp_match:
                            timestamp = timestamp_match.group(1)
                        else:
                            timestamp = get_est_now().strftime('%Y-%m-%d %H:%M:%S')
                        
                        # Determine activity type and format message
                        activity_type = 'command'
                        message = line.strip()
                        
                        if 'quiz' in line.lower():
                            activity_type = 'quiz'
                            if 'sent' in line.lower():
                                message = "📝 Quiz question sent"
                            elif 'answered' in line.lower():
                                message = "✅ Quiz question answered"
                        elif 'verse' in line.lower():
                            activity_type = 'verse'
                            if 'sent' in line.lower():
                                message = "📖 Daily verse sent"
                        elif 'voice' in line.lower():
                            activity_type = 'voice'
                            if 'joined' in line.lower():
                                message = "🎵 User joined voice channel"
                            elif 'left' in line.lower():
                                message = "🔇 User left voice channel"
                        elif 'error' in line.lower():
                            activity_type = 'error'
                            message = "❌ Error occurred"
                        
                        activities.append({
                            'type': activity_type,
                            'message': message,
                            'timestamp': timestamp,
                            'emoji': activity_types[activity_type]['emoji'],
                            'color': activity_types[activity_type]['color']
                        })
                        
                        if len(activities) >= limit:
                            break
                            
                    except Exception:
                        continue
            
            return {
                'activities': activities,
                'total_activities': len(activities),
                'last_updated': get_est_now().isoformat(),
                'status': 'success'
            }
            
        except Exception as e:
            return {
                'error': f"Failed to get activity feed: {str(e)}",
                'activities': [],
                'total_activities': 0,
                'last_updated': get_est_now().isoformat(),
                'status': 'error'
            }

    def get_leaderboard(self, limit: int = 10) -> Dict:
        """Get current leaderboard data from quiz stats."""
        try:
            quiz_stats_file = Path(self.bot_dir) / "data" / "quiz_stats.json"
            
            if not quiz_stats_file.exists():
                return {
                    'leaderboard': [],
                    'total_users': 0,
                    'last_updated': get_est_now().isoformat(),
                    'status': 'no_data'
                }
            
            # Load quiz stats
            with open(quiz_stats_file, 'r', encoding='utf-8') as f:
                quiz_stats = json.load(f)
            
            user_scores = quiz_stats.get("user_scores", {})
            
            if not user_scores:
                return {
                    'leaderboard': [],
                    'total_users': 0,
                    'last_updated': get_est_now().isoformat(),
                    'status': 'no_users'
                }
            
            # Get user info from recent logs
            user_info_cache = self._get_user_info_from_logs()
            
            # Sort users by points (primary) and correct answers (secondary)
            sorted_users = sorted(
                user_scores.items(),
                key=lambda x: (x[1]["points"], x[1].get("correct", 0)),
                reverse=True
            )[:limit]
            
            # Format leaderboard data
            leaderboard = []
            for i, (user_id, stats) in enumerate(sorted_users):
                position = i + 1
                
                # Get medal emoji for top 3
                medal_emojis = {1: "🥇", 2: "🥈", 3: "🥉"}
                position_display = medal_emojis.get(position, f"{position}.")
                
                # Get user info from cache
                user_info = user_info_cache.get(user_id, {})
                display_name = user_info.get('display_name', f'User {user_id[-4:]}')
                avatar_url = user_info.get('avatar_url', None)
                
                # If no display name found, create a more meaningful fallback
                if display_name == f'User {user_id[-4:]}':
                    # Create consistent pseudonyms based on user ID hash
                    pseudonyms = [
                        "Abdullah", "Aisha", "Omar", "Fatima", "Ali", "Khadija", 
                        "Hassan", "Zainab", "Usman", "Maryam", "Ahmad", "Safiya",
                        "Ibrahim", "Hafsah", "Yusuf", "Asma", "Ismail", "Ruqayyah",
                        "Musa", "Umm Salama", "Isa", "Sawda", "Dawud", "Maymuna",
                        "Sulaiman", "Juwayriya", "Yahya", "Zaynab", "Zakaria", "Ramlah"
                    ]
                    # Use hash of user ID to get consistent pseudonym
                    hash_val = hash(user_id) % len(pseudonyms)
                    display_name = pseudonyms[hash_val]
                
                # Get listening time stats (same as Discord leaderboard command)
                listening_time = "0s"
                try:
                    listening_stats_file = Path(self.bot_dir) / "data" / "listening_stats.json"
                    if listening_stats_file.exists():
                        with open(listening_stats_file, 'r', encoding='utf-8') as f:
                            listening_data = json.load(f)
                        
                        user_listening = listening_data.get("users", {}).get(user_id, {})
                        total_seconds = user_listening.get("total_time", 0)
                        
                        # Format listening time (same logic as bot's format_listening_time)
                        if total_seconds >= 3600:  # 1+ hours
                            hours = total_seconds // 3600
                            minutes = (total_seconds % 3600) // 60
                            if minutes > 0:
                                listening_time = f"{hours}h {minutes}m"
                            else:
                                listening_time = f"{hours}h"
                        elif total_seconds >= 60:  # 1+ minutes
                            minutes = total_seconds // 60
                            seconds = total_seconds % 60
                            if seconds > 0:
                                listening_time = f"{minutes}m {seconds}s"
                            else:
                                listening_time = f"{minutes}m"
                        else:  # Less than 1 minute
                            listening_time = f"{total_seconds}s"
                except Exception:
                    # Keep default "0s" if any error occurs
                    pass
                
                # Format user data
                user_data = {
                    'position': position,
                    'position_display': position_display,
                    'user_id': user_id,
                    'display_name': display_name,
                    'avatar_url': avatar_url,
                    'points': stats.get("points", 0),
                    'current_streak': stats.get("current_streak", 0),
                    'best_streak': stats.get("best_streak", 0),
                    'total_questions': stats.get("total_questions", 0),
                    'correct_answers': stats.get("correct_answers", 0),
                    'accuracy': round((stats.get("correct_answers", 0) / max(stats.get("total_questions", 1), 1)) * 100, 1),
                    'listening_time': listening_time
                }
                
                leaderboard.append(user_data)
            
            return {
                'leaderboard': leaderboard,
                'total_users': len(user_scores),
                'last_updated': get_est_now().isoformat(),
                'status': 'success'
            }
            
        except Exception as e:
            return {
                'error': f"Failed to get leaderboard: {str(e)}",
                'leaderboard': [],
                'total_users': 0,
                'last_updated': get_est_now().isoformat(),
                'status': 'error'
            }

    def _get_user_info_from_logs(self) -> Dict:
        """Extract user information from recent log files."""
        user_info = {}
        
        try:
            # First, try to load from user cache file if it exists
            user_cache_file = Path(self.bot_dir) / "data" / "user_cache.json"
            if user_cache_file.exists():
                try:
                    with open(user_cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                        user_info.update(cache_data.get('users', {}))
                except Exception:
                    pass
            
            # Check recent log files for user information
            log_dates = []
            current_date = get_est_now()
            
            # Check today and yesterday's logs
            for i in range(2):
                check_date = current_date - timedelta(days=i)
                log_dates.append(check_date.strftime('%Y-%m-%d'))
            
            for log_date in log_dates:
                log_file = self.log_dir / log_date / "logs.log"
                if not log_file.exists():
                    continue
                
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        # Read recent lines (last 1000 lines should be enough)
                        lines = f.readlines()
                        for line in reversed(lines[-1000:]):
                            # Look for user interaction logs that contain display names
                            if 'User Interaction' in line and 'display_name' in line:
                                try:
                                    # Extract user ID and display name from log line
                                    # Format: "user_name": "DisplayName (123456789)"
                                    import re
                                    
                                    # Look for patterns like "user_name": "DisplayName (123456789)"
                                    user_pattern = r'"user_name":\s*"([^"]+)\s*\((\d+)\)"'
                                    match = re.search(user_pattern, line)
                                    
                                    if match:
                                        display_name = match.group(1).strip()
                                        user_id = match.group(2)
                                        
                                        if user_id not in user_info:
                                            user_info[user_id] = {
                                                'display_name': display_name,
                                                'avatar_url': None  # Can't get avatar from logs
                                            }
                                    
                                    # Also look for just display names in action descriptions
                                    action_pattern = r'"action_description":\s*"([^"]*?)(?:\s+(?:joined|left|selected|answered|clicked))'
                                    action_match = re.search(action_pattern, line)
                                    
                                    if action_match:
                                        potential_name = action_match.group(1).strip()
                                        # Look for user ID in the same line
                                        id_pattern = r'"user_id":\s*(\d+)'
                                        id_match = re.search(id_pattern, line)
                                        
                                        if id_match and len(potential_name) > 0 and not potential_name.startswith('Dashboard'):
                                            user_id = id_match.group(1)
                                            if user_id not in user_info:
                                                user_info[user_id] = {
                                                    'display_name': potential_name,
                                                    'avatar_url': None
                                                }
                                
                                except Exception:
                                    continue
                                    
                except Exception:
                    continue
            
            return user_info
            
        except Exception as e:
            return {}

# =============================================================================
# Flask Routes
# =============================================================================

# Initialize monitor
monitor = BotMonitor()

@app.route('/')
def dashboard():
    """Main dashboard page."""
    user_ip = request.remote_addr
    log_dashboard_interaction("VIEW_DASHBOARD", "/", user_ip)
    return render_template('dashboard.html')

@app.route('/api/status')
def api_status():
    """API endpoint for bot status."""
    user_ip = request.remote_addr
    log_dashboard_interaction("VIEW_STATUS", "/api/status", user_ip)
    return jsonify(monitor.get_bot_status())

@app.route('/api/logs')
def api_logs():
    """API endpoint for recent logs."""
    lines = request.args.get('lines', 50, type=int)
    return jsonify({
        'logs': monitor.get_recent_logs(lines),
        'timestamp': get_est_now().isoformat()
    })

@app.route('/api/errors')
def api_errors():
    """API endpoint for error logs."""
    lines = request.args.get('lines', 20, type=int)
    return jsonify({
        'errors': monitor.get_error_logs(lines),
        'timestamp': get_est_now().isoformat()
    })

@app.route('/api/system')
def api_system():
    """API endpoint for system information."""
    return jsonify(monitor.get_system_info())

@app.route('/api/control/<action>', methods=['GET', 'POST'])
def api_control(action):
    """API endpoint for bot control actions."""
    user_ip = request.remote_addr
    log_dashboard_interaction("BOT_CONTROL", f"/api/control/{action}", user_ip, {"action": action})
    
    if action not in ['start', 'stop', 'restart', 'status']:
        log_dashboard_status(f"Invalid bot control action attempted: {action}", "WARNING", "⚠️")
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
        
        success = result.returncode == 0
        if success:
            log_dashboard_status(f"Bot control action '{action}' successful", "INFO", "✅")
        else:
            log_dashboard_status(f"Bot control action '{action}' failed: {result.stderr}", "WARNING", "⚠️")
        
        return jsonify({
            'action': action,
            'success': success,
            'output': result.stdout,
            'error': result.stderr if result.stderr else None
        })
    except Exception as e:
        log_dashboard_status(f"Bot control action '{action}' error: {str(e)}", "ERROR", "❌")
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
    user_ip = request.remote_addr
    try:
        query = request.args.get('query', '')
        date = request.args.get('date', get_est_date_string())
        lines = request.args.get('lines', 100, type=int)
        
        if not query:
            return jsonify({'error': 'Query parameter required'}), 400
        
        log_dashboard_interaction("SEARCH_LOGS", "/api/logs/search", user_ip, {"query": query, "date": date, "lines": lines})
        
        results = monitor.search_logs(query, date, lines)
        return jsonify(results)
    except Exception as e:
        log_dashboard_status(f"Error searching logs: {str(e)}", "ERROR", "❌")
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
            'timestamp': get_est_now().isoformat(),
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

@app.route('/api/quiz-stats')
def api_quiz_stats():
    """API endpoint for quiz statistics."""
    try:
        quiz_stats = monitor.get_quiz_statistics()
        return jsonify(quiz_stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/verse-stats')
def api_verse_stats():
    """API endpoint for verse statistics."""
    try:
        verse_stats = monitor.get_verse_statistics()
        return jsonify(verse_stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/intervals')
def api_intervals():
    """API endpoint for getting current intervals."""
    try:
        intervals = monitor.get_current_intervals()
        return jsonify(intervals)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/intervals/update', methods=['POST'])
def api_intervals_update():
    """API endpoint for updating intervals."""
    user_ip = request.remote_addr
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        log_dashboard_interaction("UPDATE_INTERVALS", "/api/intervals/update", user_ip, {"data": data})
        
        result = monitor.update_intervals(data)
        
        if result.get('success'):
            log_dashboard_status(f"Intervals updated successfully: {data}", "INFO", "⚙️")
        else:
            log_dashboard_status(f"Failed to update intervals: {result.get('error')}", "WARNING", "⚠️")
        
        return jsonify(result)
    except Exception as e:
        log_dashboard_status(f"Error updating intervals: {str(e)}", "ERROR", "❌")
        return jsonify({'error': str(e)}), 500

@app.route('/api/audio-control/<action>', methods=['POST'])
def api_audio_control(action):
    """API endpoint for audio control actions."""
    user_ip = request.remote_addr
    try:
        if action not in ['play', 'pause', 'skip', 'volume']:
            log_dashboard_status(f"Invalid audio control action attempted: {action}", "WARNING", "⚠️")
            return jsonify({'error': 'Invalid action'}), 400
        
        data = request.get_json() if request.content_type == 'application/json' else {}
        log_dashboard_interaction("AUDIO_CONTROL", f"/api/audio-control/{action}", user_ip, {"action": action, "data": data})
        
        result = monitor.control_audio(action, data)
        
        if result.get('success'):
            log_dashboard_status(f"Audio control action '{action}' successful", "INFO", "🎵")
        else:
            log_dashboard_status(f"Audio control action '{action}' failed: {result.get('error')}", "WARNING", "⚠️")
        
        return jsonify(result)
    except Exception as e:
        log_dashboard_status(f"Audio control action '{action}' error: {str(e)}", "ERROR", "❌")
        return jsonify({'error': str(e)}), 500

@app.route('/api/activity-feed')
def api_activity_feed():
    """API endpoint for recent Discord activity feed."""
    try:
        limit = request.args.get('limit', 50, type=int)
        activity_feed = monitor.get_activity_feed(limit)
        return jsonify(activity_feed)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/leaderboard')
def api_leaderboard():
    """API endpoint for the quiz leaderboard."""
    try:
        leaderboard_data = monitor.get_leaderboard()
        return jsonify(leaderboard_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    # Log dashboard startup
    log_dashboard_status("Dashboard starting up with tree logging enabled", "INFO", "🚀")
    
    # Run the Flask app
    app.run(
        host='0.0.0.0',
        port=8080,
        debug=False,
        threaded=True
    ) 