#!/bin/bash
# =============================================================================
# QuranBot Quick Aliases
# =============================================================================
# Add these to your ~/.zshrc or ~/.bash_profile for instant access
# Usage: source bot_aliases.sh
# =============================================================================

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# QuranBot Management Aliases
alias qb-status="$SCRIPT_DIR/manage_quranbot.sh status"
alias qb-restart="$SCRIPT_DIR/manage_quranbot.sh restart"
alias qb-stop="$SCRIPT_DIR/manage_quranbot.sh stop"
alias qb-start="$SCRIPT_DIR/manage_quranbot.sh start"
alias qb-logs="$SCRIPT_DIR/manage_quranbot.sh logs"
alias qb-update="$SCRIPT_DIR/manage_quranbot.sh update"
alias qb-backup="$SCRIPT_DIR/manage_quranbot.sh backup"
alias qb-resources="$SCRIPT_DIR/manage_quranbot.sh resources"
alias qb-audio="$SCRIPT_DIR/manage_quranbot.sh audio"
alias qb-ssh="$SCRIPT_DIR/manage_quranbot.sh ssh"
alias qb-help="$SCRIPT_DIR/manage_quranbot.sh help"

# Quick VPS connection
alias vps="ssh root@159.89.90.90"

# Quick status check
alias qb="$SCRIPT_DIR/manage_quranbot.sh status"

# Log Sync Aliases
alias qb-sync="$SCRIPT_DIR/sync_logs.sh once"
alias qb-sync-watch="$SCRIPT_DIR/sync_logs.sh watch"
alias qb-sync-live="$SCRIPT_DIR/sync_logs.sh live"
alias qb-sync-daemon="$SCRIPT_DIR/sync_logs.sh daemon"
alias qb-sync-stop="$SCRIPT_DIR/sync_logs.sh stop"
alias qb-sync-stats="$SCRIPT_DIR/sync_logs.sh stats"
alias qb-sync-migrate="$SCRIPT_DIR/sync_logs.sh migrate"
alias qb-logs-local="$SCRIPT_DIR/view_logs.sh latest 20"
alias qb-logs-view="$SCRIPT_DIR/view_logs.sh"

# Web Dashboard Aliases
alias qb-web="python $SCRIPT_DIR/web_dashboard.py"
alias qb-web-bg="python $SCRIPT_DIR/web_dashboard.py &"
alias qb-web-open="open http://localhost:8080"

echo "✅ QuranBot aliases loaded!"
echo ""
echo "Available commands:"
echo "  qb          - Quick status check"
echo "  qb-status   - Full status report"
echo "  qb-restart  - Restart bot"
echo "  qb-logs     - View live logs (remote)"
echo "  qb-update   - Update from GitHub"
echo "  vps         - Direct SSH to VPS"
echo ""
echo "Log sync commands:"
echo "  qb-sync        - Sync logs once"
echo "  qb-sync-daemon - Start background sync"
echo "  qb-sync-live   - Stream live logs"
echo "  qb-logs-local  - View local synced logs"
echo "  qb-logs-view   - Advanced log viewer"
echo "  qb-sync-migrate - Migrate old logs to date folders"
echo ""
echo "📁 Log Organization (Date-Based):"
echo "  • System logs: vps_logs/system_logs/YYYY-MM-DD/"
echo "  • New folders created daily at midnight EST"
echo "  • Automatic cleanup (7 days retention)"
echo ""
echo "Web dashboard:"
echo "  qb-web         - Start web dashboard"
echo "  qb-web-open    - Open dashboard in browser"
echo ""
echo "Type 'qb-help' for all commands"
