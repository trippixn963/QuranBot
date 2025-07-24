#!/bin/bash

# Enhanced Auto-Recovery Deployment Script
# Deploys improved voice connection and audio recovery features to VPS

set -e  # Exit on any error

# Configuration
VPS_HOST="root@159.89.90.90"
VPS_PATH="/opt/DiscordBots/QuranBot"
REPO_URL="https://github.com/johnhamwi/QuranBot.git"
BACKUP_DIR="/opt/DiscordBots/QuranBot_backup_$(date +%Y%m%d_%H%M%S)"

echo "🚀 Enhanced Auto-Recovery Deployment Started"
echo "=============================================="

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to execute commands on VPS
vps_exec() {
    ssh -o ConnectTimeout=30 "$VPS_HOST" "$1"
}

# Check if we can connect to VPS
log "🔌 Testing VPS connection..."
if ! vps_exec "echo 'VPS connection successful'"; then
    log "❌ Failed to connect to VPS. Please check your connection."
    exit 1
fi

log "✅ VPS connection established"

# Check current bot status
log "📊 Checking current bot status..."
BOT_STATUS=$(vps_exec "systemctl is-active quranbot.service" || echo "inactive")
log "Current bot status: $BOT_STATUS"

# Create backup of current deployment
log "💾 Creating backup of current deployment..."
vps_exec "sudo cp -r $VPS_PATH $BACKUP_DIR" || {
    log "⚠️  Backup creation failed, but continuing..."
}

# Stop the bot service
log "🛑 Stopping bot service..."
vps_exec "sudo systemctl stop quranbot.service" || {
    log "⚠️  Service was already stopped"
}

# Pull latest changes from repository
log "📥 Pulling latest changes from repository..."
vps_exec "cd $VPS_PATH && git fetch origin && git reset --hard origin/master" || {
    log "❌ Git pull failed"
    exit 1
}

# Verify the enhanced audio_manager.py exists
log "🔍 Verifying enhanced auto-recovery features..."
if vps_exec "grep -q 'Enhanced auto-recovery settings' $VPS_PATH/src/utils/audio_manager.py"; then
    log "✅ Enhanced auto-recovery features detected"
else
    log "❌ Enhanced auto-recovery features not found in deployment"
    exit 1
fi

# Check Python virtual environment
log "🐍 Checking Python virtual environment..."
vps_exec "cd $VPS_PATH && source .venv/bin/activate && python --version"

# Update dependencies if requirements.txt changed
log "📦 Updating dependencies..."
vps_exec "cd $VPS_PATH && source .venv/bin/activate && pip install -r requirements.txt --upgrade" || {
    log "⚠️  Dependency update had issues, but continuing..."
}

# Verify configuration files
log "⚙️  Verifying configuration..."
if vps_exec "test -f $VPS_PATH/config/.env"; then
    log "✅ Configuration files found"
else
    log "❌ Configuration files missing. Please ensure .env file is present."
    exit 1
fi

# Start the bot service
log "▶️  Starting enhanced bot service..."
vps_exec "sudo systemctl start quranbot.service"

# Wait a moment for service to start
sleep 5

# Check if service started successfully
log "🔍 Verifying service startup..."
NEW_STATUS=$(vps_exec "systemctl is-active quranbot.service" || echo "failed")

if [ "$NEW_STATUS" = "active" ]; then
    log "✅ Bot service started successfully"
else
    log "❌ Bot service failed to start. Status: $NEW_STATUS"
    log "📋 Recent service logs:"
    vps_exec "sudo journalctl -u quranbot.service --no-pager -n 20"
    exit 1
fi

# Monitor service for 30 seconds
log "👀 Monitoring service stability for 30 seconds..."
for i in {1..6}; do
    sleep 5
    STATUS=$(vps_exec "systemctl is-active quranbot.service" || echo "failed")
    if [ "$STATUS" = "active" ]; then
        log "   ✅ Check $i/6: Service running stable"
    else
        log "   ❌ Check $i/6: Service unstable - Status: $STATUS"
        exit 1
    fi
done

# Check recent logs for enhanced features
log "📋 Checking for enhanced auto-recovery initialization..."
if vps_exec "sudo journalctl -u quranbot.service --since '1 minute ago' | grep -q 'Enhanced'"; then
    log "✅ Enhanced auto-recovery features are initializing"
else
    log "⚠️  Enhanced features not yet visible in logs (may take time to activate)"
fi

# Display deployment summary
log "📊 Deployment Summary:"
log "   • VPS Host: $VPS_HOST"
log "   • Deployment Path: $VPS_PATH"
log "   • Backup Created: $BACKUP_DIR"
log "   • Service Status: $(vps_exec 'systemctl is-active quranbot.service')"
log "   • Enhanced Features: ✅ Deployed"

echo ""
echo "🎉 Enhanced Auto-Recovery Deployment Complete!"
echo "=============================================="
echo ""
echo "🔧 Enhanced Features Deployed:"
echo "   • Smarter retry mechanisms (5 attempts vs 3)"
echo "   • Faster recovery cooldown (3 minutes vs 5)"
echo "   • Proactive connection health monitoring"
echo "   • Enhanced timeout detection and handling"
echo "   • Improved FFmpeg stability options"
echo "   • Multi-step validation for connections"
echo ""
echo "📊 Monitoring Improvements:"
echo "   • Health checks every 60 seconds (vs 120)"
echo "   • Connection validation with timeout detection"
echo "   • Enhanced playback validation"
echo "   • Comprehensive status logging every 5 minutes"
echo ""
echo "🎵 Audio Enhancements:"
echo "   • Increased buffer size (2048k vs 1024k)"
echo "   • Enhanced reconnection options"
echo "   • 30-second timeout protection"
echo "   • Multi-step playback validation"
echo ""

# Provide useful commands for monitoring
echo "📋 Useful monitoring commands:"
echo ""
echo "   Check service status:"
echo "   ssh $VPS_HOST 'sudo systemctl status quranbot.service'"
echo ""
echo "   View recent logs:"
echo "   ssh $VPS_HOST 'sudo journalctl -u quranbot.service -f'"
echo ""
echo "   Check enhanced monitoring:"
echo "   ssh $VPS_HOST 'sudo journalctl -u quranbot.service | grep \"Enhanced\\|Connection Health\\|Audio Recovery\"'"
echo ""

log "🎯 Enhanced auto-recovery deployment completed successfully!"

exit 0 