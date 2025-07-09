#!/usr/bin/env python3
"""
QuranBot Web Dashboard
Simple web interface for managing QuranBot on VPS
Run with: python web_dashboard.py
Access at: http://localhost:5000
"""

import json
import subprocess
import threading
import time
from datetime import datetime

from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

VPS_HOST = "root@159.89.90.90"
SERVICE_NAME = "quranbot.service"


def run_ssh_command(command):
    """Execute SSH command on VPS"""
    try:
        full_command = f"ssh {VPS_HOST} '{command}'"
        result = subprocess.run(
            full_command, shell=True, capture_output=True, text=True, timeout=30
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Command timed out",
            "output": "",
            "returncode": -1,
        }
    except Exception as e:
        return {"success": False, "error": str(e), "output": "", "returncode": -1}


def get_bot_status():
    """Get comprehensive bot status"""
    status_cmd = f"systemctl is-active {SERVICE_NAME} && systemctl status {SERVICE_NAME} --no-pager -l"
    logs_cmd = f"journalctl -u {SERVICE_NAME} --no-pager -n 5"
    resources_cmd = "free -h && df -h / | tail -1"

    status = run_ssh_command(status_cmd)
    logs = run_ssh_command(logs_cmd)
    resources = run_ssh_command(resources_cmd)

    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "is_running": "active" in status.get("output", ""),
        "status_output": status.get("output", ""),
        "recent_logs": logs.get("output", ""),
        "resources": resources.get("output", ""),
        "errors": {
            "status": status.get("error", ""),
            "logs": logs.get("error", ""),
            "resources": resources.get("error", ""),
        },
    }


# HTML Template
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>QuranBot Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #2c3e50, #3498db);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 { font-size: 2.5rem; margin-bottom: 10px; }
        .header p { opacity: 0.9; font-size: 1.1rem; }
        .content { padding: 30px; }
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            border-left: 4px solid #3498db;
        }
        .card h3 { color: #2c3e50; margin-bottom: 15px; font-size: 1.2rem; }
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .status-running { background: #27ae60; }
        .status-stopped { background: #e74c3c; }
        .btn-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        .btn {
            background: #3498db;
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            transition: all 0.3s ease;
        }
        .btn:hover { background: #2980b9; transform: translateY(-2px); }
        .btn-danger { background: #e74c3c; }
        .btn-danger:hover { background: #c0392b; }
        .btn-success { background: #27ae60; }
        .btn-success:hover { background: #229954; }
        .btn-warning { background: #f39c12; }
        .btn-warning:hover { background: #e67e22; }
        .logs {
            background: #2c3e50;
            color: #ecf0f1;
            padding: 20px;
            border-radius: 8px;
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 0.9rem;
            white-space: pre-wrap;
            max-height: 400px;
            overflow-y: auto;
        }
        .timestamp {
            color: #95a5a6;
            font-size: 0.9rem;
            margin-bottom: 20px;
        }
        .loading {
            display: none;
            text-align: center;
            padding: 20px;
            color: #7f8c8d;
        }
        .alert {
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .alert-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        @media (max-width: 768px) {
            .header h1 { font-size: 2rem; }
            .content { padding: 20px; }
            .btn-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🕌 QuranBot Dashboard</h1>
            <p>Manage your Discord bot from anywhere</p>
        </div>

        <div class="content">
            <div id="alerts"></div>

            <div class="status-grid">
                <div class="card">
                    <h3>🤖 Bot Status</h3>
                    <div id="bot-status">
                        <span class="status-indicator" id="status-indicator"></span>
                        <span id="status-text">Loading...</span>
                    </div>
                    <div class="timestamp" id="last-updated"></div>
                </div>

                <div class="card">
                    <h3>💾 Resources</h3>
                    <div id="resources">Loading...</div>
                </div>
            </div>

            <div class="btn-grid">
                <button class="btn btn-success" onclick="executeCommand('start')">▶️ Start Bot</button>
                <button class="btn btn-warning" onclick="executeCommand('restart')">🔄 Restart Bot</button>
                <button class="btn btn-danger" onclick="executeCommand('stop')">⏹️ Stop Bot</button>
                <button class="btn" onclick="executeCommand('update')">📥 Update Bot</button>
                <button class="btn" onclick="executeCommand('backup')">💾 Backup Data</button>
                <button class="btn" onclick="refreshStatus()">🔄 Refresh</button>
            </div>

            <div class="card">
                <h3>📋 Recent Logs</h3>
                <div class="logs" id="logs">Loading logs...</div>
            </div>

            <div class="loading" id="loading">
                <p>⏳ Executing command...</p>
            </div>
        </div>
    </div>

    <script>
        function showAlert(message, type = 'success') {
            const alerts = document.getElementById('alerts');
            const alert = document.createElement('div');
            alert.className = `alert alert-${type}`;
            alert.textContent = message;
            alerts.appendChild(alert);
            setTimeout(() => alert.remove(), 5000);
        }

        function refreshStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    const indicator = document.getElementById('status-indicator');
                    const statusText = document.getElementById('status-text');
                    const lastUpdated = document.getElementById('last-updated');
                    const resources = document.getElementById('resources');
                    const logs = document.getElementById('logs');

                    if (data.is_running) {
                        indicator.className = 'status-indicator status-running';
                        statusText.textContent = 'Running';
                    } else {
                        indicator.className = 'status-indicator status-stopped';
                        statusText.textContent = 'Stopped';
                    }

                    lastUpdated.textContent = `Last updated: ${data.timestamp}`;
                    resources.textContent = data.resources;
                    logs.textContent = data.recent_logs;
                })
                .catch(error => {
                    showAlert('Failed to refresh status: ' + error.message, 'error');
                });
        }

        function executeCommand(command) {
            const loading = document.getElementById('loading');
            loading.style.display = 'block';

            fetch('/api/command', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({command: command})
            })
            .then(response => response.json())
            .then(data => {
                loading.style.display = 'none';
                if (data.success) {
                    showAlert(`Command '${command}' executed successfully!`, 'success');
                    setTimeout(refreshStatus, 2000);
                } else {
                    showAlert(`Command failed: ${data.error}`, 'error');
                }
            })
            .catch(error => {
                loading.style.display = 'none';
                showAlert('Failed to execute command: ' + error.message, 'error');
            });
        }

        // Auto-refresh every 30 seconds
        setInterval(refreshStatus, 30000);

        // Initial load
        refreshStatus();
    </script>
</body>
</html>
"""


@app.route("/")
def dashboard():
    return render_template_string(DASHBOARD_HTML)


@app.route("/api/status")
def api_status():
    return jsonify(get_bot_status())


@app.route("/api/command", methods=["POST"])
def api_command():
    data = request.get_json()
    command = data.get("command", "")

    command_map = {
        "start": f"systemctl start {SERVICE_NAME}",
        "stop": f"systemctl stop {SERVICE_NAME}",
        "restart": f"systemctl restart {SERVICE_NAME}",
        "update": f"cd /opt/QuranBot && git pull origin master && systemctl restart {SERVICE_NAME}",
        "backup": f"cd /opt/QuranBot && tar -czf /tmp/manual_backup_$(date +%Y%m%d_%H%M%S).tar.gz data/ config/ logs/ backup/ 2>/dev/null || true",
    }

    if command not in command_map:
        return jsonify({"success": False, "error": "Invalid command"})

    result = run_ssh_command(command_map[command])
    return jsonify(result)


if __name__ == "__main__":
    print("🌐 QuranBot Web Dashboard")
    print("=" * 40)
    print("📱 Access your dashboard at: http://localhost:8080")
    print("🔧 Manage QuranBot from your browser!")
    print("⏹️  Press Ctrl+C to stop")
    print()

    app.run(host="0.0.0.0", port=8080, debug=False)
