#!/bin/bash
# =============================================================================
# QuranBot Log Viewer
# =============================================================================
# Easy log viewing with filtering and search
# Usage: ./view_logs.sh [options]
# =============================================================================

LOG_DIR="./vps_logs"
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

show_help() {
    echo -e "${BLUE}QuranBot Log Viewer${NC}"
    echo ""
    echo "Usage: ./view_logs.sh [command] [options]"
    echo ""
    echo "Commands:"
    echo "  latest     - Show latest logs (default)"
    echo "  all        - Show all logs"
    echo "  errors     - Show only error messages"
    echo "  search     - Search logs for specific text"
    echo "  follow     - Follow latest log file in real-time"
    echo "  stats      - Show log statistics"
    echo ""
    echo "Examples:"
    echo "  ./view_logs.sh latest          # Show recent logs"
    echo "  ./view_logs.sh search 'error'  # Search for errors"
    echo "  ./view_logs.sh follow          # Live tail"
    echo ""
}

show_latest() {
    local lines=${1:-50}
    echo -e "${GREEN}📋 Latest $lines log entries:${NC}"
    echo ""

    if [ -d "$LOG_DIR/system_logs" ]; then
        # Find all log files in date-based subdirectories
        find "$LOG_DIR/system_logs" -name "*.log" -type f | sort | xargs cat | tail -n "$lines" | while read line; do
            if [[ "$line" == *"ERROR"* ]] || [[ "$line" == *"CRITICAL"* ]]; then
                echo -e "${RED}$line${NC}"
            elif [[ "$line" == *"WARNING"* ]] || [[ "$line" == *"WARN"* ]]; then
                echo -e "${YELLOW}$line${NC}"
            elif [[ "$line" == *"✅"* ]] || [[ "$line" == *"SUCCESS"* ]]; then
                echo -e "${GREEN}$line${NC}"
            else
                echo "$line"
            fi
        done
    else
        echo "No logs found. Run 'qb-sync' first."
    fi
}

show_all() {
    echo -e "${GREEN}📋 All logs (organized by date):${NC}"
    echo ""

    if [ -d "$LOG_DIR/system_logs" ]; then
        # Show logs organized by date directories
        find "$LOG_DIR/system_logs" -type d -name "????-??-??" | sort | while read date_dir; do
            local date_name=$(basename "$date_dir")
            echo -e "${BLUE}=== $date_name ===${NC}"
            find "$date_dir" -name "*.log" -type f | sort | xargs cat
            echo ""
        done
    else
        echo "No logs found. Run 'qb-sync' first."
    fi
}

show_errors() {
    echo -e "${RED}❌ Error messages:${NC}"
    echo ""

    if [ -d "$LOG_DIR/system_logs" ]; then
        find "$LOG_DIR/system_logs" -name "*.log" -type f | sort | xargs grep -i -E "(error|critical|exception|failed|traceback)" | while read line; do
            echo -e "${RED}$line${NC}"
        done
    else
        echo "No logs found. Run 'qb-sync' first."
    fi
}

search_logs() {
    local search_term="$1"
    if [ -z "$search_term" ]; then
        echo "Please provide a search term."
        echo "Usage: ./view_logs.sh search 'your_search_term'"
        return 1
    fi

    echo -e "${BLUE}🔍 Searching for: '$search_term'${NC}"
    echo ""

    if [ -d "$LOG_DIR/system_logs" ]; then
        find "$LOG_DIR/system_logs" -name "*.log" -type f | sort | xargs grep -i -n "$search_term" | while read line; do
            if [[ "$line" == *"error"* ]] || [[ "$line" == *"ERROR"* ]]; then
                echo -e "${RED}$line${NC}"
            elif [[ "$line" == *"warning"* ]] || [[ "$line" == *"WARNING"* ]]; then
                echo -e "${YELLOW}$line${NC}"
            else
                echo -e "${GREEN}$line${NC}"
            fi
        done
    else
        echo "No logs found. Run 'qb-sync' first."
    fi
}

follow_logs() {
    echo -e "${GREEN}📡 Following live logs (Press Ctrl+C to stop):${NC}"
    echo ""

    if [ -d "$LOG_DIR/system_logs" ]; then
        # Find the most recent log file across all date directories
        local latest_log=$(find "$LOG_DIR/system_logs" -name "*.log" -type f -exec stat -f "%m %N" {} \; 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)

        if [ -n "$latest_log" ]; then
            echo -e "${BLUE}Following: $(basename "$latest_log")${NC}"
            echo ""
            tail -f "$latest_log" | while read line; do
                if [[ "$line" == *"ERROR"* ]] || [[ "$line" == *"CRITICAL"* ]]; then
                    echo -e "${RED}$line${NC}"
                elif [[ "$line" == *"WARNING"* ]] || [[ "$line" == *"WARN"* ]]; then
                    echo -e "${YELLOW}$line${NC}"
                elif [[ "$line" == *"✅"* ]] || [[ "$line" == *"SUCCESS"* ]]; then
                    echo -e "${GREEN}$line${NC}"
                else
                    echo "$line"
                fi
            done
        else
            echo "No log files found to follow."
        fi
    else
        echo "No logs found. Run 'qb-sync' first."
    fi
}

show_stats() {
    echo -e "${BLUE}📊 Log Statistics:${NC}"
    echo ""

    if [ -d "$LOG_DIR" ]; then
        echo -e "${GREEN}Total log files:${NC} $(find "$LOG_DIR" -name "*.log" | wc -l)"
        echo -e "${GREEN}Total log size:${NC} $(du -sh "$LOG_DIR" 2>/dev/null | cut -f1)"

        # Find latest log file across all date directories
        local latest_log=$(find "$LOG_DIR/system_logs" -name "*.log" -type f -exec stat -f "%m %N" {} \; 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
        if [ -n "$latest_log" ]; then
            echo -e "${GREEN}Latest sync:${NC} $(stat -f "%Sm" "$latest_log" 2>/dev/null)"
        else
            echo -e "${GREEN}Latest sync:${NC} No logs found"
        fi
        echo ""

        echo -e "${BLUE}Date-based directories:${NC}"
        find "$LOG_DIR/system_logs" -type d -name "????-??-??" | sort -r | head -5 | while read dir; do
            local date_name=$(basename "$dir")
            local file_count=$(find "$dir" -name "*.log" 2>/dev/null | wc -l)
            echo "  $date_name ($file_count files)"
        done
        echo ""

        echo -e "${BLUE}Recent activity:${NC}"
        if [ -d "$LOG_DIR/system_logs" ]; then
            local error_count=$(find "$LOG_DIR/system_logs" -name "*.log" -exec grep -c -i "error" {} \; 2>/dev/null | awk '{sum+=$1} END {print sum+0}')
            local warning_count=$(find "$LOG_DIR/system_logs" -name "*.log" -exec grep -c -i "warning" {} \; 2>/dev/null | awk '{sum+=$1} END {print sum+0}')
            local success_count=$(find "$LOG_DIR/system_logs" -name "*.log" -exec grep -c "✅" {} \; 2>/dev/null | awk '{sum+=$1} END {print sum+0}')

            echo -e "  ${RED}Errors:${NC} $error_count"
            echo -e "  ${YELLOW}Warnings:${NC} $warning_count"
            echo -e "  ${GREEN}Success:${NC} $success_count"
        fi
    else
        echo "No logs directory found. Run 'qb-sync' first."
    fi
}

# Main script logic
case "$1" in
    "latest")
        show_latest "${2:-50}"
        ;;
    "all")
        show_all
        ;;
    "errors")
        show_errors
        ;;
    "search")
        search_logs "$2"
        ;;
    "follow")
        follow_logs
        ;;
    "stats")
        show_stats
        ;;
    "help"|"")
        show_help
        ;;
    *)
        echo "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
