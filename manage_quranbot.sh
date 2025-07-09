#!/bin/bash
# =============================================================================
# QuranBot VPS Management Script
# =============================================================================
# Easy management of QuranBot on your VPS from your Mac
# Usage: ./manage_quranbot.sh [command]
# =============================================================================

VPS_HOST="root@159.89.90.90"
BOT_PATH="/opt/QuranBot"
SERVICE_NAME="quranbot.service"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${PURPLE}===========================================${NC}"
    echo -e "${PURPLE} QuranBot VPS Management${NC}"
    echo -e "${PURPLE}===========================================${NC}"
}

# Function to show bot status
show_status() {
    print_header
    print_status "Checking QuranBot status on VPS..."
    echo ""

    ssh $VPS_HOST "
        echo -e '${CYAN}=== SERVICE STATUS ===${NC}'
        systemctl status $SERVICE_NAME --no-pager -l
        echo ''
        echo -e '${CYAN}=== RESOURCE USAGE ===${NC}'
        echo 'Memory Usage:'
        free -h | grep -E 'Mem|Swap'
        echo ''
        echo 'Disk Usage:'
        df -h / | tail -1
        echo ''
        echo -e '${CYAN}=== RECENT LOGS (Last 10 lines) ===${NC}'
        journalctl -u $SERVICE_NAME --no-pager -n 10
    "
}

# Function to restart bot
restart_bot() {
    print_status "Restarting QuranBot..."
    ssh $VPS_HOST "systemctl restart $SERVICE_NAME"
    sleep 3
    print_status "Checking if restart was successful..."
    ssh $VPS_HOST "systemctl is-active $SERVICE_NAME" > /dev/null
    if [ $? -eq 0 ]; then
        print_status "✅ QuranBot restarted successfully!"
    else
        print_error "❌ Failed to restart QuranBot"
    fi
}

# Function to stop bot
stop_bot() {
    print_warning "Stopping QuranBot..."
    ssh $VPS_HOST "systemctl stop $SERVICE_NAME"
    print_status "✅ QuranBot stopped"
}

# Function to start bot
start_bot() {
    print_status "Starting QuranBot..."
    ssh $VPS_HOST "systemctl start $SERVICE_NAME"
    sleep 3
    ssh $VPS_HOST "systemctl is-active $SERVICE_NAME" > /dev/null
    if [ $? -eq 0 ]; then
        print_status "✅ QuranBot started successfully!"
    else
        print_error "❌ Failed to start QuranBot"
    fi
}

# Function to view live logs
view_logs() {
    print_status "Viewing live QuranBot logs (Press Ctrl+C to exit)..."
    echo ""
    ssh $VPS_HOST "journalctl -u $SERVICE_NAME -f"
}

# Function to update bot
update_bot() {
    print_status "Updating QuranBot from GitHub..."
    ssh $VPS_HOST "
        cd $BOT_PATH
        git fetch origin
        git reset --hard origin/master
        systemctl restart $SERVICE_NAME
    "
    print_status "✅ QuranBot updated and restarted!"
}

# Function to backup bot data
backup_bot() {
    print_status "Creating manual backup..."
    BACKUP_NAME="quranbot_manual_$(date +%Y%m%d_%H%M%S).tar.gz"
    ssh $VPS_HOST "
        cd $BOT_PATH
        tar -czf /tmp/$BACKUP_NAME data/ config/ logs/ backup/ 2>/dev/null || true
        ls -lh /tmp/$BACKUP_NAME
    "
    print_status "✅ Backup created: /tmp/$BACKUP_NAME"
}

# Function to check system resources
check_resources() {
    print_header
    print_status "Checking VPS resources..."
    echo ""

    ssh $VPS_HOST "
        echo -e '${CYAN}=== CPU USAGE ===${NC}'
        top -bn1 | grep 'Cpu(s)' | head -1
        echo ''
        echo -e '${CYAN}=== MEMORY USAGE ===${NC}'
        free -h
        echo ''
        echo -e '${CYAN}=== DISK USAGE ===${NC}'
        df -h
        echo ''
        echo -e '${CYAN}=== NETWORK CONNECTIONS ===${NC}'
        ss -tuln | grep :443
        echo ''
        echo -e '${CYAN}=== QURANBOT PROCESSES ===${NC}'
        ps aux | grep -E '(python|ffmpeg)' | grep -v grep
    "
}

# Function to show audio status
audio_status() {
    print_status "Checking audio system status..."
    ssh $VPS_HOST "
        cd $BOT_PATH
        echo -e '${CYAN}=== AUDIO FILES ===${NC}'
        find audio/ -name '*.mp3' | wc -l | xargs echo 'Total MP3 files:'
        echo ''
        echo -e '${CYAN}=== FFMPEG PROCESSES ===${NC}'
        ps aux | grep ffmpeg | grep -v grep || echo 'No FFmpeg processes running'
        echo ''
        echo -e '${CYAN}=== AUDIO DIRECTORIES ===${NC}'
        ls -la audio/ 2>/dev/null || echo 'Audio directory not found'
    "
}

# Function to show help
show_help() {
    print_header
    echo ""
    echo -e "${CYAN}Available Commands:${NC}"
    echo ""
    echo -e "  ${GREEN}status${NC}     - Show bot status and recent logs"
    echo -e "  ${GREEN}restart${NC}    - Restart the bot"
    echo -e "  ${GREEN}stop${NC}       - Stop the bot"
    echo -e "  ${GREEN}start${NC}      - Start the bot"
    echo -e "  ${GREEN}logs${NC}       - View live logs (Ctrl+C to exit)"
    echo -e "  ${GREEN}update${NC}     - Update bot from GitHub"
    echo -e "  ${GREEN}backup${NC}     - Create manual backup"
    echo -e "  ${GREEN}resources${NC}  - Check VPS resources"
    echo -e "  ${GREEN}audio${NC}      - Check audio system status"
    echo -e "  ${GREEN}ssh${NC}        - Direct SSH to VPS"
    echo -e "  ${GREEN}help${NC}       - Show this help message"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo -e "  ./manage_quranbot.sh status"
    echo -e "  ./manage_quranbot.sh restart"
    echo -e "  ./manage_quranbot.sh logs"
    echo ""
}

# Function for direct SSH
direct_ssh() {
    print_status "Connecting to VPS via SSH..."
    ssh $VPS_HOST
}

# Main script logic
case "$1" in
    "status")
        show_status
        ;;
    "restart")
        restart_bot
        ;;
    "stop")
        stop_bot
        ;;
    "start")
        start_bot
        ;;
    "logs")
        view_logs
        ;;
    "update")
        update_bot
        ;;
    "backup")
        backup_bot
        ;;
    "resources")
        check_resources
        ;;
    "audio")
        audio_status
        ;;
    "ssh")
        direct_ssh
        ;;
    "help"|"")
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
