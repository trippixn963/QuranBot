# QuranBot VPS Scripts

This directory contains organized scripts for managing the QuranBot on the VPS.

## 📁 Directory Structure

```
scripts/vps/
├── vps_manager.bat          # 🎯 Master VPS Manager (Windows)
├── bot-control/             # 🤖 Bot Control Scripts
│   ├── start_bot.sh         # 🚀 Start the bot
│   ├── stop_bot.sh          # 🛑 Stop the bot
│   ├── restart_bot.sh       # 🔄 Restart the bot
│   ├── status_bot.sh        # 📊 Check bot status
│   └── update_bot.sh        # ⬆️ Update bot files
├── log-management/          # 📋 Log Management Scripts
│   ├── stream_logs.bat      # 🔄 Stream logs (Windows)
│   ├── stream_logs.ps1      # 🔄 Stream logs (PowerShell)
│   ├── stream_logs.sh       # 🔄 Stream logs (Linux)
│   ├── download_logs.bat    # 📥 Download logs (Windows)
│   ├── download_logs.sh     # 📥 Download logs (Linux)
│   ├── sync_logs.bat        # 🔄 Auto-sync logs
│   ├── manage_logs.bat      # 📋 Log manager menu
│   └── logs_bot.sh          # 📋 View bot logs
└── utilities/               # 🛠️ Utility Scripts
    ├── connect_vps.sh       # 🔌 Connect to VPS
    └── kill_all_python.sh   # 💀 Kill all Python processes
```

## 🚀 Quick Start

### Windows Users
```bash
# Use the master manager (recommended)
.\scripts\vps\vps_manager.bat

# Or use individual scripts
.\scripts\vps\bot-control\start_bot.sh
.\scripts\vps\log-management\stream_logs.bat
```

### Linux/Mac Users
```bash
# Use individual scripts
./scripts/vps/bot-control/start_bot.sh
./scripts/vps/log-management/stream_logs.sh
```

## 📋 Script Categories

### 🤖 Bot Control
- **start_bot.sh** - Start the QuranBot service
- **stop_bot.sh** - Stop the QuranBot service
- **restart_bot.sh** - Restart the QuranBot service
- **status_bot.sh** - Check if the bot is running
- **update_bot.sh** - Update bot files from git and restart

### 📋 Log Management
- **stream_logs.bat/.ps1/.sh** - Stream logs in real-time
- **download_logs.bat/.sh** - Download today's log file
- **sync_logs.bat** - Continuously sync logs every 30 seconds
- **manage_logs.bat** - Comprehensive log management menu
- **logs_bot.sh** - View bot logs on VPS

### 🛠️ Utilities
- **connect_vps.sh** - SSH into the VPS
- **kill_all_python.sh** - Kill all Python processes (emergency)

## 🔧 Configuration

All scripts use the SSH key located at:
```
C:/Users/hanna/.ssh/id_rsa
```

VPS connection details:
- **Host:** 159.89.90.90
- **User:** root
- **Bot Path:** /opt/quranbot

## 📊 Log Files

Log files are automatically named with the current date:
- VPS: `/opt/quranbot/logs/YYYY-MM-DD.log`
- Local: `logs/quranbot_vps_YYYY-MM-DD.log`

## 🎯 Recommended Usage

1. **Daily Management:** Use `vps_manager.bat` for most operations
2. **Real-time Monitoring:** Use `stream_logs.bat` to watch logs live
3. **Troubleshooting:** Use `status_bot.sh` and `logs_bot.sh` for diagnostics
4. **Updates:** Use `update_bot.sh` to deploy changes

## ⚠️ Important Notes

- All scripts require SSH access to the VPS
- The bot runs as a systemd service (`quranbot.service`)
- Logs are automatically rotated daily
- The bot auto-restarts on failure 