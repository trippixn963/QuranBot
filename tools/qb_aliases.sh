#!/bin/bash
# =============================================================================
# QuranBot Management Aliases
# =============================================================================
# Source this file to get convenient aliases for managing QuranBot
# Usage: source tools/qb_aliases.sh

# VPS Management
alias qb-status='ssh root@159.89.90.90 "systemctl status quranbot.service"'
alias qb-restart='ssh root@159.89.90.90 "systemctl restart quranbot.service"'
alias qb-stop='ssh root@159.89.90.90 "systemctl stop quranbot.service"'
alias qb-start='ssh root@159.89.90.90 "systemctl start quranbot.service"'
alias qb-logs='ssh root@159.89.90.90 "journalctl -u quranbot.service -f"'
alias qb-audio='ssh root@159.89.90.90 "ps aux | grep ffmpeg | grep -v grep"'

# VPS System Info
alias qb-system='ssh root@159.89.90.90 "echo \"=== System Info ===\" && free -h && echo && df -h && echo \"=== Bot Process ===\" && ps aux | grep python | grep main.py"'
alias qb-memory='ssh root@159.89.90.90 "ps aux | grep python | grep main.py | awk \"{print \$6/1024\" MB\"}\""'

# Log Management
alias qb-sync='python tools/sync_logs.py'
alias qb-sync-daemon='python tools/sync_logs.py --daemon'
alias qb-errors='ssh root@159.89.90.90 "tail -20 /opt/DiscordBots/QuranBot/logs/$(date +%Y-%m-%d)/errors.log"'
alias qb-recent='ssh root@159.89.90.90 "tail -20 /opt/DiscordBots/QuranBot/logs/$(date +%Y-%m-%d)/logs.log"'

# Automated Log Sync Daemon
alias qb-daemon-start='python tools/log_sync_daemon.py start'
alias qb-daemon-stop='python tools/log_sync_daemon.py stop'
alias qb-daemon-restart='python tools/log_sync_daemon.py restart'
alias qb-daemon-status='python tools/log_sync_daemon.py status'
alias qb-daemon-install='bash tools/install_macos_service.sh'

# macOS Service Management
alias qb-service-start='launchctl start com.quranbot.logsync'
alias qb-service-stop='launchctl stop com.quranbot.logsync'
alias qb-service-status='launchctl list | grep quranbot'
alias qb-service-logs='tail -f logs/$(date +%Y-%m-%d)/logs.log'

# Local Log Analysis
alias qb-local-logs='tail -20 logs/$(date +%Y-%m-%d)/logs.log'
alias qb-local-errors='tail -20 logs/$(date +%Y-%m-%d)/errors.log'

# Development
alias qb-test='python tools/test_bot.py'
alias qb-update='cd /Users/johnhamwi/Developer/QuranBot && git pull origin main'

# JSON Health Check
alias qb-health='python tools/json_health_check.py'
alias qb-health-repair='python tools/json_health_check.py --repair'
alias qb-health-quiz='python tools/json_health_check.py --quiz'
alias qb-health-json='python tools/json_health_check.py --json'

# Data Backup
alias qb-backup-status='ls -la backup/data_backup.tar.gz 2>/dev/null && echo "✅ Data backup exists" || echo "❌ No data backup found"'
alias qb-backup-check='ssh root@159.89.90.90 "ls -la /opt/DiscordBots/QuranBot/backup/data_backup.tar.gz 2>/dev/null && echo \"✅ VPS data backup exists\" || echo \"❌ No VPS data backup found\""'
alias qb-backup-cleanup='python tools/cleanup_old_backups.py'
alias qb-backup-cleanup-delete='python tools/cleanup_old_backups.py --delete'

# Health Monitoring
alias qb-health-check='ssh root@159.89.90.90 "ps aux | grep -E \"(ffmpeg|python.*main.py)\" | grep -v grep"'
alias qb-webhooks='ssh root@159.89.90.90 "tail -20 /opt/DiscordBots/QuranBot/logs/quranbot.log | grep -i webhook"'
alias qb-memory='ssh root@159.89.90.90 "ps aux | grep \"python.*main.py\" | grep -v grep | awk '\''{print \"Memory: \" \$6/1024 \"MB, CPU: \" \$3 \"%\"}\''"'
alias qb-monitor='echo "🔍 Bot Health Check:" && qb-status && echo && echo "💾 Audio Status:" && qb-health-check && echo && echo "💿 Memory Usage:" && qb-memory'

# VPS Deployment (use with caution)
alias qb-deploy='ssh root@159.89.90.90 "cd /opt/DiscordBots/QuranBot && git pull origin main && systemctl restart quranbot.service"'

echo "✅ QuranBot aliases loaded!"
echo "📋 Available commands:"
echo ""
echo "🖥️ VPS Management:"
echo "   qb-status      - Check VPS bot status"
echo "   qb-restart     - Restart VPS bot"
echo "   qb-logs        - Follow VPS bot logs"
echo "   qb-audio       - Check if audio is playing"
echo "   qb-system      - VPS system information"
echo ""
echo "📡 Log Syncing:"
echo "   qb-sync        - Sync logs from VPS once"
echo "   qb-sync-daemon - Run continuous log sync"
echo "   qb-recent      - Recent VPS logs"
echo "   qb-errors      - Recent VPS errors"
echo ""
echo "🤖 Automated Daemon:"
echo "   qb-daemon-install - Install automated log sync service"
echo "   qb-daemon-status  - Check daemon status"
echo "   qb-daemon-start   - Start daemon manually"
echo "   qb-daemon-stop    - Stop daemon"
echo ""
echo "🛡️ Audio Recovery System:"
echo "   qb-recovery-status  - Show recovery system status"
echo "   qb-recovery-enable  - Enable auto-recovery"
echo "   qb-recovery-disable - Disable auto-recovery"
echo "   qb-recovery-config  - Interactive configuration"
echo "   qb-recovery-reset   - Reset to default settings"
echo ""
echo "🩺 JSON Health Check:"
echo "   qb-health           - Check all JSON files"
echo "   qb-health-repair    - Check and repair corrupted files"
echo "   qb-health-quiz      - Validate quiz files specifically"
echo "   qb-health-json      - Output results in JSON format"
echo ""
echo "💾 Data Backup:"
echo "   qb-backup-status    - Check local data backup"
echo "   qb-backup-check     - Check VPS data backup"
echo "   qb-backup-cleanup   - Preview old backup cleanup"
echo "   qb-backup-cleanup-delete - Delete old backup files"
echo ""
echo "💚 Health Monitoring:"
echo "   qb-health-check     - Check FFmpeg and bot processes"
echo "   qb-webhooks         - Recent webhook activity"
echo "   qb-memory           - Memory and CPU usage"
echo "   qb-monitor          - Comprehensive health overview"
echo ""
echo "🎯 Quick check: qb-monitor && qb-health && qb-backup-check"

# Audio Recovery Management
alias qb-recovery-status='python3 tools/audio_recovery_control.py status'
alias qb-recovery-enable='python3 tools/audio_recovery_control.py enable'
alias qb-recovery-disable='python3 tools/audio_recovery_control.py disable'
alias qb-recovery-config='python3 tools/audio_recovery_control.py config'
alias qb-recovery-reset='python3 tools/audio_recovery_control.py reset' 