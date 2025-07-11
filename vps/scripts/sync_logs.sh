#!/bin/bash

# =============================================================================
# QuranBot - VPS Log Sync Script
# =============================================================================
# Automatically syncs logs from VPS to local Mac maintaining exact structure
# 
# Local Structure:  logs/YYYY-MM-DD/logs.log, errors.log, logs.json
# VPS Structure:    /opt/DiscordBots/QuranBot/logs/YYYY-MM-DD/logs.log, errors.log, logs.json
# 
# Features:
# - Maintains exact local log structure and naming
# - Syncs only new/changed files
# - Creates local directories as needed
# - Handles connection errors gracefully
# - Supports both one-time sync and continuous monitoring
# - Colored output for better visibility
# - Bandwidth efficient with rsync
# =============================================================================

# Configuration
VPS_HOST="${VPS_HOST:-root@YOUR_VPS_IP_HERE}"
VPS_LOG_PATH="/opt/DiscordBots/QuranBot/logs/"
LOCAL_LOG_PATH="./logs/"
SYNC_INTERVAL=30  # seconds between syncs in daemon mode

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Logging function
log_message() {
    echo -e "${CYAN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] ✅ $1${NC}"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ❌ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️  $1${NC}"
}

log_info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] ℹ️  $1${NC}"
}

# Function to check VPS connectivity
check_vps_connection() {
    log_info "Checking VPS connection..."
    
    if ssh -o ConnectTimeout=10 -o BatchMode=yes "$VPS_HOST" "echo 'Connection test successful'" > /dev/null 2>&1; then
        log_success "VPS connection established"
        return 0
    else
        log_error "Cannot connect to VPS ($VPS_HOST)"
        return 1
    fi
}

# Function to ensure local log directory exists
ensure_local_directories() {
    if [ ! -d "$LOCAL_LOG_PATH" ]; then
        log_info "Creating local logs directory: $LOCAL_LOG_PATH"
        mkdir -p "$LOCAL_LOG_PATH"
    fi
}

# Function to get list of log dates from VPS
get_vps_log_dates() {
    log_info "Getting log dates from VPS..."
    
    # Get list of date directories from VPS
    VPS_DATES=$(ssh "$VPS_HOST" "find $VPS_LOG_PATH -maxdepth 1 -type d -name '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' -printf '%f\n' 2>/dev/null | sort")
    
    if [ -z "$VPS_DATES" ]; then
        log_warning "No log directories found on VPS"
        return 1
    fi
    
    local date_count=$(echo "$VPS_DATES" | wc -l)
    log_success "Found $date_count log date directories on VPS"
    
    echo "$VPS_DATES"
    return 0
}

# Function to sync logs for a specific date
sync_date_logs() {
    local date_dir="$1"
    local vps_date_path="${VPS_LOG_PATH}${date_dir}/"
    local local_date_path="${LOCAL_LOG_PATH}${date_dir}/"
    
    log_info "Syncing logs for $date_dir..."
    
    # Check if VPS date directory exists and has log files
    if ! ssh "$VPS_HOST" "[ -d '$vps_date_path' ] && [ -n \"\$(ls -A '$vps_date_path' 2>/dev/null)\" ]" > /dev/null 2>&1; then
        log_warning "No logs found for $date_dir on VPS"
        return 1
    fi
    
    # Create local date directory if it doesn't exist
    if [ ! -d "$local_date_path" ]; then
        log_info "Creating local directory: $local_date_path"
        mkdir -p "$local_date_path"
    fi
    
    # Sync the three log files using rsync for efficiency
    local files_synced=0
    local files_failed=0
    
    for file in "logs.log" "errors.log" "logs.json"; do
        local vps_file="${vps_date_path}${file}"
        local local_file="${local_date_path}${file}"
        
        # Check if file exists on VPS
        if ssh "$VPS_HOST" "[ -f '$vps_file' ]" > /dev/null 2>&1; then
            # Use rsync to sync only if file is different
            if rsync -avz --progress "$VPS_HOST:$vps_file" "$local_file" > /dev/null 2>&1; then
                files_synced=$((files_synced + 1))
                log_success "  ✅ Synced $file"
            else
                files_failed=$((files_failed + 1))
                log_error "  ❌ Failed to sync $file"
            fi
        else
            log_warning "  ⚠️  File $file not found on VPS"
        fi
    done
    
    if [ $files_synced -gt 0 ]; then
        log_success "Synced $files_synced files for $date_dir"
        return 0
    else
        log_warning "No files synced for $date_dir"
        return 1
    fi
}

# Function to perform one-time sync
sync_once() {
    echo -e "${WHITE}========================================${NC}"
    echo -e "${WHITE}       QuranBot VPS Log Sync${NC}"
    echo -e "${WHITE}========================================${NC}"
    
    # Check VPS connection
    if ! check_vps_connection; then
        log_error "Cannot proceed without VPS connection"
        return 1
    fi
    
    # Ensure local directories exist
    ensure_local_directories
    
    # Get list of log dates from VPS
    local vps_dates
    if ! vps_dates=$(get_vps_log_dates); then
        log_error "Failed to get log dates from VPS"
        return 1
    fi
    
    # Sync logs for each date
    local total_dates=0
    local synced_dates=0
    
    while IFS= read -r date_dir; do
        if [ -n "$date_dir" ]; then
            total_dates=$((total_dates + 1))
            if sync_date_logs "$date_dir"; then
                synced_dates=$((synced_dates + 1))
            fi
        fi
    done <<< "$vps_dates"
    
    echo -e "${WHITE}========================================${NC}"
    log_success "Sync completed: $synced_dates/$total_dates dates synced"
    echo -e "${WHITE}========================================${NC}"
    
    return 0
}

# Function to run continuous sync daemon
sync_daemon() {
    echo -e "${WHITE}========================================${NC}"
    echo -e "${WHITE}    QuranBot VPS Log Sync Daemon${NC}"
    echo -e "${WHITE}========================================${NC}"
    log_info "Starting continuous log sync (interval: ${SYNC_INTERVAL}s)"
    log_info "Press Ctrl+C to stop"
    echo -e "${WHITE}========================================${NC}"
    
    # Create PID file
    local pid_file="./vps_logs_sync.pid"
    echo $$ > "$pid_file"
    
    # Trap signals for graceful shutdown
    trap 'log_info "Stopping log sync daemon..."; rm -f "$pid_file"; exit 0' SIGINT SIGTERM
    
    local sync_count=0
    
    while true; do
        sync_count=$((sync_count + 1))
        log_info "Sync cycle #$sync_count"
        
        # Check VPS connection
        if check_vps_connection; then
            # Ensure local directories exist
            ensure_local_directories
            
            # Get list of log dates from VPS
            local vps_dates
            if vps_dates=$(get_vps_log_dates); then
                # Sync logs for each date (focus on recent dates)
                local dates_processed=0
                
                while IFS= read -r date_dir; do
                    if [ -n "$date_dir" ]; then
                        sync_date_logs "$date_dir" > /dev/null 2>&1
                        dates_processed=$((dates_processed + 1))
                    fi
                done <<< "$vps_dates"
                
                log_success "Processed $dates_processed log dates"
            else
                log_warning "Could not get log dates from VPS"
            fi
        else
            log_warning "VPS connection failed, will retry in ${SYNC_INTERVAL}s"
        fi
        
        # Wait for next sync cycle
        sleep $SYNC_INTERVAL
    done
}

# Function to show sync status
show_status() {
    echo -e "${WHITE}========================================${NC}"
    echo -e "${WHITE}     QuranBot VPS Log Sync Status${NC}"
    echo -e "${WHITE}========================================${NC}"
    
    # Check if daemon is running
    local pid_file="./vps_logs_sync.pid"
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            log_success "Sync daemon is running (PID: $pid)"
        else
            log_warning "PID file exists but daemon is not running"
            rm -f "$pid_file"
        fi
    else
        log_info "Sync daemon is not running"
    fi
    
    # Show VPS connection status
    if check_vps_connection; then
        log_success "VPS connection is working"
    else
        log_error "VPS connection is not working"
    fi
    
    # Show local logs directory info
    if [ -d "$LOCAL_LOG_PATH" ]; then
        local log_dirs=$(find "$LOCAL_LOG_PATH" -maxdepth 1 -type d -name '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' | wc -l)
        log_info "Local log directories: $log_dirs"
        
        # Show most recent log directory
        local latest_dir=$(find "$LOCAL_LOG_PATH" -maxdepth 1 -type d -name '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' | sort | tail -1)
        if [ -n "$latest_dir" ]; then
            local dir_name=$(basename "$latest_dir")
            local file_count=$(ls "$latest_dir" 2>/dev/null | wc -l)
            log_info "Latest log directory: $dir_name ($file_count files)"
        fi
    else
        log_warning "Local logs directory does not exist"
    fi
    
    echo -e "${WHITE}========================================${NC}"
}

# Function to stop sync daemon
stop_daemon() {
    local pid_file="./vps_logs_sync.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            log_info "Stopping sync daemon (PID: $pid)..."
            kill "$pid"
            rm -f "$pid_file"
            log_success "Sync daemon stopped"
        else
            log_warning "PID file exists but daemon is not running"
            rm -f "$pid_file"
        fi
    else
        log_info "Sync daemon is not running"
    fi
}

# Function to show help
show_help() {
    echo -e "${WHITE}QuranBot VPS Log Sync Script${NC}"
    echo
    echo -e "${YELLOW}Usage:${NC}"
    echo "  $0 [command]"
    echo
    echo -e "${YELLOW}Commands:${NC}"
    echo -e "  ${GREEN}sync${NC}        Perform one-time log sync"
    echo -e "  ${GREEN}daemon${NC}      Start continuous sync daemon"
    echo -e "  ${GREEN}status${NC}      Show sync status"
    echo -e "  ${GREEN}stop${NC}        Stop sync daemon"
    echo -e "  ${GREEN}help${NC}        Show this help message"
    echo
    echo -e "${YELLOW}Configuration:${NC}"
    echo "  VPS Host: $VPS_HOST"
    echo "  VPS Path: $VPS_LOG_PATH"
    echo "  Local Path: $LOCAL_LOG_PATH"
    echo "  Sync Interval: ${SYNC_INTERVAL}s"
    echo
    echo -e "${YELLOW}Examples:${NC}"
    echo "  $0 sync          # Sync logs once"
    echo "  $0 daemon        # Start continuous sync"
    echo "  $0 status        # Check sync status"
    echo "  $0 stop          # Stop daemon"
}

# Main script logic
case "${1:-help}" in
    "sync")
        sync_once
        ;;
    "daemon")
        sync_daemon
        ;;
    "status")
        show_status
        ;;
    "stop")
        stop_daemon
        ;;
    "help"|"--help"|"-h")
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo
        show_help
        exit 1
        ;;
esac 