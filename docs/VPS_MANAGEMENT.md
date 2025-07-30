# 🖥️ QuranBot VPS Management Guide

*"And it is He who created the heavens and earth in truth. And the day He says, 'Be,' and it is, His word is the truth."* - **Quran 6:73**

## 🏗️ Architecture Overview

### **VPS Bot (Primary Production)** 🌐
- **Location**: DigitalOcean VPS (YOUR_VPS_IP)
- **Purpose**: 24/7 Discord bot serving the community
- **Independence**: Runs completely independently of local machine
- **Services**: Audio playback, commands, user interactions, automated features

### **Local Machine (Development/Monitoring)** 💻
- **Purpose**: Development, monitoring, and log analysis
- **Optional**: Can be turned off without affecting VPS operation
- **Tools**: Log syncing, development testing, backup analysis

## ✅ **Current System Status**

| Component | Status | Details |
|-----------|---------|---------|
| **VPS Bot** | ✅ **RUNNING** | Playing Surah 46 (Al-Ahqaf), FFmpeg active |
| **Audio Playback** | ✅ **ACTIVE** | Continuous 24/7 Quranic recitation |
| **Discord Integration** | ✅ **CONNECTED** | All commands and features working |
| **Backup System** | ✅ **HEALTHY** | Automatic backups with integrity checks |
| **Log Management** | ✅ **OPERATIONAL** | Structured logging with rotation |

## 🛠️ **Management Tools**

### **Quick Commands** (Load aliases first: `source tools/qb_aliases.sh`)

```bash
# VPS Status & Control
qb-status      # Check VPS bot status
qb-restart     # Restart VPS bot
qb-audio       # Check if audio is playing
qb-system      # VPS system information

# Log Management  
qb-sync        # Sync logs from VPS once
qb-sync-daemon # Run continuous log sync
qb-recent      # Recent VPS logs
qb-errors      # Recent VPS errors

# Local Analysis
qb-local-logs  # View local synced logs
qb-local-errors # View local synced errors
```

### **Standalone Log Sync Tool**

```bash
# One-time sync
python tools/sync_logs.py

# Continuous monitoring (run in background)
python tools/sync_logs.py --daemon
```

## 📋 **Daily Operations**

### **Morning Check** ☀️
```bash
# Load management tools
source tools/qb_aliases.sh

# Quick health check
qb-status && qb-audio

# Sync latest logs
qb-sync

# Check for any issues
qb-errors
```

### **Evening Review** 🌙
```bash
# Check daily stats
qb-recent | grep -E "(Surah|completed|stats)"

# Verify backup integrity
qb-recent | grep -i backup

# System resource check
qb-system
```

## 🚨 **Troubleshooting**

### **Audio Not Playing**
```bash
# Check if FFmpeg is running
qb-audio

# If no output, restart the service
qb-restart

# Monitor startup
qb-logs
```

### **Bot Offline**
```bash
# Check service status
qb-status

# If failed, check recent errors
qb-errors

# Restart if needed
qb-restart
```

### **Log Sync Issues**
```bash
# Test VPS connection
ssh root@YOUR_VPS_IP "echo 'Connection OK'"

# Manual sync
qb-sync

# Check local logs
ls -la logs/$(date +%Y-%m-%d)/
```

## 🔧 **Advanced Management**

### **Service Management**
```bash
# Direct systemctl commands
ssh root@YOUR_VPS_IP "systemctl status quranbot.service"
ssh root@YOUR_VPS_IP "systemctl restart quranbot.service"
ssh root@YOUR_VPS_IP "systemctl stop quranbot.service"
ssh root@YOUR_VPS_IP "systemctl start quranbot.service"
```

### **Log Analysis**
```bash
# Follow live logs
ssh root@YOUR_VPS_IP "journalctl -u quranbot.service -f"

# Search for specific events
ssh root@YOUR_VPS_IP "grep -i 'audio' /opt/DiscordBots/QuranBot/logs/$(date +%Y-%m-%d)/logs.log"

# Check error patterns
ssh root@YOUR_VPS_IP "tail -100 /opt/DiscordBots/QuranBot/logs/$(date +%Y-%m-%d)/errors.log"
```

### **System Monitoring**
```bash
# Resource usage
ssh root@YOUR_VPS_IP "htop -p \$(pgrep -f 'python.*main.py')"

# Memory usage
ssh root@YOUR_VPS_IP "ps aux | grep python | grep main.py | awk '{print \$6/1024\" MB\"}'"

# Disk usage
ssh root@YOUR_VPS_IP "df -h /opt/DiscordBots/QuranBot/"
```

## 📊 **Performance Metrics**

### **Normal Operating Parameters**
- **Memory Usage**: 50-80 MB (current: ~62 MB)
- **CPU Usage**: Low, spikes during audio transitions
- **Disk Usage**: Logs rotate automatically, backups compressed
- **Network**: Minimal, Discord API calls only

### **Warning Signs**
- Memory usage > 200 MB
- FFmpeg process missing
- Error logs growing rapidly
- Backup integrity failures

## 🔐 **Security & Access**

### **SSH Access**
- **Host**: root@YOUR_VPS_IP
- **Authentication**: SSH key-based (no password)
- **Permissions**: Full root access for bot management

### **File Locations**
- **Bot Directory**: `/opt/DiscordBots/QuranBot/`
- **Logs**: `/opt/DiscordBots/QuranBot/logs/YYYY-MM-DD/`
- **Backups**: `/opt/DiscordBots/QuranBot/backup/`
- **Service File**: `/etc/systemd/system/quranbot.service`

## 🔄 **Deployment & Updates**

### **Safe Update Process**
```bash
# 1. Check current status
qb-status

# 2. Update code (use with caution)
ssh root@YOUR_VPS_IP "cd /opt/DiscordBots/QuranBot && git pull origin main"

# 3. Restart service
qb-restart

# 4. Verify operation
sleep 10 && qb-status && qb-audio
```

### **Emergency Procedures**
```bash
# If bot is completely unresponsive
ssh root@YOUR_VPS_IP "systemctl stop quranbot.service && systemctl start quranbot.service"

# If system issues
ssh root@YOUR_VPS_IP "reboot"
# Note: Service will auto-start on boot
```

## 💡 **Best Practices**

### **Local Machine Usage**
1. **Turn off freely** - VPS continues running independently
2. **Sync logs periodically** - Use `qb-sync` or run daemon
3. **Monitor, don't interfere** - Let VPS handle Discord operations
4. **Use aliases** - Load `source tools/qb_aliases.sh` in each session

### **VPS Maintenance**
1. **Monitor regularly** - Check status daily
2. **Let it run** - Minimal intervention needed
3. **Check backups** - Verify integrity weekly
4. **Update carefully** - Test changes before deployment

### **Development Workflow**
1. **Test locally first** - Use separate Discord bot token
2. **Deploy to VPS** - Only after local testing
3. **Monitor deployment** - Watch logs for issues
4. **Rollback if needed** - Keep previous version ready

## 📞 **Support & Maintenance**

### **Self-Service Diagnostics**
```bash
# Complete health check
source tools/qb_aliases.sh
echo "=== VPS Status ===" && qb-status
echo "=== Audio Check ===" && qb-audio  
echo "=== Recent Activity ===" && qb-recent | tail -10
echo "=== System Resources ===" && qb-system
```

### **Log Collection for Issues**
```bash
# Gather diagnostic information
qb-sync
echo "Recent errors:" > diagnostic.txt
qb-errors >> diagnostic.txt
echo "Recent logs:" >> diagnostic.txt  
qb-recent >> diagnostic.txt
echo "System status:" >> diagnostic.txt
qb-system >> diagnostic.txt
```

---

*This guide ensures reliable 24/7 operation of QuranBot while providing flexible local monitoring capabilities. The VPS operates independently, allowing your local machine to be turned off without affecting the community's access to Quranic content.* 