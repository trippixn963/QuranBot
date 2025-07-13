#!/bin/bash
# =============================================================================
# QuranBot - macOS Service Installer
# =============================================================================
# Installs log sync daemon as a macOS launchd service for automatic startup

set -e

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="com.quranbot.logsync"
PLIST_FILE="$HOME/Library/LaunchAgents/$SERVICE_NAME.plist"
DAEMON_SCRIPT="$PROJECT_ROOT/tools/log_sync_daemon.py"

echo "🚀 QuranBot - macOS Service Installer"
echo "======================================"
echo "Project Root: $PROJECT_ROOT"
echo "Service Name: $SERVICE_NAME"
echo "Plist File: $PLIST_FILE"
echo ""

# Create LaunchAgents directory if it doesn't exist
mkdir -p "$HOME/Library/LaunchAgents"

# Create the plist file
cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$SERVICE_NAME</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>$(which python3)</string>
        <string>$DAEMON_SCRIPT</string>
        <string>start</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>$PROJECT_ROOT</string>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    
    <key>StandardOutPath</key>
    <string>/dev/null</string>
    
    <key>StandardErrorPath</key>
    <string>/dev/null</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
        <key>PYTHONPATH</key>
        <string>$PROJECT_ROOT/src</string>
    </dict>
    
    <key>ThrottleInterval</key>
    <integer>10</integer>
</dict>
</plist>
EOF

echo "✅ Created plist file: $PLIST_FILE"

# Make daemon script executable
chmod +x "$DAEMON_SCRIPT"
echo "✅ Made daemon script executable"

# Load the service
launchctl unload "$PLIST_FILE" 2>/dev/null || true  # Ignore errors if not loaded
launchctl load "$PLIST_FILE"
echo "✅ Loaded service with launchctl"

# Start the service
launchctl start "$SERVICE_NAME"
echo "✅ Started service"

echo ""
echo "🎉 Installation Complete!"
echo "========================="
echo ""
echo "📋 Service Management Commands:"
echo "  Start:   launchctl start $SERVICE_NAME"
echo "  Stop:    launchctl stop $SERVICE_NAME"
echo "  Restart: launchctl stop $SERVICE_NAME && launchctl start $SERVICE_NAME"
echo "  Status:  launchctl list | grep quranbot"
echo "  Logs:    tail -f $PROJECT_ROOT/logs/\$(date +%Y-%m-%d)/logs.log | grep 'Log Sync Daemon'"
echo ""
echo "🔧 Manual Management:"
echo "  Status:  python tools/log_sync_daemon.py status"
echo "  Stop:    python tools/log_sync_daemon.py stop"
echo ""
echo "🗑️ To Uninstall:"
echo "  launchctl unload $PLIST_FILE"
echo "  rm $PLIST_FILE"
echo ""
echo "The service will now:"
echo "  ✅ Start automatically when you log in"
echo "  ✅ Restart automatically if it crashes"
echo "  ✅ Sync logs every 30 seconds"
echo "  ✅ Run independently of the main bot"
echo ""
echo "Check status in a few seconds with:"
echo "  python tools/log_sync_daemon.py status" 