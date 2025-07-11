#!/bin/bash
# =============================================================================
# QuranBot VPS Management Script
# =============================================================================
# Comprehensive management script for QuranBot VPS deployment
# 
# Usage: ./manage_quranbot.sh [command]
# Commands: status, start, stop, restart, logs, update, deploy, dashboard
# =============================================================================

set -e

# Configuration
BOT_NAME="QuranBot"
BOT_DIR="/opt/QuranBot"
BOT_SERVICE="quranbot.service"
DASHBOARD_SERVICE="quranbot-dashboard.service"
GITHUB_REPO="https://github.com/yourusername/QuranBot.git"  # Update this
BACKUP_DIR="/opt/QuranBot/backups"
LOG_DIR="/opt/QuranBot/logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_header() {
    echo -e "${PURPLE}=== $1 ===${NC}"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

# Get bot status
get_bot_status() {
    if systemctl is-active --quiet $BOT_SERVICE; then
        echo "running"
    else
        echo "stopped"
    fi
}

# Get bot process info
get_bot_process() {
    pgrep -f "main.py" | head -1 || echo ""
}

# Show comprehensive status
show_status() {
    log_header "QuranBot Status"
    
    # Service status
    echo "Service Status:"
    systemctl status $BOT_SERVICE --no-pager -l || true
    echo
    
    # Process information
    local pid=$(get_bot_process)
    if [[ -n "$pid" ]]; then
        echo "Process Information:"
        ps -p $pid -o pid,ppid,cmd,etime,pcpu,pmem || true
        echo
    fi
    
    # System resources
    echo "System Resources:"
    echo "  CPU Usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
    echo "  Memory Usage: $(free | grep Mem | awk '{printf "%.1f%%", $3/$2 * 100.0}')"
    echo "  Disk Usage: $(df -h / | awk 'NR==2{printf "%s", $5}')"
    echo "  Load Average: $(uptime | awk -F'load average:' '{print $2}')"
    echo
    
    # Bot statistics
    if [[ -f "$BOT_DIR/data/bot_stats.json" ]]; then
        echo "Bot Statistics:"
        python3 -c "
import json
try:
    with open('$BOT_DIR/data/bot_stats.json', 'r') as f:
        stats = json.load(f)
    print(f'  Total Sessions: {stats.get(\"total_sessions\", 0)}')
    print(f'  Total Runtime: {stats.get(\"total_runtime_hours\", 0):.1f}h')
    print(f'  Last Session: {stats.get(\"last_session_start\", \"Unknown\")}')
except:
    print('  No statistics available')
"
        echo
    fi
    
    # Dashboard status
    echo "Dashboard Status:"
    local dashboard_status=$(get_dashboard_status)
    if [[ "$dashboard_status" == "running" ]]; then
        echo "  Status: ✅ Running"
        if curl -s --connect-timeout 3 http://localhost:8080/api/status > /dev/null; then
            echo "  Access: ✅ http://$(curl -s ifconfig.me):8080"
        else
            echo "  Access: ⚠️ Service running but not accessible"
        fi
    else
        echo "  Status: ❌ Stopped"
        echo "  Access: ❌ Not available"
    fi
    echo
    
    # Recent logs
    echo "Recent Activity (last 10 lines):"
    local today=$(date +%Y-%m-%d)
    local log_file="$LOG_DIR/$today/logs.log"
    if [[ -f "$log_file" ]]; then
        tail -10 "$log_file" | sed 's/^/  /'
    else
        echo "  No logs found for today"
    fi
}

# Start the bot
start_bot() {
    log_header "Starting QuranBot"
    
    if [[ "$(get_bot_status)" == "running" ]]; then
        log_warning "Bot is already running"
        return 0
    fi
    
    log_info "Starting QuranBot service..."
    systemctl start $BOT_SERVICE
    
    # Wait for startup
    sleep 5
    
    if [[ "$(get_bot_status)" == "running" ]]; then
        log_success "Bot started successfully"
        local pid=$(get_bot_process)
        [[ -n "$pid" ]] && log_info "Process ID: $pid"
    else
        log_error "Failed to start bot"
        log_info "Check logs with: $0 logs"
        return 1
    fi
}

# Stop the bot
stop_bot() {
    log_header "Stopping QuranBot"
    
    if [[ "$(get_bot_status)" == "stopped" ]]; then
        log_warning "Bot is already stopped"
        return 0
    fi
    
    log_info "Stopping QuranBot service..."
    systemctl stop $BOT_SERVICE
    
    # Wait for shutdown
    sleep 3
    
    if [[ "$(get_bot_status)" == "stopped" ]]; then
        log_success "Bot stopped successfully"
    else
        log_error "Failed to stop bot gracefully"
        log_info "Force killing process..."
        local pid=$(get_bot_process)
        [[ -n "$pid" ]] && kill -9 $pid
    fi
}

# Restart the bot
restart_bot() {
    log_header "Restarting QuranBot"
    
    stop_bot
    sleep 2
    start_bot
}

# Show logs
show_logs() {
    local lines=${1:-50}
    local today=$(date +%Y-%m-%d)
    local log_file="$LOG_DIR/$today/logs.log"
    
    log_header "QuranBot Logs (last $lines lines)"
    
    if [[ -f "$log_file" ]]; then
        tail -$lines "$log_file"
    else
        log_warning "No logs found for today"
        log_info "Available log dates:"
        ls -1 "$LOG_DIR" 2>/dev/null || echo "No logs directory found"
    fi
}

# Show error logs
show_errors() {
    local lines=${1:-20}
    local today=$(date +%Y-%m-%d)
    local error_file="$LOG_DIR/$today/errors.log"
    
    log_header "QuranBot Error Logs (last $lines lines)"
    
    if [[ -f "$error_file" ]]; then
        tail -$lines "$error_file"
    else
        log_info "No errors found for today"
    fi
}

# Update bot from GitHub
update_bot() {
    log_header "Updating QuranBot"
    
    # Create backup
    local backup_name="backup_$(date +%Y%m%d_%H%M%S)"
    log_info "Creating backup: $backup_name"
    mkdir -p "$BACKUP_DIR"
    cp -r "$BOT_DIR" "$BACKUP_DIR/$backup_name"
    
    # Stop bot
    log_info "Stopping bot for update..."
    stop_bot
    
    # Update code
    log_info "Pulling latest code..."
    cd "$BOT_DIR"
    git pull origin main || git pull origin master
    
    # Update dependencies
    log_info "Updating dependencies..."
    .venv/bin/pip install -r requirements.txt
    
    # Start bot
    log_info "Starting updated bot..."
    start_bot
    
    log_success "Update completed successfully"
}

# Deploy bot (initial setup)
deploy_bot() {
    log_header "Deploying QuranBot"
    
    # Install system dependencies
    log_info "Installing system dependencies..."
    apt update
    apt install -y python3 python3-pip python3-venv git ffmpeg
    
    # Create bot directory
    log_info "Setting up bot directory..."
    mkdir -p "$BOT_DIR"
    cd "$BOT_DIR"
    
    # Clone repository
    log_info "Cloning repository..."
    git clone "$GITHUB_REPO" .
    
    # Create virtual environment
    log_info "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    
    # Setup systemd services
    log_info "Installing systemd services..."
    cp vps/systemd/quranbot.service /etc/systemd/system/
    cp vps/systemd/quranbot-dashboard.service /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable $BOT_SERVICE
    systemctl enable $DASHBOARD_SERVICE
    
    # Create directories
    mkdir -p logs data backup/temp
    
    log_success "Deployment completed"
    log_info "Next steps:"
    log_info "1. Configure your .env file in config/"
    log_info "2. Start the bot with: $0 start"
    log_info "3. Check status with: $0 status"
}

# Get dashboard status
get_dashboard_status() {
    if systemctl is-active --quiet $DASHBOARD_SERVICE; then
        echo "running"
    else
        echo "stopped"
    fi
}

# Start web dashboard
start_dashboard() {
    log_header "Starting Web Dashboard"
    
    if [[ "$(get_dashboard_status)" == "running" ]]; then
        log_warning "Dashboard is already running"
        return 0
    fi
    
    log_info "Starting dashboard service..."
    systemctl start $DASHBOARD_SERVICE
    
    # Wait for startup
    sleep 3
    
    if [[ "$(get_dashboard_status)" == "running" ]]; then
        log_success "Dashboard started successfully"
        log_info "Access at: http://$(curl -s ifconfig.me):8080"
    else
        log_error "Failed to start dashboard"
        log_info "Check logs with: journalctl -u $DASHBOARD_SERVICE -n 20"
        return 1
    fi
}

# Stop web dashboard
stop_dashboard() {
    log_header "Stopping Web Dashboard"
    
    if [[ "$(get_dashboard_status)" == "stopped" ]]; then
        log_warning "Dashboard is already stopped"
        return 0
    fi
    
    log_info "Stopping dashboard service..."
    systemctl stop $DASHBOARD_SERVICE
    
    # Wait for shutdown
    sleep 2
    
    if [[ "$(get_dashboard_status)" == "stopped" ]]; then
        log_success "Dashboard stopped successfully"
    else
        log_error "Failed to stop dashboard"
    fi
}

# Restart web dashboard
restart_dashboard() {
    log_header "Restarting Web Dashboard"
    
    stop_dashboard
    sleep 2
    start_dashboard
}

# Show dashboard status
show_dashboard_status() {
    log_header "Dashboard Status"
    
    # Service status
    echo "Dashboard Service Status:"
    systemctl status $DASHBOARD_SERVICE --no-pager -l || true
    echo
    
    # Check if accessible
    if curl -s --connect-timeout 5 http://localhost:8080/api/status > /dev/null; then
        log_success "Dashboard is accessible on port 8080"
    else
        log_warning "Dashboard may not be accessible"
    fi
}

# Log syncing functions (for local Mac usage)
sync_logs_to_local() {
    log_header "Syncing Logs to Local Mac"
    
    # Check if sync script exists
    local sync_script="/opt/QuranBot/vps/scripts/sync_logs.sh"
    if [ ! -f "$sync_script" ]; then
        log_error "Log sync script not found: $sync_script"
        return 1
    fi
    
    # Execute sync script
    bash "$sync_script" sync
}

start_log_sync_daemon() {
    log_header "Starting Log Sync Daemon"
    
    # Check if sync script exists
    local sync_script="/opt/QuranBot/vps/scripts/sync_logs.sh"
    if [ ! -f "$sync_script" ]; then
        log_error "Log sync script not found: $sync_script"
        return 1
    fi
    
    # Execute sync daemon
    bash "$sync_script" daemon
}

show_log_sync_status() {
    log_header "Log Sync Status"
    
    # Check if sync script exists
    local sync_script="/opt/QuranBot/vps/scripts/sync_logs.sh"
    if [ ! -f "$sync_script" ]; then
        log_error "Log sync script not found: $sync_script"
        return 1
    fi
    
    # Show sync status
    bash "$sync_script" status
}

stop_log_sync_daemon() {
    log_header "Stopping Log Sync Daemon"
    
    # Check if sync script exists
    local sync_script="/opt/QuranBot/vps/scripts/sync_logs.sh"
    if [ ! -f "$sync_script" ]; then
        log_error "Log sync script not found: $sync_script"
        return 1
    fi
    
    # Stop sync daemon
    bash "$sync_script" stop
}

# Create shell aliases
create_aliases() {
    log_header "Creating Shell Aliases"
    
    local alias_file="/root/.quranbot_aliases"
    cat > "$alias_file" << 'EOF'
# QuranBot Management Aliases
alias qb-status='bash /opt/QuranBot/vps/scripts/manage_quranbot.sh status'
alias qb-start='bash /opt/QuranBot/vps/scripts/manage_quranbot.sh start'
alias qb-stop='bash /opt/QuranBot/vps/scripts/manage_quranbot.sh stop'
alias qb-restart='bash /opt/QuranBot/vps/scripts/manage_quranbot.sh restart'
alias qb-logs='bash /opt/QuranBot/vps/scripts/manage_quranbot.sh logs'
alias qb-errors='bash /opt/QuranBot/vps/scripts/manage_quranbot.sh errors'
alias qb-update='bash /opt/QuranBot/vps/scripts/manage_quranbot.sh update'
alias qb-dashboard='bash /opt/QuranBot/vps/scripts/manage_quranbot.sh dashboard'
alias qb-dashboard-stop='bash /opt/QuranBot/vps/scripts/manage_quranbot.sh stop-dashboard'
alias qb-dashboard-restart='bash /opt/QuranBot/vps/scripts/manage_quranbot.sh restart-dashboard'
alias qb-dashboard-status='bash /opt/QuranBot/vps/scripts/manage_quranbot.sh dashboard-status'
alias qb-dashboard-logs='bash /opt/QuranBot/vps/scripts/manage_quranbot.sh dashboard-logs'
# Log Syncing Aliases (for local Mac usage)
alias qb-sync-logs='bash /opt/QuranBot/vps/scripts/manage_quranbot.sh sync-logs'
alias qb-sync-daemon='bash /opt/QuranBot/vps/scripts/manage_quranbot.sh sync-daemon'
alias qb-sync-status='bash /opt/QuranBot/vps/scripts/manage_quranbot.sh sync-status'
alias qb-sync-stop='bash /opt/QuranBot/vps/scripts/manage_quranbot.sh sync-stop'
EOF
    
    # Add to bashrc if not already present
    if ! grep -q "quranbot_aliases" /root/.bashrc; then
        echo "source $alias_file" >> /root/.bashrc
    fi
    
    log_success "Aliases created. Reload shell or run: source /root/.bashrc"
    log_info "Available aliases:"
    log_info "Bot Management:"
    log_info "  qb-status   - Show bot status"
    log_info "  qb-start    - Start bot"
    log_info "  qb-stop     - Stop bot"
    log_info "  qb-restart  - Restart bot"
    log_info "  qb-logs     - Show logs"
    log_info "  qb-errors   - Show error logs"
    log_info "  qb-update   - Update bot"
    log_info "Dashboard Management:"
    log_info "  qb-dashboard         - Start web dashboard"
    log_info "  qb-dashboard-stop    - Stop web dashboard"
    log_info "  qb-dashboard-restart - Restart web dashboard"
    log_info "  qb-dashboard-status  - Show dashboard status"
    log_info "  qb-dashboard-logs    - Show dashboard logs"
    log_info "Log Syncing (for local Mac usage):"
    log_info "  qb-sync-logs         - Sync logs to local Mac"
    log_info "  qb-sync-daemon       - Start continuous log sync"
    log_info "  qb-sync-status       - Show log sync status"
    log_info "  qb-sync-stop         - Stop log sync daemon"
}

# Main script logic
main() {
    case "${1:-}" in
        "status")
            show_status
            ;;
        "start")
            check_root
            start_bot
            ;;
        "stop")
            check_root
            stop_bot
            ;;
        "restart")
            check_root
            restart_bot
            ;;
        "logs")
            show_logs ${2:-50}
            ;;
        "errors")
            show_errors ${2:-20}
            ;;
        "update")
            check_root
            update_bot
            ;;
        "deploy")
            check_root
            deploy_bot
            ;;
        "dashboard")
            start_dashboard
            ;;
        "stop-dashboard")
            check_root
            stop_dashboard
            ;;
        "restart-dashboard")
            check_root
            restart_dashboard
            ;;
        "dashboard-status")
            show_dashboard_status
            ;;
        "dashboard-logs")
            journalctl -u $DASHBOARD_SERVICE -n ${2:-50} --no-pager
            ;;
        "sync-logs")
            sync_logs_to_local
            ;;
        "sync-daemon")
            start_log_sync_daemon
            ;;
        "sync-status")
            show_log_sync_status
            ;;
        "sync-stop")
            stop_log_sync_daemon
            ;;
        "aliases")
            check_root
            create_aliases
            ;;
        "help"|"-h"|"--help")
            echo "QuranBot VPS Management Script"
            echo ""
            echo "Usage: $0 [command] [options]"
            echo ""
            echo "Commands:"
            echo "  status              Show comprehensive bot status"
            echo "  start               Start the bot"
            echo "  stop                Stop the bot"
            echo "  restart             Restart the bot"
            echo "  logs [lines]        Show recent logs (default: 50 lines)"
            echo "  errors [lines]      Show error logs (default: 20 lines)"
            echo "  update              Update bot from GitHub"
            echo "  deploy              Initial deployment setup"
            echo "  dashboard           Start web dashboard"
            echo "  stop-dashboard      Stop web dashboard"
            echo "  restart-dashboard   Restart web dashboard"
            echo "  dashboard-status    Show dashboard status"
            echo "  dashboard-logs      Show dashboard logs"
            echo "  sync-logs           Sync logs to local Mac (one-time)"
            echo "  sync-daemon         Start continuous log sync daemon"
            echo "  sync-status         Show log sync status"
            echo "  sync-stop           Stop log sync daemon"
            echo "  aliases             Create shell aliases"
            echo "  help                Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 status"
            echo "  $0 logs 100"
            echo "  $0 restart"
            echo "  $0 sync-logs        # Sync logs to local Mac"
            echo "  $0 sync-daemon      # Start continuous sync"
            ;;
        *)
            log_error "Unknown command: ${1:-}"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Run main function
main "$@" 