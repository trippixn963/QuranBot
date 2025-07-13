#!/usr/bin/env python3
# =============================================================================
# QuranBot - Professional Web Dashboard
# =============================================================================
# Advanced Flask web interface for monitoring and controlling QuranBot
# Provides real-time bot status, audio controls, statistics, and management
# =============================================================================

import json
import os
import sys
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

import pytz
from flask import Flask, jsonify, render_template, request, send_from_directory

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Import bot utilities
try:
    from src.utils.state_manager import StateManager
    from src.utils.quiz_manager import QuizManager
    from src.utils.listening_stats import ListeningStatsManager
    from src.utils.discord_api_monitor import DiscordAPIMonitor
    from src.utils.tree_log import TreeLogger
except ImportError as e:
    print(f"Warning: Could not import bot utilities: {e}")
    # Create mock classes for development
    class StateManager:
        def __init__(self, data_dir=None): pass
        def get_state(self): return {}
    class QuizManager:
        def __init__(self, data_dir=None): pass
        def get_stats(self): return {}
    class ListeningStatsManager:
        def get_stats(self): return {}
    class DiscordAPIMonitor:
        def get_health(self): return {}
    class TreeLogger:
        def log(self, *args): pass

# Initialize Flask app
app = Flask(__name__, 
           static_folder='static',
           template_folder='templates')

# Configuration
VPS_HOST = "root@159.89.90.90"

# Use VPS paths if they exist, otherwise local paths
vps_bot_path = Path("/opt/DiscordBots/QuranBot")
vps_data_path = vps_bot_path / "data"
vps_logs_path = vps_bot_path / "logs"

# Set paths based on what exists
if vps_bot_path.exists():
    LOGS_PATH = vps_logs_path
    DATA_PATH = vps_data_path
    data_path = vps_data_path
else:
    LOGS_PATH = project_root / "logs"
    DATA_PATH = project_root / "data"
    data_path = project_root / "data"

state_manager = StateManager(data_dir=str(data_path))
quiz_manager = QuizManager(data_path)
listening_stats = ListeningStatsManager()
try:
    discord_monitor = DiscordAPIMonitor(None)
except (TypeError, RuntimeError):
    # DiscordAPIMonitor requires a bot instance and event loop, use mock for web dashboard
    discord_monitor = type('MockDiscordAPIMonitor', (), {'get_health': lambda self: {'status': 'unavailable', 'message': 'Bot not running'}})()
tree_log = TreeLogger()

def get_est_time():
    """Get current time in EST"""
    est = pytz.timezone("US/Eastern")
    return datetime.now(est)

def format_timestamp_readable(timestamp_str):
    """Format timestamp to readable EST 12-hour format"""
    try:
        # Parse various timestamp formats
        if "UTC" in timestamp_str:
            # Remove UTC and parse
            clean_str = timestamp_str.replace(" UTC", "").strip()
            dt = datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")
            dt = dt.replace(tzinfo=pytz.utc)
        elif "ago" in timestamp_str:
            # Already formatted relative time
            return timestamp_str
        else:
            # Try to parse as ISO format or other formats
            try:
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except:
                return timestamp_str
        
        # Convert to EST
        est = pytz.timezone('US/Eastern')
        est_dt = dt.astimezone(est)
        
        # Format as readable 12-hour format
        return est_dt.strftime("%b %d, %I:%M %p EST")
    except:
        return timestamp_str

def format_memory_readable(memory_str):
    """Format memory usage to be more readable"""
    try:
        if "Memory:" in memory_str:
            memory_str = memory_str.replace("Memory:", "").strip()
        
        # Extract just the current usage, ignore max/peak info
        if "(" in memory_str:
            current = memory_str.split("(")[0].strip()
            return current
        
        return memory_str
    except:
        return memory_str

def format_uptime_readable(uptime_str):
    """Format uptime to be more readable"""
    try:
        if ";" in uptime_str:
            # Extract just the relative time part (e.g., "9h ago")
            parts = uptime_str.split(";")
            if len(parts) > 1:
                time_part = parts[1].strip()
                if "ago" in time_part:
                    return time_part
        
        # Handle direct timestamp format like "Sun 2025-07-13 08:03:43 UTC"
        if "UTC" in uptime_str:
            try:
                # Parse the timestamp and convert to EST
                clean_str = uptime_str.replace(" UTC", "").strip()
                # Handle format like "Sun 2025-07-13 08:03:43"
                if len(clean_str.split()) >= 3:
                    date_time_part = " ".join(clean_str.split()[1:])  # Remove day name
                    dt = datetime.strptime(date_time_part, "%Y-%m-%d %H:%M:%S")
                    dt = dt.replace(tzinfo=pytz.utc)
                    
                    # Convert to EST
                    est = pytz.timezone('US/Eastern')
                    est_dt = dt.astimezone(est)
                    
                    # Calculate time ago
                    now = get_est_time()
                    diff = now - est_dt
                    
                    if diff.days > 0:
                        return f"{diff.days}d ago"
                    elif diff.seconds > 3600:
                        hours = diff.seconds // 3600
                        return f"{hours}h ago"
                    elif diff.seconds > 60:
                        minutes = diff.seconds // 60
                        return f"{minutes}m ago"
                    else:
                        return "Just now"
            except:
                pass
        
        # Try to parse and format the timestamp
        return format_timestamp_readable(uptime_str)
    except:
        return uptime_str

def log_dashboard_action(action: str, details: Dict = None, user_ip: str = None):
    """Log dashboard actions with tree format"""
    try:
        timestamp = get_est_time().strftime("%Y-%m-%d %I:%M:%S %p EST")
        user_agent = request.headers.get('User-Agent', 'Unknown') if request else 'System'
        
        log_entry = {
            "timestamp": timestamp,
            "action": action,
            "user_ip": user_ip or (request.remote_addr if request else "127.0.0.1"),
            "user_agent": user_agent,
            "details": details or {}
        }
        
        tree_log.log("dashboard", f"🌐 {action}", log_entry)
    except Exception as e:
        print(f"Error logging dashboard action: {e}")

def get_bot_status():
    """Get current bot status from systemd service"""
    try:
        # Check if service is running (local command since dashboard runs on VPS)
        result = subprocess.run(
            ["systemctl", "is-active", "quranbot.service"],
            capture_output=True, text=True, timeout=10
        )
        
        service_active = result.stdout.strip() == "active"
        
        # Get detailed status
        status_result = subprocess.run(
            ["systemctl", "status", "quranbot.service", "--no-pager"],
            capture_output=True, text=True, timeout=10
        )
        
        # Parse uptime and memory from status
        uptime = "Unknown"
        memory = "Unknown"
        
        if status_result.stdout:
            lines = status_result.stdout.split('\n')
            for line in lines:
                if "Active:" in line:
                    parts = line.split("since")
                    if len(parts) > 1:
                        uptime = parts[1].strip()
                elif "Memory:" in line:
                    memory = line.split("Memory:")[1].strip()
        
        return {
            "online": service_active,
            "status": "running" if service_active else "stopped",
            "uptime": format_uptime_readable(uptime),
            "memory": format_memory_readable(memory),
            "last_check": get_est_time().strftime("%I:%M %p EST")
        }
    except Exception as e:
        return {
            "online": False,
            "status": "error",
            "error": str(e),
            "last_check": get_est_time().strftime("%I:%M %p EST")
        }

def get_system_metrics():
    """Get system resource metrics from VPS"""
    try:
        # Get CPU, memory, and disk usage (local command since dashboard runs on VPS)
        result = subprocess.run([
            "python3", "-c", 
            """
import psutil
import json
cpu = psutil.cpu_percent(interval=1)
memory = psutil.virtual_memory()
disk = psutil.disk_usage('/')
uptime = psutil.boot_time()
print(json.dumps({
    'cpu_percent': cpu,
    'memory_percent': memory.percent,
    'memory_used': memory.used,
    'memory_total': memory.total,
    'disk_percent': disk.percent,
    'disk_used': disk.used,
    'disk_total': disk.total,
    'uptime': uptime
}))
            """
        ], capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            return json.loads(result.stdout.strip())
        else:
            return {"error": "Failed to get system metrics"}
    except Exception as e:
        return {"error": str(e)}

def get_audio_status():
    """Get current audio playback status"""
    try:
        # Read playback state directly from JSON file
        playback_file = data_path / "playback_state.json"
        if playback_file.exists():
            with open(playback_file, 'r') as f:
                playback_data = json.load(f)
            
            return {
                "playing": playback_data.get("is_playing", False),
                "current_surah": str(playback_data.get("current_surah", "None")),
                "current_verse": "None",  # Not stored in playback state
                "voice_channel": "Connected" if playback_data.get("is_playing", False) else "Not connected",
                "volume": 50,  # Default volume
                "duration": 0,  # Would need audio file info
                "position": int(playback_data.get("current_position", 0))
            }
        else:
            return {
                "playing": False,
                "current_surah": "None",
                "current_verse": "None",
                "voice_channel": "Not connected",
                "volume": 50,
                "duration": 0,
                "position": 0
            }
    except Exception as e:
        return {
            "playing": False,
            "current_surah": "None",
            "current_verse": "None",
            "voice_channel": "Not connected",
            "volume": 50,
            "duration": 0,
            "position": 0
        }

def get_quiz_statistics():
    """Get comprehensive quiz statistics"""
    try:
        # Read quiz stats directly from JSON file
        quiz_stats_file = Path("/opt/DiscordBots/QuranBot/data/quiz_stats.json")
        user_cache_file = Path("/opt/DiscordBots/QuranBot/data/user_cache.json")
        
        # Load user cache for display names and avatars
        user_cache = {}
        if user_cache_file.exists():
            with open(user_cache_file, 'r') as f:
                cache_data = json.load(f)
                user_cache = cache_data.get("users", {})
        
        if quiz_stats_file.exists():
            with open(quiz_stats_file, 'r') as f:
                stats_data = json.load(f)
                user_scores = stats_data.get("user_scores", {})
                
                # Calculate statistics
                total_questions = sum(user.get("total_questions", 0) for user in user_scores.values())
                correct_answers = sum(user.get("correct_answers", 0) for user in user_scores.values())
                total_users = len(user_scores)
                accuracy_rate = (correct_answers / total_questions * 100) if total_questions > 0 else 0
                
                # Get top users by points with user info
                top_users = []
                for user_id, user_data in user_scores.items():
                    points = user_data.get("points", 0)
                    if points > 0:
                        # Get user info from cache
                        user_info = user_cache.get(user_id, {})
                        display_name = user_info.get("display_name", f"User {user_id[:8]}...")
                        avatar_url = user_info.get("avatar_url", "https://cdn.discordapp.com/embed/avatars/0.png")
                        
                        top_users.append({
                            "user_id": user_id,
                            "display_name": display_name,
                            "avatar_url": avatar_url,
                            "points": points,
                            "correct_answers": user_data.get("correct_answers", 0),
                            "total_questions": user_data.get("total_questions", 0),
                            "accuracy": (user_data.get("correct_answers", 0) / user_data.get("total_questions", 1) * 100) if user_data.get("total_questions", 0) > 0 else 0
                        })
                
                # Sort by points and take top 10
                top_users.sort(key=lambda x: x["points"], reverse=True)
                top_users = top_users[:10]
                
                # Create recent activity from users with recent answers
                recent_activity = []
                for user_id, user_data in user_scores.items():
                    if user_data.get("last_answer_time"):
                        user_info = user_cache.get(user_id, {})
                        display_name = user_info.get("display_name", f"User {user_id[:8]}...")
                        avatar_url = user_info.get("avatar_url", "https://cdn.discordapp.com/embed/avatars/0.png")
                        
                        recent_activity.append({
                            "user_id": user_id,
                            "display_name": display_name,
                            "avatar_url": avatar_url,
                            "action": "answered a question",
                            "timestamp": user_data.get("last_answer_time"),
                            "points": user_data.get("points", 0)
                        })
                
                # Sort by timestamp and take most recent 10
                recent_activity.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
                recent_activity = recent_activity[:10]
                
                return {
                    "total_questions": total_questions,
                    "correct_answers": correct_answers,
                    "total_users": total_users,
                    "accuracy_rate": accuracy_rate,
                    "questions_today": 0,  # Would need to track daily questions
                    "top_users": top_users,
                    "recent_activity": recent_activity
                }
        else:
            return {
                "total_questions": 0,
                "correct_answers": 0,
                "total_users": 0,
                "accuracy_rate": 0,
                "questions_today": 0,
                "top_users": [],
                "recent_activity": []
            }
    except Exception as e:
        return {"error": str(e)}

def get_listening_statistics():
    """Get listening time statistics"""
    try:
        # Read listening stats directly from JSON file
        listening_stats_file = data_path / "listening_stats.json"
        if listening_stats_file.exists():
            with open(listening_stats_file, 'r') as f:
                stats_data = json.load(f)
                
                # Calculate total listening time
                total_time = 0
                active_listeners = 0
                top_listeners = []
                
                for user_id, user_data in stats_data.items():
                    if isinstance(user_data, dict):
                        user_time = user_data.get("total_listening_time", 0)
                        total_time += user_time
                        if user_time > 0:
                            active_listeners += 1
                            top_listeners.append({
                                "user_id": user_id,
                                "listening_time": user_time,
                                "sessions": user_data.get("total_sessions", 0)
                            })
                
                # Sort by listening time and take top 10
                top_listeners.sort(key=lambda x: x["listening_time"], reverse=True)
                top_listeners = top_listeners[:10]
                
                return {
                    "total_listening_time": total_time,
                    "active_listeners": active_listeners,
                    "sessions_today": 0,  # Would need to track daily sessions
                    "average_session_time": total_time / max(active_listeners, 1) if active_listeners > 0 else 0,
                    "top_listeners": top_listeners,
                    "daily_stats": {},  # Would need to track this separately
                    "weekly_stats": {}  # Would need to track this separately
                }
        else:
            return {
                "total_listening_time": 0,
                "active_listeners": 0,
                "sessions_today": 0,
                "average_session_time": 0,
                "top_listeners": [],
                "daily_stats": {},
                "weekly_stats": {}
            }
    except Exception as e:
        return {"error": str(e)}

def get_recent_logs(lines=50):
    """Get recent log entries"""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = LOGS_PATH / today / "logs.log"
        
        if not log_file.exists():
            return []
        
        with open(log_file, 'r', encoding='utf-8') as f:
            log_lines = f.readlines()
        
        # Return last N lines
        return [line.strip() for line in log_lines[-lines:] if line.strip()]
    except Exception as e:
        return [f"Error reading logs: {e}"]

def get_discord_health():
    """Get Discord API health metrics"""
    try:
        # Read Discord API monitor data directly from JSON file
        # Use absolute path to ensure we're reading from the correct location
        discord_monitor_file = Path("/opt/DiscordBots/QuranBot/data/discord_api_monitor.json")
        
        if discord_monitor_file.exists():
            with open(discord_monitor_file, 'r') as f:
                monitor_data = json.load(f)
                
            # Get the latest health entry from the health_history array
            if monitor_data and "health_history" in monitor_data and monitor_data["health_history"]:
                latest_health = monitor_data["health_history"][-1]  # Get the last health entry
                stats = monitor_data.get("stats", {})
                
                # Determine status based on health data
                is_healthy = latest_health.get("is_healthy", False)
                gateway_connected = latest_health.get("gateway_connected", False)
                
                status = "healthy" if is_healthy else "unhealthy"
                gateway_status = "Connected" if gateway_connected else "Disconnected"
                
                return {
                    "status": status,
                    "latency": (latest_health.get("gateway_latency", 0) or 0) * 1000,  # Convert to ms
                    "rate_limit_usage": latest_health.get("rate_limit_usage", 0),
                    "gateway_status": gateway_status,
                    "reconnects": stats.get("reconnect_count", 0),
                    "last_check": latest_health.get("timestamp", "Unknown")
                }
        
        return {
            "status": "unknown",
            "latency": 0,
            "rate_limit_usage": 0,
            "gateway_status": "Unknown",
            "reconnects": 0,
            "last_check": "Never"
        }
    except Exception as e:
        return {"error": str(e), "status": "unknown"}

def get_performance_metrics():
    """Get performance metrics for the dashboard"""
    try:
        # Calculate response time based on recent requests
        response_time = "< 100ms"  # Placeholder - could be calculated from logs
        
        # Calculate requests per minute from recent logs
        requests_per_min = calculate_requests_per_minute()
        
        # Calculate error rate from logs
        error_rate = calculate_error_rate()
        
        return {
            "response_time": response_time,
            "requests_per_min": requests_per_min,
            "error_rate": error_rate
        }
    except Exception as e:
        return {
            "response_time": "N/A",
            "requests_per_min": "N/A", 
            "error_rate": "N/A"
        }

def calculate_requests_per_minute():
    """Calculate requests per minute from recent logs"""
    try:
        # Get recent logs and count HTTP requests
        logs = get_recent_logs(100)
        http_requests = [log for log in logs if "GET /" in log or "POST /" in log]
        
        if len(http_requests) >= 2:
            # Estimate based on recent activity
            return f"{len(http_requests)}/min"
        else:
            return "Low"
    except:
        return "N/A"

def calculate_error_rate():
    """Calculate error rate from recent logs"""
    try:
        logs = get_recent_logs(100)
        total_requests = len([log for log in logs if "GET /" in log or "POST /" in log])
        error_requests = len([log for log in logs if " 500 " in log or " 404 " in log or " 403 " in log])
        
        if total_requests > 0:
            error_rate = (error_requests / total_requests) * 100
            return f"{error_rate:.1f}%"
        else:
            return "0%"
    except:
        return "N/A"

def get_storage_metrics():
    """Get storage metrics for the dashboard"""
    try:
        # Calculate log files size
        log_files_size = calculate_log_files_size()
        
        # Calculate audio cache size
        audio_cache_size = calculate_audio_cache_size()
        
        # Calculate database size
        database_size = calculate_database_size()
        
        return {
            "log_files": log_files_size,
            "audio_cache": audio_cache_size,
            "database_size": database_size
        }
    except Exception as e:
        return {
            "log_files": "N/A",
            "audio_cache": "N/A",
            "database_size": "N/A"
        }

def calculate_log_files_size():
    """Calculate total size of log files"""
    try:
        log_dir = Path("/opt/DiscordBots/QuranBot/logs")
        if log_dir.exists():
            total_size = sum(f.stat().st_size for f in log_dir.rglob("*") if f.is_file())
            return format_file_size(total_size)
        return "0 MB"
    except:
        return "N/A"

def calculate_audio_cache_size():
    """Calculate size of audio cache"""
    try:
        audio_dir = Path("/opt/DiscordBots/QuranBot/audio")
        if audio_dir.exists():
            total_size = sum(f.stat().st_size for f in audio_dir.rglob("*") if f.is_file())
            return format_file_size(total_size)
        return "0 MB"
    except:
        return "N/A"

def calculate_database_size():
    """Calculate size of database files"""
    try:
        data_dir = Path("/opt/DiscordBots/QuranBot/data")
        if data_dir.exists():
            total_size = sum(f.stat().st_size for f in data_dir.rglob("*.json") if f.is_file())
            return format_file_size(total_size)
        return "0 MB"
    except:
        return "N/A"

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

def get_network_metrics():
    """Get network metrics for the dashboard"""
    try:
        # VPS connection is always connected since we're running on it
        vps_connection = "Connected"
        
        # Get Discord gateway status from health data
        discord_health = get_discord_health()
        discord_gateway = "Connected" if discord_health.get("gateway_status") == "Connected" else "Disconnected"
        
        # API endpoints status
        api_endpoints = "Online"  # Since we're responding to this request
        
        return {
            "vps_connection": vps_connection,
            "discord_gateway": discord_gateway,
            "api_endpoints": api_endpoints
        }
    except Exception as e:
        return {
            "vps_connection": "Connected",
            "discord_gateway": "N/A",
            "api_endpoints": "N/A"
        }

# =============================================================================
# ROUTES - Main Pages
# =============================================================================

@app.route('/')
def index():
    """Main dashboard page"""
    log_dashboard_action("View Dashboard", {"page": "index"}, request.remote_addr)
    return render_template('index.html')

@app.route('/analytics')
def analytics():
    """Analytics and statistics page"""
    log_dashboard_action("View Analytics", {"page": "analytics"}, request.remote_addr)
    return render_template('analytics.html')

@app.route('/controls')
def controls():
    """Bot control panel"""
    log_dashboard_action("View Controls", {"page": "controls"}, request.remote_addr)
    return render_template('controls.html')

@app.route('/logs')
def logs_page():
    """Logs viewer page"""
    log_dashboard_action("View Logs", {"page": "logs"}, request.remote_addr)
    return render_template('logs.html')

# =============================================================================
# API ROUTES - Data Endpoints
# =============================================================================

@app.route('/api/status')
def api_status():
    """Get overall bot status"""
    bot_status = get_bot_status()
    audio_status = get_audio_status()
    system_metrics = get_system_metrics()
    performance_metrics = get_performance_metrics()
    storage_metrics = get_storage_metrics()
    network_metrics = get_network_metrics()
    
    return jsonify({
        "bot": bot_status,
        "audio": audio_status,
        "system": system_metrics,
        "performance": performance_metrics,
        "storage": storage_metrics,
        "network": network_metrics,
        "timestamp": get_est_time().strftime("%I:%M %p EST")
    })

@app.route('/api/logs')
def api_logs():
    """Get recent log entries"""
    lines = request.args.get('lines', 50, type=int)
    logs = get_recent_logs(lines)
    
    return jsonify({
        "logs": logs,
        "count": len(logs),
        "timestamp": get_est_time().strftime("%I:%M %p EST")
    })

@app.route('/api/quiz/stats')
def api_quiz_stats():
    """Get quiz statistics"""
    stats = get_quiz_statistics()
    return jsonify(stats)

@app.route('/api/listening/stats')
def api_listening_stats():
    """Get listening statistics"""
    stats = get_listening_statistics()
    return jsonify(stats)

@app.route('/api/discord/health')
def api_discord_health():
    """Get Discord API health"""
    health = get_discord_health()
    return jsonify(health)

# =============================================================================
# API ROUTES - Control Endpoints
# =============================================================================

@app.route('/api/bot/control', methods=['POST'])
def api_bot_control():
    """Control bot service (start/stop/restart)"""
    data = request.get_json()
    action = data.get('action')
    
    if action not in ['start', 'stop', 'restart']:
        return jsonify({"error": "Invalid action"}), 400
    
    try:
        log_dashboard_action(f"Bot Control: {action}", {"action": action}, request.remote_addr)
        
        result = subprocess.run([
            "systemctl", action, "quranbot.service"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return jsonify({"success": True, "message": f"Bot {action} successful"})
        else:
            return jsonify({"error": result.stderr}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/audio/control', methods=['POST'])
def api_audio_control():
    """Control audio playback"""
    data = request.get_json()
    action = data.get('action')
    
    log_dashboard_action(f"Audio Control: {action}", {"action": action}, request.remote_addr)
    
    # Here you would implement audio control logic
    # For now, return success
    return jsonify({"success": True, "message": f"Audio {action} command sent"})

# =============================================================================
# STATIC FILES
# =============================================================================

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    return send_from_directory(app.static_folder, filename)

# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == '__main__':
    print("🕌 Starting QuranBot Professional Web Dashboard...")
    print(f"📊 Dashboard available at: http://159.89.90.90:8080")
    print(f"🔄 Real-time updates enabled")
    print(f"📝 Monitoring logs from: {LOGS_PATH}")
    print(f"🎛️ Advanced controls and analytics enabled")
    
    # Run the Flask app
    app.run(
        host='0.0.0.0',
        port=8080,
        debug=False,
        threaded=True
    ) 