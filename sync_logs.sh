#!/bin/bash
# =============================================================================
# QuranBot Log Sync Script
# =============================================================================
# Automatically syncs logs from VPS to your Mac
# Usage: ./sync_logs.sh [mode]
# Modes: once, watch, daemon
# =============================================================================

VPS_HOST="root@159.89.90.90"
VPS_LOG_PATH="/opt/QuranBot/logs"
VPS_JOURNAL_CMD="journalctl -u quranbot.service"
LOCAL_LOG_DIR="./vps_logs"
SERVICE_NAME="quranbot.service"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${GREEN}[SYNC]${NC} $1"
}

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create local log directory
setup_local_logs() {
    mkdir -p "$LOCAL_LOG_DIR"/{app_logs,system_logs,backups}

    # Migrate existing system logs to date-based structure if needed
    migrate_existing_system_logs

    print_info "Created local log directories with date-based organization"
}

# Migrate existing system logs to date-based structure (single file per day)
migrate_existing_system_logs() {
    local system_logs_dir="$LOCAL_LOG_DIR/system_logs"

    # Check if there are any old-format log files in the root system_logs directory
    local old_logs=$(find "$system_logs_dir" -maxdepth 1 -name "quranbot_*.log" 2>/dev/null | wc -l)

    if [ "$old_logs" -gt 0 ]; then
        print_info "Migrating existing system logs to simplified structure..."

        # Create a migration directory for current date
        local migration_date=$(TZ='America/New_York' date +%Y-%m-%d)
        local migration_dir="$system_logs_dir/$migration_date"
        mkdir -p "$migration_dir"

        # Combine all old logs into single file
        local log_file="$migration_dir/$migration_date.log"

        # Merge all old logs into single log file (sorted by filename/time)
        find "$system_logs_dir" -maxdepth 1 -name "quranbot_*.log" | sort | xargs cat > "$log_file" 2>/dev/null || true

        # Remove old timestamp-based files
        find "$system_logs_dir" -maxdepth 1 -name "quranbot_*.log" -delete 2>/dev/null || true

        print_status "Migrated logs to: $log_file"
        print_status "Simplified to single file per day"
    fi

    # Also migrate any old date directories with multiple files to single file format
    find "$system_logs_dir" -type d -name "????-??-??" | while read date_dir; do
        local date_name=$(basename "$date_dir")
        local single_log="$date_dir/$date_name.log"
        local error_log="$date_dir/$date_name-errors.log"

        # Check if we have separate error log that needs to be merged
        if [ -f "$error_log" ] && [ -f "$single_log" ]; then
            print_info "Merging separate files for $date_name into single log..."

            # Append error log to main log and remove separate error file
            echo "" >> "$single_log"
            echo "=== ERRORS/WARNINGS ===" >> "$single_log"
            cat "$error_log" >> "$single_log"
            rm -f "$error_log"

            print_status "Merged $date_name files into single log"
        fi

        # Also handle any remaining timestamp files
        local timestamp_files=$(find "$date_dir" -name "quranbot_*.log" 2>/dev/null | wc -l)

        if [ "$timestamp_files" -gt 0 ]; then
            print_info "Converting $date_name timestamp files to single log..."

            # If single log doesn't exist, create it from timestamp files
            if [ ! -f "$single_log" ]; then
                find "$date_dir" -name "quranbot_*.log" | sort | xargs cat > "$single_log" 2>/dev/null || true
            else
                # Append timestamp files to existing single log
                find "$date_dir" -name "quranbot_*.log" | sort | xargs cat >> "$single_log" 2>/dev/null || true
            fi

            # Remove old timestamp files
            find "$date_dir" -name "quranbot_*.log" -delete 2>/dev/null || true

            print_status "Converted $date_name to single file"
        fi
    done
}

# Sync application logs from VPS
sync_app_logs() {
    print_info "Syncing application logs..."

    # Create remote logs directory if it doesn't exist
    ssh $VPS_HOST "mkdir -p $VPS_LOG_PATH" 2>/dev/null

    # Sync log files using rsync
    rsync -avz --delete \
        --include="*.log" \
        --include="*.txt" \
        --exclude="*" \
        $VPS_HOST:$VPS_LOG_PATH/ "$LOCAL_LOG_DIR/app_logs/" 2>/dev/null || true

    print_status "Application logs synced to: $LOCAL_LOG_DIR/app_logs/"
}

# Sync system/service logs with date-based organization (single file per day)
sync_system_logs() {
    print_info "Syncing systemd service logs..."

    # Get current date in EST timezone
    local current_date_est=$(TZ='America/New_York' date +%Y-%m-%d)

    # Create date-based directory structure
    local date_dir="$LOCAL_LOG_DIR/system_logs/$current_date_est"
    mkdir -p "$date_dir"

    # Create single log file per day
    local log_file="$date_dir/$current_date_est.log"

    # Get recent systemd logs and save to single log file
    ssh $VPS_HOST "$VPS_JOURNAL_CMD --no-pager -n 1000" > "$log_file" 2>/dev/null

    # Cleanup: Remove directories older than 7 days (keep 1 week of logs)
    find "$LOCAL_LOG_DIR/system_logs" -type d -name "????-??-??" -mtime +7 -exec rm -rf {} \; 2>/dev/null || true

    print_status "System logs saved to: $log_file"
    print_status "Date directory: $date_dir"
}

# Create live log stream
sync_live_logs() {
    print_info "Starting live log stream (Press Ctrl+C to stop)..."
    echo ""

    # Create named pipe for live logs
    local live_log="$LOCAL_LOG_DIR/live_stream.log"

    # Stream live logs and save to file
    ssh $VPS_HOST "$VPS_JOURNAL_CMD -f" | tee "$live_log"
}

# Backup current logs
backup_logs() {
    local backup_name="logs_backup_$(date +%Y%m%d_%H%M%S).tar.gz"
    local backup_path="$LOCAL_LOG_DIR/backups/$backup_name"

    print_info "Creating log backup..."

    tar -czf "$backup_path" -C "$LOCAL_LOG_DIR" app_logs system_logs 2>/dev/null || true

    # Keep only last 5 backups
    ls -t "$LOCAL_LOG_DIR/backups/"*.tar.gz 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true

    print_status "Backup created: $backup_path"
}

# Watch for changes and sync automatically
watch_mode() {
    print_info "Starting automatic log sync (every 30 seconds)..."
    print_status "Local logs directory: $LOCAL_LOG_DIR"
    print_warning "Press Ctrl+C to stop watching"
    echo ""

    while true; do
        echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} Syncing logs..."
        sync_app_logs
        sync_system_logs

        echo -e "${GREEN}✓${NC} Sync complete - Next sync in 30 seconds"
        echo ""

        sleep 30
    done
}

# Run as background daemon
daemon_mode() {
    local pid_file="/tmp/quranbot_log_sync.pid"

    if [ -f "$pid_file" ]; then
        local old_pid=$(cat "$pid_file")
        if ps -p "$old_pid" > /dev/null 2>&1; then
            print_warning "Log sync daemon already running (PID: $old_pid)"
            return 1
        else
            rm -f "$pid_file"
        fi
    fi

    print_info "Starting log sync daemon..."

    # Run in background
    (
        while true; do
            sync_app_logs >/dev/null 2>&1
            sync_system_logs >/dev/null 2>&1
            sleep 60  # Sync every minute in daemon mode
        done
    ) &

    local daemon_pid=$!
    echo $daemon_pid > "$pid_file"

    print_status "Log sync daemon started (PID: $daemon_pid)"
    print_status "Logs will sync every minute to: $LOCAL_LOG_DIR"
    print_status "Stop with: kill $daemon_pid"

    echo $daemon_pid
}

# Stop daemon
stop_daemon() {
    local pid_file="/tmp/quranbot_log_sync.pid"

    if [ -f "$pid_file" ]; then
        local daemon_pid=$(cat "$pid_file")
        if ps -p "$daemon_pid" > /dev/null 2>&1; then
            kill "$daemon_pid" 2>/dev/null
            rm -f "$pid_file"
            print_info "Log sync daemon stopped"
        else
            print_warning "Daemon not running"
            rm -f "$pid_file"
        fi
    else
        print_warning "No daemon PID file found"
    fi
}

# Show log statistics
show_stats() {
    print_info "QuranBot Log Statistics"
    echo ""

    if [ -d "$LOCAL_LOG_DIR" ]; then
        echo -e "${BLUE}Local Log Directory:${NC} $LOCAL_LOG_DIR"
        echo -e "${BLUE}Total Size:${NC} $(du -sh "$LOCAL_LOG_DIR" 2>/dev/null | cut -f1)"
        echo ""

        echo -e "${BLUE}Application Logs:${NC}"
        find "$LOCAL_LOG_DIR/app_logs" -name "*.log" -o -name "*.txt" 2>/dev/null | wc -l | xargs echo "  Files:"
        du -sh "$LOCAL_LOG_DIR/app_logs" 2>/dev/null | cut -f1 | xargs echo "  Size:"
        echo ""

        echo -e "${BLUE}System Logs (Single File Per Day):${NC}"
        find "$LOCAL_LOG_DIR/system_logs" -name "*.log" 2>/dev/null | wc -l | xargs echo "  Total Files:"
        du -sh "$LOCAL_LOG_DIR/system_logs" 2>/dev/null | cut -f1 | xargs echo "  Total Size:"

        # Show date-based directories with file status
        local date_dirs=$(find "$LOCAL_LOG_DIR/system_logs" -type d -name "????-??-??" 2>/dev/null | sort -r)
        if [ ! -z "$date_dirs" ]; then
            echo "  Date Directories:"
            echo "$date_dirs" | head -5 | while read dir; do
                local date_name=$(basename "$dir")
                local log_file="$dir/$date_name.log"
                local file_size=""

                if [ -f "$log_file" ]; then
                    file_size=$(du -sh "$log_file" 2>/dev/null | cut -f1)
                    echo "    $date_name (📄 $file_size)"
                else
                    echo "    $date_name (❌ Missing)"
                fi
            done
        fi
        echo ""

        echo -e "${BLUE}Backups:${NC}"
        find "$LOCAL_LOG_DIR/backups" -name "*.tar.gz" 2>/dev/null | wc -l | xargs echo "  Files:"
        du -sh "$LOCAL_LOG_DIR/backups" 2>/dev/null | cut -f1 | xargs echo "  Size:"

        echo ""
        echo -e "${BLUE}Recent Log Files:${NC}"
        find "$LOCAL_LOG_DIR/system_logs" -type d -name "????-??-??" | sort -r | head -3 | while read dir; do
            local date_name=$(basename "$dir")
            local log_file="$dir/$date_name.log"
            if [ -f "$log_file" ]; then
                local file_size=$(du -sh "$log_file" 2>/dev/null | cut -f1)
                echo "  📄 $date_name/$date_name.log ($file_size)"
            fi
        done
    else
        print_warning "No local logs found. Run sync first."
    fi
}

# Show help
show_help() {
    echo -e "${BLUE}QuranBot Log Sync Tool${NC}"
    echo ""
    echo -e "${GREEN}Usage:${NC} ./sync_logs.sh [command]"
    echo ""
    echo -e "${GREEN}Commands:${NC}"
    echo "  once      - Sync logs once and exit"
    echo "  watch     - Continuously sync logs (every 30s)"
    echo "  live      - Stream live logs in real-time"
    echo "  daemon    - Run sync in background (every 60s)"
    echo "  stop      - Stop background daemon"
    echo "  backup    - Create log backup"
    echo "  migrate   - Migrate old logs to date-based structure"
    echo "  stats     - Show log statistics"
    echo "  help      - Show this help"
    echo ""
    echo -e "${GREEN}Log Organization:${NC}"
    echo "  • Application logs: $LOCAL_LOG_DIR/app_logs/"
    echo "  • System logs: $LOCAL_LOG_DIR/system_logs/YYYY-MM-DD/"
    echo "  • Backups: $LOCAL_LOG_DIR/backups/"
    echo ""
    echo -e "${GREEN}System Log Structure (Single File Per Day):${NC}"
    echo "  • Date folders: YYYY-MM-DD/ (e.g., 2025-07-09/)"
    echo "  • Single log file: YYYY-MM-DD.log"
    echo "  • New folders created daily at midnight EST"
    echo "  • Keeps 7 days of logs automatically"
    echo ""
    echo -e "${GREEN}Examples:${NC}"
    echo "  ./sync_logs.sh once     # One-time sync"
    echo "  ./sync_logs.sh watch    # Watch mode"
    echo "  ./sync_logs.sh daemon   # Background daemon"
    echo "  ./sync_logs.sh migrate  # Migrate old logs"
    echo ""
    echo -e "${GREEN}Log Location:${NC} $LOCAL_LOG_DIR"
}

# Main script logic
case "$1" in
    "once")
        setup_local_logs
        sync_app_logs
        sync_system_logs
        print_info "One-time sync complete!"
        ;;
    "watch")
        setup_local_logs
        watch_mode
        ;;
    "live")
        setup_local_logs
        sync_live_logs
        ;;
    "daemon")
        setup_local_logs
        daemon_mode
        ;;
    "stop")
        stop_daemon
        ;;
    "backup")
        setup_local_logs
        backup_logs
        ;;
    "migrate")
        setup_local_logs
        migrate_existing_system_logs
        print_info "Old log migration complete!"
        ;;
    "stats")
        show_stats
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
