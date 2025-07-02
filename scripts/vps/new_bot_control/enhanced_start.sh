#!/bin/bash
# Enhanced QuranBot Start Script
# Comprehensive bot startup with health checks and logging

VPS_HOST="159.89.90.90"
VPS_USER="root"
SSH_KEY="C:/Users/hanna/.ssh/id_rsa"
BOT_SERVICE="quranbot"
BOT_PATH="/opt/quranbot"

echo "🚀 Enhanced QuranBot Start Script"
echo "================================="
echo "📅 $(date)"
echo "🖥️  Connecting to: $VPS_HOST"
echo ""

# Function to run SSH commands with better error handling
ssh_execute() {
    local command="$1"
    local description="$2"
    
    echo "🔄 $description..."
    ssh -i "$SSH_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$VPS_USER@$VPS_HOST" "$command"
    
    if [ $? -eq 0 ]; then
        echo "✅ $description completed successfully"
        return 0
    else
        echo "❌ $description failed"
        return 1
    fi
}

# Pre-start checks
echo "🔍 Pre-start Checks"
echo "-------------------"

# Check if service exists
ssh_execute "systemctl list-unit-files | grep $BOT_SERVICE" "Checking if $BOT_SERVICE service exists"
if [ $? -ne 0 ]; then
    echo "❌ Service $BOT_SERVICE not found on system"
    exit 1
fi

# Check if already running
echo "🔍 Checking current status..."
ssh -i "$SSH_KEY" "$VPS_USER@$VPS_HOST" "systemctl is-active $BOT_SERVICE" &>/dev/null
if [ $? -eq 0 ]; then
    echo "⚠️  Bot is already running"
    echo "📊 Current status:"
    ssh_execute "systemctl status $BOT_SERVICE --no-pager -l" "Getting current status"
    echo ""
    read -p "🤔 Do you want to restart it? (y/n): " restart_choice
    if [[ $restart_choice =~ ^[Yy]$ ]]; then
        ssh_execute "systemctl restart $BOT_SERVICE" "Restarting $BOT_SERVICE"
    else
        echo "ℹ️  Operation cancelled"
        exit 0
    fi
else
    # Start the service
    ssh_execute "systemctl start $BOT_SERVICE" "Starting $BOT_SERVICE"
fi

# Wait for service to initialize
echo ""
echo "⏳ Waiting for service to initialize..."
sleep 5

# Post-start verification
echo ""
echo "🧪 Post-start Verification"
echo "--------------------------"

# Check if service is active
ssh_execute "systemctl is-active $BOT_SERVICE" "Verifying service is active"
service_active=$?

if [ $service_active -eq 0 ]; then
    echo "✅ Service is running successfully!"
    
    # Get process information
    echo ""
    echo "📊 Process Information:"
    ssh_execute "ps aux | grep python | grep -v grep | head -5" "Getting Python processes"
    
    # Get service status
    echo ""
    echo "📋 Service Status:"
    ssh_execute "systemctl status $BOT_SERVICE --no-pager -l | head -15" "Getting detailed status"
    
    # Check recent logs for errors
    echo ""
    echo "📝 Recent Logs Check:"
    ssh_execute "tail -20 $BOT_PATH/logs/\$(date +%Y-%m-%d).log 2>/dev/null | grep -i error | tail -3 || echo 'No recent errors found'" "Checking for recent errors"
    
else
    echo "❌ Service failed to start properly"
    echo ""
    echo "🔍 Troubleshooting Information:"
    ssh_execute "systemctl status $BOT_SERVICE --no-pager -l" "Getting failure details"
    echo ""
    echo "📝 Recent logs:"
    ssh_execute "journalctl -u $BOT_SERVICE --no-pager -l -n 10" "Getting system logs"
fi

echo ""
echo "🏁 Start script completed"
echo "📅 $(date)" 