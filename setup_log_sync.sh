#!/bin/bash
# =============================================================================
# QuranBot Log Sync Setup
# =============================================================================
# One-time setup for automatic log syncing from VPS to Mac
# =============================================================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}=============================================${NC}"
    echo -e "${BLUE} QuranBot Log Sync Setup${NC}"
    echo -e "${BLUE}=============================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if SSH key is set up
check_ssh_setup() {
    print_info "Checking SSH setup..."

    if ssh -o BatchMode=yes -o ConnectTimeout=5 root@159.89.90.90 exit 2>/dev/null; then
        print_success "SSH key authentication is working"
        return 0
    else
        print_error "SSH key authentication failed"
        print_info "Run: ssh-copy-id root@159.89.90.90"
        return 1
    fi
}

# Set up local log directories
setup_directories() {
    print_info "Setting up local log directories..."

    mkdir -p ./vps_logs/{app_logs,system_logs,backups}

    if [ -d "./vps_logs" ]; then
        print_success "Log directories created"
        return 0
    else
        print_error "Failed to create log directories"
        return 1
    fi
}

# Test log sync
test_sync() {
    print_info "Testing log sync..."

    if ./sync_logs.sh once >/dev/null 2>&1; then
        print_success "Log sync test successful"
        return 0
    else
        print_error "Log sync test failed"
        return 1
    fi
}

# Set up aliases
setup_aliases() {
    print_info "Setting up shell aliases..."

    # Check if aliases are already in .zshrc
    if grep -q "QuranBot Management Aliases" ~/.zshrc 2>/dev/null; then
        print_warning "Aliases already exist in ~/.zshrc"
    else
        echo "" >> ~/.zshrc
        echo "# QuranBot Management Aliases" >> ~/.zshrc
        echo "source $(pwd)/bot_aliases.sh" >> ~/.zshrc
        print_success "Aliases added to ~/.zshrc"
    fi

    # Source aliases for current session
    source bot_aliases.sh >/dev/null 2>&1
    print_success "Aliases loaded for current session"
}

# Create launch agent for automatic startup
setup_launch_agent() {
    print_info "Setting up automatic startup (optional)..."

    local plist_file="$HOME/Library/LaunchAgents/com.quranbot.logsync.plist"
    local current_dir="$(pwd)"

    # Create the plist file
    cat > "$plist_file" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.quranbot.logsync</string>

    <key>ProgramArguments</key>
    <array>
        <string>$current_dir/sync_logs.sh</string>
        <string>daemon</string>
    </array>

    <key>WorkingDirectory</key>
    <string>$current_dir</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <false/>

    <key>StartInterval</key>
    <integer>300</integer>

    <key>StandardOutPath</key>
    <string>$current_dir/vps_logs/sync_daemon.log</string>

    <key>StandardErrorPath</key>
    <string>$current_dir/vps_logs/sync_daemon_error.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
EOF

    if [ -f "$plist_file" ]; then
        print_success "Launch agent created at: $plist_file"
        print_info "To enable automatic startup, run:"
        print_info "  launchctl load $plist_file"
        print_info "To disable automatic startup, run:"
        print_info "  launchctl unload $plist_file"
    else
        print_error "Failed to create launch agent"
    fi
}

# Show final instructions
show_instructions() {
    print_header
    print_success "QuranBot Log Sync Setup Complete!"
    echo ""

    print_info "Available commands:"
    echo "  qb-sync        - Sync logs once"
    echo "  qb-sync-daemon - Start background sync"
    echo "  qb-sync-live   - Stream live logs"
    echo "  qb-logs-local  - View local synced logs"
    echo "  ./view_logs.sh - Advanced log viewer"
    echo ""

    print_info "Log location: ./vps_logs/"
    print_info "VS Code workspace: quranbot-logs.code-workspace"
    echo ""

    print_info "To start automatic syncing now:"
    echo "  qb-sync-daemon"
    echo ""

    print_info "To view logs:"
    echo "  qb-logs-local"
    echo "  ./view_logs.sh latest"
    echo "  ./view_logs.sh follow"
    echo ""
}

# Main setup process
main() {
    print_header

    local setup_failed=0

    # Run setup steps
    check_ssh_setup || setup_failed=1
    setup_directories || setup_failed=1

    if [ $setup_failed -eq 0 ]; then
        test_sync || setup_failed=1
        setup_aliases
        setup_launch_agent
        show_instructions
    else
        print_error "Setup failed. Please fix the issues above and try again."
        exit 1
    fi
}

# Run setup if called directly
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
