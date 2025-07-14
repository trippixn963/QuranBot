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
echo "🎯 Quick check: qb-status && qb-audio && qb-daemon-status"

# Audio Recovery Management
alias qb-recovery-status='python3 tools/audio_recovery_control.py status'
alias qb-recovery-enable='python3 tools/audio_recovery_control.py enable'
alias qb-recovery-disable='python3 tools/audio_recovery_control.py disable'
alias qb-recovery-config='python3 tools/audio_recovery_control.py config'
alias qb-recovery-reset='python3 tools/audio_recovery_control.py reset' 