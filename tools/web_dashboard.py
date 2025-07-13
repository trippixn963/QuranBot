#!/usr/bin/env python3
# =============================================================================
# QuranBot - Web Dashboard
# =============================================================================
# Simple Flask web interface for monitoring QuranBot status
# Provides real-time bot status, audio playback info, and system health
# =============================================================================

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pytz
from flask import Flask, jsonify, render_template_string

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

app = Flask(__name__)

# Configuration
VPS_HOST = "root@159.89.90.90"
LOGS_PATH = project_root / "logs"
DATA_PATH = project_root / "data"

def get_est_time():
    """Get current time in EST"""
    est = pytz.timezone("US/Eastern")
    return datetime.now(est)

def get_latest_log_file():
    """Get the latest log file path"""
    today = get_est_time().strftime("%Y-%m-%d")
    log_file = LOGS_PATH / today / f"{today}.log"
    return log_file if log_file.exists() else None

def get_bot_status():
    """Get current bot status from logs"""
    try:
        import subprocess
        result = subprocess.run(
            ["ssh", VPS_HOST, "systemctl is-active quranbot.service"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return "active" in result.stdout.lower()
    except:
        return False

def get_audio_status():
    """Get current audio playback status"""
    try:
        import subprocess
        result = subprocess.run(
            ["ssh", VPS_HOST, "ps aux | grep ffmpeg | grep -v grep"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return bool(result.stdout.strip())
    except:
        return False

def get_current_surah():
    """Get current surah from state files"""
    try:
        state_file = project_root / "data" / "playback_state.json"
        if state_file.exists():
            with open(state_file, 'r') as f:
                data = json.load(f)
                return data.get("current_surah", "Unknown")
    except:
        pass
    return "Unknown"

def get_recent_logs(lines=10):
    """Get recent log entries"""
    log_file = get_latest_log_file()
    if not log_file:
        return ["No logs available for today"]
    
    try:
        with open(log_file, 'r') as f:
            all_lines = f.readlines()
            return [line.strip() for line in all_lines[-lines:]]
    except:
        return ["Error reading logs"]

def get_system_uptime():
    """Get system uptime"""
    try:
        import subprocess
        result = subprocess.run(
            ["ssh", VPS_HOST, "uptime -p"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout.strip().replace("up ", "")
    except:
        return "Unknown"

# Dashboard HTML template
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QuranBot Dashboard</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            margin: 0;
            font-size: 2.5rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .header p {
            margin: 10px 0 0 0;
            opacity: 0.9;
            font-size: 1.1rem;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .card h3 {
            margin: 0 0 15px 0;
            font-size: 1.3rem;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            display: inline-block;
        }
        .status-online { background: #4CAF50; }
        .status-offline { background: #f44336; }
        .status-warning { background: #ff9800; }
        .info-item {
            margin: 10px 0;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        .info-item:last-child {
            border-bottom: none;
        }
        .info-label {
            font-weight: 600;
            opacity: 0.8;
        }
        .info-value {
            margin-top: 5px;
            font-size: 1.1rem;
        }
        .logs-container {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 10px;
            padding: 20px;
            font-family: 'Courier New', monospace;
            font-size: 0.9rem;
            max-height: 300px;
            overflow-y: auto;
        }
        .log-line {
            margin: 5px 0;
            opacity: 0.9;
        }
        .refresh-info {
            text-align: center;
            opacity: 0.7;
            margin-top: 20px;
        }
        .timestamp {
            opacity: 0.6;
            font-size: 0.9rem;
        }
    </style>
    <script>
        // Auto-refresh every 30 seconds
        setTimeout(() => {
            window.location.reload();
        }, 30000);
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🕌 QuranBot Dashboard</h1>
            <p>Real-time monitoring and status</p>
            <p class="timestamp">Last updated: {{ timestamp }}</p>
        </div>
        
        <div class="grid">
            <div class="card">
                <h3>
                    🤖 Bot Status
                    <span class="status-indicator {{ 'status-online' if bot_status else 'status-offline' }}"></span>
                </h3>
                <div class="info-item">
                    <div class="info-label">Service Status</div>
                    <div class="info-value">{{ 'Online' if bot_status else 'Offline' }}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">System Uptime</div>
                    <div class="info-value">{{ uptime }}</div>
                </div>
            </div>
            
            <div class="card">
                <h3>
                    🎵 Audio Status
                    <span class="status-indicator {{ 'status-online' if audio_status else 'status-offline' }}"></span>
                </h3>
                <div class="info-item">
                    <div class="info-label">Playback Status</div>
                    <div class="info-value">{{ 'Playing' if audio_status else 'Stopped' }}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Current Surah</div>
                    <div class="info-value">{{ current_surah }}</div>
                </div>
            </div>
            
            <div class="card">
                <h3>
                    📊 System Health
                    <span class="status-indicator {{ 'status-online' if (bot_status and audio_status) else 'status-warning' if bot_status else 'status-offline' }}"></span>
                </h3>
                <div class="info-item">
                    <div class="info-label">Overall Status</div>
                    <div class="info-value">
                        {% if bot_status and audio_status %}
                            ✅ Healthy
                        {% elif bot_status %}
                            ⚠️ Audio Issues
                        {% else %}
                            ❌ Offline
                        {% endif %}
                    </div>
                </div>
                <div class="info-item">
                    <div class="info-label">VPS Connection</div>
                    <div class="info-value">{{ 'Connected' if bot_status else 'Disconnected' }}</div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h3>📝 Recent Logs</h3>
            <div class="logs-container">
                {% for log in recent_logs %}
                <div class="log-line">{{ log }}</div>
                {% endfor %}
            </div>
        </div>
        
        <div class="refresh-info">
            <p>Dashboard auto-refreshes every 30 seconds</p>
            <p>QuranBot VPS Dashboard • Serving the Islamic community 24/7</p>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def dashboard():
    """Main dashboard page"""
    # Get current status
    bot_status = get_bot_status()
    audio_status = get_audio_status()
    current_surah = get_current_surah()
    uptime = get_system_uptime()
    recent_logs = get_recent_logs(15)
    
    # Get current EST time
    est_time = get_est_time().strftime("%Y-%m-%d %I:%M:%S %p EST")
    
    return render_template_string(
        DASHBOARD_HTML,
        bot_status=bot_status,
        audio_status=audio_status,
        current_surah=current_surah,
        uptime=uptime,
        recent_logs=recent_logs,
        timestamp=est_time
    )

@app.route('/api/status')
def api_status():
    """API endpoint for status"""
    return jsonify({
        'bot_status': get_bot_status(),
        'audio_status': get_audio_status(),
        'current_surah': get_current_surah(),
        'uptime': get_system_uptime(),
        'timestamp': get_est_time().isoformat()
    })

@app.route('/api/logs')
def api_logs():
    """API endpoint for recent logs"""
    return jsonify({
        'logs': get_recent_logs(20),
        'timestamp': get_est_time().isoformat()
    })

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': get_est_time().isoformat()
    })

if __name__ == '__main__':
    print("🕌 Starting QuranBot Dashboard...")
    print(f"📊 Dashboard will be available at: http://localhost:8080")
    print(f"🔄 Auto-refresh enabled every 30 seconds")
    print(f"📝 Monitoring logs from: {LOGS_PATH}")
    
    # Run the Flask app
    app.run(
        host='0.0.0.0',  # Allow external connections
        port=8080,
        debug=False,
        threaded=True
    ) 