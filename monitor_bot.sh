#!/bin/bash

# QuranBot Health Monitoring Script
# This script monitors the bot and restarts it if needed

BOT_NAME="quranbot"
LOG_FILE="/var/log/quranbot_monitor.log"
CHECK_INTERVAL=300  # 5 minutes

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

check_bot_health() {
    # Check if systemd service is running
    if ! systemctl is-active --quiet $BOT_NAME; then
        log "ERROR: $BOT_NAME service is not running. Restarting..."
        systemctl restart $BOT_NAME
        sleep 10
        if systemctl is-active --quiet $BOT_NAME; then
            log "SUCCESS: $BOT_NAME restarted successfully"
        else
            log "ERROR: Failed to restart $BOT_NAME"
        fi
        return 1
    fi
    
    # Check if bot is connected to Discord
    if ! journalctl -u $BOT_NAME --since "5 minutes ago" | grep -q "Connected to Discord\|Bot ready"; then
        log "WARNING: No recent Discord connection activity. Checking logs..."
        
        # Check for disconnection errors
        if journalctl -u $BOT_NAME --since "10 minutes ago" | grep -q "disconnected\|error\|exception"; then
            log "ERROR: Detected disconnection or errors. Restarting $BOT_NAME..."
            systemctl restart $BOT_NAME
            sleep 10
            if systemctl is-active --quiet $BOT_NAME; then
                log "SUCCESS: $BOT_NAME restarted after disconnection"
            else
                log "ERROR: Failed to restart $BOT_NAME after disconnection"
            fi
            return 1
        fi
    fi
    
    # Check if audio is playing
    if ! journalctl -u $BOT_NAME --since "10 minutes ago" | grep -q "Playing audio file\|audio playback"; then
        log "WARNING: No recent audio playback activity. Checking for issues..."
        
        # Check if FFmpeg is running
        if ! pgrep -f "ffmpeg.*audio" > /dev/null; then
            log "ERROR: No FFmpeg audio processes found. Restarting $BOT_NAME..."
            systemctl restart $BOT_NAME
            sleep 10
            if systemctl is-active --quiet $BOT_NAME; then
                log "SUCCESS: $BOT_NAME restarted after audio issue"
            else
                log "ERROR: Failed to restart $BOT_NAME after audio issue"
            fi
            return 1
        fi
    fi
    
    log "INFO: $BOT_NAME is healthy"
    return 0
}

# Main monitoring loop
log "INFO: Starting QuranBot health monitoring"

while true; do
    check_bot_health
    sleep $CHECK_INTERVAL
done 