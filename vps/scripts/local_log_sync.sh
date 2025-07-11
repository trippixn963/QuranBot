#!/bin/bash

# =============================================================================
# QuranBot - Local Log Sync Launcher (Mac)
# =============================================================================
# Easy launcher for log syncing from your local Mac
# 
# Usage: Run this script from your QuranBot project directory
# It will automatically sync logs from VPS maintaining exact structure
# =============================================================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Configuration
SYNC_SCRIPT="./vps/scripts/sync_logs.sh"

# Logging functions
log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] ✅ $1${NC}"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ❌ $1${NC}"
}

log_info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] ℹ️  $1${NC}"
}

# Check if we're in the right directory
check_directory() {
    if [ ! -f "main.py" ] || [ ! -d "src" ] || [ ! -d "vps" ]; then
        log_error "This script must be run from the QuranBot project directory"
        log_error "Expected structure: main.py, src/, vps/"
        exit 1
    fi
    
    if [ ! -f "$SYNC_SCRIPT" ]; then
        log_error "Log sync script not found: $SYNC_SCRIPT"
        exit 1
    fi
}

# Show help
show_help() {
    echo -e "${WHITE}QuranBot Local Log Sync Launcher${NC}"
    echo
    echo -e "${YELLOW}Usage:${NC}"
    echo "  $0 [command]"
    echo
    echo -e "${YELLOW}Commands:${NC}"
    echo -e "  ${GREEN}sync${NC}        Sync logs once from VPS"
    echo -e "  ${GREEN}daemon${NC}      Start continuous sync daemon"
    echo -e "  ${GREEN}status${NC}      Show sync status"
    echo -e "  ${GREEN}stop${NC}        Stop sync daemon"
    echo -e "  ${GREEN}help${NC}        Show this help message"
    echo
    echo -e "${YELLOW}Examples:${NC}"
    echo "  $0 sync          # Sync logs once"
    echo "  $0 daemon        # Start continuous sync"
    echo "  $0 status        # Check sync status"
    echo "  $0 stop          # Stop daemon"
    echo
    echo -e "${YELLOW}Note:${NC}"
    echo "  Logs will be synced to: ./logs/YYYY-MM-DD/"
    echo "  Each day contains: logs.log, errors.log, logs.json"
    echo "  Same structure as your local bot logs"
}

# Main script logic
main() {
    # Check if we're in the right directory
    check_directory
    
    case "${1:-help}" in
        "sync")
            log_info "Starting one-time log sync..."
            bash "$SYNC_SCRIPT" sync
            ;;
        "daemon")
            log_info "Starting continuous log sync daemon..."
            bash "$SYNC_SCRIPT" daemon
            ;;
        "status")
            bash "$SYNC_SCRIPT" status
            ;;
        "stop")
            bash "$SYNC_SCRIPT" stop
            ;;
        "help"|"--help"|"-h")
            show_help
            ;;
        *)
            log_error "Unknown command: $1"
            echo
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@" 